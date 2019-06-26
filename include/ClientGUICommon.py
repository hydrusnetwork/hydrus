from . import ClientCaches
from . import ClientData
from . import ClientConstants as CC
from . import ClientGUIFunctions
from . import ClientGUIMenus
from . import ClientGUITopLevelWindows
from . import ClientMedia
from . import ClientPaths
from . import ClientRatings
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusText
import os
import re
import sys
import threading
import time
import traceback
import wx
import wx.lib.newevent

ID_TIMER_ANIMATED = wx.NewId()
ID_TIMER_SLIDESHOW = wx.NewId()
ID_TIMER_MEDIA_INFO_DISPLAY = wx.NewId()

def WrapInGrid( parent, rows, expand_text = False ):
    
    gridbox = wx.FlexGridSizer( 2 )
    
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
        
        st = BetterStaticText( parent, text )
        
        if isinstance( control, wx.Sizer ):
            
            cflags = sizer_flags
            
        else:
            
            cflags = control_flags
            
            if control.GetToolTipText() != '':
                
                st.SetToolTip( control.GetToolTipText() )
                
            
        
        gridbox.Add( st, text_flags )
        gridbox.Add( control, cflags )
        
    
    return gridbox
    
def WrapInText( control, parent, text, colour = None ):
    
    hbox = wx.BoxSizer( wx.HORIZONTAL )
    
    st = BetterStaticText( parent, text )
    
    if colour is not None:
        
        st.SetForegroundColour( colour )
        
    
    hbox.Add( st, CC.FLAGS_VCENTER )
    hbox.Add( control, CC.FLAGS_EXPAND_BOTH_WAYS )
    
    return hbox
    
class ShortcutAwareToolTipMixin( object ):
    
    def __init__( self, tt_callable ):
        
        self._tt_callable = tt_callable
        
        self._tt = ''
        self._simple_shortcut_command = None
        
        HG.client_controller.sub( self, 'NotifyNewShortcuts', 'notify_new_shortcuts_gui' )
        
    
    def _RefreshToolTip( self ):
        
        tt = self._tt
        
        if self._simple_shortcut_command is not None:
            
            tt += os.linesep * 2
            tt += '----------'
            
            names_to_shortcuts = HG.client_controller.shortcuts_manager.GetNamesToShortcuts( self._simple_shortcut_command )
            
            if len( names_to_shortcuts ) > 0:
                
                names = list( names_to_shortcuts.keys() )
                
                names.sort()
                
                for name in names:
                    
                    shortcuts = names_to_shortcuts[ name ]
                    
                    shortcut_strings = [ shortcut.ToString() for shortcut in shortcuts ]
                    
                    shortcut_strings.sort()
                    
                    tt += os.linesep * 2
                    
                    tt += ', '.join( shortcut_strings )
                    tt += os.linesep
                    tt += '({}->{})'.format( name, self._simple_shortcut_command )
                    
                
            else:
                
                tt += os.linesep * 2
                
                tt += 'no shortcuts set'
                tt += os.linesep
                tt += '({})'.format( self._simple_shortcut_command )
                
            
        
        self._tt_callable( tt )
        
    
    def NotifyNewShortcuts( self ):
        
        self._RefreshToolTip()
        
    
    def SetToolTipWithShortcuts( self, tt, simple_shortcut_command ):
        
        self._tt = tt
        self._simple_shortcut_command = simple_shortcut_command
        
        self._RefreshToolTip()
        
    
