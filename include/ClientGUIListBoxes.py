import ClientCaches
import ClientConstants as CC
import ClientData
import ClientSearch
import collections
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusTags
import os
import wx

class ListBox( wx.ScrolledWindow ):
    
    TEXT_X_PADDING = 3
    delete_key_activates = False
    
    def __init__( self, parent, min_height = 250 ):
        
        wx.ScrolledWindow.__init__( self, parent, style = wx.VSCROLL | wx.BORDER_DOUBLE )
        
        self._background_colour = wx.Colour( 255, 255, 255 )
        
        self._ordered_strings = []
        self._strings_to_terms = {}
        
        self._client_bmp = wx.EmptyBitmap( 20, 20, 24 )
        
        self._selected_indices = set()
        self._selected_terms = set()
        self._last_hit_index = None
        
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
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        self.Bind( wx.EVT_CHAR_HOOK, self.EventKeyDown )
        
    
    def __len__( self ):
        
        return len( self._ordered_strings )
        
    
    def _Activate( self ):
        
        raise NotImplementedError()
        
    
    def _Deselect( self, index ):
        
        term = self._strings_to_terms[ self._ordered_strings[ index ] ]
        
        self._selected_indices.discard( index )
        self._selected_terms.discard( term )
        
    
    def _GetIndexUnderMouse( self, mouse_event ):
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        ( x_scroll, y_scroll ) = self.GetViewStart()
        
        y_offset = y_scroll * yUnit
        
        y = mouse_event.GetY() + y_offset
        
        row_index = ( y / self._text_y )
        
        if row_index >= len( self._ordered_strings ):
            
            return None
            
        
        return row_index
        
    
    def _GetSelectedIncludeExcludePredicates( self ):
        
        include_predicates = []
        exclude_predicates = []
        
        for term in self._selected_terms:
            
            if isinstance( term, ClientSearch.Predicate ):
                
                predicate_type = term.GetType()
                
                if predicate_type in ( HC.PREDICATE_TYPE_TAG, HC.PREDICATE_TYPE_NAMESPACE, HC.PREDICATE_TYPE_WILDCARD ):
                    
                    value = term.GetValue()
                    
                    include_predicates.append( ClientSearch.Predicate( predicate_type, value ) )
                    exclude_predicates.append( ClientSearch.Predicate( predicate_type, value, False ) )
                    
                else:
                    
                    include_predicates.append( term )
                    
                
            else:
                
                s = term
                
                include_predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, term ) )
                exclude_predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, term, False ) )
                
            
        
        return ( include_predicates, exclude_predicates )
        
    
    def _GetTextColour( self, text ): return ( 0, 111, 250 )
    
    def _HandleClick( self, event ):
        
        hit_index = self._GetIndexUnderMouse( event )
        
        shift = event.ShiftDown()
        ctrl = event.CmdDown()
        
        self._Hit( shift, ctrl, hit_index )
        
    
    def _Hit( self, shift, ctrl, hit_index ):
        
        if hit_index is not None:
            
            if hit_index == -1 or hit_index > len( self._ordered_strings ):
                
                hit_index = len( self._ordered_strings ) - 1
                
            elif hit_index == len( self._ordered_strings ) or hit_index < -1:
                
                hit_index = 0
                
            
        
        to_select = set()
        to_deselect = set()
        
        if shift:
            
            if hit_index is not None:
                
                if self._last_hit_index is not None:
                    
                    lower = min( hit_index, self._last_hit_index )
                    upper = max( hit_index, self._last_hit_index )
                    
                    to_select = range( lower, upper + 1 )
                    
                else:
                    
                    to_select.add( hit_index )
                    
                
            
        elif ctrl:
            
            if hit_index is not None:
                
                if hit_index in self._selected_indices:
                    
                    to_deselect.add( hit_index )
                    
                else:
                    
                    to_select.add( hit_index )
                    
                
            
        else:
            
            if hit_index is None:
                
                to_deselect = set( self._selected_indices )
                
            else:
                
                if hit_index not in self._selected_indices:
                    
                    to_select.add( hit_index )
                    to_deselect = set( self._selected_indices )
                    
                
            
        
        for index in to_select:
            
            self._Select( index )
            
        
        for index in to_deselect:
            
            self._Deselect( index )
            
        
        self._last_hit_index = hit_index
        
        if self._last_hit_index is not None:
            
            y = self._text_y * self._last_hit_index
            
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
            
            if current_index in self._selected_indices:
                
                dc.SetBrush( wx.Brush( text_colour ) )
                
                dc.SetPen( wx.TRANSPARENT_PEN )
                
                dc.DrawRectangle( 0, i * self._text_y, my_width, self._text_y )
                
                text_colour = self._background_colour
                
            
            dc.SetTextForeground( text_colour )
            
            ( x, y ) = ( self.TEXT_X_PADDING, i * self._text_y )
            
            dc.DrawText( text, x, y )
            
        
        self._dirty = False
        
    
    def _Select( self, index ):
    
        term = self._strings_to_terms[ self._ordered_strings[ index ] ]
        
        self._selected_indices.add( index )
        self._selected_terms.add( term )
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
        self.Refresh()
        
    
    def _TextsHaveChanged( self ):
        
        previous_selected_terms = self._selected_terms
        
        self._selected_indices = set()
        self._selected_terms = set()
        
        for ( s, term ) in self._strings_to_terms.items():
            
            if term in previous_selected_terms:
                
                index = self._ordered_strings.index( s )
                
                self._Select( index )
                
                
            
        
        ( my_x, my_y ) = self.GetClientSize()
        
        total_height = max( self._text_y * len( self._ordered_strings ), my_y )
        
        ( virtual_x, virtual_y ) = self.GetVirtualSize()
        
        if total_height != virtual_y:
            
            wx.PostEvent( self, wx.SizeEvent() )
            
        else:
            
            self._SetDirty()
            
        
    
    def EventDClick( self, event ):
        
        self._Activate()
        
    
    def EventEraseBackground( self, event ): pass
    
    def EventKeyDown( self, event ):
        
        shift = event.ShiftDown()
        ctrl = event.CmdDown()
        
        key_code = event.GetKeyCode()
        
        if key_code in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ) or ( self.delete_key_activates and key_code in CC.DELETE_KEYS ):
            
            self._Activate()
            
        else:
            
            if ctrl and key_code in ( ord( 'A' ), ord( 'a' ) ):
                
                for i in range( len( self._ordered_strings ) ):
                    
                    self._Select( i )
                    
                    self._SetDirty()
                    
                
            else:
                
                hit_index = None
                
                if len( self._ordered_strings ) > 0:
                    
                    if key_code in ( wx.WXK_HOME, wx.WXK_NUMPAD_HOME ):
                        
                        hit_index = 0
                        
                    elif key_code in ( wx.WXK_END, wx.WXK_NUMPAD_END ):
                        
                        hit_index = len( self._ordered_strings ) - 1
                        
                    elif self._last_hit_index is not None:
                        
                        if key_code in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ):
                            
                            hit_index = self._last_hit_index - 1
                            
                        elif key_code in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ):
                            
                            hit_index = self._last_hit_index + 1
                            
                        elif key_code in ( wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP ):
                            
                            hit_index = max( 0, self._last_hit_index - self._num_rows_per_page )
                            
                        elif key_code in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN ):
                            
                            hit_index = min( len( self._ordered_strings ) - 1, self._last_hit_index + self._num_rows_per_page )
                            
                        
                    
                
                if hit_index is None:
                    
                    event.Skip()
                    
                else:
                    
                    self._Hit( shift, ctrl, hit_index )
                    
                
            
        
    
    def EventMouseSelect( self, event ):
        
        self._HandleClick( event )
        
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
        
    
    def GetIdealHeight( self ):
        
        return self._text_y * len( self._ordered_strings ) + 20
        
    
    def SetTexts( self, ordered_strings ):
        
        if ordered_strings != self._ordered_strings:
            
            self._ordered_strings = ordered_strings
            self._strings_to_terms = { s : s for s in ordered_strings }
            
            self._TextsHaveChanged()
            
        
    
