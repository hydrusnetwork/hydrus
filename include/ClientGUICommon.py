import collections
import HydrusConstants as HC
import ClientCaches
import ClientData
import ClientConstants as CC
import ClientGUIMenus
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
import wx.lib.newevent
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
ID_TIMER_POPUP = wx.NewId()

def FlushOutPredicates( parent, predicates ):
    
    good_predicates = []
    
    for predicate in predicates:
        
        predicate = predicate.GetCountlessCopy()
        
        ( predicate_type, value, inclusive ) = predicate.GetInfo()
        
        if value is None and predicate_type in [ HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, HC.PREDICATE_TYPE_SYSTEM_LIMIT, HC.PREDICATE_TYPE_SYSTEM_SIZE, HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS, HC.PREDICATE_TYPE_SYSTEM_AGE, HC.PREDICATE_TYPE_SYSTEM_HASH, HC.PREDICATE_TYPE_SYSTEM_DURATION, HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, HC.PREDICATE_TYPE_SYSTEM_MIME, HC.PREDICATE_TYPE_SYSTEM_RATING, HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE ]:
            
            import ClientGUIDialogs
            
            with ClientGUIDialogs.DialogInputFileSystemPredicates( parent, predicate_type ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    good_predicates.extend( dlg.GetPredicates() )
                    
                else:
                    
                    continue
                    
                
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_UNTAGGED:
            
            good_predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '=', 0 ) ) )
            
        else:
            
            good_predicates.append( predicate )
            
        
    
    return good_predicates
    
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
            
        
        gridbox.AddF( wx.StaticText( parent, label = text ), text_flags )
        gridbox.AddF( control, cflags )
        
    
    return gridbox
    
def WrapInText( control, parent, text ):
    
    hbox = wx.BoxSizer( wx.HORIZONTAL )
    
    hbox.AddF( wx.StaticText( parent, label = text ), CC.FLAGS_VCENTER )
    hbox.AddF( control, CC.FLAGS_EXPAND_BOTH_WAYS )
    
    return hbox
    
def IsWXAncestor( child, ancestor ):
    
    parent = child
    
    while not isinstance( parent, wx.TopLevelWindow ):
        
        if parent == ancestor:
            
            return True
            
        
        parent = parent.GetParent()
        
    
    return False
    
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
            
        
    
