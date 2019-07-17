from . import ClientCaches
from . import ClientConstants as CC
from . import ClientGUIFunctions
from . import ClientGUIMenus
from . import ClientGUIShortcuts
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
import os
import wx

( OKEvent, EVT_OK ) = wx.lib.newevent.NewCommandEvent()

CHILD_POSITION_PADDING = 24
FUZZY_PADDING = 15

def GetDisplayPosition( window ):
    
    display_index = wx.Display.GetFromWindow( window )
    
    if display_index == wx.NOT_FOUND:
        
        display_index = 0 # default to primary
        
    
    display = wx.Display( display_index )
    
    rect = display.GetClientArea()
    
    return tuple( rect.GetPosition() )
    
def GetDisplaySize( window ):
    
    display_index = wx.Display.GetFromWindow( window )
    
    if display_index == wx.NOT_FOUND:
        
        display_index = 0 # default to primary
        
    
    display = wx.Display( display_index )
    
    rect = display.GetClientArea()
    
    return tuple( rect.GetSize() )
    
def GetSafePosition( position ):
    
    ( p_x, p_y ) = position
    
    # some window managers size the windows just off screen to cut off borders
    # so choose a test position that's a little more lenient
    ( test_x, test_y ) = ( p_x + FUZZY_PADDING, p_y + FUZZY_PADDING )
    
    display_index = wx.Display.GetFromPoint( ( test_x, test_y ) )
    
    if display_index == wx.NOT_FOUND:
        
        return wx.DefaultPosition
        
    else:
        
        return position
        
    
def GetSafeSize( tlw, min_size, gravity ):
    
    ( min_width, min_height ) = min_size
    
    parent = tlw.GetParent()
    
    if parent is None:
        
        width = min_width
        height = min_height
        
    else:
        
        ( parent_window_width, parent_window_height ) = parent.GetTopLevelParent().GetSize()
        
        ( width_gravity, height_gravity ) = gravity
        
        if width_gravity == -1:
            
            width = min_width
            
        else:
            
            max_width = parent_window_width - 2 * CHILD_POSITION_PADDING
            
            width = int( width_gravity * max_width )
            
        
        if height_gravity == -1:
            
            height = min_height
            
        else:
            
            max_height = parent_window_height - 2 * CHILD_POSITION_PADDING
            
            height = int( height_gravity * max_height )
            
        
    
    ( display_width, display_height ) = GetDisplaySize( tlw )
    
    width = min( display_width, width )
    height = min( display_height, height )
    
    return ( width, height )
    
def ExpandTLWIfPossible( tlw, frame_key, desired_size_delta ):
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    if not tlw.IsMaximized() and not tlw.IsFullScreen():
        
        ( current_width, current_height ) = tlw.GetSize()
        
        ( desired_delta_width, desired_delta_height ) = desired_size_delta
        
        desired_width = current_width + desired_delta_width + FUZZY_PADDING
        desired_height = current_height + desired_delta_height + FUZZY_PADDING
        
        ( width, height ) = GetSafeSize( tlw, ( desired_width, desired_height ), default_gravity )
        
        if width > current_width or height > current_height:
            
            tlw.SetSize( ( width, height ) )
            
            SlideOffScreenTLWUpAndLeft( tlw )
            
        
    
def MouseIsOnMyDisplay( window ):
    
    window_display_index = wx.Display.GetFromWindow( window )
    
    mouse_display_index = wx.Display.GetFromPoint( wx.GetMousePosition() )
    
    return window_display_index == mouse_display_index
    
def PostSizeChangedEvent( window ):
    
    event = CC.SizeChangedEvent( -1 )
    
    wx.QueueEvent( window.GetEventHandler(), event )
    
