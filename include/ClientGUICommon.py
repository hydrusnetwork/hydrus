import collections
import HydrusConstants as HC
import ClientCaches
import ClientData
import ClientConstants as CC
import ClientRatings
import itertools
import os
import random
import sys
import time
import traceback
import wx
import wx.combo
import wx.richtext
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from wx.lib.mixins.listctrl import ColumnSorterMixin
import HydrusTags
import HydrusData
import HydrusExceptions
import ClientSearch
import HydrusGlobals

TEXT_CUTOFF = 1024

#

ID_TIMER_ANIMATED = wx.NewId()
ID_TIMER_SLIDESHOW = wx.NewId()
ID_TIMER_MEDIA_INFO_DISPLAY = wx.NewId()
ID_TIMER_DROPDOWN_HIDE = wx.NewId()
ID_TIMER_AC_LAG = wx.NewId()
ID_TIMER_POPUP = wx.NewId()

class AnimatedStaticTextTimestamp( wx.StaticText ):
    
    def __init__( self, parent, prefix, rendering_function, timestamp, suffix ):
        
        self._prefix = prefix
        self._rendering_function = rendering_function
        self._timestamp = timestamp
        self._suffix = suffix
        
        self._last_tick = HydrusData.GetNow()
        
        wx.StaticText.__init__( self, parent, label = self._prefix + self._rendering_function( self._timestamp ) + self._suffix )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventAnimated, id = ID_TIMER_ANIMATED )
        
        animated_event_timer = wx.Timer( self, ID_TIMER_ANIMATED )
        animated_event_timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    def TIMEREventAnimated( self ):
        
        update = False
        
        now = HydrusData.GetNow()
        
        difference = abs( now - self._timestamp )
        
        if difference < 3600: update = True
        elif difference < 3600 * 24 and now - self._last_tick > 60: update = True
        elif now - self._last_tick > 3600: update = True
        
        if update:
            
            self.SetLabel( self._prefix + self._rendering_function( self._timestamp ) + self._suffix )
            
            wx.PostEvent( self.GetEventHandler(), wx.SizeEvent() )
            
        
    
# much of this is based on the excellent TexCtrlAutoComplete class by Edward Flick, Michele Petrazzo and Will Sadkin, just with plenty of simplification and integration into hydrus
class AutoCompleteDropdown( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._last_search_text = ''
        
        tlp = self.GetTopLevelParent()
        
        # There's a big bug in wx where FRAME_FLOAT_ON_PARENT Frames don't get passed their mouse events if their parent is a Dialog jej
        # I think it is something to do with the initialisation order; if the frame is init'ed before the ShowModal call, but whatever.
        
        if issubclass( type( tlp ), wx.Dialog ) or HC.options[ 'always_embed_autocompletes' ]: self._float_mode = False
        else: self._float_mode = True
        
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
            
            self._dropdown_window.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
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
        
        self._cache_text = ''
        self._cached_results = []
        
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
                    
                    if issubclass( type( parent ), wx.ScrolledWindow ):
                        
                        parent.Bind( wx.EVT_SCROLLWIN, self.EventMove )
                        
                    
                except: break
                
            
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventLag, id = ID_TIMER_AC_LAG )
        
        self._lag_timer = wx.Timer( self, id = ID_TIMER_AC_LAG )
        
        wx.CallAfter( self._UpdateList )
        
    
    def _BroadcastChoice( self, predicate ): pass
    
    def _BroadcastCurrentText( self ):
        
        text = self._text_ctrl.GetValue()
        
        self._BroadcastChoice( text )
        
    
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
                
                visible = ClientData.IsWXAncestor( self, current_page )
                
            
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
        
    
    def BroadcastChoice( self, predicate ):
        
        self._BroadcastChoice( predicate )
        
    
    def EventCloseDropdown( self, event ):
        
        HydrusGlobals.client_controller.GetGUI().EventExit( event )
        
    
    def EventKeyDown( self, event ):
        
        HydrusGlobals.client_controller.ResetIdleTimer()
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ) and self._ShouldTakeResponsibilityForEnter():
            
            self._TakeResponsibilityForEnter()
            
        elif event.KeyCode == wx.WXK_ESCAPE:
            
            self.GetTopLevelParent().SetFocus()
            
        elif event.KeyCode in ( wx.WXK_UP, wx.WXK_NUMPAD_UP, wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ) and self._text_ctrl.GetValue() == '' and len( self._dropdown_list ) == 0:
            
            if event.KeyCode in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ): id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'select_up' )
            elif event.KeyCode in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ): id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'select_down' )
            
            new_event = wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = id )
            
            self._text_ctrl.ProcessEvent( new_event )
            
        elif event.KeyCode in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN, wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP ) and self._text_ctrl.GetValue() == '' and len( self._dropdown_list ) == 0:
            
            if event.KeyCode in ( wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP ): id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'canvas_show_previous' )
            elif event.KeyCode in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN ): id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'canvas_show_next' )
            
            new_event = wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = id )
            
            self._text_ctrl.ProcessEvent( new_event )
            
        else: self._dropdown_list.ProcessEvent( event )
        
    
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
        
        ( char_limit, long_wait, short_wait ) = HC.options[ 'ac_timings' ]
        
        if num_chars == 0: self._UpdateList()
        elif num_chars < char_limit: self._lag_timer.Start( long_wait, wx.TIMER_ONE_SHOT )
        else: self._lag_timer.Start( short_wait, wx.TIMER_ONE_SHOT )
        
    
    def TIMEREventDropdownHide( self, event ):
        
        try:
            
            should_show = self._ShouldShow()
            
            if should_show:
                
                self._ShowDropdown()
                
            else:
                
                self._HideDropdown()
                
            
            self._move_hide_timer.Start( 250, wx.TIMER_ONE_SHOT )
            
        except wx.PyDeadObjectError: pass
        
    
    def TIMEREventLag( self, event ): self._UpdateList()
    
class AutoCompleteDropdownTags( AutoCompleteDropdown ):
    
    def __init__( self, parent, file_service_key, tag_service_key ):
        
        AutoCompleteDropdown.__init__( self, parent )
        
        self._current_namespace = ''
        self._current_matches = []
        
        self._file_service_key = file_service_key
        self._tag_service_key = tag_service_key
        
        file_service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._file_service_key )
        tag_service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._tag_service_key )
        
        self._file_repo_button = wx.Button( self._dropdown_window, label = file_service.GetName() )
        self._file_repo_button.Bind( wx.EVT_BUTTON, self.EventFileButton )
        self._file_repo_button.SetMinSize( ( 20, -1 ) )
        
        self._tag_repo_button = wx.Button( self._dropdown_window, label = tag_service.GetName() )
        self._tag_repo_button.Bind( wx.EVT_BUTTON, self.EventTagButton )
        self._tag_repo_button.SetMinSize( ( 20, -1 ) )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _ChangeFileRepository( self, file_service_key ):

        self._file_service_key = file_service_key
        
        file_service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._file_service_key )
        
        name = file_service.GetName()
        
        self._file_repo_button.SetLabel( name )
        
    
    def _ChangeTagRepository( self, tag_service_key ):

        self._tag_service_key = tag_service_key
        
        tag_service = tag_service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._tag_service_key )
        
        name = tag_service.GetName()
        
        self._tag_repo_button.SetLabel( name )
        
    
    def _InitDropDownList( self ): return ListBoxTagsAutocompleteDropdown( self._dropdown_window, self.BroadcastChoice, min_height = self._list_height )
    
    def _UpdateList( self ):
        
        self._last_search_text = self._text_ctrl.GetValue()
        
        matches = self._GenerateMatches()
        
        self._dropdown_list.SetPredicates( matches )
        
        self._current_matches = matches
        
        num_chars = len( self._text_ctrl.GetValue() )
        
        if num_chars == 0: self._lag_timer.Start( 5 * 60 * 1000, wx.TIMER_ONE_SHOT )
        
    
    def EventFileButton( self, event ):
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        services = []
        services.append( services_manager.GetService( CC.COMBINED_FILE_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.TRASH_SERVICE_KEY ) )
        services.extend( services_manager.GetServices( ( HC.FILE_REPOSITORY, ) ) )
        
        menu = wx.Menu()
        
        for service in services: menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'change_file_repository', service.GetServiceKey() ), service.GetName() )
        
        self._file_repo_button.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'change_file_repository': self._ChangeFileRepository( data )
            elif command == 'change_tag_repository': self._ChangeTagRepository( data )
            else:
                
                event.Skip()
                
                return # this is about select_up and select_down
                
            
            self._cache_text = ''
            self._current_namespace = ''
            
            self._UpdateList()
            
        
    
    def EventTagButton( self, event ):
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        services = []
        services.append( services_manager.GetService( CC.COMBINED_TAG_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.LOCAL_TAG_SERVICE_KEY ) )
        services.extend( services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        
        menu = wx.Menu()
        
        for service in services: menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'change_tag_repository', service.GetServiceKey() ), service.GetName() )
        
        self._tag_repo_button.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
class AutoCompleteDropdownTagsRead( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, page_key, file_service_key, tag_service_key, media_callable = None, include_current = True, include_pending = True, synchronised = True ):
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_key, tag_service_key )
        
        self._media_callable = media_callable
        self._page_key = page_key
        
        self._include_current = include_current
        self._include_pending = include_pending
        
        self._include_current_tags = OnOffButton( self._dropdown_window, self._page_key, 'notify_include_current', on_label = 'include current tags', off_label = 'exclude current tags', start_on = self._include_current )
        self._include_current_tags.SetToolTipString( 'select whether to include current tags in the search' )
        self._include_pending_tags = OnOffButton( self._dropdown_window, self._page_key, 'notify_include_pending', on_label = 'include pending tags', off_label = 'exclude pending tags', start_on = self._include_pending )
        self._include_pending_tags.SetToolTipString( 'select whether to include pending tags in the search' )
        
        self._synchronised = OnOffButton( self._dropdown_window, self._page_key, 'notify_search_immediately', on_label = 'searching immediately', off_label = 'waiting -- tag counts may be inaccurate', start_on = synchronised )
        self._synchronised.SetToolTipString( 'select whether to renew the search as soon as a new predicate is entered' )
        
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
        
    
    def _BroadcastChoice( self, predicate ):
        
        if self._text_ctrl.GetValue() != '':
            
            self._text_ctrl.SetValue( '' )
            
        
        HydrusGlobals.client_controller.pub( 'add_predicate', self._page_key, predicate )
        
    
    def _BroadcastCurrentText( self ):
        
        ( inclusive, search_text, entry_predicate ) = self._ParseSearchText()
        
        try:
            
            HydrusTags.CheckTagNotEmpty( search_text )
            
        except HydrusExceptions.SizeException:
            
            return
            
        
        self._BroadcastChoice( entry_predicate )
        
    
    def _ChangeFileRepository( self, file_service_key ):
        
        AutoCompleteDropdownTags._ChangeFileRepository( self, file_service_key )
        
        HydrusGlobals.client_controller.pub( 'change_file_repository', self._page_key, self._file_service_key )
        
    
    def _ChangeTagRepository( self, tag_service_key ):
        
        AutoCompleteDropdownTags._ChangeTagRepository( self, tag_service_key )
        
        HydrusGlobals.client_controller.pub( 'change_tag_repository', self._page_key, self._tag_service_key )
        
    
    def _ParseSearchText( self ):
        
        raw_entry = self._text_ctrl.GetValue()
        
        if raw_entry.startswith( '-' ):
            
            inclusive = False
            
            search_text = raw_entry[1:]
            
        else:
            
            inclusive = True
            
            search_text = raw_entry
            
        
        search_text = HydrusTags.CleanTag( search_text )
        
        entry_predicate = ClientData.Predicate( HC.PREDICATE_TYPE_TAG, search_text, inclusive = inclusive )
        
        return ( inclusive, search_text, entry_predicate )
        
    
    def _GenerateMatches( self ):
        
        num_autocomplete_chars = HC.options[ 'num_autocomplete_chars' ]
        
        ( inclusive, search_text, entry_predicate ) = self._ParseSearchText()
        
        if search_text in ( '', ':' ):
            
            self._cache_text = ''
            self._current_namespace = ''
            
            if self._file_service_key == CC.COMBINED_FILE_SERVICE_KEY: search_service_key = self._tag_service_key
            else: search_service_key = self._file_service_key
            
            matches = HydrusGlobals.client_controller.Read( 'file_system_predicates', search_service_key )
            
        else:
            
            must_do_a_search = False
            
            if '*' in search_text: must_do_a_search = True
            
            if ':' in search_text:
                
                ( namespace, half_complete_tag ) = search_text.split( ':' )
                
                if namespace != self._current_namespace:
                    
                    self._current_namespace = namespace # do a new search, no matter what half_complete tag is
                    
                    if half_complete_tag != '': must_do_a_search = True
                    
                else:
                    
                    if self._cache_text == self._current_namespace + ':' and half_complete_tag != '': must_do_a_search = True
                    
                
            else:
                
                self._current_namespace = ''
                
                half_complete_tag = search_text
                
            
            if half_complete_tag == '':
                
                self._cache_text = self._current_namespace + ':'
                
                matches = [] # a query like 'namespace:'
                
            else:
                
                fetch_from_db = True
                
                if self._media_callable is not None:
                    
                    media = self._media_callable()
                    
                    can_fetch_from_media = media is not None and len( media ) > 0
                    
                    if can_fetch_from_media and self._synchronised.IsOn(): fetch_from_db = False
                    
                
                if fetch_from_db:
                    
                    if len( search_text ) < num_autocomplete_chars:
                        
                        predicates = HydrusGlobals.client_controller.Read( 'autocomplete_predicates', file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, tag = search_text, include_current = self._include_current, include_pending = self._include_pending, add_namespaceless = True )
                        
                    else:
                        
                        if must_do_a_search or self._cache_text == '' or not search_text.startswith( self._cache_text ):
                            
                            self._cache_text = search_text
                            
                            self._cached_results = HydrusGlobals.client_controller.Read( 'autocomplete_predicates', file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, half_complete_tag = search_text, include_current = self._include_current, include_pending = self._include_pending, add_namespaceless = True )
                            
                        
                        predicates = self._cached_results
                        
                    
                else:
                    
                    # it is possible that media will change between calls to this, so don't cache it
                    # it's also quick as hell, so who cares
                    
                    tags_managers = []
                    
                    for m in media:
                        
                        if m.IsCollection(): tags_managers.extend( m.GetSingletonsTagsManagers() )
                        else: tags_managers.append( m.GetTagsManager() )
                        
                    
                    lists_of_current_tags = [ list( tags_manager.GetCurrent( self._tag_service_key ) ) for tags_manager in tags_managers ]
                    lists_of_pending_tags = [ list( tags_manager.GetPending( self._tag_service_key ) ) for tags_manager in tags_managers ]
                    
                    current_tags_flat_iterable = itertools.chain.from_iterable( lists_of_current_tags )
                    pending_tags_flat_iterable = itertools.chain.from_iterable( lists_of_pending_tags )
                    
                    current_tags_flat = [ tag for tag in current_tags_flat_iterable if ClientSearch.SearchEntryMatchesTag( search_text, tag ) ]
                    pending_tags_flat = [ tag for tag in pending_tags_flat_iterable if ClientSearch.SearchEntryMatchesTag( search_text, tag ) ]
                    
                    current_tags_to_count = collections.Counter( current_tags_flat )
                    pending_tags_to_count = collections.Counter( pending_tags_flat )
                    
                    tags_to_do = set()
                    
                    if self._include_current: tags_to_do.update( current_tags_to_count.keys() )
                    if self._include_pending: tags_to_do.update( pending_tags_to_count.keys() )
                    
                    predicates = [ ClientData.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive = inclusive, counts = { HC.CURRENT : current_tags_to_count[ tag ], HC.PENDING : pending_tags_to_count[ tag ] } ) for tag in tags_to_do ]
                    
                
                predicates = ClientSearch.SortPredicates( predicates, collapse_siblings = True )
                
                matches = ClientSearch.FilterPredicates( search_text, predicates )
                
            
            if self._current_namespace != '':
                
                if '*' not in self._current_namespace:
                    
                    matches.insert( 0, ClientData.Predicate( HC.PREDICATE_TYPE_NAMESPACE, self._current_namespace, inclusive = inclusive ) )
                    
                
                if half_complete_tag != '':
                    
                    if '*' in self._current_namespace or ( '*' in half_complete_tag and half_complete_tag != '*' ):
                        
                        matches.insert( 0, ClientData.Predicate( HC.PREDICATE_TYPE_WILDCARD, search_text, inclusive = inclusive ) )
                        
                    
                
            elif '*' in search_text:
                
                matches.insert( 0, ClientData.Predicate( HC.PREDICATE_TYPE_WILDCARD, search_text, inclusive = inclusive ) )
                
            
            try:
                
                index = matches.index( entry_predicate )
                
                predicate = matches[ index ]
                
                del matches[ index ]
                
                matches.insert( 0, predicate )
                
            except: pass
            
        
        for match in matches:
            
            if match.GetType() == HC.PREDICATE_TYPE_TAG: match.SetInclusive( inclusive )
            
        
        return matches
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        # when the user has quickly typed something in and the results are not yet in
        
        return self._text_ctrl.GetValue() != '' and self._last_search_text == ''
        
    
    def _TakeResponsibilityForEnter( self ):
        
        self._BroadcastCurrentText()
        
    
    def GetFileSearchContext( self ):
        
        return ClientData.FileSearchContext( file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, include_current_tags = self._include_current, include_pending_tags = self._include_pending )
        
    
    def IncludeCurrent( self, page_key, value ):
        
        if page_key == self._page_key: self._include_current = value
        
        self._cache_text = ''
        self._current_namespace = ''
        
    
    def IncludePending( self, page_key, value ):
        
        if page_key == self._page_key: self._include_pending = value
        
        self._cache_text = ''
        self._current_namespace = ''
        
    
    def SetSynchronisedWait( self, page_key ):
        
        if page_key == self._page_key: self._synchronised.EventButton( None )
        
    
