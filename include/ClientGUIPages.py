import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIManagement
import ClientGUIMedia
import ClientGUICanvas
import ClientDownloading
import HydrusData
import HydrusSerialisable
import HydrusThreading
import inspect
import os
import sys
import time
import traceback
import wx
import HydrusGlobals as HG

class Page( wx.SplitterWindow ):
    
    def __init__( self, parent, controller, management_controller, initial_hashes ):
        
        wx.SplitterWindow.__init__( self, parent )
        
        self._page_key = HydrusData.GenerateKey()
        
        self._controller = controller
        
        self._management_controller = management_controller
        
        self._initial_hashes = initial_hashes
        
        self._management_controller.SetKey( 'page', self._page_key )
        
        self._pretty_status = ''
        
        self.SetMinimumPaneSize( 120 )
        self.SetSashGravity( 0.0 )
        
        self.Bind( wx.EVT_SPLITTER_DCLICK, self.EventUnsplit )
        
        self._search_preview_split = wx.SplitterWindow( self, style = wx.SP_NOBORDER )
        
        self._search_preview_split.SetMinimumPaneSize( 180 )
        self._search_preview_split.SetSashGravity( 1.0 )
        
        self._search_preview_split.Bind( wx.EVT_SPLITTER_DCLICK, self.EventPreviewUnsplit )
        
        self._management_panel = ClientGUIManagement.CreateManagementPanel( self._search_preview_split, self, self._controller, self._management_controller )
        
        file_service_key = self._management_controller.GetKey( 'file_service' )
        
        self._preview_panel = ClientGUICanvas.CanvasPanel( self._search_preview_split, self._page_key )
        
        self._media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, file_service_key, [] )
        
        self._search_preview_split.SplitHorizontally( self._management_panel, self._preview_panel, HC.options[ 'vpos' ] )
        
        self.SplitVertically( self._search_preview_split, self._media_panel, HC.options[ 'hpos' ] )
        
        if HC.options[ 'hide_preview' ]:
            
            wx.CallAfter( self._search_preview_split.Unsplit, self._preview_panel )
            
        
        self._controller.sub( self, 'SetPrettyStatus', 'new_page_status' )
        self._controller.sub( self, 'SwapMediaPanel', 'swap_media_panel' )
        
        if initial_hashes is not None and len( initial_hashes ) > 0:
            
            self._initialised = False
            
            self._controller.CallToThread( self.THREADLoadInitialMediaResults )
            
        else:
            
            self._initialised = True
            
        
    
    def _SetPrettyStatus( self, status ):
        
        self._pretty_status = status
        
        self._controller.pubimmediate( 'refresh_status' )
        
    
    def _SwapMediaPanel( self, new_panel ):
        
        self._preview_panel.SetMedia( None )
        
        self._media_panel.ClearPageKey()
        
        self.ReplaceWindow( self._media_panel, new_panel )
        
        self._media_panel.Hide()
        
        # If this is a CallAfter, OS X segfaults on refresh jej
        wx.CallLater( 500, self._media_panel.Destroy )
        
        self._media_panel = new_panel
        
    
    def CleanBeforeDestroy( self ):
        
        self._management_panel.CleanBeforeDestroy()
        
    
    def EventPreviewUnsplit( self, event ):
        
        self._search_preview_split.Unsplit( self._preview_panel )
        
        self._controller.pub( 'set_focus', self._page_key, None )
        
    
    def EventUnsplit( self, event ):
        
        self.Unsplit( self._search_preview_split )
        
        self._controller.pub( 'set_focus', self._page_key, None )
        
    
    def GetHashes( self ):
        
        if self._initialised:
            
            media = self.GetMedia()
            
            hashes = []
            
            for m in media:
                
                hashes.extend( m.GetHashes() )
                
            
            return hashes
            
        else:
            
            return self._initial_hashes
            
        
    
    def GetManagementController( self ):
        
        return self._management_controller
        
    
    # used by autocomplete
    def GetMedia( self ):
        
        return self._media_panel.GetSortedMedia()
        
    
    def GetPageKey( self ):
        
        return self._page_key
        
    
    def GetPrettyStatus( self ):
        
        return self._pretty_status
        
    
    def GetSashPositions( self ):
        
        if self.IsSplit():
            
            x = self.GetSashPosition()
            
        else:
            
            x = HC.options[ 'hpos' ]
            
        
        if self._search_preview_split.IsSplit():
            
            # I used to do:
            # y = -1 * self._preview_panel.GetSize()[1]
            # but that crept 4 pixels smaller every time, I assume due to sash caret height
            
            ( sps_x, sps_y ) = self._search_preview_split.GetClientSize()
            
            sash_y = self._search_preview_split.GetSashPosition()
            
            y = -1 * ( sps_y - sash_y )
            
        else:
            
            y = HC.options[ 'vpos' ]
            
        
        return ( x, y )
        
    
    def IsURLImportPage( self ):
        
        return self._management_controller.GetType() == ClientGUIManagement.MANAGEMENT_TYPE_IMPORT_URLS
        
    
    def PageHidden( self ):
        
        self._controller.pub( 'page_hidden', self._page_key )
        
    
    def PageShown( self ):
        
        self._controller.pub( 'page_shown', self._page_key )
        
    
    def PrepareToHide( self ):
        
        self._controller.pub( 'set_focus', self._page_key, None )
        
    
    def RefreshQuery( self ):
        
        if self._initialised:
            
            self._controller.pub( 'refresh_query', self._page_key )
            
        
    
    def ShowHideSplit( self ):
        
        if self.IsSplit():
            
            self.Unsplit( self._search_preview_split )
            
            self._controller.pub( 'set_focus', self._page_key, None )
            
        else:
            
            self.SplitVertically( self._search_preview_split, self._media_panel, HC.options[ 'hpos' ] )
            
            self._search_preview_split.SplitHorizontally( self._management_panel, self._preview_panel, HC.options[ 'vpos' ] )
            
        
    
    def SetMediaFocus( self ):
        
        self._media_panel.SetFocus()
        
    
    def SetMediaResults( self, media_results ):
        
        file_service_key = self._management_controller.GetKey( 'file_service' )
        
        media_panel = ClientGUIMedia.MediaPanelThumbnails( self, self._page_key, file_service_key, media_results )
        
        self._SwapMediaPanel( media_panel )
        
        self._initialised = True
        self._initial_hashes = []
        
    
    def SetPrettyStatus( self, page_key, status ):
        
        if page_key == self._page_key:
            
            if self._initialised:
                
                self._SetPrettyStatus( status )
                
            
        
    
    def SetSearchFocus( self ):
        
        self._controller.pub( 'set_search_focus', self._page_key )
        
    
    def SetSynchronisedWait( self ):
        
        self._controller.pub( 'synchronised_wait_switch', self._page_key )
        
    
    def SwapMediaPanel( self, page_key, new_panel ):
        
        if page_key == self._page_key:
            
            self._SwapMediaPanel( new_panel )
            
        
    
    def TestAbleToClose( self ):
        
        self._management_panel.TestAbleToClose()
        
    
    def THREADLoadInitialMediaResults( self ):
        
        initial_media_results = []
        
        for group_of_initial_hashes in HydrusData.SplitListIntoChunks( self._initial_hashes, 256 ):
            
            more_media_results = self._controller.Read( 'media_results', group_of_initial_hashes )
            
            initial_media_results.extend( more_media_results )
            
            status = u'Loading initial files\u2026 ' + HydrusData.ConvertValueRangeToPrettyString( len( initial_media_results ), len( self._initial_hashes ) )
            
            self._SetPrettyStatus( status )
            
        
        hashes_to_media_results = { media_result.GetHash() : media_result for media_result in initial_media_results }
        
        sorted_initial_media_results = [ hashes_to_media_results[ hash ] for hash in self._initial_hashes ]
        
        wx.CallAfter( self.SetMediaResults, sorted_initial_media_results )
        
    
class GUISession( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._pages = []
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = []
        
        for ( page_name, management_controller, hashes ) in self._pages:
            
            serialisable_management_controller = management_controller.GetSerialisableTuple()
            
            serialisable_hashes = [ hash.encode( 'hex' ) for hash in hashes ]
            
            serialisable_info.append( ( page_name, serialisable_management_controller, serialisable_hashes ) )
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( page_name, serialisable_management_controller, serialisable_hashes ) in serialisable_info:
            
            management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
            
            hashes = [ hash.decode( 'hex' ) for hash in serialisable_hashes ]
            
            self._pages.append( ( page_name, management_controller, hashes ) )
            
        
    
    def AddPage( self, page_name, management_controller, hashes ):
        
        self._pages.append( ( page_name, management_controller, hashes ) )
        
    
    def IteratePages( self ):
        
        for page_tuple in self._pages:
            
            yield page_tuple
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION ] = GUISession