class ListBoxTags( ListBox ):
    
    has_counts = False
    
    can_spawn_new_windows = True
    
    def __init__( self, *args, **kwargs ):
        
        ListBox.__init__( self, *args, **kwargs )
        
        self._predicates_callable = None
        
        self._background_colour = wx.Colour( *HC.options[ 'gui_colours' ][ 'tags_box' ] )
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventMouseRightClick )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventMouseMiddleClick )
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        HydrusGlobals.client_controller.sub( self, 'SiblingsHaveChanged', 'notify_new_siblings_gui' )
        
    
    def _GetNamespaceColours( self ): return HC.options[ 'namespace_colours' ]
    
    def _GetAllTagsForClipboard( self, with_counts = False ):
        
        return self._ordered_strings
        
    
    def _GetTextColour( self, tag_string ):
        
        namespace_colours = self._GetNamespaceColours()
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag_string )
        
        if namespace != '':
            
            if namespace.startswith( '-' ): namespace = namespace[1:]
            elif namespace.startswith( '(+) ' ): namespace = namespace[4:]
            elif namespace.startswith( '(-) ' ): namespace = namespace[4:]
            elif namespace.startswith( '(X) ' ): namespace = namespace[4:]
            elif namespace.startswith( '    ' ): namespace = namespace[4:]
            
            if namespace in namespace_colours:
                
                ( r, g, b ) = namespace_colours[ namespace ]
                
            else:
                
                ( r, g, b ) = namespace_colours[ None ]
                
            
        else:
            
            ( r, g, b ) = namespace_colours[ '' ]
            
        
        return ( r, g, b )
        
    
    def _NewSearchPage( self ):

        predicates = []
        
        for term in self._selected_terms:
            
            if isinstance( term, ClientSearch.Predicate ):
                
                predicates.append( term )
                
            else:
                
                predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, term ) )
                
            
        
        predicates = HydrusGlobals.client_controller.GetGUI().FlushOutPredicates( predicates )
        
        if len( predicates ) > 0:
            
            HydrusGlobals.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_predicates = predicates )
            
        
    
    def _ProcessMenuPredicateEvent( self, command ):
        
        pass
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command in ( 'copy_terms', 'copy_sub_terms', 'copy_all_tags', 'copy_all_tags_with_counts' ):
                
                if command in ( 'copy_terms', 'copy_sub_terms' ):
                    
                    texts = []
                    
                    for term in self._selected_terms:
                        
                        if isinstance( term, ClientSearch.Predicate ):
                            
                            text = term.GetUnicode( with_count = False )
                            
                        else:
                            
                            text = HydrusData.ToUnicode( term )
                            
                        
                        if command == 'copy_sub_terms':
                            
                            ( namespace_gumpf, text ) = HydrusTags.SplitTag( text )
                            
                        
                        texts.append( text )
                        
                    
                    texts.sort()
                    
                    text = os.linesep.join( texts )
                    
                elif command == 'copy_all_tags':
                    
                    text = os.linesep.join( self._GetAllTagsForClipboard( with_counts = False ) )
                    
                elif command == 'copy_all_tags_with_counts':
                    
                    text = os.linesep.join( self._GetAllTagsForClipboard( with_counts = True ) )
                    
                
                HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
                
            elif command in ( 'add_include_predicates', 'remove_include_predicates', 'add_exclude_predicates', 'remove_exclude_predicates' ):
                
                self._ProcessMenuPredicateEvent( command )
                
            elif command == 'new_search_page':
                
                self._NewSearchPage()
                
            elif command in ( 'censorship', 'parent', 'sibling' ):
                
                import ClientGUIDialogsManage
                
                if command == 'censorship':
                    
                    ( tag, ) = self._selected_terms
                    
                    with ClientGUIDialogsManage.DialogManageTagCensorship( self, tag ) as dlg: dlg.ShowModal()
                    
                elif command == 'parent':
                    
                    with ClientGUIDialogsManage.DialogManageTagParents( self, self._selected_terms ) as dlg: dlg.ShowModal()
                    
                elif command == 'sibling':
                    
                    with ClientGUIDialogsManage.DialogManageTagSiblings( self, self._selected_terms ) as dlg: dlg.ShowModal()
                    
                
            else:
                
                event.Skip()
                
                return # this is about select_up and select_down
                
            
        
    
    def EventMouseMiddleClick( self, event ):
        
        self._HandleClick( event )
        
        if self.can_spawn_new_windows:
            
            self._NewSearchPage()
            
        
    
    def EventMouseRightClick( self, event ):
        
        self._HandleClick( event )
        
        if len( self._ordered_strings ) > 0:
            
            menu = wx.Menu()
            
            if len( self._selected_terms ) > 0:
                
                if len( self._selected_terms ) == 1:
                    
                    ( term, ) = self._selected_terms
                    
                    if isinstance( term, ClientSearch.Predicate ):
                        
                        if term.GetType() == HC.PREDICATE_TYPE_TAG:
                            
                            selection_string = '"' + term.GetValue() + '"'
                            
                        else:
                            
                            selection_string = '"' + term.GetUnicode( with_count = False ) + '"'
                            
                        
                    else:
                        
                        selection_string = '"' + HydrusData.ToUnicode( term ) + '"'
                        
                    
                else:
                    
                    selection_string = 'selected'
                    
                
                if self._predicates_callable is not None:
                    
                    current_predicates = self._predicates_callable()
                    
                    ( include_predicates, exclude_predicates ) = self._GetSelectedIncludeExcludePredicates()
                    
                    if current_predicates is not None:
                        
                        if True in ( include_predicate in current_predicates for include_predicate in include_predicates ):
                            
                            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'remove_include_predicates' ), 'discard ' + selection_string + ' from current search' )
                            
                        
                        if True in ( include_predicate not in current_predicates for include_predicate in include_predicates ):
                            
                            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'add_include_predicates' ), 'require ' + selection_string + ' for current search' )
                            
                        
                        if True in ( exclude_predicate in current_predicates for exclude_predicate in exclude_predicates ):
                            
                            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'remove_exclude_predicates' ), 'permit ' + selection_string + ' for current search' )
                            
                        
                        if True in ( exclude_predicate not in current_predicates for exclude_predicate in exclude_predicates ):
                            
                            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'add_exclude_predicates' ), 'exclude ' + selection_string + ' from current search' )
                            
                        
                    
                    if menu.GetMenuItemCount() > 0:
                        
                        menu.AppendSeparator()
                        
                    
                
                if self.can_spawn_new_windows:
                    
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'new_search_page' ), 'open a new search page for ' + selection_string )
                    
                
                if menu.GetMenuItemCount() > 0:
                    
                    menu.AppendSeparator()
                    
                
                menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_terms' ), 'copy ' + selection_string )
                
                if len( self._selected_terms ) == 1:
                    
                    ( namespace, subtag ) = HydrusTags.SplitTag( selection_string )
                    
                    if namespace != '':
                        
                        sub_selection_string = '"' + subtag
                        
                        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_sub_terms' ), 'copy ' + sub_selection_string )
                        
                    
                else:
                    
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_sub_terms' ), 'copy selected subtags' )
                    
                
            
            if len( self._ordered_strings ) > len( self._selected_terms ):
                
                if menu.GetMenuItemCount() > 0:
                    
                    menu.AppendSeparator()
                    
                
                menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_all_tags' ), 'copy all tags' )
                if self.has_counts: menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_all_tags_with_counts' ), 'copy all tags with counts' )
                
            
            if self.can_spawn_new_windows and len( self._selected_terms ) > 0:
                
                term_types = [ type( term ) for term in self._selected_terms ]
                
                if str in term_types or unicode in term_types:
                    
                    if menu.GetMenuItemCount() > 0:
                        
                        menu.AppendSeparator()
                        
                    
                    if len( self._selected_terms ) == 1:
                        
                        ( tag, ) = self._selected_terms
                        
                        text = tag
                        
                    else:
                        
                        text = 'selection'
                        
                    
                    if len( self._selected_terms ) == 1:
                        
                        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'censorship' ), 'censor ' + text )
                        
                    
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'parent' ), 'add parents to ' + text )
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'sibling' ), 'add siblings to ' + text )
                    
                
            
            HydrusGlobals.client_controller.PopupMenu( self, menu )
            
        
        event.Skip()
        
    
    def GetSelectedTags( self ):
        
        return self._selected_terms
        
    
    def SiblingsHaveChanged( self ):
        
        pass
        
    