class AutoCompleteDropdownTagsWrite( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, chosen_tag_callable, file_service_key, tag_service_key ):
        
        self._chosen_tag_callable = chosen_tag_callable
        
        if HC.options[ 'show_all_tags_in_autocomplete' ]: file_service_key = CC.COMBINED_FILE_SERVICE_KEY
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_key, tag_service_key )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._dropdown_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
    
    def _BroadcastChoice( self, predicate ):
        
        if self._text_ctrl.GetValue() != '':
            
            self._text_ctrl.SetValue( '' )
            
        
        if predicate is None: self._chosen_tag_callable( None )
        else:
            
            tag = predicate.GetValue()
            
            tag_censorship_manager = HydrusGlobals.client_controller.GetManager( 'tag_censorship' )
            
            result = tag_censorship_manager.FilterTags( self._tag_service_key, ( tag, ) )
            
            if len( result ) > 0:
                
                tag_parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                
                parents = tag_parents_manager.GetParents( self._tag_service_key, tag )
                
                parents = tag_censorship_manager.FilterTags( self._tag_service_key, parents )
                
                self._chosen_tag_callable( tag, parents )
                
            
        
    
    def _ParseSearchText( self ):
        
        raw_entry = self._text_ctrl.GetValue()
        
        search_text = HydrusTags.CleanTag( raw_entry )
        
        entry_predicate = ClientData.Predicate( HC.PREDICATE_TYPE_TAG, search_text )
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        sibling = siblings_manager.GetSibling( search_text )
        
        if sibling is not None:
            
            sibling_predicate = ClientData.Predicate( HC.PREDICATE_TYPE_TAG, sibling )
            
        else:
            
            sibling_predicate = None
            
        
        return ( search_text, entry_predicate, sibling_predicate )
        
    
    def _BroadcastCurrentText( self ):
        
        ( search_text, entry_predicate, sibling_predicate ) = self._ParseSearchText()
        
        try:
            
            HydrusTags.CheckTagNotEmpty( search_text )
            
        except HydrusExceptions.SizeException:
            
            return
            
        
        if sibling_predicate is not None:
            
            self._BroadcastChoice( sibling_predicate )
            
        else:
            
            self._BroadcastChoice( entry_predicate )
            
        
    
    def _GenerateMatches( self ):
        
        num_autocomplete_chars = HC.options[ 'num_autocomplete_chars' ]
        
        ( search_text, entry_predicate, sibling_predicate ) = self._ParseSearchText()
        
        if search_text in ( '', ':' ):
            
            self._cache_text = ''
            self._current_namespace = ''
            
            matches = []
            
        else:
            
            must_do_a_search = False
            
            if ':' in search_text:
                
                ( namespace, other_half ) = search_text.split( ':' )
                
                if other_half != '' and namespace != self._current_namespace:
                    
                    self._current_namespace = namespace # do a new search, no matter what half_complete tag is
                    
                    must_do_a_search = True
                    
                
            else: self._current_namespace = ''
            
            half_complete_tag = search_text
            
            if len( search_text ) < num_autocomplete_chars:
                
                predicates = HydrusGlobals.client_controller.Read( 'autocomplete_predicates', file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, tag = search_text, add_namespaceless = False )
                
            else:
                
                if must_do_a_search or self._cache_text == '' or not half_complete_tag.startswith( self._cache_text ):
                    
                    self._cache_text = half_complete_tag
                    
                    self._cached_results = HydrusGlobals.client_controller.Read( 'autocomplete_predicates', file_service_key = self._file_service_key, tag_service_key = self._tag_service_key, half_complete_tag = search_text, add_namespaceless = False )
                    
                
                predicates = self._cached_results
                
            
            predicates = ClientSearch.SortPredicates( predicates, collapse_siblings = False )
            
            matches = ClientSearch.FilterPredicates( half_complete_tag, predicates, service_key = self._tag_service_key, expand_parents = True )
            
            # do the 'put whatever they typed in at the top, whether it has count or not'
            # now with sibling support!
            # and parent support!
            # this is getting pretty ugly, and I should really move it into the matches processing, I think!
            
            top_predicates = []
            
            top_predicates.append( entry_predicate )
            
            if sibling_predicate is not None:
                
                top_predicates.append( sibling_predicate )
                
            
            for predicate in top_predicates:
                
                parents = []
                
                try:
                    
                    index = matches.index( predicate )
                    
                    predicate = matches[ index ]
                    
                    matches.remove( predicate )
                    
                    while matches[ index ].GetType() == HC.PREDICATE_TYPE_PARENT:
                        
                        parent = matches[ index ]
                        
                        matches.remove( parent )
                        
                        parents.append( parent )
                        
                    
                except:
                    
                    if predicate.GetType() == HC.PREDICATE_TYPE_TAG:
                        
                        tag = predicate.GetValue()
                        
                        parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                        
                        raw_parents = parents_manager.GetParents( self._tag_service_key, tag )
                        
                        parents = [ ClientData.Predicate( HC.PREDICATE_TYPE_PARENT, raw_parent ) for raw_parent in raw_parents ]
                        
                    
                
                parents.reverse()
                
                for parent in parents: matches.insert( 0, parent )
                
                matches.insert( 0, predicate )
                
            
        
        return matches
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        # when the user has quickly typed something in and the results are not yet in
        
        p1 = self._text_ctrl.GetValue() != '' and self._last_search_text == ''
        
        # when the text ctrl is empty and we want to push a None to the parent dialog
        
        p2 = self._text_ctrl.GetValue() == ''
        
        return p1 or p2
        
    
    def _TakeResponsibilityForEnter( self ):
        
        if self._text_ctrl.GetValue() == '':
            
            self._BroadcastChoice( None )
            
        else:
            
            self._BroadcastCurrentText()
            
        
    
class BufferedWindow( wx.Window ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Window.__init__( self, *args, **kwargs )
        
        if 'size' in kwargs:
            
            ( x, y ) = kwargs[ 'size' ]
            
            self._canvas_bmp = wx.EmptyBitmap( x, y, 24 )
            
        else: self._canvas_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def GetDC( self ): return wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
    
    def EventEraseBackground( self, event ): pass
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp )
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
        
        if my_width != current_bmp_width or my_height != current_bmp_height: self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
        
    
class BufferedWindowIcon( BufferedWindow ):
    
    def __init__( self, parent, bmp ):
        
        BufferedWindow.__init__( self, parent, size = bmp.GetSize() )
        
        self._bmp = bmp
        
        dc = self.GetDC()
        
        background_colour = self.GetParent().GetBackgroundColour()
        
        dc.SetBackground( wx.Brush( background_colour ) )
        
        dc.Clear()
        
        dc.DrawBitmap( bmp, 0, 0 )
        
    
class BetterChoice( wx.Choice ):
    
    def GetChoice( self ):
        
        selection = self.GetSelection()
        
        if selection != wx.NOT_FOUND: return self.GetClientData( selection )
        else: raise Exception( 'Choice not chosen!' )
        
    
    def SelectClientData( self, client_data ):
        
        for i in range( self.GetCount() ):
            
            if client_data == self.GetClientData( i ):
                
                self.Select( i )
                
                return
                
            
        
    
class CheckboxCollect( wx.combo.ComboCtrl ):
    
    def __init__( self, parent, page_key = None ):
        
        wx.combo.ComboCtrl.__init__( self, parent, style = wx.CB_READONLY )
        
        self._page_key = page_key
        
        sort_by = HC.options[ 'sort_by' ]
        
        collect_types = set()
        
        for ( sort_by_type, namespaces ) in sort_by: collect_types.update( namespaces )
        
        collect_types = list( [ ( namespace, ( 'namespace', namespace ) ) for namespace in collect_types ] )
        collect_types.sort()
        
        ratings_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for ratings_service in ratings_services: collect_types.append( ( ratings_service.GetName(), ( 'rating', ratings_service.GetServiceKey() ) ) )
        
        popup = self._Popup( collect_types )
        
        #self.UseAltPopupWindow( True )
        
        self.SetPopupControl( popup )
        
        ( collect_types, collect_type_strings ) = popup.GetControl().GetValue()
        
        self.SetCollectTypes( collect_types, collect_type_strings )
        
    
    def GetChoice( self ): return self._collect_by
    
    def SetCollectTypes( self, collect_types, collect_type_strings ):
        
        if len( collect_type_strings ) > 0:
            
            self.SetValue( 'collect by ' + '-'.join( collect_type_strings ) )
            
            self._collect_by = collect_types
            
        else:
            
            self.SetValue( 'no collections' )
            
            self._collect_by = None
            
        
        HydrusGlobals.client_controller.pub( 'collect_media', self._page_key, self._collect_by )
        
    
    class _Popup( wx.combo.ComboPopup ):
        
        def __init__( self, collect_types ):
            
            wx.combo.ComboPopup.__init__( self )
            
            self._collect_types = collect_types
            
        
        def Create( self, parent ):
            
            self._control = self._Control( parent, self.GetCombo(), self._collect_types )
            
            return True
            
        
        def GetAdjustedSize( self, preferred_width, preferred_height, max_height ):
            
            return( ( preferred_width, -1 ) )
            
        
        def GetControl( self ): return self._control
        
        class _Control( wx.CheckListBox ):
            
            def __init__( self, parent, special_parent, collect_types ):
                
                texts = [ text for ( text, data ) in collect_types ] # we do this so it sizes its height properly on init
                
                wx.CheckListBox.__init__( self, parent, choices = texts )
                
                self.Clear()
                
                for ( text, data ) in collect_types: self.Append( text, data )
                
                self._special_parent = special_parent
                
                default = HC.options[ 'default_collect' ]
                
                if default is not None:
                    
                    strings_we_added = { text for ( text, data ) in collect_types }
                    
                    strings_to_check = [ s for ( namespace_gumpf, s ) in default if s in strings_we_added ]
                    
                    self.SetCheckedStrings( strings_to_check )
                    
                
                self.Bind( wx.EVT_CHECKLISTBOX, self.EventChanged )
                
                self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
                
            
            # as inspired by http://trac.wxwidgets.org/attachment/ticket/14413/test_clb_workaround.py
            # what a clusterfuck
            
            def EventLeftDown( self, event ):
                
                index = self.HitTest( event.GetPosition() )
                
                if index != wx.NOT_FOUND:
                    
                    self.Check( index, not self.IsChecked( index ) )
                    
                    self.EventChanged( event )
                    
                
                event.Skip()
                
            
            def EventChanged( self, event ):
                
                ( collect_types, collect_type_strings ) = self.GetValue()
                
                self._special_parent.SetCollectTypes( collect_types, collect_type_strings )
                
            
            def GetValue( self ):
                
                collect_types = []
                
                for i in self.GetChecked(): collect_types.append( self.GetClientData( i ) )
                
                collect_type_strings = self.GetCheckedStrings()
                
                return ( collect_types, collect_type_strings )
                
            
        
    
class ChoiceSort( BetterChoice ):
    
    def __init__( self, parent, page_key = None, sort_by = None ):
        
        BetterChoice.__init__( self, parent )
        
        self._page_key = page_key
        
        if sort_by is None: sort_by = HC.options[ 'sort_by' ]
        
        sort_choices = CC.SORT_CHOICES + sort_by
        
        ratings_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for ratings_service in ratings_services:
            
            sort_choices.append( ( 'rating_descend', ratings_service ) )
            sort_choices.append( ( 'rating_ascend', ratings_service ) )
            
        
        for ( sort_by_type, sort_by_data ) in sort_choices:
            
            if sort_by_type == 'system': string = CC.sort_string_lookup[ sort_by_data ]
            elif sort_by_type == 'namespaces': string = '-'.join( sort_by_data )
            elif sort_by_type == 'rating_descend':
                
                string = sort_by_data.GetName() + ' rating highest first'
                
                sort_by_data = sort_by_data.GetServiceKey()
                
            elif sort_by_type == 'rating_ascend':
                
                string = sort_by_data.GetName() + ' rating lowest first'
                
                sort_by_data = sort_by_data.GetServiceKey()
                
            
            self.Append( 'sort by ' + string, ( sort_by_type, sort_by_data ) )
            
        
        try: self.SetSelection( HC.options[ 'default_sort' ] )
        except: pass
        
        self.Bind( wx.EVT_CHOICE, self.EventChoice )
        
        HydrusGlobals.client_controller.sub( self, 'ACollectHappened', 'collect_media' )
        
    
    def _BroadcastSort( self ):
        
        selection = self.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            sort_by = self.GetClientData( selection )
            
            HydrusGlobals.client_controller.pub( 'sort_media', self._page_key, sort_by )
            
        
    
    def ACollectHappened( self, page_key, collect_by ):
        
        if page_key == self._page_key: self._BroadcastSort()
        
    
    def EventChoice( self, event ):
        
        if self._page_key is not None: self._BroadcastSort()
        
    
