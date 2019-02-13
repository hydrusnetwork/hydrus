from . import ClientConstants as CC
from . import ClientData
from . import ClientDragDrop
from . import ClientGUICanvas
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIListBoxes
from . import ClientGUIMenus
from . import ClientGUITopLevelWindows
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUIScrolledPanelsManagement
from . import ClientMedia
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import os
import wx

class FullscreenHoverFrame( wx.Frame ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        if HC.PLATFORM_WINDOWS:
            
            border_style = wx.BORDER_RAISED
            
        else:
            
            border_style = wx.BORDER_SIMPLE
            
        
        wx.Frame.__init__( self, parent, style = wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | border_style )
        
        self._my_canvas = my_canvas
        self._canvas_key = canvas_key
        self._current_media = None
        
        self._last_ideal_position = None
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        self.SetCursor( wx.Cursor( wx.CURSOR_ARROW ) )
        
        self._hide_until =  None
        
        HG.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        raise NotImplementedError()
        
    
    def _SizeAndPosition( self ):
        
        if self.GetParent().IsShown():
            
            ( should_resize, my_ideal_size, my_ideal_position ) = self._GetIdealSizeAndPosition()
            
            if should_resize:
                
                self.Fit()
                
                self.SetSize( my_ideal_size )
                
            
            self.SetPosition( my_ideal_position )
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = media
            
        
    
    def TIMERUIUpdate( self ):
        
        new_options = HG.client_controller.new_options
        
        if new_options.GetBoolean( 'always_show_hover_windows' ):
            
            self._SizeAndPosition()
            
            self.Show()
            
            return
            
        
        if self._hide_until is not None:
            
            if HydrusData.TimeHasPassed( self._hide_until ):
                
                self._hide_until =  None
                
            else:
                
                return
                
            
        
        if self._current_media is None or not self.GetParent().IsShown():
            
            if self.IsShown():
                
                if HG.hover_window_report_mode:
                    
                    HydrusData.ShowText( repr( self ) + ' - hiding because nothing to show or parent hidden.' )
                    
                
                self.Hide()
                
            
        else:
            
            ( mouse_x, mouse_y ) = wx.GetMousePosition()
            
            ( my_width, my_height ) = self.GetSize()
            
            ( should_resize, ( my_ideal_width, my_ideal_height ), ( my_ideal_x, my_ideal_y ) ) = self._GetIdealSizeAndPosition()
            
            if my_ideal_width == -1:
                
                my_ideal_width = max( my_width, 50 )
                
            
            if my_ideal_height == -1:
                
                my_ideal_height = max( my_height, 50 )
                
            
            ( my_x, my_y ) = self.GetPosition()
            
            in_ideal_x = my_ideal_x <= mouse_x and mouse_x <= my_ideal_x + my_ideal_width
            in_ideal_y = my_ideal_y <= mouse_y and mouse_y <= my_ideal_y + my_ideal_height
            
            in_actual_x = my_x <= mouse_x and mouse_x <= my_x + my_width
            in_actual_y = my_y <= mouse_y and mouse_y <= my_y + my_height
            
            # we test both ideal and actual here because setposition is not always honoured by the OS
            # for instance, in Linux on a fullscreen view, the top taskbar is hidden, but when hover window is shown, it takes focus and causes taskbar to reappear
            # the reappearance shuffles the screen coordinates down a bit so the hover sits +20px y despite wanting to be lined up with the underlying fullscreen viewer
            # wew lad
            
            in_position = ( in_ideal_x or in_actual_x ) and ( in_ideal_y or in_actual_y )
            
            menu_open = HG.client_controller.MenuIsOpen()
            
            dialog_open = False
            
            tlps = wx.GetTopLevelWindows()
            
            for tlp in tlps:
                
                if isinstance( tlp, wx.Dialog ):
                    
                    dialog_open = True
                    
                
            
            mime = self._current_media.GetMime()
            
            mouse_is_over_interactable_media = mime == HC.APPLICATION_FLASH and self.GetParent().MouseIsOverMedia()
            
            mouse_is_near_animation_bar = self.GetParent().MouseIsNearAnimationBar()
            
            mouse_is_over_something_important = mouse_is_over_interactable_media or mouse_is_near_animation_bar
            
            focus_is_good = ClientGUICommon.TLPHasFocus( self ) or ClientGUICommon.TLPHasFocus( self.GetParent() )
            
            ready_to_show = in_position and not mouse_is_over_something_important and focus_is_good and not dialog_open and not menu_open
            ready_to_hide = not menu_open and ( not in_position or dialog_open or not focus_is_good )
            
            def get_logic_report_string():
                
                tuples = []
                
                tuples.append( ( 'in position: ', in_position ) )
                tuples.append( ( 'menu open: ', menu_open ) )
                tuples.append( ( 'dialog open: ', dialog_open ) )
                tuples.append( ( 'mouse over interactable media: ', mouse_is_over_interactable_media ) )
                tuples.append( ( 'mouse near animation bar: ', mouse_is_near_animation_bar ) )
                tuples.append( ( 'focus is good: ', focus_is_good ) )
                
                message = os.linesep * 2 + os.linesep.join( ( a + str( b ) for ( a, b ) in tuples ) ) + os.linesep
                
                return message
                
            
            if ready_to_show:
                
                self._SizeAndPosition()
                
                if not self.IsShown():
                    
                    if HG.hover_window_report_mode:
                        
                        HydrusData.ShowText( repr( self ) + ' - showing.' + get_logic_report_string() )
                        
                    
                    self.Show()
                    
                
            elif ready_to_hide:
                
                if self.IsShown():
                    
                    if HG.hover_window_report_mode:
                        
                        HydrusData.ShowText( repr( self ) + ' - hiding.' + get_logic_report_string() )
                        
                    
                    self.Hide()
                    
                
            
        
        
    
class FullscreenHoverFrameTop( FullscreenHoverFrame ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        FullscreenHoverFrame.__init__( self, parent, my_canvas, canvas_key )
        
        self._current_zoom = 1.0
        self._current_index_string = ''
        
        self._top_hbox = wx.BoxSizer( wx.HORIZONTAL )
        self._title_text = ClientGUICommon.BetterStaticText( self, 'title' )
        self._info_text = ClientGUICommon.BetterStaticText( self, 'info' )
        self._additional_info_text = ClientGUICommon.BetterStaticText( self, '', style = wx.ALIGN_CENTER )
        self._button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._PopulateLeftButtons()
        self._top_hbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_BOTH_WAYS )
        self._PopulateCenterButtons()
        self._top_hbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_BOTH_WAYS )
        self._PopulateRightButtons()
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._top_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._title_text, CC.FLAGS_CENTER )
        vbox.Add( self._info_text, CC.FLAGS_CENTER )
        vbox.Add( self._additional_info_text, CC.FLAGS_CENTER )
        vbox.Add( self._button_hbox, CC.FLAGS_CENTER )
        
        self.SetSizer( vbox )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'SetCurrentZoom', 'canvas_new_zoom' )
        HG.client_controller.sub( self, 'SetIndexString', 'canvas_new_index_string' )
        
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        
    
    def _Archive( self ):
        
        if self._current_media.HasInbox():
            
            command = ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_file' )
            
        else:
            
            command = ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'inbox_file' )
            
        
        HG.client_controller.pub( 'canvas_application_command', command, self._canvas_key )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        parent = self.GetParent()
        
        ( parent_width, parent_height ) = parent.GetClientSize()
        
        ( my_width, my_height ) = self.GetSize()
        
        my_ideal_width = int( parent_width * 0.6 )
        
        should_resize = my_ideal_width != my_width
        
        ideal_size = ( my_ideal_width, -1 )
        ideal_position = ClientGUICommon.ClientToScreen( parent, ( int( parent_width * 0.2 ), 0 ) )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _ManageShortcuts( self ):
        
        with ClientGUITopLevelWindows.DialogManage( self, 'manage shortcuts' ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageShortcutsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _PopulateCenterButtons( self ):
        
        self._archive_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.archive, self._Archive )
        
        self._trash_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.delete, HG.client_controller.pub, 'canvas_delete', self._canvas_key )
        self._trash_button.SetToolTip( 'send to trash' )
        
        self._delete_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.trash_delete, HG.client_controller.pub, 'canvas_delete', self._canvas_key )
        self._delete_button.SetToolTip( 'delete completely' )
        
        self._undelete_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.undelete, HG.client_controller.pub, 'canvas_undelete', self._canvas_key )
        self._undelete_button.SetToolTip( 'undelete' )
        
        self._top_hbox.Add( self._archive_button, CC.FLAGS_VCENTER )
        self._top_hbox.Add( self._trash_button, CC.FLAGS_VCENTER )
        self._top_hbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        self._top_hbox.Add( self._undelete_button, CC.FLAGS_VCENTER )
        
    
    def _PopulateLeftButtons( self ):
        
        self._index_text = ClientGUICommon.BetterStaticText( self, 'index' )
        
        self._top_hbox.Add( self._index_text, CC.FLAGS_VCENTER )
        
    
    def _PopulateRightButtons( self ):
        
        self._zoom_text = ClientGUICommon.BetterStaticText( self, 'zoom' )
        
        zoom_in = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.zoom_in, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_in' ), self._canvas_key )
        zoom_in.SetToolTip( 'zoom in' )
        
        zoom_out = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.zoom_out, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_out' ), self._canvas_key )
        zoom_out.SetToolTip( 'zoom out' )
        
        zoom_switch = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.zoom_switch, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'switch_between_100_percent_and_canvas_zoom' ), self._canvas_key )
        zoom_switch.SetToolTip( 'zoom switch' )
        
        shortcuts = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.keyboard, self._ShowShortcutMenu )
        shortcuts.SetToolTip( 'shortcuts' )
        
        fullscreen_switch = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.fullscreen_switch, HG.client_controller.pub, 'canvas_fullscreen_switch', self._canvas_key )
        fullscreen_switch.SetToolTip( 'fullscreen switch' )
        
        open_externally = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.open_externally, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'open_file_in_external_program' ), self._canvas_key )
        open_externally.SetToolTip( 'open externally' )
        
        drag_button = wx.BitmapButton( self, bitmap = CC.GlobalBMPs.drag )
        drag_button.SetToolTip( 'drag from here to export file' )
        drag_button.Bind( wx.EVT_LEFT_DOWN, self.EventDragButton )
        
        close = ClientGUICommon.BetterButton( self, 'X', HG.client_controller.pub, 'canvas_close', self._canvas_key )
        close.SetToolTip( 'close' )
        
        self._top_hbox.Add( self._zoom_text, CC.FLAGS_VCENTER )
        self._top_hbox.Add( zoom_in, CC.FLAGS_VCENTER )
        self._top_hbox.Add( zoom_out, CC.FLAGS_VCENTER )
        self._top_hbox.Add( zoom_switch, CC.FLAGS_VCENTER )
        self._top_hbox.Add( shortcuts, CC.FLAGS_VCENTER )
        self._top_hbox.Add( fullscreen_switch, CC.FLAGS_VCENTER )
        self._top_hbox.Add( open_externally, CC.FLAGS_VCENTER )
        self._top_hbox.Add( drag_button, CC.FLAGS_VCENTER )
        self._top_hbox.Add( close, CC.FLAGS_VCENTER )
        
    
    def _ResetArchiveButton( self ):
        
        if self._current_media.HasInbox():
            
            ClientGUICommon.SetBitmapButtonBitmap( self._archive_button, CC.GlobalBMPs.archive )
            self._archive_button.SetToolTip( 'archive' )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._archive_button, CC.GlobalBMPs.to_inbox )
            self._archive_button.SetToolTip( 'return to inbox' )
            
        
    
    def _ResetButtons( self ):
        
        if self._current_media is not None:
            
            self._ResetArchiveButton()
            
            current_locations = self._current_media.GetLocationsManager().GetCurrent()
            
            if CC.LOCAL_FILE_SERVICE_KEY in current_locations:
                
                self._trash_button.Show()
                self._delete_button.Hide()
                self._undelete_button.Hide()
                
            elif CC.TRASH_SERVICE_KEY in current_locations:
                
                self._trash_button.Hide()
                self._delete_button.Show()
                self._undelete_button.Show()
                
            
            self.Fit()
            
            self._SizeAndPosition()
            
        
    
    def _ResetText( self ):
        
        if self._current_media is None:
            
            self._title_text.Hide()
            self._info_text.Hide()
            
        else:
            
            label = self._current_media.GetTitleString()
            
            if len( label ) > 0:
                
                self._title_text.SetLabelText( label )
                
                self._title_text.Show()
                
            else: self._title_text.Hide()
            
            lines = self._current_media.GetPrettyInfoLines()
            
            label = ' | '.join( lines )
            
            self._info_text.SetLabelText( label )
            
            self._info_text.Show()
            
            if self._additional_info_text.GetLabelText() == '':
                
                self._additional_info_text.Hide()
                
            else:
                
                self._additional_info_text.Show()
                
            
        
    
    def _FlipActiveDefaultCustomShortcut( self, name ):
        
        new_options = HG.client_controller.new_options
        
        default_media_viewer_custom_shortcuts = list( new_options.GetStringList( 'default_media_viewer_custom_shortcuts' ) )
        
        if name in default_media_viewer_custom_shortcuts:
            
            default_media_viewer_custom_shortcuts.remove( name )
            
        else:
            
            default_media_viewer_custom_shortcuts.append( name )
            
            default_media_viewer_custom_shortcuts.sort()
            
        
        new_options.SetStringList( 'default_media_viewer_custom_shortcuts', default_media_viewer_custom_shortcuts )
        
    
    def _ShowShortcutMenu( self ):
        
        all_shortcut_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS )
        
        custom_shortcuts_names = [ name for name in all_shortcut_names if name not in CC.SHORTCUTS_RESERVED_NAMES ]
        
        menu = wx.Menu()
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'edit shortcuts', 'edit your sets of shortcuts, and change what shortcuts are currently active on this media viewer', self._ManageShortcuts )
        
        if len( custom_shortcuts_names ) > 0:
            
            my_canvas_active_custom_shortcuts = self._my_canvas.GetActiveCustomShortcutNames()
            default_media_viewer_custom_shortcuts = HG.client_controller.new_options.GetStringList( 'default_media_viewer_custom_shortcuts' )
            
            current_menu = wx.Menu()
            
            for name in custom_shortcuts_names:
                
                ClientGUIMenus.AppendMenuCheckItem( self, current_menu, name, 'turn this shortcut set on/off', name in my_canvas_active_custom_shortcuts, self._my_canvas.FlipActiveCustomShortcutName, name )
                
            
            ClientGUIMenus.AppendMenu( menu, current_menu, 'set current shortcuts' )
            
            defaults_menu = wx.Menu()
            
            for name in custom_shortcuts_names:
                
                ClientGUIMenus.AppendMenuCheckItem( self, defaults_menu, name, 'turn this shortcut set on/off by default', name in default_media_viewer_custom_shortcuts, self._FlipActiveDefaultCustomShortcut, name )
                
            
            ClientGUIMenus.AppendMenu( menu, defaults_menu, 'set default shortcuts' )
            
        
        HG.client_controller.PopupMenu( self, menu )
        
    
    def EventDragButton( self, event ):
        
        if self._current_media is None:
            
            event.Skip()
            
            return
            
        
        page_key = None
        
        media = [ self._current_media ]
        
        alt_down = event.AltDown()
        
        result = ClientDragDrop.DoFileExportDragDrop( self, page_key, media, alt_down )
        
        if result not in ( wx.DragError, wx.DragNone ):
            
            HG.client_controller.pub( 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pause_media' ), self._canvas_key )
            
        
    
    def EventMouseWheel( self, event ):
        
        event.ResumePropagation( 1 )
        event.Skip()
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetButtons()
                
            
        
    
    def SetCurrentZoom( self, canvas_key, zoom ):
        
        if canvas_key == self._canvas_key:
            
            self._current_zoom = zoom
            
            label = ClientData.ConvertZoomToPercentage( self._current_zoom )
            
            self._zoom_text.SetLabelText( label )
            
            self._top_hbox.Layout()
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            FullscreenHoverFrame.SetDisplayMedia( self, canvas_key, media )
            
            self._ResetText()
            
            self._ResetButtons()
            
        
    
    def SetIndexString( self, canvas_key, text ):
        
        if canvas_key == self._canvas_key:
            
            self._current_index_string = text
            
            self._index_text.SetLabelText( self._current_index_string )
            
            self._top_hbox.Layout()
            
        
    
class FullscreenHoverFrameTopArchiveDeleteFilter( FullscreenHoverFrameTop ):
    
    def _Archive( self ):
        
        HG.client_controller.pub( 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_file' ), self._canvas_key )
        
    
    def _PopulateLeftButtons( self ):
        
        self._back_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.previous, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_back' ), self._canvas_key )
        self._back_button.SetToolTip( 'back' )
        
        self._top_hbox.Add( self._back_button, CC.FLAGS_VCENTER )
        
        FullscreenHoverFrameTop._PopulateLeftButtons( self )
        
        self._skip_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.next_bmp, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_skip' ), self._canvas_key )
        self._skip_button.SetToolTip( 'skip' )
        
        self._top_hbox.Add( self._skip_button, CC.FLAGS_VCENTER )
        
    
    def _ResetArchiveButton( self ):
        
        ClientGUICommon.SetBitmapButtonBitmap( self._archive_button, CC.GlobalBMPs.archive )
        self._archive_button.SetToolTip( 'archive' )
        
    
class FullscreenHoverFrameTopNavigable( FullscreenHoverFrameTop ):
    
    def _PopulateLeftButtons( self ):
        
        self._previous_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.previous, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ), self._canvas_key )
        self._previous_button.SetToolTip( 'previous' )
        
        self._index_text = ClientGUICommon.BetterStaticText( self, 'index' )
        
        self._next_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.next_bmp, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ), self._canvas_key )
        self._next_button.SetToolTip( 'next' )
        
        self._top_hbox.Add( self._previous_button, CC.FLAGS_VCENTER )
        self._top_hbox.Add( self._index_text, CC.FLAGS_VCENTER )
        self._top_hbox.Add( self._next_button, CC.FLAGS_VCENTER )
        
    