class ListBoxTagsAutocompleteDropdown( ListBoxTags ):
    
    has_counts = True
    
    def __init__( self, parent, service_key, callable, **kwargs ):
        
        ListBoxTags.__init__( self, parent, **kwargs )
        
        self._service_key = service_key
        self._callable = callable
        
        self._predicates = {}
        
    
    def _Activate( self ):
        
        predicates = [ term for term in self._selected_terms if term.GetType() != HC.PREDICATE_TYPE_PARENT ]
        
        predicates = HydrusGlobals.client_controller.GetGUI().FlushOutPredicates( predicates )
        
        if len( predicates ) > 0:
            
            self._callable( predicates )
            
        
    
    def _GetWithParentIndices( self, index ):
        
        indices = [ index ]
        
        index += 1
        
        while index < len( self._ordered_strings ):
            
            term = self._strings_to_terms[ self._ordered_strings[ index ] ]
            
            if term.GetType() == HC.PREDICATE_TYPE_PARENT:
                
                indices.append( index )
                
            else:
                
                break
                
            
            index += 1
            
        
        return indices
        
    
    def _Deselect( self, index ):
        
        to_deselect = self._GetWithParentIndices( index )
        
        for index in to_deselect:
            
            ListBoxTags._Deselect( self, index )
            
        
    
    def _GetAllTagsForClipboard( self, with_counts = False ):
        
        return [ self._strings_to_terms[ s ].GetUnicode( with_counts ) for s in self._ordered_strings ]
        
    
    def _GetTagString( self, predicate ):
        
        raise NotImplementedError()
        
    
    def _Hit( self, shift, ctrl, hit_index ):
        
        if hit_index is not None:
            
            if hit_index == -1 or hit_index > len( self._ordered_strings ):
                
                hit_index = len( self._ordered_strings ) - 1
                
            elif hit_index == len( self._ordered_strings ) or hit_index < -1:
                
                hit_index = 0
                
            
            # this realigns the hit index in the up direction
            
            hit_term = self._strings_to_terms[ self._ordered_strings[ hit_index ] ]
            
            while hit_term.GetType() == HC.PREDICATE_TYPE_PARENT:
                
                hit_index -= 1
                
                hit_term = self._strings_to_terms[ self._ordered_strings[ hit_index ] ]
                
            
        
        ListBoxTags._Hit( self, shift, ctrl, hit_index )
        
    
    def _Select( self, index ):
        
        to_select = self._GetWithParentIndices( index )
        
        for index in to_select:
            
            ListBoxTags._Select( self, index )
            
        
    
    def EventKeyDown( self, event ):
        
        # this realigns the hit index in the down direction
        
        key_code = event.GetKeyCode()
        
        hit_index = None
        
        if len( self._ordered_strings ) > 0:
            
            if key_code in ( wx.WXK_END, wx.WXK_NUMPAD_END ):
                
                hit_index = len( self._ordered_strings ) - 1
                
            elif self._last_hit_index is not None:
                
                if key_code in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ):
                    
                    hit_index = self._last_hit_index + 1
                    
                elif key_code in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN ):
                    
                    hit_index = min( len( self._ordered_strings ) - 1, self._last_hit_index + self._num_rows_per_page )
                    
                
            
        
        if hit_index is None:
            
            ListBoxTags.EventKeyDown( self, event )
            
        else:
            
            if hit_index >= len( self._ordered_strings ):
                
                hit_index = 0
                
            
            hit_term = self._strings_to_terms[ self._ordered_strings[ hit_index ] ]
            
            while hit_term.GetType() == HC.PREDICATE_TYPE_PARENT:
                
                hit_index += 1
                
                if hit_index >= len( self._ordered_strings ):
                    
                    hit_index = 0
                    
                
                hit_term = self._strings_to_terms[ self._ordered_strings[ hit_index ] ]
                
            
            
            shift = event.ShiftDown()
            ctrl = event.CmdDown()
            
            self._Hit( shift, ctrl, hit_index )
            
        
        
    
    def SetPredicates( self, predicates ):
        
        # need to do a clever compare, since normal predicate compare doesn't take count into account
        
        they_are_the_same = True
        
        if len( predicates ) == len( self._predicates ):
            
            for index in range( len( predicates ) ):
                
                p_1 = predicates[ index ]
                p_2 = self._predicates[ index ]
                
                if p_1 != p_2 or p_1.GetCount() != p_2.GetCount():
                    
                    they_are_the_same = False
                    
                    break
                    
                
            
        else:
            
            they_are_the_same = False
            
        
        if not they_are_the_same:
            
            # important to make own copy, as same object originals can be altered (e.g. set non-inclusive) in cache, and we need to notice that change just above
            self._predicates = [ predicate.GetCopy() for predicate in predicates ]
            
            self._ordered_strings = []
            self._strings_to_terms = {}
            
            for predicate in predicates:
                
                tag_string = self._GetTagString( predicate )
                
                self._ordered_strings.append( tag_string )
                self._strings_to_terms[ tag_string ] = predicate
                
            
            self._TextsHaveChanged()
            
            if len( predicates ) > 0:
                
                self._Hit( False, False, None )
                self._Hit( False, False, 0 )
                
            
        
    
    def SetTagService( self, service_key ):
        
        self._service_key = service_key
        
    