class ExportPatternButton( wx.Button ):
    
    ID_HASH = 0
    ID_TAGS = 1
    ID_NN_TAGS = 2
    ID_NAMESPACE = 3
    ID_TAG = 4
    
    def __init__( self, parent ):
        
        wx.Button.__init__( self, parent, label = 'pattern shortcuts' )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def EventMenu( self, event ):
        
        id = event.GetId()
        
        phrase = None
        
        if id == self.ID_HASH: phrase = '{hash}'
        if id == self.ID_TAGS: phrase = '{tags}'
        if id == self.ID_NN_TAGS: phrase = '{nn tags}'
        if id == self.ID_NAMESPACE: phrase = '[...]'
        if id == self.ID_TAG: phrase = '(...)'
        else: event.Skip()
        
        if phrase is not None: HydrusGlobals.client_controller.pub( 'clipboard', 'text', phrase )
        
    
    def EventButton( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( -1, 'click on a phrase to copy to clipboard' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_HASH, 'the file\'s hash - {hash}' )
        menu.Append( self.ID_TAGS, 'all the file\'s tags - {tags}' )
        menu.Append( self.ID_NN_TAGS, 'all the file\'s non-namespaced tags - {nn tags}' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_NAMESPACE, 'all instances of a particular namespace - [...]' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_TAG, 'a particular tag, if the file has it - (...)' )
        
        self.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
class FitResistantStaticText( wx.StaticText ):
    
    # this is a huge damn mess! I think I really need to be doing this inside or before the parent's fit, or something
    
    def __init__( self, *args, **kwargs ):
        
        wx.StaticText.__init__( self, *args, **kwargs )
        
        self._wrap = 380
        
        if 'label' in kwargs: self._last_label = kwargs[ 'label' ]
        else: self._last_label = ''
        
    
    def Wrap( self, width ):
        
        self._wrap = width
        
        wx.StaticText.Wrap( self, self._wrap )
        
        ( x, y ) = self.GetSize()
        
        if x > self._wrap: x = self._wrap
        if x < 150: x = 150
        
        self.SetMinSize( ( x, y ) )
        self.SetMaxSize( ( self._wrap, -1 ) )
        
    
    def SetLabel( self, label ):
        
        if label != self._last_label:
            
            self._last_label = label
            
            wx.StaticText.SetLabel( self, label )
            
            self.Wrap( self._wrap )
            
        
    
class Frame( wx.Frame ):
    
    def __init__( self, *args, **kwargs ):
        
        HydrusGlobals.client_controller.ResetIdleTimer()
        
        wx.Frame.__init__( self, *args, **kwargs )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
    
    def SetInitialSize( self, ( width, height ) ):
        
        wx.Frame.SetInitialSize( self, ( width, height ) )
        
        min_width = min( 240, width )
        min_height = min( 180, height )
        
        self.SetMinSize( ( min_width, min_height ) )
        
    
class FrameThatResizes( Frame ):
    
    def __init__( self, *args, **kwargs ):
        
        self._resize_option_prefix = kwargs[ 'resize_option_prefix' ]
        
        del kwargs[ 'resize_option_prefix' ]
        
        Frame.__init__( self, *args, **kwargs )
        
        self._InitialiseSizeAndPosition()
        
        self.Bind( wx.EVT_SIZE, self.EventSpecialResize )
        self.Bind( wx.EVT_MOVE, self.EventSpecialMove )
        
    
    def _InitialiseSizeAndPosition( self ):
        
        client_size = HC.options[ 'client_size' ]
        
        self.SetInitialSize( client_size[ self._resize_option_prefix + 'restored_size' ] )
        
        position = client_size[ self._resize_option_prefix + 'restored_position' ]
        
        display_index = wx.Display.GetFromPoint( position )
        
        if display_index == wx.NOT_FOUND: client_size[ self._resize_option_prefix + 'restored_position' ] = ( 20, 20 )
        else:
            
            display = wx.Display( display_index )
            
            geometry = display.GetGeometry()
            
            ( p_x, p_y ) = position
            
            x_bad = p_x < geometry.x or p_x > geometry.x + geometry.width
            y_bad = p_y < geometry.y or p_y > geometry.y + geometry.height
            
            if x_bad or y_bad: client_size[ self._resize_option_prefix + 'restored_position' ] = ( 20, 20 )
            
        
        self.SetPosition( client_size[ self._resize_option_prefix + 'restored_position' ] )
        
        if client_size[ self._resize_option_prefix + 'maximised' ]: self.Maximize()
        
        if client_size[ self._resize_option_prefix + 'fullscreen' ]: wx.CallAfter( self.ShowFullScreen, True, wx.FULLSCREEN_ALL )
        
    
    def _RecordSizeAndPosition( self ):
        
        client_size = HC.options[ 'client_size' ]
        
        client_size[ self._resize_option_prefix + 'maximised' ] = self.IsMaximized()
        client_size[ self._resize_option_prefix + 'fullscreen' ] = self.IsFullScreen()
        
        if not ( self.IsMaximized() or self.IsFullScreen() ):
            
            # when dragging window up to be maximised, reported position is sometimes a bit dodgy
            
            display_index = wx.Display.GetFromPoint( self.GetPosition() )
            
            if display_index != wx.NOT_FOUND:
                
                client_size[ self._resize_option_prefix + 'restored_size' ] = tuple( self.GetSize() )
                
                client_size[ self._resize_option_prefix + 'restored_position' ] = tuple( self.GetPosition() )
                
            
        
    
    def EventSpecialMove( self, event ):
        
        self._RecordSizeAndPosition()
        
        event.Skip()
        
    
    def EventSpecialResize( self, event ):
        
        self._RecordSizeAndPosition()
        
        event.Skip()
        
    
class Gauge( wx.Gauge ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Gauge.__init__( self, *args, **kwargs )
        
        self._actual_max = None
        
    
    def SetRange( self, max ):
        
        if max > 1000:
            
            self._actual_max = max
            wx.Gauge.SetRange( self, 1000 )
            
        else:
            
            self._actual_max = None
            wx.Gauge.SetRange( self, max )
            
        
    
    def SetValue( self, value ):
        
        if self._actual_max is None: wx.Gauge.SetValue( self, value )
        else: wx.Gauge.SetValue( self, min( int( 1000 * ( float( value ) / self._actual_max ) ), 1000 ) )
        
    
class ListBook( wx.Panel ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Panel.__init__( self, *args, **kwargs )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self._names_to_active_pages = {}
        self._names_to_proto_pages = {}
        
        self._list_box = self.LB( self, style = wx.LB_SINGLE | wx.LB_SORT )
        
        self._empty_panel = wx.Panel( self )
        
        self._empty_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self._current_name = None
        
        self._current_panel = self._empty_panel
        
        self._panel_sizer = wx.BoxSizer( wx.VERTICAL )
        
        self._panel_sizer.AddF( self._empty_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._list_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        hbox.AddF( self._panel_sizer, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._list_box.Bind( wx.EVT_LISTBOX, self.EventSelection )
        
        self.SetSizer( hbox )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    class LB( wx.ListBox ):
        
        def FindString( self, name ):
            
            if HC.PLATFORM_WINDOWS: return wx.ListBox.FindString( self, name )
            else:
                
                for i in range( self.GetCount() ):
                    
                    if self.GetString( i ) == name: return i
                    
                
                return wx.NOT_FOUND
                
            
        
    
    def _RecalcListBoxWidth( self ): self.Layout()
    
    def _Select( self, selection ):
        
        if selection == wx.NOT_FOUND: self._current_name = None
        else: self._current_name = self._list_box.GetString( selection )
        
        self._current_panel.Hide()
        
        self._list_box.SetSelection( selection )
        
        if selection == wx.NOT_FOUND: self._current_panel = self._empty_panel
        else:
            
            if self._current_name in self._names_to_proto_pages:
                
                ( classname, args, kwargs ) = self._names_to_proto_pages[ self._current_name ]
                
                page = classname( *args, **kwargs )
                
                page.Hide()
                
                self._panel_sizer.AddF( page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                self._names_to_active_pages[ self._current_name ] = page
                
                del self._names_to_proto_pages[ self._current_name ]
                
                self._RecalcListBoxWidth()
                
            
            self._current_panel = self._names_to_active_pages[ self._current_name ]
            
        
        self._current_panel.Show()
        
        self.Layout()
        
        self.Refresh()
        
        event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGED, -1 )
        
        self.ProcessEvent( event )
        
    
    def AddPage( self, name, page, select = False ):
        
        if type( page ) != tuple:
            
            page.Hide()
            
            self._panel_sizer.AddF( page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        self._list_box.Append( name )
        
        self._names_to_active_pages[ name ] = page
        
        self._RecalcListBoxWidth()
        
        if self._list_box.GetCount() == 1: self._Select( 0 )
        elif select: self._Select( self._list_box.FindString( name ) )
        
    
    def AddPageArgs( self, name, classname, args, kwargs ):
        
        if self.NameExists( name ):
            
            raise HydrusExceptions.NameException( 'That name is already in use!' )
            
        
        self._list_box.Append( name )
        
        self._names_to_proto_pages[ name ] = ( classname, args, kwargs )
        
        self._RecalcListBoxWidth()
        
        if self._list_box.GetCount() == 1: self._Select( 0 )
        
    
    def DeleteAllPages( self ):
        
        self._panel_sizer.Detach( self._empty_panel )
        
        self._panel_sizer.Clear( deleteWindows = True )
        
        self._panel_sizer.AddF( self._empty_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._current_name = None
        
        self._current_panel = self._empty_panel
        
        self._names_to_active_pages = {}
        self._names_to_proto_pages = {}
        
        self._list_box.Clear()
        
    
    def DeleteCurrentPage( self ):
        
        selection = self._list_box.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            name_to_delete = self._current_name
            page_to_delete = self._current_panel
            
            next_selection = selection + 1
            previous_selection = selection - 1
            
            if next_selection < self._list_box.GetCount(): self._Select( next_selection )
            elif previous_selection >= 0: self._Select( previous_selection )
            else: self._Select( wx.NOT_FOUND )
            
            self._panel_sizer.Detach( page_to_delete )
            
            wx.CallAfter( page_to_delete.Destroy )
            
            del self._names_to_active_pages[ name_to_delete ]
            
            self._list_box.Delete( self._list_box.FindString( name_to_delete ) )
            
            self._RecalcListBoxWidth()
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'select_down': self.SelectDown()
            elif command == 'select_up': self.SelectUp()
            else: event.Skip()
            
        
    
    def EventSelection( self, event ):
        
        if self._list_box.GetSelection() != self._list_box.FindString( self._current_name ):
            
            event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING, -1 )
            
            self.GetEventHandler().ProcessEvent( event )
            
            if event.IsAllowed(): self._Select( self._list_box.GetSelection() )
            else: self._list_box.SetSelection( self._list_box.FindString( self._current_name ) )
            
        
    
    def GetCurrentName( self ): return self._current_name
    
    def GetCurrentPage( self ):
        
        if self._current_panel == self._empty_panel: return None
        else: return self._current_panel
        
    
    def GetNames( self ):
        
        names = set()
        
        names.update( self._names_to_proto_pages.keys() )
        names.update( self._names_to_active_pages.keys() )
        
        return names
        
    
    def GetNamesToActivePages( self ):
        
        return self._names_to_active_pages
        
    
    def NameExists( self, name ): return self._list_box.FindString( name ) != wx.NOT_FOUND
    
    def RenamePage( self, name, new_name ):
        
        if self.NameExists( new_name ): raise HydrusExceptions.NameException( 'That name is already in use!' )
        
        if self._current_name == name: self._current_name = new_name
        
        if name in self._names_to_active_pages:
            
            dict_to_rename = self._names_to_active_pages
            
        else:
            
            dict_to_rename = self._names_to_proto_pages
            
        
        page_info = dict_to_rename[ name ]
        
        del dict_to_rename[ name ]
        
        dict_to_rename[ new_name ] = page_info
        
        self._list_box.SetString( self._list_box.FindString( name ), new_name )
        
        self._RecalcListBoxWidth()
        
    
    def Select( self, name ):
        
        selection = self._list_box.FindString( name )
        
        if selection != wx.NOT_FOUND and selection != self._list_box.GetSelection():
            
            event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING, -1 )
            
            self.GetEventHandler().ProcessEvent( event )
            
            if event.IsAllowed(): self._Select( selection )
            
        
    
    def SelectDown( self ):
        
        current_selection = self._list_box.FindString( self._current_name )
        
        if current_selection != wx.NOT_FOUND:
            
            num_entries = self._list_box.GetCount()
            
            if current_selection == num_entries - 1: selection = 0
            else: selection = current_selection + 1
            
            if selection != current_selection: self._Select( selection )
            
        
    
    def SelectPage( self, page_to_select ):
        
        for ( name, page ) in self._names_to_active_pages.items():
            
            if page == page_to_select:
                
                self._Select( self._list_box.FindString( name ) )
                
                return
                
            
        
    
    def SelectUp( self ):
        
        current_selection = self._list_box.FindString( self._current_name )
        
        if current_selection != wx.NOT_FOUND:
            
            num_entries = self._list_box.GetCount()
            
            if current_selection == 0: selection = num_entries - 1
            else: selection = current_selection - 1
            
            if selection != current_selection: self._Select( selection )
            
        
    
class ListBox( wx.ScrolledWindow ):
    
    def __init__( self, parent, min_height = 250 ):
        
        wx.ScrolledWindow.__init__( self, parent, style = wx.VSCROLL | wx.BORDER_DOUBLE )
        
        self._background_colour = wx.Colour( 255, 255, 255 )
        
        self._ordered_strings = []
        self._strings_to_terms = {}
        
        self._client_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self._current_selected_index = None
        self._current_selected_term = None
        
        self._last_view_start = None
        self._dirty = True
        
        dc = wx.MemoryDC( self._client_bmp )
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        ( text_x, self._text_y ) = dc.GetTextExtent( 'abcdefghijklmnopqrstuvwxyz' )
        
        self._num_rows_per_page = 0
        
        self.SetScrollRate( 0, self._text_y )
        
        self.SetMinSize( ( 50, min_height ) )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventMouseSelect )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventDClick )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventMouseRightClick )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        self.Bind( wx.EVT_CHAR_HOOK, self.EventKeyDown )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def __len__( self ): return len( self._ordered_strings )
    
    def _Activate( self, s, term ): pass
    
    def _GetIndexUnderMouse( self, mouse_event ):
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        ( x_scroll, y_scroll ) = self.GetViewStart()
        
        y_offset = y_scroll * yUnit
        
        y = mouse_event.GetY() + y_offset
        
        row_index = ( y / self._text_y )
        
        if row_index >= len( self._ordered_strings ): return None
        
        return row_index
        
    
    def _GetTextColour( self, text ): return ( 0, 111, 250 )
    
    def _Redraw( self, dc ):
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        ( x_scroll, y_scroll ) = self.GetViewStart()
        
        self._last_view_start = self.GetViewStart()
        
        y_offset = y_scroll * yUnit
        
        ( my_width, my_height ) = self.GetClientSize()
        
        first_visible_index = y_offset / self._text_y
        
        last_visible_index = ( y_offset + my_height ) / self._text_y
        
        if ( y_offset + my_height ) % self._text_y != 0:
            
            last_visible_index += 1
            
        
        last_visible_index = min( last_visible_index, len( self._ordered_strings ) - 1 )
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        dc.SetBackground( wx.Brush( self._background_colour ) )
        
        dc.Clear()
        
        for ( i, current_index ) in enumerate( range( first_visible_index, last_visible_index + 1 ) ):
            
            text = self._ordered_strings[ current_index ]
            
            ( r, g, b ) = self._GetTextColour( text )
            
            text_colour = wx.Colour( r, g, b )
            
            if self._current_selected_index is not None and current_index == self._current_selected_index:
                
                dc.SetBrush( wx.Brush( text_colour ) )
                
                dc.SetPen( wx.TRANSPARENT_PEN )
                
                dc.DrawRectangle( 0, i * self._text_y, my_width, self._text_y )
                
                text_colour = wx.WHITE
                
            
            dc.SetTextForeground( text_colour )
            
            ( x, y ) = ( 3, i * self._text_y )
            
            dc.DrawText( text, x, y )
            
        
        self._dirty = False
        
    
    def _Select( self, index ):
        
        old_index = self._current_selected_index
        
        if index is not None:
            
            if index == -1 or index > len( self._ordered_strings ): index = len( self._ordered_strings ) - 1
            elif index == len( self._ordered_strings ) or index < -1: index = 0
            
        
        self._current_selected_index = index
        
        if self._current_selected_index is None:
            
            self._current_selected_term = None
            
        else:
            
            self._current_selected_term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
            
            # scroll to index, if needed
            
            y = self._text_y * self._current_selected_index
            
            ( start_x, start_y ) = self.GetViewStart()
            
            ( x_unit, y_unit ) = self.GetScrollPixelsPerUnit()
            
            ( width, height ) = self.GetClientSize()
            
            if y < start_y * y_unit:
                
                y_to_scroll_to = y / y_unit
                
                self.Scroll( -1, y_to_scroll_to )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE ) )
                
            elif y > ( start_y * y_unit ) + height - self._text_y:
                
                y_to_scroll_to = ( y - height ) / y_unit
                
                self.Scroll( -1, y_to_scroll_to + 2 )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE ) )
                
            
        
        self._SetDirty()
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
        self.Refresh()
        
    
    def _TextsHaveChanged( self ):
        
        self._current_selected_index = None
        
        if self._current_selected_term is not None:
            
            for ( s, term ) in self._strings_to_terms.items():
                
                if term == self._current_selected_term:
                    
                    self._current_selected_index = self._ordered_strings.index( s )
                    
                    break
                    
                
            
            if self._current_selected_index is None: self._current_selected_term = None
            
        
        ( my_x, my_y ) = self.GetClientSize()
        
        total_height = max( self._text_y * len( self._ordered_strings ), my_y )
        
        ( virtual_x, virtual_y ) = self.GetVirtualSize()
        
        if total_height != virtual_y:
            
            wx.PostEvent( self, wx.SizeEvent() )
            
        else:
            
            self._SetDirty()
            
        
    
    def EventDClick( self, event ):
        
        index = self._GetIndexUnderMouse( event )
        
        if index is not None and index == self._current_selected_index:
            
            s = self._ordered_strings[ self._current_selected_index ]
            
            term = self._strings_to_terms[ s ]
            
            self._Activate( s, term )
            
        
    
    def EventEraseBackground( self, event ): pass
    
    def EventKeyDown( self, event ):
        
        key_code = event.GetKeyCode()
        
        if self._current_selected_index is not None:
            
            if key_code in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                s = self._ordered_strings[ self._current_selected_index ]
                
                term = self._strings_to_terms[ s ]
                
                self._Activate( s, term )
                
            elif key_code in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ): self._Select( self._current_selected_index - 1 )
            elif key_code in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ): self._Select( self._current_selected_index + 1 )
            elif key_code in ( wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP ): self._Select( self._current_selected_index - self._num_rows_per_page )
            elif key_code in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN ): self._Select( self._current_selected_index + self._num_rows_per_page )
            elif key_code in ( wx.WXK_HOME, wx.WXK_NUMPAD_HOME ): self._Select( 0 )
            elif key_code in ( wx.WXK_END, wx.WXK_NUMPAD_END ): self._Select( len( self._ordered_strings ) - 1 )
            else: event.Skip()
            
        else: event.Skip()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'copy_term':
                
                term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
                
                HydrusGlobals.client_controller.pub( 'clipboard', 'text', term )
                
            elif command == 'copy_sub_term':
                
                term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
                
                sub_term = term.split( ':', 1 )[1]
                
                HydrusGlobals.client_controller.pub( 'clipboard', 'text', sub_term )
                
            else:
                
                event.Skip()
                
                return # this is about select_up and select_down
                
            
        
    
    def EventMouseRightClick( self, event ):
        
        index = self._GetIndexUnderMouse( event )
        
        self._Select( index )
        
        if self._current_selected_index is not None:
            
            menu = wx.Menu()
            
            term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_term' ), 'copy "' + term + '"' )
            
            if ':' in term:
                
                sub_term = term.split( ':', 1 )[1]
                
                menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_sub_term' ), 'copy "' + sub_term + '"' )
                
            
            self.PopupMenu( menu )
            
            wx.CallAfter( menu.Destroy )
            
        
        event.Skip()
        
    
    def EventMouseSelect( self, event ):
        
        index = self._GetIndexUnderMouse( event )
        
        self._Select( index )
        
        event.Skip()
        
    
    def EventPaint( self, event ):
        
        ( my_x, my_y ) = self.GetClientSize()
        
        if ( my_x, my_y ) != self._client_bmp.GetSize():
            
            self._client_bmp = wx.EmptyBitmap( my_x, my_y, 24 )
            
            self._dirty = True
            
        
        dc = wx.BufferedPaintDC( self, self._client_bmp )
        
        if self._dirty or self._last_view_start != self.GetViewStart():
            
            self._Redraw( dc )
            
        
    
    def EventResize( self, event ):
        
        ( my_x, my_y ) = self.GetClientSize()
        
        self._num_rows_per_page = my_y / self._text_y
        
        ideal_virtual_size = ( my_x, max( self._text_y * len( self._ordered_strings ), my_y ) )
        
        if ideal_virtual_size != self.GetVirtualSize():
            
            self.SetVirtualSize( ideal_virtual_size )
            
        
        self._SetDirty()
        
    
    def GetClientData( self, s = None ):
        
        if s is None: return self._strings_to_terms.values()
        else: return self._strings_to_terms[ s ]
        
    
    def SetTexts( self, ordered_strings ):
        
        if ordered_strings != self._ordered_strings:
            
            self._ordered_strings = ordered_strings
            self._strings_to_terms = { s : s for s in ordered_strings }
            
            self._TextsHaveChanged()
            
            if len( ordered_strings ) > 0: self._Select( 0 )
            
        
    
