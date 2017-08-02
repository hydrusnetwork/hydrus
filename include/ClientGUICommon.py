import ClientCaches
import ClientData
import ClientConstants as CC
import ClientGUIMenus
import ClientGUITopLevelWindows
import ClientRatings
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import os
import sys
import threading
import time
import traceback
import wx
import wx.combo
import wx.richtext
import wx.lib.newevent

ID_TIMER_ANIMATED = wx.NewId()
ID_TIMER_SLIDESHOW = wx.NewId()
ID_TIMER_MEDIA_INFO_DISPLAY = wx.NewId()

def WindowOrAnyTLPChildHasFocus( window ):
    
    focus = wx.Window.FindFocus()
    
    while focus is not None:
        
        if focus == window:
            
            return True
            
        
        focus = focus.GetParent()
        
    
    return False
    
def WindowOrSameTLPChildHasFocus( window ):
    
    focus = wx.Window.FindFocus()
    
    while focus is not None:
        
        if focus == window:
            
            return True
            
        
        if isinstance( focus, wx.TopLevelWindow ):
            
            return False
            
        
        focus = focus.GetParent()
        
    
    return False
    
def GetFocusTLP():
    
    focus = wx.Window.FindFocus()
    
    return GetTLP( focus )
    
def GetTLP( window ):
    
    if window is None:
        
        return None
        
    elif isinstance( window, wx.TopLevelWindow ):
        
        return window
        
    else:
        
        return window.GetTopLevelParent()
        
    
def TLPHasFocus( window ):
    
    focus_tlp = GetFocusTLP()
    
    window_tlp = GetTLP( window )
    
    return window_tlp == focus_tlp
    
def WindowHasFocus( window ):
    
    focus = wx.Window.FindFocus()
    
    if focus is None:
        
        return False
        
    
    return window == focus
    
def IsWXAncestor( child, ancestor ):
    
    parent = child
    
    while not isinstance( parent, wx.TopLevelWindow ):
        
        if parent == ancestor:
            
            return True
            
        
        parent = parent.GetParent()
        
    
    return False
    
def WrapInGrid( parent, rows, expand_text = False ):
    
    gridbox = wx.FlexGridSizer( 0, 2 )
    
    if expand_text:
        
        gridbox.AddGrowableCol( 0, 1 )
        
        text_flags = CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY # Trying to expand both ways nixes the center. This seems to work right.
        control_flags = CC.FLAGS_VCENTER
        sizer_flags = CC.FLAGS_SIZER_VCENTER
        
    else:
        
        gridbox.AddGrowableCol( 1, 1 )
        
        text_flags = CC.FLAGS_VCENTER
        control_flags = CC.FLAGS_EXPAND_BOTH_WAYS
        sizer_flags = CC.FLAGS_EXPAND_SIZER_BOTH_WAYS
        
    
    for ( text, control ) in rows:
        
        if isinstance( control, wx.Sizer ):
            
            cflags = sizer_flags
            
        else:
            
            cflags = control_flags
            
        
        st = BetterStaticText( parent, text )
        
        gridbox.AddF( st, text_flags )
        gridbox.AddF( control, cflags )
        
    
    return gridbox
    
def WrapInText( control, parent, text ):
    
    hbox = wx.BoxSizer( wx.HORIZONTAL )
    
    st = BetterStaticText( parent, text )
    
    hbox.AddF( st, CC.FLAGS_VCENTER )
    hbox.AddF( control, CC.FLAGS_EXPAND_BOTH_WAYS )
    
    return hbox
    
class AnimatedStaticTextTimestamp( wx.StaticText ):
    
    def __init__( self, parent, prefix, rendering_function, timestamp, suffix ):
        
        self._prefix = prefix
        self._rendering_function = rendering_function
        self._timestamp = timestamp
        self._suffix = suffix
        
        self._last_tick = HydrusData.GetNow()
        
        wx.StaticText.__init__( self, parent, label = self._prefix + self._rendering_function( self._timestamp ) + self._suffix )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventAnimated, id = ID_TIMER_ANIMATED )
        
        self._timer_animated = wx.Timer( self, ID_TIMER_ANIMATED )
        self._timer_animated.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    def TIMEREventAnimated( self ):
        
        try:
            
            update = False
            
            now = HydrusData.GetNow()
            
            difference = abs( now - self._timestamp )
            
            if difference < 3600: update = True
            elif difference < 3600 * 24 and now - self._last_tick > 60: update = True
            elif now - self._last_tick > 3600: update = True
            
            if update:
                
                self.SetLabelText( self._prefix + self._rendering_function( self._timestamp ) + self._suffix )
                
                wx.PostEvent( self.GetEventHandler(), wx.SizeEvent() )
                
            
        except wx.PyDeadObjectError:
            
            self._timer_animated.Stop()
            
        except:
            
            self._timer_animated.Stop()
            
            raise
            
        
    
class BetterBitmapButton( wx.BitmapButton ):
    
    def __init__( self, parent, bitmap, func, *args, **kwargs ):
        
        wx.BitmapButton.__init__( self, parent, bitmap = bitmap )
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        self._func( *self._args,  **self._kwargs )
        
    
class BetterButton( wx.Button ):
    
    def __init__( self, parent, label, func, *args, **kwargs ):
        
        wx.Button.__init__( self, parent, style = wx.BU_EXACTFIT )
        
        self.SetLabelText( label )
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        self._func( *self._args,  **self._kwargs )
        
    
class BetterCheckListBox( wx.CheckListBox ):
    
    def GetChecked( self ):
        
        result = [ self.GetClientData( index ) for index in wx.CheckListBox.GetChecked( self ) ]
        
        return result
        
    
class BetterChoice( wx.Choice ):
    
    def GetChoice( self ):
        
        selection = self.GetSelection()
        
        if selection != wx.NOT_FOUND: return self.GetClientData( selection )
        elif self.GetCount() > 0: return self.GetClientData( 0 )
        else: return None
        
    
    def SelectClientData( self, client_data ):
        
        for i in range( self.GetCount() ):
            
            if client_data == self.GetClientData( i ):
                
                self.Select( i )
                
                return
                
            
        
        if self.GetCount() > 0:
            
            self.Select( 0 )
            
        
    
class BetterRadioBox( wx.RadioBox ):
    
    def __init__( self, *args, **kwargs ):
        
        self._indices_to_data = { i : data for ( i, ( s, data ) ) in enumerate( kwargs[ 'choices' ] ) }
        
        kwargs[ 'choices' ] = [ s for ( s, data ) in kwargs[ 'choices' ] ]
        
        wx.RadioBox.__init__( self, *args, **kwargs )
        
    
    def GetChoice( self ):
        
        index = self.GetSelection()
        
        return self._indices_to_data[ index ]
        
    
