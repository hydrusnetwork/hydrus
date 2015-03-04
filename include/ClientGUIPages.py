import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIManagement
import ClientGUIMedia
import ClientGUIMessages
import ClientGUICanvas
import HydrusDownloading
import inspect
import os
import sys
import time
import traceback
import wx

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()
FLAGS_EXPAND_SIZER_DEPTH_ONLY = wx.SizerFlags( 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_BUTTON_SIZER = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

class PageBase( object ):
    
    _is_storable = False
    
    def __init__( self, starting_from_session = False ):
        
        self._starting_from_session = starting_from_session
        self._page_key = os.urandom( 32 )
        
        self._management_panel = None
        self._media_panel = None
        
        self._InitControllers()
        
        self._pretty_status = ''
        
        HC.pubsub.sub( self, 'SetPrettyStatus', 'new_page_status' )
        
    
    def _InitControllers( self ): pass
    
    def _InitManagementPanel( self ): pass
    
    def _InitMediaPanel( self ): pass
    
    def _PauseControllers( self ): pass
    
    def _ResumeControllers( self ): pass
    
    def CleanBeforeDestroy( self ): pass
    
    def GetPrettyStatus( self ): return self._pretty_status
    
    def GetSashPositions( self ):
        
        x = HC.options[ 'hpos' ]
        
        y = HC.options[ 'vpos' ]
        
        return ( x, y )
        
    
    def IsStorable( self ): return self._is_storable
    
    def PageHidden( self ): HC.pubsub.pub( 'page_hidden', self._page_key )
    
    def PageShown( self ): HC.pubsub.pub( 'page_shown', self._page_key )
    
    def Pause( self ):
        
        self._PauseControllers()
        
        HC.pubsub.pub( 'pause', self._page_key )
        
        HC.pubsub.pub( 'set_focus', self._page_key, None )
        
    
    def SetPrettyStatus( self, page_key, status ):
        
        if page_key == self._page_key:
            
            self._pretty_status = status
            
            HC.pubsub.pub( 'refresh_status' )
            
        
    
    def RefreshQuery( self ): HC.pubsub.pub( 'refresh_query', self._page_key )
    
    def SetMediaFocus( self ): pass
    
    def SetSearchFocus( self ): HC.pubsub.pub( 'set_search_focus', self._page_key )
    
    def SetSynchronisedWait( self ): HC.pubsub.pub( 'synchronised_wait_switch', self._page_key )
    
    def ShowHideSplit( self ): pass
    
    def TestAbleToClose( self ): pass
    
    def Resume( self ):
        
        self._ResumeControllers()
        
        HC.pubsub.pub( 'resume', self._page_key )
        
    
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
        self._preview_panel = ClientGUICanvas.CanvasPanel( self._search_preview_split, self._page_key, HC.LOCAL_FILE_SERVICE_KEY )
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
    
class PageWithMedia( PageBase, wx.SplitterWindow ):
    
    def __init__( self, parent, file_service_key = HC.LOCAL_FILE_SERVICE_KEY, initial_hashes = [], initial_media_results = [], starting_from_session = False ):
        
        wx.SplitterWindow.__init__( self, parent )
        PageBase.__init__( self, starting_from_session = starting_from_session )
        
        if len( initial_hashes ) > 0: initial_media_results = HC.app.Read( 'media_results', file_service_key, initial_hashes )
        
        self._file_service_key = file_service_key
        self._initial_media_results = initial_media_results
        
        self.SetMinimumPaneSize( 120 )
        self.SetSashGravity( 0.0 )
        
        self.Bind( wx.EVT_SPLITTER_DCLICK, self.EventUnsplit )
        
        self._search_preview_split = wx.SplitterWindow( self, style=wx.SP_NOBORDER )
        
        self._search_preview_split.SetMinimumPaneSize( 180 )
        self._search_preview_split.SetSashGravity( 0.5 )
        
        self._search_preview_split.Bind( wx.EVT_SPLITTER_DCLICK, self.EventPreviewUnsplit )
        
        self._InitManagementPanel()
        self._preview_panel = ClientGUICanvas.CanvasPanel( self._search_preview_split, self._page_key, self._file_service_key )
        self._InitMediaPanel()
        
        self.SplitVertically( self._search_preview_split, self._media_panel, HC.options[ 'hpos' ] )
        wx.CallAfter( self._search_preview_split.SplitHorizontally, self._management_panel, self._preview_panel, HC.options[ 'vpos' ] )
        
        HC.pubsub.sub( self, 'SwapMediaPanel', 'swap_media_panel' )
        
    
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
            
            wx.CallAfter( self._media_panel.Destroy )
            
            self._media_panel = new_panel
            
        
    
    def TestAbleToClose( self ): self._management_panel.TestAbleToClose()
    
class PageImport( PageWithMedia ):
    
    _is_storable = True
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            advanced_import_options = self._management_panel.GetAdvancedImportOptions()
            
            return HydrusDownloading.ImportArgsGenerator( job_key, item, advanced_import_options )
            
        
        return factory
        
    
    def _GenerateImportQueueBuilderFactory( self ):
        
        def factory( job_key, item ):
            
            return HydrusDownloading.ImportQueueBuilder( job_key, item )
            
        
        return factory
        
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, self._file_service_key, self._initial_media_results )
    
    def _InitControllers( self ):
        
        import_args_generator_factory = self._GenerateImportArgsGeneratorFactory()
        import_queue_builder_factory = self._GenerateImportQueueBuilderFactory()
        
        self._import_controller = HydrusDownloading.ImportController( import_args_generator_factory, import_queue_builder_factory, page_key = self._page_key )
        
        self._import_controller.StartDaemon()
        
    
    def _PauseControllers( self ):
        
        controller_job_key = self._import_controller.GetJobKey( 'controller' )
        
        controller_job_key.Pause()
        
    
    def _ResumeControllers( self ):
        
        controller_job_key = self._import_controller.GetJobKey( 'controller' )
        
        controller_job_key.Resume()
        
    
    def CleanBeforeDestroy( self ):
        
        PageWithMedia.CleanBeforeDestroy( self )
        
        self._import_controller.CleanBeforeDestroy()
        
    
    def GetSessionArgs( self ):
        
        hashes = [ media.GetHash() for media in self._media_panel.GetFlatMedia() ]
        
        args = tuple()
        kwargs = { 'initial_hashes' : hashes }
        
        return ( args, kwargs )
        
    
