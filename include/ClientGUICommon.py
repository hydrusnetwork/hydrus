import collections
import HydrusConstants as HC
import ClientConstants as CC
import ClientGUIMixins
import itertools
import os
import random
import time
import traceback
import wx
import wx.combo
import wx.richtext
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from wx.lib.mixins.listctrl import ColumnSorterMixin

ID_TIMER_ANIMATED = wx.NewId()
ID_TIMER_SLIDESHOW = wx.NewId()
ID_TIMER_MEDIA_INFO_DISPLAY = wx.NewId()
ID_TIMER_DROPDOWN_HIDE = wx.NewId()
ID_TIMER_AC_LAG = wx.NewId()

# Zooms

ZOOMINS = [ 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0 ]
ZOOMOUTS = [ 20.0, 10.0, 5.0, 3.0, 2.0, 1.5, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.5, 0.3, 0.2, 0.15, 0.1, 0.05, 0.01 ]

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

class AnimatedStaticTextTimestamp( wx.StaticText ):
    
    def __init__( self, parent, prefix, rendering_function, timestamp, suffix ):
        
        self._prefix = prefix
        self._rendering_function = rendering_function
        self._timestamp = timestamp
        self._suffix = suffix
        
        self._last_tick = int( time.time() )
        
        wx.StaticText.__init__( self, parent, label = self._prefix + self._rendering_function( self._timestamp ) + self._suffix )
        
        HC.pubsub.sub( self, 'Tick', 'animated_tick' )
        
    
    def Tick( self ):
        
        update = False
        
        now = int( time.time() )
        
        difference = abs( now - self._timestamp )
        
        if difference < 3600: update = True
        elif difference < 3600 * 24 and now - self._last_tick > 60: update = True
        elif now - self._last_tick > 3600: update = True
        
        if update:
            
            self.SetLabel( self._prefix + self._rendering_function( self._timestamp ) + self._suffix )
            
            wx.PostEvent( self.GetEventHandler(), wx.SizeEvent() )
            
        
    
# much of this is based on the excellent TexCtrlAutoComplete class by Edward Flick, Michele Petrazzo and Will Sadkin, just with plenty of simplification and integration into hydrus
class AutoCompleteDropdown( wx.TextCtrl ):
    
    def __init__( self, parent ):
        
        wx.TextCtrl.__init__( self, parent, style=wx.TE_PROCESS_ENTER )
        
        #self._dropdown_window = wx.PopupWindow( self, flags = wx.BORDER_RAISED )
        #self._dropdown_window = wx.PopupTransientWindow( self, style = wx.BORDER_RAISED )
        #self._dropdown_window = wx.Window( self, style = wx.BORDER_RAISED )
        
        #self._dropdown_window = wx.Panel( self )
        
        self._dropdown_window = wx.Frame( self, style = wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_RAISED )
        
        self._dropdown_window.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self._dropdown_list = self._InitDropDownList()
        
        self._first_letters = ''
        self._cached_results = self._InitCachedResults()
        
        self.Bind( wx.EVT_SET_FOCUS, self.EventSetFocus )
        self.Bind( wx.EVT_KILL_FOCUS, self.EventKillFocus )
        
        self.Bind( wx.EVT_TEXT, self.EventText, self )
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown, self )
        
        self.Bind( wx.EVT_MOVE, self.EventMove )
        self.Bind( wx.EVT_SIZE, self.EventMove )
        
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        
        self.Bind( wx.EVT_TIMER, self.EventDropdownHideTimer, id = ID_TIMER_DROPDOWN_HIDE )
        self.Bind( wx.EVT_TIMER, self.EventLagTimer, id = ID_TIMER_AC_LAG )
        
        self._move_hide_timer = wx.Timer( self, id = ID_TIMER_DROPDOWN_HIDE )
        self._lag_timer = wx.Timer( self, id = ID_TIMER_AC_LAG )
        
        tlp = self.GetTopLevelParent()
        
        tlp.Bind( wx.EVT_MOVE, self.EventMove )
        
    
    def _BroadcastChoice( self, predicate ): pass
    
    def BroadcastChoice( self, predicate ):
        
        self._BroadcastChoice( predicate )
        
        self.Clear()
        
        wx.CallAfter( self._UpdateList )
        
    
    def _HideDropdown( self ): self._dropdown_window.Show( False )
    
    def _ShowDropdownIfFocussed( self ):
        
        if not self._dropdown_window.IsShown() and self.GetTopLevelParent().IsActive() and wx.Window.FindFocus() == self:
            
            ( my_width, my_height ) = self.GetSize()
            
            self._dropdown_window.Fit()
            
            self._dropdown_window.SetSize( ( my_width, -1 ) )
            
            self._dropdown_window.Layout()
            
            self._dropdown_window.SetPosition( self.ClientToScreenXY( -2, my_height - 2 ) )
            
            self._dropdown_window.Show()
            
        
    
    def _UpdateList( self ): pass
    
    def EventDropdownHideTimer( self, event ):
        
        try: self._ShowDropdownIfFocussed()
        except: pass
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ) and self.GetValue() == '' and len( self._dropdown_list ) == 0: self._BroadcastChoice( None )
        elif event.KeyCode == wx.WXK_ESCAPE: self.GetTopLevelParent().SetFocus()
        elif event.KeyCode in ( wx.WXK_UP, wx.WXK_NUMPAD_UP, wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ) and self.GetValue() == '' and len( self._dropdown_list ) == 0:
            
            if event.KeyCode in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ): id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select_up' )
            elif event.KeyCode in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ): id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select_down' )
            
            new_event = wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = id )
            
            self.ProcessEvent( new_event )
            
        else: self._dropdown_list.ProcessEvent( event )
        
    
    def EventKillFocus( self, event ):
        
        new_window = event.GetWindow()
        
        if new_window == self._dropdown_window or new_window in self._dropdown_window.GetChildren(): pass
        else: self._HideDropdown()
        
        event.Skip()
        
    
    def EventLagTimer( self, event ): self._UpdateList()
    
    def EventMouseWheel( self, event ):
        
        if self.GetValue() == '' and len( self._dropdown_list ) == 0:
            
            if event.GetWheelRotation() > 0: id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select_up' )
            else: id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'select_down' )
            
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
                
            
        
    
    def EventMove( self, event ):
        
        try:
            
            try: self._HideDropdown()
            except: pass
            
            lag = 100
            
            self._move_hide_timer.Start( lag, wx.TIMER_ONE_SHOT )
            
        except wx.PyDeadObjectError: pass
        
        event.Skip()
        
    
    def EventSetFocus( self, event ):
        
        self._UpdateList()
        
        self._ShowDropdownIfFocussed()
        
        event.Skip()
        
    
    def EventText( self, event ):
        
        num_chars = len( self.GetValue() )
        
        if num_chars == 0: lag = 0
        else: lag = 150
        #lag = 0
        self._lag_timer.Start( lag, wx.TIMER_ONE_SHOT )
        
    
class AutoCompleteDropdownContacts( AutoCompleteDropdown ):
    
    def __init__( self, parent, compose_key, identity ):
        
        AutoCompleteDropdown.__init__( self, parent )
        
        self._compose_key = compose_key
        self._identity = identity
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._dropdown_list, FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
    
    def _BroadcastChoice( self, contact_name ): HC.pubsub.pub( 'add_contact', self._compose_key, contact_name )
    
    def _GenerateMatches( self ):
        
        num_first_letters = 1
        
        entry = self.GetValue()
        
        if entry == '':
            
            self._first_letters = ''
            
            matches = []
            
        else:
            
            if len( entry ) >= num_first_letters:
                
                if entry[ : num_first_letters ] != self._first_letters:
                    
                    self._first_letters = entry[ : num_first_letters ]
                    
                    self._cached_results = HC.app.Read( 'autocomplete_contacts', entry, name_to_exclude = self._identity.GetName() )
                    
                
                matches = self._cached_results.GetMatches( entry )
                
            else: matches = []
            
        
        return matches
        
    
    def _InitCachedResults( self ): return CC.AutocompleteMatches( [] )
    
    def _InitDropDownList( self ): return ListBoxMessagesActiveOnly( self._dropdown_window, self.BroadcastChoice )
    
    def _UpdateList( self ):
        
        matches = self._GenerateMatches()
        
        # this obv needs to be SetValues or whatever
        self._dropdown_list.SetTexts( matches )
        
        if len( matches ) > 0: self._ShowDropdownIfFocussed()
        else: self._HideDropdown()
        
    
class AutoCompleteDropdownMessageTerms( AutoCompleteDropdown ):
    
    def __init__( self, parent, page_key, identity ):
        
        AutoCompleteDropdown.__init__( self, parent )
        
        self._page_key = page_key
        self._identity = identity
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._dropdown_list, FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
    
    def _BroadcastChoice( self, predicate ): HC.pubsub.pub( 'add_predicate', self._page_key, predicate )
    
    def _InitCachedResults( self ): return CC.AutocompleteMatchesCounted( {} )
    
    def _InitDropDownList( self ): return ListBoxMessagesActiveOnly( self._dropdown_window, self.BroadcastChoice )
    
    def _GenerateMatches( self ):
        
        entry = self.GetValue()
        
        if entry.startswith( '-' ): search_term = entry[1:]
        else: search_term = entry
        
        if search_term == '': matches = HC.app.Read( 'message_system_predicates', self._identity )
        else: matches = [ ( entry, None ) ]
        
        return matches
        
    
    def _UpdateList( self ):
        
        matches = self._GenerateMatches()
        
        self._dropdown_list.SetTerms( matches )
        
        if len( matches ) > 0: self._ShowDropdownIfFocussed()
        else: self._HideDropdown()
        
    