class ListBoxMessages( ListBox ):
    
    def _GetTextColour( self, predicate_string ):
        
        if predicate_string.startswith( 'system:' ): ( r, g, b ) = ( 153, 101, 21 )
        else: ( r, g, b ) = ( 0, 111, 250 )
        
        return ( r, g, b )
        
    
class ListBoxMessagesActiveOnly( ListBoxMessages ):
    
    def __init__( self, parent, callable ):
        
        ListBoxMessages.__init__( self, parent )
        
        self._callable = callable
        
        self._matches = {}
        
    
    def _Activate( self, s, term ): self._callable( term )
    
    def SetTerms( self, matches ):
        
        if matches != self._matches:
            
            self._matches = matches
            
            self._ordered_strings = []
            self._strings_to_terms = {}
            
            for ( term, count ) in matches:
                
                if count is None: term_string = term
                else: term_string = term + ' (' + HydrusData.ConvertIntToPrettyString( count ) + ')'
                
                self._ordered_strings.append( term_string )
                self._strings_to_terms[ term_string ] = term
                
            
            self._TextsHaveChanged()
            
            if len( matches ) > 0: self._Select( 0 )
            
        
    
class ListBoxMessagesPredicates( ListBoxMessages ):
    
    def __init__( self, parent, page_key, initial_predicates = None ):
        
        if initial_predicates is None: initial_predicates = []
        
        ListBoxMessages.__init__( self, parent )
        
        self._page_key = page_key
        
        if len( initial_predicates ) > 0:
            
            for predicate in initial_predicates:
                
                self._ordered_strings.append( predicate )
                self._strings_to_terms[ predicate ] = predicate
                
            
            self._TextsHaveChanged()
            
        
    
    def _Activate( self, s, term ): HydrusGlobals.client_controller.pub( 'remove_predicate', self._page_key, term )
    
    def ActivatePredicate( self, term ):
        
        if term in self._ordered_strings:
            
            self._ordered_strings.remove( term )
            del self._strings_to_terms[ term ]
            
        else:
            
            if term == 'system:inbox' and 'system:archive' in self._ordered_strings: self._ordered_strings.remove( 'system:archive' )
            elif term == 'system:archive' and 'system:inbox' in self._ordered_strings: self._ordered_strings.remove( 'system:inbox' )
            
            self._ordered_strings.append( term )
            self._strings_to_terms[ term ] = term
            
            self._ordered_strings.sort()
            
        
        self._TextsHaveChanged()
        
    
    def AddPredicate( self, predicate ):
        
        self._ordered_strings.append( predicate )
        self._strings_to_terms[ predicate ] = predicate
        
        self._ordered_strings.sort()
        
        self._TextsHaveChanged()
        
    
    def GetPredicates( self ): return self._ordered_strings
    
    def HasPredicate( self, predicate ): return predicate in self._ordered_strings
    
    def RemovePredicate( self, predicate ):
        
        self._ordered_strings.remove( predicate )
        del self._strings_to_terms[ predicate ]
        
        self._TextsHaveChanged()
        
    
class ListBoxTags( ListBox ):
    
    has_counts = False
    
    def __init__( self, *args, **kwargs ):
        
        ListBox.__init__( self, *args, **kwargs )
        
        self._background_colour = wx.Colour( *HC.options[ 'gui_colours' ][ 'tags_box' ] )
        
    
    def _GetNamespaceColours( self ): return HC.options[ 'namespace_colours' ]
    
    def _GetAllTagsForClipboard( self, with_counts = False ): return self._ordered_strings
    
    def _GetTextColour( self, tag_string ):
        
        namespace_colours = self._GetNamespaceColours()
        
        if ':' in tag_string:
            
            ( namespace, sub_tag ) = tag_string.split( ':', 1 )
            
            if namespace.startswith( '-' ): namespace = namespace[1:]
            if namespace.startswith( '(+) ' ): namespace = namespace[4:]
            if namespace.startswith( '(-) ' ): namespace = namespace[4:]
            if namespace.startswith( '(X) ' ): namespace = namespace[4:]
            if namespace.startswith( '    ' ): namespace = namespace[4:]
            
            if namespace in namespace_colours: ( r, g, b ) = namespace_colours[ namespace ]
            else: ( r, g, b ) = namespace_colours[ None ]
            
        else: ( r, g, b ) = namespace_colours[ '' ]
        
        return ( r, g, b )
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'copy_term':
                
                term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
                
                if type( term ) == ClientData.Predicate: s = term.GetUnicode()
                else: s = term
                
                HydrusGlobals.client_controller.pub( 'clipboard', 'text', s )
                
            elif command == 'copy_sub_term':
                
                term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
                
                if type( term ) == ClientData.Predicate: s = term.GetUnicode()
                else: s = term
                
                sub_s = s.split( ':', 1 )[1]
                
                HydrusGlobals.client_controller.pub( 'clipboard', 'text', sub_s )
                
            elif command == 'copy_all_tags': HydrusGlobals.client_controller.pub( 'clipboard', 'text', os.linesep.join( self._GetAllTagsForClipboard() ) )
            elif command == 'copy_all_tags_with_counts': HydrusGlobals.client_controller.pub( 'clipboard', 'text', os.linesep.join( self._GetAllTagsForClipboard( with_counts = True ) ) )
            elif command == 'new_search_page_with_term':
                
                term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
                
                if type( term ) == ClientData.Predicate: predicate = term
                else: predicate = ClientData.Predicate( HC.PREDICATE_TYPE_TAG, term )
                
                HydrusGlobals.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_predicates = [ predicate ] )
                
            elif command in ( 'parent', 'sibling' ):
                
                tag = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
                
                import ClientGUIDialogsManage
                
                if command == 'parent':
                    
                    with ClientGUIDialogsManage.DialogManageTagParents( self, tag ) as dlg: dlg.ShowModal()
                    
                elif command == 'sibling':
                    
                    with ClientGUIDialogsManage.DialogManageTagSiblings( self, tag ) as dlg: dlg.ShowModal()
                    
                
            else:
                
                event.Skip()
                
                return # this is about select_up and select_down
                
            
        
    
    def EventMouseRightClick( self, event ):
        
        index = self._GetIndexUnderMouse( event )
        
        self._Select( index )
        
        if len( self._ordered_strings ) > 0:
        
            menu = wx.Menu()
            
            if self._current_selected_index is not None:
                
                term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
                
                if type( term ) == ClientData.Predicate: s = term.GetUnicode()
                else: s = term
                
                menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'new_search_page_with_term' ), 'open a new search page for "' + s + '"' )
                
                menu.AppendSeparator()
                
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_all_tags' ), 'copy all tags' )
            if self.has_counts: menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_all_tags_with_counts' ), 'copy all tags with counts' )
            
            if self._current_selected_index is not None:
                
                term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
                
                if type( term ) == ClientData.Predicate: s = term.GetUnicode()
                else: s = term
                
                menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_term' ), 'copy "' + s + '"' )
                
                if ':' in s:
                    
                    sub_s = s.split( ':', 1 )[1]
                    
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_sub_term' ), 'copy "' + sub_s + '"' )
                    
                
                if type( term ) in ( str, unicode ):
                    
                    menu.AppendSeparator()
                    
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'parent' ), 'add parent to ' + s )
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'sibling' ), 'add sibling to ' + s )
                    
                
            
            self.PopupMenu( menu )
            
            wx.CallAfter( menu.Destroy )
            
        
        event.Skip()
        
    
    def GetSelectedTag( self ):
        
        if self._current_selected_index is not None: return self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
        else: return None
        
    
class ListBoxTagsAutocompleteDropdown( ListBoxTags ):
    
    has_counts = True
    
    def __init__( self, parent, callable, **kwargs ):
        
        ListBoxTags.__init__( self, parent, **kwargs )
        
        self._callable = callable
        
        self._predicates = {}
        
    
    def _Activate( self, s, term ): self._callable( term )
    
    def _GetAllTagsForClipboard( self, with_counts = False ):
        
        return [ self._strings_to_terms[ s ].GetUnicode( with_counts ) for s in self._ordered_strings ]
        
    
    def _Select( self, index ):
        
        if index is not None:
            
            if self._current_selected_index is None: direction = 1
            elif index - self._current_selected_index in ( -1, 1 ): direction = index - self._current_selected_index
            else: direction = 1
            
            if index == -1 or index > len( self._ordered_strings ): index = len( self._ordered_strings ) - 1
            elif index == len( self._ordered_strings ) or index < -1: index = 0
            
            s = self._ordered_strings[ index ]
            
            new_term = self._strings_to_terms[ s ]
            
            while new_term.GetType() == HC.PREDICATE_TYPE_PARENT:
                
                index += direction
                
                if index == -1 or index > len( self._ordered_strings ): index = len( self._ordered_strings ) - 1
                elif index == len( self._ordered_strings ) or index < -1: index = 0
                
                s = self._ordered_strings[ index ]
                
                new_term = self._strings_to_terms[ s ]
                
            
        
        ListBoxTags._Select( self, index )
        
    
    def SetPredicates( self, predicates ):
        
        # need to do a clever compare, since normal predicate compare doesn't take count into account
        
        they_are_the_same = True
        
        if len( predicates ) == len( self._predicates ):
            
            p_list_1 = list( predicates )
            p_list_2 = list( self._predicates )
            
            p_list_1.sort()
            p_list_2.sort()
            
            for index in range( len( p_list_1 ) ):
                
                p_1 = p_list_1[ index ]
                p_2 = p_list_2[ index ]
                
                if p_1 != p_2 or p_1.GetCount() != p_2.GetCount():
                    
                    they_are_the_same = False
                    
                    break
                    
                
            
        else: they_are_the_same = False
        
        if not they_are_the_same:
            
            self._predicates = predicates
            
            self._ordered_strings = []
            self._strings_to_terms = {}
            
            for predicate in predicates:
                
                tag_string = predicate.GetUnicode()
                
                self._ordered_strings.append( tag_string )
                self._strings_to_terms[ tag_string ] = predicate
                
            
            self._TextsHaveChanged()
            
            if len( predicates ) > 0: self._Select( 0 )
            
        
    
class ListBoxTagsCensorship( ListBoxTags ):
    
    def _Activate( self, s, term ): self.RemoveTag( term )
    
    def _GetTagString( self, tag ):
        
        if tag == '': return 'unnamespaced'
        elif tag == ':': return 'namespaced'
        else: return tag
        
    
    def AddTag( self, tag ):
        
        tag_string = self._GetTagString( tag )
        
        if tag_string in self._strings_to_terms: self.RemoveTag( tag )
        else:
            
            self._ordered_strings.append( tag_string )
            self._strings_to_terms[ tag_string ] = tag
            
            self._TextsHaveChanged()
            
        
    
    def RemoveTag( self, tag ):
        
        tag_string = self._GetTagString( tag )
        
        self._ordered_strings.remove( tag_string )
        
        del self._strings_to_terms[ tag_string ]
        
        self._TextsHaveChanged()
        
    
class ListBoxTagsColourOptions( ListBoxTags ):
    
    def __init__( self, parent, initial_namespace_colours ):
        
        ListBoxTags.__init__( self, parent )
        
        self._namespace_colours = dict( initial_namespace_colours )
        
        for namespace in self._namespace_colours:
            
            if namespace is None: namespace_string = 'default namespace:tag'
            elif namespace == '': namespace_string = 'unnamespaced tag'
            else: namespace_string = namespace + ':tag'
            
            self._ordered_strings.append( namespace_string )
            self._strings_to_terms[ namespace_string ] = namespace
            
        
        self._TextsHaveChanged()
        
    
    def _Activate( self, s, term ): self.RemoveNamespace( term )
    
    def _GetNamespaceColours( self ): return self._namespace_colours
    
    def SetNamespaceColour( self, namespace, colour ):
        
        if namespace not in self._namespace_colours:
            
            namespace_string = namespace + ':tag'
            
            self._ordered_strings.append( namespace_string )
            self._strings_to_terms[ namespace_string ] = namespace
            
            self._ordered_strings.sort()
            
        
        self._namespace_colours[ namespace ] = colour.Get()
        
        self._TextsHaveChanged()
        
    
    def GetNamespaceColours( self ): return self._namespace_colours
    
    def GetSelectedNamespaceColour( self ):
        
        if self._current_selected_index is not None:
            
            namespace_string = self._ordered_strings[ self._current_selected_index ]
            
            namespace = self._strings_to_terms[ namespace_string ]
            
            ( r, g, b ) = self._namespace_colours[ namespace ]
            
            colour = wx.Colour( r, g, b )
            
            return ( namespace, colour )
            
        
        return None
        
    
    def RemoveNamespace( self, namespace ):
        
        if namespace is not None and namespace != '':
            
            namespace_string = namespace + ':tag'
            
            self._ordered_strings.remove( namespace_string )
            
            del self._strings_to_terms[ namespace_string ]
            
            del self._namespace_colours[ namespace ]
            
            self._TextsHaveChanged()
            
        
    
