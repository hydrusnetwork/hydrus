import HydrusConstants as HC
import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIManagement
import ClientGUIMedia
import ClientGUIMenus
import ClientGUICanvas
import ClientDownloading
import ClientSearch
import HydrusData
import HydrusExceptions
import HydrusSerialisable
import HydrusThreading
import inspect
import os
import sys
import time
import traceback
import wx
import HydrusGlobals as HG

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
        
        gridbox = wx.GridSizer( 0, 3 )
        
        gridbox.AddF( self._button_7, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._button_8, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._button_9, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._button_4, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._button_5, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._button_6, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._button_1, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._button_2, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._button_3, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
            
        elif entry_type == 'page_import_booru':
            
            button.SetLabelText( 'booru' )
            
        elif entry_type == 'page_import_gallery':
            
            site_type = obj
            
            text = HC.site_type_string_lookup[ site_type ]
            
            button.SetLabelText( text )
            
        elif entry_type == 'page_import_page_of_images':
            
            button.SetLabelText( 'page of images' )
            
        elif entry_type == 'page_import_thread_watcher':
            
            button.SetLabelText( 'thread watcher' )
            
        elif entry_type == 'page_import_urls':
            
            button.SetLabelText( 'raw urls' )
            
        
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
                    
                    new_options = self._controller.GetNewOptions()
                    
                    tag_service_key = new_options.GetKey( 'default_tag_service_search_page' )
                    
                    if not self._controller.services_manager.ServiceExists( tag_service_key ):
                        
                        tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
                        
                    
                    file_search_context = ClientSearch.FileSearchContext( file_service_key = file_service_key, tag_service_key = tag_service_key )
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerQuery( page_name, file_service_key, file_search_context, search_enabled ) )
                    
                elif entry_type == 'page_duplicate_filter':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerDuplicateFilter() )
                    
                elif entry_type == 'pages_notebook':
                    
                    self._result = ( 'pages', None )
                    
                elif entry_type == 'page_import_booru':
                    
                    with ClientGUIDialogs.DialogSelectBooru( self ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            gallery_identifier = dlg.GetGalleryIdentifier()
                            
                            self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportGallery( gallery_identifier ) )
                            
                        else:
                            
                            self.EndModal( wx.ID_CANCEL )
                            
                            return
                            
                        
                    
                elif entry_type == 'page_import_gallery':
                    
                    site_type = obj
                    
                    gallery_identifier = ClientDownloading.GalleryIdentifier( site_type )
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportGallery( gallery_identifier ) )
                    
                elif entry_type == 'page_import_page_of_images':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportPageOfImages() )
                    
                elif entry_type == 'page_import_thread_watcher':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportThreadWatcher() )
                    
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
            entries.append( ( 'page_query', CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
            
            for service in self._services:
                
                if service.GetServiceType() == HC.FILE_REPOSITORY:
                    
                    entries.append( ( 'page_query', service.GetServiceKey() ) )
                    
                
            
        elif menu_keyword == 'download':
            
            entries.append( ( 'page_import_urls', None ) )
            entries.append( ( 'page_import_thread_watcher', None ) )
            entries.append( ( 'menu', 'gallery' ) )
            entries.append( ( 'page_import_page_of_images', None ) )
            
        elif menu_keyword == 'gallery':
            
            entries.append( ( 'page_import_booru', None ) )
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_DEVIANT_ART ) )
            entries.append( ( 'menu', 'hentai foundry' ) )
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_NEWGROUNDS ) )
            
            result = HG.client_controller.Read( 'serialisable_simple', 'pixiv_account' )
            
            if result is not None:
                
                entries.append( ( 'menu', 'pixiv' ) )
                
            
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_TUMBLR ) )
            
        elif menu_keyword == 'hentai foundry':
            
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST ) )
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS ) )
            
        elif menu_keyword == 'pixiv':
            
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_PIXIV_ARTIST_ID ) )
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_PIXIV_TAG ) )
            
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
            
        
        for entry in entries: self._AddEntry( potential_buttons.pop( 0 ), entry )
        
        unused_buttons = potential_buttons
        
        for button in unused_buttons: button.Hide()
        
    
    def EventButton( self, event ):
        
        id = event.GetId()
        
        if id == wx.ID_CANCEL:
            
            self.EndModal( wx.ID_CANCEL )
            
        else:
            
            self._HitButton( id )
            
        
    
    def EventCharHook( self, event ):
        
        id = None
        
        ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
        
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
        
        self._page_key = HydrusData.GenerateKey()
        
        self._controller = controller
        
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
        self._controller.sub( self, 'SwapMediaPanel', 'swap_media_panel' )
        
    
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
        
    
    def GetName( self ):
        
        return self._management_controller.GetPageName()
        
    
    def GetNumFiles( self ):
        
        if self._initialised:
            
            return self._media_panel.GetNumFiles()
            
        else:
            
            return len( self._initial_hashes )
            
        
    
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
        
    
    def IsImporter( self ):
        
        return self._management_controller.IsImporter()
        
    
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
        
        self._management_panel.Start()
        
    
    def SetName( self, name ):
        
        return self._management_controller.SetPageName( name )
        
    
    def SetPrettyStatus( self, page_key, status ):
        
        if page_key == self._page_key:
            
            if self._initialised:
                
                self._SetPrettyStatus( status )
                
            
        
    
    def SetSearchFocus( self ):
        
        self._controller.pub( 'set_search_focus', self._page_key )
        
    
    def SetSynchronisedWait( self ):
        
        self._controller.pub( 'synchronised_wait_switch', self._page_key )
        
    
    def Start( self ):
        
        if self._initial_hashes is not None and len( self._initial_hashes ) > 0:
            
            self._controller.CallToThread( self.THREADLoadInitialMediaResults )
            
        else:
            
            self._initialised = True
            
            self._management_panel.Start()
            
        
    
    def SwapMediaPanel( self, page_key, new_panel ):
        
        if page_key == self._page_key:
            
            self._SwapMediaPanel( new_panel )
            
            self._controller.pub( 'refresh_page_name', self._page_key )
            
        
    
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
        
    
class PagesNotebook( wx.Notebook ):
    
    def __init__( self, parent, controller, name ):
        
        wx.Notebook.__init__( self, parent )
        
        self._controller = controller
        
        self._name = name
        
        self._next_new_page_index = None
        
        self._potential_drag_page = None
        
        self._closed_pages = []
        
        self._page_key = HydrusData.GenerateKey()
        
        self._controller.sub( self, 'RefreshPageName', 'refresh_page_name' )
        self._controller.sub( self, 'NotifyPageUnclosed', 'notify_page_unclosed' )
        
        if HC.PLATFORM_WINDOWS:
            
            self.Bind( wx.EVT_MOTION, self.EventDrag )
            
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
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
                    
                
            
        
    
    def _CloseAllPages( self, polite = True ):
        
        closees = [ index for index in range( self.GetPageCount() ) ]
        
        self._ClosePages( closees, polite )
        
    
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
                
            
        
    
    def _ClosePage( self, index, polite = True ):
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        if index == -1 or index > self.GetPageCount() - 1:
            
            return False
            
        
        page = self.GetPage( index )
        
        if polite:
            
            try:
                
                page.TestAbleToClose()
                
            except HydrusExceptions.PermissionException:
                
                return False
                
            
        
        page.PrepareToHide()
        
        page_key = page.GetPageKey()
        
        self._closed_pages.append( ( index, page_key ) )
        
        self.RemovePage( index )
        
        self._controller.pub( 'refresh_page_name', self._page_key )
        
        self._controller.pub( 'notify_closed_page', page )
        self._controller.pub( 'notify_new_undo' )
        
        return True
        
    
    def _ClosePages( self, indices, polite = True ):
        
        indices = list( indices )
        
        indices.sort( reverse = True ) # so we are closing from the end first
        
        for index in indices:
            
            successful = self._ClosePage( index, polite )
            
            if not successful:
                
                break
                
            
        
    
    def _CloseRightPages( self, from_index ):
        
        message = 'Close all pages to the right?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                closees = [ index for index in range( self.GetPageCount() ) if index > from_index ]
                
                self._ClosePages( closees )
                
            
        
    
    def _GetDefaultPageInsertionIndex( self ):
        
        new_options = self._controller.GetNewOptions()
        
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
            
            position = self.ScreenToClient( screen_position )
            
            ( tab_index, flags ) = self.HitTest( position )
            
            if tab_index != wx.NOT_FOUND:
                
                return self
                
            
            if flags & wx.NB_HITTEST_NOWHERE and flags & wx.NB_HITTEST_ONPAGE: # not on a label but inside my client area
                
                return current_page._GetNotebookFromScreenPosition( screen_position )
                
            
        
        return self
        
    
    def _GetPages( self ):
        
        return [ self.GetPage( i ) for i in range( self.GetPageCount() ) ]
        
    
    def _GetPageFromPageKey( self, page_key ):
        
        for page in self._GetPages():
            
            if page.GetPageKey() == page_key:
                
                return page
                
            
            if isinstance( page, PagesNotebook ):
                
                if page.HasPageKey( page_key ):
                    
                    return page._GetPageFromPageKey( page_key )
                    
                
            
        
        return None
        
    
    def _MovePage( self, page_index, delta = None, new_index = None ):
        
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
            
        
    
    def _RefreshPageName( self, index ):
        
        if index == -1 or index > self.GetPageCount() - 1:
            
            return
            
        
        new_options = self._controller.GetNewOptions()
        
        max_page_name_chars = new_options.GetInteger( 'max_page_name_chars' )
        
        page_file_count_display = new_options.GetInteger( 'page_file_count_display' )
        
        page = self.GetPage( index )
        
        page_name = page.GetName()
        
        if len( page_name ) > max_page_name_chars:
            
            page_name = page_name[ : max_page_name_chars ] + u'\u2026'
            
        
        if page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ALL or ( page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS and page.IsImporter() ):
            
            num_files = page.GetNumFiles()
            
            page_name += ' (' + HydrusData.ConvertIntToPrettyString( num_files ) + ')'
            
        
        if self.GetPageText( index ) != page_name:
            
            self.SetPageText( index, page_name )
            
        
    
    def _RenamePage( self, index ):
        
        if index == -1 or index > self.GetPageCount() - 1:
            
            return
            
        
        page = self.GetPage( index )
        
        current_name = page.GetName()
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the new name.', default = current_name, allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_name = dlg.GetValue()
                
                new_name = self.EscapeMnemonics( new_name )
                
                page.SetName( new_name )
                
                self._controller.pub( 'refresh_page_name', page.GetPageKey() )
                
            
        
    
    def _ShowMenu( self, screen_position ):
        
        position = self.ScreenToClient( screen_position )
        
        ( tab_index, flags ) = self.HitTest( position )
        
        num_pages = self.GetPageCount()
        
        click_over_tab = tab_index != -1
        
        end_index = num_pages - 1
        
        menu = wx.Menu()
        
        if tab_index != -1:
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'close page', 'Close this page.', self._ClosePage, tab_index )
            
            if num_pages > 1:
                
                can_close_left = tab_index > 0
                can_close_right = tab_index < end_index
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'close other pages', 'Close all pages but this one.', self._CloseOtherPages, tab_index )
                
                if can_close_left:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'close pages to the left', 'Close all pages to the left of this one.', self._CloseLeftPages, tab_index )
                    
                
                if can_close_right:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'close pages to the right', 'Close all pages to the right of this one.', self._CloseRightPages, tab_index )
                    
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'rename page', 'Rename this page.', self._RenamePage, tab_index )
            
            more_than_one_tab = num_pages > 1
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'new page', 'Choose a new page.', self._ChooseNewPage )
        
        if click_over_tab:
            
            if more_than_one_tab:
                
                can_home = tab_index > 1
                can_move_left = tab_index > 0
                can_move_right = tab_index < end_index
                can_end = tab_index < end_index - 1
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'new page here', 'Choose a new page.', self._ChooseNewPage, tab_index )
                
                ClientGUIMenus.AppendSeparator( menu )
                
                if can_home:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'move to left end', 'Move this page all the way to the left.', self._MovePage, tab_index, new_index = 0 )
                    
                
                if can_move_left:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'move left', 'Move this page one to the left.', self._MovePage, tab_index, delta = -1 )
                    
                
                if can_move_right:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'move right', 'Move this page one to the right.', self._MovePage, tab_index, 1 )
                    
                
                if can_end:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'move to right end', 'Move this page all the way to the right.', self._MovePage, tab_index, new_index = end_index )
                    
                
            
        
        self._controller.PopupMenu( self, menu )
        
    
    def AppendGUISession( self, name ):
        
        try:
            
            session = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session ' + name + ', this error happened:' )
            HydrusData.ShowException( e )
            
            self.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
            return
            
        
        page_tuples = session.GetPages()
        
        self.AppendSessionPageTuples( page_tuples )
        
    
    def AppendSessionPageTuples( self, page_tuples ):
        
        starting_index = self._GetDefaultPageInsertionIndex()
        
        forced_insertion_index = starting_index
        
        for page_tuple in page_tuples:
            
            ( page_type, page_data ) = page_tuple
            
            if page_type == 'pages':
                
                ( name, subpage_tuples ) = page_data
                
                try:
                    
                    page = self.NewPagesNotebook( name, forced_insertion_index )
                    
                    page.AppendSessionPageTuples( subpage_tuples )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
                # append the tuples
                
            elif page_type == 'page':
                
                ( management_controller, initial_hashes ) = page_data
                
                try:
                    
                    self.NewPage( management_controller, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index )
                    
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
            
        
    
    def CleanBeforeDestroy( self ):
        
        for page in self._GetPages():
            
            page.CleanBeforeDestroy()
            
        
    
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
        
        if event.LeftIsDown() and self._potential_drag_page is not None:
            
            drop_source = wx.DropSource( self )
            
            data_object = wx.DataObjectComposite()
            
            #
            
            hydrus_page_tab_data_object = wx.CustomDataObject( 'application/hydrus-page-tab' )
            
            data = self._potential_drag_page.GetPageKey()
            
            hydrus_page_tab_data_object.SetData( data )
            
            data_object.Add( hydrus_page_tab_data_object, True )
            
            #
            
            drop_source.SetData( data_object )
            
            drop_source.DoDragDrop()
            
            self._potential_drag_page = None
            
        
    
    def EventLeftDown( self, event ):
        
        position = event.GetPosition()
        
        ( tab_index, flags ) = self.HitTest( position )
        
        if tab_index != -1:
            
            page = self.GetPage( tab_index )
            
            self._potential_drag_page = page
            
        
        event.Skip()
        
    
    def EventLeftDoubleClick( self, event ):
        
        position = event.GetPosition()
        
        ( tab_index, flags ) = self.HitTest( position )
        
        if tab_index == wx.NOT_FOUND:
            
            if flags & wx.NB_HITTEST_NOWHERE and flags & wx.NB_HITTEST_ONPAGE:
                
                screen_position = self.ClientToScreen( position )
                
                notebook = self._GetNotebookFromScreenPosition( screen_position )
                
                notebook.EventNewPageFromScreenPosition( screen_position )
                
            else:
                
                self.ChooseNewPage()
                
            
        
    
    def EventMenu( self, event ):
        
        screen_position = self.ClientToScreen( event.GetPosition() )
        
        self._ShowMenu( screen_position )
        
    
    def EventMenuFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ShowMenu( position )
        
    
    def EventMiddleClick( self, event ):
        
        position = event.GetPosition()
        
        ( tab_index, flags ) = self.HitTest( position )
        
        if tab_index == wx.NOT_FOUND:
            
            if flags & wx.NB_HITTEST_NOWHERE and flags & wx.NB_HITTEST_ONPAGE:
                
                screen_position = self.ClientToScreen( position )
                
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
        
    
    def GetNumFiles( self ):
        
        return sum( page.GetNumFiles() for page in self._GetPages() )
        
    
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
            
        
    
    def GetOrMakeURLImportPage( self ):
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                if page.HasURLImportPage():
                    
                    return page.GetOrMakeURLImportPage()
                    
                
            elif page.IsURLImportPage():
                
                return page
                
            
        
        # import page does not exist
        
        return self.NewPageImportURLs( on_deepest_notebook = True )
        
    
    def GetPageKey( self ):
        
        return self._page_key
        
    
    def GetPages( self ):
        
        return self._GetPages()
        
    
    def GetPrettyStatus( self ):
        
        return HydrusData.ConvertIntToPrettyString( self.GetPageCount() ) + ' pages, ' + HydrusData.ConvertIntToPrettyString( self.GetNumFiles() ) + ' files'
        
    
    def HasPage( self, page ):
        
        return self.HasPageKey( page.GetPageKey() )
        
    
    def HasPageKey( self, page_key ):
        
        for page in self._GetPages():
            
            if page.GetPageKey() == page_key:
                
                return True
                
            elif isinstance( page, PagesNotebook ) and page.HasPageKey( page_key ):
                
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
        
    
    def LoadGUISession( self, name ):
        
        try:
            
            self.TestAbleToClose()
            
        except HydrusExceptions.PermissionException:
            
            return
            
        
        self._CloseAllPages( polite = False )
        
        self.AppendGUISession( name )
        
    
    def NewPage( self, management_controller, initial_hashes = None, forced_insertion_index = None, on_deepest_notebook = False ):
        
        current_page = self.GetCurrentPage()
        
        if on_deepest_notebook and isinstance( current_page, PagesNotebook ):
            
            current_page.NewPage( management_controller, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index, on_deepest_notebook = on_deepest_notebook )
            
            return
            
        
        if not HG.no_page_limit_mode:
            
            MAX_TOTAL_PAGES = 150
            
            ( total_active_page_count, total_closed_page_count ) = self._controller.gui.GetTotalPageCounts()
            
            if total_active_page_count + total_closed_page_count >= MAX_TOTAL_PAGES:
                
                self._controller.gui.DeleteAllClosedPages()
                
            
            if total_active_page_count >= MAX_TOTAL_PAGES:
                
                HydrusData.ShowText( 'The client cannot have more than ' + str( MAX_TOTAL_PAGES ) + ' pages open! For system stability reasons, please close some now!' )
                
                return
                
            
            if total_active_page_count == MAX_TOTAL_PAGES - 5:
                
                HydrusData.ShowText( 'You have ' + str( total_active_page_count ) + ' pages open! You can only open a few more before system stability is affected! Please close some now!' )
                
            
        
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
            
        
        page_name = 'page'
        
        self.InsertPage( insertion_index, page, page_name, select = True )
        
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        
        wx.CallAfter( page.Start )
        wx.CallAfter( page.SetSearchFocus )
        
        return page
        
    
    def NewPageDuplicateFilter( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerDuplicateFilter()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportBooru( self, on_deepest_notebook = False ):
        
        with ClientGUIDialogs.DialogSelectBooru( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                gallery_identifier = dlg.GetGalleryIdentifier()
                
                return self.NewPageImportGallery( gallery_identifier, on_deepest_notebook = on_deepest_notebook )
                
            
        
    
    def NewPageImportGallery( self, gallery_identifier, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportGallery( gallery_identifier )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportPageOfImages( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportPageOfImages()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportThreadWatcher( self, thread_url = None, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportThreadWatcher( thread_url )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportURLs( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportURLs()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPagePetitions( self, service_key, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerPetitions( service_key )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageQuery( self, file_service_key, initial_hashes = None, initial_predicates = None, page_name = None, on_deepest_notebook = False ):
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        if initial_predicates is None:
            
            initial_predicates = []
            
        
        if page_name is None:
            
            page_name = 'files'
            
        
        search_enabled = len( initial_hashes ) == 0
        
        new_options = self._controller.GetNewOptions()
        
        tag_service_key = new_options.GetKey( 'default_tag_service_search_page' )
        
        if not self._controller.services_manager.ServiceExists( tag_service_key ):
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        file_search_context = ClientSearch.FileSearchContext( file_service_key = file_service_key, tag_service_key = tag_service_key, predicates = initial_predicates )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( page_name, file_service_key, file_search_context, search_enabled )
        
        return self.NewPage( management_controller, initial_hashes = initial_hashes, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPagesNotebook( self, name = 'pages', forced_insertion_index = None, on_deepest_notebook = False ):
        
        current_page = self.GetCurrentPage()
        
        if on_deepest_notebook and isinstance( current_page, PagesNotebook ):
            
            current_page.NewPagesNotebook( name = name, forced_insertion_index = forced_insertion_index, on_deepest_notebook = on_deepest_notebook )
            
            return
            
        
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
            
        
        page_name = 'pages'
        
        self.InsertPage( insertion_index, page, page_name, select = True )
        
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        
        return page
        
    
    def NotifyPageUnclosed( self, page ):
        
        page_key = page.GetPageKey()
        
        for ( index, closed_page_key ) in self._closed_pages:
            
            if page_key == closed_page_key:
                
                page.Show()
                
                index = min( index, self.GetPageCount() )
                
                name = page.GetName()
                
                self.InsertPage( index, page, name, True )
                
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
        
        page = self._GetPageFromPageKey( page_key )
        
        if page is None:
            
            return
            
        
        source_notebook = page.GetParent()
        
        screen_position = wx.GetMousePosition()
        
        dest_notebook = self._GetNotebookFromScreenPosition( screen_position )
        
        ( x, y ) = dest_notebook.ScreenToClient( screen_position )
        
        ( tab_index, flags ) = dest_notebook.HitTest( ( x, y ) )
        
        EDGE_PADDING = 10
        
        ( left_tab_index, gumpf ) = dest_notebook.HitTest( ( x - EDGE_PADDING, y ) )
        ( right_tab_index, gumpf ) = dest_notebook.HitTest( ( x + EDGE_PADDING, y ) )
        
        landed_near_left_edge = left_tab_index != tab_index
        landed_near_right_edge = right_tab_index != tab_index
        
        landed_on_edge = landed_near_right_edge or landed_near_left_edge
        landed_in_middle = not landed_on_edge
        
        there_is_a_page_to_the_left = tab_index > 0
        there_is_a_page_to_the_right = tab_index < dest_notebook.GetPageCount() - 1
        
        page_on_left_is_source = there_is_a_page_to_the_left and dest_notebook.GetPage( tab_index - 1 ) == page
        page_on_right_is_source = there_is_a_page_to_the_right and dest_notebook.GetPage( tab_index + 1 ) == page
        
        if tab_index == wx.NOT_FOUND:
            
            # if it isn't dropped on anything, put it on the end
            
            tab_index = dest_notebook.GetPageCount()
            
            if tab_index > 0:
                
                if dest_notebook.GetPage( tab_index - 1 ) == page:
                    
                    return
                    
                
            
        else:
            
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
                
            
        
        if dest_notebook == page or ClientGUICommon.IsWXAncestor( dest_notebook, page ):
            
            # can't drop a notebook beneath itself!
            return
            
        
        #
        
        insertion_tab_index = tab_index
        
        for ( index, p ) in enumerate( source_notebook._GetPages() ):
            
            if p == page:
                
                if source_notebook == dest_notebook and index + 1 < insertion_tab_index:
                    
                    # we are just about to remove it from earlier in the same list, which shuffles the inserting index up one
                    
                    insertion_tab_index -= 1
                    
                
                source_notebook.RemovePage( index )
                
                break
                
            
        
        if source_notebook != dest_notebook:
            
            page.Reparent( dest_notebook )
            
        
        dest_notebook.InsertPage( insertion_tab_index, page, 'page' )
        
        self.ShowPage( page )
        
        self._controller.pub( 'refresh_page_name', source_notebook.GetPageKey() )
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        
    
    def PrepareToHide( self ):
        
        for page in self._GetPages():
            
            page.PrepareToHide()
            
        
    
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
                    
                
            
        
    
    def SaveGUISession( self, name = None ):
        
        if name is None:
            
            while True:
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the new session.' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        name = dlg.GetValue()
                        
                        if name in ( 'just a blank page', 'last session' ):
                            
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
                        
                    
                
            
        
        session = GUISession( name )
        
        for page in self._GetPages():
            
            session.AddPage( page )
            
        
        self._controller.Write( 'serialisable', session )
        
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
        
        for page in self._GetPages():
            
            page.TestAbleToClose()
            
        
    
class GUISession( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION
    SERIALISABLE_VERSION = 3
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._pages = []
        
    
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
        
        def GetSerialisablePageTuple( page_tuple ):
            
            ( page_type, page_data ) = page_tuple
            
            if page_type == 'pages':
                
                ( name, page_tuples ) = page_data
                
                serialisable_page_tuples = [ GetSerialisablePageTuple( pt ) for pt in page_tuples ]
                
                serialisable_page_data = ( name, serialisable_page_tuples )
                
            elif page_type == 'page':
                
                ( management_controller, hashes ) = page_data
                
                serialisable_management_controller = management_controller.GetSerialisableTuple()
                
                serialisable_hashes = [ hash.encode( 'hex' ) for hash in hashes ]
                
                serialisable_page_data = ( serialisable_management_controller, serialisable_hashes )
                
            
            serialisable_tuple = ( page_type, serialisable_page_data )
            
            return serialisable_tuple
            
        
        serialisable_info = []
        
        for page_tuple in self._pages:
            
            serialisable_page_tuple = GetSerialisablePageTuple( page_tuple )
            
            serialisable_info.append( serialisable_page_tuple )
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        def GetPageTuple( serialisable_page_tuple ):
            
            ( page_type, serialisable_page_data ) = serialisable_page_tuple
            
            if page_type == 'pages':
                
                ( name, serialisable_page_tuples ) = serialisable_page_data
                
                page_tuples = [ GetPageTuple( spt ) for spt in serialisable_page_tuples ]
                
                page_data = ( name, page_tuples )
                
            elif page_type == 'page':
                
                ( serialisable_management_controller, serialisable_hashes ) = serialisable_page_data
                
                management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
                
                hashes = [ hash.decode( 'hex' ) for hash in serialisable_hashes ]
                
                page_data = ( management_controller, hashes )
                
            
            page_tuple = ( page_type, page_data )
            
            return page_tuple
            
        
        for serialisable_page_tuple in serialisable_info:
            
            page_tuple = GetPageTuple( serialisable_page_tuple )
            
            self._pages.append( page_tuple )
            
        
    
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
            
        
    
    def AddPage( self, page ):
        
        page_tuple = self._GetPageTuple( page )
        
        self._pages.append( page_tuple )
        
    
    def GetPages( self ):
        
        return self._pages
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION ] = GUISession