class PageImportGallery( PageImport ):
    
    def __init__( self, parent, gallery_name, gallery_type, initial_hashes = [], starting_from_session = False ):
        
        self._gallery_name = gallery_name
        self._gallery_type = gallery_type
        
        PageImport.__init__( self, parent, initial_hashes = initial_hashes, starting_from_session = starting_from_session )
        
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            advanced_import_options = self._management_panel.GetAdvancedImportOptions()
            advanced_tag_options = self._management_panel.GetAdvancedTagOptions()
            
            downloaders_factory = self._GetDownloadersFactory()
            
            return HydrusDownloading.ImportArgsGeneratorGallery( job_key, item, advanced_import_options, advanced_tag_options, downloaders_factory )
            
        
        return factory
        
    
    def _GenerateImportQueueBuilderFactory( self ):
        
        def factory( job_key, item ):
            
            downloaders_factory = self._GetDownloadersFactory()
            
            return HydrusDownloading.ImportQueueBuilderGallery( job_key, item, downloaders_factory )
            
        
        return factory
        
    
    def _GetDownloadersFactory( self ):
        
        if self._gallery_name == 'booru':
            
            def downloaders_factory( raw_tags ):
                
                booru = self._gallery_type
                tags = raw_tags.split( ' ' )
                
                return ( HydrusDownloading.DownloaderBooru( booru, tags ), )
                
            
        elif self._gallery_name == 'deviant art':
            
            if self._gallery_type == 'artist':
                
                def downloaders_factory( artist ):
                    
                    return ( HydrusDownloading.DownloaderDeviantArt( artist ), )
                    
                
            
        elif self._gallery_name == 'giphy':
            
            def downloaders_factory( tag ):
                
                return ( HydrusDownloading.DownloaderGiphy( tag ), )
                
            
        elif self._gallery_name == 'hentai foundry':
            
            if self._gallery_type == 'artist':
                
                def downloaders_factory( artist ):
                    
                    advanced_hentai_foundry_options = self._management_panel.GetAdvancedHentaiFoundryOptions()
                    
                    pictures_downloader = HydrusDownloading.DownloaderHentaiFoundry( 'artist pictures', artist, advanced_hentai_foundry_options )
                    scraps_downloader = HydrusDownloading.DownloaderHentaiFoundry( 'artist scraps', artist, advanced_hentai_foundry_options )
                    
                    return ( pictures_downloader, scraps_downloader )
                    
                
            elif self._gallery_type == 'tags':
                
                def downloaders_factory( raw_tags ):
                    
                    advanced_hentai_foundry_options = self._management_panel.GetAdvancedHentaiFoundryOptions()
                    
                    tags = raw_tags.split( ' ' )
                    
                    return ( HydrusDownloading.DownloaderHentaiFoundry( 'tags', tags, advanced_hentai_foundry_options ), )
                    
                
            
        elif self._gallery_name == 'newgrounds':
            
            def downloaders_factory( artist ):
                
                return ( HydrusDownloading.DownloaderNewgrounds( artist ), )
                
            
        elif self._gallery_name == 'pixiv':
            
            if self._gallery_type in ( 'artist', 'artist_id' ):
                
                def downloaders_factory( artist_id ):
                    
                    return ( HydrusDownloading.DownloaderPixiv( 'artist_id', artist_id ), )
                    
                
            elif self._gallery_type == 'tag':
                
                def downloaders_factory( tag ):
                    
                    return ( HydrusDownloading.DownloaderPixiv( 'tags', tag ), )
                    
                
            
        elif self._gallery_name == 'tumblr':
            
            def downloaders_factory( username ):
                
                return ( HydrusDownloading.DownloaderTumblr( username ), )
                
            
        
        return downloaders_factory
        
    
    def _InitManagementPanel( self ):
        
        if self._gallery_name == 'hentai foundry':
            
            name = 'hentai foundry'
            namespaces = [ 'creator', 'title', '' ]
            
            if self._gallery_type == 'artist': initial_search_value = 'artist username'
            elif self._gallery_type == 'tags': initial_search_value = 'search tags'
            
            ato = HC.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_HENTAI_FOUNDRY )
            
            self._management_panel = ClientGUIManagement.ManagementPanelImportsGalleryHentaiFoundry( self._search_preview_split, self, self._page_key, self._import_controller, name, namespaces, ato, initial_search_value, starting_from_session = self._starting_from_session )
            
        else:
            
            if self._gallery_name == 'booru':
                
                booru = self._gallery_type
                
                name = booru.GetName()
                namespaces = booru.GetNamespaces()
                initial_search_value = 'search tags'
                
                ato = HC.GetDefaultAdvancedTagOptions( ( HC.SITE_TYPE_BOORU, name ) )
                
            elif self._gallery_name == 'deviant art':
                
                if self._gallery_type == 'artist':
                    
                    name = 'deviant art'
                    namespaces = [ 'creator', 'title' ]
                    initial_search_value = 'artist username'
                    
                
                ato = HC.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_DEVIANT_ART )
                
            elif self._gallery_name == 'giphy':
                
                name = 'giphy'
                namespaces = [ '' ]
        
                initial_search_value = 'search tag'
                
                ato = HC.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_GIPHY )
                
            elif self._gallery_name == 'newgrounds':
                
                name = 'newgrounds'
                namespaces = [ 'creator', 'title', '' ]
                initial_search_value = 'artist username'
                
                ato = HC.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_NEWGROUNDS )
                
            elif self._gallery_name == 'pixiv':
                
                name = 'pixiv'
                namespaces = [ 'creator', 'title', '' ]
                
                if self._gallery_type in ( 'artist', 'artist_id' ): initial_search_value = 'numerical artist id'
                elif self._gallery_type == 'tag': initial_search_value = 'search tag'
                
                ato = HC.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_PIXIV )
                
            elif self._gallery_name == 'tumblr':
                
                name = 'tumblr'
                namespaces = [ '' ]
                initial_search_value = 'username'
                
                ato = HC.GetDefaultAdvancedTagOptions( HC.SITE_TYPE_TUMBLR )
                
            
            self._management_panel = ClientGUIManagement.ManagementPanelImportsGallery( self._search_preview_split, self, self._page_key, self._import_controller, name, namespaces, ato, initial_search_value, starting_from_session = self._starting_from_session )
            
        
    
    def GetSessionArgs( self ):
        
        hashes = [ media.GetHash() for media in self._media_panel.GetFlatMedia() ]
        
        args = ( self._gallery_name, self._gallery_type )
        kwargs = { 'initial_hashes' : hashes }
        
        return ( args, kwargs )
        
    