class ListBoxTagsStrings( ListBoxTags ):
    
    def __init__( self, parent, removed_callable = None ):
        
        ListBoxTags.__init__( self, parent )
        
        self._removed_callable = removed_callable
        self._tags = set()
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
    
    def _GetAllTagsForClipboard( self, with_counts = False ):
        
        tags = list( self._tags )
        
        tags.sort()
        
        return tags
        
    
    def _RecalcTags( self ):
        
        self._strings_to_terms = {}
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        for tag in self._tags:
            
            tag_string = tag
            
            sibling = siblings_manager.GetSibling( tag )
            
            if sibling is not None: tag_string += ' (will display as ' + sibling + ')'
            
            self._strings_to_terms[ tag_string ] = tag
            
        
        self._ordered_strings = self._strings_to_terms.keys()
        
        self._ordered_strings.sort()
        
        self._TextsHaveChanged()
        
    
    def _Activate( self, s, tag ): self._RemoveTag( tag )
    
    def _RemoveTag( self, tag ):
        
        if tag in self._tags:
            
            self._tags.discard( tag )
            
            self._RecalcTags()
            
            if self._removed_callable is not None:
                
                self._removed_callable( tag )
                
            
        
    
    def AddTag( self, tag, parents = None ):
        
        if parents is None: parents = []
        
        if tag in self._tags: self._tags.discard( tag )
        else:
            
            self._tags.add( tag )
            
            self._tags.update( parents )
            
        
        self._RecalcTags()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE ):
            
            tag = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
            
            self._RemoveTag( tag )
            
        else: event.Skip()
        
    
    def GetTags( self ): return self._tags
    
    def SetTags( self, tags ):
        
        self._tags = set()
        
        for tag in tags: self._tags.add( tag )
        
        self._RecalcTags()
        
    
class ListBoxTagsPredicates( ListBoxTags ):
    
    has_counts = False
    
    def __init__( self, parent, page_key, initial_predicates = None ):
        
        if initial_predicates is None: initial_predicates = []
        
        ListBoxTags.__init__( self, parent, min_height = 100 )
        
        self._page_key = page_key
        
        if len( initial_predicates ) > 0:
            
            for predicate in initial_predicates:
                
                predicate_string = predicate.GetUnicode()
                
                self._ordered_strings.append( predicate_string )
                self._strings_to_terms[ predicate_string ] = predicate
                
            
            self._TextsHaveChanged()
            
        
    
    def _Activate( self, s, term ): HydrusGlobals.client_controller.pub( 'remove_predicate', self._page_key, term )
    
    def _GetAllTagsForClipboard( self, with_counts = False ):
        
        return [ self._strings_to_terms[ s ].GetUnicode( with_counts ) for s in self._ordered_strings ]
        
    
    def AddPredicate( self, predicate ):
        
        predicate = predicate.GetCountlessCopy()
        
        predicate_string = predicate.GetUnicode()
        
        inbox_predicate = ClientSearch.SYSTEM_PREDICATE_INBOX
        archive_predicate = ClientSearch.SYSTEM_PREDICATE_ARCHIVE
        
        if predicate == inbox_predicate and self.HasPredicate( archive_predicate ): self.RemovePredicate( archive_predicate )
        elif predicate == archive_predicate and self.HasPredicate( inbox_predicate ): self.RemovePredicate( inbox_predicate )
        
        local_predicate = ClientSearch.SYSTEM_PREDICATE_LOCAL
        not_local_predicate = ClientSearch.SYSTEM_PREDICATE_NOT_LOCAL
        
        if predicate == local_predicate and self.HasPredicate( not_local_predicate ): self.RemovePredicate( not_local_predicate )
        elif predicate == not_local_predicate and self.HasPredicate( local_predicate ): self.RemovePredicate( local_predicate )
        
        self._ordered_strings.append( predicate_string )
        self._strings_to_terms[ predicate_string ] = predicate
        
        self._ordered_strings.sort()
        
        self._TextsHaveChanged()
        
    
    def GetPredicates( self ): return self._strings_to_terms.values()
    
    def HasPredicate( self, predicate ): return predicate in self._strings_to_terms.values()
    
    def RemovePredicate( self, predicate ):
        
        for ( s, existing_predicate ) in self._strings_to_terms.items():
            
            if existing_predicate == predicate:
                
                self._ordered_strings.remove( s )
                del self._strings_to_terms[ s ]
                
                self._TextsHaveChanged()
                
                break
                
            
        
    