class BetterBitmapButton( wx.BitmapButton, ShortcutAwareToolTipMixin ):
    
    def __init__( self, parent, bitmap, func, *args, **kwargs ):
        
        wx.BitmapButton.__init__( self, parent, bitmap = bitmap )
        ShortcutAwareToolTipMixin.__init__( self, self.SetToolTip )
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        self._func( *self._args,  **self._kwargs )
        
    
# this hands out additional space according to proportion, but only on the pixels beyond min size
# so two items with weight 1 that have min size 100 & 200 will have min size of 300, not 400
# given a size of 400, they will size 150 & 250, sharing the 'additional' pixels
# I may be stupid, but I cannot see a vanilla wx flag or layout method that does this
class BetterBoxSizer( wx.BoxSizer ):
    
    def CalcMin( self ):
        
        horizontal_total_width = 0
        horizontal_max_height = 0
        vertical_max_width = 0
        vertical_total_height = 0
        
        for sizer_item in self.GetChildren():
            
            if not sizer_item.IsShown():
                
                continue
                
            
            ( width, height ) = sizer_item.CalcMin()
            
            horizontal_total_width += width
            horizontal_max_height = max( horizontal_max_height, height )
            vertical_max_width = max( vertical_max_width, width )
            vertical_total_height += height
            
        
        if self.GetOrientation() == wx.HORIZONTAL:
            
            return wx.Size( horizontal_total_width, horizontal_max_height )
            
        else:
            
            return wx.Size( vertical_max_width, vertical_total_height )
            
        
    
    def RecalcSizes( self ):
        
        my_orientation = self.GetOrientation()
        
        ( x, y ) = self.GetPosition()
        ( my_width, my_height ) = self.GetSize()
        
        ( min_my_width, min_my_height ) = self.CalcMin()
        
        extra_height = my_height - min_my_height
        extra_width = my_width - min_my_width
        
        i_am_too_small = ( my_orientation == wx.HORIZONTAL and extra_width < 0 ) or ( my_orientation == wx.VERTICAL and extra_height < 0 )
        
        total_proportion = sum( ( sizer_item.GetProportion() for sizer_item in self.GetChildren() if sizer_item.IsShown() ) )
        
        for sizer_item in self.GetChildren():
            
            if not sizer_item.IsShown():
                
                continue
                
            
            ( sizer_min_width, sizer_min_height ) = sizer_item.CalcMin()
            
            flag = sizer_item.GetFlag()
            
            #
            
            if wx.EXPAND & flag:
                
                horizontal_height = my_height
                vertical_width = my_width
                
            else:
                
                horizontal_height = sizer_min_height
                vertical_width = sizer_min_width
                
            
            #
            
            proportion = sizer_item.GetProportion()
            
            if proportion == 0 or i_am_too_small:
                
                horizontal_width = sizer_min_width
                vertical_height = sizer_min_height
                
            else:
                
                share_of_extra_pixels = proportion / total_proportion
                
                horizontal_width = sizer_min_width + int( share_of_extra_pixels * extra_width )
                vertical_height = sizer_min_height + int( share_of_extra_pixels * extra_height )
                
            
            #
            
            x_offset = 0
            y_offset = 0
            
            if my_orientation == wx.HORIZONTAL:
                
                if wx.ALIGN_BOTTOM & flag:
                    
                    y_offset = my_height - horizontal_height
                    
                elif wx.ALIGN_CENTER_VERTICAL & flag:
                    
                    y_offset = ( my_height - horizontal_height ) // 2
                    
                
            else:
                
                if wx.ALIGN_RIGHT & flag:
                    
                    x_offset = my_width - vertical_width
                    
                elif wx.ALIGN_CENTER_HORIZONTAL & flag:
                    
                    x_offset = ( my_width - vertical_width ) // 2
                    
                
            
            #
            
            pos = wx.Point( x + x_offset, y + y_offset )
            
            if my_orientation == wx.HORIZONTAL:
                
                size = wx.Size( horizontal_width, horizontal_height )
                
                x += horizontal_width
                
            else:
                
                size = wx.Size( vertical_width, vertical_height )
                
                y += vertical_height
                
            
            sizer_item.SetDimension( pos, size )
            
        
    
class BetterButton( wx.Button, ShortcutAwareToolTipMixin ):
    
    def __init__( self, parent, label, func, *args, **kwargs ):
        
        wx.Button.__init__( self, parent, style = wx.BU_EXACTFIT )
        ShortcutAwareToolTipMixin.__init__( self, self.SetToolTip )
        
        self.SetLabelText( label )
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        self._func( *self._args,  **self._kwargs )
        
    
class BetterCheckListBox( wx.CheckListBox ):
    
    def __init__( self, parent ):
        
        wx.CheckListBox.__init__( self, parent, style = wx.LB_EXTENDED )
        
    
    def GetChecked( self ):
        
        result = [ self.GetClientData( index ) for index in self.GetCheckedItems() ]
        
        return result
        
    
    def SetCheckedData( self, datas ):
        
        for index in range( self.GetCount() ):
            
            data = self.GetClientData( index )
            
            check_it = data in datas
            
            self.Check( index, check_it )
            
        
    
class BetterChoice( wx.Choice ):
    
    def Append( self, display_string, client_data ):
        
        wx.Choice.Append( self, display_string, client_data )
        
        if self.GetCount() == 1:
            
            self.Select( 0 )
            
        
    
    def GetChoice( self ):
        
        selection = self.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            return self.GetClientData( selection )
            
        elif self.GetCount() > 0:
            
            return self.GetClientData( 0 )
            
        else:
            
            return None
            
        
    
    def SelectClientData( self, client_data ):
        
        for i in range( self.GetCount() ):
            
            if client_data == self.GetClientData( i ):
                
                self.Select( i )
                
                return
                
            
        
        if self.GetCount() > 0:
            
            self.Select( 0 )
            
        
    
class BetterColourControl( wx.ColourPickerCtrl ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.ColourPickerCtrl.__init__( self, *args, **kwargs )
        
        self.GetPickerCtrl().Bind( wx.EVT_RIGHT_DOWN, self.EventMenu )
        
    
    def _ImportHexFromClipboard( self ):
        
        try:
            
            import_string = HG.client_controller.GetClipboardText()
            
        except Exception as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        if import_string.startswith( '#' ):
            
            import_string = import_string[1:]
            
        
        import_string = '#' + re.sub( '[^0-9a-fA-F]', '', import_string )
        
        if len( import_string ) != 7:
            
            wx.MessageBox( 'That did not appear to be a hex string!' )
            
            return
            
        
        try:
            
            colour = wx.Colour( import_string )
            
        except Exception as e:
            
            wx.MessageBox( str( e ) )
            
            HydrusData.ShowException( e )
            
            return
            
        
        self.SetColour( colour )
        
    
    def EventMenu( self, event ):
        
        menu = wx.Menu()
        
        hex_string = self.GetColour().GetAsString( wx.C2S_HTML_SYNTAX )
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'copy ' + hex_string + ' to the clipboard', 'Copy the current colour to the clipboard.', HG.client_controller.pub, 'clipboard', 'text', hex_string )
        ClientGUIMenus.AppendMenuItem( self, menu, 'import a hex colour from the clipboard', 'Look at the clipboard for a colour in the format #FF0000, and set the colour.', self._ImportHexFromClipboard )
        
        HG.client_controller.PopupMenu( self, menu )
        
    