class PageImportHDD( PageImport ):
    
    def __init__( self, parent, paths_info, initial_hashes = [], advanced_import_options = {}, paths_to_tags = {}, delete_after_success = False, starting_from_session = False ):
        
        self._paths_info = paths_info
        self._advanced_import_options = advanced_import_options
        self._paths_to_tags = paths_to_tags
        self._delete_after_success = delete_after_success
        
        PageImport.__init__( self, parent, initial_hashes = initial_hashes, starting_from_session = starting_from_session )
        
        self._import_controller.PendImportQueueJob( self._paths_info )
        
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            return HydrusDownloading.ImportArgsGeneratorHDD( job_key, item, self._advanced_import_options, self._paths_to_tags, self._delete_after_success )
            
        
        return factory
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportHDD( self._search_preview_split, self, self._page_key, self._import_controller, starting_from_session = self._starting_from_session )
    
    def GetSessionArgs( self ):
        
        hashes = [ media.GetHash() for media in self._media_panel.GetFlatMedia() ]
        
        args = ( [], )
        kwargs = { 'initial_hashes' : hashes }
        
        return ( args, kwargs )
        
    
class PageImportThreadWatcher( PageImport ):
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            advanced_import_options = self._management_panel.GetAdvancedImportOptions()
            advanced_tag_options = self._management_panel.GetAdvancedTagOptions()
            
            # fourchan_board should be on the job_key or whatever. it is stuck on initial queue generation
            # we should not be getting it from the management_panel
            # we should have access to this info from the job_key or w/e
            
            return HydrusDownloading.ImportArgsGeneratorThread( job_key, item, advanced_import_options, advanced_tag_options )
            
        
        return factory
        
    
    def _GenerateImportQueueBuilderFactory( self ):
        
        def factory( job_key, item ):
            
            return HydrusDownloading.ImportQueueBuilderThread( job_key, item )
            
        
        return factory
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportThreadWatcher( self._search_preview_split, self, self._page_key, self._import_controller, starting_from_session = self._starting_from_session )
    
