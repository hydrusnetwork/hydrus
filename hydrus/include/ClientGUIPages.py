from . import HydrusConstants as HC
from . import ClientConstants as CC
from . import ClientData
from . import ClientGUIDialogs
from . import ClientGUIFunctions
from . import ClientGUIManagement
from . import ClientGUIMedia
from . import ClientGUIMenus
from . import ClientGUICanvas
from . import ClientDownloading
from . import ClientSearch
from . import ClientGUIShortcuts
from . import ClientThreading
import collections
import hashlib
from . import HydrusData
from . import HydrusExceptions
from . import HydrusSerialisable
from . import HydrusThreading
import inspect
import os
import sys
import time
import traceback
import wx
from . import HydrusGlobals as HG

RESERVED_SESSION_NAMES = { '', 'just a blank page', 'last session', 'exit session' }

class DialogPageChooser( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, controller ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'new page', position = 'center' )
        
        self._controller = controller
        
        self._result = None
        
        # spawn in this order, so focus precipitates from the graphical top
        
        self._button_7 = wx.Button( self, label = '', id = 7 )
        self._button_8 = wx.Button( self, label = '', id = 8 )
        self._button_9 = wx.Button( self, label = '', id = 9 )
        self._button_4 = wx.Button( self, label = '', id = 4 )
        self._button_5 = wx.Button( self, label = '', id = 5 )
        self._button_6 = wx.Button( self, label = '', id = 6 )
        self._button_1 = wx.Button( self, label = '', id = 1 )
        self._button_2 = wx.Button( self, label = '', id = 2 )
        self._button_3 = wx.Button( self, label = '', id = 3 )
        
        gridbox = wx.GridSizer( 3 )
        
        gridbox.Add( self._button_7, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._button_8, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._button_9, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._button_4, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._button_5, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._button_6, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._button_1, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._button_2, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._button_3, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( gridbox )
        
        self.SetInitialSize( ( 420, 210 ) )
        
        self._services = HG.client_controller.services_manager.GetServices()
        
        repository_petition_permissions = [ ( content_type, HC.PERMISSION_ACTION_OVERRULE ) for content_type in HC.REPOSITORY_CONTENT_TYPES ]
        
        self._petition_service_keys = [ service.GetServiceKey() for service in self._services if service.GetServiceType() in HC.REPOSITORIES and True in ( service.HasPermission( content_type, action ) for ( content_type, action ) in repository_petition_permissions ) ]
        
        self._InitButtons( 'home' )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
        #
        
        self.Show( True )
        
    
    def _AddEntry( self, button, entry ):
        
        id = button.GetId()
        
        self._command_dict[ id ] = entry
        
        ( entry_type, obj ) = entry
        
        if entry_type == 'menu':
            
            button.SetLabelText( obj )
            
        elif entry_type == 'page_duplicate_filter':
            
            button.SetLabelText( 'duplicates processing' )
            
        elif entry_type == 'pages_notebook':
            
            button.SetLabelText( 'page of pages' )
            
        elif entry_type in ( 'page_query', 'page_petitions' ):
            
            name = HG.client_controller.services_manager.GetService( obj ).GetName()
            
            button.SetLabelText( name )
            
        elif entry_type == 'page_import_gallery':
            
            button.SetLabelText( 'gallery' )
            
        elif entry_type == 'page_import_simple_downloader':
            
            button.SetLabelText( 'simple downloader' )
            
        elif entry_type == 'page_import_watcher':
            
            button.SetLabelText( 'watcher' )
            
        elif entry_type == 'page_import_urls':
            
            button.SetLabelText( 'urls' )
            
        
        button.Show()
        
    
    def _HitButton( self, id ):
        
        if id in self._command_dict:
            
            ( entry_type, obj ) = self._command_dict[ id ]
            
            if entry_type == 'menu':
                
                self._InitButtons( obj )
                
            else:
                
                if entry_type == 'page_query': 
                    
                    file_service_key = obj
                    
                    page_name = 'files'
                    
                    search_enabled = True
                    
                    new_options = self._controller.new_options
                    
                    tag_service_key = new_options.GetKey( 'default_tag_service_search_page' )
                    
                    if not self._controller.services_manager.ServiceExists( tag_service_key ):
                        
                        tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
                        
                    
                    file_search_context = ClientSearch.FileSearchContext( file_service_key = file_service_key, tag_service_key = tag_service_key )
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerQuery( page_name, file_service_key, file_search_context, search_enabled ) )
                    
                elif entry_type == 'page_duplicate_filter':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerDuplicateFilter() )
                    
                elif entry_type == 'pages_notebook':
                    
                    self._result = ( 'pages', None )
                    
                elif entry_type == 'page_import_gallery':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportGallery() )
                    
                elif entry_type == 'page_import_simple_downloader':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportSimpleDownloader() )
                    
                elif entry_type == 'page_import_watcher':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportMultipleWatcher() )
                    
                elif entry_type == 'page_import_urls':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportURLs() )
                    
                elif entry_type == 'page_petitions':
                    
                    petition_service_key = obj
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerPetitions( petition_service_key ) )
                    
                
                self.EndModal( wx.ID_OK )
                
            
        
    
    def _InitButtons( self, menu_keyword ):
        
        self._command_dict = {}
        
        entries = []
        
        if menu_keyword == 'home':
            
            entries.append( ( 'menu', 'files' ) )
            entries.append( ( 'menu', 'download' ) )
            
            if len( self._petition_service_keys ) > 0:
                
                entries.append( ( 'menu', 'petitions' ) )
                
            
            entries.append( ( 'menu', 'special' ) )
            
        elif menu_keyword == 'files':
            
            entries.append( ( 'page_query', CC.LOCAL_FILE_SERVICE_KEY ) )
            entries.append( ( 'page_query', CC.TRASH_SERVICE_KEY ) )
            
            if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                entries.append( ( 'page_query', CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
                
            
            for service in self._services:
                
                if service.GetServiceType() == HC.FILE_REPOSITORY:
                    
                    entries.append( ( 'page_query', service.GetServiceKey() ) )
                    
                
            
        elif menu_keyword == 'download':
            
            entries.append( ( 'page_import_urls', None ) )
            entries.append( ( 'page_import_watcher', None ) )
            entries.append( ( 'page_import_gallery', None ) )
            entries.append( ( 'page_import_simple_downloader', None ) )
            
        elif menu_keyword == 'petitions':
            
            entries = [ ( 'page_petitions', service_key ) for service_key in self._petition_service_keys ]
            
        elif menu_keyword == 'special':
            
            entries.append( ( 'pages_notebook', None ) )
            entries.append( ( 'page_duplicate_filter', None ) )
            
        
        if len( entries ) <= 4:
            
            self._button_1.Hide()
            self._button_3.Hide()
            self._button_5.Hide()
            self._button_7.Hide()
            self._button_9.Hide()
            
            potential_buttons = [ self._button_8, self._button_4, self._button_6, self._button_2 ]
            
        elif len( entries ) <= 9:
            
            potential_buttons = [ self._button_7, self._button_8, self._button_9, self._button_4, self._button_5, self._button_6, self._button_1, self._button_2, self._button_3 ]
            
        else:
            
            # sort out a multi-page solution? maybe only if this becomes a big thing; the person can always select from the menus, yeah?
            
            potential_buttons = [ self._button_7, self._button_8, self._button_9, self._button_4, self._button_5, self._button_6, self._button_1, self._button_2, self._button_3 ]
            entries = entries[:9]
            
        
        for entry in entries:
            
            self._AddEntry( potential_buttons.pop( 0 ), entry )
            
        
        unused_buttons = potential_buttons
        
        for button in unused_buttons:
            
            button.Hide()
            
        
    
    def EventButton( self, event ):
        
        id = event.GetId()
        
        if id == wx.ID_CANCEL:
            
            self.EndModal( wx.ID_CANCEL )
            
        else:
            
            self._HitButton( id )
            
        
    
    def EventCharHook( self, event ):
        
        id = None
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key == wx.WXK_UP: id = 8
        elif key == wx.WXK_LEFT: id = 4
        elif key == wx.WXK_RIGHT: id = 6
        elif key == wx.WXK_DOWN: id = 2
        elif key == wx.WXK_NUMPAD1: id = 1
        elif key == wx.WXK_NUMPAD2: id = 2
        elif key == wx.WXK_NUMPAD3: id = 3
        elif key == wx.WXK_NUMPAD4: id = 4
        elif key == wx.WXK_NUMPAD5: id = 5
        elif key == wx.WXK_NUMPAD6: id = 6
        elif key == wx.WXK_NUMPAD7: id = 7
        elif key == wx.WXK_NUMPAD8: id = 8
        elif key == wx.WXK_NUMPAD9: id = 9
        elif key == wx.WXK_ESCAPE:
            
            self.EndModal( wx.ID_CANCEL )
            
            return
            
        else:
            
            event.Skip()
            
        
        if id is not None:
            
            self._HitButton( id )
            
        
    
    def GetValue( self ):
        
        return self._result
        
    
class Page( wx.SplitterWindow ):
    
    def __init__( self, parent, controller, management_controller, initial_hashes ):
        
        wx.SplitterWindow.__init__( self, parent )
        
        self._controller = controller
        
        self._page_key = self._controller.AcquirePageKey()
        
        self._management_controller = management_controller
        
        self._initial_hashes = initial_hashes
        
        self._management_controller.SetKey( 'page', self._page_key )
        
        self._initialised = False
        
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
        self._controller.sub( self, 'SetSplitterPositions', 'set_splitter_positions' )
        
    
    def _SetPrettyStatus( self, status ):
        
        self._pretty_status = status
        
        self._controller.gui.SetStatusBarDirty()
        
    
    def _SwapMediaPanel( self, new_panel ):
        
        # if a new media page comes in while its menu is open, we can enter program instability.
        # so let's just put it off.
        
        if self._controller.MenuIsOpen():
            
            self._controller.CallLaterWXSafe( self, 0.5, self._SwapMediaPanel, new_panel )
            
            return
            
        
        self._preview_panel.SetMedia( None )
        
        self._media_panel.ClearPageKey()
        
        collect_by = self._management_panel.GetCollectBy()
        
        if collect_by != []:
            
            new_panel.Collect( self._page_key, collect_by )
            
            sort_by = self._management_panel.GetSortBy()
            
            new_panel.Sort( self._page_key, sort_by )
            
        
        self.ReplaceWindow( self._media_panel, new_panel )
        
        self._media_panel.DestroyLater()
        
        self._media_panel = new_panel
        
        self._controller.pub( 'refresh_page_name', self._page_key )
        
    
    def CheckAbleToClose( self ):
        
        self._management_panel.CheckAbleToClose()
        
    
    def CleanBeforeClose( self ):
        
        self._management_panel.CleanBeforeClose()
        
        self._controller.pub( 'set_focus', self._page_key, None )
        
    
    def CleanBeforeDestroy( self ):
        
        self._management_panel.CleanBeforeDestroy()
        
        self._preview_panel.CleanBeforeDestroy()
        
        self._controller.ReleasePageKey( self._page_key )
        
    
    def EventPreviewUnsplit( self, event ):
        
        self._search_preview_split.Unsplit( self._preview_panel )
        
        self._controller.pub( 'set_focus', self._page_key, None )
        
    
    def EventUnsplit( self, event ):
        
        self.Unsplit( self._search_preview_split )
        
        self._controller.pub( 'set_focus', self._page_key, None )
        
    
    def GetHashes( self ):
        
        if self._initialised:
            
            return self._media_panel.GetHashes( ordered = True )
            
        else:
            
            return self._initial_hashes
            
        
    
    def GetManagementController( self ):
        
        return self._management_controller
        
    
    def GetManagementPanel( self ):
        
        return self._management_panel
        
    
    # used by autocomplete
    def GetMedia( self ):
        
        return self._media_panel.GetSortedMedia()
        
    
    def GetMediaPanel( self ):
        
        return self._media_panel
        
    
    def GetName( self ):
        
        return self._management_controller.GetPageName()
        
    
    def GetNumFileSummary( self ):
        
        if self._initialised:
            
            num_files = self._media_panel.GetNumFiles()
            
        else:
            
            num_files = len( self._initial_hashes )
            
        
        ( num_value, num_range ) = self._management_controller.GetValueRange()
        
        if num_value == num_range:
            
            ( num_value, num_range ) = ( 0, 0 )
            
        
        return ( num_files, ( num_value, num_range ) )
        
    
    def GetPageKey( self ):
        
        return self._page_key
        
    
    def GetPageKeys( self ):
        
        return { self._page_key }
        
    
    def GetPageInfoDict( self, is_selected = False ):
        
        root = {}
        
        root[ 'name' ] = self.GetName()
        root[ 'page_key' ] = self._page_key.hex()
        root[ 'page_type' ] = self._management_controller.GetType()
        root[ 'focused' ] = is_selected
        
        return root
        
    
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
        
    
    def IsMultipleWatcherPage( self ):
        
        return self._management_controller.GetType() == ClientGUIManagement.MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER
        
    
    def IsImporter( self ):
        
        return self._management_controller.IsImporter()
        
    
    def IsURLImportPage( self ):
        
        return self._management_controller.GetType() == ClientGUIManagement.MANAGEMENT_TYPE_IMPORT_URLS
        
    
    def PageHidden( self ):
        
        self._management_panel.PageHidden()
        self._media_panel.PageHidden()
        
    
    def PageShown( self ):
        
        self._management_panel.PageShown()
        self._media_panel.PageShown()
        
    
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
        
        wx.CallAfter( self._management_panel.Start ) # importand this is callafter, so it happens after a heavy session load is done
        
    
    def SetName( self, name ):
        
        return self._management_controller.SetPageName( name )
        
    
    def SetPrettyStatus( self, page_key, status ):
        
        if page_key == self._page_key:
            
            if self._initialised:
                
                self._SetPrettyStatus( status )
                
            
        
    
    def SetSearchFocus( self ):
        
        self._management_panel.SetSearchFocus()
        
    
    def SetSplitterPositions( self, hpos, vpos ):
        
        if self._search_preview_split.IsSplit():
            
            self._search_preview_split.SetSashPosition( vpos )
            
        else:
            
            self._search_preview_split.SplitHorizontally( self._management_panel, self._preview_panel, vpos )
            
        
        if self.IsSplit():
            
            self.SetSashPosition( hpos )
            
        else:
            
            self.SplitVertically( self._search_preview_split, self._media_panel, hpos )
            
        
        if HC.options[ 'hide_preview' ]:
            
            wx.CallAfter( self._search_preview_split.Unsplit, self._preview_panel )
            
        
    
    def SetSynchronisedWait( self ):
        
        self._controller.pub( 'synchronised_wait_switch', self._page_key )
        
    
    def Start( self ):
        
        if self._initial_hashes is not None and len( self._initial_hashes ) > 0:
            
            self._controller.CallToThread( self.THREADLoadInitialMediaResults, self._controller, self._initial_hashes )
            
        else:
            
            self._initialised = True
            
            wx.CallAfter( self._management_panel.Start ) # importand this is callafter, so it happens after a heavy session load is done
            
        
    
    def SwapMediaPanel( self, new_panel ):
        
        self._SwapMediaPanel( new_panel )
        
    
    def TestAbleToClose( self ):
        
        try:
            
            self._management_panel.CheckAbleToClose()
            
        except HydrusExceptions.VetoException as e:
            
            reason = str( e )
            
            with ClientGUIDialogs.DialogYesNo( self, reason + ' Are you sure you want to close it?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
        
    
    def THREADLoadInitialMediaResults( self, controller, initial_hashes ):
        
        def wx_code_status( status ):
            
            if not self:
                
                return
                
            
            self._SetPrettyStatus( status )
            
        
        def wx_code_publish( media_results ):
            
            if not self:
                
                return
                
            
            self.SetMediaResults( media_results )
            
        
        initial_media_results = []
        
        for group_of_initial_hashes in HydrusData.SplitListIntoChunks( initial_hashes, 256 ):
            
            more_media_results = controller.Read( 'media_results', group_of_initial_hashes )
            
            initial_media_results.extend( more_media_results )
            
            status = 'Loading initial files\u2026 ' + HydrusData.ConvertValueRangeToPrettyString( len( initial_media_results ), len( initial_hashes ) )
            
            wx.CallAfter( wx_code_status, status )
            
        
        hashes_to_media_results = { media_result.GetHash() : media_result for media_result in initial_media_results }
        
        sorted_initial_media_results = [ hashes_to_media_results[ hash ] for hash in initial_hashes if hash in hashes_to_media_results ]
        
        wx.CallAfter( wx_code_publish, sorted_initial_media_results )
        
    
    def REPEATINGPageUpdate( self ):
        
        self._management_panel.REPEATINGPageUpdate()
        
    
class PagesNotebook( wx.Notebook ):
    
    def __init__( self, parent, controller, name ):
        
        if controller.new_options.GetBoolean( 'notebook_tabs_on_left' ):
            
            style = wx.NB_LEFT
            
        else:
            
            style = wx.NB_TOP
            
        
        wx.Notebook.__init__( self, parent, style = style )
        
        self._controller = controller
        
        self._page_key = self._controller.AcquirePageKey()
        
        self._name = name
        
        self._next_new_page_index = None
        
        self._potential_drag_page = None
        
        self._closed_pages = []
        
        self._last_last_session_hash = None
        
        self._controller.sub( self, 'RefreshPageName', 'refresh_page_name' )
        self._controller.sub( self, 'NotifyPageUnclosed', 'notify_page_unclosed' )
        
        self.Bind( wx.EVT_MOTION, self.EventDrag )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
        self.Bind( wx.EVT_LEFT_UP, self.EventLeftUp )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventLeftDoubleClick )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventMiddleClick )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventMenu )
        self.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventPageChanged )
        
    
    def _ChooseNewPage( self, insertion_index = None ):
        
        self._next_new_page_index = insertion_index
        
        with DialogPageChooser( self, self._controller ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( page_type, page_data ) = dlg.GetValue()
                
                if page_type == 'pages':
                    
                    self.NewPagesNotebook()
                    
                elif page_type == 'page':
                    
                    management_controller = page_data
                    
                    self.NewPage( management_controller )
                    
                
            
        
    
    def _CloseAllPages( self, polite = True, delete_pages = False ):
        
        closees = [ index for index in range( self.GetPageCount() ) ]
        
        self._ClosePages( closees, polite, delete_pages = delete_pages )
        
    
    def _CloseLeftPages( self, from_index ):
        
        message = 'Close all pages to the left?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                closees = [ index for index in range( self.GetPageCount() ) if index < from_index ]
                
                self._ClosePages( closees )
                
            
        
    
    def _CloseOtherPages( self, except_index ):
        
        message = 'Close all other pages?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                closees = [ index for index in range( self.GetPageCount() ) if index != except_index ]
                
                self._ClosePages( closees )
                
            
        
    
    def _ClosePage( self, index, polite = True, delete_page = False ):
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        if index == -1 or index > self.GetPageCount() - 1:
            
            return False
            
        
        page = self.GetPage( index )
        
        if polite:
            
            try:
                
                page.TestAbleToClose()
                
            except HydrusExceptions.VetoException:
                
                return False
                
            
        
        page.CleanBeforeClose()
        
        page_key = page.GetPageKey()
        
        self._closed_pages.append( ( index, page_key ) )
        
        self.RemovePage( index )
        
        self._controller.pub( 'refresh_page_name', self._page_key )
        
        if delete_page:
            
            self._controller.pub( 'notify_deleted_page', page )
            
        else:
            
            self._controller.pub( 'notify_closed_page', page )
            self._controller.pub( 'notify_new_undo' )
            
        
        return True
        
    
    def _ClosePages( self, indices, polite = True, delete_pages = False ):
        
        indices = list( indices )
        
        indices.sort( reverse = True ) # so we are closing from the end first
        
        for index in indices:
            
            successful = self._ClosePage( index, polite, delete_page = delete_pages )
            
            if not successful:
                
                break
                
            
        
    
    def _CloseRightPages( self, from_index ):
        
        message = 'Close all pages to the right?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                closees = [ index for index in range( self.GetPageCount() ) if index > from_index ]
                
                self._ClosePages( closees )
                
            
        
    
    def _GetDefaultPageInsertionIndex( self ):
        
        new_options = self._controller.new_options
        
        new_page_goes = new_options.GetInteger( 'default_new_page_goes' )
        
        current_index = self.GetSelection()
        
        if current_index == wx.NOT_FOUND:
            
            new_page_goes = CC.NEW_PAGE_GOES_FAR_LEFT
            
        
        if new_page_goes == CC.NEW_PAGE_GOES_FAR_LEFT:
            
            insertion_index = 0
            
        elif new_page_goes == CC.NEW_PAGE_GOES_LEFT_OF_CURRENT:
            
            insertion_index = current_index
            
        elif new_page_goes == CC.NEW_PAGE_GOES_RIGHT_OF_CURRENT:
            
            insertion_index = current_index + 1
            
        elif new_page_goes == CC.NEW_PAGE_GOES_FAR_RIGHT:
            
            insertion_index = self.GetPageCount()
            
        
        return insertion_index
        
    
    def _GetMediaPages( self, only_my_level ):
        
        results = []
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                if not only_my_level:
                    
                    results.extend( page.GetMediaPages() )
                    
                
            else:
                
                results.append( page )
                
            
        
        return results
        
    
    def _GetIndex( self, page_key ):
        
        for ( page, index ) in ( ( self.GetPage( index ), index ) for index in range( self.GetPageCount() ) ):
            
            if page.GetPageKey() == page_key:
                
                return index
                
            
        
        raise HydrusExceptions.DataMissing()
        
    
    def _GetNotebookFromScreenPosition( self, screen_position ):
        
        current_page = self.GetCurrentPage()
        
        if current_page is None or not isinstance( current_page, PagesNotebook ):
            
            return self
            
        else:
            
            ( tab_index, flags ) = ClientGUIFunctions.NotebookScreenToHitTest( self, screen_position )
            
            if tab_index != wx.NOT_FOUND:
                
                return self
                
            
            if HC.PLATFORM_OSX:
                
                ( x, y ) = screen_position
                ( child_x, child_y ) = current_page.GetPosition()
                
                on_child_notebook_somewhere = y > child_y # wew lad, OSX not delivering onpage maybe?
                
            else:
                
                on_child_notebook_somewhere = flags & wx.NB_HITTEST_ONPAGE
                
            
            if on_child_notebook_somewhere:
                
                return current_page._GetNotebookFromScreenPosition( screen_position )
                
            
        
        return self
        
    
    def _GetPages( self ):
        
        return [ self.GetPage( i ) for i in range( self.GetPageCount() ) ]
        
    
    def _GetPageFromName( self, page_name ):
        
        for page in self._GetPages():
            
            if page.GetName() == page_name:
                
                return page
                
            
            if isinstance( page, PagesNotebook ):
                
                result = page._GetPageFromName( page_name )
                
                if result is not None:
                    
                    return result
                    
                
            
        
        return None
        
    
    def _GetTopNotebook( self ):
        
        top_notebook = self
        
        parent = top_notebook.GetParent()
        
        while isinstance( parent, PagesNotebook ):
            
            top_notebook = parent
            
            parent = top_notebook.GetParent()
            
        
        return top_notebook
        
    
    def _MovePage( self, page, dest_notebook, insertion_tab_index, follow_dropped_page = False ):
        
        source_notebook = page.GetParent()
        
        for ( index, p ) in enumerate( source_notebook._GetPages() ):
            
            if p == page:
                
                source_notebook.RemovePage( index )
                
                break
                
            
        
        if source_notebook != dest_notebook:
            
            page.Reparent( dest_notebook )
            
            self._controller.pub( 'refresh_page_name', source_notebook.GetPageKey() )
            
        
        insertion_tab_index = min( insertion_tab_index, dest_notebook.GetPageCount() )
        
        dest_notebook.InsertPage( insertion_tab_index, page, page.GetName(), select = follow_dropped_page )
        
        if follow_dropped_page:
            
            self.ShowPage( page )
            
        
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        
    
    def _MovePages( self, pages, dest_notebook ):
        
        insertion_tab_index = dest_notebook.GetNumPages( only_my_level = True )
        
        for page in pages:
            
            if page.GetParent() != dest_notebook:
                
                self._MovePage( page, dest_notebook, insertion_tab_index )
                
                insertion_tab_index += 1
                
            
        
    
    def _RefreshPageName( self, index ):
        
        if index == -1 or index > self.GetPageCount() - 1:
            
            return
            
        
        new_options = self._controller.new_options
        
        max_page_name_chars = new_options.GetInteger( 'max_page_name_chars' )
        
        page_file_count_display = new_options.GetInteger( 'page_file_count_display' )
        
        import_page_progress_display = new_options.GetBoolean( 'import_page_progress_display' )
        
        page = self.GetPage( index )
        
        page_name = page.GetName()
        
        page_name = page_name.replace( os.linesep, '' )
        
        if len( page_name ) > max_page_name_chars:
            
            page_name = page_name[ : max_page_name_chars ] + '\u2026'
            
        
        num_string = ''
        
        ( num_files, ( num_value, num_range ) ) = page.GetNumFileSummary()
        
        if page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ALL or ( page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS and page.IsImporter() ):
            
            num_string += HydrusData.ToHumanInt( num_files )
            
        
        if import_page_progress_display:
            
            if num_range > 0 and num_value != num_range:
                
                if len( num_string ) > 0:
                    
                    num_string += ', '
                    
                
                num_string += HydrusData.ConvertValueRangeToPrettyString( num_value, num_range )
                
            
        
        if len( num_string ) > 0:
            
            page_name += ' (' + num_string + ')'
            
        
        safe_page_name = self.EscapeMnemonics( page_name )
        
        existing_page_name = self.GetPageText( index )
        
        if existing_page_name not in ( safe_page_name, page_name ):
            
            self.SetPageText( index, safe_page_name )
            
        
    
    def _RenamePage( self, index ):
        
        if index == -1 or index > self.GetPageCount() - 1:
            
            return
            
        
        page = self.GetPage( index )
        
        current_name = page.GetName()
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the new name.', default = current_name, allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_name = dlg.GetValue()
                
                page.SetName( new_name )
                
                self._controller.pub( 'refresh_page_name', page.GetPageKey() )
                
            
        
    
    def _SendPageToNewNotebook( self, index ):
        
        if 0 <= index and index <= self.GetPageCount() - 1:
            
            page = self.GetPage( index )
            
            dest_notebook = self.NewPagesNotebook( forced_insertion_index = index, give_it_a_blank_page = False )
            
            self._MovePage( page, dest_notebook, 0 )
            
        
    
    def _SendRightPagesToNewNotebook( self, from_index ):
        
        message = 'Send all pages to the right to a new page of pages?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                pages_index = self.GetPageCount()
                
                dest_notebook = self.NewPagesNotebook( forced_insertion_index = pages_index, give_it_a_blank_page = False )
                
                movees = list( range( from_index + 1, pages_index ) )
                
                movees.reverse()
                
                for index in movees:
                    
                    page = self.GetPage( index )
                    
                    self._MovePage( page, dest_notebook, 0 )
                    
                
            
        
    
    def _ShiftPage( self, page_index, delta = None, new_index = None ):
        
        new_page_index = page_index
        
        if delta is not None:
            
            new_page_index = page_index + delta
            
        
        if new_index is not None:
            
            new_page_index = new_index
            
        
        if new_page_index == page_index:
            
            return
            
        
        if 0 <= new_page_index and new_page_index <= self.GetPageCount() - 1:
            
            page_is_selected = self.GetSelection() == page_index
            
            page = self.GetPage( page_index )
            name = self.GetPageText( page_index )
            
            self.RemovePage( page_index )
            
            self.InsertPage( new_page_index, page, name, page_is_selected )
            
        
    
    def _ShowMenu( self, screen_position ):
        
        ( tab_index, flags ) = ClientGUIFunctions.NotebookScreenToHitTest( self, screen_position )
        
        num_pages = self.GetPageCount()
        
        end_index = num_pages - 1
        
        more_than_one_tab = num_pages > 1
        
        click_over_tab = tab_index != -1
        
        can_go_left = tab_index > 0
        can_go_right = tab_index < end_index
        
        click_over_page_of_pages = False
        
        menu = wx.Menu()
        
        if click_over_tab:
            
            page = self.GetPage( tab_index )
            
            click_over_page_of_pages = isinstance( page, PagesNotebook )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'close page', 'Close this page.', self._ClosePage, tab_index )
            
            if num_pages > 1:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'close other pages', 'Close all pages but this one.', self._CloseOtherPages, tab_index )
                
                if can_go_left:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'close pages to the left', 'Close all pages to the left of this one.', self._CloseLeftPages, tab_index )
                    
                
                if can_go_right:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'close pages to the right', 'Close all pages to the right of this one.', self._CloseRightPages, tab_index )
                    
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'rename page', 'Rename this page.', self._RenamePage, tab_index )
            
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'new page', 'Choose a new page.', self._ChooseNewPage )
        
        if click_over_tab:
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'new page here', 'Choose a new page.', self._ChooseNewPage, tab_index )
            
            if more_than_one_tab:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                can_home = tab_index > 1
                can_move_left = tab_index > 0
                can_move_right = tab_index < end_index
                can_end = tab_index < end_index - 1
                
                if can_home:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'move to left end', 'Move this page all the way to the left.', self._ShiftPage, tab_index, new_index = 0 )
                    
                
                if can_move_left:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'move left', 'Move this page one to the left.', self._ShiftPage, tab_index, delta = -1 )
                    
                
                if can_move_right:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'move right', 'Move this page one to the right.', self._ShiftPage, tab_index, 1 )
                    
                
                if can_end:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'move to right end', 'Move this page all the way to the right.', self._ShiftPage, tab_index, new_index = end_index )
                    
                
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'sort pages by most files first', 'Sort these pages according to how many files they appear to have.', self._SortPagesByFileCount, 'desc' )
                ClientGUIMenus.AppendMenuItem( self, menu, 'sort pages by fewest files first', 'Sort these pages according to how few files they appear to have.', self._SortPagesByFileCount, 'asc' )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'send this page down to a new page of pages', 'Make a new page of pages and put this page in it.', self._SendPageToNewNotebook, tab_index )
            
            if can_go_right:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'send pages to the right to a new page of pages', 'Make a new page of pages and put all the pages to the right into it.', self._SendRightPagesToNewNotebook, tab_index )
                
            
            if click_over_page_of_pages and page.GetPageCount() > 0:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'refresh all this page\'s pages', 'Command every page below this one to refresh.', page.RefreshAllPages )
                
            
        
        existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
        
        if len( existing_session_names ) > 0 or click_over_page_of_pages:
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        if len( existing_session_names ) > 0:
            
            submenu = wx.Menu()
            
            for name in existing_session_names:
                
                ClientGUIMenus.AppendMenuItem( self, submenu, name, 'Load this session here.', self.AppendGUISession, name )
                
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'append session' )
            
        
        if click_over_page_of_pages:
            
            submenu = wx.Menu()
            
            for name in existing_session_names:
                
                if name in RESERVED_SESSION_NAMES:
                    
                    continue
                    
                
                ClientGUIMenus.AppendMenuItem( self, submenu, name, 'Save this page of pages to the session.', page.SaveGUISession, name )
                
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'create a new session', 'Save this page of pages to the session.', page.SaveGUISession, suggested_name = page.GetName() )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'save this page of pages to a session' )
            
        
        self._controller.PopupMenu( self, menu )
        
    
    def _SortPagesByFileCount( self, order ):
        
        ordered_pages = list( self.GetPages() )
        
        def key( page ):
            
            ( total_num_files, ( total_num_value, total_num_range ) ) = page.GetNumFileSummary()
            
            return ( total_num_files, total_num_range, total_num_value )
            
        
        ordered_pages.sort( key = key )
        
        if order == 'desc':
            
            ordered_pages.reverse()
            
        
        selected_page = self.GetCurrentPage()
        
        pages_to_names = {}
        
        for i in range( self.GetPageCount() ):
            
            page = self.GetPage( 0 )
            
            name = self.GetPageText( 0 )
            
            pages_to_names[ page ] = name
            
            self.RemovePage( 0 )
            
        
        for page in ordered_pages:
            
            is_selected = page == selected_page
            
            name = pages_to_names[ page ]
            
            self.AddPage( page, name, select = is_selected )
            
        
    
    def AppendGUISession( self, name, load_in_a_page_of_pages = True ):
        
        try:
            
            session = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session ' + name + ', this error happened:' )
            HydrusData.ShowException( e )
            
            self.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
            return
            
        
        if load_in_a_page_of_pages:
            
            destination = self.NewPagesNotebook( name = name, give_it_a_blank_page = False)
            
        else:
            
            destination = self
            
        
        page_tuples = session.GetPageTuples()
        
        destination.AppendSessionPageTuples( page_tuples )
        
    
    def AppendGUISessionBackup( self, name, timestamp, load_in_a_page_of_pages = True ):
        
        try:
            
            session = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name, timestamp )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session ' + name + ' (ts ' + str( timestamp ) + ', this error happened:' )
            HydrusData.ShowException( e )
            
            self.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
            return
            
        
        if load_in_a_page_of_pages:
            
            destination = self.NewPagesNotebook( name = name, give_it_a_blank_page = False)
            
        else:
            
            destination = self
            
        
        page_tuples = session.GetPageTuples()
        
        destination.AppendSessionPageTuples( page_tuples )
        
    
    def AppendSessionPageTuples( self, page_tuples ):
        
        starting_index = self._GetDefaultPageInsertionIndex()
        
        forced_insertion_index = starting_index
        
        done_first_page = False
        
        for page_tuple in page_tuples:
            
            ( page_type, page_data ) = page_tuple
            
            if page_type == 'pages':
                
                ( name, subpage_tuples ) = page_data
                
                try:
                    
                    page = self.NewPagesNotebook( name, forced_insertion_index = forced_insertion_index, give_it_a_blank_page = False, select_page = False )
                    
                    page.AppendSessionPageTuples( subpage_tuples )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
            elif page_type == 'page':
                
                ( management_controller, initial_hashes ) = page_data
                
                try:
                    
                    select_page = not done_first_page
                    
                    self.NewPage( management_controller, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index, select_page = select_page )
                    
                    done_first_page = True
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
            
            forced_insertion_index += 1
            
        
    
    def ChooseNewPage( self ):
        
        self._ChooseNewPage()
        
    
    def ChooseNewPageForDeepestNotebook( self ):
        
        current_page = self.GetCurrentPage()
        
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
            
        
        self._controller.ReleasePageKey( self._page_key )
        
    
    def CloseCurrentPage( self, polite = True ):
        
        selection = self.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            page = self.GetPage( selection )
            
            if isinstance( page, PagesNotebook ):
                
                if page.GetNumPages() > 0:
                    
                    page.CloseCurrentPage( polite )
                    
                else:
                    
                    self._ClosePage( selection, polite = polite )
                    
                
            else:
                
                self._ClosePage( selection, polite = polite )
                
            
        
    
    def EventDrag( self, event ):
        
        if event.Dragging() and self._potential_drag_page is not None:
            
            drop_source = wx.DropSource( self._controller.gui )
            
            #
            
            hydrus_page_tab_data_object = wx.CustomDataObject( 'application/hydrus-page-tab' )
            
            data = self._potential_drag_page.GetPageKey()
            
            hydrus_page_tab_data_object.SetData( data )
            
            #
            
            drop_source.SetData( hydrus_page_tab_data_object )
            
            drop_source.DoDragDrop( wx.Drag_DefaultMove )
            
            self._potential_drag_page = None
            
        
        event.Skip()
        
    
    def EventLeftDown( self, event ):
        
        event_skip_ok = True
        
        position = event.GetPosition()
        
        ( tab_index, flags ) = self.HitTest( position )
        
        if tab_index != -1:
            
            page = self.GetPage( tab_index )
            
            if HC.PLATFORM_OSX and page == self.GetCurrentPage():
                
                # drag doesn't work if we allow the event to go ahead
                # but we do want the event to go ahead if it is a 'select different page' event
                
                event_skip_ok = False
                
            
            self._potential_drag_page = page
            
        
        if event_skip_ok:
            
            event.Skip()
            
        
    
    def EventLeftDoubleClick( self, event ):
        
        position = event.GetPosition()
        
        ( tab_index, flags ) = self.HitTest( position )
        
        if tab_index == wx.NOT_FOUND:
            
            if flags & wx.NB_HITTEST_NOWHERE and flags & wx.NB_HITTEST_ONPAGE:
                
                screen_position = ClientGUIFunctions.ClientToScreen( self, position )
                
                notebook = self._GetNotebookFromScreenPosition( screen_position )
                
                notebook.EventNewPageFromScreenPosition( screen_position )
                
            else:
                
                self.ChooseNewPage()
                
            
        else:
            
            event.Skip()
            
        
    
    def EventLeftUp( self, event ):
        
        self._potential_drag_page = None
        
        event.Skip()
        
    
    def EventMenu( self, event ):
        
        screen_position = ClientGUIFunctions.ClientToScreen( self, event.GetPosition() )
        
        self._ShowMenu( screen_position )
        
    
    def EventMenuFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ShowMenu( position )
        
    
    def EventMiddleClick( self, event ):
        
        if self._controller.MenuIsOpen():
            
            return
            
        
        position = event.GetPosition()
        
        ( tab_index, flags ) = self.HitTest( position )
        
        if tab_index == wx.NOT_FOUND:
            
            if flags & wx.NB_HITTEST_NOWHERE and flags & wx.NB_HITTEST_ONPAGE:
                
                screen_position = ClientGUIFunctions.ClientToScreen( self, position )
                
                notebook = self._GetNotebookFromScreenPosition( screen_position )
                
                notebook.EventNewPageFromScreenPosition( screen_position )
                
            else:
                
                self.ChooseNewPage()
                
            
        else:
            
            self._ClosePage( tab_index )
            
        
    
    def EventNewPageFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ChooseNewPage()
        
    
    def EventPageChanged( self, event ):
        
        if event.EventObject == self: # because OS X wants to bump this up to parent notebooks
            
            old_selection = event.GetOldSelection()
            selection = event.GetSelection()
            
            if old_selection != wx.NOT_FOUND:
                
                self.GetPage( old_selection ).PageHidden()
                
            
            if selection != wx.NOT_FOUND:
                
                self.GetPage( selection ).PageShown()
                
            
            self._controller.gui.RefreshStatusBar()
            
        
        if HC.PLATFORM_OSX:
            
            event.Skip() # need this or OS X spergs out and never .Show()s new page, wew
            
        
        self._controller.pub( 'notify_page_change' )
        
    
    def GetCurrentMediaPage( self ):
        
        page = self.GetCurrentPage()
        
        if isinstance( page, PagesNotebook ):
            
            return page.GetCurrentMediaPage()
            
        else:
            
            return page # this can be None
            
        
    
    def GetMediaPages( self, only_my_level = False ):
        
        return self._GetMediaPages( only_my_level )
        
    
    def GetName( self ):
        
        return self._name
        
    
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
        
    
    def GetNumPages( self, only_my_level = False ):
        
        if only_my_level:
            
            return self.GetPageCount()
            
        else:
            
            total = 0
            
            for page in self._GetPages():
                
                if isinstance( page, PagesNotebook ):
                    
                    total += page.GetNumPages( False )
                    
                else:
                    
                    total += 1
                    
                
            
            return total
            
        
    
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
            
        
    
    def GetOrMakeURLImportPage( self, desired_page_name = None, desired_page_key = None, select_page =  True ):
        
        potential_url_import_pages = [ page for page in self._GetMediaPages( False ) if page.IsURLImportPage() ]
        
        if desired_page_key is not None and desired_page_key in ( page.GetPageKey() for page in potential_url_import_pages ):
            
            potential_url_import_pages = [ page for page in potential_url_import_pages if page.GetPageKey() == desired_page_key ]
            
        elif desired_page_name is not None:
            
            potential_url_import_pages = [ page for page in potential_url_import_pages if page.GetName() == desired_page_name ]
            
        
        if len( potential_url_import_pages ) > 0:
            
            # ok, we can use an existing one. should we use the current?
            
            current_media_page = self.GetCurrentMediaPage()
            
            if current_media_page is not None and current_media_page in potential_url_import_pages:
                
                return current_media_page
                
            else:
                
                return potential_url_import_pages[0]
                
            
        else:
            
            return self.NewPageImportURLs( page_name = desired_page_name, on_deepest_notebook = True, select_page = select_page )
            
        
    
    def GetPageFromPageKey( self, page_key ):
        
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
        
    
    def GetPageInfoDict( self, is_selected = True ):
        
        current_page = self.GetCurrentPage()
        
        my_pages_list = []
        
        for page in self._GetPages():
            
            page_is_focused = is_selected and page == current_page
            
            page_info_dict = page.GetPageInfoDict( is_selected = is_selected )
            
            my_pages_list.append( page_info_dict )
            
        
        root = {}
        
        root[ 'name' ] = self.GetName()
        root[ 'page_key' ] = self._page_key.hex()
        root[ 'page_type' ] = ClientGUIManagement.MANAGEMENT_TYPE_PAGE_OF_PAGES
        root[ 'selected' ] = is_selected
        root[ 'pages' ] = my_pages_list
        
        return root
        
    
    def GetPages( self ):
        
        return self._GetPages()
        
    
    def GetPrettyStatus( self ):
        
        ( num_files, ( num_value, num_range ) ) = self.GetNumFileSummary()
        
        num_string = HydrusData.ToHumanInt( num_files )
        
        if num_range > 0 and num_value != num_range:
            
            num_string += ', ' + HydrusData.ConvertValueRangeToPrettyString( num_value, num_range )
            
        
        return HydrusData.ToHumanInt( self.GetPageCount() ) + ' pages, ' + num_string + ' files'
        
    
    def GetTestAbleToCloseStatement( self ):
        
        count = collections.Counter()
        
        for page in self._GetMediaPages( False ):
            
            try:
                
                page.CheckAbleToClose()
                
            except HydrusExceptions.VetoException as e:
                
                reason = str( e )
                
                count[ reason ] += 1
                
            
        
        if len( count ) > 0:
            
            total_problems = sum( count.values() )
            
            message = ''
            
            for ( reason, c ) in list(count.items()):
                
                if c == 1:
                    
                    message = '1 page says: ' + reason
                    
                else:
                    
                    message = HydrusData.ToHumanInt( c ) + ' pages say:' + reason
                    
                
                message += os.linesep
                
            
            return message
            
        else:
            
            return None
            
        
    
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
        
    
    def IsMultipleWatcherPage( self ):
        
        return False
        
    
    def IsImporter( self ):
        
        return False
        
    
    def IsURLImportPage( self ):
        
        return False
        
    
    def LoadGUISession( self, name ):
        
        if self.GetPageCount() > 0:
            
            message = 'Close the current pages and load session "' + name + '"?'
            
            with ClientGUIDialogs.DialogYesNo( self, message, title = 'Clear and load session?' ) as yn_dlg:
                
                if yn_dlg.ShowModal() != wx.ID_YES:
                    
                    return
                    
                
            
            try:
                
                self.TestAbleToClose()
                
            except HydrusExceptions.VetoException:
                
                return
                
            
            self._CloseAllPages( polite = False, delete_pages = True )
            
            self._controller.CallLaterWXSafe( self, 1.0, self.AppendGUISession, name, load_in_a_page_of_pages = False )
            
        else:
            
            self.AppendGUISession( name, load_in_a_page_of_pages = False )
            
        
    
    def MediaDragAndDropDropped( self, source_page_key, hashes ):
        
        source_page = self.GetPageFromPageKey( source_page_key )
        
        if source_page is None:
            
            return
            
        
        screen_position = wx.GetMousePosition()
        
        dest_notebook = self._GetNotebookFromScreenPosition( screen_position )
        
        ( x, y ) = screen_position
        
        ( tab_index, flags ) = ClientGUIFunctions.NotebookScreenToHitTest( dest_notebook, ( x, y ) )
        
        do_add = True
        # do chase - if we need to chase to an existing dest page on which we dropped files
        # do return - if we need to return to source page if we created a new one
        
        if flags & wx.NB_HITTEST_ONPAGE:
            
            dest_page = dest_notebook.GetCurrentPage()
            
        elif tab_index == wx.NOT_FOUND:
            
            dest_page = dest_notebook.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes )
            
            do_add = False
            
        else:
            
            dest_page = dest_notebook.GetPage( tab_index )
            
            if isinstance( dest_page, PagesNotebook ):
                
                result = dest_page.GetCurrentMediaPage()
                
                if result is None:
                    
                    dest_page = dest_page.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes )
                    
                    do_add = False
                    
                else:
                    
                    dest_page = result
                    
                
            
        
        if dest_page is None:
            
            return # we somehow dropped onto a new notebook that has no pages
            
        
        if dest_page.GetPageKey() == source_page_key:
            
            return # we dropped onto the same page we picked up on
            
        
        if do_add:
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            dest_page.GetMediaPanel().AddMediaResults( dest_page.GetPageKey(), media_results )
            
        else:
            
            self.ShowPage( source_page )
            
        
        ctrl_down = wx.GetKeyState( wx.WXK_COMMAND ) or wx.GetKeyState( wx.WXK_CONTROL )
        
        if not ctrl_down:
            
            source_page.GetMediaPanel().RemoveMedia( source_page.GetPageKey(), hashes )
            
        
    
    def NewPage( self, management_controller, initial_hashes = None, forced_insertion_index = None, on_deepest_notebook = False, select_page = True ):
        
        if self.GetTopLevelParent().IsIconized():
            
            return None
            
        
        current_page = self.GetCurrentPage()
        
        if on_deepest_notebook and isinstance( current_page, PagesNotebook ):
            
            return current_page.NewPage( management_controller, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index, on_deepest_notebook = on_deepest_notebook )
            
        
        WARNING_TOTAL_PAGES = self._controller.new_options.GetInteger( 'total_pages_warning' )
        MAX_TOTAL_PAGES = 200
        
        ( total_active_page_count, total_closed_page_count ) = self._controller.gui.GetTotalPageCounts()
        
        if total_active_page_count + total_closed_page_count >= WARNING_TOTAL_PAGES:
            
            self._controller.gui.DeleteAllClosedPages()
            
        
        if not HG.no_page_limit_mode:
            
            if total_active_page_count >= MAX_TOTAL_PAGES:
                
                message = 'The client should not have more than ' + str( MAX_TOTAL_PAGES ) + ' pages open, as it leads to program instability! Are you sure you want to open more pages?'
                
                with ClientGUIDialogs.DialogYesNo( self, message, title = 'Too many pages!', yes_label = 'yes, and do not tell me again', no_label = 'no' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        HG.no_page_limit_mode = True
                        
                        self._controller.pub( 'notify_new_options' )
                        
                    else:
                        
                        return None
                        
                    
                
            
            if total_active_page_count == WARNING_TOTAL_PAGES:
                
                HydrusData.ShowText( 'You have ' + str( total_active_page_count ) + ' pages open! You can only open a few more before program stability is affected! Please close some now!' )
                
            
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        page = Page( self, self._controller, management_controller, initial_hashes )
        
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
        insertion_index = min( insertion_index, self.GetPageCount() )
        
        self.InsertPage( insertion_index, page, page_name, select = select_page )
        
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        self._controller.pub( 'notify_new_pages' )
        
        wx.CallAfter( page.Start )
        
        if select_page:
            
            page.SetSearchFocus()
            
            # this is here for now due to the pagechooser having a double-layer dialog on a booru choice, which messes up some focus inheritance
            
            self._controller.CallLaterWXSafe( self, 0.5, page.SetSearchFocus )
            
        
        return page
        
    
    def NewPageDuplicateFilter( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerDuplicateFilter()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportGallery( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportGallery()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportSimpleDownloader( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportSimpleDownloader()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportMultipleWatcher( self, page_name = None, url = None, on_deepest_notebook = False, select_page = True ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportMultipleWatcher( page_name = page_name, url = url )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPageImportURLs( self, page_name = None, on_deepest_notebook = False, select_page = True ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportURLs( page_name = page_name )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPagePetitions( self, service_key, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerPetitions( service_key )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageQuery( self, file_service_key, initial_hashes = None, initial_predicates = None, page_name = None, on_deepest_notebook = False, do_sort = False, select_page = True ):
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        if initial_predicates is None:
            
            initial_predicates = []
            
        
        if page_name is None:
            
            page_name = 'files'
            
        
        search_enabled = len( initial_hashes ) == 0
        
        new_options = self._controller.new_options
        
        tag_service_key = new_options.GetKey( 'default_tag_service_search_page' )
        
        if not self._controller.services_manager.ServiceExists( tag_service_key ):
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        file_search_context = ClientSearch.FileSearchContext( file_service_key = file_service_key, tag_service_key = tag_service_key, predicates = initial_predicates )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( page_name, file_service_key, file_search_context, search_enabled )
        
        page = self.NewPage( management_controller, initial_hashes = initial_hashes, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
        if do_sort:
            
            HG.client_controller.pub( 'do_page_sort', page.GetPageKey() )
            
        
        return page
        
    
    def NewPagesNotebook( self, name = 'pages', forced_insertion_index = None, on_deepest_notebook = False, give_it_a_blank_page = True, select_page = True ):
        
        current_page = self.GetCurrentPage()
        
        if on_deepest_notebook and isinstance( current_page, PagesNotebook ):
            
            return current_page.NewPagesNotebook( name = name, forced_insertion_index = forced_insertion_index, on_deepest_notebook = on_deepest_notebook, give_it_a_blank_page = give_it_a_blank_page )
            
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        page = PagesNotebook( self, self._controller, name )
        
        if forced_insertion_index is None:
            
            if self._next_new_page_index is None:
                
                insertion_index = self._GetDefaultPageInsertionIndex()
                
            else:
                
                insertion_index = self._next_new_page_index
                
                self._next_new_page_index = None
                
            
        else:
            
            insertion_index = forced_insertion_index
            
        
        page_name = page.GetName()
        
        self.InsertPage( insertion_index, page, page_name, select = select_page )
        
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        
        if give_it_a_blank_page:
            
            page.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
        
        return page
        
    
    def NotifyPageUnclosed( self, page ):
        
        page_key = page.GetPageKey()
        
        for ( index, closed_page_key ) in self._closed_pages:
            
            if page_key == closed_page_key:
                
                page.Show()
                
                insert_index = min( index, self.GetPageCount() )
                
                name = page.GetName()
                
                self.InsertPage( insert_index, page, name, True )
                
                self._controller.pub( 'refresh_page_name', page.GetPageKey() )
                
                self._closed_pages.remove( ( index, closed_page_key ) )
                
                break
                
            
        
    
    def PageHidden( self ):
        
        result = self.GetCurrentPage()
        
        if result is not None:
            
            result.PageHidden()
            
        
    
    def PageShown( self ):
        
        result = self.GetCurrentPage()
        
        if result is not None:
            
            result.PageShown()
            
        
    
    def PageDragAndDropDropped( self, page_key ):
        
        page = self.GetPageFromPageKey( page_key )
        
        if page is None:
            
            return
            
        
        screen_position = wx.GetMousePosition()
        
        dest_notebook = self._GetNotebookFromScreenPosition( screen_position )
        
        ( x, y ) = screen_position
        
        ( tab_index, flags ) = ClientGUIFunctions.NotebookScreenToHitTest( dest_notebook, ( x, y ) )
        
        if flags & wx.NB_HITTEST_ONPAGE:
            
            # was not dropped on label area, so ditch DnD
            
            return
            
        
        if tab_index == wx.NOT_FOUND:
            
            # if it isn't dropped on anything, put it on the end
            
            tab_index = dest_notebook.GetPageCount()
            
            if tab_index > 0:
                
                if dest_notebook.GetPage( tab_index - 1 ) == page:
                    
                    return
                    
                
            
        else:
            
            EDGE_PADDING = 10
            
            ( left_tab_index, gumpf ) = ClientGUIFunctions.NotebookScreenToHitTest( dest_notebook, ( x - EDGE_PADDING, y ) )
            ( right_tab_index, gumpf ) = ClientGUIFunctions.NotebookScreenToHitTest( dest_notebook,  ( x + EDGE_PADDING, y ) )
            
            landed_near_left_edge = left_tab_index != tab_index
            landed_near_right_edge = right_tab_index != tab_index
            
            landed_on_edge = landed_near_right_edge or landed_near_left_edge
            landed_in_middle = not landed_on_edge
            
            there_is_a_page_to_the_left = tab_index > 0
            there_is_a_page_to_the_right = tab_index < dest_notebook.GetPageCount() - 1
            
            page_on_left_is_source = there_is_a_page_to_the_left and dest_notebook.GetPage( tab_index - 1 ) == page
            page_on_right_is_source = there_is_a_page_to_the_right and dest_notebook.GetPage( tab_index + 1 ) == page
            
            # dropped on source and not on the right edge: do nothing
            
            landee_page = dest_notebook.GetPage( tab_index )
            
            if landee_page == page:
                
                if landed_near_right_edge and there_is_a_page_to_the_right:
                    
                    tab_index += 1
                    
                else:
                    
                    return
                    
                
            
            # dropped just to the left of source: do nothing
            
            if landed_near_right_edge and page_on_right_is_source:
                
                return
                
            
            # dropped on left side of an edge: insert on right side
            
            if landed_near_right_edge:
                
                tab_index += 1
                
            
            if landed_in_middle and isinstance( landee_page, PagesNotebook ):
                
                dest_notebook = landee_page
                tab_index = dest_notebook.GetPageCount()
                
            
        
        if dest_notebook == page or ClientGUIFunctions.IsWXAncestor( dest_notebook, page ):
            
            # can't drop a notebook beneath itself!
            return
            
        
        insertion_tab_index = tab_index
        
        shift_down = wx.GetKeyState( wx.WXK_SHIFT )
        
        follow_dropped_page = not shift_down
        
        new_options = HG.client_controller.new_options
        
        if new_options.GetBoolean( 'reverse_page_shift_drag_behaviour' ):
            
            follow_dropped_page = not follow_dropped_page
            
        
        self._MovePage( page, dest_notebook, insertion_tab_index, follow_dropped_page )
        
        self.Refresh()
        
        if dest_notebook != self:
            
            dest_notebook.Refresh()
            
        
    
    def PresentImportedFilesToPage( self, hashes, page_name ):
        
        page = self._GetPageFromName( page_name )
        
        if page is None:
            
            page = self.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes, page_name = page_name, on_deepest_notebook = True, select_page = False )
            
        else:
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            page.GetMediaPanel().AddMediaResults( page.GetPageKey(), media_results )
            
        
        return page
        
    
    def RefreshAllPages( self ):
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                page.RefreshAllPages()
                
            else:
                
                page.RefreshQuery()
                
            
        
    
    def RefreshPageName( self, page_key = None ):
        
        if page_key is None:
            
            for index in range( self.GetPageCount() ):
                
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
                    
                
            
        
    
    def SaveGUISession( self, name = None, suggested_name = '' ):
        
        if name is None:
            
            while True:
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the new session.', default = suggested_name ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        name = dlg.GetValue()
                        
                        if name in RESERVED_SESSION_NAMES:
                            
                            wx.MessageBox( 'Sorry, you cannot have that name! Try another.' )
                            
                        else:
                            
                            existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
                            
                            if name in existing_session_names:
                                
                                message = 'Session \'' + name + '\' already exists! Do you want to overwrite it?'
                                
                                with ClientGUIDialogs.DialogYesNo( self, message, title = 'Overwrite existing session?', yes_label = 'yes, overwrite', no_label = 'no, choose another name' ) as yn_dlg:
                                    
                                    if yn_dlg.ShowModal() != wx.ID_YES:
                                        
                                        continue
                                        
                                    
                                
                            
                            break
                            
                        
                    else:
                        
                        return
                        
                    
                
            
        elif name not in RESERVED_SESSION_NAMES: # i.e. a human asked to do this
            
            message = 'Overwrite this session?'
            
            with ClientGUIDialogs.DialogYesNo( self, message, title = 'Overwrite existing session?', yes_label = 'yes, overwrite', no_label = 'no' ) as yn_dlg:
                
                if yn_dlg.ShowModal() != wx.ID_YES:
                    
                    return
                    
                
            
        
        #
        
        session = GUISession( name )
        
        for page in self._GetPages():
            
            session.AddPageTuple( page )
            
        
        #
        
        if name == 'last session':
            
            session_hash = hashlib.sha256( bytes( session.DumpToString(), 'utf-8' ) ).digest()
            
            if session_hash == self._last_last_session_hash:
                
                return
                
            
            self._last_last_session_hash = session_hash
            
        
        self._controller.WriteSynchronous( 'serialisable', session )
        
        self._controller.pub( 'notify_new_sessions' )
        
    
    def SetName( self, name ):
        
        self._name = name
        
    
    def ShowPage( self, showee ):
        
        for ( i, page ) in enumerate( self._GetPages() ):
            
            if isinstance( page, wx.Notebook ) and page.HasPage( showee ):
                
                self.SetSelection( i )
                
                page.ShowPage( showee )
                
                break
                
            elif page == showee:
                
                self.SetSelection( i )
                
                break
                
            
        
    
    def TestAbleToClose( self ):
        
        statement = self.GetTestAbleToCloseStatement()
        
        if statement is not None:
            
            message = 'Are you sure you want to close this page of pages?'
            message += os.linesep * 2
            message += statement
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
        
    
    def REPEATINGPageUpdate( self ):
        
        pass
        
    
class GUISession( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION
    SERIALISABLE_NAME = 'GUI Session'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._page_tuples = []
        
    
    def _GetPageTuple( self, page ):
        
        if isinstance( page, PagesNotebook ):
            
            name = page.GetName()
            
            page_tuples = [ self._GetPageTuple( subpage ) for subpage in page.GetPages() ]
            
            return ( 'pages', ( name, page_tuples ) )
            
        else:
            
            management_controller = page.GetManagementController()
            
            hashes = list( page.GetHashes() )
            
            return ( 'page', ( management_controller, hashes ) )
            
        
    
    def _GetSerialisableInfo( self ):
        
        def handle_e( e ):
            
            HydrusData.ShowText( 'Attempting to save a page to the session failed! Its data tuple and error follows! Please close it or see if you can clear any potentially invalid data from it!' )
            
            HydrusData.ShowText( page_tuple )
            
            HydrusData.ShowException( e )
            
        
        def GetSerialisablePageTuple( page_tuple ):
            
            ( page_type, page_data ) = page_tuple
            
            if page_type == 'pages':
                
                ( name, page_tuples ) = page_data
                
                serialisable_page_tuples = []
                
                for pt in page_tuples:
                    
                    try:
                        
                        serialisable_page_tuples.append( GetSerialisablePageTuple( pt ) )
                        
                    except Exception as e:
                        
                        handle_e( e )
                        
                    
                
                serialisable_page_data = ( name, serialisable_page_tuples )
                
            elif page_type == 'page':
                
                ( management_controller, hashes ) = page_data
                
                serialisable_management_controller = management_controller.GetSerialisableTuple()
                
                serialisable_hashes = [ hash.hex() for hash in hashes ]
                
                serialisable_page_data = ( serialisable_management_controller, serialisable_hashes )
                
            
            serialisable_tuple = ( page_type, serialisable_page_data )
            
            return serialisable_tuple
            
        
        serialisable_info = []
        
        for page_tuple in self._page_tuples:
            
            try:
                
                serialisable_page_tuple = GetSerialisablePageTuple( page_tuple )
                
                serialisable_info.append( serialisable_page_tuple )
                
            except Exception as e:
                
                handle_e( e )
                
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        def handle_e( e ):
            
            HydrusData.ShowText( 'A page failed to load! Its serialised data and error follows!' )
            
            HydrusData.ShowText( serialisable_page_tuple )
            
            HydrusData.ShowException( e )
            
        
        def GetPageTuple( serialisable_page_tuple ):
            
            ( page_type, serialisable_page_data ) = serialisable_page_tuple
            
            if page_type == 'pages':
                
                ( name, serialisable_page_tuples ) = serialisable_page_data
                
                page_tuples = []
                
                for spt in serialisable_page_tuples:
                    
                    try:
                        
                        page_tuples.append( GetPageTuple( spt ) )
                        
                    except Exception as e:
                        
                        handle_e( e )
                        
                    
                
                page_data = ( name, page_tuples )
                
            elif page_type == 'page':
                
                ( serialisable_management_controller, serialisable_hashes ) = serialisable_page_data
                
                management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
                
                hashes = [ bytes.fromhex( hash ) for hash in serialisable_hashes ]
                
                page_data = ( management_controller, hashes )
                
            
            page_tuple = ( page_type, page_data )
            
            return page_tuple
            
        
        for serialisable_page_tuple in serialisable_info:
            
            try:
                
                page_tuple = GetPageTuple( serialisable_page_tuple )
                
                self._page_tuples.append( page_tuple )
                
            except Exception as e:
                
                handle_e( e )
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            new_serialisable_info = []
            
            for ( page_name, serialisable_management_controller, serialisable_hashes ) in old_serialisable_info:
                
                management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
                
                management_controller.SetPageName( page_name )
                
                serialisable_management_controller = management_controller.GetSerialisableTuple()
                
                new_serialisable_info.append( ( serialisable_management_controller, serialisable_hashes ) )
                
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            new_serialisable_info = []
            
            for ( serialisable_management_controller, serialisable_hashes ) in old_serialisable_info:
                
                new_serialisable_info.append( ( 'page', ( serialisable_management_controller, serialisable_hashes ) ) )
                
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            def clean_tuple( spt ):
                
                ( page_type, serialisable_page_data ) = spt
                
                if page_type == 'pages':
                    
                    ( name, pages_serialisable_page_tuples ) = serialisable_page_data
                    
                    if name.startswith( '[USER]' ) and len( name ) > 6:
                        
                        name = name[6:]
                        
                    
                    pages_serialisable_page_tuples = [ clean_tuple( pages_spt ) for pages_spt in pages_serialisable_page_tuples ]
                    
                    return ( 'pages', ( name, pages_serialisable_page_tuples ) )
                    
                else:
                    
                    return spt
                    
                
            
            new_serialisable_info = []
            
            serialisable_page_tuples = old_serialisable_info
            
            for serialisable_page_tuple in serialisable_page_tuples:
                
                serialisable_page_tuple = clean_tuple( serialisable_page_tuple )
                
                new_serialisable_info.append( serialisable_page_tuple )
                
            
            return ( 4, new_serialisable_info )
            
        
    
    def AddPageTuple( self, page ):
        
        page_tuple = self._GetPageTuple( page )
        
        self._page_tuples.append( page_tuple )
        
    
    def GetPageTuples( self ):
        
        return self._page_tuples
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION ] = GUISession