class BetterNotebook( wx.Notebook ):
    
    def _ShiftSelection( self, delta ):
        
        existing_selection = self.GetSelection()
        
        if existing_selection != wx.NOT_FOUND:
            
            new_selection = ( existing_selection + delta ) % self.GetPageCount()
            
            if new_selection != existing_selection:
                
                self.SetSelection( new_selection )
                
            
        
    
    def GetPages( self ):
        
        return [ self.GetPage( i ) for i in range( self.GetPageCount() ) ]
        
    
    def SelectLeft( self ):
        
        self._ShiftSelection( -1 )
        
    
    def SelectPage( self, page ):
        
        for i in range( self.GetPageCount() ):
            
            if self.GetPage( i ) == page:
                
                self.SetSelection( i )
                
                return
                
            
        
    
    def SelectRight( self ):
        
        self._ShiftSelection( 1 )
        
    
class BetterRadioBox( wx.RadioBox ):
    
    def __init__( self, *args, **kwargs ):
        
        self._indices_to_data = { i : data for ( i, ( s, data ) ) in enumerate( kwargs[ 'choices' ] ) }
        
        kwargs[ 'choices' ] = [ s for ( s, data ) in kwargs[ 'choices' ] ]
        
        wx.RadioBox.__init__( self, *args, **kwargs )
        
    
    def GetChoice( self ):
        
        index = self.GetSelection()
        
        return self._indices_to_data[ index ]
        
    
class BetterStaticText( wx.StaticText ):
    
    def __init__( self, parent, label = None, tooltip_label = False, **kwargs ):
        
        wx.StaticText.__init__( self, parent, **kwargs )
        
        self._tooltip_label = tooltip_label
        
        if 'style' in kwargs and kwargs[ 'style' ] & wx.ST_ELLIPSIZE_END:
            
            self._tooltip_label = True
            
        
        self._last_set_text = '' # we want a separate copy since the one we'll send to the st will be wrapped and have additional '\n's
        
        self._wrap_width = None
        
        if label is not None:
            
            # to escape mnemonic '&' swallowing
            self.SetLabelText( label )
            
        
        # wx.lib.wordwrap mite be cool here to pre-calc the wrapped text, which may be more reliable in init than wrap, but it needs a dc
        
    
    def SetLabelText( self, text ):
        
        if text != self._last_set_text:
            
            self._last_set_text = text
            
            wx.StaticText.SetLabelText( self, text )
            
            if self._wrap_width is not None:
                
                self.Wrap( self._wrap_width )
                
            
            if self._tooltip_label:
                
                self.SetToolTip( text )
                
            
        
    
    def SetWrapWidth( self, wrap_width ):
        
        self._wrap_width = wrap_width
        
        if self._wrap_width is not None:
            
            self.Wrap( self._wrap_width )
            
        
    
class BetterHyperLink( BetterStaticText ):
    
    def __init__( self, parent, label, url ):
        
        BetterStaticText.__init__( self, parent, label )
        
        self._url = url
        
        self.SetCursor( wx.Cursor( wx.CURSOR_HAND ) )
        self.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HOTLIGHT ) )
        
        font = self.GetFont()
        
        font.SetUnderlined( True )
        
        self.SetFont( font )
        
        self.SetToolTip( self._url )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventClick )
        
    
    def EventClick( self, event ):
        
        ClientPaths.LaunchURLInWebBrowser( self._url )
        
    