def SaveTLWSizeAndPosition( tlw, frame_key ):
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    maximised = tlw.IsMaximized()
    fullscreen = tlw.IsFullScreen()
    
    if not ( maximised or fullscreen ):
        
        safe_position = GetSafePosition( tuple( tlw.GetPosition() ) )
        
        if safe_position != wx.DefaultPosition:
            
            last_size = tuple( tlw.GetSize() )
            last_position = safe_position
            
        
    
    new_options.SetFrameLocation( frame_key, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
    
def SetInitialTLWSizeAndPosition( tlw, frame_key ):
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    parent = tlw.GetParent()
    
    if remember_size and last_size is not None:
        
        ( width, height ) = last_size
        
    else:
        
        ( min_width, min_height ) = tlw.GetEffectiveMinSize()
        
        min_width += FUZZY_PADDING
        min_height += FUZZY_PADDING
        
        ( width, height ) = GetSafeSize( tlw, ( min_width, min_height ), default_gravity )
        
    
    tlw.SetInitialSize( ( width, height ) )
    
    min_width = min( 240, width )
    min_height = min( 240, height )
    
    tlw.SetMinSize( ( min_width, min_height ) )
    
    #
    
    if remember_position and last_position is not None:
        
        safe_position = GetSafePosition( last_position )
        
        tlw.SetPosition( safe_position )
        
    elif default_position == 'topleft':
        
        if parent is not None:
            
            if isinstance( parent, wx.TopLevelWindow ):
                
                parent_tlp = parent
                
            else:
                
                parent_tlp = parent.GetTopLevelParent()
                
            
            ( parent_x, parent_y ) = parent_tlp.GetPosition()
            
            tlw.SetPosition( ( parent_x + CHILD_POSITION_PADDING, parent_y + CHILD_POSITION_PADDING ) )
            
        else:
            
            safe_position = GetSafePosition( ( 0 + CHILD_POSITION_PADDING, 0 + CHILD_POSITION_PADDING ) )
            
            tlw.SetPosition( safe_position )
            
        
        SlideOffScreenTLWUpAndLeft( tlw )
        
    elif default_position == 'center':
        
        wx.CallAfter( tlw.Center )
        
    
    # if these aren't callafter, the size and pos calls don't stick if a restore event happens
    
    if maximised:
        
        wx.CallAfter( tlw.Maximize )
        
    
    if fullscreen:
        
        wx.CallAfter( tlw.ShowFullScreen, True, wx.FULLSCREEN_ALL )
        
    
def SlideOffScreenTLWUpAndLeft( tlw ):
    
    ( tlw_width, tlw_height ) = tlw.GetSize()
    ( tlw_x, tlw_y ) = tlw.GetPosition()
    
    tlw_right = tlw_x + tlw_width
    tlw_bottom = tlw_y + tlw_height
    
    ( display_width, display_height ) = GetDisplaySize( tlw )
    ( display_x, display_y ) = GetDisplayPosition( tlw )
    
    display_right = display_x + display_width
    display_bottom = display_y + display_height
    
    move_x = tlw_right > display_right
    move_y = tlw_bottom > display_bottom
    
    if move_x or move_y:
        
        delta_x = min( display_right - tlw_right, 0 )
        delta_y = min( display_bottom - tlw_bottom, 0 )
        
        tlw.SetPosition( ( tlw_x + delta_x, tlw_y + delta_y ) )
        
    
class NewDialog( wx.Dialog ):
    
    def __init__( self, parent, title, style_override = None ):
        
        if style_override is None:
            
            style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
            
            if not HC.PLATFORM_LINUX and parent is not None:
                
                style |= wx.FRAME_FLOAT_ON_PARENT
                
            
        else:
            
            style = style_override
            
        
        wx.Dialog.__init__( self, parent, title = title, style = style )
        
        self._consumed_esc_to_cancel = False
        
        self._new_options = HG.client_controller.new_options
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self.SetIcon( HG.client_controller.frame_icon )
        
        HG.client_controller.ResetIdleTimer()
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
    
    def _CanCancel( self ):
        
        return True
        
    
    def _CanOK( self ):
        
        return True
        
    
    def _ReadyToClose( self, value ):
        
        return True
        
    
    def _SaveOKPosition( self ):
        
        pass
        
    
    def _TryEndModal( self, value ):
        
        if not self.IsModal(): # in some rare cases (including spammy AutoHotkey, looks like), this can be fired before the dialog can clean itself up
            
            return
            
        
        if not self._ReadyToClose( value ):
            
            return
            
        
        if value == wx.ID_CANCEL:
            
            if not self._CanCancel():
                
                return
                
            
        
        if value == wx.ID_OK:
            
            if not self._CanOK():
                
                return
                
            
            self._SaveOKPosition()
            
        
        self.CleanBeforeDestroy()
        
        try:
            
            self.EndModal( value )
            
        except Exception as e:
            
            HydrusData.ShowText( 'This dialog seems to have been unable to close for some reason. I am printing the stack to the log. The dialog may have already closed, or may attempt to close now. Please inform hydrus dev of this situation. I recommend you restart the client if you can. If the UI is locked, you will have to kill it via task manager.' )
            
            HydrusData.PrintException( e )
            
            import traceback
            
            HydrusData.DebugPrint( ''.join( traceback.format_stack() ) )
            
            try:
                
                self.Close()
                
            except:
                
                HydrusData.ShowText( 'The dialog would not close on command.' )
                
            
            try:
                
                self.Destroy()
                
            except:
                
                HydrusData.ShowText( 'The dialog would not destroy on command.' )
                
            
        
    
    def CleanBeforeDestroy( self ):
        
        parent = self.GetParent()
        
        if parent is not None and not ClientGUIFunctions.GetTLP( parent ) == HG.client_controller.gui:
            
            wx.CallAfter( parent.SetFocus )
            
        
    
    def DoOK( self ):
        
        self._TryEndModal( wx.ID_OK )
        
    
    def EventCharHook( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        obj = event.GetEventObject()
        
        event_from_us = obj is not None and ClientGUIFunctions.IsWXAncestor( obj, self )
        
        if event_from_us and key == wx.WXK_ESCAPE and not self._consumed_esc_to_cancel:
            
            self._consumed_esc_to_cancel = True
            
            self._TryEndModal( wx.ID_CANCEL )
            
        else:
            
            event.Skip()
            
        
    
    def EventClose( self, event ):
        
        if not self:
            
            return
            
        
        self._TryEndModal( wx.ID_CANCEL )
        
    
    def EventDialogButton( self, event ):
        
        if not self:
            
            return
            
        
        event_id = event.GetId()
        
        if event_id == wx.ID_ANY:
            
            event.Skip()
            
            return
            
        
        event_object = event.GetEventObject()
        
        if event_object is not None:
            
            tlp = event_object.GetTopLevelParent()
            
            if tlp != self:
                
                event.Skip()
                
                return
                
            
        
        self._TryEndModal( event_id )
        
    
    def EventOK( self, event ):
        
        if not self:
            
            return
            
        
        self._TryEndModal( wx.ID_OK )
        
    
class DialogThatResizes( NewDialog ):
    
    def __init__( self, parent, title, frame_key, style_override = None ):
        
        self._frame_key = frame_key
        
        NewDialog.__init__( self, parent, title, style_override = style_override )
        
    
    def _SaveOKPosition( self ):
        
        SaveTLWSizeAndPosition( self, self._frame_key )
        
    
class DialogThatTakesScrollablePanel( DialogThatResizes ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog', style_override = None, hide_buttons = False ):
        
        self._panel = None
        self._hide_buttons = hide_buttons
        
        DialogThatResizes.__init__( self, parent, title, frame_key, style_override = style_override )
        
        self._InitialiseButtons()
        
        self.Bind( EVT_OK, self.EventOK )
        self.Bind( CC.EVT_SIZE_CHANGED, self.EventChildSizeChanged )
        
    
    def _CanCancel( self ):
        
        return self._panel.CanCancel()
        
    
    def _CanOK( self ):
        
        return self._panel.CanOK()
        
    
    def _GetButtonBox( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseButtons( self ):
        
        raise NotImplementedError()
        
    
    def CleanBeforeDestroy( self ):
        
        DialogThatResizes.CleanBeforeDestroy( self )
        
        if hasattr( self._panel, 'CleanBeforeDestroy' ):
            
            self._panel.CleanBeforeDestroy()
            
        
    
    def EventChildSizeChanged( self, event ):
        
        if self._panel is not None:
            
            # the min size here is to compensate for wx.Notebook and anything else that don't update virtualsize on page change
            
            ( current_panel_width, current_panel_height ) = self._panel.GetSize()
            ( desired_panel_width, desired_panel_height ) = self._panel.GetVirtualSize()
            ( min_panel_width, min_panel_height ) = self._panel.GetEffectiveMinSize()
            
            desired_delta_width = max( 0, desired_panel_width - current_panel_width, min_panel_width - current_panel_width )
            desired_delta_height = max( 0, desired_panel_height - current_panel_height, min_panel_height - current_panel_height )
            
            if desired_delta_width > 0 or desired_delta_height > 0:
                
                ExpandTLWIfPossible( self, self._frame_key, ( desired_delta_width, desired_delta_height ) )
                
            
        
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        buttonbox = self._GetButtonBox()
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        if buttonbox is not None:
            
            vbox.Add( buttonbox, CC.FLAGS_BUTTON_SIZER )
            
        
        self.SetSizer( vbox )
        
        SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self._panel.SetupScrolling( scrollIntoView = False ) # this changes geteffectiveminsize calc, so it needs to be below settlwsizeandpos
        
        PostSizeChangedEvent( self ) # helps deal with some Linux/otherscrollbar weirdness where setupscrolling changes inherent virtual size
        
    
class DialogNullipotent( DialogThatTakesScrollablePanel ):
    
    def _GetButtonBox( self ):
        
        buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        buttonbox.Add( self._close, CC.FLAGS_VCENTER )
        
        return buttonbox
        
    
    def _InitialiseButtons( self ):
        
        self._close = wx.Button( self, id = wx.ID_OK, label = 'close' )
        self._close.Bind( wx.EVT_BUTTON, self.EventOK )
        
        if self._hide_buttons:
            
            self._close.Hide()
            
            self.Bind( wx.EVT_CLOSE, self.EventOK ) # the close event no longer goes to the default button, since it is hidden, wew
            
        
    
    def _ReadyToClose( self, value ):
        
        try:
            
            self._panel.TryToClose()
            
            return True
            
        except HydrusExceptions.VetoException as e:
            
            message = str( e )
            
            if len( message ) > 0:
                
                wx.MessageBox( message )
                
            
            return False
            
        
    
class DialogApplyCancel( DialogThatTakesScrollablePanel ):
    
    def _GetButtonBox( self ):
        
        buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        buttonbox.Add( self._apply, CC.FLAGS_VCENTER )
        buttonbox.Add( self._cancel, CC.FLAGS_VCENTER )
        
        return buttonbox
        
    
    def _InitialiseButtons( self ):
        
        self._apply = wx.Button( self, id = wx.ID_OK, label = 'apply' )
        self._apply.SetForegroundColour( ( 0, 128, 0 ) )
        self._apply.Bind( wx.EVT_BUTTON, self.EventDialogButton )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        self._cancel.Bind( wx.EVT_BUTTON, self.EventDialogButton )
        
        if self._hide_buttons:
            
            self._apply.Hide()
            self._cancel.Hide()
            
            self.Bind( wx.EVT_CLOSE, self.EventClose ) # the close event no longer goes to the default button, since it is hidden, wew
            
        
    
class DialogEdit( DialogApplyCancel ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog', hide_buttons = False ):
        
        DialogApplyCancel.__init__( self, parent, title, frame_key = frame_key, hide_buttons = hide_buttons )
        
    
    def _ReadyToClose( self, value ):
        
        if value != wx.ID_OK:
            
            return True
            
        
        try:
            
            value = self._panel.GetValue()
            
            return True
            
        except HydrusExceptions.VetoException as e:
            
            message = str( e )
            
            if len( message ) > 0:
                
                wx.MessageBox( message )
                
            
            return False
            
        
    
class DialogManage( DialogApplyCancel ):
    
    def _ReadyToClose( self, value ):
        
        if value != wx.ID_OK:
            
            return True
            
        
        try:
            
            self._panel.CommitChanges()
            
            return True
            
        except HydrusExceptions.VetoException as e:
            
            message = str( e )
            
            if len( message ) > 0:
                
                wx.MessageBox( message )
                
            
            return False
            
        
    
class DialogCustomButtonQuestion( DialogThatTakesScrollablePanel ):
    
    def __init__( self, parent, title, frame_key = 'regular_center_dialog', style_override = None ):
        
        DialogThatTakesScrollablePanel.__init__( self, parent, title, frame_key = frame_key, style_override = style_override )
        
    
    def _GetButtonBox( self ):
        
        return None
        
    
    def _InitialiseButtons( self ):
        
        pass
        
    
class Frame( wx.Frame ):
    
    def __init__( self, parent, title, float_on_parent = True ):
        
        style = wx.DEFAULT_FRAME_STYLE
        
        if float_on_parent:
            
            style |= wx.FRAME_FLOAT_ON_PARENT
            
        
        wx.Frame.__init__( self, parent, title = title, style = style )
        
        self._new_options = HG.client_controller.new_options
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self.SetIcon( HG.client_controller.frame_icon )
        
        self.Bind( wx.EVT_CLOSE, self.EventAboutToClose )
        
        HG.client_controller.ResetIdleTimer()
        
    
    def CleanBeforeDestroy( self ):
        
        parent = self.GetParent()
        
        if parent is not None and not ClientGUIFunctions.GetTLP( parent ) == HG.client_controller.gui:
            
            wx.CallAfter( parent.SetFocus )
            
        
    
    def EventAboutToClose( self, event ):
        
        self.CleanBeforeDestroy()
        
        event.Skip()
        
    
class FrameThatResizes( Frame ):
    
    def __init__( self, parent, title, frame_key, float_on_parent = True ):
        
        self._frame_key = frame_key
        
        Frame.__init__( self, parent, title, float_on_parent )
        
        self.Bind( wx.EVT_SIZE, self.EventSizeAndPositionChanged )
        self.Bind( wx.EVT_MOVE_END, self.EventSizeAndPositionChanged )
        self.Bind( wx.EVT_CLOSE, self.EventSizeAndPositionChanged )
        self.Bind( wx.EVT_MAXIMIZE, self.EventSizeAndPositionChanged )
        
    
    def EventSizeAndPositionChanged( self, event ):
        
        SaveTLWSizeAndPosition( self, self._frame_key )
        
        event.Skip()
        
    
class FrameThatTakesScrollablePanel( FrameThatResizes ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog', float_on_parent = True ):
        
        self._panel = None
        
        FrameThatResizes.__init__( self, parent, title, frame_key, float_on_parent )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'close' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventClose )
        
        self.Bind( EVT_OK, self.EventClose )
        self.Bind( CC.EVT_SIZE_CHANGED, self.EventChildSizeChanged )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
    
    def CleanBeforeDestroy( self ):
        
        FrameThatResizes.CleanBeforeDestroy( self )
        
        if hasattr( self._panel, 'CleanBeforeDestroy' ):
            
            self._panel.CleanBeforeDestroy()
            
        
    
    def EventCharHook( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key == wx.WXK_ESCAPE:
            
            self.Close()
            
        else:
            
            event.Skip()
            
        
    
    def EventClose( self, event ):
        
        self.Close()
        
    
    def EventChildSizeChanged( self, event ):
        
        if self._panel is not None:
            
            # the min size here is to compensate for wx.Notebook and anything else that don't update virtualsize on page change
            
            ( current_panel_width, current_panel_height ) = self._panel.GetSize()
            ( desired_panel_width, desired_panel_height ) = self._panel.GetVirtualSize()
            ( min_panel_width, min_panel_height ) = self._panel.GetEffectiveMinSize()
            
            desired_delta_width = max( 0, desired_panel_width - current_panel_width, min_panel_width - current_panel_width )
            desired_delta_height = max( 0, desired_panel_height - current_panel_height, min_panel_height - current_panel_height )
            
            if desired_delta_width > 0 or desired_delta_height > 0:
                
                ExpandTLWIfPossible( self, self._frame_key, ( desired_delta_width, desired_delta_height ) )
                
            
        
    
    def GetPanel( self ):
        
        return self._panel
        
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._ok, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self.Show( True )
        
        self._panel.SetupScrolling( scrollIntoView = False ) # this changes geteffectiveminsize calc, so it needs to be below settlwsizeandpos
        
        PostSizeChangedEvent( self ) # helps deal with some Linux/otherscrollbar weirdness where setupscrolling changes inherent virtual size
        
    
