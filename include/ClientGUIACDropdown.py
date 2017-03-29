import ClientCaches
import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIListBoxes
import ClientGUIMenus
import ClientSearch
import collections
import HydrusConstants as HC
import HydrusExceptions
import HydrusGlobals
import HydrusTags
import itertools
import wx

ID_TIMER_DROPDOWN_HIDE = wx.NewId()
ID_TIMER_AC_LAG = wx.NewId()

# much of this is based on the excellent TexCtrlAutoComplete class by Edward Flick, Michele Petrazzo and Will Sadkin, just with plenty of simplification and integration into hydrus
class AutoCompleteDropdown( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._intercept_key_events = True
        
        self._last_search_text = ''
        self._next_updatelist_is_probably_fast = False
        
        tlp = self.GetTopLevelParent()
        
        # There's a big bug in wx where FRAME_FLOAT_ON_PARENT Frames don't get passed their mouse events if their parent is a Dialog jej
        # I think it is something to do with the initialisation order; if the frame is init'ed before the ShowModal call, but whatever.
        
        # This turned out to be ugly when I added the manage tags frame, so I've set it to if the tlp has a parent, which basically means "not the main gui"
        
        if tlp.GetParent() is not None  or HC.options[ 'always_embed_autocompletes' ]:
            
            self._float_mode = False
            
        else:
            
            self._float_mode = True
            
        
        self._text_ctrl = wx.TextCtrl( self, style=wx.TE_PROCESS_ENTER )
        
        self._text_ctrl.SetBackgroundColour( wx.Colour( *HC.options[ 'gui_colours' ][ 'autocomplete_background' ] ) )
        
        self._last_attempted_dropdown_width = 0
        self._last_attempted_dropdown_position = ( None, None )
        
        if self._float_mode:
            
            self._text_ctrl.Bind( wx.EVT_SET_FOCUS, self.EventSetFocus )
            self._text_ctrl.Bind( wx.EVT_KILL_FOCUS, self.EventKillFocus )
            
        
        self._text_ctrl.Bind( wx.EVT_TEXT, self.EventText )
        self._text_ctrl.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._text_ctrl.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._text_ctrl, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #self._dropdown_window = wx.PopupWindow( self, flags = wx.BORDER_RAISED )
        #self._dropdown_window = wx.PopupTransientWindow( self, style = wx.BORDER_RAISED )
        #self._dropdown_window = wx.Window( self, style = wx.BORDER_RAISED )
        
        #self._dropdown_window = wx.Panel( self )
        
        if self._float_mode:
            
            self._dropdown_window = wx.Frame( self, style = wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_RAISED )
            
            self._dropdown_window.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
            
            self._dropdown_window.SetSize( ( 0, 0 ) )
            
            self._dropdown_window.SetPosition( self._text_ctrl.ClientToScreenXY( 0, 0 ) )
            
            self._dropdown_window.Show()
            
            self._dropdown_window.Bind( wx.EVT_CLOSE, self.EventCloseDropdown )
            
            self._dropdown_hidden = True
            
            self._list_height = 250
            
        else:
            
            self._dropdown_window = wx.Panel( self )
            
            self._list_height = 125
            
        
        self._dropdown_list = self._InitDropDownList()
        
        if not self._float_mode: vbox.AddF( self._dropdown_window, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._cache_text = None
        self._cached_results = []
        
        self._initial_matches_fetched = False
        
        if self._float_mode:
            
            self.Bind( wx.EVT_MOVE, self.EventMove )
            self.Bind( wx.EVT_SIZE, self.EventMove )
            
            self.Bind( wx.EVT_TIMER, self.TIMEREventDropdownHide, id = ID_TIMER_DROPDOWN_HIDE )
            
            self._move_hide_timer = wx.Timer( self, id = ID_TIMER_DROPDOWN_HIDE )
            
            self._move_hide_timer.Start( 1, wx.TIMER_ONE_SHOT )
            
            tlp.Bind( wx.EVT_MOVE, self.EventMove )
            
            parent = self
            
            while True:
                
                try:
                    
                    parent = parent.GetParent()
                    
                    if isinstance( parent, wx.ScrolledWindow ):
                        
                        parent.Bind( wx.EVT_SCROLLWIN, self.EventMove )
                        
                    
                except:
                    
                    break
                    
                
            
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventLag, id = ID_TIMER_AC_LAG )
        
        self._lag_timer = wx.Timer( self, id = ID_TIMER_AC_LAG )
        
        wx.CallAfter( self._UpdateList )
        
    
    def _BroadcastChoices( self, predicates ):
        
        raise NotImplementedError()
        
    
    def _BroadcastCurrentText( self ):
        
        text = self._text_ctrl.GetValue()
        
        self._BroadcastChoices( { text } )
        
    
    def _GenerateMatches( self ):
        
        raise NotImplementedError()
        
    
    def _HideDropdown( self ):
        
        if not self._dropdown_hidden:
            
            self._dropdown_window.SetSize( ( 0, 0 ) )
            
            self._dropdown_hidden = True
            
        
    
    def _InitDropDownList( self ):
        
        raise NotImplementedError()
        
    
    def _ShouldShow( self ):
        
        tlp_active = self.GetTopLevelParent().IsActive() or self._dropdown_window.IsActive()
        
        if HC.PLATFORM_LINUX:
            
            tlp = self.GetTopLevelParent()
            
            if isinstance( tlp, wx.Dialog ):
                
                visible = True
                
            else:
                
                # notebook on linux doesn't 'hide' things apparently, so isshownonscreen, which recursively tests parents' hide status, doesn't work!
                
                gui = HydrusGlobals.client_controller.GetGUI()
                
                current_page = gui.GetCurrentPage()
                
                visible = ClientGUICommon.IsWXAncestor( self, current_page )
                
            
        else:
            
            visible = self._text_ctrl.IsShownOnScreen()
            
        
        focus_window = wx.Window.FindFocus()
        
        focus_remains_on_self_or_children = focus_window == self._dropdown_window or focus_window in self._dropdown_window.GetChildren() or focus_window == self._text_ctrl
        
        return tlp_active and visible and focus_remains_on_self_or_children
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        raise NotImplementedError()
        
    
    def _ShowDropdown( self ):
        
        ( text_width, text_height ) = self._text_ctrl.GetSize()
        
        desired_dropdown_position = self._text_ctrl.ClientToScreenXY( -2, text_height - 2 )
        
        if self._last_attempted_dropdown_position != desired_dropdown_position:
            
            self._dropdown_window.SetPosition( desired_dropdown_position )
            
            self._last_attempted_dropdown_position = desired_dropdown_position
            
        
        #
        
        show_and_fit_needed = False
        
        if self._dropdown_hidden:
            
            show_and_fit_needed = True
            
        else:
            
            if text_width != self._last_attempted_dropdown_width:
                
                show_and_fit_needed = True
                
            
        
        if show_and_fit_needed:
            
            self._dropdown_window.Fit()
            
            self._dropdown_window.SetSize( ( text_width, -1 ) )
            
            self._dropdown_window.Layout()
            
            self._dropdown_hidden = False
            
            self._last_attempted_dropdown_width = text_width
            
        
    
    def _TakeResponsibilityForEnter( self ):
        
        raise NotImplementedError()
        
    
    def _UpdateList( self ):
        
        pass
        
    
    def BroadcastChoices( self, predicates ):
        
        self._BroadcastChoices( predicates )
        
    
    def EventCloseDropdown( self, event ):
        
        HydrusGlobals.client_controller.GetGUI().Close()
        
    
    def EventKeyDown( self, event ):
        
        HydrusGlobals.client_controller.ResetIdleTimer()
        
        if event.KeyCode in ( wx.WXK_INSERT, wx.WXK_NUMPAD_INSERT ):
            
            if self._intercept_key_events:
                
                self._intercept_key_events = False
                
                ( r, g, b ) = HC.options[ 'gui_colours' ][ 'autocomplete_background' ]
                
                if r != g or r != b or g != b:
                    
                    colour = wx.Colour( g, b, r )
                    
                elif r > 127:
                    
                    colour = wx.Colour( g, b, r / 2 )
                    
                else:
                    
                    colour = wx.Colour( g, b, r * 2 )
                    
                
            else:
                
                self._intercept_key_events = True
                
                colour = wx.Colour( *HC.options[ 'gui_colours' ][ 'autocomplete_background' ] )
                
            
            self._text_ctrl.SetBackgroundColour( colour )
            
            self._text_ctrl.Refresh()
            
        elif event.KeyCode == wx.WXK_SPACE and event.RawControlDown(): # this is control, not command on os x, for which command+space does some os stuff
            
            self._UpdateList()
            
            self._lag_timer.Stop()
            
        elif self._intercept_key_events:
            
            if event.KeyCode in ( ord( 'A' ), ord( 'a' ) ) and event.CmdDown():
                
                event.Skip()
                
            elif event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ) and self._ShouldTakeResponsibilityForEnter():
                
                self._TakeResponsibilityForEnter()
                
            elif event.KeyCode == wx.WXK_ESCAPE:
                
                self.GetTopLevelParent().SetFocus()
                
            elif event.KeyCode in ( wx.WXK_UP, wx.WXK_NUMPAD_UP, wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ) and self._text_ctrl.GetValue() == '' and len( self._dropdown_list ) == 0:
                
                if event.KeyCode in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ): id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'select_up' )
                elif event.KeyCode in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ): id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'select_down' )
                
                new_event = wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = id )
                
                self._text_ctrl.ProcessEvent( new_event )
                
            elif event.KeyCode in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN, wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP ) and self._text_ctrl.GetValue() == '' and len( self._dropdown_list ) == 0:
                
                if event.KeyCode in ( wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP ):
                    
                    id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'canvas_show_previous' )
                    
                elif event.KeyCode in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN ):
                    
                    id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'canvas_show_next' )
                    
                
                new_event = wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = id )
                
                self._text_ctrl.ProcessEvent( new_event )
                
            else:
                
                self._dropdown_list.ProcessEvent( event )
                
            
        else:
            
            event.Skip()
            
        
    
    def EventKillFocus( self, event ):
        
        self._move_hide_timer.Start( 1, wx.TIMER_ONE_SHOT )
        
        event.Skip()
        
    
    def EventMouseWheel( self, event ):
        
        if self._text_ctrl.GetValue() == '' and len( self._dropdown_list ) == 0:
            
            if event.GetWheelRotation() > 0: id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'select_up' )
            else: id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'select_down' )
            
            new_event = wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = id )
            
            self.ProcessEvent( new_event )
            
        else:
            
            if event.CmdDown():
                
                key_event = wx.KeyEvent( wx.EVT_KEY_DOWN.typeId )
                
                if event.GetWheelRotation() > 0: key_event.m_keyCode = wx.WXK_UP
                else: key_event.m_keyCode = wx.WXK_DOWN
                
                self._dropdown_list.ProcessEvent( key_event )
                
            else:
                
                # for some reason, the scrolledwindow list doesn't process scroll events properly when in a popupwindow
                # so let's just tell it to scroll manually
                
                ( start_x, start_y ) = self._dropdown_list.GetViewStart()
                
                if event.GetWheelRotation() > 0: self._dropdown_list.Scroll( -1, start_y - 3 )
                else: self._dropdown_list.Scroll( -1, start_y + 3 )
                
                if event.GetWheelRotation() > 0: command_type = wx.wxEVT_SCROLLWIN_LINEUP
                else: command_type = wx.wxEVT_SCROLLWIN_LINEDOWN
                
                wx.PostEvent( self, wx.ScrollWinEvent( command_type ) )
                
            
        
    
    def EventMove( self, event ):
        
        try:
            
            self._HideDropdown()
            
            self._move_hide_timer.Start( 250, wx.TIMER_ONE_SHOT )
            
        except wx.PyDeadObjectError: pass
        
        event.Skip()
        
    
    def EventSetFocus( self, event ):
        
        self._move_hide_timer.Start( 1, wx.TIMER_ONE_SHOT )
        
        event.Skip()
        
    
    def EventText( self, event ):
        
        num_chars = len( self._text_ctrl.GetValue() )
        
        if num_chars == 0:
            
            self._UpdateList()
            
        elif HC.options[ 'fetch_ac_results_automatically' ]:
            
            ( char_limit, long_wait, short_wait ) = HC.options[ 'ac_timings' ]
            
            self._next_updatelist_is_probably_fast = self._next_updatelist_is_probably_fast and num_chars > len( self._last_search_text )
            
            if self._next_updatelist_is_probably_fast: self._UpdateList()
            elif num_chars < char_limit: self._lag_timer.Start( long_wait, wx.TIMER_ONE_SHOT )
            else: self._lag_timer.Start( short_wait, wx.TIMER_ONE_SHOT )
            
        
    
    def RefreshList( self ):
        
        self._cache_text = None
        
        self._UpdateList()
        
    
    def TIMEREventDropdownHide( self, event ):
        
        try:
            
            should_show = self._ShouldShow()
            
            if should_show:
                
                self._ShowDropdown()
                
            else:
                
                self._HideDropdown()
                
            
            self._move_hide_timer.Start( 250, wx.TIMER_ONE_SHOT )
            
        except wx.PyDeadObjectError:
            
            self._move_hide_timer.Stop()
            
        except:
            
            self._move_hide_timer.Stop()
            
            raise
            
        
    
    def TIMEREventLag( self, event ):
        
        try:
            
            self._UpdateList()
            
        except wx.PyDeadObjectError:
            
            self._lag_timer.Stop()
            
        except:
            
            self._lag_timer.Stop()
            
            raise
            
        
    
