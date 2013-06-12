import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIManagement
import ClientGUIMedia
import ClientGUIMessages
import ClientGUICanvas
import os
import time
import traceback
import wx

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()

FLAGS_BUTTON_SIZERS = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

class PageBase():
    
    def __init__( self ):
        
        self._page_key = os.urandom( 32 )
        
        self._pretty_status = ''
        
        self._options = wx.GetApp().Read( 'options' )
        
        HC.pubsub.sub( self, 'SetPrettyStatus', 'new_page_status' )
        
    
    def GetPrettyStatus( self ): return self._pretty_status
    
    def GetSashPositions( self ):
        
        x = self._options[ 'hpos' ]
        
        y = self._options[ 'vpos' ]
        
        return ( x, y )
        
    
    def PageHidden( self ): HC.pubsub.pub( 'page_hidden', self._page_key )
    
    def PageShown( self ): HC.pubsub.pub( 'page_shown', self._page_key )
    
    def SetPrettyStatus( self, page_key, status ):
        
        if page_key == self._page_key:
            
            self._pretty_status = status
            
            HC.pubsub.pub( 'refresh_status' )
            
        
    
    def RefreshQuery( self ): HC.pubsub.pub( 'refresh_query', self._page_key )
    
    def SetMediaFocus( self ): pass
    
    def SetSearchFocus( self ): HC.pubsub.pub( 'set_search_focus', self._page_key )
    
    def SetSynchronisedWait( self ): HC.pubsub.pub( 'synchronised_wait_switch', self._page_key )
    
    def ShowHideSplit( self ): pass
    
    def TryToClose( self ): pass
    