class BetterButton( wx.Button ):
    
    def __init__( self, parent, label, callable, *args, **kwargs ):
        
        wx.Button.__init__( self, parent, label = label )
        
        self._callable = callable
        self._args = args
        self._kwargs = kwargs
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        self._callable( *self._args,  **self._kwargs )
        
    
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
    
    def __init__( self, parent, page_key = None, add_namespaces_and_ratings = True ):
        
        BetterChoice.__init__( self, parent )
        
        self._page_key = page_key
        
        sort_choices = ClientData.GetSortChoices( add_namespaces_and_ratings = add_namespaces_and_ratings )
        
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
        
    
class EditStringToStringDict( wx.Panel ):
    
    def __init__( self, parent, initial_dict ):
        
        wx.Panel.__init__( self, parent )
        
        self._listctrl = SaneListCtrl( self, 120, [ ( 'key', 200 ), ( 'value', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        self._add = BetterButton( self, 'add', self.Add )
        self._edit = BetterButton( self, 'edit', self.Edit )
        self._delete = BetterButton( self, 'delete', self.Delete )
        
        #
        
        for display_tuple in initial_dict.items():
            
            self._listctrl.Append( display_tuple, display_tuple )
            
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._add, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._edit, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._delete, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def Add( self ):
        
        import ClientGUIDialogs
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the key', allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                key = dlg.GetValue()
                
                with ClientGUIDialogs.DialogTextEntry( self, 'enter the value', allow_blank = True ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        value = dlg.GetValue()
                        
                        display_tuple = ( key, value )
                        
                        self._listctrl.Append( display_tuple, display_tuple )
                        
                    
                
            
        
    
    def Delete( self ):
        
        self._listctrl.RemoveAllSelected()
        
    
    def Edit( self ):
        
        for i in self._listctrl.GetAllSelected():
            
            ( key, value ) = self._listctrl.GetClientData( i )
            
            import ClientGUIDialogs
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the key', default = key, allow_blank = False ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    key = dlg.GetValue()
                    
                else:
                    
                    return
                    
                
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the value', default = value, allow_blank = True ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    value = dlg.GetValue()
                    
                else:
                    
                    return
                    
                
            
            display_tuple = ( key, value )
            
            self._listctrl.UpdateRow( i, display_tuple, display_tuple )
            
        
    
    def GetValue( self ):
        
        value_dict = { key : value for ( key, value ) in self._listctrl.GetClientData() }
        
        return value_dict
        
    
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
        
        HydrusGlobals.client_controller.PopupMenu( self, menu )
        
    
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
        event = CC.SizeChangedEvent( -1 )
        
        wx.CallAfter( self.ProcessEvent, event )
        
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
        
    
    def _NewSearchPage( self ):

        predicates = []
        
        for term in self._selected_terms:
            
            if isinstance( term, ClientSearch.Predicate ):
                
                predicates.append( term )
                
            else:
                
                predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, term ) )
                
            
        
        predicates = FlushOutPredicates( self, predicates )
        
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
                            
                        
                        if command == 'copy_sub_terms' and ':' in text:
                            
                            ( namespace_gumpf, text ) = text.split( ':', 1 )
                            
                        
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
                    
                    if ':' in selection_string:
                        
                        sub_selection_string = '"' + selection_string.split( ':', 1 )[1]
                        
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
        
        predicates = FlushOutPredicates( self, predicates )
        
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
                    
                    if ':' in tag:
                        
                        ( namespace, subtag ) = tag.split( ':', 1 )
                        
                    else:
                        
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
        
    
class MenuButton( BetterButton ):
    
    def __init__( self, parent, label, menu_items ):
        
        BetterButton.__init__( self, parent, label, self.DoMenu )
        
        self._menu_items = menu_items
        
    
    def DoMenu( self ):
        
        menu = wx.Menu()
        
        for ( title, description, callable ) in self._menu_items:
            
            ClientGUIMenus.AppendMenuItem( menu, title, description, self, callable )
            
        
        HydrusGlobals.client_controller.PopupMenu( self, menu )
        
    
class NoneableSpinCtrl( wx.Panel ):
    
    def __init__( self, parent, message, none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1, num_dimensions = 1 ):
        
        wx.Panel.__init__( self, parent )
        
        self._unit = unit
        self._multiplier = multiplier
        self._num_dimensions = num_dimensions
        
        self._checkbox = wx.CheckBox( self, label = none_phrase )
        self._checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckBox )
        
        self._one = wx.SpinCtrl( self, min = min, max = max, size = ( 60, -1 ) )
        
        if num_dimensions == 2:
            
            self._two = wx.SpinCtrl( self, initial = 0, min = min, max = max, size = ( 60, -1 ) )
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if len( message ) > 0:
            
            hbox.AddF( wx.StaticText( self, label = message + ': ' ), CC.FLAGS_VCENTER )
            
        
        hbox.AddF( self._one, CC.FLAGS_VCENTER )
        
        if self._num_dimensions == 2:
            
            hbox.AddF( wx.StaticText( self, label = 'x' ), CC.FLAGS_VCENTER )
            hbox.AddF( self._two, CC.FLAGS_VCENTER )
            
        
        if self._unit is not None:
            
            hbox.AddF( wx.StaticText( self, label = unit ), CC.FLAGS_VCENTER )
            
        
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
        
        HydrusGlobals.client_controller.sub( self, 'HitButton', 'hit_on_off_button' )
        
    
    def EventButton( self, event ):
        
        if self._on:
            
            self._on = False
            
            self.SetLabelText( self._off_label )
            
            self.SetForegroundColour( ( 128, 0, 0 ) )
            
            HydrusGlobals.client_controller.pub( self._topic, self._page_key, False )
            
        else:
            
            self._on = True
            
            self.SetLabelText( self._on_label )
            
            self.SetForegroundColour( ( 0, 128, 0 ) )
            
            HydrusGlobals.client_controller.pub( self._topic, self._page_key, True )
            
        
    
    def IsOn( self ): return self._on
    
class PopupWindow( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent, style = wx.BORDER_SIMPLE )
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
    
    def TryToDismiss( self ):
        
        self.GetParent().Dismiss( self )
        
    
    def EventDismiss( self, event ):
        
        self.TryToDismiss()
        
    
class PopupDismissAll( PopupWindow ):
    
    def __init__( self, parent ):
        
        PopupWindow.__init__( self, parent )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._text = wx.StaticText( self )
        self._text.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
        button = wx.Button( self, label = 'dismiss all' )
        button.Bind( wx.EVT_BUTTON, self.EventButton )
        button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        
        hbox.AddF( self._text, CC.FLAGS_VCENTER )
        hbox.AddF( ( 20, 20 ), CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( button, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def TryToDismiss( self ):
        
        pass
        
    
    def EventButton( self, event ):
        
        self.GetParent().DismissAll()
        
    
    def SetNumMessages( self, num_messages_pending ):
        
        self._text.SetLabelText( HydrusData.ConvertIntToPrettyString( num_messages_pending ) + ' more messages' )
        
    
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
        
        self._copy_to_clipboard_button = wx.Button( self )
        self._copy_to_clipboard_button.Bind( wx.EVT_BUTTON, self.EventCopyToClipboardButton )
        self._copy_to_clipboard_button.Bind( wx.EVT_RIGHT_DOWN, self.EventDismiss )
        self._copy_to_clipboard_button.Hide()
        
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
        
        hbox.AddF( self._pause_button, CC.FLAGS_VCENTER )
        hbox.AddF( self._cancel_button, CC.FLAGS_VCENTER )
        
        vbox.AddF( self._title, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._text_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._gauge_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._text_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._gauge_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._copy_to_clipboard_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._show_files_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._show_tb_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._tb_text, CC.FLAGS_EXPAND_PERPENDICULAR )
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
        
    
    def EventCopyToClipboardButton( self, event ):
        
        result = self._job_key.GetIfHasVariable( 'popup_clipboard' )
        
        if result is not None:
            
            ( title, text ) = result
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def EventPauseButton( self, event ):
        
        self._job_key.PausePlay()
        
        if self._job_key.IsPaused():
            
            self._pause_button.SetBitmap( CC.GlobalBMPs.play )
            
        else:
            
            self._pause_button.SetBitmap( CC.GlobalBMPs.pause )
            
        
    
    def EventShowFilesButton( self, event ):
        
        result = self._job_key.GetIfHasVariable( 'popup_files' )
        
        if result is not None:
            
            hashes = result
            
            media_results = HydrusGlobals.client_controller.Read( 'media_results', hashes )
            
            HydrusGlobals.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_media_results = media_results )
            
        
    
    def EventShowTBButton( self, event ):
        
        if self._tb_text.IsShown():
            
            self._show_tb_button.SetLabelText( 'show traceback' )
            
            self._tb_text.Hide()
            
        else:
            
            self._show_tb_button.SetLabelText( 'hide traceback' )
            
            self._tb_text.Show()
            
        
        self.GetParent().MakeSureEverythingFits()
        
    
    def GetJobKey( self ):
        
        return self._job_key
        
    
    def IsDeleted( self ):
        
        return self._job_key.IsDeleted()
        
    
    def TryToDismiss( self ):
        
        if self._job_key.IsPausable() or self._job_key.IsCancellable():
            
            return
            
        else:
            
            PopupWindow.TryToDismiss( self )
            
        
    
    def Update( self ):
        
        paused = self._job_key.IsPaused()
        
        title = self._job_key.GetIfHasVariable( 'popup_title' )
        
        if title is not None:
            
            text = title
            
            if self._title.GetLabelText() != text: self._title.SetLabelText( text )
            
            self._title.Show()
            
        else:
            
            self._title.Hide()
            
        
        popup_text_1 = self._job_key.GetIfHasVariable( 'popup_text_1' )
        
        if popup_text_1 is not None or paused:
            
            if paused:
                
                text = 'paused'
                
            else:
                
                text = popup_text_1
                
            
            if self._text_1.GetLabelText() != text:
                
                self._text_1.SetLabelText( self._ProcessText( HydrusData.ToUnicode( text ) ) )
                
            
            self._text_1.Show()
            
        else:
            
            self._text_1.Hide()
            
        
        popup_gauge_1 = self._job_key.GetIfHasVariable( 'popup_gauge_1' )
        
        if popup_gauge_1 is not None and not paused:
            
            ( gauge_value, gauge_range ) = popup_gauge_1
            
            if gauge_range is None or gauge_value is None:
                
                self._gauge_1.Pulse()
                
            else:
                
                self._gauge_1.SetRange( gauge_range )
                self._gauge_1.SetValue( gauge_value )
                
            
            self._gauge_1.Show()
            
        else:
            
            self._gauge_1.Hide()
            
        
        popup_text_2 = self._job_key.GetIfHasVariable( 'popup_text_2' )
        
        if popup_text_2 is not None and not paused:
            
            text = popup_text_2
            
            if self._text_2.GetLabelText() != text:
                
                self._text_2.SetLabelText( self._ProcessText( HydrusData.ToUnicode( text ) ) )
                
            
            self._text_2.Show()
            
        else:
            
            self._text_2.Hide()
            
        
        popup_gauge_2 = self._job_key.GetIfHasVariable( 'popup_gauge_2' )
        
        if popup_gauge_2 is not None and not paused:
            
            ( gauge_value, gauge_range ) = popup_gauge_2
            
            if gauge_range is None or gauge_value is None:
                
                self._gauge_2.Pulse()
                
            else:
                
                self._gauge_2.SetRange( gauge_range )
                self._gauge_2.SetValue( gauge_value )
                
            
            self._gauge_2.Show()
            
        else:
            
            self._gauge_2.Hide()
            
        
        popup_clipboard = self._job_key.GetIfHasVariable( 'popup_clipboard' )
        
        if popup_clipboard is not None:
            
            ( title, text ) = popup_clipboard
            
            if self._copy_to_clipboard_button.GetLabelText() != title:
                
                self._copy_to_clipboard_button.SetLabelText( title )
                
            
            self._copy_to_clipboard_button.Show()
            
        else:
            
            self._copy_to_clipboard_button.Hide()
            
        
        popup_files = self._job_key.GetIfHasVariable( 'popup_files' )
        
        if popup_files is not None:
            
            hashes = popup_files
            
            text = 'show ' + HydrusData.ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
            if self._show_files_button.GetLabelText() != text:
                
                self._show_files_button.SetLabelText( text )
                
            
            self._show_files_button.Show()
            
        else:
            
            self._show_files_button.Hide()
            
        
        popup_traceback = self._job_key.GetIfHasVariable( 'popup_traceback' )
        
        if popup_traceback is not None:
            
            self._copy_tb_button.Show()
            
        else:
            
            self._copy_tb_button.Hide()
            
        
        if popup_traceback is not None:
            
            text = popup_traceback
            
            if self._tb_text.GetLabelText() != text:
                
                self._tb_text.SetLabelText( self._ProcessText( HydrusData.ToUnicode( text ) ) )
                
            
            self._show_tb_button.Show()
            
        else:
            
            self._show_tb_button.Hide()
            self._tb_text.Hide()
            
        
        if self._job_key.IsPausable():
            
            self._pause_button.Show()
            
        else:
            
            self._pause_button.Hide()
            
        
        if self._job_key.IsCancellable():
            
            self._cancel_button.Show()
            
        else:
            
            self._cancel_button.Hide()
            
        
    
class PopupMessageManager( wx.Frame ):
    
    def __init__( self, parent ):
        
        wx.Frame.__init__( self, parent, style = wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_NONE )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
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
        
        size_and_position_needed = False
        
        num_messages_displayed = self._message_vbox.GetItemCount()
        
        self._pending_job_keys = [ job_key for job_key in self._pending_job_keys if not job_key.IsDeleted() ]
        
        if len( self._pending_job_keys ) > 0 and num_messages_displayed < self._max_messages_to_display:
            
            job_key = self._pending_job_keys.pop( 0 )
            
            window = PopupMessage( self, job_key )
            
            window.Update()
            
            self._message_vbox.AddF( window, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            size_and_position_needed = True
            
        
        dismiss_shown_before = self._dismiss_all.IsShown()
        
        num_messages_pending = len( self._pending_job_keys )
        
        if num_messages_pending > 0:
            
            self._dismiss_all.SetNumMessages( num_messages_pending )
            
            self._dismiss_all.Show()
            
        else:
            
            self._dismiss_all.Hide()
            
        
        if self._dismiss_all.IsShown() != dismiss_shown_before:
            
            size_and_position_needed = True
            
        
        if size_and_position_needed:
            
            self._SizeAndPositionAndShow()
            
        
    
    def _DisplayingError( self ):
        
        sizer_items = self._message_vbox.GetChildren()
        
        for sizer_item in sizer_items:
            
            message_window = sizer_item.GetWindow()
            
            job_key = message_window.GetJobKey()
            
            if job_key.HasVariable( 'popup_traceback' ):
                
                return True
                
            
        
        return False
        
    
    def _SizeAndPositionAndShow( self ):
        
        try:
            
            parent = self.GetParent()
            
            # changing show status while parent iconised in Windows leads to grey window syndrome
            going_to_bug_out_at_hide_or_show = HC.PLATFORM_WINDOWS and parent.IsIconized()
            
            new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            if new_options.GetBoolean( 'hide_message_manager_on_gui_iconise' ):
                
                if parent.IsIconized():
                    
                    self.Hide()
                    
                    return
                    
                
            
            current_focus_tlp = wx.GetTopLevelParent( wx.Window.FindFocus() )
            
            gui_is_active = current_focus_tlp in ( self, parent )
            
            if new_options.GetBoolean( 'hide_message_manager_on_gui_deactive' ):
                
                if gui_is_active:
                    
                    # gui can have focus even while minimised to the taskbar--let's not show in this case
                    if not self.IsShown() and parent.IsIconized():
                        
                        return
                        
                    
                else:
                    
                    if not going_to_bug_out_at_hide_or_show:
                        
                        self.Hide()
                        
                    
                    return
                    
                
            
            num_messages_displayed = self._message_vbox.GetItemCount()
            
            there_is_stuff_to_display = num_messages_displayed > 0
            
            if there_is_stuff_to_display:
                
                best_size = self.GetBestSize()
                
                if best_size != self.GetSize():
                    
                    self.Fit()
                    
                
                ( parent_width, parent_height ) = parent.GetClientSize()
                
                ( my_width, my_height ) = self.GetClientSize()
                
                my_x = ( parent_width - my_width ) - 25
                my_y = ( parent_height - my_height ) - 5
                
                my_position = parent.ClientToScreenXY( my_x, my_y )
                
                if my_position != self.GetPosition():
                    
                    self.SetPosition( parent.ClientToScreenXY( my_x, my_y ) )
                    
                    
                
                # Unhiding tends to raise the main gui tlp, which is annoying if a media viewer window has focus
                show_is_not_annoying = gui_is_active or self._DisplayingError()
                
                ok_to_show = show_is_not_annoying and not going_to_bug_out_at_hide_or_show
                
                if ok_to_show:
                    
                    was_hidden = not self.IsShown()
                    
                    self.Show()
                    
                    if was_hidden:
                        
                        self.Layout()
                        
                    
                
            else:
                
                if not going_to_bug_out_at_hide_or_show:
                    
                    self.Hide()
                    
                
            
        except:
            
            text = 'The popup message manager experienced a fatal error and will now stop working! Please restart the client as soon as possible! If this keeps happening, please email the details and your client.log to the hydrus developer.'
            
            HydrusData.Print( text )
            
            HydrusData.Print( traceback.format_exc() )
            
            wx.MessageBox( text )
            
            self._timer.Stop()
            
            self.CleanBeforeDestroy()
            
            self.Destroy()
            
        
    
    def AddMessage( self, job_key ):
        
        try:
            
            self._pending_job_keys.append( job_key )
            
            self._CheckPending()
            
        except:
            
            HydrusData.Print( traceback.format_exc() )
            
        
    
    def CleanBeforeDestroy( self ):
        
        for job_key in self._pending_job_keys:
            
            if job_key.IsCancellable():
                
                job_key.Cancel()
                
            
        
        sizer_items = self._message_vbox.GetChildren()
        
        for sizer_item in sizer_items:
            
            message_window = sizer_item.GetWindow()
            
            job_key = message_window.GetJobKey()
            
            if job_key.IsCancellable():
                
                job_key.Cancel()
                
            
        
        sys.excepthook = self._old_excepthook
        
        HydrusData.ShowException = self._old_show_exception
        
    
    def Dismiss( self, window ):
        
        self._message_vbox.Detach( window )
        
        # OS X segfaults if this is instant
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
        
    
    def MakeSureEverythingFits( self ):
        
        self._SizeAndPositionAndShow()
        
    
    def TIMEREvent( self, event ):
        
        try:
            
            if HydrusGlobals.view_shutdown:
                
                self._timer.Stop()
                
                self.Destroy()
                
                return
                
            
            sizer_items = self._message_vbox.GetChildren()
            
            for sizer_item in sizer_items:
                
                message_window = sizer_item.GetWindow()
                
                if message_window.IsDeleted():
                    
                    message_window.TryToDismiss()
                    
                    break
                    
                else:
                    
                    message_window.Update()
                    
                
            
            self._SizeAndPositionAndShow()
            
        except wx.PyDeadObjectError:
            
            self._timer.Stop()
            
        except:
            
            self._timer.Stop()
            
            raise
            
        
    
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
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        name = service.GetName()
        
        self.SetToolTipString( name )
        
        HydrusGlobals.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HydrusGlobals.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
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
        
        HydrusGlobals.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HydrusGlobals.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
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
        submenu.Append( self.ID_REGEX_FILENAME, r'filename - (?<=' + os.path.sep.encode( 'string_escape' ) + r')[^' + os.path.sep.encode( 'string_escape' ) + ']*?(?=\..*$)' )
        
        menu.AppendMenu( -1, 'regex components', submenu )
        
        submenu = wx.Menu()
        
        submenu.Append( self.ID_REGEX_MANAGE_FAVOURITES, 'manage favourites' )
        
        submenu.AppendSeparator()
        
        for ( index, ( regex_phrase, description ) ) in enumerate( HC.options[ 'regex_favourites' ] ):
            
            menu_id = index + 100
            
            submenu.Append( menu_id, description )
            
        
        menu.AppendMenu( -1, 'favourites', submenu )
        
        HydrusGlobals.client_controller.PopupMenu( self, menu )
        
    
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
        elif id == self.ID_REGEX_FILENAME: phrase = '(?<=' + os.path.sep.encode( 'string_escape' ) + r')[^' + os.path.sep.encode( 'string_escape' ) + ']*?(?=\..*$)'
        elif id == self.ID_REGEX_MANAGE_FAVOURITES:
            
            import ClientGUIDialogsManage
            
            with ClientGUIDialogsManage.DialogManageRegexFavourites( self.GetTopLevelParent() ) as dlg:
                
                dlg.ShowModal()
                
            
        elif id in self.ID_REGEX_FAVOURITES:
            
            index = id - 100
            
            ( phrase, description ) = HC.options[ 'regex_favourites' ][ index ]
            
        else: event.Skip()
        
        if phrase is not None: HydrusGlobals.client_controller.pub( 'clipboard', 'text', phrase )
        
    
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
            
        
    
class SaneListCtrl( wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin ):
    
    def __init__( self, parent, height, columns, delete_key_callback = None, activation_callback = None ):
        
        num_columns = len( columns )
        
        wx.ListCtrl.__init__( self, parent, style = wx.LC_REPORT )
        ListCtrlAutoWidthMixin.__init__( self )
        ColumnSorterMixin.__init__( self, num_columns )
        
        self.itemDataMap = {}
        self._data_indices_to_sort_indices = {}
        self._data_indices_to_sort_indices_dirty = False
        self._next_data_index = 0
        
        resize_column = 1
        
        for ( i, ( name, width ) ) in enumerate( columns ):
            
            self.InsertColumn( i, name, width = width )
            
            if width == -1:
                
                resize_column = i + 1
                
            
        
        self.setResizeColumn( resize_column )
        
        self.SetMinSize( ( -1, height ) )
        
        self._delete_key_callback = delete_key_callback
        self._activation_callback = activation_callback
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        self.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventItemActivated )
        
        self.Bind( wx.EVT_LIST_COL_BEGIN_DRAG, self.EventBeginColDrag )
        
    
    _GetDataIndex = wx.ListCtrl.GetItemData
    
    def _GetIndexFromDataIndex( self, data_index ):
        
        if self._data_indices_to_sort_indices_dirty:
            
            self._data_indices_to_sort_indices = { self._GetDataIndex( index ) : index for index in range( self.GetItemCount() ) }
            
            self._data_indices_to_sort_indices_dirty = False
            
        
        try:
            
            return self._data_indices_to_sort_indices[ data_index ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'Data not found!' )
            
        
    
    def Append( self, display_tuple, sort_tuple ):
        
        index = wx.ListCtrl.Append( self, display_tuple )
        
        data_index = self._next_data_index
        
        self.SetItemData( index, data_index )
        
        self.itemDataMap[ data_index ] = list( sort_tuple )
        self._data_indices_to_sort_indices[ data_index ] = index
        
        self._next_data_index += 1
        
    
    def DeleteItem( self, *args, **kwargs ):
        
        wx.ListCtrl.DeleteItem( self, *args, **kwargs )
        
        self._data_indices_to_sort_indices_dirty = True
        
    
    def EventBeginColDrag( self, event ):
        
        # resizeCol is not zero-indexed
        
        if event.GetColumn() == self._resizeCol - 1:
            
            last_column = self.GetColumnCount()
            
            if self._resizeCol != last_column:
                
                self.setResizeColumn( last_column )
                
            else:
                
                event.Veto()
                
                return
                
            
        
        event.Skip()
        
    
    def EventItemActivated( self, event ):
        
        if self._activation_callback is not None:
            
            self._activation_callback()
            
        else:
            
            event.Skip()
            
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in CC.DELETE_KEYS:
            
            if self._delete_key_callback is not None:
                
                self._delete_key_callback()
                
            
        elif event.KeyCode in ( ord( 'A' ), ord( 'a' ) ) and event.CmdDown():
            
            self.SelectAll()
            
        else:
            
            event.Skip()
            
        
    
    def GetAllSelected( self ):
        
        indices = []
        
        i = self.GetFirstSelected()
        
        while i != -1:
            
            indices.append( i )
            
            i = self.GetNextSelected( i )
            
        
        return indices
        
    
    def GetClientData( self, index = None ):
        
        if index is None:
            
            data_indicies = [ self._GetDataIndex( index ) for index in range( self.GetItemCount() ) ]
            
            datas = [ tuple( self.itemDataMap[ data_index ] ) for data_index in data_indicies ]
            
            return datas
            
        else:
            
            data_index = self._GetDataIndex( index )
            
            return tuple( self.itemDataMap[ data_index ] )
            
        
    
    def GetIndexFromClientData( self, data, column_index = None ):
        
        for index in range( self.GetItemCount() ):
            
            client_data = self.GetClientData( index )
            
            if column_index is None:
                
                comparison_data = client_data
                
            else:
                
                comparison_data = client_data[ column_index ]
                
            
            if comparison_data == data:
                
                return index
                
            
        
        raise HydrusExceptions.DataMissing( 'Data not found!' )
        
    
    def GetSecondarySortValues( self, col, key1, key2 ):
        
        # This overrides the ColumnSortedMixin. Just spam the whole tuple back.
        
        return ( self.itemDataMap[ key1 ], self.itemDataMap[ key2 ] )
        
    
    def HasClientData( self, data, column_index = None ):
        
        try:
            
            index = self.GetIndexFromClientData( data, column_index )
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def GetListCtrl( self ):
        
        return self
        
    
    def GetSelectedClientData( self ):
        
        indices = self.GetAllSelected()
        
        results = []
        
        for index in indices:
            
            results.append( self.GetClientData( index ) )
            
        
        return results
        
    
    def OnSortOrderChanged( self ):
        
        self._data_indices_to_sort_indices_dirty = True
        
    
    def RemoveAllSelected( self ):
        
        indices = self.GetAllSelected()
        
        indices.reverse() # so we don't screw with the indices of deletees below
        
        for index in indices:
            
            self.DeleteItem( index )
            
        
    
    def SelectAll( self ):
        
        currently_selected = set( self.GetAllSelected() )
        
        currently_not_selected = [ index for index in range( self.GetItemCount() ) if index not in currently_selected ]
        
        for index in currently_not_selected:
            
            self.Select( index )
            
        
    
    def UpdateRow( self, index, display_tuple, sort_tuple ):
        
        column = 0
        
        for value in display_tuple:
            
            self.SetStringItem( index, column, value )
            
            column += 1
            
        
        data_index = self._GetDataIndex( index )
        
        self.itemDataMap[ data_index ] = list( sort_tuple )
        
    
class SaneListCtrlForSingleObject( SaneListCtrl ):
    
    def __init__( self, *args, **kwargs ):
        
        # this could one day just take column parameters that the user can pick
        # it could just take obj in append or whatever and generate column tuples off that
        
        self._data_indices_to_objects = {}
        self._objects_to_data_indices = {}
        
        SaneListCtrl.__init__( self, *args, **kwargs )
        
    
    def Append( self, display_tuple, sort_tuple, obj ):
        
        self._data_indices_to_objects[ self._next_data_index ] = obj
        self._objects_to_data_indices[ obj ] = self._next_data_index
        
        SaneListCtrl.Append( self, display_tuple, sort_tuple )
        
    
    def GetClientData( self, index = None ):
        
        if index is None:
            
            data_indicies = [ self._GetDataIndex( index ) for index in range( self.GetItemCount() ) ]
            
            datas = [ self._data_indices_to_objects[ data_index ] for data_index in data_indicies ]
            
            return datas
            
        else:
            
            data_index = self._GetDataIndex( index )
            
            return self._data_indices_to_objects[ data_index ]
            
        
    
    def GetIndexFromClientData( self, obj ):
        
        try:
            
            data_index = self._objects_to_data_indices[ obj ]
            
            index = self._GetIndexFromDataIndex( data_index )
            
            return index
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'Data not found!' )
            
        
    
    def HasClientData( self, data ):
        
        try:
            
            index = self.GetIndexFromClientData( data )
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def SetNonDupeName( self, obj ):
        
        # when column population is handled here, we can tuck this into normal append/update calls internally
        
        name = obj.GetName()
        
        current_names = { obj.GetName() for obj in self.GetClientData() }
        
        if name in current_names:
            
            i = 1
            
            original_name = name
            
            while name in current_names:
                
                name = original_name + ' (' + str( i ) + ')'
                
                i += 1
                
            
            obj.SetName( name )
            
        
    
    def UpdateRow( self, index, display_tuple, sort_tuple, obj ):
        
        SaneListCtrl.UpdateRow( self, index, display_tuple, sort_tuple )
        
        data_index = self._GetDataIndex( index )
        
        self._data_indices_to_objects[ data_index ] = obj
        self._objects_to_data_indices[ obj ] = data_index
        
    
class SeedCacheControl( SaneListCtrlForSingleObject ):
    
    def __init__( self, parent, seed_cache ):
        
        height = 300
        columns = [ ( 'source', -1 ), ( 'status', 90 ), ( 'added', 150 ), ( 'last modified', 150 ), ( 'note', 200 ) ]
        
        SaneListCtrlForSingleObject.__init__( self, parent, height, columns )
        
        self._seed_cache = seed_cache
        
        for seed in self._seed_cache.GetSeeds():
            
            self._AddSeed( seed )
            
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        HydrusGlobals.client_controller.sub( self, 'NotifySeedUpdated', 'seed_cache_seed_updated' )
        
    
    def _AddSeed( self, seed ):
        
        sort_tuple = self._seed_cache.GetSeedInfo( seed )
        
        ( display_tuple, sort_tuple ) = self._GetListCtrlTuples( seed )
        
        self.Append( display_tuple, sort_tuple, seed )
        
    
    def _GetListCtrlTuples( self, seed ):
        
        sort_tuple = self._seed_cache.GetSeedInfo( seed )
        
        ( seed, status, added_timestamp, last_modified_timestamp, note ) = sort_tuple
        
        pretty_seed = HydrusData.ToUnicode( seed )
        pretty_status = CC.status_string_lookup[ status ]
        pretty_added = HydrusData.ConvertTimestampToPrettyAgo( added_timestamp )
        pretty_modified = HydrusData.ConvertTimestampToPrettyAgo( last_modified_timestamp )
        pretty_note = note.split( os.linesep )[0]
        
        display_tuple = ( pretty_seed, pretty_status, pretty_added, pretty_modified, pretty_note )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedNotes( self ):
        
        notes = []
        
        for seed in self.GetSelectedClientData():
            
            ( seed, status, added_timestamp, last_modified_timestamp, note ) = self._seed_cache.GetSeedInfo( seed )
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( notes )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedSeeds( self ):
        
        seeds = self.GetSelectedClientData()
        
        if len( seeds ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( seeds )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _SetSelected( self, status_to_set ):
        
        seeds_to_reset = self.GetSelectedClientData()
        
        for seed in seeds_to_reset:
            
            self._seed_cache.UpdateSeedStatus( seed, status_to_set )
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'copy_seed_notes': self._CopySelectedNotes()
            elif command == 'copy_seeds': self._CopySelectedSeeds()
            elif command == 'set_seed_unknown': self._SetSelected( CC.STATUS_UNKNOWN )
            elif command == 'set_seed_skipped': self._SetSelected( CC.STATUS_SKIPPED )
            else: event.Skip()
            
        
    
    def EventShowMenu( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_seeds' ), 'copy sources' )
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_seed_notes' ), 'copy notes' )
        
        menu.AppendSeparator()
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'set_seed_skipped' ), 'skip' )
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'set_seed_unknown' ), 'try again' )
        
        HydrusGlobals.client_controller.PopupMenu( self, menu )
        
    
    def NotifySeedUpdated( self, seed ):
        
        if self._seed_cache.HasSeed( seed ):
            
            if self.HasClientData( seed ):
                
                index = self.GetIndexFromClientData( seed )
                
                ( display_tuple, sort_tuple ) = self._GetListCtrlTuples( seed )
                
                self.UpdateRow( index, display_tuple, sort_tuple, seed )
                
            else:
                
                self._AddSeed( seed )
                
            
        else:
            
            if self.HasClientData( seed ):
                
                index = self.GetIndexFromClientData( seed )
                
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
        
    
( TimeDeltaEvent, EVT_TIME_DELTA ) = wx.lib.newevent.NewCommandEvent()

