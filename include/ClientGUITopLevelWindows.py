import ClientCaches
import ClientConstants as CC
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import os
import wx

CHILD_POSITION_PADDING = 50
FUZZY_PADDING = 30

def GetDisplayPosition( window ):
    
    display_index = wx.Display.GetFromWindow( window )
    
    if display_index == wx.NOT_FOUND:
        
        display_index = 0 # default to primary
        
    
    display = wx.Display( display_index )
    
    rect = display.GetClientArea()
    
    return rect.GetPosition()
    
def GetDisplaySize( window ):
    
    display_index = wx.Display.GetFromWindow( window )
    
    if display_index == wx.NOT_FOUND:
        
        display_index = 0 # default to primary
        
    
    display = wx.Display( display_index )
    
    rect = display.GetClientArea()
    
    return rect.GetSize()
    
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
        
        max_width = parent_window_width - 2 * CHILD_POSITION_PADDING
        max_height = parent_window_height - 2 * CHILD_POSITION_PADDING
        
        ( width_gravity, height_gravity ) = gravity
        
        if width_gravity == -1:
            
            width = min_width
            
        else:
            
            width = int( width_gravity * max_width )
            
        
        if height_gravity == -1:
            
            height = min_height
            
        else:
            
            height = int( height_gravity * max_height )
            
        
    
    ( display_width, display_height ) = GetDisplaySize( tlw )
    
    width = min( display_width, width )
    height = min( display_height, height )
    
    return ( width, height )
    