class ListBoxTagsAutocompleteDropdownRead( ListBoxTagsAutocompleteDropdown ):
    
    def _GetTagString( self, predicate ):
        
        return predicate.GetUnicode()
        
    
class ListBoxTagsAutocompleteDropdownWrite( ListBoxTagsAutocompleteDropdown ):
    
    def _GetTagString( self, predicate ):
        
        return predicate.GetUnicode( sibling_service_key = self._service_key )
        
    
class ListBoxTagsCensorship( ListBoxTags ):
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._selected_terms )
            
            for tag in tags:
                
                self._RemoveTag( tag )
                
            
            self._TextsHaveChanged()
            
        
    
    def _AddTag( self, tag ):
        
        tag_string = self._GetTagString( tag )
        
        if tag_string not in self._strings_to_terms:
            
            self._ordered_strings.append( tag_string )
            self._strings_to_terms[ tag_string ] = tag
            
        
    
    def _GetTagString( self, tag ):
        
        if tag == '': return 'unnamespaced'
        elif tag == ':': return 'namespaced'
        else: return HydrusTags.RenderTag( tag )
        
    
    def _RemoveTag( self, tag ):
        
        tag_string = self._GetTagString( tag )
        
        if tag_string in self._strings_to_terms:
            
            tag_string = self._GetTagString( tag )
            
            self._ordered_strings.remove( tag_string )
            
            del self._strings_to_terms[ tag_string ]
            
        
    
    def AddTags( self, tags ):
        
        for tag in tags:
            
            self._AddTag( tag )
            
        
        self._TextsHaveChanged()
        
    
    def EnterTags( self, tags ):
        
        for tag in tags:
            
            tag_string = self._GetTagString( tag )
            
            if tag_string in self._strings_to_terms:
                
                self._RemoveTag( tag )
                
            else:
                
                self._AddTag( tag )
                
            
        
        self._TextsHaveChanged()
        
    
    def _RemoveTags( self, tags ):
        
        for tag in tags:
            
            self._RemoveTag( tag )
            
        
        self._TextsHaveChanged()
        
    