class AutoCompleteDropdownTags( AutoCompleteDropdown ):
    
    def __init__( self, parent, file_service_identifier, tag_service_identifier ):
        
        AutoCompleteDropdown.__init__( self, parent )
        
        self._options = HC.app.Read( 'options' )
        
        self._current_namespace = ''
        self._current_matches = []
        
        self._file_service_identifier = file_service_identifier
        self._tag_service_identifier = tag_service_identifier
        
        name = self._file_service_identifier.GetName()
        
        self._file_repo_button = wx.Button( self._dropdown_window, label = name )
        self._file_repo_button.Bind( wx.EVT_BUTTON, self.EventFileButton )
        
        name = self._tag_service_identifier.GetName()
        
        self._tag_repo_button = wx.Button( self._dropdown_window, label = name )
        self._tag_repo_button.Bind( wx.EVT_BUTTON, self.EventTagButton )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _InitCachedResults( self ): return CC.AutocompleteMatchesPredicates( HC.LOCAL_FILE_SERVICE_IDENTIFIER, [] )
    
    def _InitDropDownList( self ): return TagsBoxActiveOnly( self._dropdown_window, self.BroadcastChoice )
    
    def _UpdateList( self ):
        
        matches = self._GenerateMatches()
        
        self._dropdown_list.SetPredicates( matches )
        
        self._current_matches = matches
        
    
    def EventFileButton( self, event ):
        
        service_identifiers = []
        service_identifiers.append( HC.COMBINED_FILE_SERVICE_IDENTIFIER )
        service_identifiers.append( HC.LOCAL_FILE_SERVICE_IDENTIFIER )
        service_identifiers.extend( HC.app.Read( 'service_identifiers', ( HC.FILE_REPOSITORY, ) ) )
        
        menu = wx.Menu()
        
        for service_identifier in service_identifiers: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'change_file_repository', service_identifier ), service_identifier.GetName() )
        
        self.PopupMenu( menu )
        
        menu.Destroy()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'change_file_repository':
                    
                    service_identifier = data
                    
                    self._file_service_identifier = service_identifier
                    
                    name = service_identifier.GetName()
                    
                    self._file_repo_button.SetLabel( name )
                    
                    HC.pubsub.pub( 'change_file_repository', self._page_key, service_identifier )
                    
                elif command == 'change_tag_repository':
                    
                    service_identifier = data
                    
                    self._tag_service_identifier = service_identifier
                    
                    name = service_identifier.GetName()
                    
                    self._tag_repo_button.SetLabel( name )
                    
                    HC.pubsub.pub( 'change_tag_repository', self._page_key, service_identifier )
                    
                else:
                    
                    event.Skip()
                    
                    return # this is about select_up and select_down
                    
                
                self._first_letters = ''
                self._current_namespace = ''
                
                self._UpdateList()
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def EventTagButton( self, event ):
        
        service_identifiers = []
        service_identifiers.append( HC.COMBINED_TAG_SERVICE_IDENTIFIER )
        service_identifiers.append( HC.LOCAL_TAG_SERVICE_IDENTIFIER )
        service_identifiers.extend( HC.app.Read( 'service_identifiers', ( HC.TAG_REPOSITORY, ) ) )
        
        menu = wx.Menu()
        
        for service_identifier in service_identifiers: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'change_tag_repository', service_identifier ), service_identifier.GetName() )
        
        self.PopupMenu( menu )
        
        menu.Destroy()
        
    