class BufferedWindow( wx.Window ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Window.__init__( self, *args, **kwargs )
        
        if 'size' in kwargs:
            
            ( x, y ) = kwargs[ 'size' ]
            
            self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( x, y, 24 )
            
        else:
            
            self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( 20, 20, 24 )
            
        
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
            
            self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( my_width, my_height, 24 )
            
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
        
    
class CheckboxCollect( wx.ComboCtrl ):
    
    def __init__( self, parent, management_controller = None ):
        
        wx.ComboCtrl.__init__( self, parent, style = wx.CB_READONLY )
        
        self._management_controller = management_controller
        
        if self._management_controller is not None and self._management_controller.HasVariable( 'media_collect' ):
            
            self._collect_by = self._management_controller.GetVariable( 'media_collect' )
            
        else:
            
            self._collect_by = HC.options[ 'default_collect' ]
            
        
        if self._collect_by is None:
            
            self._collect_by = []
            
        
        popup = self._Popup( self._collect_by )
        
        #self.UseAltPopupWindow( True )
        
        self.SetPopupControl( popup )
        
        self.SetValue( 'no collections' ) # initialising to this because if there are no collections, no broadcast call goes through
        
    
    def GetChoice( self ):
        
        return self._collect_by
        
    
    def SetCollectTypes( self, collect_by, description ):
        
        collect_by = list( collect_by )
        
        self._collect_by = collect_by
        
        self.SetValue( description )
        
        if self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_collect', collect_by )
            
            page_key = self._management_controller.GetKey( 'page' )
            
            HG.client_controller.pub( 'collect_media', page_key, self._collect_by )
            
        
    
    class _Popup( wx.ComboPopup ):
        
        def __init__( self, collect_by ):
            
            wx.ComboPopup.__init__( self )
            
            self._initial_collect_by = collect_by
            
            self._control = None
            
        
        def Create( self, parent ):
            
            self._control = self._Control( parent, self.GetComboCtrl(), self._initial_collect_by )
            
            return True
            
        
        def GetAdjustedSize( self, preferred_width, preferred_height, max_height ):
            
            return( ( preferred_width, -1 ) )
            
        
        def GetControl( self ):
            
            return self._control
            
        
        def GetStringValue( self ):
            
            # this is an abstract method that provides the string to put in the comboctrl
            # I've never used/needed it, but one user reported getting the NotImplemented thing by repeatedly clicking, so let's add it anyway
            
            if self._control is None:
                
                return 'initialising'
                
            else:
                
                return self._control.GetDescription()
                
            
        
        class _Control( wx.CheckListBox ):
            
            def __init__( self, parent, special_parent, collect_by ):
                
                text_and_data_tuples = set()
                
                sort_by = HC.options[ 'sort_by' ]
                
                for ( sort_by_type, namespaces ) in sort_by:
                    
                    text_and_data_tuples.update( namespaces )
                    
                
                text_and_data_tuples = list( [ ( namespace, ( 'namespace', namespace ) ) for namespace in text_and_data_tuples ] )
                text_and_data_tuples.sort()
                
                ratings_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
                
                for ratings_service in ratings_services:
                    
                    text_and_data_tuples.append( ( ratings_service.GetName(), ( 'rating', ratings_service.GetServiceKey().hex() ) ) )
                    
                
                texts = [ text for ( text, data ) in text_and_data_tuples ] # we do this so it sizes its height properly on init
                
                wx.CheckListBox.__init__( self, parent, choices = texts )
                
                self.Clear()
                
                for ( text, data ) in text_and_data_tuples:
                    
                    self.Append( text, data )
                    
                
                self._special_parent = special_parent
                
                self.Bind( wx.EVT_CHECKLISTBOX, self.EventChanged )
                
                self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
                
                wx.CallAfter( self.SetValue, collect_by )
                
            
            def _BroadcastCollect( self ):
                
                ( collect_by, description ) = self._GetValues()
                
                self._special_parent.SetCollectTypes( collect_by, description )
                
            
            def _GetValues( self ):
                
                collect_by = []
                
                for index in self.GetCheckedItems():
                    
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
                
            
            def GetDescription( self ):
                
                ( collect_by, description ) = self._GetValues()
                
                return description
                
            
            def SetValue( self, collect_by ):
                
                try:
                    
                    # an old possible value, now collapsed to []
                    if collect_by is None:
                        
                        collect_by = []
                        
                    
                    # tuple for the set hashing
                    desired_collect_by_rows = { tuple( item ) for item in collect_by }
                    
                    indices_to_check = []
                    
                    for index in range( self.GetCount() ):
                        
                        if self.GetClientData( index ) in desired_collect_by_rows:
                            
                            indices_to_check.append( index )
                            
                        
                    
                    if len( indices_to_check ) > 0:
                        
                        self.SetCheckedItems( indices_to_check )
                        
                        self._BroadcastCollect()
                        
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'Failed to set a collect-by value!' )
                    
                    HydrusData.ShowException( e )
                    
                
            
        
    
class CheckboxManager( object ):
    
    def GetCurrentValue( self ):
        
        raise NotImplementedError()
        
    
    def Invert( self ):
        
        raise NotImplementedError()
        
    
class CheckboxManagerBoolean( CheckboxManager ):
    
    def __init__( self, obj, name ):
        
        CheckboxManager.__init__( self )
        
        self._obj = obj
        self._name = name
        
    
    def GetCurrentValue( self ):
        
        if not self._obj:
            
            return False
            
        
        return getattr( self._obj, self._name )
        
    
    def Invert( self ):
        
        if not self._obj:
            
            return
            
        
        value = getattr( self._obj, self._name )
        
        setattr( self._obj, self._name, not value )
        
    
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
        
        new_options = HG.client_controller.new_options
        
        return new_options.GetBoolean( self._boolean_name )
        
    
    def Invert( self ):
        
        new_options = HG.client_controller.new_options
        
        new_options.InvertBoolean( self._boolean_name )
        
    