class ListBoxTagsColourOptions( ListBoxTags ):
    
    can_spawn_new_windows = False
    
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
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            self._RemoveNamespaces( self._selected_terms )
            
        
    
    def _GetNamespaceColours( self ): return self._namespace_colours
    
    def _RemoveNamespaces( self, namespaces ):
        
        for namespace in namespaces:
            
            if namespace is not None and namespace != '':
                
                namespace_string = namespace + ':tag'
                
                self._ordered_strings.remove( namespace_string )
                
                del self._strings_to_terms[ namespace_string ]
                
                del self._namespace_colours[ namespace ]
                
            
        
        self._TextsHaveChanged()
        
    
    def SetNamespaceColour( self, namespace, colour ):
        
        if namespace not in self._namespace_colours:
            
            namespace_string = namespace + ':tag'
            
            self._ordered_strings.append( namespace_string )
            self._strings_to_terms[ namespace_string ] = namespace
            
            self._ordered_strings.sort()
            
        
        self._namespace_colours[ namespace ] = colour.Get()
        
        self._TextsHaveChanged()
        
    
    def GetNamespaceColours( self ): return self._namespace_colours
    
    def GetSelectedNamespaceColours( self ):
        
        results = []
        
        for namespace in self._selected_terms:
            
            ( r, g, b ) = self._namespace_colours[ namespace ]
            
            colour = wx.Colour( r, g, b )
            
            results.append( ( namespace, colour ) )
            
        
        return results
        
    
class ListBoxTagsStrings( ListBoxTags ):
    
    def __init__( self, parent, service_key = None, show_sibling_text = True, sort_tags = True ):
        
        ListBoxTags.__init__( self, parent )
        
        if service_key is not None:
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        self._service_key = service_key
        self._show_sibling_text = show_sibling_text
        self._sort_tags = sort_tags
        self._tags = []
        
    
    def _RecalcTags( self ):
        
        self._strings_to_terms = {}
        
        self._ordered_strings = []
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        for tag in self._tags:
            
            tag_string = HydrusTags.RenderTag( tag )
            
            if self._show_sibling_text:
                
                sibling = siblings_manager.GetSibling( self._service_key, tag )
                
                if sibling is not None:
                    
                    tag_string += ' (will display as ' + HydrusTags.RenderTag( sibling ) + ')'
                    
                
            
            self._ordered_strings.append( tag_string )
            
            self._strings_to_terms[ tag_string ] = tag
            
        
        if self._sort_tags:
            
            self._ordered_strings.sort()
            
        
        self._TextsHaveChanged()
        
    
    def GetTags( self ):
        
        return set( self._tags )
        
    
    def SetTags( self, tags ):
        
        self._tags = list( tags )
        
        self._RecalcTags()
        
    
    def SiblingsHaveChanged( self ):
        
        self._RecalcTags()
        
    
class ListBoxTagsStringsAddRemove( ListBoxTagsStrings ):
    
    def __init__( self, parent, service_key = None, removed_callable = None, show_sibling_text = True ):
        
        ListBoxTagsStrings.__init__( self, parent, service_key = service_key, show_sibling_text = show_sibling_text )
        
        self._removed_callable = removed_callable
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._selected_terms )
            
            self._RemoveTags( tags )
            
        
    
    def _RemoveTags( self, tags ):
        
        for tag in tags:
            
            if tag in self._tags:
                
                self._tags.remove( tag )
                
            
        
        self._RecalcTags()
        
        if self._removed_callable is not None:
            
            self._removed_callable( tags )
            
        
    
    def AddTags( self, tags ):
        
        for tag in tags:
            
            if tag not in self._tags:
                
                self._tags.append( tag )
                
            
        
        self._RecalcTags()
        
    
    def Clear( self ):
        
        self._tags = []
        
        self._RecalcTags()
        
    
    def EnterTags( self, tags ):
        
        removed = set()
        
        for tag in tags:
            
            if tag in self._tags:
                
                self._tags.remove( tag )
                
                removed.add( tag )
                
            else:
                
                self._tags.append( tag )
                
            
        
        self._RecalcTags()
        
        if len( removed ) > 0 and self._removed_callable is not None:
            
            self._removed_callable( removed )
            
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in CC.DELETE_KEYS:
            
            self._Activate()
            
        else:
            
            event.Skip()
            
        
    
    def RemoveTags( self, tags ):
        
        self._RemoveTags( tags )
        
    