class PageLog( PageBase, wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        PageBase.__init__( self )
        
        log = wx.GetApp().GetLog()
        
        self._log_list_ctrl = ClientGUICommon.SaneListCtrl( self, 480, [ ( 'type', 60 ), ( 'source', 180 ), ( 'message', -1 ), ( 'time', 120 ) ] )
        
        for ( type, source, message, time ) in log: self._AddEntry( type, source, message, time )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._log_list_ctrl, FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        HC.pubsub.sub( self, 'AddError', 'log_error' )
        HC.pubsub.sub( self, 'AddMessage', 'log_message' )
        
    
    def _AddEntry( self, type, source, message, time ): self._log_list_ctrl.Append( ( CC.log_string_lookup[ type ], source, message, HC.ConvertTimestampToPrettyTime( time ) ), ( CC.log_string_lookup[ type ], source, message, time ) )
    
    def AddError( self, source, message ):
        
        # assuming we want to show errors right now
        
        self._AddEntry( CC.LOG_ERROR, source, message, time.time() )
        
    
    def AddMessage( self, source, message ):
        
        # assuming we want to show messages right now
        
        self._AddEntry( CC.LOG_MESSAGE, source, message, time.time() )
        
    
class PageMessages( PageBase, wx.SplitterWindow ):
    
    def __init__( self, parent, identity ):
        
        wx.SplitterWindow.__init__( self, parent )
        PageBase.__init__( self )
        
        self.SetMinimumPaneSize( 120 )
        self.SetSashGravity( 0.0 )
        
        self._identity = identity
        
        self._search_preview_split = wx.SplitterWindow( self, style=wx.SP_NOBORDER )
        
        self._search_preview_split.SetMinimumPaneSize( 180 )
        self._search_preview_split.SetSashGravity( 0.5 )
        
        self._search_preview_split.Bind( wx.EVT_SPLITTER_DCLICK, self.EventPreviewUnsplit )
        
        self._InitManagementPanel()
        self._preview_panel = ClientGUICanvas.CanvasPanel( self._search_preview_split, self._page_key, HC.LOCAL_FILE_SERVICE_IDENTIFIER )
        self._InitMessagesPanel()
        
        self.SplitVertically( self._search_preview_split, self._messages_panel, self._options[ 'hpos' ] )
        wx.CallAfter( self._search_preview_split.SplitHorizontally, self._management_panel, self._preview_panel, self._options[ 'vpos' ] )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelMessages( self._search_preview_split, self._page_key, self._identity )
    
    def _InitMessagesPanel( self ): self._messages_panel = ClientGUIMessages.ConversationSplitter( self, self._page_key, self._identity )
    
    def EventPreviewUnsplit( self, event ): self._search_preview_split.Unsplit( self._preview_panel )
    
    def GetSashPositions( self ):
        
        if self.IsSplit(): x = self.GetSashPosition()
        else: x = self._options[ 'hpos' ]
        
        if self._search_preview_split.IsSplit(): y = -1 * self._preview_panel.GetSize()[1]
        else: y = self._options[ 'vpos' ]
        
        return ( x, y )
        
    
    def ShowHideSplit( self ):
        
        if self._search_preview_split.IsSplit(): self._search_preview_split.Unsplit( self._preview_panel )
        else: self._search_preview_split.SplitHorizontally( self._management_panel, self._preview_panel, self._options[ 'vpos' ] )
        
    
    def TryToClose( self ): self._management_panel.TryToClose()
    
class PageWithMedia( PageBase, wx.SplitterWindow ):
    
    def __init__( self, parent, file_service_identifier = HC.LOCAL_FILE_SERVICE_IDENTIFIER ):
        
        wx.SplitterWindow.__init__( self, parent )
        PageBase.__init__( self )
        
        self._file_service_identifier = file_service_identifier
        
        self.SetMinimumPaneSize( 120 )
        self.SetSashGravity( 0.0 )
        
        self.Bind( wx.EVT_SPLITTER_DCLICK, self.EventUnsplit )
        
        self._search_preview_split = wx.SplitterWindow( self, style=wx.SP_NOBORDER )
        
        self._search_preview_split.SetMinimumPaneSize( 180 )
        self._search_preview_split.SetSashGravity( 0.5 )
        
        self._search_preview_split.Bind( wx.EVT_SPLITTER_DCLICK, self.EventPreviewUnsplit )
        
        self._InitManagementPanel()
        self._preview_panel = ClientGUICanvas.CanvasPanel( self._search_preview_split, self._page_key, self._file_service_identifier )
        self._InitMediaPanel()
        
        self.SplitVertically( self._search_preview_split, self._media_panel, self._options[ 'hpos' ] )
        wx.CallAfter( self._search_preview_split.SplitHorizontally, self._management_panel, self._preview_panel, self._options[ 'vpos' ] )
        
        HC.pubsub.sub( self, 'SwapMediaPanel', 'swap_media_panel' )
        
    
    def EventPreviewUnsplit( self, event ): self._search_preview_split.Unsplit( self._preview_panel )
    
    def EventUnsplit( self, event ): self.Unsplit( self._search_preview_split )
    
    # used by autocomplete
    def GetMedia( self ): return self._media_panel.GetSortedMedia()
    
    def GetSashPositions( self ):
        
        if self.IsSplit(): x = self.GetSashPosition()
        else: x = self._options[ 'hpos' ]
        
        if self._search_preview_split.IsSplit(): y = -1 * self._preview_panel.GetSize()[1]
        else: y = self._options[ 'vpos' ]
        
        return ( x, y )
        
    
    def ShowHideSplit( self ):
        
        if self.IsSplit():
            
            self.Unsplit( self._search_preview_split )
            
        else:
            
            self.SplitVertically( self._search_preview_split, self._media_panel, self._options[ 'hpos' ] )
            
            self._search_preview_split.SplitHorizontally( self._management_panel, self._preview_panel, self._options[ 'vpos' ] )
            
        
    
    def SetMediaFocus( self ): self._media_panel.SetFocus()
    
    def SwapMediaPanel( self, page_key, new_panel ):
        
        if page_key == self._page_key:
            
            self._preview_panel.SetMedia( None )
            
            self.ReplaceWindow( self._media_panel, new_panel )
            
            self._media_panel.Destroy()
            
            self._media_panel = new_panel
            
        
    
    def TryToClose( self ): self._management_panel.TryToClose()
    
class PageImport( PageWithMedia ):
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, self._file_service_identifier, [], CC.FileQueryResult( self._file_service_identifier, [], [] ) )
    
class PageImportBooru( PageImport ):
    
    def __init__( self, parent, booru ):
        
        self._booru = booru
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedBooru( self._search_preview_split, self, self._page_key, self._booru )
    
class PageImportDeviantArt( PageImport ):
    
    def __init__( self, parent ):
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedDeviantArt( self._search_preview_split, self, self._page_key )
    