class ListBoxTagsSelection( ListBoxTags ):
    
    has_counts = True
    
    def __init__( self, parent, collapse_siblings = False ):
        
        ListBoxTags.__init__( self, parent, min_height = 200 )
        
        self._sort = HC.options[ 'default_tag_sort' ]
        
        self._last_media = set()
        
        self._tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
        
        self._collapse_siblings = collapse_siblings
        
        self._current_tags_to_count = collections.Counter()
        self._deleted_tags_to_count = collections.Counter()
        self._pending_tags_to_count = collections.Counter()
        self._petitioned_tags_to_count = collections.Counter()
        
        self._show_current = True
        self._show_deleted = False
        self._show_pending = True
        self._show_petitioned = True
        
    
    def _GetAllTagsForClipboard( self, with_counts = False ):
        
        if with_counts: return self._ordered_strings
        else: return [ self._strings_to_terms[ s ] for s in self._ordered_strings ]
        
    
    def _RecalcStrings( self ):
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        all_tags = set()
        
        if self._show_current: all_tags.update( ( tag for ( tag, count ) in self._current_tags_to_count.items() if count > 0 ) )
        if self._show_deleted: all_tags.update( ( tag for ( tag, count ) in self._deleted_tags_to_count.items() if count > 0 ) )
        if self._show_pending: all_tags.update( ( tag for ( tag, count ) in self._pending_tags_to_count.items() if count > 0 ) )
        if self._show_petitioned: all_tags.update( ( tag for ( tag, count ) in self._petitioned_tags_to_count.items() if count > 0 ) )
        
        self._ordered_strings = []
        self._strings_to_terms = {}
        
        for tag in all_tags:
            
            tag_string = tag
            
            if self._show_current and tag in self._current_tags_to_count: tag_string += ' (' + HydrusData.ConvertIntToPrettyString( self._current_tags_to_count[ tag ] ) + ')'
            if self._show_pending and tag in self._pending_tags_to_count: tag_string += ' (+' + HydrusData.ConvertIntToPrettyString( self._pending_tags_to_count[ tag ] ) + ')'
            if self._show_petitioned and tag in self._petitioned_tags_to_count: tag_string += ' (-' + HydrusData.ConvertIntToPrettyString( self._petitioned_tags_to_count[ tag ] ) + ')'
            if self._show_deleted and tag in self._deleted_tags_to_count: tag_string += ' (X' + HydrusData.ConvertIntToPrettyString( self._deleted_tags_to_count[ tag ] ) + ')'
            
            if not self._collapse_siblings:
                
                sibling = siblings_manager.GetSibling( tag )
                
                if sibling is not None: tag_string += ' (will display as ' + sibling + ')'
                
            
            self._ordered_strings.append( tag_string )
            self._strings_to_terms[ tag_string ] = tag
            
        
        self._SortTags()
        
    
    def _SortTags( self ):
        
        if self._sort == CC.SORT_BY_LEXICOGRAPHIC_ASC: compare_function = lambda a, b: cmp( a, b )
        elif self._sort == CC.SORT_BY_LEXICOGRAPHIC_DESC: compare_function = lambda a, b: cmp( b, a )
        elif self._sort in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_DESC ):
            
            tags_to_count = collections.defaultdict( lambda: 0 )
            
            tags_to_count.update( self._current_tags_to_count )
            for ( tag, count ) in self._pending_tags_to_count.items(): tags_to_count[ tag ] += count
            
            if self._sort == CC.SORT_BY_INCIDENCE_ASC: compare_function = lambda a, b: cmp( ( tags_to_count[ self._strings_to_terms[ a ] ], a ), ( tags_to_count[ self._strings_to_terms[ b ] ], b ) )
            elif self._sort == CC.SORT_BY_INCIDENCE_DESC: compare_function = lambda a, b: cmp( ( tags_to_count[ self._strings_to_terms[ b ] ], a ), ( tags_to_count[ self._strings_to_terms[ a ] ], b ) )
            
        
        self._ordered_strings.sort( compare_function )
        
        self._TextsHaveChanged()
        
    
    def ChangeTagRepository( self, service_key ):
        
        self._tag_service_key = service_key
        
        self.SetTagsByMedia( self._last_media, force_reload = True )
        
    
    def SetSort( self, sort ):
        
        self._sort = sort
        
        self._SortTags()
        
    
    def SetTags( self, current_tags_to_count = collections.Counter(), deleted_tags_to_count = collections.Counter(), pending_tags_to_count = collections.Counter(), petitioned_tags_to_count = collections.Counter() ):
        
        if self._collapse_siblings:
            
            siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
            
            current_tags_to_count = siblings_manager.CollapseTagsToCount( current_tags_to_count )
            deleted_tags_to_count = siblings_manager.CollapseTagsToCount( deleted_tags_to_count )
            pending_tags_to_count = siblings_manager.CollapseTagsToCount( pending_tags_to_count )
            petitioned_tags_to_count = siblings_manager.CollapseTagsToCount( petitioned_tags_to_count )
            
        
        self._current_tags_to_count = current_tags_to_count
        self._deleted_tags_to_count = deleted_tags_to_count
        self._pending_tags_to_count = pending_tags_to_count
        self._petitioned_tags_to_count = petitioned_tags_to_count
        
        self._RecalcStrings()
        
    
    def SetShow( self, show_type, value ):
        
        if show_type == 'current': self._show_current = value
        elif show_type == 'deleted': self._show_deleted = value
        elif show_type == 'pending': self._show_pending = value
        elif show_type == 'petitioned': self._show_petitioned = value
        
        self._RecalcStrings()
        
    
    def SetTagsByMedia( self, media, force_reload = False ):
        
        media = set( media )
        
        if force_reload:
            
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( media, self._tag_service_key )
            
            self.SetTags( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
            
        else:
            
            removees = self._last_media.difference( media )
            adds = media.difference( self._last_media )
            
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( removees, self._tag_service_key )
            
            if self._collapse_siblings:
                
                siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
                
                current_tags_to_count = siblings_manager.CollapseTagsToCount( current_tags_to_count )
                deleted_tags_to_count = siblings_manager.CollapseTagsToCount( deleted_tags_to_count )
                pending_tags_to_count = siblings_manager.CollapseTagsToCount( pending_tags_to_count )
                petitioned_tags_to_count = siblings_manager.CollapseTagsToCount( petitioned_tags_to_count )
                
            
            self._current_tags_to_count.subtract( current_tags_to_count )
            self._deleted_tags_to_count.subtract( deleted_tags_to_count )
            self._pending_tags_to_count.subtract( pending_tags_to_count )
            self._petitioned_tags_to_count.subtract( petitioned_tags_to_count )
            
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( adds, self._tag_service_key )
            
            if self._collapse_siblings:
                
                current_tags_to_count = siblings_manager.CollapseTagsToCount( current_tags_to_count )
                deleted_tags_to_count = siblings_manager.CollapseTagsToCount( deleted_tags_to_count )
                pending_tags_to_count = siblings_manager.CollapseTagsToCount( pending_tags_to_count )
                petitioned_tags_to_count = siblings_manager.CollapseTagsToCount( petitioned_tags_to_count )
                
            
            self._current_tags_to_count.update( current_tags_to_count )
            self._deleted_tags_to_count.update( deleted_tags_to_count )
            self._pending_tags_to_count.update( pending_tags_to_count )
            self._petitioned_tags_to_count.update( petitioned_tags_to_count )
            
            for counter in ( self._current_tags_to_count, self._deleted_tags_to_count, self._pending_tags_to_count, self._petitioned_tags_to_count ):
                
                tags = counter.keys()
                
                for tag in tags:
                    
                    if counter[ tag ] == 0: del counter[ tag ]
                    
                
            
            self._RecalcStrings()
            
        
        self._last_media = media
        
    
class ListBoxTagsSelectionManagementPanel( ListBoxTagsSelection ):
    
    def __init__( self, parent, page_key ):
        
        ListBoxTagsSelection.__init__( self, parent, collapse_siblings = True )
        
        self._page_key = page_key
        
        HydrusGlobals.client_controller.sub( self, 'SetTagsByMediaPubsub', 'new_tags_selection' )
        HydrusGlobals.client_controller.sub( self, 'ChangeTagRepositoryPubsub', 'change_tag_repository' )
        
    
    def _Activate( self, s, term ):
        
        predicate = ClientData.Predicate( HC.PREDICATE_TYPE_TAG, term )
        
        HydrusGlobals.client_controller.pub( 'add_predicate', self._page_key, predicate )
        
    
    def ChangeTagRepositoryPubsub( self, page_key, service_key ):
        
        if page_key == self._page_key: self.ChangeTagRepository( service_key )
        
    
    def SetTagsByMediaPubsub( self, page_key, media, force_reload = False ):
        
        if page_key == self._page_key: self.SetTagsByMedia( media, force_reload = force_reload )
        
    
class ListBoxTagsSelectionTagsDialog( ListBoxTagsSelection ):
    
    def __init__( self, parent, callable ):
        
        ListBoxTagsSelection.__init__( self, parent, collapse_siblings = False )
        
        self._callable = callable
        
    
    def _Activate( self, s, term ): self._callable( term )
    
class ListCtrlAutoWidth( wx.ListCtrl, ListCtrlAutoWidthMixin ):
    
    def __init__( self, parent, height ):
        
        wx.ListCtrl.__init__( self, parent, size=( -1, height ), style=wx.LC_REPORT )
        ListCtrlAutoWidthMixin.__init__( self )
        
    
    def GetAllSelected( self ):
        
        indices = []
        
        i = self.GetFirstSelected()
        
        while i != -1:
            
            indices.append( i )
            
            i = self.GetNextSelected( i )
            
        
        return indices
        
    
    def RemoveAllSelected( self ):
        
        indices = self.GetAllSelected()
        
        indices.reverse() # so we don't screw with the indices of deletees below
        
        for index in indices: self.DeleteItem( index )
        
    
class NoneableSpinCtrl( wx.Panel ):
    
    def __init__( self, parent, message, none_phrase = 'no limit', min = 0, max = 1000000, multiplier = 1, num_dimensions = 1 ):
        
        wx.Panel.__init__( self, parent )
        
        self._num_dimensions = num_dimensions
        self._multiplier = multiplier
        
        self._checkbox = wx.CheckBox( self, label = none_phrase )
        self._checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckBox )
        
        self._one = wx.SpinCtrl( self, min = min, max = max, size = ( 60, -1 ) )
        
        if num_dimensions == 2: self._two = wx.SpinCtrl( self, initial = 0, min = min, max = max, size = ( 60, -1 ) )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if len( message ) > 0:
            
            hbox.AddF( wx.StaticText( self, label = message + ': ' ), CC.FLAGS_MIXED )
            
        
        hbox.AddF( self._one, CC.FLAGS_MIXED )
        
        if self._num_dimensions == 2:
            
            hbox.AddF( wx.StaticText( self, label = 'x' ), CC.FLAGS_MIXED )
            hbox.AddF( self._two, CC.FLAGS_MIXED )
            
        
        hbox.AddF( self._checkbox, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
    
    def Bind( self, event_type, callback ):
        
        self._checkbox.Bind( wx.EVT_CHECKBOX, callback )
        self._one.Bind( wx.EVT_SPINCTRL, callback )
        if self._num_dimensions == 2: self._two.Bind( wx.EVT_SPINCTRL, callback )
        
    
    def EventCheckBox( self, event ):
        
        if self._checkbox.GetValue():
            
            self._one.Disable()
            if self._num_dimensions == 2: self._two.Disable()
            
        else:
            
            self._one.Enable()
            if self._num_dimensions == 2: self._two.Enable()
            
        
    
    def GetValue( self ):
        
        if self._checkbox.GetValue(): return None
        else:
            
            if self._num_dimensions == 2: return ( self._one.GetValue() * self._multiplier, self._two.GetValue() * self._multiplier )
            else: return self._one.GetValue() * self._multiplier
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._checkbox.SetValue( True )
            
            self._one.Disable()
            if self._num_dimensions == 2: self._two.Disable()
            
        else:
            
            self._checkbox.SetValue( False )
            
            if self._num_dimensions == 2:
                
                self._two.Enable()
                
                ( value, y ) = value
                
                self._two.SetValue( y / self._multiplier )
                
            
            self._one.Enable()
            
            self._one.SetValue( value / self._multiplier )
            
        
    
class OnOffButton( wx.Button ):
    
    def __init__( self, parent, page_key, topic, on_label, off_label = None, start_on = True ):
        
        if start_on: label = on_label
        else: label = off_label
        
        wx.Button.__init__( self, parent, label = label )
        
        self._page_key = page_key
        self._topic = topic
        self._on_label = on_label
        
        if off_label is None: self._off_label = on_label
        else: self._off_label = off_label
        
        self._on = start_on
        
        if self._on: self.SetForegroundColour( ( 0, 128, 0 ) )
        else: self.SetForegroundColour( ( 128, 0, 0 ) )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
        HydrusGlobals.client_controller.sub( self, 'HitButton', 'hit_on_off_button' )
        
    
    def EventButton( self, event ):
        
        if self._on:
            
            self._on = False
            
            self.SetLabel( self._off_label )
            
            self.SetForegroundColour( ( 128, 0, 0 ) )
            
            HydrusGlobals.client_controller.pub( self._topic, self._page_key, False )
            
        else:
            
            self._on = True
            
            self.SetLabel( self._on_label )
            
            self.SetForegroundColour( ( 0, 128, 0 ) )
            
            HydrusGlobals.client_controller.pub( self._topic, self._page_key, True )
            
        
    
    def IsOn( self ): return self._on
    
class PopupWindow( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent, style = wx.BORDER_SIMPLE )
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
    
    def TryToDismiss( self ): self.GetParent().Dismiss( self )
    
    def EventDismiss( self, event ): self.TryToDismiss()
    
class PopupDismissAll( PopupWindow ):
    
    def __init__( self, parent ):
        
        PopupWindow.__init__( self, parent )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._text = wx.StaticText( self )
        self._text.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
        button = wx.Button( self, label = 'dismiss all' )
        button.Bind( wx.EVT_BUTTON, self.EventButton )
        button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
        hbox.AddF( self._text, CC.FLAGS_MIXED )
        hbox.AddF( button, CC.FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
    
    def TryToDismiss( self ): pass
    
    def EventButton( self, event ): self.GetParent().DismissAll()
    
    def SetNumMessages( self, num_messages_pending ): self._text.SetLabel( HydrusData.ConvertIntToPrettyString( num_messages_pending ) + ' more messages' )
    
class PopupMessage( PopupWindow ):
    
    def __init__( self, parent, job_key ):
        
        PopupWindow.__init__( self, parent )
        
        self._job_key = job_key
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._title = FitResistantStaticText( self, style = wx.ALIGN_CENTER )
        self._title.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._title.Hide()
        
        self._text_1 = FitResistantStaticText( self )
        self._text_1.Wrap( 380 )
        self._text_1.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._text_1.Hide()
        
        self._gauge_1 = Gauge( self, size = ( 380, -1 ) )
        self._gauge_1.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._gauge_1.Hide()
        
        self._text_2 = FitResistantStaticText( self )
        self._text_2.Wrap( 380 )
        self._text_2.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._text_2.Hide()
        
        self._gauge_2 = Gauge( self, size = ( 380, -1 ) )
        self._gauge_2.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._gauge_2.Hide()
        
        self._show_files_button = wx.Button( self )
        self._show_files_button.Bind( wx.EVT_BUTTON, self.EventShowFilesButton )
        self._show_files_button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._show_files_button.Hide()
        
        self._show_tb_button = wx.Button( self, label = 'show traceback' )
        self._show_tb_button.Bind( wx.EVT_BUTTON, self.EventShowTBButton )
        self._show_tb_button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._show_tb_button.Hide()
        
        self._tb_text = FitResistantStaticText( self )
        self._tb_text.Wrap( 380 )
        self._tb_text.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._tb_text.Hide()
        
        self._show_caller_tb_button = wx.Button( self, label = 'show caller traceback' )
        self._show_caller_tb_button.Bind( wx.EVT_BUTTON, self.EventShowCallerTBButton )
        self._show_caller_tb_button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._show_caller_tb_button.Hide()
        
        self._caller_tb_text = FitResistantStaticText( self )
        self._caller_tb_text.Wrap( 380 )
        self._caller_tb_text.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._caller_tb_text.Hide()
        
        self._show_db_tb_button = wx.Button( self, label = 'show db traceback' )
        self._show_db_tb_button.Bind( wx.EVT_BUTTON, self.EventShowDBTBButton )
        self._show_db_tb_button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._show_db_tb_button.Hide()
        
        self._db_tb_text = FitResistantStaticText( self )
        self._db_tb_text.Wrap( 380 )
        self._db_tb_text.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._db_tb_text.Hide()
        
        self._copy_tb_button = wx.Button( self, label = 'copy traceback information' )
        self._copy_tb_button.Bind( wx.EVT_BUTTON, self.EventCopyTBButton )
        self._copy_tb_button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._copy_tb_button.Hide()
        
        self._pause_button = wx.BitmapButton( self, bitmap = CC.GlobalBMPs.pause )
        self._pause_button.Bind( wx.EVT_BUTTON, self.EventPauseButton )
        self._pause_button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._pause_button.Hide()
        
        self._cancel_button = wx.BitmapButton( self, bitmap = CC.GlobalBMPs.stop )
        self._cancel_button.Bind( wx.EVT_BUTTON, self.EventCancelButton )
        self._cancel_button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._cancel_button.Hide()
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._pause_button, CC.FLAGS_MIXED )
        hbox.AddF( self._cancel_button, CC.FLAGS_MIXED )
        
        vbox.AddF( self._title, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._text_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._gauge_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._text_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._gauge_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._show_files_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._show_tb_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._tb_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._show_caller_tb_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._caller_tb_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._show_db_tb_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._db_tb_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._copy_tb_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ProcessText( self, text ):
        
        if len( text ) > TEXT_CUTOFF:
            
            new_text = 'The text is too long to display here. Here is the start of it (the rest is printed to the log):'
            
            new_text += os.linesep * 2
            
            new_text += text[:TEXT_CUTOFF]
            
            text = new_text
            
        
        return text
        
    
    def EventCancelButton( self, event ):
        
        self._job_key.Cancel()
        
        self._pause_button.Disable()
        self._cancel_button.Disable()
        
    
    def EventCopyTBButton( self, event ):
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', self._job_key.ToString() )
        
    
    def EventPauseButton( self, event ):
        
        self._job_key.PausePlay()
        
        if self._job_key.IsPaused():
            
            self._pause_button.SetBitmap( CC.GlobalBMPs.play )
            
        else:
            
            self._pause_button.SetBitmap( CC.GlobalBMPs.pause )
            
        
    
    def EventShowCallerTBButton( self, event ):
        
        if self._caller_tb_text.IsShown():
            
            self._show_caller_tb_button.SetLabel( 'show caller traceback' )
            
            self._caller_tb_text.Hide()
            
        else:
            
            self._show_caller_tb_button.SetLabel( 'hide caller traceback' )
            
            self._caller_tb_text.Show()
            
        
        self.GetParent().MakeSureEverythingFits()
        
    
    def EventShowDBTBButton( self, event ):
        
        if self._db_tb_text.IsShown():
            
            self._show_db_tb_button.SetLabel( 'show db traceback' )
            
            self._db_tb_text.Hide()
            
        else:
            
            self._show_db_tb_button.SetLabel( 'hide db traceback' )
            
            self._db_tb_text.Show()
            
        
        self.GetParent().MakeSureEverythingFits()
        
    
    def EventShowFilesButton( self, event ):
        
        hashes = self._job_key.GetVariable( 'popup_files' )
        
        media_results = HydrusGlobals.client_controller.Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, hashes )
        
        HydrusGlobals.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_media_results = media_results )
        
    
    def EventShowTBButton( self, event ):
        
        if self._tb_text.IsShown():
            
            self._show_tb_button.SetLabel( 'show traceback' )
            
            self._tb_text.Hide()
            
        else:
            
            self._show_tb_button.SetLabel( 'hide traceback' )
            
            self._tb_text.Show()
            
        
        self.GetParent().MakeSureEverythingFits()
        
    
    def TryToDismiss( self ):
        
        if self._job_key.IsPausable() or self._job_key.IsCancellable(): return
        else: PopupWindow.TryToDismiss( self )
        
    
    def Update( self ):
        
        if self._job_key.IsDeleted():
            
            self.TryToDismiss()
            
            return
            
        
        if self._job_key.HasVariable( 'popup_title' ):
            
            text = self._job_key.GetVariable( 'popup_title' )
            
            if self._title.GetLabel() != text: self._title.SetLabel( text )
            
            self._title.Show()
            
        else: self._title.Hide()
        
        if self._job_key.HasVariable( 'popup_text_1' ) and not self._job_key.IsPaused():
            
            text = self._job_key.GetVariable( 'popup_text_1' )
            
            if self._text_1.GetLabel() != text: self._text_1.SetLabel( self._ProcessText( HydrusData.ToString( text ) ) )
            
            self._text_1.Show()
            
        else: self._text_1.Hide()
        
        if self._job_key.HasVariable( 'popup_gauge_1' ) and not self._job_key.IsPaused():
            
            ( gauge_value, gauge_range ) = self._job_key.GetVariable( 'popup_gauge_1' )
            
            if gauge_range is None or gauge_value is None: self._gauge_1.Pulse()
            else:
                
                self._gauge_1.SetRange( gauge_range )
                self._gauge_1.SetValue( gauge_value )
                
            
            self._gauge_1.Show()
            
        else: self._gauge_1.Hide()
        
        if self._job_key.HasVariable( 'popup_text_2' ) and not self._job_key.IsPaused():
            
            text = self._job_key.GetVariable( 'popup_text_2' )
            
            if self._text_2.GetLabel() != text: self._text_2.SetLabel( self._ProcessText( HydrusData.ToString( text ) ) )
            
            self._text_2.Show()
            
        else: self._text_2.Hide()
        
        if self._job_key.HasVariable( 'popup_gauge_2' ) and not self._job_key.IsPaused():
            
            ( gauge_value, gauge_range ) = self._job_key.GetVariable( 'popup_gauge_2' )
            
            if gauge_range is None or gauge_value is None: self._gauge_2.Pulse()
            else:
                
                self._gauge_2.SetRange( gauge_range )
                self._gauge_2.SetValue( gauge_value )
                
            
            self._gauge_2.Show()
            
        else: self._gauge_2.Hide()
        
        if self._job_key.HasVariable( 'popup_files' ):
            
            hashes = self._job_key.GetVariable( 'popup_files' )
            
            text = 'show ' + HydrusData.ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
            if self._show_files_button.GetLabel() != text: self._show_files_button.SetLabel( text )
            
            self._show_files_button.Show()
            
        else: self._show_files_button.Hide()
        
        if self._job_key.HasVariable( 'popup_traceback' ) or self._job_key.HasVariable( 'popup_caller_traceback' ) or self._job_key.HasVariable( 'popup_db_traceback' ): self._copy_tb_button.Show()
        else: self._copy_tb_button.Hide()
        
        if self._job_key.HasVariable( 'popup_traceback' ):
            
            text = self._job_key.GetVariable( 'popup_traceback' )
            
            if self._tb_text.GetLabel() != text: self._tb_text.SetLabel( self._ProcessText( HydrusData.ToString( text ) ) )
            
            self._show_tb_button.Show()
            
        else:
            
            self._show_tb_button.Hide()
            self._tb_text.Hide()
            
        
        if self._job_key.HasVariable( 'popup_caller_traceback' ):
            
            text = self._job_key.GetVariable( 'popup_caller_traceback' )
            
            if self._caller_tb_text.GetLabel() != text: self._caller_tb_text.SetLabel( self._ProcessText( HydrusData.ToString( text ) ) )
            
            self._show_caller_tb_button.Show()
            
        else:
            
            self._show_caller_tb_button.Hide()
            self._caller_tb_text.Hide()
            
        
        if self._job_key.HasVariable( 'popup_db_traceback' ):
            
            text = self._job_key.GetVariable( 'popup_db_traceback' )
            
            if self._db_tb_text.GetLabel() != text: self._db_tb_text.SetLabel( self._ProcessText( HydrusData.ToString( text ) ) )
            
            self._show_db_tb_button.Show()
            
        else:
            
            self._show_db_tb_button.Hide()
            self._db_tb_text.Hide()
            
        
        if self._job_key.IsPausable(): self._pause_button.Show()
        else: self._pause_button.Hide()
        
        if self._job_key.IsCancellable(): self._cancel_button.Show()
        else: self._cancel_button.Hide()
        
    