class ListBoxTagsPredicates( ListBoxTags ):
    
    delete_key_activates = True
    has_counts = False
    
    def __init__( self, parent, page_key, initial_predicates = None ):
        
        if initial_predicates is None: initial_predicates = []
        
        ListBoxTags.__init__( self, parent, min_height = 100 )
        
        self._page_key = page_key
        self._predicates_callable = self.GetPredicates
        
        if len( initial_predicates ) > 0:
            
            for predicate in initial_predicates:
                
                predicate_string = predicate.GetUnicode()
                
                self._ordered_strings.append( predicate_string )
                self._strings_to_terms[ predicate_string ] = predicate
                
            
            self._TextsHaveChanged()
            
        
        HydrusGlobals.client_controller.sub( self, 'EnterPredicates', 'enter_predicates' )
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            self._EnterPredicates( set( self._selected_terms ) )
            
        
    
    def _EnterPredicates( self, predicates, permit_add = True, permit_remove = True ):
        
        if len( predicates ) == 0:
            
            return
            
        
        predicates_to_be_added = set()
        predicates_to_be_removed = set()
        
        for predicate in predicates:
            
            predicate = predicate.GetCountlessCopy()
            
            if self._HasPredicate( predicate ):
                
                if permit_remove:
                    
                    predicates_to_be_removed.add( predicate )
                    
                
            else:
                
                if permit_add:
                    
                    predicates_to_be_added.add( predicate )
                    
                    inverse_predicate = predicate.GetInverseCopy()
                    
                    if self._HasPredicate( inverse_predicate ):
                        
                        predicates_to_be_removed.add( inverse_predicate )
                        
                    
                
            
        
        for predicate in predicates_to_be_added:
            
            predicate_string = predicate.GetUnicode()
            
            self._ordered_strings.append( predicate_string )
            self._strings_to_terms[ predicate_string ] = predicate
            
        
        for predicate in predicates_to_be_removed:
            
            for ( s, existing_predicate ) in self._strings_to_terms.items():
                
                if existing_predicate == predicate:
                    
                    self._ordered_strings.remove( s )
                    del self._strings_to_terms[ s ]
                    
                    break
                    
                
            
        
        self._ordered_strings.sort()
        
        self._TextsHaveChanged()
        
        HydrusGlobals.client_controller.pub( 'refresh_query', self._page_key )
        
    
    def _GetAllTagsForClipboard( self, with_counts = False ):
        
        return [ self._strings_to_terms[ s ].GetUnicode( with_counts ) for s in self._ordered_strings ]
        
    
    def _HasPredicate( self, predicate ): return predicate in self._strings_to_terms.values()
    
    def _ProcessMenuPredicateEvent( self, command ):
        
        ( include_predicates, exclude_predicates ) = self._GetSelectedIncludeExcludePredicates()
        
        if command == 'add_include_predicates':
            
            self._EnterPredicates( include_predicates, permit_remove = False )
            
        elif command == 'remove_include_predicates':
            
            self._EnterPredicates( include_predicates, permit_add = False )
            
        elif command == 'add_exclude_predicates':
            
            self._EnterPredicates( exclude_predicates, permit_remove = False )
            
        elif command == 'remove_exclude_predicates':
            
            self._EnterPredicates( exclude_predicates, permit_add = False )
            
        
    
    def EnterPredicates( self, page_key, predicates, permit_add = True, permit_remove = True ):
        
        if page_key == self._page_key:
            
            self._EnterPredicates( predicates, permit_add = permit_add, permit_remove = permit_remove )
            
        
    
    def GetPredicates( self ):
        
        return self._strings_to_terms.values()
        
    
