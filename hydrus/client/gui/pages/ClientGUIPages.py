import collections
import collections.abc
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIReviewWindowsQuick
from hydrus.client.gui import QtInit
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.pages import ClientGUIPagesCore
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUINewPageChooser
from hydrus.client.gui.pages import ClientGUIMediaResultsPanel
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelThumbnails
from hydrus.client.gui.pages import ClientGUISession
from hydrus.client.gui.pages import ClientGUISidebar

# noinspection PyUnresolvedReferences
from hydrus.client.gui.pages import ClientGUISessionLegacy # to get serialisable data types loaded

from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

def ConvertNumHashesToWeight( num_hashes: int ) -> int:
    
    return num_hashes
    
def ConvertNumHashesAndSeedsToWeight( num_hashes: int, num_seeds: int ) -> int:
    
    return ConvertNumHashesToWeight( num_hashes ) + ConvertNumSeedsToWeight( num_seeds )
    
def ConvertNumSeedsToWeight( num_seeds: int ) -> int:
    
    return num_seeds * 20
    

def GetParentNotebook( widget: QW.QWidget ) -> "PagesNotebook | None":
    
    parent = widget.parentWidget()
    
    while not isinstance( parent, PagesNotebook ):
        
        if parent is None:
            
            return None
            
        
        parent = parent.parentWidget()
        
    
    return parent
    