class ChoiceSort( wx.Panel ):
    
    def __init__( self, parent, management_controller = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._management_controller = management_controller
        
        self._sort_type_choice = BetterChoice( self )
        self._sort_asc_choice = BetterChoice( self )
        
        asc_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_asc_choice, 15 )
        
        self._sort_asc_choice.SetMinSize( ( asc_width, -1 ) )
        
        sort_types = ClientData.GetSortTypeChoices()
        
        choice_tuples = []
        
        for sort_type in sort_types:
            
            example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
            
            choice_tuples.append( ( example_sort.GetSortTypeString(), sort_type ) )
            
        
        choice_tuples.sort()
        
        for ( display_string, value ) in choice_tuples:
            
            self._sort_type_choice.Append( display_string, value )
            
        
        type_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_type_choice, 10 )
        
        self._sort_type_choice.SetMinSize( ( type_width, -1 ) )
        
        self._sort_asc_choice.Append( '', CC.SORT_ASC )
        
        self._UpdateAscLabels()
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._sort_type_choice, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._sort_asc_choice, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        self._sort_type_choice.Bind( wx.EVT_CHOICE, self.EventSortTypeChoice )
        self._sort_asc_choice.Bind( wx.EVT_CHOICE, self.EventSortAscChoice )
        
        HG.client_controller.sub( self, 'ACollectHappened', 'collect_media' )
        HG.client_controller.sub( self, 'BroadcastSort', 'do_page_sort' )
        
        if self._management_controller is not None and self._management_controller.HasVariable( 'media_sort' ):
            
            media_sort = self._management_controller.GetVariable( 'media_sort' )
            
            try:
                
                self.SetSort( media_sort )
                
            except:
                
                default_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
                
                self.SetSort( default_sort )
                
            
        
    
    def _BroadcastSort( self ):
        
        media_sort = self._GetCurrentSort()
        
        if self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_sort', media_sort )
            
            page_key = self._management_controller.GetKey( 'page' )
            
            HG.client_controller.pub( 'sort_media', page_key, media_sort )
            
        
    
    def _GetCurrentSort( self ):
        
        sort_type = self._sort_type_choice.GetChoice()
        sort_asc = self._sort_asc_choice.GetChoice()
        
        media_sort = ClientMedia.MediaSort( sort_type, sort_asc )
        
        return media_sort
        
    
    def _UpdateAscLabels( self, set_default_asc = False ):
        
        media_sort = self._GetCurrentSort()
        
        self._sort_asc_choice.Clear()
        
        if media_sort.CanAsc():
            
            ( asc_str, desc_str, default_asc ) = media_sort.GetSortAscStrings()
            
            self._sort_asc_choice.Append( asc_str, CC.SORT_ASC )
            self._sort_asc_choice.Append( desc_str, CC.SORT_DESC )
            
            if set_default_asc:
                
                asc_to_set = default_asc
                
            else:
                
                asc_to_set = media_sort.sort_asc
                
            
            self._sort_asc_choice.SelectClientData( asc_to_set )
            
            self._sort_asc_choice.Enable()
            
        else:
            
            self._sort_asc_choice.Append( '', CC.SORT_ASC )
            self._sort_asc_choice.Append( '', CC.SORT_DESC )
            
            self._sort_asc_choice.SelectClientData( CC.SORT_ASC )
            
            self._sort_asc_choice.Disable()
            
        
    
    def _UserChoseASort( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'save_page_sort_on_change' ):
            
            media_sort = self._GetCurrentSort()
            
            HG.client_controller.new_options.SetDefaultSort( media_sort )
            
        
    
    def ACollectHappened( self, page_key, collect_by ):
        
        if self._management_controller is not None:
            
            my_page_key = self._management_controller.GetKey( 'page' )
            
            if page_key == my_page_key:
                
                self._BroadcastSort()
                
            
        
    
    def BroadcastSort( self, page_key = None ):
        
        if page_key is not None and page_key != self._management_controller.GetKey( 'page' ):
            
            return
            
        
        self._BroadcastSort()
        
    
    def EventSortAscChoice( self, event ):
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def EventSortTypeChoice( self, event ):
        
        self._UserChoseASort()
        
        self._UpdateAscLabels( set_default_asc = True )
        
        self._BroadcastSort()
        
    
    def GetSort( self ):
        
        return self._GetCurrentSort()
        
    
    def SetSort( self, media_sort ):
        
        self._sort_type_choice.SelectClientData( media_sort.sort_type )
        self._sort_asc_choice.SelectClientData( media_sort.sort_asc )
        
        self._UpdateAscLabels()
        
    
