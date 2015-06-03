import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIManagement
import ClientGUIMedia
import ClientGUICanvas
import ClientDownloading
import HydrusData
import HydrusThreading
import inspect
import os
import sys
import time
import traceback
import wx
import ClientData
import HydrusGlobals

class PageBase( object ):
    
    _is_storable = False
    
    def __init__( self, starting_from_session = False ):
        
        self._starting_from_session = starting_from_session
        self._page_key = os.urandom( 32 )
        
        self._management_panel = None
        self._media_panel = None
        
        self._pretty_status = ''
        
        HydrusGlobals.pubsub.sub( self, 'SetPrettyStatus', 'new_page_status' )
        
    
    def _InitManagementPanel( self ): pass
    
    def _InitMediaPanel( self ): pass
    
    def CleanBeforeDestroy( self ): pass
    
    def GetPrettyStatus( self ): return self._pretty_status
    
    def GetSashPositions( self ):
        
        x = HC.options[ 'hpos' ]
        
        y = HC.options[ 'vpos' ]
        
        return ( x, y )
        
    
    def IsStorable( self ): return self._is_storable
    
    def PageHidden( self ): HydrusGlobals.pubsub.pub( 'page_hidden', self._page_key )
    
    def PageShown( self ): HydrusGlobals.pubsub.pub( 'page_shown', self._page_key )
    
    def Pause( self ):
        
        HydrusGlobals.pubsub.pub( 'pause', self._page_key )
        
        HydrusGlobals.pubsub.pub( 'set_focus', self._page_key, None )
        
    
    def SetPrettyStatus( self, page_key, status ):
        
        if page_key == self._page_key:
            
            self._pretty_status = status
            
            HydrusGlobals.pubsub.pub( 'refresh_status' )
            
        
    
    def RefreshQuery( self ): HydrusGlobals.pubsub.pub( 'refresh_query', self._page_key )
    
    def SetMediaFocus( self ): pass
    
    def SetSearchFocus( self ): HydrusGlobals.pubsub.pub( 'set_search_focus', self._page_key )
    
    def SetSynchronisedWait( self ): HydrusGlobals.pubsub.pub( 'synchronised_wait_switch', self._page_key )
    
    def ShowHideSplit( self ): pass
    
    def TestAbleToClose( self ): pass
    
    def Resume( self ):
        
        HydrusGlobals.pubsub.pub( 'resume', self._page_key )
        
    '''
class PageMessages( PageBase, wx.SplitterWindow ):
    
    def __init__( self, parent, identity, starting_from_session = False ):
        
        wx.SplitterWindow.__init__( self, parent )
        PageBase.__init__( self, starting_from_session = starting_from_session )
        
        self.SetMinimumPaneSize( 120 )
        self.SetSashGravity( 0.0 )
        
        self._identity = identity
        
        self._search_preview_split = wx.SplitterWindow( self, style=wx.SP_NOBORDER )
        
        self._search_preview_split.SetMinimumPaneSize( 180 )
        self._search_preview_split.SetSashGravity( 0.5 )
        
        self._search_preview_split.Bind( wx.EVT_SPLITTER_DCLICK, self.EventPreviewUnsplit )
        
        self._InitManagementPanel()
        self._preview_panel = ClientGUICanvas.CanvasPanel( self._search_preview_split, self._page_key, CC.LOCAL_FILE_SERVICE_KEY )
        self._InitMessagesPanel()
        
        self.SplitVertically( self._search_preview_split, self._messages_panel, HC.options[ 'hpos' ] )
        wx.CallAfter( self._search_preview_split.SplitHorizontally, self._management_panel, self._preview_panel, HC.options[ 'vpos' ] )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelMessages( self._search_preview_split, self._page_key, self._identity, starting_from_session = self._starting_from_session )
    
    def _InitMessagesPanel( self ): self._messages_panel = ClientGUIMessages.ConversationSplitter( self, self._page_key, self._identity )
    
    def EventPreviewUnsplit( self, event ): self._search_preview_split.Unsplit( self._preview_panel )
    
    def GetSashPositions( self ):
        
        if self.IsSplit(): x = self.GetSashPosition()
        else: x = HC.options[ 'hpos' ]
        
        if self._search_preview_split.IsSplit(): y = -1 * self._preview_panel.GetSize()[1]
        else: y = HC.options[ 'vpos' ]
        
        return ( x, y )
        
    
    def ShowHideSplit( self ):
        
        if self._search_preview_split.IsSplit(): self._search_preview_split.Unsplit( self._preview_panel )
        else: self._search_preview_split.SplitHorizontally( self._management_panel, self._preview_panel, HC.options[ 'vpos' ] )
        
    
    def TestAbleToClose( self ): self._management_panel.TestAbleToClose()
    '''