class AutoCompleteDropdownTagsRead( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, page_key, file_service_identifier, tag_service_identifier, media_callable ):
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_identifier, tag_service_identifier )
        
        self._media_callable = media_callable
        self._page_key = page_key
        
        self._include_current = True
        self._include_pending = True
        
        self._include_current_tags = OnOffButton( self._dropdown_window, self._page_key, 'notify_include_current', on_label = 'include current tags', off_label = 'exclude current tags' )
        self._include_current_tags.SetToolTipString( 'select whether to include current tags in the search' )
        self._include_pending_tags = OnOffButton( self._dropdown_window, self._page_key, 'notify_include_pending', on_label = 'include pending tags', off_label = 'exclude pending tags' )
        self._include_pending_tags.SetToolTipString( 'select whether to include pending tags in the search' )
        
        self._synchronised = OnOffButton( self._dropdown_window, self._page_key, 'notify_search_immediately', on_label = 'searching immediately', off_label = 'waiting' )
        self._synchronised.SetToolTipString( 'select whether to renew the search as soon as a new predicate is entered' )
        
        button_hbox_1 = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox_1.AddF( self._include_current_tags, FLAGS_EXPAND_BOTH_WAYS )
        button_hbox_1.AddF( self._include_pending_tags, FLAGS_EXPAND_BOTH_WAYS )
        
        button_hbox_2 = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox_2.AddF( self._file_repo_button, FLAGS_EXPAND_BOTH_WAYS )
        button_hbox_2.AddF( self._tag_repo_button, FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( button_hbox_1, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._synchronised, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( button_hbox_2, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._dropdown_list, FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
        HC.pubsub.sub( self, 'SetSynchronisedWait', 'synchronised_wait_switch' )
        
        HC.pubsub.sub( self, 'IncludeCurrent', 'notify_include_current' )
        HC.pubsub.sub( self, 'IncludePending', 'notify_include_pending' )
        
    
    def _BroadcastChoice( self, predicate ): HC.pubsub.pub( 'add_predicate', self._page_key, predicate )
    
    def _GenerateMatches( self ):
        
        num_first_letters = self._options[ 'num_autocomplete_chars' ]
        
        raw_entry = self.GetValue()
        
        if raw_entry.startswith( '-' ):
            
            operator = '-'
            
            search_text = raw_entry[1:]
            
        else:
            
            operator = '+'
            
            search_text = raw_entry
            
        
        search_text = HC.CleanTag( search_text )
        
        if search_text == '':
            
            self._first_letters = ''
            self._current_namespace = ''
            
            if self._file_service_identifier == HC.COMBINED_FILE_SERVICE_IDENTIFIER: s_i = self._tag_service_identifier
            else: s_i = self._file_service_identifier
            
            matches = HC.app.Read( 'file_system_predicates', s_i )
            
        else:
            
            must_do_a_search = False
            
            if ':' in search_text:
                
                ( namespace, half_complete_tag ) = search_text.split( ':' )
                
                if namespace != self._current_namespace:
                    
                    self._current_namespace = namespace # do a new search, no matter what half_complete tag is
                    
                    must_do_a_search = True
                    
                
            else:
                
                self._current_namespace = ''
                
                half_complete_tag = search_text
                
            
            if len( half_complete_tag ) >= num_first_letters:
                
                if must_do_a_search or self._first_letters == '' or not half_complete_tag.startswith( self._first_letters ):
                    
                    self._first_letters = half_complete_tag
                    
                    media = self._media_callable()
                    
                    # if synchro not on, then can't rely on current media as being accurate for current preds, so search db normally
                    if media is None or not self._synchronised.IsOn(): self._cached_results = HC.app.Read( 'autocomplete_tags', file_service_identifier = self._file_service_identifier, tag_service_identifier = self._tag_service_identifier, half_complete_tag = search_text, include_current = self._include_current, include_pending = self._include_pending )
                    else:
                        
                        tags_managers = []
                        
                        for m in media:
                            
                            if m.IsCollection(): tags_managers.extend( m.GetSingletonsTagsManagers() )
                            else: tags_managers.append( m.GetTagsManager() )
                            
                        
                        lists_of_tags = []
                        
                        if self._include_current: lists_of_tags += [ list( tags_manager.GetCurrent( self._tag_service_identifier ) ) for tags_manager in tags_managers ]
                        if self._include_pending: lists_of_tags += [ list( tags_manager.GetPending( self._tag_service_identifier ) ) for tags_manager in tags_managers ]
                        
                        all_tags_flat_iterable = itertools.chain.from_iterable( lists_of_tags )
                        
                        all_tags_flat = [ tag for tag in all_tags_flat_iterable if HC.SearchEntryMatchesTag( half_complete_tag, tag ) ]
                        
                        if self._current_namespace != '': all_tags_flat = [ tag for tag in all_tags_flat if tag.startswith( self._current_namespace + ':' ) ]
                        
                        tags_to_count = collections.Counter( all_tags_flat )
                        
                        self._cached_results = CC.AutocompleteMatchesPredicates( self._tag_service_identifier, [ HC.Predicate( HC.PREDICATE_TYPE_TAG, ( operator, tag ), count ) for ( tag, count ) in tags_to_count.items() ] )
                        
                    
                
                matches = self._cached_results.GetMatches( half_complete_tag )
                
            else: matches = []
            
            if self._current_namespace != '': matches.insert( 0, HC.Predicate( HC.PREDICATE_TYPE_NAMESPACE, ( operator, namespace ), None ) )
            
            entry_predicate = HC.Predicate( HC.PREDICATE_TYPE_TAG, ( operator, search_text ), None )
            
            try:
                
                index = matches.index( entry_predicate )
                
                predicate = matches[ index ]
                
                del matches[ index ]
                
                matches.insert( 0, predicate )
                
            except: pass
            
        
        for match in matches:
            
            if match.GetPredicateType() == HC.PREDICATE_TYPE_TAG: match.SetOperator( operator )
            
        
        return matches
        
    
    def IncludeCurrent( self, page_key, value ):
        
        if page_key == self._page_key: self._include_current = value
        
        self._first_letters = ''
        self._current_namespace = ''
        
    
    def IncludePending( self, page_key, value ):
        
        if page_key == self._page_key: self._include_pending = value
        
        self._first_letters = ''
        self._current_namespace = ''
        
    
    def SetSynchronisedWait( self, page_key ):
        
        if page_key == self._page_key: self._synchronised.EventButton( None )
        
    
class AutoCompleteDropdownTagsWrite( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, chosen_tag_callable, file_service_identifier, tag_service_identifier ):
        
        self._chosen_tag_callable = chosen_tag_callable
        
        self._page_key = None # this makes the parent's eventmenu pubsubs with page_key simpler!
        
        self._options = HC.app.Read( 'options' )
        
        if self._options[ 'show_all_tags_in_autocomplete' ]: file_service_identifier = HC.COMBINED_FILE_SERVICE_IDENTIFIER
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_identifier, tag_service_identifier )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._file_repo_button, FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( self._tag_repo_button, FLAGS_EXPAND_BOTH_WAYS )
        
        vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._dropdown_list, FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
    
    def _BroadcastChoice( self, predicate ):
        
        if predicate is None: self._chosen_tag_callable( None )
        else:
            
            ( operator, tag ) = predicate.GetValue()
            
            parent_manager = HC.app.GetTagParentsManager()
            
            parents = parent_manager.GetParents( self._tag_service_identifier, tag )
            
            self._chosen_tag_callable( tag, parents )
            
        
    
    def _GenerateMatches( self ):
        
        num_first_letters = self._options[ 'num_autocomplete_chars' ]
        
        raw_entry = self.GetValue()
        
        search_text = HC.CleanTag( raw_entry )
        
        if search_text == '':
            
            self._first_letters = ''
            self._current_namespace = ''
            
            matches = []
            
        else:
            
            must_do_a_search = False
            
            if ':' in search_text:
                
                ( namespace, half_complete_tag ) = search_text.split( ':' )
                
                if namespace != self._current_namespace:
                    
                    self._current_namespace = namespace # do a new search, no matter what half_complete tag is
                    
                    must_do_a_search = True
                    
                
            else:
                
                self._current_namespace = ''
                
                half_complete_tag = search_text
                
            
            if len( half_complete_tag ) >= num_first_letters:
                
                if must_do_a_search or self._first_letters == '' or not half_complete_tag.startswith( self._first_letters ):
                    
                    self._first_letters = half_complete_tag
                    
                    self._cached_results = HC.app.Read( 'autocomplete_tags', file_service_identifier = self._file_service_identifier, tag_service_identifier = self._tag_service_identifier, half_complete_tag = search_text, collapse = False )
                    
                
                matches = self._cached_results.GetMatches( half_complete_tag )
                
            else: matches = []
            
            # do the 'put whatever they typed in at the top, whether it has count or not'
            # now with sibling support!
            # and parent support!
            # this is getting pretty ugly, and I should really move it into the matches processing, I think!
            
            top_predicates = []
            
            top_predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', search_text ), 0 ) )
            
            siblings_manager = HC.app.GetTagSiblingsManager()
            
            sibling = siblings_manager.GetSibling( search_text )
            
            if sibling is not None: top_predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', sibling ), 0 ) )
            
            for predicate in top_predicates:
                
                parents = []
                
                try:
                    
                    index = matches.index( predicate )
                    
                    predicate = matches[ index ]
                    
                    matches.remove( predicate )
                    
                    while matches[ index ].GetPredicateType() == HC.PREDICATE_TYPE_PARENT:
                        
                        parent = matches[ index ]
                        
                        matches.remove( parent )
                        
                        parents.append( parent )
                        
                    
                except:
                    
                    if predicate.GetPredicateType() == HC.PREDICATE_TYPE_TAG:
                        
                        tag = predicate.GetTag()
                        
                        parents_manager = HC.app.GetTagParentsManager()
                        
                        raw_parents = parents_manager.GetParents( self._tag_service_identifier, tag )
                        
                        parents = [ HC.Predicate( HC.PREDICATE_TYPE_PARENT, raw_parent, None ) for raw_parent in raw_parents ]
                        
                    
                
                parents.reverse()
                
                for parent in parents: matches.insert( 0, parent )
                
                matches.insert( 0, predicate )
                
            
        
        return matches
        
    
class BufferedWindow( wx.Window ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Window.__init__( self, *args, **kwargs )
        
        if 'size' in kwargs:
            
            ( x, y ) = kwargs[ 'size' ]
            
            self._canvas_bmp = wx.EmptyBitmap( x, y, 24 )
            
        else: self._canvas_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        
        
    
    def GetDC( self ): return wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp )
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
        
        if my_width != current_bmp_width or my_height != current_bmp_height: self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
        
    
class BetterChoice( wx.Choice ):
    
    def GetChoice( self ):
        
        selection = self.GetSelection()
        
        if selection != wx.NOT_FOUND: return self.GetClientData( selection )
        else: raise Exception( 'choice not chosen' )
        
    
class CheckboxCollect( wx.combo.ComboCtrl ):
    
    def __init__( self, parent, page_key = None ):
        
        wx.combo.ComboCtrl.__init__( self, parent, style = wx.CB_READONLY )
        
        self._page_key = page_key
        
        options = HC.app.Read( 'options' )
        
        sort_by = options[ 'sort_by' ]
        
        collect_types = set()
        
        for ( sort_by_type, namespaces ) in sort_by: collect_types.update( namespaces )
        
        collect_types = list( [ ( namespace, ( 'namespace', namespace ) ) for namespace in collect_types ] )
        collect_types.sort()
        
        ratings_service_identifiers = HC.app.Read( 'service_identifiers', ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for service_identifier in ratings_service_identifiers: collect_types.append( ( service_identifier.GetName(), ( 'rating', service_identifier ) ) )
        
        popup = self._Popup( collect_types )
        
        #self.UseAltPopupWindow( True )
        
        self.SetPopupControl( popup )
        
    
    def GetChoice( self ): return self._collect_by
    
    def SetCollectTypes( self, collect_types, collect_type_strings ):
        
        if len( collect_type_strings ) > 0:
            
            self.SetValue( 'collect by ' + '-'.join( collect_type_strings ) )
            
            self._collect_by = collect_types
            
        else:
            
            self.SetValue( 'no collections' )
            
            self._collect_by = None
            
        
        HC.pubsub.pub( 'collect_media', self._page_key, self._collect_by )
        
    
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
                
                options = HC.app.Read( 'options' )
                
                default = options[ 'default_collect' ]
                
                if default is not None: self.SetCheckedStrings( default )
                
                self.Bind( wx.EVT_CHECKLISTBOX, self.EventChanged )
                
                self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
                
                self.EventChanged( None )
                
            
            # as inspired by http://trac.wxwidgets.org/attachment/ticket/14413/test_clb_workaround.py
            # what a clusterfuck
            
            def EventLeftDown( self, event ):
                
                index = self.HitTest( event.GetPosition() )
                
                if index != wx.NOT_FOUND:
                    
                    self.Check( index, not self.IsChecked( index ) )
                    
                    self.EventChanged( event )
                    
                
                event.Skip()
                
            
            def EventChanged( self, event ):
                
                collect_types = []
                
                for i in self.GetChecked(): collect_types.append( self.GetClientData( i ) )
                
                collect_type_strings = self.GetCheckedStrings()
                
                self._special_parent.SetCollectTypes( collect_types, collect_type_strings )
                
            
        
    
class ChoiceCollect( BetterChoice ):
    
    def __init__( self, parent, page_key = None, sort_by = None ):
        
        BetterChoice.__init__( self, parent )
        
        self._page_key = page_key
        
        options = HC.app.Read( 'options' )
        
        if sort_by is None: sort_by = options[ 'sort_by' ]
        
        collect_choices = CC.GenerateCollectByChoices( sort_by )
        
        for ( string, data ) in collect_choices: self.Append( string, data )
        
        self.SetSelection( options[ 'default_collect' ] )
        
        self.Bind( wx.EVT_CHOICE, self.EventChoice )
        
    
    def EventChoice( self, event ):
        
        if self._page_key is not None:
            
            selection = self.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                collect_by = self.GetClientData( selection )
                
                HC.pubsub.pub( 'collect_media', self._page_key, collect_by )
                
            
        
    
class ChoiceSort( BetterChoice ):
    
    def __init__( self, parent, page_key = None, sort_by = None ):
        
        BetterChoice.__init__( self, parent )
        
        self._page_key = page_key
        
        options = HC.app.Read( 'options' )
        
        if sort_by is None: sort_by = options[ 'sort_by' ]
        
        sort_choices = CC.SORT_CHOICES + sort_by
        
        ratings_service_identifiers = HC.app.Read( 'service_identifiers', ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for ratings_service_identifier in ratings_service_identifiers:
            
            sort_choices.append( ( 'rating_descend', ratings_service_identifier ) )
            sort_choices.append( ( 'rating_ascend', ratings_service_identifier ) )
            
        
        for ( sort_by_type, sort_by_data ) in sort_choices:
            
            if sort_by_type == 'system': string = CC.sort_string_lookup[ sort_by_data ]
            elif sort_by_type == 'namespaces': string = '-'.join( sort_by_data )
            elif sort_by_type == 'rating_descend': string = sort_by_data.GetName() + ' rating highest first'
            elif sort_by_type == 'rating_ascend': string = sort_by_data.GetName() + ' rating lowest first'
            
            self.Append( 'sort by ' + string, ( sort_by_type, sort_by_data ) )
            
        
        try: self.SetSelection( options[ 'default_sort' ] )
        except: pass
        
        self.Bind( wx.EVT_CHOICE, self.EventChoice )
        
        HC.pubsub.sub( self, 'ACollectHappened', 'collect_media' )
        
    
    def _BroadcastSort( self ):
        
        selection = self.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            sort_by = self.GetClientData( selection )
            
            HC.pubsub.pub( 'sort_media', self._page_key, sort_by )
            
        
    
    def ACollectHappened( self, page_key, collect_by ):
        
        if page_key == self._page_key: self._BroadcastSort()
        
    
    def EventChoice( self, event ):
        
        if self._page_key is not None: self._BroadcastSort()
        
    
class FileDropTarget( wx.FileDropTarget ):
    
    def __init__( self, callable ):
        
        wx.FileDropTarget.__init__( self )
        
        self._callable = callable
        
    
    def OnDropFiles( self, x, y, paths ): wx.CallAfter( self._callable, paths )
    
class Frame( wx.Frame ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Frame.__init__( self, *args, **kwargs )
        
        self._options = HC.app.Read( 'options' )
        
        #self.SetDoubleBuffered( True )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
    
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
        
        self._list_box = wx.ListBox( self, style = wx.LB_SINGLE | wx.LB_SORT )
        
        self._empty_panel = wx.Panel( self )
        
        self._empty_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self._current_name = None
        
        self._current_panel = self._empty_panel
        
        self._panel_sizer = wx.BoxSizer( wx.VERTICAL )
        
        self._panel_sizer.AddF( self._empty_panel, FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._list_box, FLAGS_EXPAND_PERPENDICULAR )
        hbox.AddF( self._panel_sizer, FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._list_box.Bind( wx.EVT_LISTBOX, self.EventSelection )
        
        self.SetSizer( hbox )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _RecalcListBoxWidth( self ): self.Layout()
    
    def _Select( self, selection ):
        
        if selection == wx.NOT_FOUND: self._current_name = None
        else: self._current_name = self._list_box.GetString( selection )
        
        self._current_panel.Hide()
        
        self._list_box.SetSelection( selection )
        
        if selection == wx.NOT_FOUND: self._current_panel = self._empty_panel
        else:
            
            panel_info = self._list_box.GetClientData( selection )
            
            if type( panel_info ) == tuple:
                
                ( classname, args, kwargs ) = panel_info
                
                page = classname( *args, **kwargs )
                
                page.Hide()
                
                self._panel_sizer.AddF( page, FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                self._list_box.SetClientData( selection, page )
                
                self._RecalcListBoxWidth()
                
            
            self._current_panel = self._list_box.GetClientData( selection )
            
        
        self._current_panel.Show()
        
        self.Layout()
        
        event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGED, -1 )
        
        self.ProcessEvent( event )
        
    
    def AddPage( self, page, name, select = False ):
        
        if type( page ) != tuple:
            
            page.Hide()
            
            self._panel_sizer.AddF( page, FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        self._list_box.Append( name, page )
        
        self._RecalcListBoxWidth()
        
        if self._list_box.GetCount() == 1: self._Select( 0 )
        elif select: self._Select( self._list_box.FindString( name ) )
        
    
    def DeleteAllPages( self ):
        
        self._panel_sizer.Detach( self._empty_panel )
        
        self._panel_sizer.Clear( deleteWindows = True )
        
        self._panel_sizer.AddF( self._empty_panel, FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._current_name = None
        
        self._current_panel = self._empty_panel
        
        self._list_box.Clear()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'select_down': self.SelectDown()
                elif command == 'select_up': self.SelectUp()
                else: event.Skip()
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
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
        
    
    def GetNameToPageDict( self ): return { self._list_box.GetString( i ) : self._list_box.GetClientData( i ) for i in range( self._list_box.GetCount() ) if type( self._list_box.GetClientData( i ) ) != tuple }
    
    def NameExists( self, name, panel = None ): return self._list_box.FindString( name ) != wx.NOT_FOUND
    
    def DeleteCurrentPage( self ):
        
        selection = self._list_box.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            next_selection = selection + 1
            previous_selection = selection - 1
            
            if next_selection < self._list_box.GetCount(): self._Select( next_selection )
            elif previous_selection >= 0: self._Select( previous_selection )
            else: self._Select( wx.NOT_FOUND )
            
            panel_info = self._list_box.GetClientData( selection )
            
            if type( panel_info ) != tuple: self._panel_sizer.Remove( panel_info )
            
            self._list_box.Delete( selection )
            
            self._RecalcListBoxWidth()
            
        
    
    def RenamePage( self, name, new_name ):
        
        if self._list_box.FindString( new_name ) != wx.NOT_FOUND: raise Exception( 'That name is already in use!' )
        
        if self._current_name == name: self._current_name = new_name
        
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
            
        
    
    def SelectPage( self, page ):
        
        for i in range( self._list_box.GetCount() ):
            
            if self._list_box.GetClientData( i ) == page:
                
                self._Select( i )
                
                return
                
            
        
    
    def SelectUp( self ):
        
        current_selection = self._list_box.FindString( self._current_name )
        
        if current_selection != wx.NOT_FOUND:
            
            num_entries = self._list_box.GetCount()
            
            if current_selection == 0: selection = num_entries - 1
            else: selection = current_selection - 1
            
            if selection != current_selection: self._Select( selection )
            
        
    
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
        
    
class ListBox( wx.ScrolledWindow ):
    
    def __init__( self, parent, min_height = 250 ):
        
        wx.ScrolledWindow.__init__( self, parent, style = wx.VSCROLL | wx.BORDER_DOUBLE )
        
        self._ordered_strings = []
        self._strings_to_terms = {}
        
        self._options = HC.app.Read( 'options' )
        
        self._canvas_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self._current_selected_index = None
        
        dc = self._GetScrolledDC()
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        ( text_x, self._text_y ) = dc.GetTextExtent( 'abcdefghijklmnopqrstuvwxyz' )
        
        self._num_rows_per_page = 0
        
        self.SetScrollRate( 0, self._text_y )
        
        self.SetMinSize( ( 50, min_height ) )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventMouseSelect )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventDClick )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventMouseRightClick )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def __len__( self ): return len( self._ordered_strings )
    
    def _Activate( self, s, term ): pass
    
    def _DrawTexts( self ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        dc = self._GetScrolledDC()
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        i = 0
        
        dc.SetBackground( wx.Brush( wx.Colour( 255, 255, 255 ) ) )
        
        dc.Clear()
        
        for ( i, text ) in enumerate( self._ordered_strings ):
            
            ( r, g, b ) = self._GetTextColour( text )
            
            text_colour = wx.Colour( r, g, b )
            
            if self._current_selected_index is not None and i == self._current_selected_index:
                
                dc.SetBrush( wx.Brush( text_colour ) )
                
                dc.SetPen( wx.TRANSPARENT_PEN )
                
                dc.DrawRectangle( 0, i * self._text_y, my_width, self._text_y )
                
                text_colour = wx.WHITE
                
            
            dc.SetTextForeground( text_colour )
            
            ( x, y ) = ( 3, i * self._text_y )
            
            dc.DrawText( text, x, y )
            
        
    
    def _GetIndexUnderMouse( self, mouse_event ):
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        ( x_scroll, y_scroll ) = self.GetViewStart()
        
        y_offset = y_scroll * yUnit
        
        y = mouse_event.GetY() + y_offset
        
        row_index = ( y / self._text_y )
        
        if row_index >= len( self._ordered_strings ): return None
        
        return row_index
        
    
    def _GetScrolledDC( self ):
        
        cdc = wx.ClientDC( self )
        
        self.DoPrepareDC( cdc ) # because this is a scrolled window
        
        return wx.BufferedDC( cdc, self._canvas_bmp )
        
    
    def _GetTextColour( self, text ): return ( 0, 111, 250 )
    
    def _Select( self, index ):
        
        if index is not None:
            
            if index == -1 or index > len( self._ordered_strings ): index = len( self._ordered_strings ) - 1
            elif index == len( self._ordered_strings ) or index < -1: index = 0
            
        
        self._current_selected_index = index
        
        self._DrawTexts()
        
        if self._current_selected_index is not None:
            
            # scroll to index, if needed
            
            y = self._text_y * self._current_selected_index
            
            ( start_x, start_y ) = self.GetViewStart()
            
            ( x_unit, y_unit ) = self.GetScrollPixelsPerUnit()
            
            ( width, height ) = self.GetClientSize()
            
            if y < start_y * y_unit:
                
                y_to_scroll_to = y / y_unit
                
                self.Scroll( -1, y_to_scroll_to )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE ) )
                
            elif y > ( start_y * y_unit ) + height:
                
                y_to_scroll_to = ( y - height ) / y_unit
                
                self.Scroll( -1, y_to_scroll_to + 3 )
                
                wx.PostEvent( self, wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE ) )
                
            
        
    
    def _TextsHaveChanged( self ):
        
        self._current_selected_index = None
        
        total_height = self._text_y * len( self._ordered_strings )
        
        ( my_x, my_y ) = self._canvas_bmp.GetSize()
        
        if my_y != total_height: wx.PostEvent( self, wx.SizeEvent() )
        else: self._DrawTexts()
        
    
    def EventDClick( self, event ):
        
        index = self._GetIndexUnderMouse( event )
        
        if index is not None and index == self._current_selected_index:
            
            s = self._ordered_strings[ self._current_selected_index ]
            
            term = self._strings_to_terms[ s ]
            
            self._Activate( s, term )
            
        
    
    def EventKeyDown( self, event ):
        
        key_code = event.GetKeyCode()
        
        if self._current_selected_index is not None:
            
            if key_code in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                s = self._ordered_strings[ self._current_selected_index ]
                
                term = self._strings_to_terms[ s ]
                
                self._Activate( s, term )
                
            elif key_code in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ): self._Select( self._current_selected_index - 1 )
            elif key_code in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ): self._Select( self._current_selected_index + 1 )
            elif key_code == wx.WXK_PAGEUP: self._Select( self._current_selected_index - self._num_rows_per_page )
            elif key_code == wx.WXK_PAGEDOWN: self._Select( self._current_selected_index + self._num_rows_per_page )
            else: event.Skip()
            
        else: event.Skip()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'copy': HC.pubsub.pub( 'clipboard', 'text', data )
                else:
                    
                    event.Skip()
                    
                    return # this is about select_up and select_down
                    
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def EventMouseRightClick( self, event ):
        
        index = self._GetIndexUnderMouse( event )
        
        self._Select( index )
        
        if self._current_selected_index is not None:
            
            menu = wx.Menu()
            
            term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
            
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy', term ), 'copy ' + term )
            
            if ':' in term:
                
                sub_term = term.split( ':', 1 )[1]
                
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy', sub_term ), 'copy ' + sub_term )
                
            
            self.PopupMenu( menu )
            
            menu.Destroy()
            
        
        event.Skip()
        
    
    def EventMouseSelect( self, event ):
        
        index = self._GetIndexUnderMouse( event )
        
        self._Select( index )
        
        event.Skip()
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp, wx.BUFFER_VIRTUAL_AREA )
    
    def EventResize( self, event ):
        
        ( client_x, client_y ) = self.GetClientSize()
        
        ( my_x, my_y ) = self._canvas_bmp.GetSize()
        
        self._num_rows_per_page = client_y / self._text_y
        
        total_height = self._text_y * len( self._ordered_strings )
        
        if my_x != client_x or my_y != total_height:
            
            new_y = max( client_y, total_height )
            
            self.SetVirtualSize( ( client_x, new_y ) )
            
            self._canvas_bmp = wx.EmptyBitmap( client_x, new_y, 24 )
            
            self._DrawTexts()
            
        
    
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
                else: term_string = term + ' (' + HC.ConvertIntToPrettyString( count ) + ')'
                
                self._ordered_strings.append( term_string )
                self._strings_to_terms[ term_string ] = term
                
            
            self._TextsHaveChanged()
            
            if len( matches ) > 0: self._Select( 0 )
            
        
    