class PopupMessageManager( wx.Frame ):
    
    def __init__( self, parent ):
        
        wx.Frame.__init__( self, parent, style = wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_NONE )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self._max_messages_to_display = 10
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._message_vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._dismiss_all = PopupDismissAll( self )
        self._dismiss_all.Hide()
        
        vbox.AddF( self._message_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._dismiss_all, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self._pending_job_keys = []
        
        parent.Bind( wx.EVT_SIZE, self.EventMove )
        parent.Bind( wx.EVT_MOVE, self.EventMove )
        
        HydrusGlobals.client_controller.sub( self, 'AddMessage', 'message' )
        
        self._old_excepthook = sys.excepthook
        self._old_show_exception = HydrusData.ShowException
        
        sys.excepthook = ClientData.CatchExceptionClient
        HydrusData.ShowException = ClientData.ShowExceptionClient
        HydrusData.ShowText = ClientData.ShowTextClient
        
        self.Bind( wx.EVT_TIMER, self.TIMEREvent, id = ID_TIMER_POPUP )
        
        self._timer = wx.Timer( self, id = ID_TIMER_POPUP )
        
        self._timer.Start( 500, wx.TIMER_CONTINUOUS )
        
    
    def _CheckPending( self ):
        
        num_messages_displayed = self._message_vbox.GetItemCount()
        
        if len( self._pending_job_keys ) > 0 and num_messages_displayed < self._max_messages_to_display:
            
            job_key = self._pending_job_keys.pop( 0 )
            
            window = PopupMessage( self, job_key )
            
            window.Update()
            
            self._message_vbox.AddF( window, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        num_messages_pending = len( self._pending_job_keys )
        
        if num_messages_pending > 0:
            
            self._dismiss_all.SetNumMessages( num_messages_pending )
            
            self._dismiss_all.Show()
            
        else: self._dismiss_all.Hide()
        
        self._SizeAndPositionAndShow()
        
    
    def _SizeAndPositionAndShow( self ):
        
        try:
            
            self.Fit()
            
            parent = self.GetParent()
            
            ( parent_width, parent_height ) = parent.GetClientSize()
            
            ( my_width, my_height ) = self.GetClientSize()
            
            my_x = ( parent_width - my_width ) - 5
            my_y = ( parent_height - my_height ) - 15
            
            self.SetPosition( parent.ClientToScreenXY( my_x, my_y ) )
            
            num_messages_displayed = self._message_vbox.GetItemCount()
            
            if num_messages_displayed > 0:
                
                current_focus = wx.Window.FindFocus()
                
                tlp = wx.GetTopLevelParent( current_focus )
                
                show_happened = self.Show()
                
                if show_happened and tlp is not None:
                    
                    self.Raise()
                    
                    tlp.Raise()
                    
                
            else: self.Hide()
            
        except:
            
            # I don't understand the error here.
            # It happened for someone in Fit(), causing 'C++ assertion 'm_hDWP failed at blah ... EndRepositioningChildren Shouldn't be called'
            # It might be related to an id-cache overflow error I had before, in which case it is fixed
            
            text = 'The popup message manager experienced a fatal error and will now stop working! Please restart the client as soon as possible! If this keeps happening, please email the details and your client.log to the hydrus developer.'
            
            print( text )
            
            print( traceback.format_exc() )
            
            wx.MessageBox( text )
            
            self._timer.Stop()
            
            self.CleanBeforeDestroy()
            
            self.Destroy()
            
        
    
    def AddMessage( self, job_key ):
        
        try:
            
            self._pending_job_keys.append( job_key )
            
            self._CheckPending()
            
        except: print( traceback.format_exc() )
        
    
    def CleanBeforeDestroy( self ):
        
        sys.excepthook = self._old_excepthook
        
        HydrusData.ShowException = self._old_show_exception
        
    
    def Dismiss( self, window ):
        
        self._message_vbox.Detach( window )
        
        wx.CallAfter( window.Destroy )
        
        self._SizeAndPositionAndShow()
        
        self._CheckPending()
        
    
    def DismissAll( self ):
        
        self._pending_job_keys = [ job_key for job_key in self._pending_job_keys if job_key.IsPausable() or job_key.IsCancellable() ]
        
        sizer_items = self._message_vbox.GetChildren()
        
        for sizer_item in sizer_items:
            
            message_window = sizer_item.GetWindow()
            
            message_window.TryToDismiss()
            
        
        self._CheckPending()
        
    
    def EventMove( self, event ):
        
        self._SizeAndPositionAndShow()
        
        event.Skip()
        
    
    def MakeSureEverythingFits( self ): self._SizeAndPositionAndShow()
    
    def TIMEREvent( self, event ):
        
        if HydrusGlobals.view_shutdown:
            
            self.Destroy()
            
            return
            
        
        sizer_items = self._message_vbox.GetChildren()
        
        for sizer_item in sizer_items:
            
            message_window = sizer_item.GetWindow()
            
            message_window.Update()
            
        
        self._SizeAndPositionAndShow()
        
    
class RatingLike( wx.Window ):
    
    def __init__( self, parent, service_key ):
        
        wx.Window.__init__( self, parent )
        
        self._service_key = service_key
        
        self._canvas_bmp = wx.EmptyBitmap( 16, 16, 24 )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventLeftDown )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventRightDown )
        self.Bind( wx.EVT_RIGHT_DCLICK, self.EventRightDown )
        
        self.SetMinSize( ( 16, 16 ) )
        
        self._dirty = True
        
    
    def _Draw( self ):
        
        raise NotImplementedError()
        
    
    def GetDC( self ): return wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
    
    def EventEraseBackground( self, event ): pass
    
    def EventLeftDown( self, event ):
        
        raise NotImplementedError()
        
    
    def EventPaint( self, event ):
        
        if self._dirty:
            
            self._Draw()
            
        
        wx.BufferedPaintDC( self, self._canvas_bmp )
        
    
    def EventRightDown( self, event ):
        
        raise NotImplementedError()
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
class RatingLikeDialog( RatingLike ):
    
    def __init__( self, parent, service_key ):
        
        RatingLike.__init__( self, parent, service_key )
        
        self._rating_state = ClientRatings.NULL
        
    
    def _Draw( self ):
        
        dc = self.GetDC()
        
        dc.SetBackground( wx.Brush( self.GetParent().GetBackgroundColour() ) )
        
        dc.Clear()
        
        ( pen_colour, brush_colour ) = ClientRatings.GetPenAndBrushColours( self._service_key, self._rating_state )
        
        ClientRatings.DrawLike( dc, 0, 0, self._service_key, self._rating_state )
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        if self._rating_state == ClientRatings.LIKE: self._rating_state = ClientRatings.NULL
        else: self._rating_state = ClientRatings.LIKE
        
        self._dirty = True
        
        self.Refresh()
        
    
    def EventRightDown( self, event ):
        
        if self._rating_state == ClientRatings.DISLIKE: self._rating_state = ClientRatings.NULL
        else: self._rating_state = ClientRatings.DISLIKE
        
        self._dirty = True
        
        self.Refresh()
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def SetRatingState( self, rating_state ):
        
        self._rating_state = rating_state
        
        self._dirty = True
        
        self.Refresh()
        
    
class RatingLikeCanvas( RatingLike ):

    def __init__( self, parent, service_key, canvas_key ):
        
        RatingLike.__init__( self, parent, service_key )
        
        self._canvas_key = canvas_key
        self._current_media = None
        self._rating_state = None
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        name = service.GetName()
        
        self.SetToolTipString( name )
        
        HydrusGlobals.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HydrusGlobals.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
    def _Draw( self ):
        
        dc = self.GetDC()
        
        dc.SetBackground( wx.Brush( self.GetParent().GetBackgroundColour() ) )
        
        dc.Clear()
        
        if self._current_media is not None:
            
            self._rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), self._service_key )
            
            ClientRatings.DrawLike( dc, 0, 0, self._service_key, self._rating_state )
            
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.LIKE: rating = None
            else: rating = 1
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HydrusGlobals.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def EventRightDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.DISLIKE: rating = None
            else: rating = 0
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HydrusGlobals.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                for content_update in content_updates:
                    
                    ( data_type, action, row ) = content_update.ToTuple()
                    
                    if data_type == HC.CONTENT_TYPE_RATINGS:
                        
                        hashes = content_update.GetHashes()
                        
                        if len( self._hashes.intersection( hashes ) ) > 0:
                            
                            self._dirty = True
                            
                            self.Refresh()
                            
                            return
                            
                        
                    
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = media
            
            self._hashes = self._current_media.GetHashes()
            
            self._dirty = True
            
            self.Refresh()
            
        
    
class RatingNumerical( wx.Window ):
    
    def __init__( self, parent, service_key ):
        
        wx.Window.__init__( self, parent )
        
        self._service_key = service_key
        
        self._service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._service_key )
        
        self._num_stars = self._service.GetInfo( 'num_stars' )
        self._allow_zero = self._service.GetInfo( 'allow_zero' )
        
        my_width = ClientRatings.GetNumericalWidth( self._service_key )
        
        self._canvas_bmp = wx.EmptyBitmap( my_width, 16, 24 )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventLeftDown )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventRightDown )
        self.Bind( wx.EVT_RIGHT_DCLICK, self.EventRightDown )
        
        self.SetMinSize( ( my_width, 16 ) )
        
        self._dirty = True
        
    
    def _Draw( self ):
        
        raise NotImplementedError()
        
    
    def _GetRatingFromClickEvent( self, event ):
        
        x = event.GetX()
        y = event.GetY()
        
        ( my_width, my_height ) = self.GetClientSize()
        
        # assuming a border of 2 on every side here
        
        my_active_width = my_width - 4
        my_active_height = my_height - 4
        
        x_adjusted = x - 2
        y_adjusted = y - 2
        
        if 0 <= y and y <= my_active_height:
            
            if 0 <= x and x <= my_active_width:
            
                proportion_filled = float( x_adjusted ) / my_active_width
                
                if self._allow_zero:
                    
                    rating = round( proportion_filled * self._num_stars ) / self._num_stars
                    
                else:
                    
                    rating = float( int( proportion_filled * self._num_stars ) ) / ( self._num_stars - 1 )
                    
                
                return rating
                
            
        
        return None
        
    
    def GetDC( self ): return wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
    
    def EventEraseBackground( self, event ): pass
    
    def EventLeftDown( self, event ):
        
        raise NotImplementedError()
        
    
    def EventPaint( self, event ):
        
        if self._dirty:
            
            self._Draw()
            
        
        wx.BufferedPaintDC( self, self._canvas_bmp )
        
    
    def EventRightDown( self, event ):
        
        raise NotImplementedError()
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
class RatingNumericalDialog( RatingNumerical ):
    
    def __init__( self, parent, service_key ):
        
        RatingNumerical.__init__( self, parent, service_key )
        
        self._rating_state = ClientRatings.NULL
        self._rating = None
        
    
    def _Draw( self ):
        
        dc = self.GetDC()
        
        dc.SetBackground( wx.Brush( self.GetParent().GetBackgroundColour() ) )
        
        dc.Clear()
        
        ClientRatings.DrawNumerical( dc, 0, 0, self._service_key, self._rating_state, self._rating )
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        rating = self._GetRatingFromClickEvent( event )
        
        if rating is not None:
            
            self._rating_state = ClientRatings.SET
            
            self._rating = rating
            
            self._dirty = True
            
            self.Refresh()
            
        
    
    def EventRightDown( self, event ):
        
        self._rating_state = ClientRatings.NULL
        
        self._dirty = True
        
        self.Refresh()
        
    
    def GetRating( self ):
        
        return self._rating
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def SetRating( self, rating ):
        
        self._rating_state = ClientRatings.SET
        
        self._rating = rating
        
        self._dirty = True
        
        self.Refresh()
        
    
    def SetRatingState( self, rating_state ):
        
        self._rating_state = rating_state
        
        self._dirty = True
        
        self.Refresh()
        
    
class RatingNumericalCanvas( RatingNumerical ):

    def __init__( self, parent, service_key, canvas_key ):
        
        RatingNumerical.__init__( self, parent, service_key )
        
        self._canvas_key = canvas_key
        self._current_media = None
        self._rating_state = None
        self._rating = None
        
        name = self._service.GetName()
        
        self.SetToolTipString( name )
        
        HydrusGlobals.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HydrusGlobals.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
    def _Draw( self ):
        
        dc = self.GetDC()
        
        dc.SetBackground( wx.Brush( self.GetParent().GetBackgroundColour() ) )
        
        dc.Clear()
        
        if self._current_media is not None:
            
            ( self._rating_state, self._rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), self._service_key )
            
            ClientRatings.DrawNumerical( dc, 0, 0, self._service_key, self._rating_state, self._rating )
            
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        if self._current_media is not None:
            
            rating = self._GetRatingFromClickEvent( event )
            
            if rating is not None:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
                
                HydrusGlobals.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
                
            
        
    
    def EventRightDown( self, event ):
        
        if self._current_media is not None:
            
            rating = None
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HydrusGlobals.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                for content_update in content_updates:
                    
                    ( data_type, action, row ) = content_update.ToTuple()
                    
                    if data_type == HC.CONTENT_TYPE_RATINGS:
                        
                        hashes = content_update.GetHashes()
                        
                        if len( self._hashes.intersection( hashes ) ) > 0:
                            
                            self._dirty = True
                            
                            self.Refresh()
                            
                            return
                            
                        
                    
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = media
            
            self._hashes = self._current_media.GetHashes()
            
            self._dirty = True
            
            self.Refresh()
            
        
    