def ExpandTLWIfPossible( tlw, frame_key, desired_size_delta ):
    
    new_options = HydrusGlobals.client_controller.GetNewOptions()
    
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
        
    
def SaveTLWSizeAndPosition( tlw, frame_key ):
    
    new_options = HydrusGlobals.client_controller.GetNewOptions()
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    maximised = tlw.IsMaximized()
    fullscreen = tlw.IsFullScreen()
    
    if not ( maximised or fullscreen ):
        
        safe_position = GetSafePosition( tlw.GetPositionTuple() )
        
        if safe_position != wx.DefaultPosition:
            
            last_size = tlw.GetSizeTuple()
            last_position = safe_position
            
        
    
    new_options.SetFrameLocation( frame_key, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
    
def SetTLWSizeAndPosition( tlw, frame_key ):
    
    new_options = HydrusGlobals.client_controller.GetNewOptions()
    
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
                
            
            ( parent_x, parent_y ) = parent_tlp.GetPositionTuple()
            
            tlw.SetPosition( ( parent_x + CHILD_POSITION_PADDING, parent_y + CHILD_POSITION_PADDING ) )
            
        else:
            
            safe_position = GetSafePosition( ( 0 + CHILD_POSITION_PADDING, 0 + CHILD_POSITION_PADDING ) )
            
            tlw.SetPosition( safe_position )
            
        
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
    
    def __init__( self, parent, title ):
        
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        
        if not HC.PLATFORM_LINUX and parent is not None:
            
            style |= wx.FRAME_FLOAT_ON_PARENT
            
        
        wx.Dialog.__init__( self, parent, title = title, style = style )
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self.SetIcon( wx.Icon( os.path.join( HC.STATIC_DIR, 'hydrus.ico' ), wx.BITMAP_TYPE_ICO ) )
        
        self.Bind( wx.EVT_BUTTON, self.EventDialogButton )
        
        self.Bind( wx.EVT_MENU_CLOSE, self.EventMenuClose )
        self.Bind( wx.EVT_MENU_HIGHLIGHT_ALL, self.EventMenuHighlight )
        self.Bind( wx.EVT_MENU_OPEN, self.EventMenuOpen )
        
        self._menu_stack = []
        self._menu_text_stack = []
        
        HydrusGlobals.client_controller.ResetIdleTimer()
        
    
    def EventMenuClose( self, event ):
        
        menu = event.GetMenu()
        
        if menu is not None and menu in self._menu_stack:
            
            index = self._menu_stack.index( menu )
            
            del self._menu_stack[ index ]
            
            previous_text = self._menu_text_stack.pop()
            
            status_bar = HydrusGlobals.client_controller.GetGUI().GetStatusBar()
            
            status_bar.SetStatusText( previous_text )
            
        
    
    def EventMenuHighlight( self, event ):
        
        status_bar = HydrusGlobals.client_controller.GetGUI().GetStatusBar()
        
        if len( self._menu_stack ) > 0:
            
            text = ''
            
            menu = self._menu_stack[-1]
            
            if menu is not None:
                
                menu_item = menu.FindItemById( event.GetMenuId() )
                
                if menu_item is not None:
                    
                    text = menu_item.GetHelp()
                    
                
            
            status_bar.SetStatusText( text )
            
        
    
    def EventMenuOpen( self, event ):
        
        menu = event.GetMenu()
        
        if menu is not None:
            
            status_bar = HydrusGlobals.client_controller.GetGUI().GetStatusBar()
            
            previous_text = status_bar.GetStatusText()
            
            self._menu_stack.append( menu )
            
            self._menu_text_stack.append( previous_text )
            
        
    
    def EventDialogButton( self, event ): self.EndModal( event.GetId() )
    
class DialogThatResizes( NewDialog ):
    
    def __init__( self, parent, title, frame_key ):
        
        self._frame_key = frame_key
        
        NewDialog.__init__( self, parent, title )
        
    
class DialogThatTakesScrollablePanel( DialogThatResizes ):
    
    def __init__( self, parent, title, frame_key ):
        
        self._panel = None
        
        DialogThatResizes.__init__( self, parent, title, frame_key )
        
        self._InitialiseButtons()
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( CC.EVT_SIZE_CHANGED, self.EventChildSizeChanged )
        
    
    def _GetButtonBox( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseButtons( self ):
        
        raise NotImplementedError()
        
    
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
                
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'ok':
                
                self.EventOk( None )
                
            else:
                
                event.Skip()
                
            
        
    
    def EventOk( self, event ):
        
        raise NotImplementedError()
        
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        buttonbox = self._GetButtonBox()
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( buttonbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        SetTLWSizeAndPosition( self, self._frame_key )
        
        self._panel.SetupScrolling()
        
    
class DialogThatTakesScrollablePanelClose( DialogThatTakesScrollablePanel ):
    
    def _GetButtonBox( self ):
        
        buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        buttonbox.AddF( self._close, CC.FLAGS_VCENTER )
        
        return buttonbox
        
    
    def _InitialiseButtons( self ):
        
        self._close = wx.Button( self, id = wx.ID_OK, label = 'close' )
        self._close.Bind( wx.EVT_BUTTON, self.EventOk )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL )
        self._cancel.Hide()
        
    
class DialogNullipotent( DialogThatTakesScrollablePanelClose ):
    
    def __init__( self, parent, title ):
        
        DialogThatTakesScrollablePanelClose.__init__( self, parent, title, 'regular_dialog' )
        
    
    def EventOk( self, event ):
        
        SaveTLWSizeAndPosition( self, self._frame_key )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogThatTakesScrollablePanelApplyCancel( DialogThatTakesScrollablePanel ):
    
    def _GetButtonBox( self ):
        
        buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        buttonbox.AddF( self._apply, CC.FLAGS_VCENTER )
        buttonbox.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        return buttonbox
        
    
    def _InitialiseButtons( self ):
        
        self._apply = wx.Button( self, id = wx.ID_OK, label = 'apply' )
        self._apply.Bind( wx.EVT_BUTTON, self.EventOk )
        self._apply.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
    
class DialogEdit( DialogThatTakesScrollablePanelApplyCancel ):
    
    def __init__( self, parent, title ):
        
        DialogThatTakesScrollablePanelApplyCancel.__init__( self, parent, title, 'regular_dialog' )
        
    
    def EventOk( self, event ):
        
        try:
            
            value = self._panel.GetValue()
            
        except HydrusExceptions.VetoException:
            
            return
            
        
        SaveTLWSizeAndPosition( self, self._frame_key )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManage( DialogThatTakesScrollablePanelApplyCancel ):
    
    def EventOk( self, event ):
        
        self._panel.CommitChanges()
        
        SaveTLWSizeAndPosition( self, self._frame_key )
        
        self.EndModal( wx.ID_OK )
        
    
class Frame( wx.Frame ):
    
    def __init__( self, parent, title, float_on_parent = True ):
        
        style = wx.DEFAULT_FRAME_STYLE
        
        if float_on_parent:
            
            style |= wx.FRAME_FLOAT_ON_PARENT
            
        
        wx.Frame.__init__( self, parent, title = title, style = style )
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self.SetIcon( wx.Icon( os.path.join( HC.STATIC_DIR, 'hydrus.ico' ), wx.BITMAP_TYPE_ICO ) )
        
        self.Bind( wx.EVT_MENU_CLOSE, self.EventMenuClose )
        self.Bind( wx.EVT_MENU_HIGHLIGHT_ALL, self.EventMenuHighlight )
        self.Bind( wx.EVT_MENU_OPEN, self.EventMenuOpen )
        
        self._menu_stack = []
        self._menu_text_stack = []
        
        HydrusGlobals.client_controller.ResetIdleTimer()
        
    
    def EventMenuClose( self, event ):
        
        menu = event.GetMenu()
        
        if menu is not None and menu in self._menu_stack:
            
            index = self._menu_stack.index( menu )
            
            del self._menu_stack[ index ]
            
            previous_text = self._menu_text_stack.pop()
            
            status_bar = HydrusGlobals.client_controller.GetGUI().GetStatusBar()
            
            status_bar.SetStatusText( previous_text )
            
        
    
    def EventMenuHighlight( self, event ):
        
        status_bar = HydrusGlobals.client_controller.GetGUI().GetStatusBar()
        
        if len( self._menu_stack ) > 0:
            
            text = ''
            
            menu = self._menu_stack[-1]
            
            if menu is not None:
                
                menu_item = menu.FindItemById( event.GetMenuId() )
                
                if menu_item is not None:
                    
                    text = menu_item.GetHelp()
                    
                
            
            status_bar.SetStatusText( text )
            
        
    
    def EventMenuOpen( self, event ):
        
        menu = event.GetMenu()
        
        if menu is not None:
            
            status_bar = HydrusGlobals.client_controller.GetGUI().GetStatusBar()
            
            previous_text = status_bar.GetStatusText()
            
            self._menu_stack.append( menu )
            
            self._menu_text_stack.append( previous_text )
            
        
    
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
    
    def __init__( self, parent, title, frame_key, float_on_parent = True ):
        
        self._panel = None
        
        FrameThatResizes.__init__( self, parent, title, frame_key, float_on_parent )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'close' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventCloseButton )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( CC.EVT_SIZE_CHANGED, self.EventChildSizeChanged )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
    
    def EventCharHook( self, event ):
        
        if event.KeyCode == wx.WXK_ESCAPE:
            
            self.Close()
            
        else:
            
            event.Skip()
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'ok':
                
                self.Close()
                
            else:
                
                event.Skip()
                
            
        
    
    def EventCloseButton( self, event ):
        
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
                
            
        
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._ok, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        SetTLWSizeAndPosition( self, self._frame_key )
        
        self.Show( True )
        
        self._panel.SetupScrolling()
        
    