class ListBoxMessagesPredicates( ListBoxMessages ):
    
    def __init__( self, parent, page_key, initial_predicates = [] ):
        
        ListBoxMessages.__init__( self, parent )
        
        self._page_key = page_key
        
        if len( initial_predicates ) > 0:
            
            for predicate in initial_predicates:
                
                self._ordered_strings.append( predicate )
                self._strings_to_terms[ predicate ] = predicate
                
            
            self._TextsHaveChanged()
            
        
    
    def _Activate( self, s, term ): HC.pubsub.pub( 'remove_predicate', self._page_key, term )
    
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
        
    
class NoneableSpinCtrl( wx.Panel ):
    
    def __init__( self, parent, message, value, none_phrase = 'no limit', max = 1000000, multiplier = 1, num_dimensions = 1 ):
        
        wx.Panel.__init__( self, parent )
        
        self._num_dimensions = num_dimensions
        self._multiplier = multiplier
        
        self._checkbox = wx.CheckBox( self, label = none_phrase )
        self._checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckBox )
        
        if value is None:
            
            self._one = wx.SpinCtrl( self, initial = 0, max = max, size = ( 80, -1 ) )
            self._one.Disable()
            
            if num_dimensions == 2:
                
                self._two = wx.SpinCtrl( self, initial = 0, max = max, size = ( 80, -1 ) )
                self._two.Disable()
                
            
            self._checkbox.SetValue( True )
            
        else:
            
            if num_dimensions == 2:
                
                ( value, value_2 ) = value
                
                self._two = wx.SpinCtrl( self, max = max, size = ( 80, -1 ) )
                self._two.SetValue( value_2 / multiplier )
                
            
            self._one = wx.SpinCtrl( self, max = max, size = ( 80, -1 ) )
            self._one.SetValue( value / multiplier )
            
            self._checkbox.SetValue( False )
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        hbox.AddF( wx.StaticText( self, label=message + ': ' ), FLAGS_MIXED )
        hbox.AddF( self._one, FLAGS_MIXED )
        
        if self._num_dimensions == 2:
            
            hbox.AddF( wx.StaticText( self, label = 'x' ), FLAGS_MIXED )
            hbox.AddF( self._two, FLAGS_MIXED )
            
        
        hbox.AddF( self._checkbox, FLAGS_MIXED )
        
        self.SetSizer( hbox )
        
    
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
            
            self._one.Enable()
            if self._num_dimensions == 2: self._two.Enable()
            
            if self._num_dimensions == 2:
                
                ( value, y ) = value
                
                self._two.SetValue( y / self._multiplier )
                
            
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
        
        HC.pubsub.sub( self, 'HitButton', 'hit_on_off_button' )
        
    
    def EventButton( self, event ):
        
        if self._on:
            
            self._on = False
            
            self.SetLabel( self._off_label )
            
            self.SetForegroundColour( ( 128, 0, 0 ) )
            
            HC.pubsub.pub( self._topic, self._page_key, False )
            
        else:
            
            self._on = True
            
            self.SetLabel( self._on_label )
            
            self.SetForegroundColour( ( 0, 128, 0 ) )
            
            HC.pubsub.pub( self._topic, self._page_key, True )
            
        
    
    def IsOn( self ): return self._on
    