class AlphaColourControl( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._colour_picker = BetterColourControl( self )
        
        self._alpha_selector = wx.SpinCtrl( self, min = 0, max = 255 )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._colour_picker, CC.FLAGS_VCENTER )
        hbox.Add( BetterStaticText( self, 'alpha: ' ), CC.FLAGS_VCENTER )
        hbox.Add( self._alpha_selector, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetValue( self ):
        
        colour = self._colour_picker.GetColour()
        
        ( r, g, b, a ) = colour.Get() # no alpha support here, so it'll be 255
        
        a = self._alpha_selector.GetValue()
        
        colour = wx.Colour( r, g, b, a )
        
        return colour
        
    
    def SetValue( self, colour ):
        
        ( r, g, b, a ) = colour.Get()
        
        picker_colour = wx.Colour( r, g, b )
        
        self._colour_picker.SetColour( picker_colour )
        
        self._alpha_selector.SetValue( a )
        
    
class ExportPatternButton( BetterButton ):
    
    def __init__( self, parent ):
        
        BetterButton.__init__( self, parent, 'pattern shortcuts', self._Hit )
        
    
    def _Hit( self ):
        
        menu = wx.Menu()
        
        ClientGUIMenus.AppendMenuLabel( menu, 'click on a phrase to copy to clipboard' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'the file\'s hash - {hash}', 'copy "{hash}" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '{hash}' )
        ClientGUIMenus.AppendMenuItem( self, menu, 'all the file\'s tags - {tags}', 'copy "{tags}" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '{tags}' )
        ClientGUIMenus.AppendMenuItem( self, menu, 'all the file\'s non-namespaced tags - {nn tags}', 'copy "{nn tags}" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '{nn tags}' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'all instances of a particular namespace - [\u2026]', 'copy "[\u2026]" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '[\u2026]' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'a particular tag, if the file has it - (\u2026)', 'copy "(\u2026)" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(\u2026)' )
        
        HG.client_controller.PopupMenu( self, menu )
        
    
class Gauge( wx.Gauge ):
    
    def __init__( self, *args, **kwargs ):
        
        wx.Gauge.__init__( self, *args, **kwargs )
        
        self._actual_value = None
        self._actual_range = None
        
        self._is_pulsing = False
        
    
    def GetValueRange( self ):
        
        if self._actual_range is None:
            
            range = self.GetRange()
            
        else:
            
            range = self._actual_range
            
        
        return ( self._actual_value, range )
        
    
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
        
        self._actual_value = value
        
        if not self._is_pulsing:
            
            if value is None:
                
                self.Pulse()
                
                self._is_pulsing = True
                
            else:
                
                if self._actual_range is not None:
                    
                    value = min( int( 1000 * ( value / self._actual_range ) ), 1000 )
                    
                
                value = min( value, self.GetRange() )
                
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
        
        self._panel_sizer.Add( self._empty_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._list_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        hbox.Add( self._panel_sizer, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._list_box.Bind( wx.EVT_LISTBOX, self.EventSelection )
        
        self.SetSizer( hbox )
        
    
    def _ActivatePage( self, key ):

        ( classname, args, kwargs ) = self._keys_to_proto_pages[ key ]
        
        page = classname( *args, **kwargs )
        
        page.Hide()
        
        self._panel_sizer.Add( page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
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
        
        wx.QueueEvent( self.GetEventHandler(), event )
        
        # now the virtualsize is updated, we now tell any parent resizing frame/dialog that is interested in resizing that now is the time
        ClientGUITopLevelWindows.PostSizeChangedEvent( self )
        
        event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGED, -1 )
        
        wx.QueueEvent( self.GetEventHandler(), event )
        
    
    def AddPage( self, display_name, key, page, select = False ):
        
        if self._GetIndex( key ) != wx.NOT_FOUND:
            
            raise HydrusExceptions.NameException( 'That entry already exists!' )
            
        
        if not isinstance( page, tuple ):
            
            page.Hide()
            
            self._panel_sizer.Add( page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
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
        
        self._panel_sizer.Clear( delete_windows = True )
        
        self._panel_sizer.Add( self._empty_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
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
            
            page_to_delete.DestroyLater()
            
            del self._keys_to_active_pages[ key_to_delete ]
            
            self._list_box.Delete( selection )
            
            self._RecalcListBoxWidth()
            
        
    
    def EventSelection( self, event ):
        
        if self._list_box.GetSelection() != self._GetIndex( self._current_key ):
            
            event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING, -1 )
            
            wx.QueueEvent( self.GetEventHandler(), event )
            
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
        
        return list(self._keys_to_active_pages.values())
        
    
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
        
    
    def Select( self, key ):
        
        index = self._GetIndex( key )
        
        if index != wx.NOT_FOUND and index != self._list_box.GetSelection():
            
            event = wx.NotifyEvent( wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING, -1 )
            
            wx.QueueEvent( self.GetEventHandler(), event )
            
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
        
        for ( key, page ) in list(self._keys_to_active_pages.items()):
            
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
                
                if current_value is not None:
                    
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
        
    
class NetworkContextButton( BetterButton ):
    
    def __init__( self, parent, network_context, limited_types = None, allow_default = True ):
        
        BetterButton.__init__( self, parent, network_context.ToString(), self._Edit )
        
        self._network_context = network_context
        self._limited_types = limited_types
        self._allow_default = allow_default
        
    
    def _Edit( self ):
        
        from . import ClientGUITopLevelWindows
        from . import ClientGUIScrolledPanelsEdit
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit network context' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditNetworkContextPanel( dlg, self._network_context, limited_types = self._limited_types, allow_default = self._allow_default )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._network_context = panel.GetValue()
                
                self._Update()
                
            
        
    
    def _Update( self ):
        
        self.SetLabelText( self._network_context.ToString() )
        
    
    def GetValue( self ):
        
        return self._network_context
        
    
    def SetValue( self, network_context ):
        
        self._network_context = network_context
        
        self._Update()
        
    
class NoneableSpinCtrl( wx.Panel ):
    
    def __init__( self, parent, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1, num_dimensions = 1 ):
        
        wx.Panel.__init__( self, parent )
        
        self._unit = unit
        self._multiplier = multiplier
        self._num_dimensions = num_dimensions
        
        self._checkbox = wx.CheckBox( self )
        self._checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckBox )
        self._checkbox.SetLabelText( none_phrase )
        
        self._one = wx.SpinCtrl( self, min = min, max = max )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._one, len( str( max ) ) + 5 )
        
        self._one.SetInitialSize( ( width, -1 ) )
        
        if num_dimensions == 2:
            
            self._two = wx.SpinCtrl( self, initial = 0, min = min, max = max )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( self._two, len( str( max ) ) + 5 )
            
            self._two.SetInitialSize( ( width, -1 ) )
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if len( message ) > 0:
            
            hbox.Add( BetterStaticText( self, message + ': ' ), CC.FLAGS_VCENTER )
            
        
        hbox.Add( self._one, CC.FLAGS_VCENTER )
        
        if self._num_dimensions == 2:
            
            hbox.Add( BetterStaticText( self, 'x' ), CC.FLAGS_VCENTER )
            hbox.Add( self._two, CC.FLAGS_VCENTER )
            
        
        if self._unit is not None:
            
            hbox.Add( BetterStaticText( self, self._unit ), CC.FLAGS_VCENTER )
            
        
        hbox.Add( self._checkbox, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def Bind( self, event_type, callback ):
        
        self._checkbox.Bind( wx.EVT_CHECKBOX, callback )
        
        self._one.Bind( wx.EVT_SPINCTRL, callback )
        
        if self._num_dimensions == 2:
            
            self._two.Bind( wx.EVT_SPINCTRL, callback )
            
        
    
    def EventCheckBox( self, event ):
        
        if self._checkbox.GetValue():
            
            self._one.Disable()
            
            if self._num_dimensions == 2:
                
                self._two.Disable()
                
            
        else:
            
            self._one.Enable()
            
            if self._num_dimensions == 2:
                
                self._two.Enable()
                
            
        
    
    def GetValue( self ):
        
        if self._checkbox.GetValue():
            
            return None
            
        else:
            
            if self._num_dimensions == 2:
                
                return ( self._one.GetValue() * self._multiplier, self._two.GetValue() * self._multiplier )
                
            else:
                
                return self._one.GetValue() * self._multiplier
                
            
        
    
    def SetToolTip( self, text ):
        
        wx.Panel.SetToolTip( self, text )
        
        for c in self.GetChildren():
            
            c.SetToolTip( text )
            
        
    
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
                
                self._two.SetValue( y // self._multiplier )
                
            
            self._one.Enable()
            
            self._one.SetValue( value // self._multiplier )
            
        
    
class NoneableTextCtrl( wx.Panel ):
    
    def __init__( self, parent, message = '', none_phrase = 'none' ):
        
        wx.Panel.__init__( self, parent )
        
        self._checkbox = wx.CheckBox( self )
        self._checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckBox )
        self._checkbox.SetLabelText( none_phrase )
        
        self._text = wx.TextCtrl( self )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if len( message ) > 0:
            
            hbox.Add( BetterStaticText( self, message + ': ' ), CC.FLAGS_VCENTER )
            
        
        hbox.Add( self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._checkbox, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def Bind( self, event_type, callback ):
        
        self._checkbox.Bind( wx.EVT_CHECKBOX, callback )
        
        self._text.Bind( wx.EVT_TEXT, callback )
        
    
    def EventCheckBox( self, event ):
        
        if self._checkbox.GetValue():
            
            self._text.Disable()
            
        else:
            
            self._text.Enable()
            
        
    
    def GetValue( self ):
        
        if self._checkbox.GetValue():
            
            return None
            
        else:
            
            return self._text.GetValue()
            
        
    
    def SetToolTip( self, text ):
        
        wx.Panel.SetToolTip( self, text )
        
        for c in self.GetChildren():
            
            c.SetToolTip( text )
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._checkbox.SetValue( True )
            
            self._text.Disable()
            
        else:
            
            self._checkbox.SetValue( False )
            
            self._text.Enable()
            
            self._text.SetValue( value )
            
        
    
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
        
        self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( 16, 16, 24 )
        
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
        
        self.SetToolTip( name )
        
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
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
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
        
        self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( my_width, 16, 24 )
        
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
            
                proportion_filled = x_adjusted / my_active_width
                
                if self._allow_zero:
                    
                    rating = round( proportion_filled * self._num_stars ) / self._num_stars
                    
                else:
                    
                    rating = int( proportion_filled * self._num_stars ) / ( self._num_stars - 1 )
                    
                
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
        
        self.SetToolTip( name )
        
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
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
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
            
        
    
class RegexButton( BetterButton ):
    
    def __init__( self, parent ):
        
        BetterButton.__init__( self, parent, 'regex shortcuts', self._ShowMenu )
        
    
    def _ShowMenu( self ):
        
        menu = wx.Menu()
        
        ClientGUIMenus.AppendMenuLabel( menu, 'click on a phrase to copy it to the clipboard' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        submenu = wx.Menu()
        
        ClientGUIMenus.AppendMenuItem( self, submenu, r'whitespace character - \s', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'\s' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'number character - \d', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'\d' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'alphanumeric or backspace character - \w', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'\w' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'any character - .', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'.' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'backslash character - \\', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'\\' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'beginning of line - ^', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'^' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'end of line - $', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'$' )
        ClientGUIMenus.AppendMenuItem( self, submenu, 'any of these - [\u2026]', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '[\u2026]' )
        ClientGUIMenus.AppendMenuItem( self, submenu, 'anything other than these - [^\u2026]', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '[^\u2026]' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( self, submenu, r'0 or more matches, consuming as many as possible - *', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'*' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'1 or more matches, consuming as many as possible - +', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'+' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'0 or 1 matches, preferring 1 - ?', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'?' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'0 or more matches, consuming as few as possible - *?', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'*?' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'1 or more matches, consuming as few as possible - +?', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'+?' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'0 or 1 matches, preferring 0 - ??', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'??' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'exactly m matches - {m}', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'{m}' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'm to n matches, consuming as many as possible - {m,n}', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'{m,n}' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'm to n matches, consuming as few as possible - {m,n}?', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'{m,n}?' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( self, submenu, 'the next characters are: (non-consuming) - (?=\u2026)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?=\u2026)' )
        ClientGUIMenus.AppendMenuItem( self, submenu, 'the next characters are not: (non-consuming) - (?!\u2026)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?!\u2026)' )
        ClientGUIMenus.AppendMenuItem( self, submenu, 'the previous characters are: (non-consuming) - (?<=\u2026)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?<=\u2026)' )
        ClientGUIMenus.AppendMenuItem( self, submenu, 'the previous characters are not: (non-consuming) - (?<!\u2026)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?<!\u2026)' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( self, submenu, r'0074 -> 74 - [1-9]+\d*', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'[1-9]+\d*' )
        ClientGUIMenus.AppendMenuItem( self, submenu, r'filename - (?<=' + re.escape( os.path.sep ) + r')[^' + re.escape( os.path.sep ) + r']*?(?=\..*$)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?<=' + re.escape( os.path.sep ) + r')[^' + re.escape( os.path.sep ) + r']*?(?=\..*$)' )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'regex components' )
        
        submenu = wx.Menu()
        
        ClientGUIMenus.AppendMenuItem( self, submenu, 'manage favourites', 'manage some custom favourite phrases', self._ManageFavourites )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        for ( regex_phrase, description ) in HC.options[ 'regex_favourites' ]:
            
            ClientGUIMenus.AppendMenuItem( self, submenu, description, 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', regex_phrase )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'favourites' )
        
        HG.client_controller.PopupMenu( self, menu )
        
    
    def _ManageFavourites( self ):
        
        regex_favourites = HC.options[ 'regex_favourites' ]
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'manage regex favourites' ) as dlg:
            
            from . import ClientGUIScrolledPanelsEdit
            
            panel = ClientGUIScrolledPanelsEdit.EditRegexFavourites( dlg, regex_favourites )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                regex_favourites = panel.GetValue()
                
                HC.options[ 'regex_favourites' ] = regex_favourites
                
                HG.client_controller.Write( 'save_options', HC.options )
                
            
        
    
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
            
        
    
class StaticBox( wx.Panel ):
    
    def __init__( self, parent, title ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._sizer = BetterBoxSizer( wx.VERTICAL )
        
        normal_font = wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT )
        
        normal_font_size = normal_font.GetPointSize()
        normal_font_family = normal_font.GetFamily()
        
        title_font = wx.Font( int( normal_font_size ), normal_font_family, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD )
        
        title_text = wx.StaticText( self, label = title )
        title_text.SetFont( title_font )
        
        self._sizer.Add( title_text, CC.FLAGS_CENTER )
        
        self.SetSizer( self._sizer )
        
    
    def Add( self, widget, flags ):
        
        self._sizer.Add( widget, flags )
        
    
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
        
        self.Add( self._sorter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def ChangeTagService( self, service_key ):
        
        self._tags_box.ChangeTagService( service_key )
        
    
    def EventSort( self, event ):
        
        selection = self._sorter.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            sort = self._sorter.GetClientData( selection )
            
            self._tags_box.SetSort( sort )
            
        
    
    def SetTagsBox( self, tags_box ):
        
        self._tags_box = tags_box
        
        self.Add( self._tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def SetTagsByMedia( self, media, force_reload = False ):
        
        self._tags_box.SetTagsByMedia( media, force_reload = force_reload )
        
    
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
            
            self.Add( radio_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._indices_to_radio_buttons[ index ] = radio_button
            self._radio_buttons_to_data[ radio_button ] = data
            
        
        if initial_index is not None and initial_index in self._indices_to_radio_buttons: self._indices_to_radio_buttons[ initial_index ].SetValue( True )
        
    
    def GetSelectedClientData( self ):
        
        for radio_button in list(self._radio_buttons_to_data.keys()):
            
            if radio_button.GetValue() == True: return self._radio_buttons_to_data[ radio_button ]
            
        
    
    def SetSelection( self, index ):
        
        self._indices_to_radio_buttons[ index ].SetValue( True )
        
    
    def SetString( self, index, text ):
        
        self._indices_to_radio_buttons[ index ].SetLabelText( text )
        
    
class TextAndGauge( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._st = BetterStaticText( self )
        self._gauge = Gauge( self )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def SetValue( self, text, value, range ):
        
        if not self:
            
            return
            
        
        self._st.SetLabelText( text )
        
        self._gauge.SetRange( range )
        self._gauge.SetValue( value )
        
    
class ThreadToGUIUpdater( object ):
    
    def __init__( self, win, func ):
        
        self._win = win
        self._func = func
        
        self._lock = threading.Lock()
        self._dirty_count = 0
        
        self._args = None
        self._kwargs = None
        
        self._doing_it = False
        
    
    def WXDoIt( self ):
        
        with self._lock:
            
            if not self._win:
                
                self._win = None
                
                return
                
            
            try:
                
                self._func( *self._args, **self._kwargs )
                
            except HydrusExceptions.ShutdownException:
                
                pass
                
            
            self._dirty_count = 0
            self._doing_it = False
            
        
    
    # the point here is that we can spam this a hundred times a second, updating the args and kwargs, and wx will catch up to it when it can
    # if wx feels like running fast, it'll update at 60fps
    # if not, we won't get bungled up with 10,000+ pubsub events in the event queue
    def Update( self, *args, **kwargs ):
        
        with self._lock:
            
            self._args = args
            self._kwargs = kwargs
            
            if not self._doing_it and not HG.view_shutdown:
                
                wx.CallAfter( self.WXDoIt )
                
                self._doing_it = True
                
            
            self._dirty_count += 1
            
            take_a_break = self._dirty_count % 1000 == 0
            
        
        # just in case we are choking the wx thread, let's give it a break every now and then
        if take_a_break:
            
            time.sleep( 0.25 )
            
        
    