class BetterStaticText( wx.StaticText ):
    
    def __init__( self, parent, label = None, **kwargs ):
        
        wx.StaticText.__init__( self, parent, **kwargs )
        
        if label is not None:
            
            # to escape mnemonic '&' swallowing
            self.SetLabelText( label )
            
        
        # at some point, rewrite this to be a control that'll produce a custom geteffectiveminsize and use wx.lib.wordwrap to dc draw the text
        # st.Wrap is a pain to deal with here, seems to sometimes/always not be able to increase after an initial non-zero call
        
    
    def SetLabelText( self, text ):
        
        if text != self.GetLabelText():
            
            wx.StaticText.SetLabelText( self, text )
            
        
    
class BufferedWindow( wx.Window ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Window.__init__( self, *args, **kwargs )
        
        if 'size' in kwargs:
            
            ( x, y ) = kwargs[ 'size' ]
            
            self._canvas_bmp = wx.EmptyBitmap( x, y, 24 )
            
        else:
            
            self._canvas_bmp = wx.EmptyBitmap( 20, 20, 24 )
            
        
        self._dirty = True
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _Draw( self, dc ):
        
        raise NotImplementedError()
        
    
    def EventEraseBackground( self, event ): pass
    
    def EventPaint( self, event ):
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if self._dirty:
            
            self._Draw( dc )
            
        
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
        
        if my_width != current_bmp_width or my_height != current_bmp_height:
            
            self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
            
            self._dirty = True
            
        
        self.Refresh()
        
    
class BufferedWindowIcon( BufferedWindow ):
    
    def __init__( self, parent, bmp ):
        
        BufferedWindow.__init__( self, parent, size = bmp.GetSize() )
        
        self._bmp = bmp
        
    
    def _Draw( self, dc ):
        
        background_colour = self.GetParent().GetBackgroundColour()
        
        dc.SetBackground( wx.Brush( background_colour ) )
        
        dc.Clear()
        
        dc.DrawBitmap( self._bmp, 0, 0 )
        
        self._dirty = False
        
    
class CheckboxCollect( wx.combo.ComboCtrl ):
    
    def __init__( self, parent, page_key = None ):
        
        wx.combo.ComboCtrl.__init__( self, parent, style = wx.CB_READONLY )
        
        self._page_key = page_key
        
        popup = self._Popup()
        
        #self.UseAltPopupWindow( True )
        
        self.SetPopupControl( popup )
        
    
    def GetChoice( self ):
        
        return self._collect_by
        
    
    def SetCollectTypes( self, collect_by, description ):
        
        self._collect_by = collect_by
        
        self.SetValue( description )
        
        HG.client_controller.pub( 'collect_media', self._page_key, self._collect_by )
        
    
    class _Popup( wx.combo.ComboPopup ):
        
        def __init__( self ):
            
            wx.combo.ComboPopup.__init__( self )
            
        
        def Create( self, parent ):
            
            self._control = self._Control( parent, self.GetCombo() )
            
            return True
            
        
        def GetAdjustedSize( self, preferred_width, preferred_height, max_height ):
            
            return( ( preferred_width, -1 ) )
            
        
        def GetControl( self ):
            
            return self._control
            
        
        class _Control( wx.CheckListBox ):
            
            def __init__( self, parent, special_parent ):
                
                text_and_data_tuples = set()
                
                sort_by = HC.options[ 'sort_by' ]
                
                for ( sort_by_type, namespaces ) in sort_by:
                    
                    text_and_data_tuples.update( namespaces )
                    
                
                text_and_data_tuples = list( [ ( namespace, ( 'namespace', namespace ) ) for namespace in text_and_data_tuples ] )
                text_and_data_tuples.sort()
                
                ratings_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
                
                for ratings_service in ratings_services:
                    
                    text_and_data_tuples.append( ( ratings_service.GetName(), ( 'rating', ratings_service.GetServiceKey() ) ) )
                    
                
                texts = [ text for ( text, data ) in text_and_data_tuples ] # we do this so it sizes its height properly on init
                
                wx.CheckListBox.__init__( self, parent, choices = texts )
                
                self.Clear()
                
                for ( text, data ) in text_and_data_tuples:
                    
                    self.Append( text, data )
                    
                
                self._special_parent = special_parent
                
                default = HC.options[ 'default_collect' ]
                
                self.SetValue( default )
                
                self.Bind( wx.EVT_CHECKLISTBOX, self.EventChanged )
                
                self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
                
            
            def _BroadcastCollect( self ):
                
                ( collect_by, description ) = self._GetValues()
                
                self._special_parent.SetCollectTypes( collect_by, description )
                
            
            def _GetValues( self ):
                
                collect_by = []
                
                for index in self.GetChecked():
                    
                    collect_by.append( self.GetClientData( index ) )
                    
                
                collect_by_strings = self.GetCheckedStrings()
                
                if len( collect_by ) > 0:
                    
                    description = 'collect by ' + '-'.join( collect_by_strings )
                    
                else:
                    
                    description = 'no collections'
                    
                
                return ( collect_by, description )
                
            
            # as inspired by http://trac.wxwidgets.org/attachment/ticket/14413/test_clb_workaround.py
            # what a clusterfuck
            
            def EventLeftDown( self, event ):
                
                index = self.HitTest( event.GetPosition() )
                
                if index != wx.NOT_FOUND:
                    
                    self.Check( index, not self.IsChecked( index ) )
                    
                    self.EventChanged( event )
                    
                
                event.Skip()
                
            
            def EventChanged( self, event ):
                
                self._BroadcastCollect()
                
            
            def SetValue( self, collect_by ):
                
                # an old possible value, now collapsed to []
                if collect_by is None:
                    
                    collect_by = []
                    
                
                desired_collect_by_rows = set( collect_by )
                
                indices_to_check = []
                
                for index in range( self.GetCount() ):
                    
                    if self.GetClientData( index ) in desired_collect_by_rows:
                        
                        indices_to_check.append( index )
                        
                    
                
                self.SetChecked( indices_to_check )
                
                self._BroadcastCollect()
                
            
        
    
class ChoiceSort( BetterChoice ):
    
    def __init__( self, parent, page_key = None, add_namespaces_and_ratings = True ):
        
        BetterChoice.__init__( self, parent )
        
        self._page_key = page_key
        
        services_manager = HG.client_controller.services_manager
        
        sort_choices = ClientData.GetSortChoices( add_namespaces_and_ratings = add_namespaces_and_ratings )
        
        for sort_by in sort_choices:
            
            ( sort_by_type, sort_by_data ) = sort_by
            
            if sort_by_type == 'system':
                
                label = CC.sort_string_lookup[ sort_by_data ]
                
            elif sort_by_type == 'namespaces':
                
                label = '-'.join( sort_by_data )
                
            elif sort_by_type in ( 'rating_descend', 'rating_ascend' ):
                
                service_key = sort_by_data
                
                service = services_manager.GetService( service_key )
                
                if sort_by_type == 'rating_descend':
                    
                    label = service.GetName() + ' rating highest first'
                    
                elif sort_by_type == 'rating_ascend':
                    
                    label = service.GetName() + ' rating lowest first'
                    
                
            
            self.Append( 'sort by ' + label, sort_by )
            
        
        self.Bind( wx.EVT_CHOICE, self.EventChoice )
        
        HG.client_controller.sub( self, 'ACollectHappened', 'collect_media' )
        
    
    def _BroadcastSort( self ):
        
        selection = self.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            sort_by = self.GetClientData( selection )
            
            HG.client_controller.pub( 'sort_media', self._page_key, sort_by )
            
        
    
    def ACollectHappened( self, page_key, collect_by ):
        
        if page_key == self._page_key:
            
            self._BroadcastSort()
            
        
    
    def BroadcastSort( self ):
        
        self._BroadcastSort()
        
    
    def EventChoice( self, event ):
        
        if self._page_key is not None:
            
            self._BroadcastSort()
            
        
    
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
        if id == self.ID_NAMESPACE: phrase = u'[\u2026]'
        if id == self.ID_TAG: phrase = u'(\u2026)'
        else: event.Skip()
        
        if phrase is not None: HG.client_controller.pub( 'clipboard', 'text', phrase )
        
    
    def EventButton( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( -1, 'click on a phrase to copy to clipboard' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        menu.Append( self.ID_HASH, 'the file\'s hash - {hash}' )
        menu.Append( self.ID_TAGS, 'all the file\'s tags - {tags}' )
        menu.Append( self.ID_NN_TAGS, 'all the file\'s non-namespaced tags - {nn tags}' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        menu.Append( self.ID_NAMESPACE, u'all instances of a particular namespace - [\u2026]' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        menu.Append( self.ID_TAG, u'a particular tag, if the file has it - (\u2026)' )
        
        HG.client_controller.PopupMenu( self, menu )
        
    
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
        
    
    def SetLabelText( self, label ):
        
        if label != self._last_label:
            
            self._last_label = label
            
            wx.StaticText.SetLabelText( self, label )
            
            self.Wrap( self._wrap )
            
        
    
class Gauge( wx.Gauge ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Gauge.__init__( self, *args, **kwargs )
        
        self._actual_range = None
        
        self._is_pulsing = False
        
    
    def SetRange( self, range ):
        
        if range is None:
            
            self.Pulse()
            
            self._is_pulsing = True
            
        else:
            
            if self._is_pulsing:
                
                self.StopPulsing()
                
            
            if range > 1000:
                
                self._actual_range = range
                range = 1000
                
            else:
                
                self._actual_range = None
                
            
            if range != self.GetRange():
                
                wx.Gauge.SetRange( self, range )
                
            
        
    
    def SetValue( self, value ):
        
        if not self._is_pulsing:
            
            if value is None:
                
                self.Pulse()
                
                self._is_pulsing = True
                
            else:
                
                if self._actual_range is not None:
                    
                    value = min( int( 1000 * ( float( value ) / self._actual_range ) ), 1000 )
                    
                
                if value != self.GetValue():
                    
                    wx.Gauge.SetValue( self, value )
                    
                
            
        
    
    def StopPulsing( self ):
        
        self._is_pulsing = False
        
        self.SetRange( 1 )
        self.SetValue( 1 )
        self.SetValue( 0 )
        
    
class ListBook( wx.Panel ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Panel.__init__( self, *args, **kwargs )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._keys_to_active_pages = {}
        self._keys_to_proto_pages = {}
        
        # Don't use LB_SORT! Linux can't handle clientdata that jumps around!
        self._list_box = wx.ListBox( self, style = wx.LB_SINGLE )
        
        self._empty_panel = wx.Panel( self )
        
        self._empty_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._current_key = None
        
        self._current_panel = self._empty_panel
        
        self._panel_sizer = wx.BoxSizer( wx.VERTICAL )
        
        self._panel_sizer.AddF( self._empty_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._list_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        hbox.AddF( self._panel_sizer, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._list_box.Bind( wx.EVT_LISTBOX, self.EventSelection )
        
        self.SetSizer( hbox )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _ActivatePage( self, key ):

        ( classname, args, kwargs ) = self._keys_to_proto_pages[ key ]
        
        page = classname( *args, **kwargs )
        
        page.Hide()
        
        self._panel_sizer.AddF( page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._keys_to_active_pages[ key ] = page
        
        del self._keys_to_proto_pages[ key ]
        
        self._panel_sizer.CalcMin()
        
        self._RecalcListBoxWidth()
        
    
    def _GetIndex( self, key ):
        
        for i in range( self._list_box.GetCount() ):
            
            i_key = self._list_box.GetClientData( i )
            
            if i_key == key:
                
                return i
                
            
        
        return wx.NOT_FOUND
        
    
    def _RecalcListBoxWidth( self ):
        
        self.Layout()
        
    
    def _Select( self, selection ):
        
        if selection == wx.NOT_FOUND:
            
            self._current_key = None
            
        else:
            
            self._current_key = self._list_box.GetClientData( selection )
            
        
        self._current_panel.Hide()
        
        self._list_box.SetSelection( selection )
        
        if selection == wx.NOT_FOUND:
            
            self._current_panel = self._empty_panel
            
        else:
            
            if self._current_key in self._keys_to_proto_pages:
                
                self._ActivatePage( self._current_key )
                
            
            self._current_panel = self._keys_to_active_pages[ self._current_key ]
            
        
        self._current_panel.Show()
        
        self.Layout()
        
        self.Refresh()
        
        # this tells any parent scrolled panel to update its virtualsize and recalc its scrollbars
        event = wx.NotifyEvent( wx.wxEVT_SIZE, self.GetId() )
        
        wx.CallAfter( self.ProcessEvent, event )
        
        # now the virtualsize is updated, we now tell any parent resizing frame/dialog that is interested in resizing that now is the time
        ClientGUITopLevelWindows.PostSizeChangedEvent( self )
        
        event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGED, -1 )
        
        wx.CallAfter( self.ProcessEvent, event )
        
    
    def AddPage( self, display_name, key, page, select = False ):
        
        if self._GetIndex( key ) != wx.NOT_FOUND:
            
            raise HydrusExceptions.NameException( 'That entry already exists!' )
            
        
        if not isinstance( page, tuple ):
            
            page.Hide()
            
            self._panel_sizer.AddF( page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        # Can't do LB_SORT because of Linux not being able to track clientdata, have to do it manually.
        
        current_display_names = self._list_box.GetStrings()
        
        insertion_index = len( current_display_names )
        
        for ( i, current_display_name ) in enumerate( current_display_names ):
            
            if current_display_name > display_name:
                
                insertion_index = i
                
                break
                
            
        
        self._list_box.Insert( display_name, insertion_index, key )
        
        self._keys_to_active_pages[ key ] = page
        
        self._RecalcListBoxWidth()
        
        if self._list_box.GetCount() == 1:
            
            self._Select( 0 )
            
        elif select:
            
            index = self._GetIndex( key )
            
            self._Select( index )
            
        
    
    def AddPageArgs( self, display_name, key, classname, args, kwargs ):
        
        if self._GetIndex( key ) != wx.NOT_FOUND:
            
            raise HydrusExceptions.NameException( 'That entry already exists!' )
            
        
        # Can't do LB_SORT because of Linux not being able to track clientdata, have to do it manually.
        
        current_display_names = self._list_box.GetStrings()
        
        insertion_index = len( current_display_names )
        
        for ( i, current_display_name ) in enumerate( current_display_names ):
            
            if current_display_name > display_name:
                
                insertion_index = i
                
                break
                
            
        
        self._list_box.Insert( display_name, insertion_index, key )
        
        self._keys_to_proto_pages[ key ] = ( classname, args, kwargs )
        
        self._RecalcListBoxWidth()
        
        if self._list_box.GetCount() == 1:
            
            self._Select( 0 )
            
        
    
    def DeleteAllPages( self ):
        
        self._panel_sizer.Detach( self._empty_panel )
        
        self._panel_sizer.Clear( deleteWindows = True )
        
        self._panel_sizer.AddF( self._empty_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._current_key = None
        
        self._current_panel = self._empty_panel
        
        self._keys_to_active_pages = {}
        self._keys_to_proto_pages = {}
        
        self._list_box.Clear()
        
    
    def DeleteCurrentPage( self ):
        
        selection = self._list_box.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            key_to_delete = self._current_key
            page_to_delete = self._current_panel
            
            next_selection = selection + 1
            previous_selection = selection - 1
            
            if next_selection < self._list_box.GetCount():
                
                self._Select( next_selection )
                
            elif previous_selection >= 0:
                
                self._Select( previous_selection )
                
            else:
                
                self._Select( wx.NOT_FOUND )
                
            
            self._panel_sizer.Detach( page_to_delete )
            
            page_to_delete.Destroy()
            
            del self._keys_to_active_pages[ key_to_delete ]
            
            self._list_box.Delete( selection )
            
            self._RecalcListBoxWidth()
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'select_down': self.SelectDown()
            elif command == 'select_up': self.SelectUp()
            else: event.Skip()
            
        
    
    def EventSelection( self, event ):
        
        if self._list_box.GetSelection() != self._GetIndex( self._current_key ):
            
            event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING, -1 )
            
            self.GetEventHandler().ProcessEvent( event )
            
            if event.IsAllowed():
                
                self._Select( self._list_box.GetSelection() )
                
            else:
                
                self._list_box.SetSelection( self._GetIndex( self._current_key ) )
                
            
        
    
    def GetCurrentKey( self ):
        
        return self._current_key
        
    
    def GetCurrentPage( self ):
        
        if self._current_panel == self._empty_panel:
            
            return None
            
        else:
            
            return self._current_panel
            
        
    
    def GetActivePages( self ):
        
        return self._keys_to_active_pages.values()
        
    
    def GetPage( self, key ):
        
        if key in self._keys_to_proto_pages:
            
            self._ActivatePage( key )
            
        
        if key in self._keys_to_active_pages:
            
            return self._keys_to_active_pages[ key ]
            
        
        raise Exception( 'That page not found!' )
        
    
    def GetPageCount( self ):
        
        return len( self._keys_to_active_pages ) + len( self._keys_to_proto_pages )
        
    
    def KeyExists( self, key ):
        
        return key in self._keys_to_active_pages or key in self._keys_to_proto_pages
        
    
    def RenamePage( self, key, new_name ):
        
        index = self._GetIndex( key )
        
        if index != wx.NOT_FOUND:
            
            self._list_box.SetString( index, new_name )
            
        
        self._RecalcListBoxWidth()
        
    
    def Select( self, key ):
        
        index = self._GetIndex( key )
        
        if index != wx.NOT_FOUND and index != self._list_box.GetSelection():
            
            event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING, -1 )
            
            self.GetEventHandler().ProcessEvent( event )
            
            if event.IsAllowed():
                
                self._Select( index )
                
            
        
    
    def SelectDown( self ):
        
        current_selection = self._list_box.GetSelection()
        
        if current_selection != wx.NOT_FOUND:
            
            num_entries = self._list_box.GetCount()
            
            if current_selection == num_entries - 1: selection = 0
            else: selection = current_selection + 1
            
            if selection != current_selection:
                
                self._Select( selection )
                
            
        
    
    def SelectPage( self, page_to_select ):
        
        for ( key, page ) in self._keys_to_active_pages.items():
            
            if page == page_to_select:
                
                self._Select( self._GetIndex( key ) )
                
                return
                
            
        
    
    def SelectUp( self ):
        
        current_selection = self._list_box.GetSelection()
        
        if current_selection != wx.NOT_FOUND:
            
            num_entries = self._list_box.GetCount()
            
            if current_selection == 0: selection = num_entries - 1
            else: selection = current_selection - 1
            
            if selection != current_selection:
                
                self._Select( selection )
                
            
        
    
class CheckboxManager( object ):
    
    def GetCurrentValue( self ):
        
        raise NotImplementedError()
        
    
    def Invert( self ):
        
        raise NotImplementedError()
        
    
class CheckboxManagerCalls( CheckboxManager ):
    
    def __init__( self, invert_call, value_call ):
        
        CheckboxManager.__init__( self )
        
        self._invert_call = invert_call
        self._value_call = value_call
        
    
    def GetCurrentValue( self ):
        
        return self._value_call()
        
    
    def Invert( self ):
        
        self._invert_call()
        
    
class CheckboxManagerOptions( CheckboxManager ):
    
    def __init__( self, boolean_name ):
        
        CheckboxManager.__init__( self )
        
        self._boolean_name = boolean_name
        
    
    def GetCurrentValue( self ):
        
        new_options = HG.client_controller.GetNewOptions()
        
        return new_options.GetBoolean( self._boolean_name )
        
    
    def Invert( self ):
        
        new_options = HG.client_controller.GetNewOptions()
        
        new_options.InvertBoolean( self._boolean_name )
        
    
class MenuBitmapButton( BetterBitmapButton ):
    
    def __init__( self, parent, bitmap, menu_items ):
        
        BetterBitmapButton.__init__( self, parent, bitmap, self.DoMenu )
        
        self._menu_items = menu_items
        
    
    def DoMenu( self ):
        
        menu = wx.Menu()
        
        for ( item_type, title, description, data ) in self._menu_items:
            
            if item_type == 'normal':
                
                func = data
                
                ClientGUIMenus.AppendMenuItem( self, menu, title, description, func )
                
            elif item_type == 'check':
                
                check_manager = data
                
                current_value = check_manager.GetCurrentValue()
                func = check_manager.Invert
                
                ClientGUIMenus.AppendMenuCheckItem( self, menu, title, description, current_value, func )
                
            elif item_type == 'separator':
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
        
        HG.client_controller.PopupMenu( self, menu )
        
    
class MenuButton( BetterButton ):
    
    def __init__( self, parent, label, menu_items ):
        
        BetterButton.__init__( self, parent, label, self.DoMenu )
        
        self._menu_items = menu_items
        
    
    def DoMenu( self ):
        
        menu = wx.Menu()
        
        for ( item_type, title, description, data ) in self._menu_items:
            
            if item_type == 'normal':
                
                callable = data
                
                ClientGUIMenus.AppendMenuItem( self, menu, title, description, callable )
                
            elif item_type == 'check':
                
                check_manager = data
                
                initial_value = check_manager.GetInitialValue()
                
                ClientGUIMenus.AppendMenuCheckItem( self, menu, title, description, initial_value, check_manager.Invert )
                
            elif item_type == 'separator':
                
                ClientGUIMenus.AppendSeparator( menu )
                
            elif item_type == 'label':
                
                ClientGUIMenus.AppendMenuLabel( menu, title, description )
                
            
        
        HG.client_controller.PopupMenu( self, menu )
        
    
    def SetMenuItems( self, menu_items ):
        
        self._menu_items = menu_items
        
    
class NoneableSpinCtrl( wx.Panel ):
    
    def __init__( self, parent, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1, num_dimensions = 1 ):
        
        wx.Panel.__init__( self, parent )
        
        self._unit = unit
        self._multiplier = multiplier
        self._num_dimensions = num_dimensions
        
        self._checkbox = wx.CheckBox( self )
        self._checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckBox )
        self._checkbox.SetLabelText( none_phrase )
        
        self._one = wx.SpinCtrl( self, min = min, max = max, size = ( 60, -1 ) )
        
        if num_dimensions == 2:
            
            self._two = wx.SpinCtrl( self, initial = 0, min = min, max = max, size = ( 60, -1 ) )
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if len( message ) > 0:
            
            hbox.AddF( BetterStaticText( self, message + ': ' ), CC.FLAGS_VCENTER )
            
        
        hbox.AddF( self._one, CC.FLAGS_VCENTER )
        
        if self._num_dimensions == 2:
            
            hbox.AddF( BetterStaticText( self, 'x' ), CC.FLAGS_VCENTER )
            hbox.AddF( self._two, CC.FLAGS_VCENTER )
            
        
        if self._unit is not None:
            
            hbox.AddF( BetterStaticText( self, self._unit ), CC.FLAGS_VCENTER )
            
        
        hbox.AddF( self._checkbox, CC.FLAGS_VCENTER )
        
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
            
        
    
    def SetToolTipString( self, text ):
        
        wx.Panel.SetToolTipString( self, text )
        
        for c in self.GetChildren():
            
            c.SetToolTipString( text )
            
        
    
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
        
        HG.client_controller.sub( self, 'HitButton', 'hit_on_off_button' )
        
    
    def EventButton( self, event ):
        
        if self._on:
            
            self._on = False
            
            self.SetLabelText( self._off_label )
            
            self.SetForegroundColour( ( 128, 0, 0 ) )
            
            HG.client_controller.pub( self._topic, self._page_key, False )
            
        else:
            
            self._on = True
            
            self.SetLabelText( self._on_label )
            
            self.SetForegroundColour( ( 0, 128, 0 ) )
            
            HG.client_controller.pub( self._topic, self._page_key, True )
            
        
    
    def IsOn( self ): return self._on
    
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
        
    
    def _Draw( self, dc ):
        
        raise NotImplementedError()
        
    
    def EventEraseBackground( self, event ): pass
    
    def EventLeftDown( self, event ):
        
        raise NotImplementedError()
        
    
    def EventPaint( self, event ):
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if self._dirty:
            
            self._Draw( dc )
            
        
    
    def EventRightDown( self, event ):
        
        raise NotImplementedError()
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
class RatingLikeDialog( RatingLike ):
    
    def __init__( self, parent, service_key ):
        
        RatingLike.__init__( self, parent, service_key )
        
        self._rating_state = ClientRatings.NULL
        
    
    def _Draw( self, dc ):
        
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
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        name = service.GetName()
        
        self.SetToolTipString( name )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
    def _Draw( self, dc ):
        
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
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def EventRightDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.DISLIKE: rating = None
            else: rating = 0
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
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
            
            if self._current_media is None:
                
                self._hashes = set()
                
            else:
                
                self._hashes = self._current_media.GetHashes()
                
            
            self._dirty = True
            
            self.Refresh()
            
        
    
class RatingNumerical( wx.Window ):
    
    def __init__( self, parent, service_key ):
        
        wx.Window.__init__( self, parent )
        
        self._service_key = service_key
        
        self._service = HG.client_controller.services_manager.GetService( self._service_key )
        
        self._num_stars = self._service.GetNumStars()
        self._allow_zero = self._service.AllowZero()
        
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
        
    
    def _Draw( self, dc ):
        
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
        
    
    def EventEraseBackground( self, event ): pass
    
    def EventLeftDown( self, event ):
        
        raise NotImplementedError()
        
    
    def EventPaint( self, event ):
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if self._dirty:
            
            self._Draw( dc )
            
        
    
    def EventRightDown( self, event ):
        
        raise NotImplementedError()
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
class RatingNumericalDialog( RatingNumerical ):
    
    def __init__( self, parent, service_key ):
        
        RatingNumerical.__init__( self, parent, service_key )
        
        self._rating_state = ClientRatings.NULL
        self._rating = None
        
    
    def _Draw( self, dc ):
        
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
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
    def _Draw( self, dc ):
        
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
                
                HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
                
            
        
    
    def EventRightDown( self, event ):
        
        if self._current_media is not None:
            
            rating = None
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
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
            
            if self._current_media is None:
                
                self._hashes = set()
                
            else:
                
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
        
        ClientGUIMenus.AppendSeparator( menu )
        
        submenu = wx.Menu()
        
        submenu.Append( self.ID_REGEX_WHITESPACE, r'whitespace character - \s' )
        submenu.Append( self.ID_REGEX_NUMBER, r'number character - \d' )
        submenu.Append( self.ID_REGEX_ALPHANUMERIC, r'alphanumeric or backspace character - \w' )
        submenu.Append( self.ID_REGEX_ANY, r'any character - .' )
        submenu.Append( self.ID_REGEX_BACKSPACE, r'backspace character - \\' )
        submenu.Append( self.ID_REGEX_BEGINNING, r'beginning of line - ^' )
        submenu.Append( self.ID_REGEX_END, r'end of line - $' )
        submenu.Append( self.ID_REGEX_SET, u'any of these - [\u2026]' )
        submenu.Append( self.ID_REGEX_NOT_SET, u'anything other than these - [^\u2026]' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        submenu.Append( self.ID_REGEX_0_OR_MORE_GREEDY, r'0 or more matches, consuming as many as possible - *' )
        submenu.Append( self.ID_REGEX_1_OR_MORE_GREEDY, r'1 or more matches, consuming as many as possible - +' )
        submenu.Append( self.ID_REGEX_0_OR_1_GREEDY, r'0 or 1 matches, preferring 1 - ?' )
        submenu.Append( self.ID_REGEX_0_OR_MORE_MINIMAL, r'0 or more matches, consuming as few as possible - *?' )
        submenu.Append( self.ID_REGEX_1_OR_MORE_MINIMAL, r'1 or more matches, consuming as few as possible - +?' )
        submenu.Append( self.ID_REGEX_0_OR_1_MINIMAL, r'0 or 1 matches, preferring 0 - *' )
        submenu.Append( self.ID_REGEX_EXACTLY_M, r'exactly m matches - {m}' )
        submenu.Append( self.ID_REGEX_M_TO_N_GREEDY, r'm to n matches, consuming as many as possible - {m,n}' )
        submenu.Append( self.ID_REGEX_M_TO_N_MINIMAL, r'm to n matches, consuming as few as possible - {m,n}?' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        submenu.Append( self.ID_REGEX_LOOKAHEAD, u'the next characters are: (non-consuming) - (?=\u2026)' )
        submenu.Append( self.ID_REGEX_NEGATIVE_LOOKAHEAD, u'the next characters are not: (non-consuming) - (?!\u2026)' )
        submenu.Append( self.ID_REGEX_LOOKBEHIND, u'the previous characters are: (non-consuming) - (?<=\u2026)' )
        submenu.Append( self.ID_REGEX_NEGATIVE_LOOKBEHIND, u'the previous characters are not: (non-consuming) - (?<!\u2026)' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        submenu.Append( self.ID_REGEX_NUMBER_WITHOUT_ZEROES, r'0074 -> 74 - [1-9]+\d*' )
        submenu.Append( self.ID_REGEX_FILENAME, r'filename - (?<=' + os.path.sep.encode( 'string_escape' ) + r')[^' + os.path.sep.encode( 'string_escape' ) + r']*?(?=\..*$)' )
        
        menu.AppendMenu( -1, 'regex components', submenu )
        
        submenu = wx.Menu()
        
        submenu.Append( self.ID_REGEX_MANAGE_FAVOURITES, 'manage favourites' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        for ( index, ( regex_phrase, description ) ) in enumerate( HC.options[ 'regex_favourites' ] ):
            
            menu_id = index + 100
            
            submenu.Append( menu_id, description )
            
        
        menu.AppendMenu( -1, 'favourites', submenu )
        
        HG.client_controller.PopupMenu( self, menu )
        
    
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
        elif id == self.ID_REGEX_SET: phrase = u'[\u2026]'
        elif id == self.ID_REGEX_NOT_SET: phrase = u'[^\u2026]'
        elif id == self.ID_REGEX_0_OR_MORE_GREEDY: phrase = r'*'
        elif id == self.ID_REGEX_1_OR_MORE_GREEDY: phrase = r'+'
        elif id == self.ID_REGEX_0_OR_1_GREEDY: phrase = r'?'
        elif id == self.ID_REGEX_0_OR_MORE_MINIMAL: phrase = r'*?'
        elif id == self.ID_REGEX_1_OR_MORE_MINIMAL: phrase = r'+?'
        elif id == self.ID_REGEX_0_OR_1_MINIMAL: phrase = r'*'
        elif id == self.ID_REGEX_EXACTLY_M: phrase = r'{m}'
        elif id == self.ID_REGEX_M_TO_N_GREEDY: phrase = r'{m,n}'
        elif id == self.ID_REGEX_M_TO_N_MINIMAL: phrase = r'{m,n}?'
        elif id == self.ID_REGEX_LOOKAHEAD: phrase = u'(?=\u2026)'
        elif id == self.ID_REGEX_NEGATIVE_LOOKAHEAD: phrase = u'(?!\u2026)'
        elif id == self.ID_REGEX_LOOKBEHIND: phrase = u'(?<=\u2026)'
        elif id == self.ID_REGEX_NEGATIVE_LOOKBEHIND: phrase = u'(?<!\u2026)'
        elif id == self.ID_REGEX_NUMBER_WITHOUT_ZEROES: phrase = r'[1-9]+\d*'
        elif id == self.ID_REGEX_FILENAME: phrase = '(?<=' + os.path.sep.encode( 'string_escape' ) + r')[^' + os.path.sep.encode( 'string_escape' ) + r']*?(?=\..*$)'
        elif id == self.ID_REGEX_MANAGE_FAVOURITES:
            
            import ClientGUIDialogsManage
            
            with ClientGUIDialogsManage.DialogManageRegexFavourites( self.GetTopLevelParent() ) as dlg:
                
                dlg.ShowModal()
                
            
        elif id in self.ID_REGEX_FAVOURITES:
            
            index = id - 100
            
            ( phrase, description ) = HC.options[ 'regex_favourites' ][ index ]
            
        else: event.Skip()
        
        if phrase is not None: HG.client_controller.pub( 'clipboard', 'text', phrase )
        
    
class SaneMultilineTextCtrl( wx.TextCtrl ):
    
    def __init__( self, parent, style = None ):
        
        if style is None:
            
            style = wx.TE_MULTILINE
            
        else:
            
            style |= wx.TE_MULTILINE
            
        
        wx.TextCtrl.__init__( self, parent, style = style )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
    
    def EventKeyDown( self, event ):
        
        ctrl = event.CmdDown()
        
        key_code = event.GetKeyCode()
        
        if ctrl and key_code in ( ord( 'A' ), ord( 'a' ) ):
            
            self.SelectAll()
            
        else:
            
            event.Skip()
            
        
    
class Shortcut( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._mouse_radio = wx.RadioButton( self, style = wx.RB_GROUP, label = 'mouse' )
        self._mouse_shortcut = ShortcutMouse( self, self._mouse_radio )
        
        self._keyboard_radio = wx.RadioButton( self, label = 'keyboard' )
        self._keyboard_shortcut = ShortcutKeyboard( self, self._keyboard_radio )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( BetterStaticText( self, 'Mouse events only work for the duplicate and archive/delete filters atm!' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        gridbox.AddF( self._mouse_radio, CC.FLAGS_VCENTER )
        gridbox.AddF( self._mouse_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._keyboard_radio, CC.FLAGS_VCENTER )
        gridbox.AddF( self._keyboard_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        if self._mouse_radio.GetValue() == True:
            
            return self._mouse_shortcut.GetValue()
            
        else:
            
            return self._keyboard_shortcut.GetValue()
            
        
    
    def SetValue( self, shortcut ):
        
        if shortcut.GetShortcutType() == CC.SHORTCUT_TYPE_MOUSE:
            
            self._mouse_radio.SetValue( True )
            self._mouse_shortcut.SetValue( shortcut )
            
        else:
            
            self._keyboard_radio.SetValue( True )
            self._keyboard_shortcut.SetValue( shortcut )
            
        
    
class ShortcutKeyboard( wx.TextCtrl ):
    
    def __init__( self, parent, related_radio = None ):
        
        self._shortcut = ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F7, [] )
        
        self._related_radio = related_radio
        
        wx.TextCtrl.__init__( self, parent, style = wx.TE_PROCESS_ENTER )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._SetShortcutString()
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
        wx.TextCtrl.SetValue( self, display_string )
        
    
    def EventKeyDown( self, event ):
        
        shortcut = ClientData.ConvertKeyEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            if self._related_radio is not None:
                
                self._related_radio.SetValue( True )
                
            
            self._SetShortcutString()
            
        
    
    def GetValue( self ):
        
        return self._shortcut
        
    
    def SetValue( self, shortcut ):
        
        self._shortcut = shortcut
        
        self._SetShortcutString()
        
    
class ShortcutMouse( wx.Button ):
    
    def __init__( self, parent, related_radio = None ):
        
        self._shortcut = ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] )
        
        self._related_radio = related_radio
        
        wx.Button.__init__( self, parent )
        
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse )
        
        self._SetShortcutString()
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
        self.SetLabel( display_string )
        
    
    def EventMouse( self, event ):
        
        shortcut = ClientData.ConvertMouseEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            if self._related_radio is not None:
                
                self._related_radio.SetValue( True )
                
            
            self._SetShortcutString()
            
        
    
    def GetValue( self ):
        
        return self._shortcut
        
    
    def SetValue( self, shortcut ):
        
        self._shortcut = shortcut
        
        self._SetShortcutString()
        
    
class StaticBox( wx.Panel ):
    
    def __init__( self, parent, title ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
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
        self._sorter.Append( 'lexicographic (a-z) (grouped by namespace)', CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC )
        self._sorter.Append( 'lexicographic (z-a) (grouped by namespace)', CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC )
        self._sorter.Append( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
        self._sorter.Append( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
        self._sorter.Append( 'incidence (desc) (grouped by namespace)', CC.SORT_BY_INCIDENCE_NAMESPACE_DESC )
        self._sorter.Append( 'incidence (asc) (grouped by namespace)', CC.SORT_BY_INCIDENCE_NAMESPACE_ASC )
        
        if HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_ASC: self._sorter.Select( 0 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_DESC: self._sorter.Select( 1 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC: self._sorter.Select( 2 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC: self._sorter.Select( 3 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_DESC: self._sorter.Select( 4 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_ASC: self._sorter.Select( 5 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_NAMESPACE_DESC: self._sorter.Select( 6 )
        elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_NAMESPACE_ASC: self._sorter.Select( 7 )
        
        self._sorter.Bind( wx.EVT_CHOICE, self.EventSort )
        
        self.AddF( self._sorter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def ChangeTagService( self, service_key ): self._tags_box.ChangeTagService( service_key )
    
    def EventSort( self, event ):
        
        selection = self._sorter.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            sort = self._sorter.GetClientData( selection )
            
            self._tags_box.SetSort( sort )
            
        
    
    def SetTagsBox( self, tags_box ):
        
        self._tags_box = tags_box
        
        self.AddF( self._tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def SetTagsByMedia( self, media, force_reload = False ):
        
        self._tags_box.SetTagsByMedia( media, force_reload = force_reload )
        
    
class TextAndGauge( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._st = BetterStaticText( self )
        self._gauge = Gauge( self )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def SetValue( self, text, value, range ):
        
        if text != self._st.GetLabelText():
            
            self._st.SetLabelText( text )
            
        
        self._gauge.SetRange( range )
        self._gauge.SetValue( value )
        
    
( DirtyEvent, EVT_DIRTY ) = wx.lib.newevent.NewEvent()

class ThreadToGUIUpdater( object ):
    
    def __init__( self, event_handler, func ):
        
        self._event_handler = event_handler
        self._func = func
        
        self._lock = threading.Lock()
        self._dirty_count = 0
        self._args = None
        self._kwargs = None
        
        self._my_object_alive = True
        
        event_handler.Bind( EVT_DIRTY, self.EventDirty )
        
    
    def EventDirty( self, event ):
        
        with self._lock:
            
            try:
                
                self._func( *self._args, **self._kwargs )
                
            except HydrusExceptions.ShutdownException:
                
                pass
                
            
            self._dirty_count = 0
            
        
    
    # the point here is that we can spam this a hundred times a second and wx will catch up to it when the single event gets processed
    # if wx feels like running fast, it'll update at 60fps
    # if not, we won't get bungled up with 10,000+ pubsub events in the event queue
    def Update( self, *args, **kwargs ):
        
        with self._lock:
            
            self._args = args
            self._kwargs = kwargs
            
            if self._dirty_count == 0 and self._my_object_alive:
                
                def wx_code():
                    
                    try:
                        
                        wx.PostEvent( self._event_handler, DirtyEvent() )
                        
                    except TypeError:
                        
                        if not bool( self._event_handler ):
                            
                            # Event Handler is dead (would give PyDeadObjectError if accessed--PostEvent throws TypeError)
                            
                            self._my_object_alive = False
                            
                        else:
                            
                            raise
                            
                        
                    
                    
                
                wx.CallAfter( wx_code )
                
            
            self._dirty_count += 1
            
            take_a_break = self._dirty_count % 1000 == 0
            
        
        # just in case we are choking the wx thread, let's give it a break every now and then
        if take_a_break:
            
            time.sleep( 0.25 )
            
        
    
( TimeDeltaEvent, EVT_TIME_DELTA ) = wx.lib.newevent.NewCommandEvent()

class TimeDeltaButton( wx.Button ):
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False, monthly_allowed = False ):
        
        wx.Button.__init__( self, parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        self._monthly_allowed = monthly_allowed
        
        self._value = self._min
        
        self.SetLabelText( 'initialising' )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def _RefreshLabel( self ):
        
        text_components = []
        
        value = self._value
        
        if value is None:
            
            text = 'monthly'
            
        else:
            
            text = HydrusData.ConvertTimeDeltaToPrettyString( value )
            
        
        self.SetLabelText( text )
        
    
    def EventButton( self, event ):
        
        import ClientGUIDialogs
        
        with ClientGUIDialogs.DialogInputTimeDelta( self, self._value, min = self._min, days = self._show_days, hours = self._show_hours, minutes = self._show_minutes, seconds = self._show_seconds, monthly_allowed = self._monthly_allowed ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                value = dlg.GetValue()
                
                self.SetValue( value )
                
                new_event = TimeDeltaEvent( 0 )
                
                wx.PostEvent( self, new_event )
                
            
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
        self._RefreshLabel()
        
        self.GetParent().Layout()
        
    
class TimeDeltaCtrl( wx.Panel ):
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False, monthly_allowed = False ):
        
        wx.Panel.__init__( self, parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        self._monthly_allowed = monthly_allowed
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if self._show_days:
            
            self._days = wx.SpinCtrl( self, min = 0, max = 360, size = ( 50, -1 ) )
            self._days.Bind( wx.EVT_SPINCTRL, self.EventChange )
            
            hbox.AddF( self._days, CC.FLAGS_VCENTER )
            hbox.AddF( BetterStaticText( self, 'days' ), CC.FLAGS_VCENTER )
            
        
        if self._show_hours:
            
            self._hours = wx.SpinCtrl( self, min = 0, max = 23, size = ( 45, -1 ) )
            self._hours.Bind( wx.EVT_SPINCTRL, self.EventChange )
            
            hbox.AddF( self._hours, CC.FLAGS_VCENTER )
            hbox.AddF( BetterStaticText( self, 'hours' ), CC.FLAGS_VCENTER )
            
        
        if self._show_minutes:
            
            self._minutes = wx.SpinCtrl( self, min = 0, max = 59, size = ( 45, -1 ) )
            self._minutes.Bind( wx.EVT_SPINCTRL, self.EventChange )
            
            hbox.AddF( self._minutes, CC.FLAGS_VCENTER )
            hbox.AddF( BetterStaticText( self, 'minutes' ), CC.FLAGS_VCENTER )
            
        
        if self._show_seconds:
            
            self._seconds = wx.SpinCtrl( self, min = 0, max = 59, size = ( 45, -1 ) )
            self._seconds.Bind( wx.EVT_SPINCTRL, self.EventChange )
            
            hbox.AddF( self._seconds, CC.FLAGS_VCENTER )
            hbox.AddF( BetterStaticText( self, 'seconds' ), CC.FLAGS_VCENTER )
            
        
        if self._monthly_allowed:
            
            self._monthly = wx.CheckBox( self )
            self._monthly.Bind( wx.EVT_CHECKBOX, self.EventChange )
            
            hbox.AddF( self._monthly, CC.FLAGS_VCENTER )
            hbox.AddF( BetterStaticText( self, 'monthly' ), CC.FLAGS_VCENTER )
            
        
        self.SetSizer( hbox )
        
    
    def _UpdateEnables( self ):
        
        value = self.GetValue()
        
        if value is None:
            
            if self._show_days:
                
                self._days.Disable()
                
            
            if self._show_hours:
                
                self._hours.Disable()
                
            
            if self._show_minutes:
                
                self._minutes.Disable()
                
            
            if self._show_seconds:
                
                self._seconds.Disable()
                
            
        else:
            
            if self._show_days:
                
                self._days.Enable()
                
            
            if self._show_hours:
                
                self._hours.Enable()
                
            
            if self._show_minutes:
                
                self._minutes.Enable()
                
            
            if self._show_seconds:
                
                self._seconds.Enable()
                
            
        
    
    def EventChange( self, event ):
        
        value = self.GetValue()
        
        if value is not None and value < self._min:
            
            self.SetValue( self._min )
            
        
        self._UpdateEnables()
        
        new_event = TimeDeltaEvent( 0 )
        
        wx.PostEvent( self, new_event )
        
    
    def GetValue( self ):
        
        if self._monthly_allowed and self._monthly.GetValue():
            
            return None
            
        
        value = 0
        
        if self._show_days:
            
            value += self._days.GetValue() * 86400
            
        
        if self._show_hours:
            
            value += self._hours.GetValue() * 3600
            
        
        if self._show_minutes:
            
            value += self._minutes.GetValue() * 60
            
        
        if self._show_seconds:
            
            value += self._seconds.GetValue()
            
        
        return value
        
    
    def SetValue( self, value ):
        
        if self._monthly_allowed:
            
            if value is None:
                
                self._monthly.SetValue( True )
                
            else:
                
                self._monthly.SetValue( False )
                
            
        
        if value is not None:
            
            if value < self._min:
                
                value = self._min
                
            
            if self._show_days:
                
                self._days.SetValue( value / 86400 )
                
                value %= 86400
                
            
            if self._show_hours:
                
                self._hours.SetValue( value / 3600 )
                
                value %= 3600
                
            
            if self._show_minutes:
                
                self._minutes.SetValue( value / 60 )
                
                value %= 60
                
            
            if self._show_seconds:
                
                self._seconds.SetValue( value )
                
            
        
        self._UpdateEnables()
        
    
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
    
    def SetString( self, index, text ): self._indices_to_radio_buttons[ index ].SetLabelText( text )
    