class AutoCompleteDropdownTags( AutoCompleteDropdown ):
    
    def __init__( self, parent, file_service_key, tag_service_key ):
        
        self._file_service_key = file_service_key
        self._tag_service_key = tag_service_key
        
        AutoCompleteDropdown.__init__( self, parent )
        
        self._current_matches = []
        
        file_service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._file_service_key )
        
        
        tag_service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._tag_service_key )
        
        self._file_repo_button = ClientGUICommon.BetterButton( self._dropdown_window, file_service.GetName(), self.FileButtonHit )
        self._file_repo_button.SetMinSize( ( 20, -1 ) )
        
        self._tag_repo_button = ClientGUICommon.BetterButton( self._dropdown_window, tag_service.GetName(), self.TagButtonHit )
        self._tag_repo_button.SetMinSize( ( 20, -1 ) )
        
    
    def _ChangeFileService( self, file_service_key ):
        
        if file_service_key == CC.COMBINED_FILE_SERVICE_KEY and self._tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            self._ChangeTagService( CC.LOCAL_TAG_SERVICE_KEY )
            
        
        self._file_service_key = file_service_key
        
        file_service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._file_service_key )
        
        name = file_service.GetName()
        
        self._file_repo_button.SetLabelText( name )
        
        wx.CallAfter( self.RefreshList )
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY and self._file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
            
            self._ChangeFileService( CC.LOCAL_FILE_SERVICE_KEY )
            
        
        self._tag_service_key = tag_service_key
        
        self._dropdown_list.SetTagService( self._tag_service_key )
        
        tag_service = tag_service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._tag_service_key )
        
        name = tag_service.GetName()
        
        self._tag_repo_button.SetLabelText( name )
        
        self._cache_text = None
        
        wx.CallAfter( self.RefreshList )
        
    
    def _UpdateList( self ):
        
        self._last_search_text = self._text_ctrl.GetValue()
        
        matches = self._GenerateMatches()
        
        self._initial_matches_fetched = True
        
        self._dropdown_list.SetPredicates( matches )
        
        self._current_matches = matches
        
        num_chars = len( self._text_ctrl.GetValue() )
        
        if num_chars == 0:
            
            self._lag_timer.Start( 5 * 60 * 1000, wx.TIMER_ONE_SHOT )
            
        
    
    def FileButtonHit( self ):
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        services = []
        
        services.append( services_manager.GetService( CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.TRASH_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
        services.extend( services_manager.GetServices( ( HC.FILE_REPOSITORY, ) ) )
        services.append( services_manager.GetService( CC.COMBINED_FILE_SERVICE_KEY ) )
        
        menu = wx.Menu()
        
        for service in services:
            
            ClientGUIMenus.AppendMenuItem( self, menu, service.GetName(), 'Change the current file domain to ' + service.GetName() + '.', self._ChangeFileService, service.GetServiceKey() )
            
        
        HydrusGlobals.client_controller.PopupMenu( self._file_repo_button, menu )
        
    
    def SetFileService( self, file_service_key ):
        
        self._ChangeFileService( file_service_key )
        
    
    def SetTagService( self, tag_service_key ):
        
        self._ChangeTagService( tag_service_key )
        
    
    def TagButtonHit( self ):
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        services = []
        
        services.append( services_manager.GetService( CC.LOCAL_TAG_SERVICE_KEY ) )
        services.extend( services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        services.append( services_manager.GetService( CC.COMBINED_TAG_SERVICE_KEY ) )
        
        menu = wx.Menu()
        
        for service in services:
            
            ClientGUIMenus.AppendMenuItem( self, menu, service.GetName(), 'Change the current tag domain to ' + service.GetName() + '.', self._ChangeTagService, service.GetServiceKey() )
            
        
        HydrusGlobals.client_controller.PopupMenu( self._tag_repo_button, menu )
        
    
class AutoCompleteDropdownTagsRead( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, page_key, file_search_context, media_callable = None, synchronised = True, include_unusual_predicate_types = True ):
        
        file_service_key = file_search_context.GetFileServiceKey()
        tag_service_key = file_search_context.GetTagServiceKey()
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_key, tag_service_key )
        
        self._media_callable = media_callable
        self._page_key = page_key
        
        self._file_search_context = file_search_context
        
        self._include_current_tags = ClientGUICommon.OnOffButton( self._dropdown_window, self._page_key, 'notify_include_current', on_label = 'include current tags', off_label = 'exclude current tags', start_on = file_search_context.IncludeCurrentTags() )
        self._include_current_tags.SetToolTipString( 'select whether to include current tags in the search' )
        self._include_pending_tags = ClientGUICommon.OnOffButton( self._dropdown_window, self._page_key, 'notify_include_pending', on_label = 'include pending tags', off_label = 'exclude pending tags', start_on = file_search_context.IncludePendingTags() )
        self._include_pending_tags.SetToolTipString( 'select whether to include pending tags in the search' )
        
        self._synchronised = ClientGUICommon.OnOffButton( self._dropdown_window, self._page_key, 'notify_search_immediately', on_label = 'searching immediately', off_label = 'waiting -- tag counts may be inaccurate', start_on = synchronised )
        self._synchronised.SetToolTipString( 'select whether to renew the search as soon as a new predicate is entered' )
        
        self._include_unusual_predicate_types = include_unusual_predicate_types
        
        button_hbox_1 = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox_1.AddF( self._include_current_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox_1.AddF( self._include_pending_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        button_hbox_2 = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox_2.AddF( self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox_2.AddF( self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( button_hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._synchronised, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( button_hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._dropdown_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
        HydrusGlobals.client_controller.sub( self, 'SetSynchronisedWait', 'synchronised_wait_switch' )
        
        HydrusGlobals.client_controller.sub( self, 'IncludeCurrent', 'notify_include_current' )
        HydrusGlobals.client_controller.sub( self, 'IncludePending', 'notify_include_pending' )
        
    
    def _BroadcastChoices( self, predicates ):
        
        if self._text_ctrl.GetValue() != '':
            
            self._text_ctrl.SetValue( '' )
            
        
        HydrusGlobals.client_controller.pub( 'enter_predicates', self._page_key, predicates )
        
    
    def _BroadcastCurrentText( self ):
        
        ( inclusive, search_text, explicit_wildcard, cache_text, entry_predicate ) = self._ParseSearchText()
        
        try:
            
            HydrusTags.CheckTagNotEmpty( search_text )
            
        except HydrusExceptions.SizeException:
            
            return
            
        
        self._BroadcastChoices( { entry_predicate } )
        
    
    def _ChangeFileService( self, file_service_key ):
        
        AutoCompleteDropdownTags._ChangeFileService( self, file_service_key )
        
        self._file_search_context.SetFileServiceKey( file_service_key )
        
        HydrusGlobals.client_controller.pub( 'change_file_service', self._page_key, file_service_key )
        
        HydrusGlobals.client_controller.pub( 'refresh_query', self._page_key )
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        AutoCompleteDropdownTags._ChangeTagService( self, tag_service_key )
        
        self._file_search_context.SetTagServiceKey( tag_service_key )
        
        HydrusGlobals.client_controller.pub( 'change_tag_service', self._page_key, tag_service_key )
        
        HydrusGlobals.client_controller.pub( 'refresh_query', self._page_key )
        
    
    def _InitDropDownList( self ):
        
        return ClientGUIListBoxes.ListBoxTagsACRead( self._dropdown_window, self.BroadcastChoices, self._tag_service_key, min_height = self._list_height )
        
    
    def _ParseSearchText( self ):
        
        raw_entry = self._text_ctrl.GetValue()
        
        if raw_entry.startswith( '-' ):
            
            inclusive = False
            
            entry_text = raw_entry[1:]
            
        else:
            
            inclusive = True
            
            entry_text = raw_entry
            
        
        tag = HydrusTags.CleanTag( entry_text )
        
        explicit_wildcard = '*' in entry_text
        
        search_text = ClientSearch.ConvertEntryTextToSearchText( entry_text )
        
        if explicit_wildcard:
            
            cache_text = None
            
            entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, search_text, inclusive )
            
        else:
            
            cache_text = search_text[:-1] # take off the trailing '*' for the cache text
            
            siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
            
            sibling = siblings_manager.GetSibling( self._tag_service_key, tag )
            
            if sibling is None:
                
                entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive )
                
            else:
                
                entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, sibling, inclusive )
                
            
        
        return ( inclusive, search_text, explicit_wildcard, cache_text, entry_predicate )
        
    
    def _GenerateMatches( self ):
        
        self._next_updatelist_is_probably_fast = False
        
        num_autocomplete_chars = HC.options[ 'num_autocomplete_chars' ]
        
        ( inclusive, search_text, explicit_wildcard, cache_text, entry_predicate ) = self._ParseSearchText()
        
        if search_text in ( '', ':', '*' ):
            
            input_just_changed = self._cache_text is not None
            
            db_not_going_to_hang_if_we_hit_it = not HydrusGlobals.client_controller.DBCurrentlyDoingJob()
            
            if input_just_changed or db_not_going_to_hang_if_we_hit_it or not self._initial_matches_fetched:
                
                self._cache_text = None
                
                if self._file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                    
                    search_service_key = self._tag_service_key
                    
                else:
                    
                    search_service_key = self._file_service_key
                    
                
                self._cached_results = HydrusGlobals.client_controller.Read( 'file_system_predicates', search_service_key )
                
            
            matches = self._cached_results
            
        else:
            
            ( namespace, half_complete_subtag ) = HydrusTags.SplitTag( search_text )
            
            siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
            
            if False and half_complete_subtag == '':
                
                self._cache_text = None
                
                matches = [] # a query like 'namespace:'
                
            else:
                
                fetch_from_db = True
                
                if self._media_callable is not None:
                    
                    media = self._media_callable()
                    
                    can_fetch_from_media = media is not None and len( media ) > 0
                    
                    if can_fetch_from_media and self._synchronised.IsOn():
                        
                        fetch_from_db = False
                        
                    
                
                if fetch_from_db:
                    
                    # if user searches 'blah', then we include 'blah (23)' for 'series:blah (10)', 'blah (13)'
                    # if they search for 'series:blah', then we don't!
                    add_namespaceless = ':' not in namespace
                    
                    include_current = self._file_search_context.IncludeCurrentTags()
                    include_pending = self._file_search_context.IncludePendingTags()
                    
                    small_and_specific_search = cache_text is not None and len( cache_text ) < num_autocomplete_chars
                    
                    if small_and_specific_search:
                        
                        predicates = HydrusGlobals.client_controller.Read( 'autocomplete_predicates', file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, search_text = search_text, exact_match = True, inclusive = inclusive, include_current = include_current, include_pending = include_pending, add_namespaceless = add_namespaceless, collapse_siblings = True )
                        
                    else:
                        
                        cache_invalid_for_this_search = cache_text is None or self._cache_text is None or not cache_text.startswith( self._cache_text )
                        
                        if cache_invalid_for_this_search:
                            
                            self._cache_text = cache_text
                            
                            self._cached_results = HydrusGlobals.client_controller.Read( 'autocomplete_predicates', file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, search_text = search_text, inclusive = inclusive, include_current = include_current, include_pending = include_pending, add_namespaceless = add_namespaceless, collapse_siblings = True )
                            
                        
                        predicates = self._cached_results
                        
                        self._next_updatelist_is_probably_fast = True
                        
                    
                else:
                    
                    # it is possible that media will change between calls to this, so don't cache it
                    # it's also quick as hell, so who cares
                    
                    tags_managers = []
                    
                    for m in media:
                        
                        if m.IsCollection(): tags_managers.extend( m.GetSingletonsTagsManagers() )
                        else: tags_managers.append( m.GetTagsManager() )
                        
                    
                    tags_to_do = set()
                    
                    current_tags_to_count = collections.Counter()
                    pending_tags_to_count = collections.Counter()
                    
                    if self._file_search_context.IncludeCurrentTags():
                        
                        lists_of_current_tags = [ list( tags_manager.GetCurrent( self._tag_service_key ) ) for tags_manager in tags_managers ]
                        
                        current_tags_flat_iterable = itertools.chain.from_iterable( lists_of_current_tags )
                        
                        current_tags_flat = ClientSearch.FilterTagsBySearchText( self._tag_service_key, search_text, current_tags_flat_iterable )
                        
                        current_tags_to_count.update( current_tags_flat )
                        
                        tags_to_do.update( current_tags_to_count.keys() )
                        
                    
                    if self._file_search_context.IncludePendingTags():
                        
                        lists_of_pending_tags = [ list( tags_manager.GetPending( self._tag_service_key ) ) for tags_manager in tags_managers ]
                        
                        pending_tags_flat_iterable = itertools.chain.from_iterable( lists_of_pending_tags )
                        
                        pending_tags_flat = ClientSearch.FilterTagsBySearchText( self._tag_service_key, search_text, pending_tags_flat_iterable )
                        
                        pending_tags_to_count.update( pending_tags_flat )
                        
                        tags_to_do.update( pending_tags_to_count.keys() )
                        
                    
                    predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive, current_tags_to_count[ tag ], pending_tags_to_count[ tag ] ) for tag in tags_to_do ]
                    
                    if self._tag_service_key != CC.COMBINED_TAG_SERVICE_KEY:
                        
                        predicates = siblings_manager.CollapsePredicates( self._tag_service_key, predicates )
                        
                    
                    if namespace == '':
                        
                        predicates = ClientData.MergePredicates( predicates, add_namespaceless = True )
                        
                    
                    self._next_updatelist_is_probably_fast = True
                    
                
                matches = ClientSearch.FilterPredicatesBySearchText( self._tag_service_key, search_text, predicates )
                
                matches = ClientSearch.SortPredicates( matches )
                
            
            if self._include_unusual_predicate_types:
                
                if explicit_wildcard:
                    
                    matches.insert( 0, ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, search_text, inclusive ) )
                    
                else:
                    
                    if namespace != '' and half_complete_subtag in ( '', '*' ):
                        
                        matches.insert( 0, ClientSearch.Predicate( HC.PREDICATE_TYPE_NAMESPACE, namespace, inclusive ) )
                        
                    
                
            
            for match in matches:
                
                if match.GetInclusive() != inclusive: match.SetInclusive( inclusive )
                
            
            try:
                
                index = matches.index( entry_predicate )
                
                predicate = matches[ index ]
                
                del matches[ index ]
                
                matches.insert( 0, predicate )
                
            except:
                
                pass
                
            
        
        return matches
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        # when the user has quickly typed something in and the results are not yet in
        
        return self._text_ctrl.GetValue() != '' and self._last_search_text == ''
        
    
    def _TakeResponsibilityForEnter( self ):
        
        self._BroadcastCurrentText()
        
    
    def GetFileSearchContext( self ):
        
        return self._file_search_context
        
    
    def IncludeCurrent( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._file_search_context.SetIncludeCurrentTags( value )
            
            wx.CallAfter( self.RefreshList )
            
            HydrusGlobals.client_controller.pub( 'refresh_query', self._page_key )
            
        
    
    def IncludePending( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._file_search_context.SetIncludePendingTags( value )
            
            wx.CallAfter( self.RefreshList )
            
            HydrusGlobals.client_controller.pub( 'refresh_query', self._page_key )
            
        
    
    def SetSynchronisedWait( self, page_key ):
        
        if page_key == self._page_key: self._synchronised.EventButton( None )
        
    
class AutoCompleteDropdownTagsWrite( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, chosen_tag_callable, expand_parents, file_service_key, tag_service_key, null_entry_callable = None ):
        
        self._chosen_tag_callable = chosen_tag_callable
        self._expand_parents = expand_parents
        self._null_entry_callable = null_entry_callable
        
        if tag_service_key != CC.COMBINED_TAG_SERVICE_KEY and HC.options[ 'show_all_tags_in_autocomplete' ]:
            
            file_service_key = CC.COMBINED_FILE_SERVICE_KEY
            
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_key, tag_service_key )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._dropdown_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
    
    def _BroadcastChoices( self, predicates ):
        
        if self._text_ctrl.GetValue() != '':
            
            self._text_ctrl.SetValue( '' )
            
        
        tags = { predicate.GetValue() for predicate in predicates }
        
        if len( tags ) > 0:
            
            self._chosen_tag_callable( tags )
            
        
    
    def _ParseSearchText( self ):
        
        raw_entry = self._text_ctrl.GetValue()
        
        tag = HydrusTags.CleanTag( raw_entry )
        
        search_text = ClientSearch.ConvertEntryTextToSearchText( raw_entry )
        
        if ClientSearch.IsComplexWildcard( search_text ):
            
            cache_text = None
            
        else:
            
            cache_text = search_text[:-1] # take off the trailing '*' for the cache text
            
        
        entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag )
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        sibling = siblings_manager.GetSibling( self._tag_service_key, tag )
        
        if sibling is not None:
            
            sibling_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, sibling )
            
        else:
            
            sibling_predicate = None
            
        
        return ( search_text, cache_text, entry_predicate, sibling_predicate )
        
    
    def _BroadcastCurrentText( self ):
        
        ( search_text, cache_text, entry_predicate, sibling_predicate ) = self._ParseSearchText()
        
        try:
            
            HydrusTags.CheckTagNotEmpty( search_text )
            
        except HydrusExceptions.SizeException:
            
            return
            
        
        self._BroadcastChoices( { entry_predicate } )
        
    
    def _GenerateMatches( self ):
        
        self._next_updatelist_is_probably_fast = False
        
        num_autocomplete_chars = HC.options[ 'num_autocomplete_chars' ]
        
        ( search_text, cache_text, entry_predicate, sibling_predicate ) = self._ParseSearchText()
        
        if search_text in ( '', ':', '*' ):
            
            self._cache_text = None
            
            matches = []
            
        else:
            
            must_do_a_search = False
            
            small_and_specific_search = cache_text is not None and len( cache_text ) < num_autocomplete_chars
            
            if small_and_specific_search:
                
                predicates = HydrusGlobals.client_controller.Read( 'autocomplete_predicates', file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, search_text = search_text, exact_match = True, add_namespaceless = False, collapse_siblings = False )
                
            else:
                
                cache_invalid_for_this_search = cache_text is None or self._cache_text is None or not cache_text.startswith( self._cache_text )
                
                if must_do_a_search or cache_invalid_for_this_search:
                    
                    self._cache_text = cache_text
                    
                    self._cached_results = HydrusGlobals.client_controller.Read( 'autocomplete_predicates', file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, search_text = search_text, add_namespaceless = False, collapse_siblings = False )
                    
                
                predicates = self._cached_results
                
                self._next_updatelist_is_probably_fast = True
                
            
            matches = ClientSearch.FilterPredicatesBySearchText( self._tag_service_key, search_text, predicates )
            
            matches = ClientSearch.SortPredicates( matches )
            
            self._PutAtTopOfMatches( matches, entry_predicate )
            
            if sibling_predicate is not None:
                
                self._PutAtTopOfMatches( matches, sibling_predicate )
                
            
            if self._expand_parents:
                
                parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                
                matches = parents_manager.ExpandPredicates( self._tag_service_key, matches )
                
            
        
        return matches
        
    
    def _InitDropDownList( self ):
        
        return ClientGUIListBoxes.ListBoxTagsACWrite( self._dropdown_window, self.BroadcastChoices, self._tag_service_key, min_height = self._list_height )
        
    
    def _PutAtTopOfMatches( self, matches, predicate ):
        
        try:
            
            index = matches.index( predicate )
            
            predicate = matches[ index ]
            
            matches.remove( predicate )
            
        except ValueError:
            
            pass
            
        
        matches.insert( 0, predicate )
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        # when the user has quickly typed something in and the results are not yet in
        
        p1 = self._text_ctrl.GetValue() != '' and self._last_search_text == ''
        
        # when the text ctrl is empty and we want to push a None to the parent dialog
        
        p2 = self._text_ctrl.GetValue() == ''
        
        return p1 or p2
        
    
    def _TakeResponsibilityForEnter( self ):
        
        if self._text_ctrl.GetValue() == '':
            
            if self._null_entry_callable is not None:
                
                self._null_entry_callable()
                
            
        else:
            
            self._BroadcastCurrentText()
            
        
    