class PageWithMedia( PageBase, wx.SplitterWindow ):
    
    def __init__( self, parent, file_service_key = CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = None, initial_media_results = None, starting_from_session = False ):
        
        if initial_hashes is None: initial_hashes = []
        if initial_media_results is None: initial_media_results = []
        
        wx.SplitterWindow.__init__( self, parent )
        PageBase.__init__( self, starting_from_session = starting_from_session )
        
        if len( initial_hashes ) > 0: initial_media_results = wx.GetApp().Read( 'media_results', file_service_key, initial_hashes )
        
        self._file_service_key = file_service_key
        self._initial_media_results = initial_media_results
        
        self.SetMinimumPaneSize( 120 )
        self.SetSashGravity( 0.0 )
        
        self.Bind( wx.EVT_SPLITTER_DCLICK, self.EventUnsplit )
        
        self._search_preview_split = wx.SplitterWindow( self, style=wx.SP_NOBORDER )
        
        self._search_preview_split.SetMinimumPaneSize( 180 )
        self._search_preview_split.SetSashGravity( 1.0 )
        
        self._search_preview_split.Bind( wx.EVT_SPLITTER_DCLICK, self.EventPreviewUnsplit )
        
        self._InitManagementPanel()
        self._preview_panel = ClientGUICanvas.CanvasPanel( self._search_preview_split, self._page_key, self._file_service_key )
        self._InitMediaPanel()
        
        self.SplitVertically( self._search_preview_split, self._media_panel, HC.options[ 'hpos' ] )
        wx.CallAfter( self._search_preview_split.SplitHorizontally, self._management_panel, self._preview_panel, HC.options[ 'vpos' ] )
        
        HydrusGlobals.pubsub.sub( self, 'SwapMediaPanel', 'swap_media_panel' )
        
    
    def CleanBeforeDestroy( self ): self._management_panel.CleanBeforeDestroy()
    
    def EventPreviewUnsplit( self, event ): self._search_preview_split.Unsplit( self._preview_panel )
    
    def EventUnsplit( self, event ): self.Unsplit( self._search_preview_split )
    
    # used by autocomplete
    def GetMedia( self ): return self._media_panel.GetSortedMedia()
    
    def GetSashPositions( self ):
        
        if self.IsSplit(): x = self.GetSashPosition()
        else: x = HC.options[ 'hpos' ]
        
        if self._search_preview_split.IsSplit(): y = -1 * self._preview_panel.GetSize()[1]
        else: y = HC.options[ 'vpos' ]
        
        return ( x, y )
        
    
    def ShowHideSplit( self ):
        
        if self.IsSplit():
            
            self.Unsplit( self._search_preview_split )
            
        else:
            
            self.SplitVertically( self._search_preview_split, self._media_panel, HC.options[ 'hpos' ] )
            
            self._search_preview_split.SplitHorizontally( self._management_panel, self._preview_panel, HC.options[ 'vpos' ] )
            
        
    
    def SetMediaFocus( self ): self._media_panel.SetFocus()
    
    def SwapMediaPanel( self, page_key, new_panel ):
        
        if page_key == self._page_key:
            
            self._preview_panel.SetMedia( None )
            
            self.ReplaceWindow( self._media_panel, new_panel )
            
            self._media_panel.Hide()
            
            # If this is a CallAfter, OS X segfaults on refresh jej
            wx.CallLater( 500, self._media_panel.Destroy )
            
            self._media_panel = new_panel
            
        
    
    def TestAbleToClose( self ): self._management_panel.TestAbleToClose()
    
class PageImport( PageWithMedia ):
    
    _is_storable = True
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, self._file_service_key, self._initial_media_results )
    
    def GetSessionArgs( self ):
        
        hashes = [ media.GetHash() for media in self._media_panel.GetFlatMedia() ]
        
        args = tuple()
        kwargs = { 'initial_hashes' : hashes }
        
        return ( args, kwargs )
        
    
class PageImportGallery( PageImport ):
    
    def __init__( self, parent, site_type, gallery_type, initial_hashes = None, starting_from_session = False ):
        
        if initial_hashes is None: initial_hashes = []
        
        self._site_type = site_type
        self._gallery_type = gallery_type
        
        PageImport.__init__( self, parent, initial_hashes = initial_hashes, starting_from_session = starting_from_session )
        
    
    def _InitManagementPanel( self ):
        
        self._management_panel = ClientGUIManagement.ManagementPanelImportsGallery( self._search_preview_split, self, self._page_key, self._site_type, self._gallery_type, starting_from_session = self._starting_from_session )
        
    
    def GetSessionArgs( self ):
        
        hashes = [ media.GetHash() for media in self._media_panel.GetFlatMedia() ]
        
        args = ( self._site_type, self._gallery_type )
        kwargs = { 'initial_hashes' : hashes }
        
        return ( args, kwargs )
        
    