class RegexButton( wx.Button ):
    
    ID_REGEX_WHITESPACE = 0
    ID_REGEX_NUMBER = 1
    ID_REGEX_ALPHANUMERIC = 2
    ID_REGEX_ANY = 3
    ID_REGEX_BEGINNING = 4
    ID_REGEX_END = 5
    ID_REGEX_0_OR_MORE_GREEDY = 6
    ID_REGEX_1_OR_MORE_GREEDY = 7
    ID_REGEX_0_OR_1_GREEDY = 8
    ID_REGEX_0_OR_MORE_MINIMAL = 9
    ID_REGEX_1_OR_MORE_MINIMAL = 10
    ID_REGEX_0_OR_1_MINIMAL = 11
    ID_REGEX_EXACTLY_M = 12
    ID_REGEX_M_TO_N_GREEDY = 13
    ID_REGEX_M_TO_N_MINIMAL = 14
    ID_REGEX_LOOKAHEAD = 15
    ID_REGEX_NEGATIVE_LOOKAHEAD = 16
    ID_REGEX_LOOKBEHIND = 17
    ID_REGEX_NEGATIVE_LOOKBEHIND = 18
    ID_REGEX_NUMBER_WITHOUT_ZEROES = 19
    ID_REGEX_BACKSPACE = 22
    ID_REGEX_SET = 23
    ID_REGEX_NOT_SET = 24
    ID_REGEX_FILENAME = 25
    ID_REGEX_MANAGE_FAVOURITES = 26
    ID_REGEX_FAVOURITES = range( 100, 200 )
    
    def __init__( self, parent ):
        
        wx.Button.__init__( self, parent, label = 'regex shortcuts' )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def EventButton( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( -1, 'click on a phrase to copy to clipboard' )
        
        menu.AppendSeparator()
        
        submenu = wx.Menu()
        
        submenu.Append( self.ID_REGEX_WHITESPACE, r'whitespace character - \s' )
        submenu.Append( self.ID_REGEX_NUMBER, r'number character - \d' )
        submenu.Append( self.ID_REGEX_ALPHANUMERIC, r'alphanumeric or backspace character - \w' )
        submenu.Append( self.ID_REGEX_ANY, r'any character - .' )
        submenu.Append( self.ID_REGEX_BACKSPACE, r'backspace character - \\' )
        submenu.Append( self.ID_REGEX_BEGINNING, r'beginning of line - ^' )
        submenu.Append( self.ID_REGEX_END, r'end of line - $' )
        submenu.Append( self.ID_REGEX_SET, r'any of these - [...]' )
        submenu.Append( self.ID_REGEX_NOT_SET, r'anything other than these - [^...]' )
        
        submenu.AppendSeparator()
        
        submenu.Append( self.ID_REGEX_0_OR_MORE_GREEDY, r'0 or more matches, consuming as many as possible - *' )
        submenu.Append( self.ID_REGEX_1_OR_MORE_GREEDY, r'1 or more matches, consuming as many as possible - +' )
        submenu.Append( self.ID_REGEX_0_OR_1_GREEDY, r'0 or 1 matches, preferring 1 - ?' )
        submenu.Append( self.ID_REGEX_0_OR_MORE_MINIMAL, r'0 or more matches, consuming as few as possible - *?' )
        submenu.Append( self.ID_REGEX_1_OR_MORE_MINIMAL, r'1 or more matches, consuming as few as possible - +?' )
        submenu.Append( self.ID_REGEX_0_OR_1_MINIMAL, r'0 or 1 matches, preferring 0 - *' )
        submenu.Append( self.ID_REGEX_EXACTLY_M, r'exactly m matches - {m}' )
        submenu.Append( self.ID_REGEX_M_TO_N_GREEDY, r'm to n matches, consuming as many as possible - {m,n}' )
        submenu.Append( self.ID_REGEX_M_TO_N_MINIMAL, r'm to n matches, consuming as few as possible - {m,n}?' )
        
        submenu.AppendSeparator()
        
        submenu.Append( self.ID_REGEX_LOOKAHEAD, r'the next characters are: (non-consuming) - (?=...)' )
        submenu.Append( self.ID_REGEX_NEGATIVE_LOOKAHEAD, r'the next characters are not: (non-consuming) - (?!...)' )
        submenu.Append( self.ID_REGEX_LOOKBEHIND, r'the previous characters are: (non-consuming) - (?<=...)' )
        submenu.Append( self.ID_REGEX_NEGATIVE_LOOKBEHIND, r'the previous characters are not: (non-consuming) - (?<!...)' )
        
        submenu.AppendSeparator()
        
        submenu.Append( self.ID_REGEX_NUMBER_WITHOUT_ZEROES, r'0074 -> 74 - [1-9]+\d*' )
        submenu.Append( self.ID_REGEX_FILENAME, r'filename - (?<=' + os.path.sep.encode( 'string_escape' ) + r')[\w\s]*?(?=\..*$)' )
        
        menu.AppendMenu( -1, 'regex components', submenu )
        
        submenu = wx.Menu()
        
        submenu.Append( self.ID_REGEX_MANAGE_FAVOURITES, 'manage favourites' )
        
        submenu.AppendSeparator()
        
        for ( index, ( regex_phrase, description ) ) in enumerate( HC.options[ 'regex_favourites' ] ):
            
            menu_id = index + 100
            
            submenu.Append( menu_id, description )
            
        
        menu.AppendMenu( -1, 'favourites', submenu )
        
        self.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
    def EventMenu( self, event ):
        
        id = event.GetId()
        
        phrase = None
        
        if id == self.ID_REGEX_WHITESPACE: phrase = r'\s'
        elif id == self.ID_REGEX_NUMBER: phrase = r'\d'
        elif id == self.ID_REGEX_ALPHANUMERIC: phrase = r'\w'
        elif id == self.ID_REGEX_ANY: phrase = r'.'
        elif id == self.ID_REGEX_BACKSPACE: phrase = r'\\'
        elif id == self.ID_REGEX_BEGINNING: phrase = r'^'
        elif id == self.ID_REGEX_END: phrase = r'$'
        elif id == self.ID_REGEX_SET: phrase = r'[...]'
        elif id == self.ID_REGEX_NOT_SET: phrase = r'[^...]'
        elif id == self.ID_REGEX_0_OR_MORE_GREEDY: phrase = r'*'
        elif id == self.ID_REGEX_1_OR_MORE_GREEDY: phrase = r'+'
        elif id == self.ID_REGEX_0_OR_1_GREEDY: phrase = r'?'
        elif id == self.ID_REGEX_0_OR_MORE_MINIMAL: phrase = r'*?'
        elif id == self.ID_REGEX_1_OR_MORE_MINIMAL: phrase = r'+?'
        elif id == self.ID_REGEX_0_OR_1_MINIMAL: phrase = r'*'
        elif id == self.ID_REGEX_EXACTLY_M: phrase = r'{m}'
        elif id == self.ID_REGEX_M_TO_N_GREEDY: phrase = r'{m,n}'
        elif id == self.ID_REGEX_M_TO_N_MINIMAL: phrase = r'{m,n}?'
        elif id == self.ID_REGEX_LOOKAHEAD: phrase = r'(?=...)'
        elif id == self.ID_REGEX_NEGATIVE_LOOKAHEAD: phrase = r'(?!...)'
        elif id == self.ID_REGEX_LOOKBEHIND: phrase = r'(?<=...)'
        elif id == self.ID_REGEX_NEGATIVE_LOOKBEHIND: phrase = r'(?<!...)'
        elif id == self.ID_REGEX_NUMBER_WITHOUT_ZEROES: phrase = r'[1-9]+\d*'
        elif id == self.ID_REGEX_FILENAME: phrase = r'(?<=' + os.path.sep.encode( 'string_escape' ) + r')[\w\s]*?(?=\..*$)'
        elif id == self.ID_REGEX_MANAGE_FAVOURITES:
            
            import ClientGUIDialogsManage
            
            with ClientGUIDialogsManage.DialogManageRegexFavourites( self.GetTopLevelParent() ) as dlg:
                
                dlg.ShowModal()
                
            
        elif id in self.ID_REGEX_FAVOURITES:
            
            index = id - 100
            
            ( phrase, description ) = HC.options[ 'regex_favourites' ][ index ]
            
        else: event.Skip()
        
        if phrase is not None: HydrusGlobals.client_controller.pub( 'clipboard', 'text', phrase )
        
    
class SaneListCtrl( wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin ):
    
    def __init__( self, parent, height, columns, delete_key_callback = None, use_display_tuple_for_sort = False ):
        
        num_columns = len( columns )
        
        wx.ListCtrl.__init__( self, parent, style = wx.LC_REPORT )
        ListCtrlAutoWidthMixin.__init__( self )
        ColumnSorterMixin.__init__( self, num_columns )
        
        self.itemDataMap = {}
        self._next_data_index = 0
        self._use_display_tuple_for_sort = use_display_tuple_for_sort
        self._custom_client_data = {}
        
        resize_column = 1
        
        for ( i, ( name, width ) ) in enumerate( columns ):
            
            self.InsertColumn( i, name, width = width )
            
            if width == -1: resize_column = i + 1
            
        
        self.setResizeColumn( resize_column )
        
        self.SetMinSize( ( -1, height ) )
        
        self._delete_key_callback = delete_key_callback
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
    
    def Append( self, display_tuple, client_data ):
        
        index = wx.ListCtrl.Append( self, display_tuple )
        
        self.SetItemData( index, self._next_data_index )
        
        if self._use_display_tuple_for_sort:
            
            self.itemDataMap[ self._next_data_index ] = list( display_tuple )
            
            self._custom_client_data[ self._next_data_index ] = client_data
            
        else:
            
            self.itemDataMap[ self._next_data_index ] = list( client_data )
            
        
        self._next_data_index += 1
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE ):
            
            if self._delete_key_callback is not None: self._delete_key_callback()
            
        else: event.Skip()
        
    
    def GetAllSelected( self ):
        
        indices = []
        
        i = self.GetFirstSelected()
        
        while i != -1:
            
            indices.append( i )
            
            i = self.GetNextSelected( i )
            
        
        return indices
        
    
    def GetClientData( self, index = None ):
        
        if index is None:
            
            data_indicies = [ self.GetItemData( index ) for index in range( self.GetItemCount() ) ]
            
            if self._use_display_tuple_for_sort:
                
                datas = [ self._custom_client_data[ data_index ] for data_index in data_indicies ]
                
            else:
                
                datas = [ tuple( self.itemDataMap[ data_index ] ) for data_index in data_indicies ]
                
            
            return datas
            
        else:
            
            data_index = self.GetItemData( index )
            
            if self._use_display_tuple_for_sort:
                
                return self._custom_client_data[ data_index ]
                
            else:
                
                return tuple( self.itemDataMap[ data_index ] )
                
            
        
    
    def GetIndexFromClientData( self, data, column_index = None ):
        
        for index in range( self.GetItemCount() ):
            
            client_data = self.GetClientData( index )
            
            if column_index is None:
                
                comparison_data = client_data
                
            else:
                
                comparison_data = client_data[ column_index ]
                
            
            if comparison_data == data: return index
            
        
        raise HydrusExceptions.NotFoundException( 'Data not found!' )
        
    
    def HasClientData( self, data, column_index = None ):
        
        try:
            
            index = self.GetIndexFromClientData( data, column_index )
            
            return True
            
        except HydrusExceptions.NotFoundException:
            
            return False
            
        
    
    def GetListCtrl( self ): return self
    
    def GetSelectedClientData( self ):
        
        indices = self.GetAllSelected()
        
        results = []
        
        for index in indices:
            
            results.append( self.GetClientData( index ) )
            
        
        return results
        
    
    def RemoveAllSelected( self ):
        
        indices = self.GetAllSelected()
        
        indices.reverse() # so we don't screw with the indices of deletees below
        
        for index in indices: self.DeleteItem( index )
        
    
    def UpdateValue( self, index, column, display_value, data_value ):
        
        self.SetStringItem( index, column, display_value )
        
        data_index = self.GetItemData( index )
        
        self.itemDataMap[ data_index ][ column ] = data_value
        
    
    def UpdateRow( self, index, display_tuple, client_data ):
        
        column = 0
        
        for value in display_tuple:
            
            self.SetStringItem( index, column, value )
            
            column += 1
            
        
        data_index = self.GetItemData( index )
        
        if self._use_display_tuple_for_sort:
            
            self.itemDataMap[ data_index ] = list( display_tuple )
            
            self._custom_client_data[ data_index ] = client_data
            
        else:
            
            self.itemDataMap[ data_index ] = list( client_data )
            
        
    
class SeedCacheControl( SaneListCtrl ):
    
    def __init__( self, parent, seed_cache ):
        
        height = 300
        columns = [ ( 'source', -1 ), ( 'status', 90 ), ( 'added', 150 ), ( 'last modified', 150 ), ( 'note', 200 ) ]
        
        SaneListCtrl.__init__( self, parent, height, columns )
        
        self._seed_cache = seed_cache
        
        for info_tuple in self._seed_cache.GetSeedsWithInfo():
            
            self._AddSeed( info_tuple )
            
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        HydrusGlobals.client_controller.sub( self, 'NotifySeedUpdated', 'seed_cache_seed_updated' )
        
    
    def _AddSeed( self, info_tuple ):
        
        pretty_tuple = self._GetPrettyTuple( info_tuple )
        
        self.Append( pretty_tuple, info_tuple )
        
    
    def _GetPrettyTuple( self, info_tuple ):
        
        ( seed, status, added_timestamp, last_modified_timestamp, note ) = info_tuple
        
        pretty_seed = HydrusData.ToString( seed )
        pretty_status = CC.status_string_lookup[ status ]
        pretty_added = HydrusData.ConvertTimestampToPrettyAgo( added_timestamp )
        pretty_modified = HydrusData.ConvertTimestampToPrettyAgo( last_modified_timestamp )
        pretty_note = note
        
        return ( pretty_seed, pretty_status, pretty_added, pretty_modified, pretty_note )
        
    
    def _CopySelectedNotes( self ):
        
        notes = []
        
        seeds_to_reset = set()
        
        for ( seed, status, added_timestamp, last_modified_timestamp, note ) in self.GetSelectedClientData():
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( notes )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _SetSelectedUnknown( self ):
        
        seeds_to_reset = set()
        
        for ( seed, status, added_timestamp, last_modified_timestamp, note ) in self.GetSelectedClientData():
            
            if status != CC.STATUS_UNKNOWN:
                
                seeds_to_reset.add( seed )
                
            
        
        for seed in seeds_to_reset:
            
            self._seed_cache.UpdateSeedStatus( seed, CC.STATUS_UNKNOWN )
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'copy_seed_notes': self._CopySelectedNotes()
            elif command == 'set_seed_unknown': self._SetSelectedUnknown()
            else: event.Skip()
            
        
    
    def EventShowMenu( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_seed_notes' ), 'copy notes' )
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'set_seed_unknown' ), 'try again' )
        
        self.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
    def NotifySeedAdded( self, seed ):
        
        if self._seed_cache.HasSeed( seed ):
            
            info_tuple = self._seed_cache
            
        
    
    def NotifySeedUpdated( self, seed ):
        
        if self._seed_cache.HasSeed( seed ):
            
            info_tuple = self._seed_cache.GetSeedInfo( seed )
            
            if self.HasClientData( seed, 0 ):
                
                index = self.GetIndexFromClientData( seed, 0 )
                
                pretty_tuple = self._GetPrettyTuple( info_tuple )
                
                self.UpdateRow( index, pretty_tuple, info_tuple )
                
            else:
                
                self._AddSeed( info_tuple )
                
            
        else:
            
            if self.HasClientData( seed, 0 ):
                
                index = self.GetIndexFromClientData( seed, 0 )
                
                self.DeleteItem( index )
                
            
        
    
class Shortcut( wx.TextCtrl ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7 ):
        
        self._modifier = modifier
        self._key = key
        
        wx.TextCtrl.__init__( self, parent, style = wx.TE_PROCESS_ENTER )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._SetShortcutString()
        
    
    def _SetShortcutString( self ):
        
        display_string = ''
        
        if self._modifier == wx.ACCEL_ALT: display_string += 'alt + '
        elif self._modifier == wx.ACCEL_CTRL: display_string += 'ctrl + '
        elif self._modifier == wx.ACCEL_SHIFT: display_string += 'shift + '
        
        if self._key in range( 65, 91 ): display_string += chr( self._key + 32 ) # + 32 for converting ascii A -> a
        elif self._key in range( 97, 123 ): display_string += chr( self._key )
        else: display_string += CC.wxk_code_string_lookup[ self._key ]
        
        wx.TextCtrl.SetValue( self, display_string )
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in range( 65, 91 ) or event.KeyCode in CC.wxk_code_string_lookup.keys():
            
            modifier = wx.ACCEL_NORMAL
            
            if event.AltDown(): modifier = wx.ACCEL_ALT
            elif event.CmdDown(): modifier = wx.ACCEL_CTRL
            elif event.ShiftDown(): modifier = wx.ACCEL_SHIFT
            
            ( self._modifier, self._key ) = ClientData.GetShortcutFromEvent( event )
            
            self._SetShortcutString()
        
    
    def GetValue( self ): return ( self._modifier, self._key )
    
    def SetValue( self, modifier, key ):
        
        ( self._modifier, self._key ) = ( modifier, key )
        
        self._SetShortcutString()
        
    
class StaticBox( wx.Panel ):
    
    def __init__( self, parent, title ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self._sizer = wx.BoxSizer( wx.VERTICAL )
        
        normal_font = wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT )
        
        normal_font_size = normal_font.GetPointSize()
        normal_font_family = normal_font.GetFamily()
        
        title_font = wx.Font( int( normal_font_size ), normal_font_family, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD )
        
        title_text = wx.StaticText( self, label = title, style = wx.ALIGN_CENTER )
        title_text.SetFont( title_font )
        
        self._sizer.AddF( title_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( self._sizer )
        
    
    def AddF( self, widget, flags ): self._sizer.AddF( widget, flags )
    
class StaticBoxSorterForListBoxTags( StaticBox ):
    
    def __init__( self, parent, title ):
        
        StaticBox.__init__( self, parent, title )
        
        self._sorter = wx.Choice( self )
        
        self._sorter.Append( 'lexicographic (a-z)', CC.SORT_BY_LEXICOGRAPHIC_ASC )
        self._sorter.Append( 'lexicographic (z-a)', CC.SORT_BY_LEXICOGRAPHIC_DESC )
        self._sorter.Append( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
        self._sorter.Append( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
        
        if HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_ASC: self._sorter.Select( 0 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_DESC: self._sorter.Select( 1 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_DESC: self._sorter.Select( 2 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_ASC: self._sorter.Select( 3 )
        
        self._sorter.Bind( wx.EVT_CHOICE, self.EventSort )
        
        self.AddF( self._sorter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def ChangeTagRepository( self, service_key ): self._tags_box.ChangeTagRepository( service_key )
    
    def EventSort( self, event ):
        
        selection = self._sorter.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            sort = self._sorter.GetClientData( selection )
            
            self._tags_box.SetSort( sort )
            
        
    
    def SetTagsBox( self, tags_box ):
        
        self._tags_box = tags_box
        
        self.AddF( self._tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def SetTagsByMedia( self, media, force_reload = False ): self._tags_box.SetTagsByMedia( media, force_reload = force_reload )
    
class RadioBox( StaticBox ):
    
    def __init__( self, parent, title, choice_pairs, initial_index = None ):
        
        StaticBox.__init__( self, parent, title )
        
        self._indices_to_radio_buttons = {}
        self._radio_buttons_to_data = {}
        
        first_button = True
        
        for ( index, ( text, data ) ) in enumerate( choice_pairs ):
            
            if first_button:
                
                style = wx.RB_GROUP
                
                first_button = False
                
            else: style = 0
            
            radio_button = wx.RadioButton( self, label = text, style = style )
            
            self.AddF( radio_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._indices_to_radio_buttons[ index ] = radio_button
            self._radio_buttons_to_data[ radio_button ] = data
            
        
        if initial_index is not None and initial_index in self._indices_to_radio_buttons: self._indices_to_radio_buttons[ initial_index ].SetValue( True )
        
    
    def GetSelectedClientData( self ):
        
        for radio_button in self._radio_buttons_to_data.keys():
            
            if radio_button.GetValue() == True: return self._radio_buttons_to_data[ radio_button ]
            
        
    
    def SetSelection( self, index ): self._indices_to_radio_buttons[ index ].SetValue( True )
    
    def SetString( self, index, text ): self._indices_to_radio_buttons[ index ].SetLabel( text )
    
class ShowKeys( Frame ):
    
    def __init__( self, key_type, keys ):
        
        if key_type == 'registration': title = 'Registration Keys'
        elif key_type == 'access': title = 'Access Keys'
        
        # give it no parent, so this doesn't close when the dialog is closed!
        Frame.__init__( self, None, title = HydrusGlobals.client_controller.PrepStringForDisplay( title ) )
        
        self._key_type = key_type
        self._keys = keys
        
        #
        
        self._text_ctrl = wx.TextCtrl( self, style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP )
        
        self._save_to_file = wx.Button( self, label = 'save to file' )
        self._save_to_file.Bind( wx.EVT_BUTTON, self.EventSaveToFile )
        
        self._done = wx.Button( self, id = wx.ID_OK, label = 'done' )
        self._done.Bind( wx.EVT_BUTTON, self.EventDone )
        
        #
        
        if key_type == 'registration': prepend = 'r'
        else: prepend = ''
        
        self._text = os.linesep.join( [ prepend + key.encode( 'hex' ) for key in self._keys ] )
        
        self._text_ctrl.SetValue( self._text )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._text_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._save_to_file, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( self._done, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 500: x = 500
        if y < 200: y = 200
        
        self.SetInitialSize( ( x, y ) )
        
        self.Show( True )
        
    
    def EventDone( self, event ): self.Close()
    
    def EventSaveToFile( self, event ):
        
        filename = 'keys.txt'
        
        with wx.FileDialog( None, style=wx.FD_SAVE, defaultFile = filename ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                with open( dlg.GetPath(), 'wb' ) as f: f.write( self._text )
                
            
        
    