class Page( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, page_manager: ClientGUIPageManager.PageManager, initial_hashes ):
        
        super().__init__( parent )
        
        self._page_key = CG.client_controller.AcquirePageKey()
        
        self._page_manager = page_manager
        
        self._initial_hashes = initial_hashes
        self._initial_hash_blocks_still_to_load = []
        self._initial_media_results_loaded = []
        
        self._page_manager.SetVariable( 'page_key', self._page_key )
        
        if len( initial_hashes ) > 0:
            
            self._page_manager.NotifyLoadingWithHashes()
            
        
        self._initialised = len( initial_hashes ) == 0
        self._pre_initialisation_media_results = []
        
        self._initial_media_results_load_updater = self._InitialiseInitialMediaResultsLoadUpdater()
        
        self._pretty_status = ''
        self._pretty_status_override = ''
        
        self._management_media_split = QW.QSplitter( self )
        self._management_media_split.setOrientation( QC.Qt.Orientation.Horizontal )
        
        self._search_preview_split = QW.QSplitter( self._management_media_split )
        self._search_preview_split.setOrientation( QC.Qt.Orientation.Vertical )
        
        self._done_split_setups = False
        
        self._sidebar = ClientGUISidebar.CreateSidebar( self._search_preview_split, self, self._page_manager )
        
        self._preview_panel = QW.QFrame( self._search_preview_split )
        self._preview_panel.setFrameStyle( QW.QFrame.Shape.Panel | QW.QFrame.Shadow.Sunken )
        self._preview_panel.setLineWidth( 2 )
        
        self._preview_canvas = ClientGUICanvas.CanvasPanelWithHovers( self._preview_panel, self._page_key, self._page_manager.GetLocationContext() )
        
        self._sidebar.locationChanged.connect( self._preview_canvas.SetLocationContext )
        
        # this is the only place we _do_ want to set the split as the parent of the thumbnail panel. doing it on init avoids init flicker
        self._media_panel = self._sidebar.GetDefaultEmptyMediaResultsPanel( self._management_media_split )
        
        self._management_media_split.addWidget( self._search_preview_split )
        self._management_media_split.addWidget( self._media_panel )
        
        self._search_preview_split.addWidget( self._sidebar )
        self._search_preview_split.addWidget( self._preview_panel )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._preview_canvas, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._preview_panel.setLayout( vbox )
        
        self._management_media_split.widget( 0 ).setMinimumWidth( 120 )
        self._management_media_split.widget( 1 ).setMinimumWidth( 120 )
        
        self._management_media_split.setStretchFactor( 0, 0 )
        self._management_media_split.setStretchFactor( 1, 1 )
        
        self._search_preview_split.widget( 0 ).setMinimumHeight( 180 )
        self._search_preview_split.widget( 1 ).setMinimumHeight( 180 )
        
        self._search_preview_split.setStretchFactor( 0, 1 )
        self._search_preview_split.setStretchFactor( 1, 0 )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._management_media_split, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._handle_event_filter = QP.WidgetEventFilter( self._management_media_split.handle( 1 ) )
        self._handle_event_filter.EVT_LEFT_DCLICK( self.EventUnsplit )
        
        self._search_preview_split._handle_event_filter = QP.WidgetEventFilter( self._search_preview_split.handle( 1 ) )
        self._search_preview_split._handle_event_filter.EVT_LEFT_DCLICK( self.EventPreviewUnsplit )
        
        CG.client_controller.sub( self, 'SetSplitterPositions', 'set_splitter_positions' )
        
        self._current_session_page_container = None
        self._current_session_page_container_hashes_hash = self._GetCurrentSessionPageHashesHash()
        self._current_session_page_container_timestamp = 0
        
        self._ConnectMediaResultsPanelSignals()
        
        self.SetSplitterPositions()
        
        self._search_preview_split.splitterMoved.connect( self._PreviewSplitterMoved )
        
        self._preview_canvas.launchMediaViewer.connect( self._PreviewCanvasWantsToLaunchMediaViewer )
        
    
    def _ConnectMediaResultsPanelSignals( self ):
        
        self._media_panel.refreshQuery.connect( self.RefreshQuery )
        self._media_panel.focusMediaChanged.connect( self._preview_canvas.SetMedia )
        self._media_panel.focusMediaCleared.connect( self._preview_canvas.ClearMedia )
        self._media_panel.focusMediaPaused.connect( self._preview_canvas.PauseMedia )
        self._media_panel.statusTextChanged.connect( self._SetPrettyStatus )
        
        self._sidebar.ConnectMediaResultsPanelSignals( self._media_panel )
        
    
    def _DoInitialMediaResultsLoadWork( self ):
        
        self._initial_media_results_load_updater.update()
        
    
    def _GetCurrentSessionPageHashesHash( self ):
        
        hashlist = self.GetHashes()
        
        hashlist_hashable = tuple( hashlist )
        
        return hash( hashlist_hashable )
        
    
    def _InitialiseInitialMediaResultsLoadUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            if len( self._initial_hash_blocks_still_to_load ) == 0:
                
                self._initialised = True
                
            
            if self._initialised:
                
                raise HydrusExceptions.CancelledException()
                
            
            if CG.client_controller.PageClosedButNotDestroyed( self._page_key ):
                
                raise HydrusExceptions.CancelledException()
                
            
            status = f'Loading initial files{HC.UNICODE_ELLIPSIS} {HydrusNumbers.ValueRangeToPrettyString( len( self._initial_media_results_loaded ), len( self._initial_hashes ) )}'
            
            self._SetPrettyStatus( status, override = True )
            
            block_of_hashes = self._initial_hash_blocks_still_to_load.pop()
            
            return block_of_hashes
            
        
        def work_callable( block_of_hashes ):
            
            block_of_media_results = CG.client_controller.Read( 'media_results', block_of_hashes )
            
            return block_of_media_results
            
        
        def publish_callable( block_of_media_results ):
            
            self._initial_media_results_loaded.extend( block_of_media_results )
            
            if len( self._initial_hash_blocks_still_to_load ) == 0:
                
                self._SetPrettyStatus( '', override = True )
                
                hashes_to_media_results = { media_result.GetHash() : media_result for media_result in self._initial_media_results_loaded }
                
                sorted_initial_media_results = [ hashes_to_media_results[ hash ] for hash in self._initial_hashes if hash in hashes_to_media_results ]
                
                media_panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self, self._page_key, self._page_manager, sorted_initial_media_results )
                
                self._SwapMediaResultsPanel( media_panel )
                
                self._initialised = True
                self._initial_media_results_loaded = []
                self._initial_hashes = []
                
                if len( self._pre_initialisation_media_results ) > 0:
                    
                    media_panel.AddMediaResults( self._page_key, self._pre_initialisation_media_results )
                    
                    self._pre_initialisation_media_results = []
                    
                
                CG.client_controller.CallAfterQtSafe( self, self._sidebar.Start )
                
            else:
                
                self._DoInitialMediaResultsLoadWork()
                
            
        
        return ClientGUIAsync.AsyncQtUpdater( 'page initial media results load', self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _PreviewCanvasWantsToLaunchMediaViewer( self ):
        
        media = self._preview_canvas.GetMedia()
        
        if media is not None:
            
            self._media_panel.LaunchMediaViewerOn( media )
            
        
    
    def _PreviewSplitterMoved( self ):
        
        sizes = self._search_preview_split.sizes()
        
        if len( sizes ) > 0:
            
            # can't test the preview itself, it has funky minimum size gubbins. we are explicitly testing the splitter viewport or whatever
            preview_split_size = sizes[-1]
            
            self._preview_canvas.SetSplitterHiddenStatus( preview_split_size == 0 )
            
        
    
    def _SetCurrentPageContainer( self, page_container: ClientGUISession.GUISessionContainerPageSingle ):
        
        self._current_session_page_container = page_container
        self._current_session_page_container_hashes_hash = self._GetCurrentSessionPageHashesHash()
        self._current_session_page_container_timestamp = HydrusTime.GetNow()
        
    
    def _SetPrettyStatus( self, status: str, override = False ):
        
        if override:
            
            self._pretty_status_override = status
            
        else:
            
            self._pretty_status = status
            
        
        if self.isVisible():
            
            CG.client_controller.gui.SetStatusBarDirty()
            
        
    
    def _SwapMediaResultsPanel( self, new_panel: ClientGUIMediaResultsPanel.MediaResultsPanel ):
        """
        Yo, it is important that the new_panel here starts with a parent _other_ than the splitter! The page itself is usually fine.
        If we give it the splitter as parent, you can get a frame of unusual layout flicker, usually a page-wide autocomplete input. Re-parent it here and we are fine.
        """
        
        previous_sizes = self._management_media_split.sizes()
        
        self._preview_canvas.ClearMedia()
        
        self._media_panel.ClearPageKey()
        
        media_collect = self._sidebar.GetMediaCollect()
        
        if media_collect.DoesACollect():
            
            new_panel.Collect( media_collect )
            
            media_sort = self._sidebar.GetMediaSort()
            
            new_panel.Sort( media_sort )
            
        
        old_panel = self._media_panel
        self._media_panel = new_panel
        
        # note focus isn't on the thumb panel but some innerwidget scroll gubbins
        had_focus_before = ClientGUIFunctions.IsQtAncestor( QW.QApplication.focusWidget(), old_panel )
        
        if QtInit.WE_ARE_QT5:
            
            # this takes ownership of new_panel
            self._management_media_split.insertWidget( 1, new_panel )
            
            old_panel.setParent( None )
            old_panel.setVisible( False )
            
        else:
            
            if new_panel.parentWidget() == self._management_media_split:
                
                # ideally, this does not occur. we always want to replace and reduce flicker
                
                old_panel.setParent( None )
                old_panel.setVisible( False )
                
            else:
                
                # this sets parent of new panel to self and sets parent of old panel to None
                # rumao, it doesn't work if new_panel is already our child
                self._management_media_split.replaceWidget( 1, new_panel )
                
            
        
        self._media_panel.setMinimumWidth( 120 )
        
        self._management_media_split.setStretchFactor( 1, 1 )
        
        self._management_media_split.setSizes( previous_sizes )
        
        self._ConnectMediaResultsPanelSignals()
        
        CG.client_controller.pub( 'refresh_page_name', self._page_key )
        
        CG.client_controller.pub( 'notify_new_pages_count' )
        
        if had_focus_before:
            
            ClientGUIFunctions.SetFocusLater( new_panel )
            
        
        # if we try to kill a media page while a menu is open on it, we can enter program instability.
        # so let's just put it off.
        def clean_up_old_panel():
            
            if CGC.core().MenuIsOpen():
                
                CG.client_controller.CallLaterQtSafe( self, 0.5, 'menu closed panel swap loop', clean_up_old_panel )
                
                return
                
            
            old_panel.CleanBeforeDestroy()
            
            old_panel.deleteLater()
            
        
        clean_up_old_panel()
        
    
    def ActivateFavouriteSearch( self, fav_search: tuple[ str, str ] ):
        
        self._sidebar.ActivateFavouriteSearch( fav_search )
        
    
    def AddMediaResults( self, media_results ):
        
        if self._initialised:
            
            self._media_panel.AddMediaResults( self._page_key, media_results )
            
        else:
            
            self._pre_initialisation_media_results.extend( media_results )
            
        
    
    def AskIfAbleToClose( self, for_session_close = False ):
        
        user_was_asked = False
        
        try:
            
            self.CheckAbleToClose( for_session_close = for_session_close )
            
        except HydrusExceptions.VetoException as e:
            
            message = f'Close "{self.GetName()}"?\n\n{e}'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            user_was_asked = True
            
            if result == QW.QDialog.DialogCode.Rejected:
                
                raise HydrusExceptions.VetoException()
                
            
        
        if not user_was_asked and CG.client_controller.new_options.GetBoolean( 'confirm_all_page_closes' ):
            
            message = f'Close "{self.GetName()}"?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Rejected:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def CheckAbleToClose( self, for_session_close = False ):
        
        self._sidebar.CheckAbleToClose( for_session_close = for_session_close )
        
    
    def CleanBeforeClose( self ):
        
        self._sidebar.CleanBeforeClose()
        
        self._media_panel.SetFocusedMedia( None )
        
    
    def CleanBeforeDestroy( self ):
        
        self._sidebar.CleanBeforeDestroy()
        
        self._preview_canvas.CleanBeforeDestroy()
        
        self._media_panel.CleanBeforeDestroy()
        
        CG.client_controller.ReleasePageKey( self._page_key )
        
    
    def EnterPredicates( self, predicates ):
        
        self._sidebar.EnterPredicates( self._page_key, predicates )
        
        
    def EventPreviewUnsplit( self, event ):
        
        QP.Unsplit( self._search_preview_split, self._preview_panel )
        
        self._media_panel.SetFocusedMedia( None )
        
    
    def EventUnsplit( self, event ):
        
        QP.Unsplit( self._management_media_split, self._search_preview_split )
        
        self._media_panel.SetFocusedMedia( None )
        
    
    def GetAPIInfoDict( self, simple ):
        
        d = {}
        
        d[ 'name' ] = self._page_manager.GetPageName()
        d[ 'page_key' ] = self._page_key.hex()
        d[ 'page_state' ] = self.GetPageState()
        d[ 'page_type' ] = self._page_manager.GetType()
        d[ 'is_media_page' ] = True
        
        management_info = self._page_manager.GetAPIInfoDict( simple )
        
        d[ 'management' ] = management_info
        
        media_info = self._media_panel.GetAPIInfoDict( simple )
        
        d[ 'media' ] = media_info
        
        return d
        
    
    def GetCollect( self ):
        
        return self._sidebar.GetMediaCollect()
        
    
    def GetHashes( self ):
        
        if self._initialised:
            
            return self._media_panel.GetHashes( ordered = True )
            
        else:
            
            hashes = list( self._initial_hashes )
            hashes.extend( ( media_result.GetHash() for media_result in self._pre_initialisation_media_results ) )
            
            hashes = HydrusLists.DedupeList( hashes )
            
            return hashes
            
        
    
    def GetPageManager( self ):
        
        return self._page_manager
        
    
    def GetSidebar( self ):
        
        return self._sidebar
        
    
    # used by autocomplete
    def GetMedia( self ):
        
        return self._media_panel.GetSortedMedia()
        
    
    def GetMediaResultsPanel( self ):
        
        return self._media_panel
        
    
    def GetName( self ):
        
        return self._page_manager.GetPageName()
        
    
    def GetNameForMenu( self, elide = True ) -> str:
        
        name_for_menu = self.GetName()
        
        ( num_files, ( num_value, num_range ) ) = self.GetNumFileSummary()
        
        if num_files > 0:
            
            name_for_menu = '{} - {} files'.format( name_for_menu, HydrusNumbers.ToHumanInt( num_files ) )
            
        
        if num_value != num_range:
            
            name_for_menu = '{} - {}'.format( name_for_menu, HydrusNumbers.ValueRangeToPrettyString( num_value, num_range ) )
            
        
        return HydrusText.ElideText( name_for_menu, 32, elide_center = True ) if elide else name_for_menu
        
    
    def GetNumFileSummary( self ):
        
        if self._initialised:
            
            num_files = self._media_panel.GetNumFiles()
            
        else:
            
            num_files = len( self._initial_hashes )
            
        
        ( num_value, num_range ) = self._page_manager.GetValueRange()
        
        if num_value == num_range:
            
            ( num_value, num_range ) = ( 0, 0 )
            
        
        return ( num_files, ( num_value, num_range ) )
        
    
    def GetPageKey( self ):
        
        return self._page_key
        
    
    def GetPageKeys( self ):
        
        return { self._page_key }
        
    
    def GetPageState( self ) -> int:
        
        if self._initialised:
            
            return self._sidebar.GetPageState()
            
        else:
            
            return CC.PAGE_STATE_INITIALISING
            
        
    
    def GetPrettyStatusForStatusBar( self ):
        
        if self._pretty_status_override != '':
            
            return self._pretty_status_override
            
        else:
            
            return self._pretty_status
            
        
    
    def GetSerialisablePage( self, only_changed_page_data, about_to_save ):
        
        if only_changed_page_data and not self.IsCurrentSessionPageDirty():
            
            hashes_to_page_data = {}
            
            skipped_unchanged_page_hashes = { self._current_session_page_container.GetPageDataHash() }
            
            return ( self._current_session_page_container, hashes_to_page_data, skipped_unchanged_page_hashes )
            
        
        name = self.GetName()
        
        page_data = ClientGUISession.GUISessionPageData( self._page_manager, self.GetHashes() )
        
        # this is the only place this is generated. this will be its key/name/id from now on
        # we won't regen the hash for identifier since it could change due to object updates etc...
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( name, page_data_hash )
        
        hashes_to_page_data = { page_data_hash : page_data }
        
        if about_to_save:
            
            self._SetCurrentPageContainer( page_container )
            
        
        skipped_unchanged_page_hashes = set()
        
        return ( page_container, hashes_to_page_data, skipped_unchanged_page_hashes )
        
    
    def GetSessionAPIInfoDict( self, is_selected = False ):
        
        root = {}
        
        root[ 'name' ] = self.GetName()
        root[ 'page_key' ] = self._page_key.hex()
        root[ 'page_state' ] = self.GetPageState()
        root[ 'page_type' ] = self._page_manager.GetType()
        root[ 'is_media_page' ] = True
        root[ 'selected' ] = is_selected
        
        return root
        
    
    def GetSashPositions( self ):
        
        hpos = HC.options[ 'hpos' ]
        
        sizes = self._management_media_split.sizes()
        
        if len( sizes ) > 1:
            
            if sizes[0] != 0:
                
                hpos = sizes[0]
                
            
        
        vpos = HC.options[ 'vpos' ]
        
        sizes = self._search_preview_split.sizes()
        
        if len( sizes ) > 1:
            
            if sizes[1] != 0:
                
                vpos = - sizes[1]
                
            
        
        return ( hpos, vpos )
        
    
    def GetSort( self ):
        
        return self._sidebar.GetMediaSort()
        
    
    def GetTotalFileSize( self ):
        
        if self._initialised:
            
            return self._media_panel.GetTotalFileSize()
            
        else:
            
            return 0
            
        
    
    def GetTotalNumHashesAndSeeds( self ):
        
        num_hashes = len( self.GetHashes() )
        num_seeds = self._page_manager.GetNumSeeds()
        
        return ( num_hashes, num_seeds )
        
    
    def GetTotalWeight( self ) -> int:
        
        ( num_hashes, num_seeds ) = self.GetTotalNumHashesAndSeeds()
        
        return ConvertNumHashesAndSeedsToWeight( num_hashes, num_seeds )
        
    
    def IsCurrentSessionPageDirty( self ):
        
        if self._current_session_page_container is None:
            
            return True
            
        else:
            
            if self._GetCurrentSessionPageHashesHash() != self._current_session_page_container_hashes_hash:
                
                return True
                
            
            return self._page_manager.HasSerialisableChangesSince( self._current_session_page_container_timestamp )
            
        
    
    def IsGalleryDownloaderPage( self ):
        
        return self._page_manager.GetType() == ClientGUIPagesCore.PAGE_TYPE_IMPORT_MULTIPLE_GALLERY
        
    
    def IsImporter( self ):
        
        return self._page_manager.IsImporter()
        
    
    def IsInitialised( self ):
        
        return self._initialised
        
    
    def IsMultipleWatcherPage( self ):
        
        return self._page_manager.GetType() == ClientGUIPagesCore.PAGE_TYPE_IMPORT_MULTIPLE_WATCHER
        
    
    def IsURLImportPage( self ):
        
        return self._page_manager.GetType() == ClientGUIPagesCore.PAGE_TYPE_IMPORT_URLS
        
    
    def NotifyUnclosed( self ):
        
        self._DoInitialMediaResultsLoadWork()
        
    
    def PageHidden( self ):
        
        self._sidebar.PageHidden()
        self._media_panel.PageHidden()
        self._preview_canvas.PageHidden()
        
    
    def PageShown( self ):
        
        if self.isVisible() and not self._done_split_setups:
            
            self.SetSplitterPositions()
            
            self._done_split_setups = True
            
        
        self._sidebar.PageShown()
        self._media_panel.PageShown()
        self._preview_canvas.PageShown()
        
        self._DoInitialMediaResultsLoadWork()
        
    
    def RefreshQuery( self ):
        
        if self._initialised:
            
            self._sidebar.RefreshQuery()
            
        
    
    def SetMediaFocus( self ):
        
        self._media_panel.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    
    def SetName( self, name ):
        
        return self._page_manager.SetPageName( name )
        
    
    def SetPageContainerClean( self, page_container: ClientGUISession.GUISessionContainerPageSingle ):
        
        self._SetCurrentPageContainer( page_container )
        
    
    def SetPrettyStatus( self, page_key, status ):
        
        if page_key == self._page_key:
            
            if self._initialised:
                
                self._SetPrettyStatus( status )
                
            
        
    
    def SetSearchFocus( self ):
        
        self._sidebar.SetSearchFocus()
        
    
    def SetSplitterPositions( self, hpos = None, vpos = None ):
        
        # this has some hacky old wx stuff going on, but I've sliced it down a good bit too
        # I'm pretty sure vpos is always negative (we store the size of the preview panel), and the hpos positive (it is the management sidebar)
        # ultimately, the solution is to finally move on from these hell variable names vpos and hpos
        
        if hpos is None:
            
            hpos = HC.options[ 'hpos' ]
            
        
        if vpos is None:
            
            vpos = HC.options[ 'vpos' ]
            
        
        total_sum = sum( self._search_preview_split.sizes() )
        
        if total_sum == 0:
            
            return
            
        
        # handle if it was hidden before
        self._search_preview_split.setVisible( True )
        
        total_sum = sum( self._management_media_split.sizes() )
        
        if hpos < 0:
            
            self._management_media_split.setSizes( [ total_sum + hpos, -hpos ] )
            
        elif hpos > 0:
            
            self._management_media_split.setSizes( [ hpos, total_sum - hpos ] )
            
        
        # handle if it was hidden before
        self._preview_panel.setVisible( True )
        
        if vpos < 0:
            
            self._search_preview_split.setSizes( [ total_sum + vpos, -vpos ] )
            
        elif vpos > 0:
            
            self._search_preview_split.setSizes( [ vpos, total_sum - vpos ] )
            
        
        if HC.options[ 'hide_preview' ]:
            
            CG.client_controller.CallAfterQtSafe( self, QP.Unsplit, self._search_preview_split, self._preview_panel )
            
        
    
    def ShowHideSplit( self ):
        
        if QP.SplitterVisibleCount( self._management_media_split ) > 1:
            
            QP.Unsplit( self._management_media_split, self._search_preview_split )
            
            self.SetMediaFocus()
            
            self._media_panel.SetFocusedMedia( None )
            
        else:
            
            self.SetSplitterPositions()
            
            self.SetSearchFocus()
            
        
    
    def SetSort( self, media_sort, do_sort = True ):
        
        self._sidebar.SetMediaSort( media_sort, do_sort = do_sort )
        
    
    def Start( self ):
        
        if self._initial_hashes is not None and len( self._initial_hashes ) > 0:
            
            self._initial_hash_blocks_still_to_load = list( HydrusLists.SplitListIntoChunks( self._initial_hashes, 100 ) )
            
            self._DoInitialMediaResultsLoadWork()
            
        else:
            
            self._initialised = True
            
            # do this 'after' so on a long session setup, it all boots once session loaded
            CG.client_controller.CallAfterQtSafe( self, self._sidebar.Start )
            
        
    
    def SwapMediaResultsPanel( self, new_panel ):
        
        self._SwapMediaResultsPanel( new_panel )
        
    
    def REPEATINGPageUpdate( self ):
        
        self._sidebar.REPEATINGPageUpdate()
        
    

directions_for_notebook_tabs = {}

directions_for_notebook_tabs[ CC.DIRECTION_UP ] = QW.QTabWidget.TabPosition.North
directions_for_notebook_tabs[ CC.DIRECTION_LEFT ] = QW.QTabWidget.TabPosition.West
directions_for_notebook_tabs[ CC.DIRECTION_RIGHT ] = QW.QTabWidget.TabPosition.East
directions_for_notebook_tabs[ CC.DIRECTION_DOWN ] = QW.QTabWidget.TabPosition.South

def ConvertReasonsAndPagesToStatement( reasons_and_pages: list ) -> str:
    
    if len( reasons_and_pages ) > 0:
        
        message_blocks = []
        
        for ( reason, pages ) in reasons_and_pages:
            
            reason = typing.cast( str, reason )
            pages = typing.cast( list[ Page ], pages )
            
            names = [ page.GetName() for page in pages ]
            
            if len( pages ) == 1:
                
                message_block = f'page "{names[0]}" says: {reason}'
                
            else:
                
                message_block = f'pages{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( names )}say: {reason}'
                
            
            message_blocks.append( message_block )
            
        
        message = '\n----\n'.join( message_blocks )
        
        return message
        
    else:
        
        return ''
        
    

def ShowReasonsAndPagesConfirmationDialog( win: QW.QWidget, reasons_and_pages, message, auto_yes_time = None ):
    
    no_tuples = [
        ( 'no', 'no' ),
        ( 'no, but show me the pages', 'show' )
    ]
    
    ( result_code, data ) = ClientGUIDialogsQuick.GetYesNoNo( win, message, no_tuples = no_tuples, auto_yes_time = auto_yes_time, disable_yes_initially = True )
    
    if result_code == QW.QDialog.DialogCode.Accepted:
        
        return
        
    elif result_code == QW.QDialog.DialogCode.Rejected:
        
        if data == 'show':
            
            def spawn_this_guy():
                
                def catch_datamissing( page ):
                    
                    try:
                        
                        CG.client_controller.gui.ShowPage( page.GetPageKey() )
                        
                    except HydrusExceptions.DataMissing as e:
                        
                        raise HydrusExceptions.VetoException( str( e ) )
                        
                    
                
                choice_tuples = []
                
                for ( reason, pages ) in reasons_and_pages:
                    
                    choice_tuples.extend(
                        ( f'{reason}: {page.GetName()}', HydrusData.Call( catch_datamissing, page ), 'Show this page.' )
                        for page
                        in pages
                    )
                    
                
                ClientGUIReviewWindowsQuick.OpenListButtons( win, 'Go To Page', choice_tuples )
                
            
            CG.client_controller.CallAfterQtSafe( win, spawn_this_guy )
            
        
        raise HydrusExceptions.VetoException()
        
    

class PagesNotebook( QP.TabWidgetWithDnD ):
    
    freshSessionLoaded = QC.Signal( ClientGUISession.GUISessionContainer )
    
    def __init__( self, parent: QW.QWidget, name ):
        
        super().__init__( parent )
        
        direction = CG.client_controller.new_options.GetInteger( 'notebook_tab_alignment' )
        
        self.setTabPosition( directions_for_notebook_tabs[ direction ] )
        
        self._page_key = CG.client_controller.AcquirePageKey()
        
        self._name = name
        
        self._next_new_page_index = None
        
        self._potential_drag_page = None
        
        self._closed_pages = []
        
        CG.client_controller.sub( self, 'RefreshPageName', 'refresh_page_name' )
        CG.client_controller.sub( self, 'TryToUncloseThisPage', 'unclose_this_page' )
        CG.client_controller.sub( self, '_UpdateOptions', 'notify_new_options' )
        
        self.currentChanged.connect( self.pageJustChanged )
        self.pageDragAndDropped.connect( self._RefreshPageNamesAfterDnD )
        
        # noinspection PyUnresolvedReferences
        self.tabBar().tabDoubleLeftClicked.connect( self._RenamePage )
        # noinspection PyUnresolvedReferences
        self.tabBar().tabMiddleClicked.connect( self._ClosePage )
        
        # noinspection PyUnresolvedReferences
        self.tabBar().tabSpaceDoubleLeftClicked.connect( self.ChooseNewPage )
        # noinspection PyUnresolvedReferences
        self.tabBar().tabSpaceDoubleMiddleClicked.connect( self.ChooseNewPage )
        
        self._previous_page_index = -1
        
        self._time_of_last_move_selection_event = 0
        
        self._UpdateOptions()
        
        self.tabBar().installEventFilter( self )
        self.installEventFilter( self )
        
    
    def _ChooseNewPage( self, insertion_index = None ):
        
        self._next_new_page_index = insertion_index
        
        with ClientGUINewPageChooser.DialogPageChooser( self, CG.client_controller ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( page_type, page_data ) = dlg.GetValue()
                
                if page_type == 'pages':
                    
                    new_notebook = self.NewPagesNotebook()
                    
                    if CG.client_controller.new_options.GetBoolean( 'rename_page_of_pages_on_pick_new' ):
                        
                        message = 'Enter the name for the new page of pages.'
                        
                        try:
                            
                            new_name = ClientGUIDialogsQuick.EnterText( self, message, default = 'pages' )
                            
                        except HydrusExceptions.CancelledException:
                            
                            return
                            
                        
                        new_notebook.SetName( new_name )
                        
                        CG.client_controller.pub( 'refresh_page_name', new_notebook.GetPageKey() )
                        
                    
                elif page_type == 'page':
                    
                    page_manager = page_data
                    
                    self.NewPage( page_manager )
                    
                
            
        
    
    def _CloseAllPages( self, polite = True, delete_pages = False ):
        
        closees = [ index for index in range( self.count() ) ]
        
        self._ClosePages( closees, 'pages', polite = polite, delete_pages = delete_pages )
        
    
    def _CloseLeftPages( self, from_index ):
        
        closees = [ index for index in range( self.count() ) if index < from_index ]
        
        self._ClosePages( closees, 'pages to the left' )
        
        
    
    def _CloseOtherPages( self, except_index ):
        
        closees = [ index for index in range( self.count() ) if index != except_index ]
        
        self._ClosePages( closees, 'other pages' )
        
    
    def _ClosePage( self, index, polite = True, delete_page = False ):
        
        CG.client_controller.ResetIdleTimer()
        CG.client_controller.ResetPageChangeTimer()
        
        if index < 0 or index > self.count() - 1:
            
            return False
            
        
        page = typing.cast( Page | PagesNotebook, self.widget( index ) )
        
        if polite:
            
            try:
                
                page.AskIfAbleToClose()
                
            except HydrusExceptions.VetoException:
                
                return False
                
            
        
        we_are_closing_the_current_focus = index == self.currentIndex()
        
        page.CleanBeforeClose()
        
        page_key = page.GetPageKey()
        
        self._closed_pages.append( ( index, page_key ) )
        
        self.removeTab( index )
        
        CG.client_controller.pub( 'refresh_page_name', self._page_key )
        
        if delete_page:
            
            CG.client_controller.pub( 'notify_deleted_page', page )
            
        else:
            
            CG.client_controller.pub( 'notify_closed_page', page )
            
        
        if we_are_closing_the_current_focus:
            
            focus_goes_to = CG.client_controller.new_options.GetInteger( 'close_page_focus_goes' )
            
            new_page_focus = None
            
            if focus_goes_to == CC.CLOSED_PAGE_FOCUS_GOES_LEFT:
                
                new_page_focus = index - 1
                
            elif focus_goes_to == CC.CLOSED_PAGE_FOCUS_GOES_RIGHT:
                
                new_page_focus = index
                
            
            if new_page_focus is not None and index >= 0 or index <= self.count() - 1 and new_page_focus != self.currentIndex():
                
                self.setCurrentIndex( new_page_focus )
                
            
        
        self.UpdatePreviousPageIndex()
        
        return True
        
    
    def _ClosePages( self, indices, pages_description, polite = True, delete_pages = False ):
        
        if not polite:
            
            do_it = True
            
        else:
            
            actual_num_pages = 0
            actual_media_pages = []
            
            for i in indices:
                
                page = self.widget( i )
                
                if isinstance( page, Page ):
                    
                    actual_num_pages += 1
                    actual_media_pages.append( page )
                    
                elif isinstance( page, PagesNotebook ):
                    
                    actual_num_pages += 1 + page.GetNumPagesHeld()
                    actual_media_pages.extend( page.GetMediaPages( only_my_level = False ) )
                    
                
            
            reasons_and_pages = self.GetAbleToCloseData( pages = actual_media_pages )
            
            if len( reasons_and_pages ) > 0:
                
                statement = ConvertReasonsAndPagesToStatement( reasons_and_pages )
                
                message = f'Are you sure you want to close {HydrusNumbers.ToHumanInt( actual_num_pages )} {pages_description}?'
                message += '\n' * 2
                message += statement
                
                try:
                    
                    # raises veto on no
                    ShowReasonsAndPagesConfirmationDialog( self, reasons_and_pages, message )
                    
                    do_it = True
                    
                except HydrusExceptions.VetoException:
                    
                    do_it = False
                    
                
            else:
                
                message = f'Close {HydrusNumbers.ToHumanInt( actual_num_pages )} {pages_description}?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                do_it = result == QW.QDialog.DialogCode.Accepted
                
            
        
        if do_it:
            
            indices = list( indices )
            
            indices.sort( reverse = True ) # so we are closing from the end first
            
            for index in indices:
                
                successful = self._ClosePage( index, polite = False, delete_page = delete_pages )
                
                if not successful:
                    
                    break
                    
                
            
        
    
    def _CloseRightPages( self, from_index ):
        
        closees = [ index for index in range( self.count() ) if index > from_index ]
        
        self._ClosePages( closees, 'pages to the right' )
        
    
    def _CollapsePage( self, page_index: int ):
        
        if 0 <= page_index <= self.count() - 1:
            
            page = typing.cast( Page | PagesNotebook, self.widget( page_index ) )
            
            hashes = page.GetHashes()
            
            message = f'This will collect the {HydrusNumbers.ToHumanInt(len(hashes))} files in this page and place them, in current order, in a single new search page. This can work on a page of pages.'
            message += '\n\n'
            message += 'The old page will be closed, no matter its type.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
            self._ClosePages( [ page_index ], 'collapsing', polite = False )
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self.NewPageQuery( default_location_context, initial_hashes = hashes, forced_insertion_index = page_index )
            
        
    
    def _CollapsePagesToTheRight( self, page_index: int ):
        
        closees = [ index for index in range( self.count() ) if index >= page_index ]
        
        hashes = []
        
        for index in closees:
            
            page = typing.cast( Page | PagesNotebook, self.widget( index ) )
            
            hashes.extend( page.GetHashes() )
            
        
        hashes = HydrusLists.DedupeList( hashes )
        
        message = f'This will collect the {HydrusNumbers.ToHumanInt(len(hashes))} files in view in the {HydrusNumbers.ToHumanInt(len(closees))} pages and place them, in current order, in a single new search page.'
        message += '\n\n'
        message += 'All the pages harvested from will be closed, no matter their type.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        self._ClosePages( closees, 'collapsing', polite = False )
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        self.NewPageQuery( default_location_context, initial_hashes = hashes, forced_insertion_index = page_index )
        
    
    def _DuplicatePage( self, index ):
        
        if index == -1 or index > self.count() - 1:
            
            return False
            
        
        page = typing.cast(  Page | PagesNotebook, self.widget( index ) )
        
        only_changed_page_data = False
        about_to_save = False
        
        ( container, hashes_to_page_data, skipped_unchanged_page_hashes ) = page.GetSerialisablePage( only_changed_page_data, about_to_save )
        
        top_notebook_container = ClientGUISession.GUISessionContainerPageNotebook( 'dupe top notebook', page_containers = [ container ] )
        
        session = ClientGUISession.GUISessionContainer( 'dupe session', top_notebook_container = top_notebook_container, hashes_to_page_data = hashes_to_page_data )
        
        self.InsertSession( index + 1, session, session_is_clean = False )
        
    
    def _GetDefaultPageInsertionIndex( self ):
        
        new_options = CG.client_controller.new_options
        
        new_page_goes = new_options.GetInteger( 'default_new_page_goes' )
        
        current_index = self.currentIndex()
        
        if current_index == -1:
            
            new_page_goes = CC.NEW_PAGE_GOES_FAR_LEFT
            
        
        if new_page_goes == CC.NEW_PAGE_GOES_FAR_LEFT:
            
            insertion_index = 0
            
        elif new_page_goes == CC.NEW_PAGE_GOES_LEFT_OF_CURRENT:
            
            insertion_index = current_index
            
        elif new_page_goes == CC.NEW_PAGE_GOES_RIGHT_OF_CURRENT:
            
            insertion_index = current_index + 1
            
        elif new_page_goes == CC.NEW_PAGE_GOES_FAR_RIGHT:
            
            insertion_index = self.count()
            
        else:
            
            insertion_index = 0
            
        
        return insertion_index
        
    
    def _GetMediaPages( self, only_my_level ) -> list[ Page ]:
        
        results = []
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                if not only_my_level:
                    
                    results.extend( page.GetMediaPages() )
                    
                
            else:
                
                results.append( page )
                
            
        
        return results
        
    
    def _GetIndex( self, page_key ):
        
        for ( page, index ) in ( ( self.widget( index ), index ) for index in range( self.count() ) ):
            
            page = typing.cast( Page | PagesNotebook, page )
            
            if page.GetPageKey() == page_key:
                
                return index
                
            
        
        raise HydrusExceptions.DataMissing()
        
    
    def _GetNotebookFromScreenPosition( self, screen_position ) -> "PagesNotebook":
        
        current_page = self.currentWidget()
        
        if current_page is None or not isinstance( current_page, PagesNotebook ):
            
            return self
            
        else:
            
            on_child_notebook_somewhere = current_page.mapFromGlobal( screen_position ).y() > current_page.pos().y()
            
            if on_child_notebook_somewhere:
                
                return current_page._GetNotebookFromScreenPosition( screen_position )
                
            
        
        return self
        
    
    def _GetPages( self ) -> "list[ Page | PagesNotebook ]":
        
        return [ self.widget( i ) for i in range( self.count() ) ]
        
    
    def _GetPageFromName( self, page_name, only_media_pages = False ):
        
        for page in self._GetPages():
            
            if page.GetName() == page_name:
                
                do_not_do_it = only_media_pages and isinstance( page, PagesNotebook )
                
                if not do_not_do_it:
                    
                    return page
                    
                
            
            if isinstance( page, PagesNotebook ):
                
                result = page._GetPageFromName( page_name, only_media_pages = only_media_pages )
                
                if result is not None:
                    
                    return result
                    
                
            
        
        return None
        
    
    def _MovePage( self, page, dest_notebook: "PagesNotebook", insertion_tab_index, follow_dropped_page = False ):
        
        source_notebook = GetParentNotebook( page )
        
        if source_notebook is None:
            
            return
            
        
        source_notebook = typing.cast( PagesNotebook, source_notebook )
        
        for ( index, p ) in enumerate( source_notebook.GetPages() ):
            
            if p == page:
                
                source_notebook.removeTab( index )
                
                source_notebook.UpdatePreviousPageIndex()
                
                break
                
            
        
        if source_notebook != dest_notebook:
            
            page.setParent( dest_notebook )
            
            CG.client_controller.pub( 'refresh_page_name', source_notebook.GetPageKey() )
            
        
        insertion_tab_index = min( insertion_tab_index, dest_notebook.count() )
        
        dest_notebook.insertTab( insertion_tab_index, page, page.GetName() )
        
        if follow_dropped_page: dest_notebook.setCurrentIndex( insertion_tab_index )
        
        if follow_dropped_page:
            
            self.ShowPage( page )
            
        
        CG.client_controller.pub( 'refresh_page_name', page.GetPageKey() )
        
    
    def _RefreshPageName( self, index ):
        
        if index == -1 or index > self.count() - 1:
            
            return
            
        
        new_options = CG.client_controller.new_options
        
        max_page_name_chars = new_options.GetInteger( 'max_page_name_chars' )
        
        page_file_count_display = new_options.GetInteger( 'page_file_count_display' )
        
        import_page_progress_display = new_options.GetBoolean( 'import_page_progress_display' )
        
        page: Page | PagesNotebook = self.widget( index )
        
        if isinstance( page, Page ) and not page.IsInitialised():
            
            full_page_name = 'initialising'
            
        else:
            
            full_page_name = page.GetName()
            
            full_page_name = ''.join( full_page_name.splitlines() )
            
            full_page_name = full_page_name[:256]
            
        
        page_name = HydrusText.ElideText( full_page_name, max_page_name_chars )
        
        do_tooltip = len( page_name ) != len( full_page_name ) or CG.client_controller.new_options.GetBoolean( 'elide_page_tab_names' )
        
        num_string = ''
        
        ( num_files, ( num_value, num_range ) ) = page.GetNumFileSummary()
        
        a = page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ALL
        b = page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS and page.IsImporter()
        c = page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ALL_BUT_ONLY_IF_GREATER_THAN_ZERO and num_files > 0
        
        if a or b or c:
            
            num_string += HydrusNumbers.ToHumanInt( num_files )
            
        
        if import_page_progress_display:
            
            if num_range > 0 and num_value != num_range:
                
                if len( num_string ) > 0:
                    
                    num_string += ' - '
                    
                
                num_string += HydrusNumbers.ValueRangeToPrettyString( num_value, num_range )
                
            
        
        if len( num_string ) > 0:
            
            page_name += f' ({num_string})'
            
        
        if isinstance( page, PagesNotebook ) and CG.client_controller.new_options.GetBoolean( 'decorate_page_of_pages_tab_names' ):
            
            name_decorator = CG.client_controller.new_options.GetString( 'page_of_pages_decorator' )
            
            page_name += name_decorator
            
        
        safe_page_name = ClientGUIFunctions.EscapeMnemonics( page_name )
        
        tab_bar = self.tabBar()
        
        existing_page_name = tab_bar.tabText( index )
        
        if existing_page_name not in ( safe_page_name, page_name ):
            
            tab_bar.setTabText( index, safe_page_name )
            
            if do_tooltip:
                
                self.setTabToolTip( index, full_page_name )
                
            
        
    
    def _RenamePage( self, index ):
        
        if index == -1 or index > self.count() - 1:
            
            return
            
        
        page: Page | PagesNotebook = self.widget( index )
        
        current_name = page.GetName()
        
        message = 'Enter the new name.'
        
        try:
            
            new_name = ClientGUIDialogsQuick.EnterText( self, message, default = current_name )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        page.SetName( new_name )
        
        CG.client_controller.pub( 'refresh_page_name', page.GetPageKey() )
        
    
    def _SendPageToNewNotebook( self, index ):
        
        if 0 <= index <= self.count() - 1:
            
            page = self.widget( index )
            
            dest_notebook = self.NewPagesNotebook( forced_insertion_index = index, give_it_a_blank_page = False )
            
            self._MovePage( page, dest_notebook, 0 )
            
            if CG.client_controller.new_options.GetBoolean( 'rename_page_of_pages_on_send' ):
                
                message = 'Enter the name for the new page of pages.'
                
                try:
                    
                    new_name = ClientGUIDialogsQuick.EnterText( self, message, default = 'pages' )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                dest_notebook.SetName( new_name )
                
                CG.client_controller.pub( 'refresh_page_name', dest_notebook.GetPageKey() )
                
            
        
    
    def _SendRightPagesToNewNotebook( self, from_index ):
        
        message = 'Send all pages to the right to a new page of pages?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            pages_index = self.count()
            
            dest_notebook = self.NewPagesNotebook( forced_insertion_index = pages_index, give_it_a_blank_page = False )
            
            movees = list( range( from_index, pages_index ) )
            
            movees.reverse()
            
            for index in movees:
                
                page = self.widget( index )
                
                self._MovePage( page, dest_notebook, 0 )
                
            
            if CG.client_controller.new_options.GetBoolean( 'rename_page_of_pages_on_send' ):
                
                message = 'Enter the name for the new page of pages.'
                
                try:
                    
                    new_name = ClientGUIDialogsQuick.EnterText( self, message, default = 'pages' )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                dest_notebook.SetName( new_name )
                
                CG.client_controller.pub( 'refresh_page_name', dest_notebook.GetPageKey() )
                
            
        
    
    def _ShiftPage( self, page_index, delta = None, new_index = None ):
        
        new_page_index = page_index
        
        if delta is not None:
            
            new_page_index = page_index + delta
            
        
        if new_index is not None:
            
            new_page_index = new_index
            
        
        if new_page_index == page_index:
            
            return
            
        
        if 0 <= new_page_index <= self.count() - 1:
            
            page_is_selected = self.currentIndex() == page_index
            
            page = self.widget( page_index )
            name = self.tabText( page_index )
            
            self.removeTab( page_index )
            
            self.UpdatePreviousPageIndex()
            
            self.insertTab( new_page_index, page, name )
            if page_is_selected: self.setCurrentIndex( new_page_index )
            
        
    
    def _ShowMenu( self, screen_position ):
        
        tab_index = ClientGUIFunctions.NotebookScreenToHitTest( self, screen_position )
        
        num_pages = self.count()
        
        end_index = num_pages - 1
        
        more_than_one_tab = num_pages > 1
        
        click_over_tab = tab_index != -1
        
        can_go_home = tab_index > 1
        can_go_left = tab_index > 0
        can_go_right = tab_index < end_index
        can_go_end = tab_index < end_index - 1
        
        click_over_page_of_pages = False
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if click_over_tab:
            
            page: Page | PagesNotebook = self.widget( tab_index )
            
            click_over_page_of_pages = isinstance( page, PagesNotebook )
            
            if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                label = 'page weight: {}'.format( HydrusNumbers.ToHumanInt( page.GetTotalWeight() ) )
                
                ClientGUIMenus.AppendMenuLabel( menu, label, label )
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            ClientGUIMenus.AppendMenuItem( menu, 'close page', 'Close this page.', self._ClosePage, tab_index )
            
            if more_than_one_tab:
                
                if not can_go_left or not can_go_right:
                    
                    if num_pages == 2:
                        
                        label = 'close other page'
                        description = 'Close the other page.'
                        
                    else:
                        
                        label = 'close other pages'
                        description = 'Close all pages but this one.'
                        
                    
                    ClientGUIMenus.AppendMenuItem( menu, label, description, self._CloseOtherPages, tab_index )
                    
                else:
                    
                    close_menu = ClientGUIMenus.GenerateMenu( menu )
                    
                    ClientGUIMenus.AppendMenuItem( close_menu, 'other pages', 'Close all pages but this one.', self._CloseOtherPages, tab_index )
                    
                    if can_go_left:
                        
                        ClientGUIMenus.AppendMenuItem( close_menu, 'pages to the left', 'Close all pages to the left of this one.', self._CloseLeftPages, tab_index )
                        
                    
                    if can_go_right:
                        
                        ClientGUIMenus.AppendMenuItem( close_menu, 'pages to the right', 'Close all pages to the right of this one.', self._CloseRightPages, tab_index )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, close_menu, 'close' )
                    
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        #
        
        if click_over_page_of_pages:
            
            notebook_to_get_selectable_media_pages_from = self.widget( tab_index )
            
        else:
            
            notebook_to_get_selectable_media_pages_from = self
            
        
        selectable_media_pages = notebook_to_get_selectable_media_pages_from.GetMediaPages()
        
        if len( selectable_media_pages ) > 0:
            
            select_menu = ClientGUIMenus.GenerateMenu( menu )
            
            for selectable_media_page in selectable_media_pages:
                
                label = selectable_media_page.GetNameForMenu()
                
                ClientGUIMenus.AppendMenuItem( select_menu, label, 'select this page', self.ShowPage, selectable_media_page )
                
            
            ClientGUIMenus.AppendMenu( menu, select_menu, 'pages' )
            
        
        #
        
        if more_than_one_tab:
            
            selection_index = self.currentIndex()
            
            can_select_home = selection_index > 1
            can_select_left = selection_index > 0
            can_select_right = selection_index < end_index
            can_select_end = selection_index < end_index - 1
            
            navigate_menu = ClientGUIMenus.GenerateMenu( menu )
            
            if can_select_home:
                
                ClientGUIMenus.AppendMenuItem( navigate_menu, 'first page', 'Select the page at the start of these.', self.MoveSelectionEnd, -1 )
                
            
            if can_select_left:
                
                ClientGUIMenus.AppendMenuItem( navigate_menu, 'page to the left', 'Select the page to the left of this one.', self.MoveSelection, -1 )
                
            
            if can_select_right:
                
                ClientGUIMenus.AppendMenuItem( navigate_menu, 'page to the right', 'Select the page to the right of this one.', self.MoveSelection, 1 )
                
            
            if can_select_end:
                
                ClientGUIMenus.AppendMenuItem( navigate_menu, 'last page', 'Select the page at the end of these.', self.MoveSelectionEnd, 1 )
                
            
            ClientGUIMenus.AppendMenu( menu, navigate_menu, 'select' )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'new page', 'Choose a new page.', self._ChooseNewPage )
        
        if click_over_tab:
            
            ClientGUIMenus.AppendMenuItem( menu, 'new page here', 'Choose a new page.', self._ChooseNewPage, tab_index )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if more_than_one_tab:
                
                move_menu = ClientGUIMenus.GenerateMenu( menu )
                
                if can_go_home:
                    
                    ClientGUIMenus.AppendMenuItem( move_menu, 'to left end', 'Move this page all the way to the left.', self._ShiftPage, tab_index, new_index=0 )
                    
                
                if can_go_left:
                    
                    ClientGUIMenus.AppendMenuItem( move_menu, 'left', 'Move this page one to the left.', self._ShiftPage, tab_index, delta=-1 )
                    
                
                if can_go_right:
                    
                    ClientGUIMenus.AppendMenuItem( move_menu, 'right', 'Move this page one to the right.', self._ShiftPage, tab_index, 1 )
                    
                
                if can_go_end:
                    
                    ClientGUIMenus.AppendMenuItem( move_menu, 'to right end', 'Move this page all the way to the right.', self._ShiftPage, tab_index, new_index=end_index )
                    
                
                ClientGUIMenus.AppendMenu( menu, move_menu, 'move page' )
                
            
            ClientGUIMenus.AppendMenuItem( menu, 'rename page', 'Rename this page.', self._RenamePage, tab_index )
            
            ClientGUIMenus.AppendMenuItem( menu, 'duplicate page', 'Duplicate this page.', self._DuplicatePage, tab_index )
            
            if more_than_one_tab:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                submenu = ClientGUIMenus.GenerateMenu( menu )
                
                ClientGUIMenus.AppendMenuItem( submenu, 'by most files first', 'Sort these pages according to how many files they have.', self._SortPagesByFileCount, 'desc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by fewest files first', 'Sort these pages according to how few files they have.', self._SortPagesByFileCount, 'asc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by largest total file size first', 'Sort these pages according to how large their files are.', self._SortPagesByFileSize, 'desc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by smallest total file size first', 'Sort these pages according to how small their files are.', self._SortPagesByFileSize, 'asc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by name a-z', 'Sort these pages according to their names.', self._SortPagesByName, 'asc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by name z-a', 'Sort these pages according to their names.', self._SortPagesByName, 'desc' )
                
                ClientGUIMenus.AppendMenu( menu, submenu, 'sort pages' )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            collapse_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( collapse_menu, 'this page', 'Gather the files in this page and put them all in a new single searc hpage.', self._CollapsePage, tab_index )
            
            if can_go_right:
                
                ClientGUIMenus.AppendMenuItem( collapse_menu, 'pages from here to the right', 'Gather all the files from here to the right and put them all in a single search page.', self._CollapsePagesToTheRight, tab_index )
                ClientGUIMenus.AppendMenuItem( collapse_menu, 'pages to the right', 'Gather all the files from the right of here and put them all in a single search page.', self._CollapsePagesToTheRight, tab_index + 1 )
                
            
            ClientGUIMenus.AppendMenu( menu, collapse_menu, 'collapse to a single page' )
            
            send_down_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( send_down_menu, 'this page', 'Make a new page of pages and put this page in it.', self._SendPageToNewNotebook, tab_index )
            
            if can_go_right:
                
                ClientGUIMenus.AppendMenuItem( send_down_menu, 'pages from here to the right', 'Make a new page of pages and put this and all the pages to the right into it.', self._SendRightPagesToNewNotebook, tab_index )
                ClientGUIMenus.AppendMenuItem( send_down_menu, 'pages to the right', 'Make a new page of pages and put all the pages to the right into it.', self._SendRightPagesToNewNotebook, tab_index + 1 )
                
            
            ClientGUIMenus.AppendMenu( menu, send_down_menu, 'send down to a new page of pages' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if not click_over_page_of_pages:
                
                ClientGUIMenus.AppendMenuItem( menu, 'refresh this page', 'Command this page to refresh.', page.RefreshQuery )
                
            elif click_over_page_of_pages and page.count() > 0:
                
                ClientGUIMenus.AppendMenuItem( menu, 'refresh all this page\'s pages', 'Command every page below this one to refresh.', page.RefreshAllPages )
                
            
        
        existing_session_names = CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
        
        if len( existing_session_names ) > 0 or click_over_page_of_pages:
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        if len( existing_session_names ) > 0:
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            for name in existing_session_names:
                
                ClientGUIMenus.AppendMenuItem( submenu, name, 'Load this session here.', self.AppendGUISessionFreshest, name )
                
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'append session' )
            
        
        if click_over_page_of_pages:
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            for name in existing_session_names:
                
                if name in ClientGUISession.RESERVED_SESSION_NAMES:
                    
                    continue
                    
                
                ClientGUIMenus.AppendMenuItem( submenu, name, 'Save this page of pages to the session.', CG.client_controller.gui.ProposeSaveGUISession, notebook = page, name = name )
                
            
            ClientGUIMenus.AppendMenuItem( submenu, 'create a new session', 'Save this page of pages to the session.', CG.client_controller.gui.ProposeSaveGUISession, notebook = page, suggested_name = page.GetName() )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'save this page of pages to a session' )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SortPagesByFileCount( self, order ):
        
        def key( page ):
            
            ( total_num_files, ( total_num_value, total_num_range ) ) = page.GetNumFileSummary()
            
            return ( total_num_files, total_num_range, total_num_value )
            
        
        ordered_pages = sorted( self.GetPages(), key = key, reverse = order == 'desc' )
        
        self._SortPagesSetPages( ordered_pages )
        
    
    def _SortPagesByFileSize( self, order ):
        
        def key( page ):
            
            total_file_size = page.GetTotalFileSize()
            
            return total_file_size
            
        
        ordered_pages = sorted( self.GetPages(), key = key, reverse = order == 'desc' )
        
        self._SortPagesSetPages( ordered_pages )
        
    
    def _SortPagesByName( self, order ):
        
        def file_count_secondary( page ):
            
            ( total_num_files, ( total_num_value, total_num_range ) ) = page.GetNumFileSummary()
            
            return ( total_num_files, total_num_range, total_num_value )
            
        
        ordered_pages = sorted( self.GetPages(), key = file_count_secondary, reverse = True )
        
        ordered_pages = sorted( ordered_pages, key = lambda page: page.GetName(), reverse = order == 'desc' )
        
        self._SortPagesSetPages( ordered_pages )
        
    
    def _SortPagesSetPages( self, ordered_pages ):
        
        selected_page = self.currentWidget()
        
        pages_to_names = {}
        
        for i in range( self.count() ):
            
            page = self.widget( 0 )
            
            name = self.tabText( 0 )
            
            pages_to_names[ page ] = name
            
            self.removeTab( 0 )
            
            self.UpdatePreviousPageIndex()
            
        
        for page in ordered_pages:
            
            name = pages_to_names[ page ]
            
            self.addTab( page, name )
            
            if page == selected_page:
                
                self.setCurrentIndex( self.count() - 1 )
                
            
        
    
    def _RefreshPageNamesAfterDnD( self, page_widget, source_widget ):
        
        if hasattr( page_widget, 'GetPageKey' ):
            
            CG.client_controller.pub( 'refresh_page_name', page_widget.GetPageKey() )
            
        
        source_notebook = GetParentNotebook( source_widget )
        
        if source_notebook is not None and hasattr( source_notebook, 'GetPageKey' ):
            
            CG.client_controller.pub( 'refresh_page_name', source_notebook.GetPageKey() )
            
        
    
    def _UpdateOptions( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'elide_page_tab_names' ):
            
            self.tabBar().setElideMode( QC.Qt.TextElideMode.ElideMiddle )
            
        else:
            
            self.tabBar().setElideMode( QC.Qt.TextElideMode.ElideNone )
            
        
        direction = CG.client_controller.new_options.GetInteger( 'notebook_tab_alignment' )
        
        self.setTabPosition( directions_for_notebook_tabs[ direction ] )
        
    
    def AppendGUISession( self, session: ClientGUISession.GUISessionContainer ):
        
        starting_index = self._GetDefaultPageInsertionIndex()
        
        forced_insertion_index = starting_index
        
        self.InsertSession( forced_insertion_index, session )
        
    
    def AppendGUISessionBackup( self, name, timestamp_ms, load_in_a_page_of_pages = True ):
        
        try:
            
            session = session = CG.client_controller.Read( 'gui_session', name, timestamp_ms )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session "{}" (ts {}), this error happened:'.format( name, timestamp_ms ) )
            HydrusData.ShowException( e )
            
            return
            
        
        if load_in_a_page_of_pages:
            
            destination = self.NewPagesNotebook( name = name, give_it_a_blank_page = False )
            
        else:
            
            destination = self
            
        
        destination.AppendGUISession( session )
        
    
    def AppendGUISessionFreshest( self, name, load_in_a_page_of_pages = True ):
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( 'loading session "{}"'.format( name ) + HC.UNICODE_ELLIPSIS )
        
        CG.client_controller.pub( 'message', job_status )
        
        # get that message showing before we do the work of loading session
        CG.client_controller.app.processEvents()
        
        try:
            
            session = CG.client_controller.Read( 'gui_session', name )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session "{}", this error happened:'.format( name ) )
            HydrusData.ShowException( e )
            
            return
            
        
        CG.client_controller.app.processEvents()
        
        if load_in_a_page_of_pages:
            
            destination = self.NewPagesNotebook( name = name, give_it_a_blank_page = False )
            
        else:
            
            destination = self
            
        
        CG.client_controller.app.processEvents()
        
        destination.AppendGUISession( session )
        
        self.freshSessionLoaded.emit( session )
        
        job_status.FinishAndDismiss()
        
    
    def AskIfAbleToClose( self, for_session_close = False ):
        
        user_was_asked = False
        
        reasons_and_pages = self.GetAbleToCloseData( for_session_close = for_session_close )
        
        if len( reasons_and_pages ) > 0:
            
            statement = ConvertReasonsAndPagesToStatement( reasons_and_pages )
            
            message = f'Close "{self.GetName()}"?'
            message += '\n' * 2
            message += statement
            
            user_was_asked = True
            
            # raises veto on no
            ShowReasonsAndPagesConfirmationDialog( self, reasons_and_pages, message )
            
        
        if not user_was_asked and CG.client_controller.new_options.GetBoolean( 'confirm_all_page_closes' ) and not for_session_close:
            
            message = f'Close "{self.GetName()}"?'
            
            num_pages_held = self.GetNumPagesHeld()
            
            if num_pages_held > 0:
                
                message += f'\n\nIt is holding {HydrusNumbers.ToHumanInt( num_pages_held )} pages.'
                
            else:
                
                message += '\n\nIt is empty.'
                
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Rejected:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def ChooseNewPage( self ):
        
        self._ChooseNewPage()
        
    
    def ChooseNewPageForDeepestNotebook( self ):
        
        current_page = self.currentWidget()
        
        if isinstance( current_page, PagesNotebook ):
            
            current_page.ChooseNewPageForDeepestNotebook()
            
        else:
            
            self._ChooseNewPage()
            
        
    
    def CleanBeforeClose( self ):
        
        for page in self._GetPages():
            
            page.CleanBeforeClose()
            
        
    
    def CleanBeforeDestroy( self ):
        
        for page in self._GetPages():
            
            page.CleanBeforeDestroy()
            
        
        CG.client_controller.ReleasePageKey( self._page_key )
        
    
    def CloseCurrentPage( self, polite = True ):
        
        selection = self.currentIndex()
        
        if selection != -1:
            
            page = self.widget( selection )
            
            if isinstance( page, PagesNotebook ):
                
                if page.GetNumPagesHeld() > 0:
                    
                    page.CloseCurrentPage( polite )
                    
                else:
                    
                    self._ClosePage( selection, polite = polite )
                    
                
            else:
                
                self._ClosePage( selection, polite = polite )
                
            
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() in ( QC.QEvent.Type.MouseButtonDblClick, QC.QEvent.Type.MouseButtonRelease ):
                
                screen_position = QG.QCursor.pos()
                
                if watched == self.tabBar():
                    
                    tab_pos = self.tabBar().mapFromGlobal( screen_position )
                    
                    over_a_tab = self.tabBar().tabAt( tab_pos ) != -1
                    over_tab_greyspace = not over_a_tab
                    
                else:
                    
                    over_a_tab = False
                    
                    widget_under_mouse = typing.cast( QW.QApplication, QW.QApplication.instance() ).widgetAt( screen_position )
                    
                    if widget_under_mouse is None:
                        
                        over_tab_greyspace = None
                        
                    else:
                        
                        if self.count() == 0 and isinstance( widget_under_mouse, QW.QStackedWidget ):
                            
                            over_tab_greyspace = True
                            
                        else:
                            
                            over_tab_greyspace = widget_under_mouse == self
                            
                        
                    
                
                if event.type() == QC.QEvent.Type.MouseButtonDblClick:
                    
                    event = typing.cast( QG.QMouseEvent, event )
                    
                    if event.button() == QC.Qt.MouseButton.LeftButton and over_tab_greyspace and not over_a_tab:
                        
                        self.EventNewPageFromScreenPosition( screen_position )
                        
                        return True
                        
                    
                elif event.type() == QC.QEvent.Type.MouseButtonRelease:
                    
                    event = typing.cast( QG.QMouseEvent, event )
                    
                    if event.button() == QC.Qt.MouseButton.RightButton and ( over_a_tab or over_tab_greyspace ):
                        
                        self.ShowMenuFromScreenPosition( screen_position )
                        
                        return True
                        
                    elif event.button() == QC.Qt.MouseButton.MiddleButton and over_tab_greyspace and not over_a_tab:
                        
                        self.EventNewPageFromScreenPosition( screen_position )
                        
                        return True
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def ShowMenuFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ShowMenu( position )
        
    
    def EventNewPageFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ChooseNewPage()
        
    
    def GetAbleToCloseData( self, for_session_close = False, pages = None ):
        
        reasons_to_pages = collections.defaultdict( list )
        
        if pages is None:
            
            pages_to_consult = self._GetMediaPages( False )
            
        else:
            
            pages_to_consult = pages
            
        
        for page in pages_to_consult:
            
            try:
                
                page.CheckAbleToClose( for_session_close = for_session_close )
                
            except HydrusExceptions.VetoException as e:
                
                reason = str( e )
                
                reasons_to_pages[ reason ].append( page )
                
            
        
        for ( reason, pages ) in reasons_to_pages.items():
            
            pages.sort( key = lambda p: HydrusText.HumanTextSortKey( p.GetName() ) )
            
        
        reasons_and_pages = sorted( reasons_to_pages.items(), key = lambda a: len( a[1] ) )
        
        return reasons_and_pages
        
    
    def GetAPIInfoDict( self, simple ):
        
        return {
            'name' : self.GetName(),
            'page_key' : self._page_key.hex(),
            'page_state' : self.GetPageState(),
            'page_type' : ClientGUIPagesCore.PAGE_TYPE_PAGE_OF_PAGES,
            'is_media_page' : False
        }
        
    
    def GetCurrentGUISession( self, name: str, only_changed_page_data: bool, about_to_save: bool ):
        
        ( page_container, hashes_to_page_data, skipped_unchanged_page_hashes ) = self.GetSerialisablePage( only_changed_page_data, about_to_save )
        
        session = ClientGUISession.GUISessionContainer( name, top_notebook_container = page_container, hashes_to_page_data = hashes_to_page_data, skipped_unchanged_page_hashes = skipped_unchanged_page_hashes )
        
        return session
        
    
    def GetCurrentMediaPage( self ):
        
        page = self.currentWidget()
        
        if isinstance( page, PagesNotebook ):
            
            return page.GetCurrentMediaPage()
            
        else:
            
            return page # this can be None
            
        
    
    def GetHashes( self ):
        
        hashes = []
        
        for page in self.GetMediaPages():
            
            hashes.extend( page.GetHashes() )
            
        
        hashes = HydrusLists.DedupeList( hashes )
        
        return hashes
        
    
    def GetMediaPages( self, only_my_level = False ):
        
        return self._GetMediaPages( only_my_level )
        
    
    def GetName( self ):
        
        return self._name
        
    
    def GetNameForMenu( self, elide = True ) -> str:
        
        name_for_menu = self.GetName()
        
        ( num_files, ( num_value, num_range ) ) = self.GetNumFileSummary()
        
        if num_files > 0:
            
            name_for_menu = '{} - {} files'.format( name_for_menu, HydrusNumbers.ToHumanInt( num_files ) )
            
        
        if num_value != num_range:
            
            name_for_menu = '{} - {}'.format( name_for_menu, HydrusNumbers.ValueRangeToPrettyString( num_value, num_range ) )
            
        
        return HydrusText.ElideText( name_for_menu, 32, elide_center = True ) if elide else name_for_menu
        
    
    def GetNumFileSummary( self ):
        
        total_num_files = 0
        total_num_value = 0
        total_num_range = 0
        
        for page in self._GetPages():
            
            ( num_files, ( num_value, num_range ) ) = page.GetNumFileSummary()
            
            total_num_files += num_files
            total_num_value += num_value
            total_num_range += num_range
            
        
        return ( total_num_files, ( total_num_value, total_num_range ) )
        
    
    def GetNumPagesHeld( self, only_my_level = False ):
        
        if only_my_level:
            
            return self.count()
            
        else:
            
            total = 0
            
            for page in self._GetPages():
                
                if isinstance( page, PagesNotebook ):
                    
                    total += page.GetNumPagesHeld( only_my_level = False )
                    
                else:
                    
                    total += 1
                    
                
            
            return total
            
        
    
    def GetOrMakeGalleryDownloaderPage( self, desired_page_name = None, desired_page_key = None, select_page = True ):
        
        potential_gallery_downloader_pages = [ page for page in self._GetMediaPages( False ) if page.IsGalleryDownloaderPage() ]
        
        if desired_page_key is not None and desired_page_key in ( page.GetPageKey() for page in potential_gallery_downloader_pages ):
            
            potential_gallery_downloader_pages = [ page for page in potential_gallery_downloader_pages if page.GetPageKey() == desired_page_key ]
            
        elif desired_page_name is not None:
            
            potential_gallery_downloader_pages = [ page for page in potential_gallery_downloader_pages if page.GetName() == desired_page_name ]
            
        
        if len( potential_gallery_downloader_pages ) > 0:
            
            # ok, we can use an existing one. should we use the current?
            
            current_media_page = self.GetCurrentMediaPage()
            
            if current_media_page is not None and current_media_page in potential_gallery_downloader_pages:
                
                return current_media_page
                
            else:
                
                return potential_gallery_downloader_pages[0]
                
            
        else:
            
            return self.NewPageImportGallery( page_name = desired_page_name, on_deepest_notebook = True, select_page = select_page )
            
        
    
    def GetOrMakeMultipleWatcherPage( self, desired_page_name = None, desired_page_key = None, select_page = True ):
        
        potential_watcher_pages = [ page for page in self._GetMediaPages( False ) if page.IsMultipleWatcherPage() ]
        
        if desired_page_key is not None and desired_page_key in ( page.GetPageKey() for page in potential_watcher_pages ):
            
            potential_watcher_pages = [ page for page in potential_watcher_pages if page.GetPageKey() == desired_page_key ]
            
        elif desired_page_name is not None:
            
            potential_watcher_pages = [ page for page in potential_watcher_pages if page.GetName() == desired_page_name ]
            
        
        if len( potential_watcher_pages ) > 0:
            
            # ok, we can use an existing one. should we use the current?
            
            current_media_page = self.GetCurrentMediaPage()
            
            if current_media_page is not None and current_media_page in potential_watcher_pages:
                
                return current_media_page
                
            else:
                
                return potential_watcher_pages[0]
                
            
        else:
            
            return self.NewPageImportMultipleWatcher( page_name = desired_page_name, on_deepest_notebook = True, select_page = select_page )
            
        
    
    def GetOrMakeURLImportPage( self, desired_page_name = None, desired_page_key = None, select_page = True, destination_location_context = None, destination_tag_import_options = None ):
        
        potential_url_import_pages = [ page for page in self._GetMediaPages( False ) if page.IsURLImportPage() ]
        
        if desired_page_key is not None and desired_page_key in ( page.GetPageKey() for page in potential_url_import_pages ):
            
            potential_url_import_pages = [ page for page in potential_url_import_pages if page.GetPageKey() == desired_page_key ]
            
        elif desired_page_name is not None:
            
            potential_url_import_pages = [ page for page in potential_url_import_pages if page.GetName() == desired_page_name ]
            
        
        if destination_location_context is not None:
            
            good_url_import_pages = []
            
            for url_import_page in potential_url_import_pages:
                
                urls_import = url_import_page.GetPageManager().GetVariable( 'urls_import' )
                
                file_import_options = urls_import.GetFileImportOptions()
                
                if not file_import_options.IsDefault() and file_import_options.GetDestinationLocationContext() == destination_location_context:
                    
                    good_url_import_pages.append( url_import_page )
                    
                
            
            potential_url_import_pages = good_url_import_pages
            
        
        if destination_tag_import_options is not None:
            
            good_url_import_pages = []
            
            for url_import_page in potential_url_import_pages:
                
                urls_import = url_import_page.GetPageManager().GetVariable( 'urls_import' )
                
                tag_import_options = urls_import.GetTagImportOptions()
                
                if tag_import_options.GetSerialisableTuple() == destination_tag_import_options.GetSerialisableTuple():
                    
                    good_url_import_pages.append( url_import_page )
                    
                
            
            potential_url_import_pages = good_url_import_pages
            
        
        if len( potential_url_import_pages ) > 0:
            
            # ok, we can use an existing one. should we use the current?
            
            current_media_page = self.GetCurrentMediaPage()
            
            if current_media_page is not None and current_media_page in potential_url_import_pages:
                
                return current_media_page
                
            else:
                
                return potential_url_import_pages[0]
                
            
        else:
            
            return self.NewPageImportURLs( page_name = desired_page_name, on_deepest_notebook = True, select_page = select_page, destination_location_context = destination_location_context, destination_tag_import_options = destination_tag_import_options )
            
        
    
    def GetPageFromPageKey( self, page_key ) -> "Page | PagesNotebook | None":
        
        if self._page_key == page_key:
            
            return self
            
        
        for page in self._GetPages():
            
            if page.GetPageKey() == page_key:
                
                return page
                
            
            if isinstance( page, PagesNotebook ):
                
                if page.HasPageKey( page_key ):
                    
                    return page.GetPageFromPageKey( page_key )
                    
                
            
        
        return None
        
    
    def GetPageKey( self ):
        
        return self._page_key
        
    
    def GetPageKeys( self ):
        
        page_keys = { self._page_key }
        
        for page in self._GetPages():
            
            page_keys.update( page.GetPageKeys() )
            
        
        return page_keys
        
    
    def GetPages( self ):
        
        return self._GetPages()
        
    
    def GetPageState( self ) -> int:
        
        return CC.PAGE_STATE_NORMAL
        
    
    def GetPrettyStatusForStatusBar( self ):
        
        ( num_files, ( num_value, num_range ) ) = self.GetNumFileSummary()
        
        num_string = HydrusNumbers.ToHumanInt( num_files )
        
        if num_range > 0 and num_value != num_range:
            
            num_string += ', ' + HydrusNumbers.ValueRangeToPrettyString( num_value, num_range )
            
        
        return HydrusNumbers.ToHumanInt( self.count() ) + ' pages, ' + num_string + ' files'
        
    
    def GetSerialisablePage( self, only_changed_page_data, about_to_save ):
        
        page_containers = []
        
        hashes_to_page_data = {}
        
        skipped_unchanged_page_hashes = set()
        
        for page in self._GetPages():
            
            ( sub_page_container, some_hashes_to_page_data, some_skipped_unchanged_page_hashes ) = page.GetSerialisablePage( only_changed_page_data, about_to_save )
            
            page_containers.append( sub_page_container )
            
            hashes_to_page_data.update( some_hashes_to_page_data )
            skipped_unchanged_page_hashes.update( some_skipped_unchanged_page_hashes )
            
        
        page_container = ClientGUISession.GUISessionContainerPageNotebook( self._name, page_containers = page_containers )
        
        return ( page_container, hashes_to_page_data, skipped_unchanged_page_hashes )
        
    
    def GetSessionAPIInfoDict( self, is_selected = True ):
        
        current_page = self.currentWidget()
        
        my_pages_list = []
        
        for page in self._GetPages():
            
            page_is_selected = is_selected and page == current_page
            
            page_info_dict = page.GetSessionAPIInfoDict( is_selected = page_is_selected )
            
            my_pages_list.append( page_info_dict )
            
        
        root = {}
        
        root[ 'name' ] = self.GetName()
        root[ 'page_key' ] = self._page_key.hex()
        root[ 'page_state' ] = self.GetPageState()
        root[ 'page_type' ] = ClientGUIPagesCore.PAGE_TYPE_PAGE_OF_PAGES
        root[ 'is_media_page' ] = False
        root[ 'selected' ] = is_selected
        root[ 'pages' ] = my_pages_list
        
        return root
        
    
    def GetTotalFileSize( self ):
        
        total_file_size = 0
        
        for page in self._GetPages():
            
            total_file_size += page.GetTotalFileSize()
            
        
        return total_file_size
        
    
    def GetTotalNumHashesAndSeeds( self ) -> tuple[ int, int ]:
        
        total_num_hashes = 0
        total_num_seeds = 0
        
        for page in self._GetPages():
            
            ( num_hashes, num_seeds ) = page.GetTotalNumHashesAndSeeds()
            
            total_num_hashes += num_hashes
            total_num_seeds += num_seeds
            
        
        return ( total_num_hashes, total_num_seeds )
        
    
    def GetTotalWeight( self ) -> int:
        
        total_weight = sum( ( page.GetTotalWeight() for page in self._GetPages() ) )
        
        return total_weight
        
    
    def HasMediaPageName( self, page_name, only_my_level = False ):
        
        media_pages = self._GetMediaPages( only_my_level )
        
        for page in media_pages:
            
            if page.GetName() == page_name:
                
                return True
                
            
        
        return False
        
    
    def HasPage( self, page ):
        
        return self.HasPageKey( page.GetPageKey() )
        
    
    def HasPageKey( self, page_key ):
        
        for page in self._GetPages():
            
            if page.GetPageKey() == page_key:
                
                return True
                
            elif isinstance( page, PagesNotebook ) and page.HasPageKey( page_key ):
                
                return True
                
            
        
        return False
        
    
    def HasMultipleWatcherPage( self ):
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                if page.HasMultipleWatcherPage():
                    
                    return True
                    
                
            else:
                
                if page.IsMultipleWatcherPage():
                    
                    return True
                    
                
            
        
        return False
        
    
    def HasURLImportPage( self ):
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                if page.HasURLImportPage():
                    
                    return True
                    
                
            else:
                
                if page.IsURLImportPage():
                    
                    return True
                    
                
            
        
        return False
        
    
    def InsertSession( self, forced_insertion_index: int, session: ClientGUISession.GUISessionContainer, session_is_clean = True ):
        
        # get the top notebook, then for every page in there...
        
        top_notebook_container = session.GetTopNotebook()
        
        page_containers = top_notebook_container.GetPageContainers()
        select_first_page = True
        
        self.InsertSessionNotebookPages( forced_insertion_index, session, page_containers, select_first_page, session_is_clean = session_is_clean )
        
    
    def InsertSessionNotebook( self, forced_insertion_index: int, session: ClientGUISession.GUISessionContainer, notebook_page_container: ClientGUISession.GUISessionContainerPageNotebook, select_first_page: bool, session_is_clean = True ):
        
        name = notebook_page_container.GetName()
        
        page = self.NewPagesNotebook( name, forced_insertion_index = forced_insertion_index, give_it_a_blank_page = False, select_page = select_first_page )
        
        page_containers = notebook_page_container.GetPageContainers()
        
        page.InsertSessionNotebookPages( 0, session, page_containers, select_first_page, session_is_clean = session_is_clean )
        
    
    def InsertSessionNotebookPages( self, forced_insertion_index: int, session: ClientGUISession.GUISessionContainer, page_containers: collections.abc.Collection[ ClientGUISession.GUISessionContainerPage ], select_first_page: bool, session_is_clean = True ):
        
        done_first_page = False
        
        for page_container in page_containers:
            
            select_page = select_first_page and not done_first_page
            
            try:
                
                if isinstance( page_container, ClientGUISession.GUISessionContainerPageNotebook ):
                    
                    self.InsertSessionNotebook( forced_insertion_index, session, page_container, select_page, session_is_clean = session_is_clean )
                    
                else:
                    
                    result = self.InsertSessionPage( forced_insertion_index, session, page_container, select_page, session_is_clean = session_is_clean )
                    
                    if result is None:
                        
                        continue
                        
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            forced_insertion_index += 1
            
            done_first_page = True
            
        
    
    def InsertSessionPage( self, forced_insertion_index: int, session: ClientGUISession.GUISessionContainer, page_container: ClientGUISession.GUISessionContainerPageSingle, select_page: bool, session_is_clean = True ):
        
        try:
            
            page_data_hash = page_container.GetPageDataHash()
            
            page_data = session.GetPageData( page_data_hash )
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.ShowText( 'The page with name "{}" and hash "{}" failed to load because its data was missing!'.format( page_container.GetName(), page_data_hash.hex() ) )
            
            return None
            
        
        page_manager = page_data.GetPageManager()
        initial_hashes = page_data.GetHashes()
        
        page = self.NewPage( page_manager, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index, select_page = select_page )
        
        if session_is_clean and page is not None:
            
            page.SetPageContainerClean( page_container )
            
        
        return page
        
    
    def IsMultipleWatcherPage( self ):
        
        return False
        
    
    def IsImporter( self ):
        
        return False
        
    
    def IsURLImportPage( self ):
        
        return False
        
    
    def LoadGUISession( self, name ):
        
        if self.count() > 0:
            
            message = 'Close the current pages and load session "{}"?'.format( name )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Clear and load session?' )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
            try:
                
                self.AskIfAbleToClose( for_session_close = True )
                
            except HydrusExceptions.VetoException:
                
                return
                
            
            self._CloseAllPages( polite = False, delete_pages = True )
            
            CG.client_controller.CallLaterQtSafe( self, 1.0, 'append session', self.AppendGUISessionFreshest, name, load_in_a_page_of_pages = False )
            
        else:
            
            self.AppendGUISessionFreshest( name, load_in_a_page_of_pages = False )
            
        
    
    def MediaDragAndDropDropped( self, source_page_key, hashes ):
        
        source_page = self.GetPageFromPageKey( source_page_key )
        
        if source_page is None:
            
            return
            
        
        source_page_manager = source_page.GetPageManager()
        
        location_context = source_page_manager.GetLocationContext()
        
        screen_position = QG.QCursor.pos()
        
        dest_notebook = self._GetNotebookFromScreenPosition( screen_position )
        
        tab_index = ClientGUIFunctions.NotebookScreenToHitTest( dest_notebook, screen_position )
        
        do_add = True
        # do chase - if we need to chase to an existing dest page on which we dropped files
        # do return - if we need to return to source page if we created a new one
        
        current_widget = dest_notebook.currentWidget()
        
        if tab_index == -1 and current_widget is not None and not isinstance( current_widget, PagesNotebook ) and current_widget.rect().contains( current_widget.mapFromGlobal( screen_position ) ):
            
            dest_page = current_widget
            
        elif tab_index == -1:
            
            dest_page = dest_notebook.NewPageQuery( location_context, initial_hashes = hashes )
            
            do_add = False
            
        else:
            
            dest_page = dest_notebook.widget( tab_index )
            
            if isinstance( dest_page, PagesNotebook ):
                
                result = dest_page.GetCurrentMediaPage()
                
                if result is None:
                    
                    dest_page = dest_page.NewPageQuery( location_context, initial_hashes = hashes )
                    
                    do_add = False
                    
                else:
                    
                    dest_page = result
                    
                
            
        
        if dest_page is None:
            
            return # we somehow dropped onto a new notebook that has no pages
            
        
        if isinstance( dest_page, PagesNotebook ):
            
            return # dropped on the edge of some notebook somehow
            
        
        if dest_page.GetPageKey() == source_page_key:
            
            return # we dropped onto the same page we picked up on
            
        
        if do_add:
            
            media_results = CG.client_controller.Read( 'media_results', hashes, sorted = True )
            
            dest_page.AddMediaResults( media_results )
            
        else:
            
            self.ShowPage( source_page )
            
        
        # queryKBM here for instant check, not waiting for event processing to catch up u wot mate
        ctrl_down = QW.QApplication.queryKeyboardModifiers() & QC.Qt.KeyboardModifier.ControlModifier
        
        if not ctrl_down:
            
            source_page.GetMediaResultsPanel().RemoveMedia( hashes )
            
        
    
    def MoveSelection( self, delta, just_do_test = False ):
        
        if self.count() <= 1: # 1 is a no-op
            
            return False
            
        
        current_page = self.currentWidget()
        
        i_have_done_a_recent_move = not HydrusTime.TimeHasPassed( self._time_of_last_move_selection_event + 3 )
        
        if isinstance( current_page, PagesNotebook ) and not i_have_done_a_recent_move:
            
            if current_page.MoveSelection( delta, just_do_test = True ):
                
                return current_page.MoveSelection( delta, just_do_test = just_do_test )
                
            
        
        new_index = self.currentIndex() + delta
        
        if 0 <= new_index <= self.count() - 1:
            
            if not just_do_test:
                
                self.setCurrentIndex( new_index )
                
                self._time_of_last_move_selection_event = HydrusTime.GetNow()
                
            
            return True
            
        
        return False
        
    
    def MoveSelectionEnd( self, delta, just_do_test = False ):
        
        if self.count() <= 1: # 1 is a no-op
            
            return False
            
        
        current_page = self.currentWidget()
        
        i_have_done_a_recent_move = not HydrusTime.TimeHasPassed( self._time_of_last_move_selection_event + 3 )
        
        if isinstance( current_page, PagesNotebook ) and not i_have_done_a_recent_move:
            
            if current_page.MoveSelectionEnd( delta, just_do_test = True ):
                
                return current_page.MoveSelectionEnd( delta, just_do_test = just_do_test )
                
            
        
        if delta < 0:
            
            new_index = 0
            
        else:
            
            new_index = self.count() - 1
            
        
        if not just_do_test:
            
            self.setCurrentIndex( new_index )
            
            self._time_of_last_move_selection_event = HydrusTime.GetNow()
            
        
        return True
        
    
    def NewPage( self, page_manager, initial_hashes = None, forced_insertion_index = None, on_deepest_notebook = False, select_page = True ) -> Page:
        
        current_page = self.currentWidget()
        
        if on_deepest_notebook and isinstance( current_page, PagesNotebook ):
            
            return current_page.NewPage( page_manager, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index, on_deepest_notebook = on_deepest_notebook )
            
        
        # the 'too many pages open' thing used to be here
        
        CG.client_controller.ResetIdleTimer()
        CG.client_controller.ResetPageChangeTimer()
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        page = Page( self, page_manager, initial_hashes )
        
        if forced_insertion_index is None:
            
            if self._next_new_page_index is None:
                
                insertion_index = self._GetDefaultPageInsertionIndex()
                
            else:
                
                insertion_index = self._next_new_page_index
                
                self._next_new_page_index = None
                
            
        else:
            
            insertion_index = forced_insertion_index
            
        
        page_name = page.GetName()
        
        # in some unusual circumstances, this gets out of whack
        insertion_index = min( insertion_index, self.count() )
        
        if CG.client_controller.new_options.GetBoolean( 'force_hide_page_signal_on_new_page' ):
            
            current_gui_page = CG.client_controller.gui.GetCurrentPage()
            
            if current_gui_page is not None:
                
                current_gui_page.PageHidden()
                
            
        
        self.insertTab( insertion_index, page, page_name )
        
        if select_page:
            
            self.setCurrentIndex( insertion_index )
            
        
        CG.client_controller.pub( 'refresh_page_name', page.GetPageKey() )
        CG.client_controller.pub( 'notify_new_pages' )
        
        page.Start()
        
        if select_page:
            
            page.SetSearchFocus()
            
            # this is here for now due to the pagechooser having a double-layer dialog on a booru choice, which messes up some focus inheritance
            
            CG.client_controller.CallLaterQtSafe( self, 0.5, 'set page focus', page.SetSearchFocus )
            
        
        return page
        
    
    def NewPageDuplicateFilter(
        self,
        location_context = None,
        initial_predicates = None,
        page_name = None,
        select_page = True,
        on_deepest_notebook = False
    ):
        
        page_manager = ClientGUIPageManager.CreatePageManagerDuplicateFilter( location_context = location_context, initial_predicates = initial_predicates, page_name = page_name )
        
        return self.NewPage( page_manager, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPageImportGallery( self, page_name = None, on_deepest_notebook = False, select_page = True ):
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportGallery( page_name = page_name )
        
        return self.NewPage( page_manager, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPageImportSimpleDownloader( self, on_deepest_notebook = False ):
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportSimpleDownloader()
        
        return self.NewPage( page_manager, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportMultipleWatcher( self, page_name = None, url = None, on_deepest_notebook = False, select_page = True ):
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportMultipleWatcher( page_name = page_name, url = url )
        
        return self.NewPage( page_manager, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPageImportURLs( self, page_name = None, on_deepest_notebook = False, select_page = True, destination_location_context = None, destination_tag_import_options = None ):
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportURLs( page_name = page_name, destination_location_context = destination_location_context, destination_tag_import_options = destination_tag_import_options )
        
        return self.NewPage( page_manager, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPagePetitions( self, service_key, on_deepest_notebook = False ):
        
        page_manager = ClientGUIPageManager.CreatePageManagerPetitions( service_key )
        
        return self.NewPage( page_manager, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageQuery(
        self,
        location_context: ClientLocation.LocationContext,
        initial_hashes = None,
        initial_predicates = None,
        initial_sort = None,
        initial_collect = None,
        page_name = None,
        on_deepest_notebook = False,
        do_sort = False,
        forced_insertion_index = None,
        select_page = True
    ):
        
        if initial_predicates is None:
            
            initial_predicates = []
            
        
        new_options = CG.client_controller.new_options
        
        tag_service_key = new_options.GetKey( 'default_tag_service_search_page' )
        
        if not CG.client_controller.services_manager.ServiceExists( tag_service_key ):
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        if location_context.IsAllKnownFiles() and tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
            
        
        tag_context = ClientSearchTagContext.TagContext( service_key = tag_service_key )
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = initial_predicates )
        
        return self.NewPageQueryFileSearchContext(
            file_search_context,
            initial_hashes = initial_hashes,
            initial_sort = initial_sort,
            initial_collect = initial_collect,
            page_name = page_name,
            on_deepest_notebook = on_deepest_notebook,
            do_sort = do_sort,
            forced_insertion_index = forced_insertion_index,
            select_page = select_page
        )
        
    
    def NewPageQueryFileSearchContext(
        self,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        initial_hashes = None,
        initial_sort = None,
        initial_collect = None,
        page_name = None,
        on_deepest_notebook = False,
        do_sort = False,
        forced_insertion_index = None,
        select_page = True
    ):
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        if page_name is None:
            
            page_name = 'files'
            
        
        start_system_hash_locked = False
        
        if len( initial_hashes ) > 0:
            
            if len( file_search_context.GetPredicates() ) == 0:
                
                start_system_hash_locked = True
                
                predicates = [ ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, value = ( tuple( initial_hashes ), 'sha256' ) ) ]
                
                file_search_context.SetPredicates( predicates )
                
            
            # this is important, it is consulted deeper to determine query refresh on start!
            file_search_context.SetComplete()
            
        
        page_manager = ClientGUIPageManager.CreatePageManagerQuery( page_name, file_search_context, start_system_hash_locked = start_system_hash_locked )
        
        if initial_sort is not None:
            
            page_manager.SetVariable( 'media_sort', initial_sort )
            
        
        if initial_collect is not None:
            
            page_manager.SetVariable( 'media_collect', initial_collect )
            
        
        page = self.NewPage( page_manager, initial_hashes = initial_hashes, on_deepest_notebook = on_deepest_notebook, forced_insertion_index = forced_insertion_index, select_page = select_page )
        
        # don't need to do 'Do a Collect if needed', since SwapPanel lower down does it for us
        
        if do_sort:
            
            media_sort = page.GetSort()
            
            page.GetMediaResultsPanel().Sort( media_sort )
            
        
        return page
        
    
    def NewPagesNotebook( self, name = 'pages', forced_insertion_index = None, on_deepest_notebook = False, give_it_a_blank_page = True, select_page = True ):
        
        current_page = self.currentWidget()
        
        if on_deepest_notebook and isinstance( current_page, PagesNotebook ):
            
            return current_page.NewPagesNotebook( name = name, forced_insertion_index = forced_insertion_index, on_deepest_notebook = on_deepest_notebook, give_it_a_blank_page = give_it_a_blank_page )
            
        
        CG.client_controller.ResetIdleTimer()
        CG.client_controller.ResetPageChangeTimer()
        
        page = PagesNotebook( self, name )
        
        if forced_insertion_index is None:
            
            if self._next_new_page_index is None:
                
                insertion_index = self._GetDefaultPageInsertionIndex()
                
            else:
                
                insertion_index = self._next_new_page_index
                
                self._next_new_page_index = None
                
            
        else:
            
            insertion_index = forced_insertion_index
            
        
        page_name = page.GetName()
        
        self.insertTab( insertion_index, page, page_name )
        
        if select_page:
            
            self.setCurrentIndex( insertion_index )
            
        
        CG.client_controller.pub( 'refresh_page_name', page.GetPageKey() )
        
        if give_it_a_blank_page:
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            page.NewPageQuery( default_location_context )
            
        
        return page
        
    
    def NotifyUnclosed( self ):
        
        for page in self._GetPages():
            
            page.NotifyUnclosed()
            
        
    
    def TryToUncloseThisPage( self, page ):
        
        page_key = page.GetPageKey()
        
        for ( index, closed_page_key ) in self._closed_pages:
            
            if page_key == closed_page_key:
                
                page.show()
                
                insert_index = min( index, self.count() )
                
                name = page.GetName()
                
                self.insertTab( insert_index, page, name )
                self.setCurrentIndex( insert_index )
                
                CG.client_controller.pub( 'refresh_page_name', page.GetPageKey() )
                
                page.NotifyUnclosed()
                
                self._closed_pages.remove( ( index, closed_page_key ) )
                
                break
                
            
        
    
    def PageHidden( self ):
        
        result: Page | PagesNotebook = self.currentWidget()
        
        if result is not None:
            
            result.PageHidden()
            
        
    
    def pageJustChanged( self, index ):
        
        old_selection = self._previous_page_index
        selection = index
        
        if old_selection != -1 and old_selection < self.count():
            
            old_page: Page | PagesNotebook = self.widget( old_selection )
            
            old_page.PageHidden()
            
        
        if selection != -1:
            
            new_page: Page | PagesNotebook = self.widget( selection )
            
            new_page.PageShown()
            
        
        CG.client_controller.gui.RefreshStatusBar()
        CG.client_controller.gui.NotifyPageJustChanged()
        
        self._previous_page_index = index
        
        CG.client_controller.pub( 'notify_page_change' )
        
    
    def PageShown( self ):
        
        result: Page | PagesNotebook = self.currentWidget()
        
        if result is not None:
            
            result.PageShown()
            
        
    
    def PresentImportedFilesToPage( self, hashes, page_name ):
        
        hashes = list( hashes )
        
        page = self._GetPageFromName( page_name, only_media_pages = True )
        
        if page is None:
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
            
            page = self.NewPageQuery( location_context, initial_hashes = hashes, page_name = page_name, on_deepest_notebook = True, select_page = False )
            
        else:
            
            def work_callable():
                
                media_results = CG.client_controller.Read( 'media_results', hashes, sorted = True )
                
                return media_results
                
            
            def publish_callable( media_results ):
                
                page.AddMediaResults( media_results )
                
            
            job = ClientGUIAsync.AsyncQtJob( page, work_callable, publish_callable )
            
            job.start()
            
        
        return page
        
    
    def RefreshAllPages( self ):
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                page.RefreshAllPages()
                
            else:
                
                page.RefreshQuery()
                
            
        
    
    def RefreshPageName( self, page_key = None ):
        
        if page_key is None:
            
            for index in range( self.count() ):
                
                self._RefreshPageName( index )
                
            
        else:
            
            for ( index, page ) in enumerate( self._GetPages() ):
                
                do_it = False
                
                if page.GetPageKey() == page_key:
                    
                    do_it = True
                    
                elif isinstance( page, PagesNotebook ) and page.HasPageKey( page_key ):
                    
                    do_it = True
                    
                
                if do_it:
                    
                    self._RefreshPageName( index )
                    
                    break
                    
                
            
        
    
    def SetName( self, name ):
        
        self._name = name
        
    
    def ShowPage( self, showee ):
        
        for ( i, page ) in enumerate( self._GetPages() ):
            
            if isinstance( page, PagesNotebook ) and page.HasPage( showee ):
                
                self.setCurrentIndex( i )
                
                page.ShowPage( showee )
                
                break
                
            elif page == showee:
                
                self.setCurrentIndex( i )
                
                break
                
            
        
    
    def UpdatePreviousPageIndex( self ):
        
        self._previous_page_index = self.currentIndex()
        
    
    def REPEATINGPageUpdate( self ):
        
        pass
        
    

class PagesHistory( collections.OrderedDict ):
    
    def __init__( self ):
        
        collections.OrderedDict.__init__( self )
        
    
    def AddPage( self, page: Page ):
        
        page_key = page.GetPageKey()
        page_name = page.GetNameForMenu( elide = False )
        
        if page_key in self:
            
            self.pop( page_key )
            
        
        self[ page_key ] = page_name
        
    
    def CleanPages( self, existing_page_keys: set[ bytes ] ):
        
        for page_key in set( self.keys() ).difference( existing_page_keys ):
            
            self.pop( page_key )
            
        
    
    def GetHistory( self ):
        
        return list( self.items() )
        
    