class PageImportGiphy( PageImport ):
    
    def __init__( self, parent ):
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedGiphy( self._search_preview_split, self, self._page_key )
    
class PageImportHDD( PageImport ):
    
    def __init__( self, parent, paths_info, **kwargs ):
        
        self._paths_info = paths_info
        self._kwargs = kwargs
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportHDD( self._search_preview_split, self, self._page_key, self._paths_info, **self._kwargs )
    
class PageImportHentaiFoundryArtist( PageImport ):
    
    def __init__( self, parent ):
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedHentaiFoundryArtist( self._search_preview_split, self, self._page_key )
    
class PageImportHentaiFoundryTags( PageImport ):
    
    def __init__( self, parent ):
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedHentaiFoundryTags( self._search_preview_split, self, self._page_key )
    
class PageImportNewgrounds( PageImport ):
    
    def __init__( self, parent ):
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedNewgrounds( self._search_preview_split, self, self._page_key )
    
class PageImportPixivArtist( PageImport ):
    
    def __init__( self, parent ):
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedPixivArtist( self._search_preview_split, self, self._page_key )
    
class PageImportPixivTag( PageImport ):
    
    def __init__( self, parent ):
        
        PageImport.__init__( self, parent )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedPixivTag( self._search_preview_split, self, self._page_key )
    
class PageImportThreadWatcher( PageImport ):
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportThreadWatcher( self._search_preview_split, self, self._page_key )
    
class PageImportTumblr( PageImport ):
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueAdvancedTumblr( self._search_preview_split, self, self._page_key )
    
class PageImportURL( PageImport ):
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportWithQueueURL( self._search_preview_split, self, self._page_key )
    
class PagePetitions( PageWithMedia ):
    
    def __init__( self, parent, petition_service_identifier ):
        
        self._petition_service_identifier = petition_service_identifier
        
        petition_service_type = petition_service_identifier.GetType()
        
        if petition_service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ): self._file_service_identifier = self._petition_service_identifier
        else: self._file_service_identifier = HC.COMBINED_FILE_SERVICE_IDENTIFIER
        
        PageWithMedia.__init__( self, parent, self._file_service_identifier )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelPetitions( self._search_preview_split, self, self._page_key, self._file_service_identifier, self._petition_service_identifier )
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelNoQuery( self, self._page_key, self._file_service_identifier )
    
class PageQuery( PageWithMedia ):
    
    def __init__( self, parent, file_service_identifier, initial_media_results = [], initial_predicates = [] ):
        
        self._initial_media_results = initial_media_results
        self._initial_predicates = initial_predicates
        
        PageWithMedia.__init__( self, parent, file_service_identifier )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelQuery( self._search_preview_split, self, self._page_key, self._file_service_identifier, initial_predicates = self._initial_predicates )
    
    def _InitMediaPanel( self ):
        
        if len( self._initial_media_results ) == 0: self._media_panel = ClientGUIMedia.MediaPanelNoQuery( self, self._page_key, self._file_service_identifier )
        else:
            
            file_query_result = CC.FileQueryResult( self._file_service_identifier, self._initial_predicates, self._initial_media_results )
            
            self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, self._file_service_identifier, self._initial_predicates, file_query_result )
            
        
    
class PageThreadDumper( PageWithMedia ):
    
    def __init__( self, parent, imageboard, hashes ):
        
        self._imageboard = imageboard
        
        search_context = CC.FileSearchContext()
        
        self._unsorted_file_query_result = wx.GetApp().Read( 'media_results', search_context, hashes )
        
        hashes_to_media_results = { media_result.GetHash() : media_result for media_result in self._unsorted_file_query_result }
        
        self._media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
        
        self._media_results = filter( self._imageboard.IsOkToPost, self._media_results )
        
        self._file_query_result = CC.FileQueryResult( HC.LOCAL_FILE_SERVICE_IDENTIFIER, [], self._media_results )
        
        PageWithMedia.__init__( self, parent, HC.LOCAL_FILE_SERVICE_IDENTIFIER )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelDumper( self._search_preview_split, self, self._page_key, self._imageboard, self._media_results )
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, HC.LOCAL_FILE_SERVICE_IDENTIFIER, [], self._file_query_result )
    