class ListBoxTagsSelection( ListBoxTags ):
    
    has_counts = True
    
    def __init__( self, parent, include_counts = True, collapse_siblings = False ):
        
        ListBoxTags.__init__( self, parent, min_height = 200 )
        
        self._sort = HC.options[ 'default_tag_sort' ]
        
        if not include_counts and self._sort in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
            
            self._sort = CC.SORT_BY_LEXICOGRAPHIC_ASC
            
        
        self._last_media = set()
        
        self._tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
        
        self._include_counts = include_counts
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
        
        if with_counts:
            
            return self._ordered_strings
            
        else:
            
            return [ self._strings_to_terms[ s ] for s in self._ordered_strings ]
            
        
    
    def _GetTagString( self, tag ):
        
        tag_string = HydrusTags.RenderTag( tag )
        
        if self._include_counts:
            
            if self._show_current and tag in self._current_tags_to_count: tag_string += ' (' + HydrusData.ConvertIntToPrettyString( self._current_tags_to_count[ tag ] ) + ')'
            if self._show_pending and tag in self._pending_tags_to_count: tag_string += ' (+' + HydrusData.ConvertIntToPrettyString( self._pending_tags_to_count[ tag ] ) + ')'
            if self._show_petitioned and tag in self._petitioned_tags_to_count: tag_string += ' (-' + HydrusData.ConvertIntToPrettyString( self._petitioned_tags_to_count[ tag ] ) + ')'
            if self._show_deleted and tag in self._deleted_tags_to_count: tag_string += ' (X' + HydrusData.ConvertIntToPrettyString( self._deleted_tags_to_count[ tag ] ) + ')'
            
        else:
            
            if self._show_pending and tag in self._pending_tags_to_count: tag_string += ' (+)'
            if self._show_petitioned and tag in self._petitioned_tags_to_count: tag_string += ' (-)'
            if self._show_deleted and tag in self._deleted_tags_to_count: tag_string += ' (X)'
            
        
        if not self._collapse_siblings:
            
            siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
            
            sibling = siblings_manager.GetSibling( self._tag_service_key, tag )
            
            if sibling is not None:
                
                tag_string += ' (will display as ' + HydrusTags.RenderTag( sibling ) + ')'
                
            
        
        return tag_string
        
    
    def _RecalcStrings( self, limit_to_these_tags = None ):
        
        if limit_to_these_tags is None:
            
            all_tags = set()
            
            if self._show_current: all_tags.update( ( tag for ( tag, count ) in self._current_tags_to_count.items() if count > 0 ) )
            if self._show_deleted: all_tags.update( ( tag for ( tag, count ) in self._deleted_tags_to_count.items() if count > 0 ) )
            if self._show_pending: all_tags.update( ( tag for ( tag, count ) in self._pending_tags_to_count.items() if count > 0 ) )
            if self._show_petitioned: all_tags.update( ( tag for ( tag, count ) in self._petitioned_tags_to_count.items() if count > 0 ) )
            
            self._ordered_strings = []
            self._strings_to_terms = {}
            
            for tag in all_tags:
                
                tag_string = self._GetTagString( tag )
                
                self._ordered_strings.append( tag_string )
                self._strings_to_terms[ tag_string ] = tag
                
            
            self._SortTags()
            
        else:
            
            sort_needed = False
            
            terms_to_old_strings = { tag : tag_string for ( tag_string, tag ) in self._strings_to_terms.items() }
            
            for tag in limit_to_these_tags:
                
                tag_string = self._GetTagString( tag )
                
                do_insert = True
                
                if tag in terms_to_old_strings:
                    
                    old_tag_string = terms_to_old_strings[ tag ]
                    
                    if tag_string == old_tag_string:
                        
                        do_insert = False
                        
                    else:
                        
                        self._ordered_strings.remove( old_tag_string )
                        del self._strings_to_terms[ old_tag_string ]
                        
                    
                
                if do_insert:
                    
                    self._ordered_strings.append( tag_string )
                    self._strings_to_terms[ tag_string ] = tag
                    
                    sort_needed = True
                    
                
            
            if sort_needed:
                
                self._SortTags()
                
            
        
    
    def _SortTags( self ):
        
        if self._sort in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
            
            tags_to_count = collections.Counter()
            
            if self._show_current: tags_to_count.update( self._current_tags_to_count )
            if self._show_deleted: tags_to_count.update( self._deleted_tags_to_count )
            if self._show_pending: tags_to_count.update( self._pending_tags_to_count )
            if self._show_petitioned: tags_to_count.update( self._petitioned_tags_to_count )

            def key( unordered_string ):
                
                return tags_to_count[ self._strings_to_terms[ unordered_string ] ]
                
            
            # we do a plain sort here to establish a-z for equal values later
            # don't incorporate it into the key as a tuple because it is in the opposite direction to what we want
            if self._sort in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC ):
                
                self._ordered_strings.sort( reverse = True )
                
                reverse = False
                
            elif self._sort in ( CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
                
                self._ordered_strings.sort()
                
                reverse = True
                
            
            self._ordered_strings.sort( key = key, reverse = reverse )
            
            if self._sort in ( CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
                
                # python list sort is stable, so lets now sort again
                
                def secondary_key( unordered_string ):
                    
                    tag = self._strings_to_terms[ unordered_string ]
                    
                    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
                    
                    if namespace == '':
                        
                        namespace = '{' # '{' is above 'z' in ascii, so this works for most situations
                        
                    
                    return namespace
                    
                
                if self._sort == CC.SORT_BY_INCIDENCE_NAMESPACE_ASC:
                    
                    reverse = True
                    
                elif self._sort == CC.SORT_BY_INCIDENCE_NAMESPACE_DESC:
                    
                    reverse = False
                    
                
                self._ordered_strings.sort( key = secondary_key, reverse = reverse )
                
            
        else:
            
            ClientData.SortTagsList( self._ordered_strings, self._sort )
            
        
        self._TextsHaveChanged()
        
    
    def ChangeTagService( self, service_key ):
        
        self._tag_service_key = service_key
        
        self.SetTagsByMedia( self._last_media, force_reload = True )
        
    
    def SetSort( self, sort ):
        
        self._sort = sort
        
        self._SortTags()
        
    
    def SetShow( self, show_type, value ):
        
        if show_type == 'current': self._show_current = value
        elif show_type == 'deleted': self._show_deleted = value
        elif show_type == 'pending': self._show_pending = value
        elif show_type == 'petitioned': self._show_petitioned = value
        
        self._RecalcStrings()
        
    
    def IncrementTagsByMedia( self, media ):
        
        media = set( media )
        media = media.difference( self._last_media )
        
        ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( media, tag_service_key = self._tag_service_key, collapse_siblings = self._collapse_siblings )
        
        self._current_tags_to_count.update( current_tags_to_count )
        self._deleted_tags_to_count.update( deleted_tags_to_count )
        self._pending_tags_to_count.update( pending_tags_to_count )
        self._petitioned_tags_to_count.update( petitioned_tags_to_count )
        
        tags_changed = set()
        
        if self._show_current: tags_changed.update( current_tags_to_count.keys() )
        if self._show_deleted: tags_changed.update( deleted_tags_to_count.keys() )
        if self._show_pending: tags_changed.update( pending_tags_to_count.keys() )
        if self._show_petitioned: tags_changed.update( petitioned_tags_to_count.keys() )
        
        if len( tags_changed ) > 0:
            
            self._RecalcStrings( tags_changed )
            
        
        self._last_media.update( media )
        
    
    def SetTagsByMedia( self, media, force_reload = False ):
        
        media = set( media )
        
        if force_reload:
            
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( media, tag_service_key = self._tag_service_key, collapse_siblings = self._collapse_siblings )
            
            self._current_tags_to_count = current_tags_to_count
            self._deleted_tags_to_count = deleted_tags_to_count
            self._pending_tags_to_count = pending_tags_to_count
            self._petitioned_tags_to_count = petitioned_tags_to_count
            
            self._RecalcStrings()
            
        else:
            
            removees = self._last_media.difference( media )
            adds = media.difference( self._last_media )
            
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( removees, tag_service_key = self._tag_service_key, collapse_siblings = self._collapse_siblings )
            
            self._current_tags_to_count.subtract( current_tags_to_count )
            self._deleted_tags_to_count.subtract( deleted_tags_to_count )
            self._pending_tags_to_count.subtract( pending_tags_to_count )
            self._petitioned_tags_to_count.subtract( petitioned_tags_to_count )
            
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( adds, tag_service_key = self._tag_service_key, collapse_siblings = self._collapse_siblings )
            
            self._current_tags_to_count.update( current_tags_to_count )
            self._deleted_tags_to_count.update( deleted_tags_to_count )
            self._pending_tags_to_count.update( pending_tags_to_count )
            self._petitioned_tags_to_count.update( petitioned_tags_to_count )
            
            for counter in ( self._current_tags_to_count, self._deleted_tags_to_count, self._pending_tags_to_count, self._petitioned_tags_to_count ):
                
                tags = counter.keys()
                
                for tag in tags:
                    
                    if counter[ tag ] == 0: del counter[ tag ]
                    
                
            
            if len( removees ) == 0:
                
                tags_changed = set()
                
                if self._show_current: tags_changed.update( current_tags_to_count.keys() )
                if self._show_deleted: tags_changed.update( deleted_tags_to_count.keys() )
                if self._show_pending: tags_changed.update( pending_tags_to_count.keys() )
                if self._show_petitioned: tags_changed.update( petitioned_tags_to_count.keys() )
                
                if len( tags_changed ) > 0:
                    
                    self._RecalcStrings( tags_changed )
                    
                
            else:
                
                self._RecalcStrings()
                
            
        
        self._last_media = media
        
    
    def SiblingsHaveChanged( self ):
        
        self.SetTagsByMedia( self._last_media, force_reload = True )
        
    
class ListBoxTagsSelectionHoverFrame( ListBoxTagsSelection ):
    
    def __init__( self, parent, canvas_key ):
        
        ListBoxTagsSelection.__init__( self, parent, include_counts = False, collapse_siblings = True )
        
        self._canvas_key = canvas_key
        
    
    def _Activate( self ):
        
        # if the hover window has focus when the manage tags spawns, then when it disappears, the main gui gets put as the next heir
        # so when manage tags closes, main gui pops to the front!
        
        #self.GetParent().GiveParentFocus()
        
        HydrusGlobals.client_controller.pub( 'canvas_manage_tags', self._canvas_key )
        
    
class ListBoxTagsSelectionManagementPanel( ListBoxTagsSelection ):
    
    def __init__( self, parent, page_key, predicates_callable = None ):
        
        ListBoxTagsSelection.__init__( self, parent, include_counts = True, collapse_siblings = True )
        
        self._page_key = page_key
        self._predicates_callable = predicates_callable
        
        HydrusGlobals.client_controller.sub( self, 'IncrementTagsByMediaPubsub', 'increment_tags_selection' )
        HydrusGlobals.client_controller.sub( self, 'SetTagsByMediaPubsub', 'new_tags_selection' )
        HydrusGlobals.client_controller.sub( self, 'ChangeTagServicePubsub', 'change_tag_service' )
        
    
    def _Activate( self ):
        
        predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, term ) for term in self._selected_terms ]
        
        if len( predicates ) > 0:
            
            HydrusGlobals.client_controller.pub( 'enter_predicates', self._page_key, predicates )
            
        
    
    def _ProcessMenuPredicateEvent( self, command ):
        
        ( include_predicates, exclude_predicates ) = self._GetSelectedIncludeExcludePredicates()
        
        if command == 'add_include_predicates':
            
            HydrusGlobals.client_controller.pub( 'enter_predicates', self._page_key, include_predicates, permit_remove = False )
            
        elif command == 'remove_include_predicates':
            
            HydrusGlobals.client_controller.pub( 'enter_predicates', self._page_key, include_predicates, permit_add = False )
            
        elif command == 'add_exclude_predicates':
            
            HydrusGlobals.client_controller.pub( 'enter_predicates', self._page_key, exclude_predicates, permit_remove = False )
            
        elif command == 'remove_exclude_predicates':
            
            HydrusGlobals.client_controller.pub( 'enter_predicates', self._page_key, exclude_predicates, permit_add = False )
            
        
    
    def ChangeTagServicePubsub( self, page_key, service_key ):
        
        if page_key == self._page_key:
            
            self.ChangeTagService( service_key )
            
        
    
    def IncrementTagsByMediaPubsub( self, page_key, media ):
        
        if page_key == self._page_key:
            
            self.IncrementTagsByMedia( media )
            
        
    
    def SetTagsByMediaPubsub( self, page_key, media, force_reload = False ):
        
        if page_key == self._page_key:
            
            self.SetTagsByMedia( media, force_reload = force_reload )
            
        
    
class ListBoxTagsSelectionTagsDialog( ListBoxTagsSelection ):
    
    delete_key_activates = True
    
    def __init__( self, parent, callable ):
        
        ListBoxTagsSelection.__init__( self, parent, include_counts = True, collapse_siblings = False )
        
        self._callable = callable
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            self._callable( self._selected_terms )
            
        
    