class PageImportHDD( PageImport ):
    
    def __init__( self, parent, paths_info, initial_hashes = None, advanced_import_options = None, paths_to_tags = None, delete_after_success = False, starting_from_session = False ):
        
        if advanced_import_options is None: advanced_import_options = {}
        if paths_to_tags is None: paths_to_tags = {}
        
        self._paths_info = paths_info
        self._advanced_import_options = advanced_import_options
        self._paths_to_tags = paths_to_tags
        self._delete_after_success = delete_after_success
        
        PageImport.__init__( self, parent, initial_hashes = initial_hashes, starting_from_session = starting_from_session )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportHDD( self._search_preview_split, self, self._page_key, self._paths_info, self._advanced_import_options, self._paths_to_tags, self._delete_after_success, starting_from_session = self._starting_from_session )
    
    def GetSessionArgs( self ):
        
        hashes = [ media.GetHash() for media in self._media_panel.GetFlatMedia() ]
        
        args = ( [], )
        kwargs = { 'initial_hashes' : hashes }
        
        return ( args, kwargs )
        
    
class PageImportThreadWatcher( PageImport ):
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportThreadWatcher( self._search_preview_split, self, self._page_key, starting_from_session = self._starting_from_session )
    
class PageImportURL( PageImport ):
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportsURL( self._search_preview_split, self, self._page_key, starting_from_session = self._starting_from_session )
    
class PagePetitions( PageWithMedia ):
    
    def __init__( self, parent, petition_service_key, starting_from_session = False ):
        
        self._petition_service_key = petition_service_key
        
        petition_service = wx.GetApp().GetManager( 'services' ).GetService( petition_service_key )
        
        petition_service_type = petition_service.GetServiceType()
        
        if petition_service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ): self._file_service_key = self._petition_service_key
        else: self._file_service_key = CC.COMBINED_FILE_SERVICE_KEY
        
        PageWithMedia.__init__( self, parent, self._file_service_key, starting_from_session = starting_from_session )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelPetitions( self._search_preview_split, self, self._page_key, self._file_service_key, self._petition_service_key, starting_from_session = self._starting_from_session )
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelNoQuery( self, self._page_key, self._file_service_key )
    
class PageQuery( PageWithMedia ):
    
    _is_storable = True
    
    def __init__( self, parent, file_service_key, initial_hashes = None, initial_media_results = None, initial_predicates = None, starting_from_session = False ):
        
        if initial_hashes is None: initial_hashes = []
        if initial_media_results is None: initial_media_results = []
        if initial_predicates is None: initial_predicates = []
        
        self._initial_predicates = initial_predicates
        
        PageWithMedia.__init__( self, parent, file_service_key, initial_hashes = initial_hashes, initial_media_results = initial_media_results, starting_from_session = starting_from_session )
        
    
    def _InitManagementPanel( self ):
        
        show_search = len( self._initial_predicates ) > 0 or len( self._initial_media_results ) == 0
        
        self._management_panel = ClientGUIManagement.ManagementPanelQuery( self._search_preview_split, self, self._page_key, self._file_service_key, show_search = show_search, initial_predicates = self._initial_predicates, starting_from_session = self._starting_from_session )
        
    
    def _InitMediaPanel( self ):
        
        if len( self._initial_media_results ) == 0: self._media_panel = ClientGUIMedia.MediaPanelNoQuery( self, self._page_key, self._file_service_key )
        else:
            
            refreshable = len( self._initial_predicates ) > 0 or len( self._initial_media_results ) == 0
            
            self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, self._file_service_key, self._initial_media_results, refreshable = refreshable )
            
        
    
    def GetSessionArgs( self ):
        
        hashes = [ media.GetHash() for media in self._media_panel.GetFlatMedia() ]
        predicates = self._management_panel.GetPredicates()
        
        args = ( self._file_service_key, )
        kwargs = { 'initial_hashes' : hashes, 'initial_predicates' : predicates }
        
        return ( args, kwargs )
        
    
class PageThreadDumper( PageWithMedia ):
    
    def __init__( self, parent, imageboard, hashes, starting_from_session = False ):
        
        self._imageboard = imageboard
        
        media_results = wx.GetApp().Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, hashes )
        
        hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
        
        self._media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
        
        self._media_results = filter( self._imageboard.IsOkToPost, self._media_results )
        
        PageWithMedia.__init__( self, parent, CC.LOCAL_FILE_SERVICE_KEY, starting_from_session = starting_from_session )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelDumper( self._search_preview_split, self, self._page_key, self._imageboard, self._media_results, starting_from_session = self._starting_from_session )
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, self._media_results )
    
class_to_text = {}
text_to_class = {}

current_module = sys.modules[ __name__ ]

for ( name, c ) in inspect.getmembers( current_module ):
    
    if inspect.isclass( c ):
        
        class_to_text[ c ] = name
        text_to_class[ name ] = c
        
    