class FullscreenHoverFrameTopDuplicatesFilter( FullscreenHoverFrameTopNavigable ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        FullscreenHoverFrameTopNavigable.__init__( self, parent, my_canvas, canvas_key )
        
        HG.client_controller.sub( self, 'SetDuplicatePair', 'canvas_new_duplicate_pair' )
        
    
    def _PopulateCenterButtons( self ):
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit duplicate action options for \'this is better\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_BETTER ) ) )
        menu_items.append( ( 'normal', 'edit duplicate action options for \'same quality\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_SAME_QUALITY ) ) )
        menu_items.append( ( 'normal', 'edit duplicate action options for \'alternates\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_ALTERNATE ) ) )
        menu_items.append( ( 'normal', 'edit duplicate action options for \'not duplicates\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_NOT_DUPLICATE ) ) )
        menu_items.append( ( 'separator', None, None, None ) )
        menu_items.append( ( 'normal', 'edit background lighten/darken switch intensity', 'edit how much the background will brighten or darken as you switch between the pair', self._EditBackgroundSwitchIntensity ) )
        
        cog_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.cog, menu_items )
        
        self._top_hbox.Add( cog_button, CC.FLAGS_SIZER_VCENTER )
        
        FullscreenHoverFrameTopNavigable._PopulateCenterButtons( self )
        
        dupe_commands = []
        
        dupe_commands.append( ( 'this is better', 'Set that the current file you are looking at is better than the other in the pair.', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_this_is_better' ) ) )
        dupe_commands.append( ( 'same quality', 'Set that the two files are duplicates of very similar quality.', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_exactly_the_same' ) ) )
        dupe_commands.append( ( 'alternates', 'Set that the files are not duplicates, but that one is derived from the other or that they are both descendants of a common ancestor.', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_alternates' ) ) )
        dupe_commands.append( ( 'not duplicates', 'Set that the files are not duplicates or otherwise related--that this pair is a false-positive match.', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_not_dupes' ) ) )
        dupe_commands.append( ( 'custom action', 'Choose one of the other actions but customise the merge and delete options for this specific decision.', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_custom_action' ) ) )
        
        for ( label, tooltip, command ) in dupe_commands:
            
            command_button = ClientGUICommon.BetterButton( self, label, HG.client_controller.pub, 'canvas_application_command', command, self._canvas_key )
            
            command_button.SetToolTip( tooltip )
            
            self._button_hbox.Add( command_button, CC.FLAGS_VCENTER )
            
        
    
    def _EditBackgroundSwitchIntensity( self ):
        
        new_options = HG.client_controller.new_options
        
        value = new_options.GetNoneableInteger( 'duplicate_background_switch_intensity' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit lighten/darken intensity' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditNoneableIntegerPanel( dlg, value, message = 'intensity: ', none_phrase = 'do not change', min = 1, max = 9 )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_value = panel.GetValue()
                
                new_options.SetNoneableInteger( 'duplicate_background_switch_intensity', new_value )
                
            
        
    
    def _EditMergeOptions( self, duplicate_type ):
        
        new_options = HG.client_controller.new_options
        
        duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg, duplicate_type, duplicate_action_options )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                duplicate_action_options = panel.GetValue()
                
                new_options.SetDuplicateActionOptions( duplicate_type, duplicate_action_options )
                
            
        
    
    def _PopulateLeftButtons( self ):
        
        self._first_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.first, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_back' ), self._canvas_key )
        self._first_button.SetToolTip( 'go back a pair' )
        
        self._top_hbox.Add( self._first_button, CC.FLAGS_VCENTER )
        
        FullscreenHoverFrameTopNavigable._PopulateLeftButtons( self )
        
        self._last_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.last, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_skip' ), self._canvas_key )
        self._last_button.SetToolTip( 'show a different pair' )
        
        self._top_hbox.Add( self._last_button, CC.FLAGS_VCENTER )
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            if media is None:
                
                self._additional_info_text.SetLabelText( '' )
                
            
            FullscreenHoverFrameTopNavigable.SetDisplayMedia( self, canvas_key, media )
            
        
    
    def SetDuplicatePair( self, canvas_key, shown_media, comparison_media ):
        
        if canvas_key == self._canvas_key:
            
            ( statements, score ) = ClientMedia.GetDuplicateComparisonStatements( shown_media, comparison_media )
            
            self._additional_info_text.SetLabelText( os.linesep.join( statements ) )
            
            self._ResetText()
            
            self._ResetButtons()
            
        
    
class FullscreenHoverFrameTopNavigableList( FullscreenHoverFrameTopNavigable ):
    
    def _PopulateLeftButtons( self ):
        
        self._first_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.first, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_first' ), self._canvas_key )
        self._first_button.SetToolTip( 'first' )
        
        self._top_hbox.Add( self._first_button, CC.FLAGS_VCENTER )
        
        FullscreenHoverFrameTopNavigable._PopulateLeftButtons( self )
        
        self._last_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.last, HG.client_controller.pub, 'canvas_application_command', ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_last' ), self._canvas_key )
        self._last_button.SetToolTip( 'last' )
        
        self._top_hbox.Add( self._last_button, CC.FLAGS_VCENTER )
        
    
class FullscreenHoverFrameTopRight( FullscreenHoverFrame ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        FullscreenHoverFrame.__init__( self, parent, my_canvas, canvas_key )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._icon_panel = wx.Panel( self )
        
        self._trash_icon = ClientGUICommon.BufferedWindowIcon( self._icon_panel, CC.GlobalBMPs.trash )
        self._inbox_icon = ClientGUICommon.BufferedWindowIcon( self._icon_panel, CC.GlobalBMPs.inbox )
        
        icon_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        icon_hbox.Add( ( 16, 16 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        icon_hbox.Add( self._trash_icon, CC.FLAGS_VCENTER )
        icon_hbox.Add( self._inbox_icon, CC.FLAGS_VCENTER )
        
        self._icon_panel.SetSizer( icon_hbox )
        
        # repo strings
        
        self._file_repos = wx.StaticText( self, label = '', style = wx.ALIGN_RIGHT )
        
        # urls
        
        self._last_seen_urls = []
        self._urls_vbox = wx.BoxSizer( wx.VERTICAL )
        
        # likes
        
        like_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        like_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ), randomised = False )
        
        if len( like_services ) > 0:
            
            like_hbox.Add( ( 16, 16 ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        for service in like_services:
            
            service_key = service.GetServiceKey()
            
            control = ClientGUICommon.RatingLikeCanvas( self, service_key, canvas_key )
            
            like_hbox.Add( control, CC.FLAGS_NONE )
            
        
        # each numerical one in turn
        
        vbox.Add( like_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        numerical_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ), randomised = False )
        
        for service in numerical_services:
            
            service_key = service.GetServiceKey()
            
            control = ClientGUICommon.RatingNumericalCanvas( self, service_key, canvas_key )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( ( 16, 16 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            hbox.Add( control, CC.FLAGS_NONE )
            
            vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        vbox.Add( self._icon_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._file_repos, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._urls_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self._ResetData()
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        parent = self.GetParent()
        
        ( parent_width, parent_height ) = parent.GetClientSize()
        
        ( my_width, my_height ) = self.GetSize()
        
        my_ideal_width = int( parent_width * 0.2 )
        
        should_resize = my_ideal_width != my_width
        
        ideal_size = ( my_ideal_width, -1 )
        ideal_position = ClientGUICommon.ClientToScreen( parent, ( int( parent_width * 0.8 ), 0 ) )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _ResetData( self ):
        
        if self._current_media is not None:
            
            has_inbox = self._current_media.HasInbox()
            has_trash = CC.TRASH_SERVICE_KEY in self._current_media.GetLocationsManager().GetCurrent()
            
            if has_inbox or has_trash:
                
                self._icon_panel.Show()
                
                if has_inbox:
                    
                    self._inbox_icon.Show()
                    
                else:
                    
                    self._inbox_icon.Hide()
                    
                
                if has_trash:
                    
                    self._trash_icon.Show()
                    
                else:
                    
                    self._trash_icon.Hide()
                    
                
            else:
                
                self._icon_panel.Hide()
                
            
            remote_strings = self._current_media.GetLocationsManager().GetRemoteLocationStrings()
            
            if len( remote_strings ) == 0:
                
                self._file_repos.Hide()
                
            else:
                
                remote_string = os.linesep.join( remote_strings )
                
                self._file_repos.SetLabelText( remote_string )
                
                self._file_repos.Show()
                
            
            # urls
            
            urls = self._current_media.GetLocationsManager().GetURLs()
            
            if urls != self._last_seen_urls:
                
                self._last_seen_urls = list( urls )
                
                self._urls_vbox.Clear( delete_windows = True )
                
                url_tuples = HG.client_controller.network_engine.domain_manager.ConvertURLsToMediaViewerTuples( urls )
                
                for ( display_string, url ) in url_tuples:
                    
                    link = ClientGUICommon.BetterHyperLink( self, display_string, url )
                    
                    self._urls_vbox.Add( link, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
            
            self.Fit()
            
        
        self._SizeAndPosition()
        
    
    def EventMouseWheel( self, event ):
        
        event.ResumePropagation( 1 )
        event.Skip()
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                # ratings updates do not change the shape of this hover but file changes of several kinds do
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates if content_update.GetDataType() == HC.CONTENT_TYPE_FILES ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetData()
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            FullscreenHoverFrame.SetDisplayMedia( self, canvas_key, media )
            
            self._ResetData()
            
        
    
class FullscreenHoverFrameTags( FullscreenHoverFrame ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        FullscreenHoverFrame.__init__( self, parent, my_canvas, canvas_key )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._tags = ClientGUIListBoxes.ListBoxTagsSelectionHoverFrame( self, self._canvas_key )
        
        vbox.Add( self._tags, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        parent = self.GetParent()
        
        ( parent_width, parent_height ) = parent.GetClientSize()
        
        ( my_width, my_height ) = self.GetSize()
        
        my_ideal_width = int( parent_width * 0.2 )
        
        my_ideal_height = parent_height
        
        should_resize = my_ideal_width != my_width or my_ideal_height != my_height
        
        ideal_size = ( my_ideal_width, my_ideal_height )
        ideal_position = ClientGUICommon.ClientToScreen( parent, ( 0, 0 ) )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _ResetTags( self ):
        
        if self._current_media is not None:
            
            self._tags.SetTagsByMedia( [ self._current_media ], force_reload = True )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetTags()
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            FullscreenHoverFrame.SetDisplayMedia( self, canvas_key, media )
            
            self._ResetTags()
            
        
    