class TimeDeltaButton( wx.Button ):
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False ):
        
        wx.Button.__init__( self, parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        
        self._value = self._min
        
        self.SetLabelText( 'initialising' )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def _RefreshLabel( self ):
        
        text_components = []
        
        value = self._value
        
        if self._show_days:
            
            days = value / 86400
            
            if days > 0:
                
                text_components.append( HydrusData.ConvertIntToPrettyString( days ) + ' days' )
                
            
            value %= 86400
            
        
        if self._show_hours:
            
            hours = value / 3600
            
            if hours > 0:
                
                text_components.append( HydrusData.ConvertIntToPrettyString( hours ) + ' hours' )
                
            
            value %= 3600
            
        
        if self._show_minutes:
            
            minutes = value / 60
            
            if minutes > 0:
                
                text_components.append( HydrusData.ConvertIntToPrettyString( minutes ) + ' minutes' )
                
            
            value %= 60
            
        
        if self._show_seconds:
            
            if value > 0 or len( text_components ) == 0:
                
                text_components.append( HydrusData.ConvertIntToPrettyString( value ) + ' seconds' )
                
            
        
        text = ' '.join( text_components )
        
        self.SetLabelText( text )
        
    
    def EventButton( self, event ):
        
        import ClientGUIDialogs
        
        with ClientGUIDialogs.DialogInputTimeDelta( self, self._value, min = self._min, days = self._show_days, hours = self._show_hours, minutes = self._show_minutes, seconds = self._show_seconds ) as dlg:
            
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
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False ):
        
        wx.Panel.__init__( self, parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if self._show_days:
            
            self._days = wx.SpinCtrl( self, min = 0, max = 360, size = ( 50, -1 ) )
            self._days.Bind( wx.EVT_SPINCTRL, self.EventSpin )
            
            hbox.AddF( self._days, CC.FLAGS_VCENTER )
            hbox.AddF( wx.StaticText( self, label = 'days' ), CC.FLAGS_VCENTER )
            
        
        if self._show_hours:
            
            self._hours = wx.SpinCtrl( self, min = 0, max = 23, size = ( 45, -1 ) )
            self._hours.Bind( wx.EVT_SPINCTRL, self.EventSpin )
            
            hbox.AddF( self._hours, CC.FLAGS_VCENTER )
            hbox.AddF( wx.StaticText( self, label = 'hours' ), CC.FLAGS_VCENTER )
            
        
        if self._show_minutes:
            
            self._minutes = wx.SpinCtrl( self, min = 0, max = 59, size = ( 45, -1 ) )
            self._minutes.Bind( wx.EVT_SPINCTRL, self.EventSpin )
            
            hbox.AddF( self._minutes, CC.FLAGS_VCENTER )
            hbox.AddF( wx.StaticText( self, label = 'minutes' ), CC.FLAGS_VCENTER )
            
        
        if self._show_seconds:
            
            self._seconds = wx.SpinCtrl( self, min = 0, max = 59, size = ( 45, -1 ) )
            self._seconds.Bind( wx.EVT_SPINCTRL, self.EventSpin )
            
            hbox.AddF( self._seconds, CC.FLAGS_VCENTER )
            hbox.AddF( wx.StaticText( self, label = 'seconds' ), CC.FLAGS_VCENTER )
            
        
        self.SetSizer( hbox )
        
    
    def EventSpin( self, event ):
        
        value = self.GetValue()
        
        if value < self._min:
            
            self.SetValue( self._min )
            
        
        new_event = TimeDeltaEvent( 0 )
        
        wx.PostEvent( self, new_event )
        
    
    def GetValue( self ):
        
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
    
class WaitingPolitelyStaticText( wx.StaticText ):
    
    def __init__( self, parent, page_key ):
        
        wx.StaticText.__init__( self, parent, label = 'ready  ' )
        
        self._page_key = page_key
        self._waiting = False
        
        HydrusGlobals.client_controller.sub( self, 'SetWaitingPolitely', 'waiting_politely' )
        
        self.SetWaitingPolitely( self._page_key, False )
        
    
    def SetWaitingPolitely( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._waiting = value
            
            if self._waiting:
                
                self.SetLabelText( 'waiting' )
                self.SetToolTipString( 'waiting before attempting another download' )
                
            else:
                
                self.SetLabelText( 'ready  ' )
                self.SetToolTipString( 'ready to download' )
                
            
        
    
class WaitingPolitelyTrafficLight( BufferedWindow ):
    
    def __init__( self, parent, page_key ):
        
        BufferedWindow.__init__( self, parent, size = ( 19, 19 ) )
        
        self._page_key = page_key
        self._waiting = False
        
        HydrusGlobals.client_controller.sub( self, 'SetWaitingPolitely', 'waiting_politely' )
        
        self.SetWaitingPolitely( self._page_key, False )
        
    
    def _Draw( self, dc ):
        
        dc.SetBackground( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) ) )
        
        dc.Clear()
        
        if self._waiting:
            
            dc.SetBrush( wx.Brush( wx.Colour( 250, 190, 77 ) ) )
            
        else:
            
            dc.SetBrush( wx.Brush( wx.Colour( 77, 250, 144 ) ) )
            
        
        dc.SetPen( wx.Pen( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNSHADOW ) ) )
        
        dc.DrawCircle( 9, 9, 7 )
        
    
    def SetWaitingPolitely( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._waiting = value
            
            if self._waiting:
                
                self.SetToolTipString( 'waiting before attempting another download' )
                
            else:
                
                self.SetToolTipString( 'ready to download' )
                
            
            self._dirty = True
            
            self.Refresh()
            
        
    
def GetWaitingPolitelyControl( parent, page_key ):
    
    new_options = HydrusGlobals.client_controller.GetNewOptions()
    
    if new_options.GetBoolean( 'waiting_politely_text' ):
        
        return WaitingPolitelyStaticText( parent, page_key )
        
    else:
        
        return WaitingPolitelyTrafficLight( parent, page_key )
        
    