class PageImportURL( PageImport ):
    
    def _GenerateImportArgsGeneratorFactory( self ):
        
        def factory( job_key, item ):
            
            advanced_import_options = self._management_panel.GetAdvancedImportOptions()
            
            return HydrusDownloading.ImportArgsGeneratorURLs( job_key, item, advanced_import_options )
            
        
        return factory
        
    
    def _GenerateImportQueueBuilderFactory( self ):
        
        def factory( job_key, item ):
            
            return HydrusDownloading.ImportQueueBuilderURLs( job_key, item )
            
        
        return factory
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelImportsURL( self._search_preview_split, self, self._page_key, self._import_controller, starting_from_session = self._starting_from_session )
    
class PagePetitions( PageWithMedia ):
    
    def __init__( self, parent, petition_service_key, starting_from_session = False ):
        
        self._petition_service_key = petition_service_key
        
        petition_service = HC.app.GetManager( 'services' ).GetService( petition_service_key )
        
        petition_service_type = petition_service.GetServiceType()
        
        if petition_service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ): self._file_service_key = self._petition_service_key
        else: self._file_service_key = HC.COMBINED_FILE_SERVICE_KEY
        
        PageWithMedia.__init__( self, parent, self._file_service_key, starting_from_session = starting_from_session )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelPetitions( self._search_preview_split, self, self._page_key, self._file_service_key, self._petition_service_key, starting_from_session = self._starting_from_session )
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelNoQuery( self, self._page_key, self._file_service_key )
    
class PageQuery( PageWithMedia ):
    
    _is_storable = True
    
    def __init__( self, parent, file_service_key, initial_hashes = [], initial_media_results = [], initial_predicates = [], starting_from_session = False ):
        
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
        
        media_results = HC.app.Read( 'media_results', HC.LOCAL_FILE_SERVICE_KEY, hashes )
        
        hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
        
        self._media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
        
        self._media_results = filter( self._imageboard.IsOkToPost, self._media_results )
        
        PageWithMedia.__init__( self, parent, HC.LOCAL_FILE_SERVICE_KEY, starting_from_session = starting_from_session )
        
    
    def _InitManagementPanel( self ): self._management_panel = ClientGUIManagement.ManagementPanelDumper( self._search_preview_split, self, self._page_key, self._imageboard, self._media_results, starting_from_session = self._starting_from_session )
    
    def _InitMediaPanel( self ): self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, HC.LOCAL_FILE_SERVICE_KEY, self._media_results )
    
class_to_text = {}
text_to_class = {}

current_module = sys.modules[ __name__ ]

for ( name, c ) in inspect.getmembers( current_module ):
    
    if inspect.isclass( c ):
        
        class_to_text[ c ] = name
        text_to_class[ name ] = c
        
    