class PopupMessage( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent, style = wx.BORDER_SIMPLE )
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
    
    def EventDismiss( self, event ):
        
        self.GetParent().Dismiss( self )
        
    
class PopupMessageError( PopupMessage ):
    
    def __init__( self, parent, message_string ):
        
        PopupMessage.__init__( self, parent )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        error = wx.StaticText( self, label = 'error', style = wx.ALIGN_CENTER )
        error.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
        text = wx.StaticText( self, label = message_string ) # make this multi-line. There's an easy way to do that, right? A func that takes a pixel width, I think
        text.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
        vbox.AddF( error, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( text, FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
class PopupMessageFiles( PopupMessage ):
    
    def __init__( self, parent, message_string, hashes ):
        
        PopupMessage.__init__( self, parent )
        
        self._hashes = hashes
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = wx.StaticText( self, label = message_string ) # make this multi-line. There's an easy way to do that, right? A func that takes a pixel width, I think
        text.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
        button = wx.Button( self, label = 'show files in new page' )
        button.Bind( wx.EVT_BUTTON, self.EventButton )
        
        vbox.AddF( text, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( button, FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def EventButton( self, event ):
    
        search_context = CC.FileSearchContext()
        
        unsorted_file_query_result = HC.app.Read( 'media_results', search_context, self._hashes )
        
        media_results = { media_result for media_result in unsorted_file_query_result }
        
        HC.pubsub.pub( 'new_page_query', HC.LOCAL_FILE_SERVICE_IDENTIFIER, initial_media_results = media_results )
        
    
class PopupMessageText( PopupMessage ):
    
    def __init__( self, parent, message_string ):
        
        PopupMessage.__init__( self, parent )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = wx.StaticText( self, label = message_string ) # make this multi-line. There's an easy way to do that, right? A func that takes a pixel width, I think
        text.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
        vbox.AddF( text, FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
class PopupMessageManager( wx.Frame ):
    
    def __init__( self, top_level_parent ):
        
        wx.Frame.__init__( self, top_level_parent, style = wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_NONE )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self.SetSizer( vbox )
        
        self._message_windows = []
        
        top_level_parent.Bind( wx.EVT_SIZE, self.EventMove )
        top_level_parent.Bind( wx.EVT_MOVE, self.EventMove )
        
        self._SizeAndPositionAndShow()
        
        HC.pubsub.sub( self, 'AddMessage', 'message' )
        # maybe make a ding noise when a new message arrives
        
        # on right mouse click, dismiss relevant message and refit
        
    
    def _CreateMessageWindow( self, message ):
        
        message_type = message.GetType()
        info = message.GetInfo()
        
        if message_type == HC.MESSAGE_TYPE_TEXT:
            
            message_string = info
            
            print( 'message: ' + message_string )
            
            window = PopupMessageText( self, message_string )
            
        elif message_type == HC.MESSAGE_TYPE_ERROR:
            
            exception = info
            
            message_string = str( exception )
            
            print( 'error: ' + message_string )
            
            window = PopupMessageError( self, message_string )
            
        elif message_type == HC.MESSAGE_TYPE_FILES:
            
            ( message_string, hashes ) = info
            
            window = PopupMessageFiles( self, message_string, hashes )
            
        
        return window
        
    
    def _SizeAndPositionAndShow( self ):
        
        self.Fit()
        
        parent = self.GetParent()
        
        ( parent_width, parent_height ) = parent.GetClientSize()
        
        ( my_width, my_height ) = self.GetClientSize()
        
        my_x = ( parent_width - my_width ) - 5
        my_y = ( parent_height - my_height ) - 15
        
        self.SetPosition( parent.ClientToScreenXY( my_x, my_y ) )
        
        if len( self._message_windows ) > 0: self.Show()
        else: self.Hide()
        
    
    def AddMessage( self, message ):
        
        window = self._CreateMessageWindow( message )
        
        self._message_windows.append( window )
        
        vbox = self.GetSizer()
        
        vbox.AddF( window, FLAGS_EXPAND_PERPENDICULAR )
        
        self._SizeAndPositionAndShow()
        
    
    def Dismiss( self, window ):
        
        self._message_windows.remove( window )
        
        vbox = self.GetSizer()
        
        vbox.Detach( window )
        
        window.Destroy()
        
        self._SizeAndPositionAndShow()
        
    
    def EventMove( self, event ):
        
        self._SizeAndPositionAndShow()
        
        event.Skip()
        
    
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
    ID_REGEX_NUMBER_EXT = 20
    ID_REGEX_AUTHOR = 21
    ID_REGEX_BACKSPACE = 22
    ID_REGEX_SET = 23
    ID_REGEX_NOT_SET = 24
    
    def __init__( self, parent ):
        
        wx.Button.__init__( self, parent, label = 'regex shortcuts' )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def EventButton( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( -1, 'click on a phrase to copy to clipboard' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_REGEX_WHITESPACE, r'whitespace character - \s' )
        menu.Append( self.ID_REGEX_NUMBER, r'number character - \d' )
        menu.Append( self.ID_REGEX_ALPHANUMERIC, r'alphanumeric or backspace character - \w' )
        menu.Append( self.ID_REGEX_ANY, r'any character - .' )
        menu.Append( self.ID_REGEX_BACKSPACE, r'backspace character - \\' )
        menu.Append( self.ID_REGEX_BEGINNING, r'beginning of line - ^' )
        menu.Append( self.ID_REGEX_END, r'end of line - $' )
        menu.Append( self.ID_REGEX_SET, r'any of these - [...]' )
        menu.Append( self.ID_REGEX_NOT_SET, r'anything other than these - [^...]' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_REGEX_0_OR_MORE_GREEDY, r'0 or more matches, consuming as many as possible - *' )
        menu.Append( self.ID_REGEX_1_OR_MORE_GREEDY, r'1 or more matches, consuming as many as possible - +' )
        menu.Append( self.ID_REGEX_0_OR_1_GREEDY, r'0 or 1 matches, preferring 1 - ?' )
        menu.Append( self.ID_REGEX_0_OR_MORE_MINIMAL, r'0 or more matches, consuming as few as possible - *?' )
        menu.Append( self.ID_REGEX_1_OR_MORE_MINIMAL, r'1 or more matches, consuming as few as possible - +?' )
        menu.Append( self.ID_REGEX_0_OR_1_MINIMAL, r'0 or 1 matches, preferring 0 - *' )
        menu.Append( self.ID_REGEX_EXACTLY_M, r'exactly m matches - {m}' )
        menu.Append( self.ID_REGEX_M_TO_N_GREEDY, r'm to n matches, consuming as many as possible - {m,n}' )
        menu.Append( self.ID_REGEX_M_TO_N_MINIMAL, r'm to n matches, consuming as few as possible - {m,n}?' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_REGEX_LOOKAHEAD, r'the next characters are: (non-consuming) - (?=...)' )
        menu.Append( self.ID_REGEX_NEGATIVE_LOOKAHEAD, r'the next characters are not: (non-consuming) - (?!...)' )
        menu.Append( self.ID_REGEX_LOOKBEHIND, r'the previous characters are: (non-consuming) - (?<=...)' )
        menu.Append( self.ID_REGEX_NEGATIVE_LOOKBEHIND, r'the previous characters are not: (non-consuming) - (?<!...)' )
        
        menu.AppendSeparator()
        
        menu.Append( self.ID_REGEX_NUMBER_WITHOUT_ZEROES, r'0074 -> 74 - [1-9]+\d*' )
        menu.Append( self.ID_REGEX_NUMBER_EXT, r'...0074.jpg -> 74 - [1-9]+\d*(?=.{4}$)' )
        menu.Append( self.ID_REGEX_AUTHOR, r'E:\my collection\author name - v4c1p0074.jpg -> author name - [^\\][\w\s]*(?=\s-)' )
        
        self.PopupMenu( menu )
        
        menu.Destroy()
        
    
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
        elif id == self.ID_REGEX_NUMBER_EXT: phrase = r'[1-9]+\d*(?=.{4}$)'
        elif id == self.ID_REGEX_AUTHOR: phrase = r'[^\\][\w\s]*(?=\s-)'
        else: event.Skip()
        
        if phrase is not None:
            
            if wx.TheClipboard.Open():
                
                data = wx.TextDataObject( phrase )
                
                wx.TheClipboard.SetData( data )
                
                wx.TheClipboard.Close()
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
class SaneListCtrl( wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin ):
    
    def __init__( self, parent, height, columns ):
        
        num_columns = len( columns )
        
        wx.ListCtrl.__init__( self, parent, size=( -1, height ), style=wx.LC_REPORT )
        ListCtrlAutoWidthMixin.__init__( self )
        ColumnSorterMixin.__init__( self, num_columns )
        
        self.GetTopLevelParent().SetDoubleBuffered( False ) # windows double buffer makes listctrls refresh and bug out
        
        self.itemDataMap = {}
        self._next_data_index = 0
        
        resize_column = 1
        
        for ( i, ( name, width ) ) in enumerate( columns ):
            
            self.InsertColumn( i, name, width = width )
            
            if width == -1: resize_column = i + 1
            
        
        self.setResizeColumn( resize_column )
        
    
    def Append( self, display_tuple, data_tuple ):
        
        index = wx.ListCtrl.Append( self, display_tuple )
        
        self.SetItemData( index, self._next_data_index )
        
        self.itemDataMap[ self._next_data_index ] = list( data_tuple )
        
        self._next_data_index += 1
        
    
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
            
            datas = [ tuple( self.itemDataMap[ data_index ] ) for data_index in data_indicies ]
            
            return datas
            
        else:
            
            data_index = self.GetItemData( index )
            
            return tuple( self.itemDataMap[ data_index ] )
            
        
    
    def GetIndexFromClientData( self, data ):
        
        for index in range( self.GetItemCount() ):
            
            if self.GetClientData( index ) == data: return index
            
        
        raise Exception( 'Data not found!' )
        
    
    def GetListCtrl( self ): return self
    
    def RemoveAllSelected( self ):
        
        indices = self.GetAllSelected()
        
        indices.reverse() # so we don't screw with the indices of deletees below
        
        for index in indices: self.DeleteItem( index )
        
    
    def UpdateValue( self, index, column, display_value, data_value ):
        
        self.SetStringItem( index, column, display_value )
        
        data_index = self.GetItemData( index )
        
        self.itemDataMap[ data_index ][ column ] = data_value
        
    
    def UpdateRow( self, index, display_tuple, data_tuple ):
        
        column = 0
        
        for value in display_tuple:
            
            self.SetStringItem( index, column, value )
            
            column += 1
            
        
        data_index = self.GetItemData( index )
        
        self.itemDataMap[ data_index ] = data_tuple
        
    
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
        else: display_string += HC.wxk_code_string_lookup[ self._key ]
        
        wx.TextCtrl.SetValue( self, display_string )
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in range( 65, 91 ) or event.KeyCode in HC.wxk_code_string_lookup.keys():
            
            modifier = wx.ACCEL_NORMAL
            
            if event.AltDown(): modifier = wx.ACCEL_ALT
            elif event.ControlDown(): modifier = wx.ACCEL_CTRL
            elif event.ShiftDown(): modifier = wx.ACCEL_SHIFT
            
            ( self._modifier, self._key ) = HC.GetShortcutFromEvent( event )
            
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
        
        self._sizer.AddF( title_text, FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( self._sizer )
        
    
    def AddF( self, widget, flags ): self._sizer.AddF( widget, flags )
    
class AdvancedOptions( StaticBox ):
    
    def __init__( self, parent, title ):
        
        StaticBox.__init__( self, parent, title )
        
        self._collapsible_panel = wx.CollapsiblePane( self, label = 'expand' )
        
        my_panel = self._collapsible_panel.GetPane()
        
        self._InitPanel( my_panel )
        
        self.AddF( self._collapsible_panel, FLAGS_EXPAND_PERPENDICULAR )
        
        self.Bind( wx.EVT_COLLAPSIBLEPANE_CHANGED, self.EventChanged )
        
    
    def _InitPanel( self, panel ): pass
    
    def EventChanged( self, event ):
        
        self.GetParent().Layout() # make this vertical only?
        
        if self._collapsible_panel.IsExpanded(): label = 'collapse'
        else: label = 'expand'
        
        self._collapsible_panel.SetLabel( label )
        
        event.Skip()
        
    
class AdvancedHentaiFoundryOptions( AdvancedOptions ):
    
    def __init__( self, parent ): AdvancedOptions.__init__( self, parent, 'advanced hentai foundry options' )
    
    def _InitPanel( self, panel ):
        
        def offensive_choice():
            
            c = wx.Choice( panel )
            
            c.Append( 'none', 0 )
            c.Append( 'mild', 1 )
            c.Append( 'moderate', 2 )
            c.Append( 'strong', 3 )
            
            c.SetSelection( 3 )
            
            return c
            
        
        self._rating_nudity = offensive_choice()
        self._rating_violence = offensive_choice()
        self._rating_profanity = offensive_choice()
        self._rating_racism = offensive_choice()
        self._rating_sex = offensive_choice()
        self._rating_spoilers = offensive_choice()
        
        self._rating_yaoi = wx.CheckBox( panel )
        self._rating_yuri = wx.CheckBox( panel )
        self._rating_loli = wx.CheckBox( panel )
        self._rating_shota = wx.CheckBox( panel )
        self._rating_teen = wx.CheckBox( panel )
        self._rating_guro = wx.CheckBox( panel )
        self._rating_furry = wx.CheckBox( panel )
        self._rating_beast = wx.CheckBox( panel )
        self._rating_male = wx.CheckBox( panel )
        self._rating_female = wx.CheckBox( panel )
        self._rating_futa = wx.CheckBox( panel )
        self._rating_other = wx.CheckBox( panel )
        
        self._rating_yaoi.SetValue( True )
        self._rating_yuri.SetValue( True )
        self._rating_loli.SetValue( True )
        self._rating_shota.SetValue( True )
        self._rating_teen.SetValue( True )
        self._rating_guro.SetValue( True )
        self._rating_furry.SetValue( True )
        self._rating_beast.SetValue( True )
        self._rating_male.SetValue( True )
        self._rating_female.SetValue( True )
        self._rating_futa.SetValue( True )
        self._rating_other.SetValue( True )
        
        self._filter_order = wx.Choice( panel )
        
        self._filter_order.Append( 'newest first', 'date_new' )
        self._filter_order.Append( 'oldest first', 'date_old' )
        self._filter_order.Append( 'most views first', 'views most' ) # no underscore
        self._filter_order.Append( 'highest rating first', 'rating highest' ) # no underscore
        self._filter_order.Append( 'most favourites first', 'faves most' ) # no underscore
        self._filter_order.Append( 'most popular first', 'popularity most' ) # no underscore
        
        self._filter_order.SetSelection( 0 )
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        gridbox.AddF( wx.StaticText( panel, label = 'nudity' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_nudity, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'violence' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_violence, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'profanity' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_profanity, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'racism' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_racism, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'sex' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_sex, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'spoilers' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_spoilers, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'yaoi' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_yaoi, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'yuri' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_yuri, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'loli' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_loli, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'shota' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_shota, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'teen' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_teen, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'guro' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_guro, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'furry' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_furry, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'beast' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_beast, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'male' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_male, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'female' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_female, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'futa' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_futa, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'other' ), FLAGS_MIXED )
        gridbox.AddF( self._rating_other, FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( panel, label = 'order' ), FLAGS_MIXED )
        gridbox.AddF( self._filter_order, FLAGS_EXPAND_BOTH_WAYS )
        
        panel.SetSizer( gridbox )
        
    
    def GetInfo( self ):
        
        info = {}
        
        info[ 'rating_nudity' ] = self._rating_nudity.GetClientData( self._rating_nudity.GetSelection() )
        info[ 'rating_violence' ] = self._rating_violence.GetClientData( self._rating_violence.GetSelection() )
        info[ 'rating_profanity' ] = self._rating_profanity.GetClientData( self._rating_profanity.GetSelection() )
        info[ 'rating_racism' ] = self._rating_racism.GetClientData( self._rating_racism.GetSelection() )
        info[ 'rating_sex' ] = self._rating_sex.GetClientData( self._rating_sex.GetSelection() )
        info[ 'rating_spoilers' ] = self._rating_spoilers.GetClientData( self._rating_spoilers.GetSelection() )
        
        info[ 'rating_yaoi' ] = int( self._rating_yaoi.GetValue() )
        info[ 'rating_yuri' ] = int( self._rating_yuri.GetValue() )
        info[ 'rating_loli' ] = int( self._rating_loli.GetValue() )
        info[ 'rating_shota' ] = int( self._rating_shota.GetValue() )
        info[ 'rating_teen' ] = int( self._rating_teen.GetValue() )
        info[ 'rating_guro' ] = int( self._rating_guro.GetValue() )
        info[ 'rating_furry' ] = int( self._rating_furry.GetValue() )
        info[ 'rating_beast' ] = int( self._rating_beast.GetValue() )
        info[ 'rating_male' ] = int( self._rating_male.GetValue() )
        info[ 'rating_female' ] = int( self._rating_female.GetValue() )
        info[ 'rating_futa' ] = int( self._rating_futa.GetValue() )
        info[ 'rating_other' ] = int( self._rating_other.GetValue() )
        
        info[ 'filter_media' ] = 'A'
        info[ 'filter_order' ] = self._filter_order.GetClientData( self._filter_order.GetSelection() )
        info[ 'filter_type' ] = 0
        
        return info
        
    
    def SetInfo( self, info ):
        
        self._rating_nudity.SetSelection( info[ 'rating_nudity' ] )
        self._rating_violence.SetSelection( info[ 'rating_violence' ] )
        self._rating_profanity.SetSelection( info[ 'rating_profanity' ] )
        self._rating_racism.SetSelection( info[ 'rating_racism' ] )
        self._rating_sex.SetSelection( info[ 'rating_sex' ] )
        self._rating_spoilers.SetSelection( info[ 'rating_spoilers' ] )
        
        self._rating_yaoi.SetValue( bool( info[ 'rating_yaoi' ] ) )
        self._rating_yuri.SetValue( bool( info[ 'rating_yuri' ] ) )
        self._rating_loli.SetValue( bool( info[ 'rating_loli' ] ) )
        self._rating_shota.SetValue( bool( info[ 'rating_shota' ] ) )
        self._rating_teen.SetValue( bool( info[ 'rating_teen' ] ) )
        self._rating_guro.SetValue( bool( info[ 'rating_guro' ] ) )
        self._rating_furry.SetValue( bool( info[ 'rating_furry' ] ) )
        self._rating_beast.SetValue( bool( info[ 'rating_beast' ] ) )
        self._rating_male.SetValue( bool( info[ 'rating_male' ] ) )
        self._rating_female.SetValue( bool( info[ 'rating_female' ] ) )
        self._rating_futa.SetValue( bool( info[ 'rating_futa' ] ) )
        self._rating_other.SetValue( bool( info[ 'rating_other' ] ) )
        
        #info[ 'filter_media' ] = 'A'
        self._filter_order.SetSelection( info[ 'filter_order' ] )
        #info[ 'filter_type' ] = 0
        
    
class AdvancedImportOptions( AdvancedOptions ):
    
    def __init__( self, parent, initial_settings = {} ):
        
        self._initial_settings = initial_settings
        
        AdvancedOptions.__init__( self, parent, 'advanced import options' )
        
    
    def _InitPanel( self, panel ):
        
        options = HC.app.Read( 'options' )
        
        self._auto_archive = wx.CheckBox( panel )
        
        self._exclude_deleted = wx.CheckBox( panel )
        
        self._min_size = NoneableSpinCtrl( panel, 'minimum size (KB): ', 5120, multiplier = 1024 )
        
        self._min_resolution = NoneableSpinCtrl( panel, 'minimum resolution: ', ( 50, 50 ), num_dimensions = 2 )
        
        hbox1 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox1.AddF( self._auto_archive, FLAGS_MIXED )
        hbox1.AddF( wx.StaticText( panel, label = ' archive all imports' ), FLAGS_MIXED )
        
        hbox2 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox2.AddF( self._exclude_deleted, FLAGS_MIXED )
        hbox2.AddF( wx.StaticText( panel, label = ' exclude already deleted files' ), FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( hbox1, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( hbox2, FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._min_size, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._min_resolution, FLAGS_EXPAND_PERPENDICULAR )
        
        panel.SetSizer( vbox )
        
        self._SetControls( self._initial_settings )
        
    
    def _SetControls( self, info ):
        
        options = HC.app.Read( 'options' )
        
        if 'auto_archive' in info: self._auto_archive.SetValue( info[ 'auto_archive' ] )
        else: self._auto_archive.SetValue( False )
        
        if 'exclude_deleted_files' in info: self._exclude_deleted.SetValue( info[ 'exclude_deleted_files' ] )
        else: self._exclude_deleted.SetValue( options[ 'exclude_deleted_files' ] )
        
        if 'min_size' in info: self._min_size.SetValue( info[ 'min_size' ] )
        else: self._min_size.SetValue( None )
        
        if 'min_resolution' in info: self._min_resolution.SetValue( info[ 'min_resolution' ] )
        else: self._min_resolution.SetValue( None )
        
    
    def GetInfo( self ):
        
        info = {}
        
        if self._auto_archive.GetValue(): info[ 'auto_archive' ] = True
        
        if self._exclude_deleted.GetValue(): info[ 'exclude_deleted_files' ] = True
        
        min_size = self._min_size.GetValue()
        
        if min_size is not None: info[ 'min_size' ] = min_size
        
        min_resolution = self._min_resolution.GetValue()
        
        if min_resolution is not None: info[ 'min_resolution' ] = min_resolution
        
        return info
        
    
    def SetInfo( self, info ): self._SetControls( info )
    
class AdvancedTagOptions( AdvancedOptions ):
    
    def __init__( self, parent, info_string, namespaces = [], initial_settings = {} ):
        
        self._info_string = info_string
        self._namespaces = namespaces
        self._initial_settings = initial_settings
        
        self._checkboxes_to_service_identifiers = {}
        self._service_identifiers_to_namespaces = {}
        
        AdvancedOptions.__init__( self, parent, 'advanced tag options' )
        
    
    def _InitPanel( self, panel ):
        
        service_identifiers = HC.app.Read( 'service_identifiers', ( HC.TAG_REPOSITORY, HC.LOCAL_TAG ) )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        if len( service_identifiers ) > 0:
            
            for service_identifier in service_identifiers:
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                checkbox = wx.CheckBox( panel )
                if service_identifier in self._initial_settings: checkbox.SetValue( True )
                checkbox.Bind( wx.EVT_CHECKBOX, self.EventChecked )
                
                self._checkboxes_to_service_identifiers[ checkbox ] = service_identifier
                
                hbox.AddF( wx.StaticText( panel, label = service_identifier.GetName() ), FLAGS_MIXED )
                hbox.AddF( checkbox, FLAGS_MIXED )
                
                if len( self._namespaces ) > 0:
                    
                    namespace_vbox = wx.BoxSizer( wx.VERTICAL )
                    
                    self._service_identifiers_to_namespaces[ service_identifier ] = []
                    
                    gridbox = wx.FlexGridSizer( 0, 2 )
                    
                    gridbox.AddGrowableCol( 1, 1 )
                    
                    for namespace in self._namespaces:
                        
                        if namespace == '': text = wx.StaticText( panel, label = 'no namespace' )
                        else: text = wx.StaticText( panel, label = namespace )
                        
                        namespace_checkbox = wx.CheckBox( panel )
                        if service_identifier in self._initial_settings and namespace not in self._initial_settings[ service_identifier ]: namespace_checkbox.SetValue( False )
                        else: namespace_checkbox.SetValue( True )
                        namespace_checkbox.Bind( wx.EVT_CHECKBOX, self.EventChecked )
                        
                        self._service_identifiers_to_namespaces[ service_identifier ].append( ( namespace, namespace_checkbox ) )
                        
                        gridbox.AddF( text, FLAGS_MIXED )
                        gridbox.AddF( namespace_checkbox, FLAGS_EXPAND_BOTH_WAYS )
                        
                    
                    hbox.AddF( gridbox, FLAGS_MIXED )
                    
                
                vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( panel, label = self._info_string ), FLAGS_MIXED )
            hbox.AddF( vbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            panel.SetSizer( hbox )
            
        else:
            
            vbox.AddF( wx.StaticText( panel, label = 'no tag repositories' ), FLAGS_EXPAND_BOTH_WAYS )
            
            panel.SetSizer( vbox )
            
        
    
    def EventChecked( self, event ):
        
        wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'advanced_tag_options_changed' ) ) )
        
        event.Skip()
        
    
    def GetInfo( self ):
        
        service_identifiers = [ self._checkboxes_to_service_identifiers[ checkbox ] for checkbox in self._checkboxes_to_service_identifiers.keys() if checkbox.GetValue() ]
        
        result = {}
        
        for service_identifier in service_identifiers:
            
            good_namespaces = []
            
            if service_identifier in self._service_identifiers_to_namespaces:
                
                namespaces = self._service_identifiers_to_namespaces[ service_identifier ]
                
                for ( namespace, namespace_checkbox ) in namespaces:
                    
                    if namespace_checkbox.GetValue(): good_namespaces.append( namespace )
                    
                
            
            result[ service_identifier ] = good_namespaces
            
        
        return result
        
    
    def SetInfo( self, info ):
        
        for ( checkbox, service_identifier ) in self._checkboxes_to_service_identifiers.items():
            
            if service_identifier in info:
                
                checkbox.SetValue( True )
                
                for ( namespace, namespace_checkbox ) in self._service_identifiers_to_namespaces[ service_identifier ]:
                    
                    if namespace in info[ service_identifier ]: namespace_checkbox.SetValue( True )
                    else: namespace_checkbox.SetValue( False )
                    
                
            else:
                
                checkbox.SetValue( False )
                
                for ( namespace, namespace_checkbox ) in self._service_identifiers_to_namespaces[ service_identifier ]: namespace_checkbox.SetValue( True )
                
            
        
    
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
            
            self.AddF( radio_button, FLAGS_EXPAND_PERPENDICULAR )
            
            self._indices_to_radio_buttons[ index ] = radio_button
            self._radio_buttons_to_data[ radio_button ] = data
            
        
        if initial_index is not None and initial_index in self._indices_to_radio_buttons: self._indices_to_radio_buttons[ index ].SetValue( True )
        
    
    def GetSelectedClientData( self ):
        
        for radio_button in self._radio_buttons_to_data.keys():
            
            if radio_button.GetValue() == True: return self._radio_buttons_to_data[ radio_button ]
            
        
    
    def SetSelection( self, index ): self._indices_to_radio_buttons[ index ].SetValue( True )
    
    def SetString( self, index, text ): self._indices_to_radio_buttons[ index ].SetLabel( text )
    
class TagsBox( ListBox ):
    
    def _GetNamespaceColours( self ): return self._options[ 'namespace_colours' ]
    
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
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'copy': HC.pubsub.pub( 'clipboard', 'text', data )
                elif command in ( 'parent', 'sibling' ):
                    
                    tag = data
                    
                    import ClientGUIDialogsManage
                    
                    if command == 'parent':
                        
                        with ClientGUIDialogsManage.DialogManageTagParents( self, tag ) as dlg: dlg.ShowModal()
                        
                    elif command == 'sibling':
                        
                        with ClientGUIDialogsManage.DialogManageTagSiblings( self, tag ) as dlg: dlg.ShowModal()
                        
                    
                else:
                    
                    event.Skip()
                    
                    return # this is about select_up and select_down
                    
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def EventMouseRightClick( self, event ):
        
        index = self._GetIndexUnderMouse( event )
        
        self._Select( index )
        
        if self._current_selected_index is not None:
            
            menu = wx.Menu()
            
            term = self._strings_to_terms[ self._ordered_strings[ self._current_selected_index ] ]
            
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy', term ), 'copy ' + term )
            
            if ':' in term:
                
                sub_term = term.split( ':', 1 )[1]
                
                menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy', sub_term ), 'copy ' + sub_term )
                
            
            menu.AppendSeparator()
            
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'parent', term ), 'add parent to ' + term )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'sibling', term ), 'add sibling to ' + term )
            
            self.PopupMenu( menu )
            
            menu.Destroy()
            
        
        event.Skip()
        
    
class TagsBoxActiveOnly( TagsBox ):
    
    def __init__( self, parent, callable ):
        
        TagsBox.__init__( self, parent )
        
        self._callable = callable
        
        self._predicates = {}
        
    
    def _Activate( self, s, term ): self._callable( term )
    
    def _Select( self, index ):
        
        if index is not None:
            
            if self._current_selected_index is None: direction = 1
            elif index - self._current_selected_index in ( -1, 1 ): direction = index - self._current_selected_index
            else: direction = 1
            
            if index == -1 or index > len( self._ordered_strings ): index = len( self._ordered_strings ) - 1
            elif index == len( self._ordered_strings ) or index < -1: index = 0
            
            s = self._ordered_strings[ index ]
            
            new_term = self._strings_to_terms[ s ]
            
            while new_term.GetPredicateType() == HC.PREDICATE_TYPE_PARENT:
                
                index += direction
                
                if index == -1 or index > len( self._ordered_strings ): index = len( self._ordered_strings ) - 1
                elif index == len( self._ordered_strings ) or index < -1: index = 0
                
                s = self._ordered_strings[ index ]
                
                new_term = self._strings_to_terms[ s ]
                
            
        
        ListBox._Select( self, index )
        
    
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
            
        
    
class TagsBoxCPP( TagsBox ):
    
    def __init__( self, parent, page_key ):
        
        TagsBox.__init__( self, parent, min_height = 200 )
        
        self._sort = self._options[ 'default_tag_sort' ]
        
        self._page_key = page_key
        
        self._tag_service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER
        self._last_media = None
        
        self._current_tags_to_count = {}
        self._pending_tags_to_count = {}
        self._petitioned_tags_to_count = {}
        
        HC.pubsub.sub( self, 'SetTagsByMedia', 'new_tags_selection' )
        HC.pubsub.sub( self, 'ChangeTagRepository', 'change_tag_repository' )
        
    
    def _Activate( self, s, term ):
        
        predicate = HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', term ), None )
        
        HC.pubsub.pub( 'add_predicate', self._page_key, predicate )
        
    
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
        
    
    def ChangeTagRepository( self, page_key, service_identifier ):
        
        if page_key == self._page_key:
            
            self._tag_service_identifier = service_identifier
            
            if self._last_media is not None: self.SetTagsByMedia( self._page_key, self._last_media )
            
        
    
    def SetSort( self, sort ):
        
        self._sort = sort
        
        self._SortTags()
        
    
    def SetTags( self, current_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ):
        
        siblings_manager = HC.app.GetTagSiblingsManager()
        
        current_tags_to_count = siblings_manager.CollapseTagsToCount( current_tags_to_count )
        
        if current_tags_to_count != self._current_tags_to_count or pending_tags_to_count != self._pending_tags_to_count or petitioned_tags_to_count != self._petitioned_tags_to_count:
            
            self._current_tags_to_count = current_tags_to_count
            self._pending_tags_to_count = pending_tags_to_count
            self._petitioned_tags_to_count = petitioned_tags_to_count
            
            all_tags = { tag for tag in self._current_tags_to_count.keys() + self._pending_tags_to_count.keys() + self._petitioned_tags_to_count.keys() }
            
            self._ordered_strings = []
            self._strings_to_terms = {}
            
            for tag in all_tags:
                
                tag_string = tag
                
                if tag in self._current_tags_to_count: tag_string += ' (' + HC.ConvertIntToPrettyString( self._current_tags_to_count[ tag ] ) + ')'
                if tag in self._pending_tags_to_count: tag_string += ' (+' + HC.ConvertIntToPrettyString( self._pending_tags_to_count[ tag ] ) + ')'
                if tag in self._petitioned_tags_to_count: tag_string += ' (-' + HC.ConvertIntToPrettyString( self._petitioned_tags_to_count[ tag ] ) + ')'
                
                sibling = siblings_manager.GetSibling( tag )
                
                if sibling is not None: tag_string += ' (' + sibling + ')'
                
                self._ordered_strings.append( tag_string )
                self._strings_to_terms[ tag_string ] = tag
                
            
            self._SortTags()
            
        
    
    def SetTagsByMedia( self, page_key, media ):
        
        if page_key == self._page_key:
            
            self._last_media = media
            
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = CC.GetMediasTagCount( media, self._tag_service_identifier )
            
            self.SetTags( current_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
            
        
    
class TagsBoxCPPWithSorter( StaticBox ):
    
    def __init__( self, parent, page_key ):
        
        StaticBox.__init__( self, parent, 'selection tags' )
        
        self._options = HC.app.Read( 'options' )
        
        self._sorter = wx.Choice( self )
        
        self._sorter.Append( 'lexicographic (a-z)', CC.SORT_BY_LEXICOGRAPHIC_ASC )
        self._sorter.Append( 'lexicographic (z-a)', CC.SORT_BY_LEXICOGRAPHIC_DESC )
        self._sorter.Append( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
        self._sorter.Append( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
        
        if self._options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_ASC: self._sorter.Select( 0 )
        elif self._options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_DESC: self._sorter.Select( 1 )
        elif self._options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_DESC: self._sorter.Select( 2 )
        elif self._options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_ASC: self._sorter.Select( 3 )
        
        self._sorter.Bind( wx.EVT_CHOICE, self.EventSort )
        
        self._tags_box = TagsBoxCPP( self, page_key )
        
        self.AddF( self._sorter, FLAGS_EXPAND_PERPENDICULAR )
        self.AddF( self._tags_box, FLAGS_EXPAND_BOTH_WAYS )
        
    
    def EventSort( self, event ):
        
        selection = self._sorter.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            sort = self._sorter.GetClientData( selection )
            
            self._tags_box.SetSort( sort )
            
        
    
class TagsBoxFlat( TagsBox ):
    
    def __init__( self, parent, removed_callable ):
        
        TagsBox.__init__( self, parent )
        
        self._removed_callable = removed_callable
        self._tags = set()
        
    
    def _RecalcTags( self ):
        
        self._strings_to_terms = {}
        
        siblings_manager = HC.app.GetTagSiblingsManager()
        
        for tag in self._tags:
            
            tag_string = tag
            
            sibling = siblings_manager.GetSibling( tag )
            
            if sibling is not None: tag_string += ' (' + sibling + ')'
            
            self._strings_to_terms[ tag_string ] = tag
            
        
        self._ordered_strings = self._strings_to_terms.keys()
        
        self._ordered_strings.sort()
        
        self._TextsHaveChanged()
        
    
    def _Activate( self, s, tag ):
        
        if tag in self._tags:
            
            self._tags.discard( tag )
            
            self._RecalcTags()
            
            self._removed_callable( tag )
            
        
    
    def AddTag( self, tag, parents ):
        
        if tag in self._tags: self._tags.discard( tag )
        else:
            
            self._tags.add( tag )
            
            self._tags.update( parents )
            
        
        self._RecalcTags()
        
    
    def GetTags( self ): return self._tags
    
    def SetTags( self, tags ):
        
        self._tags = tags
        
        self._RecalcTags()
        
    
class TagsBoxManage( TagsBox ):
    
    def __init__( self, parent, callable, current_tags, deleted_tags, pending_tags, petitioned_tags ):
        
        TagsBox.__init__( self, parent )
        
        self._callable = callable
        
        self._current_tags = set( current_tags )
        self._deleted_tags = set( deleted_tags )
        self._pending_tags = set( pending_tags )
        self._petitioned_tags = set( petitioned_tags )
        
        self._RebuildTagStrings()
        
    
    def _Activate( self, s, term ): self._callable( term )
    
    def _RebuildTagStrings( self ):
        
        siblings_manager = HC.app.GetTagSiblingsManager()
        
        all_tags = self._current_tags | self._deleted_tags | self._pending_tags | self._petitioned_tags
        
        self._ordered_strings = []
        self._strings_to_terms = {}
        
        for tag in all_tags:
            
            if tag in self._petitioned_tags: prefix = HC.ConvertStatusToPrefix( HC.PETITIONED )
            elif tag in self._current_tags: prefix = HC.ConvertStatusToPrefix( HC.CURRENT )
            elif tag in self._pending_tags:
                
                if tag in self._deleted_tags: prefix = HC.ConvertStatusToPrefix( HC.DELETED_PENDING )
                else: prefix = HC.ConvertStatusToPrefix( HC.PENDING )
                
            else: prefix = HC.ConvertStatusToPrefix( HC.DELETED )
            
            tag_string = prefix + tag
            
            sibling = siblings_manager.GetSibling( tag )
            
            if sibling is not None: tag_string += ' (' + sibling + ')'
            
            self._ordered_strings.append( tag_string )
            self._strings_to_terms[ tag_string ] = tag
            
        
        self._ordered_strings.sort()
        
        self._TextsHaveChanged()
        
    
    def PetitionTag( self, tag ):
        
        self._petitioned_tags.add( tag )
        
        self._RebuildTagStrings()
        
    
    def PendTag( self, tag ):
        
        self._pending_tags.add( tag )
        
        self._RebuildTagStrings()
        
    
    def RescindPetition( self, tag ):
        
        self._petitioned_tags.discard( tag )
        
        self._RebuildTagStrings()
        
    
    def RescindPend( self, tag ):
        
        self._pending_tags.discard( tag )
        
        self._RebuildTagStrings()
        
    
class TagsBoxOptions( TagsBox ):
    
    def __init__( self, parent, initial_namespace_colours ):
        
        TagsBox.__init__( self, parent )
        
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
            
        
    
class TagsBoxPredicates( TagsBox ):
    
    def __init__( self, parent, page_key, initial_predicates = [] ):
        
        TagsBox.__init__( self, parent, min_height = 100 )
        
        self._page_key = page_key
        
        if len( initial_predicates ) > 0:
            
            for predicate in initial_predicates:
                
                predicate_string = predicate.GetUnicode()
                
                self._ordered_strings.append( predicate_string )
                self._strings_to_terms[ predicate_string ] = predicate
                
            
            self._TextsHaveChanged()
            
        
    
    def _Activate( self, s, term ): HC.pubsub.pub( 'remove_predicate', self._page_key, term )
    
    def AddPredicate( self, predicate ):
        
        predicate = predicate.GetCountlessCopy()
        
        predicate_string = predicate.GetUnicode()
        
        inbox_predicate = HC.SYSTEM_PREDICATE_INBOX
        archive_predicate = HC.SYSTEM_PREDICATE_ARCHIVE
        
        if predicate == inbox_predicate and self.HasPredicate( archive_predicate ): self.RemovePredicate( archive_predicate )
        elif predicate == archive_predicate and self.HasPredicate( inbox_predicate ): self.RemovePredicate( inbox_predicate )
        
        local_predicate = HC.SYSTEM_PREDICATE_LOCAL
        not_local_predicate = HC.SYSTEM_PREDICATE_NOT_LOCAL
        
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
                
            
        
    