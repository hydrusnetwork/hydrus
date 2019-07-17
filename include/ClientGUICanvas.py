from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import ClientCaches
from . import ClientConstants as CC
from . import ClientData
from . import ClientDuplicates
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIDialogsManage
from . import ClientGUIDialogsQuick
from . import ClientGUIFunctions
from . import ClientGUIHoverFrames
from . import ClientGUIMedia
from . import ClientGUIMenus
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsButtonQuestions
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUIScrolledPanelsManagement
from . import ClientGUIShortcuts
from . import ClientGUITags
from . import ClientGUITopLevelWindows
from . import ClientMedia
from . import ClientPaths
from . import ClientRatings
from . import ClientRendering
from . import ClientSearch
from . import ClientTags
from . import ClientThreading
import gc
from . import HydrusImageHandling
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTags
import os
import wx

FLASHWIN_OK = False
# this is currently a bit dodgy in wxPython 4.0, so disabled for now
'''
if HC.PLATFORM_WINDOWS:
    
    try:
        
        import wx.lib.flashwin
        
        FLASHWIN_OK = True
        
    except Exception as e:
        
        HydrusData.Print( 'Flashwin did not load OK:' )
        
        HydrusData.PrintException( e )
        
'''
    
ID_TIMER_HOVER_SHOW = wx.NewId()

ANIMATED_SCANBAR_HEIGHT = 20
ANIMATED_SCANBAR_CARET_WIDTH = 10

OPEN_EXTERNALLY_BUTTON_SIZE = ( 200, 45 )

def CalculateCanvasMediaSize( media, canvas_size ):
    
    ( canvas_width, canvas_height ) = canvas_size
    
    if ShouldHaveAnimationBar( media ):
        
        canvas_height -= ANIMATED_SCANBAR_HEIGHT
        
    
    if media.GetMime() == HC.APPLICATION_FLASH:
        
        canvas_height -= 10
        canvas_width -= 10
        
    
    canvas_width = max( canvas_width, 80 )
    canvas_height = max( canvas_height, 60 )
    
    return ( canvas_width, canvas_height )
    
def CalculateCanvasZooms( canvas, media, show_action ):
    
    if media is None:
        
        return ( 1.0, 1.0 )
        
    
    if show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
        
        return ( 1.0, 1.0 )
        
    
    ( media_width, media_height ) = media.GetResolution()
    
    if media_width == 0 or media_height == 0:
        
        return ( 1.0, 1.0 )
        
    
    new_options = HG.client_controller.new_options
    
    ( canvas_width, canvas_height ) = CalculateCanvasMediaSize( media, canvas.GetClientSize() )
    
    width_zoom = canvas_width / media_width
    
    height_zoom = canvas_height / media_height
    
    canvas_zoom = min( ( width_zoom, height_zoom ) )
    
    #
    
    mime = media.GetMime()
    
    ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = new_options.GetMediaZoomOptions( mime )
    
    if exact_zooms_only:
        
        max_regular_zoom = 1.0
        
        if canvas_zoom > 1.0:
            
            while max_regular_zoom * 2 < canvas_zoom:
                
                max_regular_zoom *= 2
                
            
        elif canvas_zoom < 1.0:
            
            while max_regular_zoom > canvas_zoom:
                
                max_regular_zoom /= 2
                
            
        
    else:
        
        regular_zooms = new_options.GetMediaZooms()
        
        valid_regular_zooms = [ zoom for zoom in regular_zooms if zoom < canvas_zoom ]
        
        if len( valid_regular_zooms ) > 0:
            
            max_regular_zoom = max( valid_regular_zooms )
            
        else:
            
            max_regular_zoom = canvas_zoom
            
        
    
    if canvas.PREVIEW_WINDOW:
        
        scale_up_action = preview_scale_up
        scale_down_action = preview_scale_down
        
    else:
        
        scale_up_action = media_scale_up
        scale_down_action = media_scale_down
        
    
    can_be_scaled_down = media_width > canvas_width or media_height > canvas_height
    can_be_scaled_up = media_width < canvas_width and media_height < canvas_height
    
    #
    
    if can_be_scaled_up:
        
        scale_action = scale_up_action
        
    elif can_be_scaled_down:
        
        scale_action = scale_down_action
        
    else:
        
        scale_action = CC.MEDIA_VIEWER_SCALE_100
        
    
    if scale_action == CC.MEDIA_VIEWER_SCALE_100:
        
        default_zoom = 1.0
        
    elif scale_action == CC.MEDIA_VIEWER_SCALE_MAX_REGULAR:
        
        default_zoom = max_regular_zoom
        
    else:
        
        default_zoom = canvas_zoom
        
    
    return ( default_zoom, canvas_zoom )
    
def CalculateMediaContainerSize( media, zoom, action ):
    
    if action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
        
        raise Exception( 'This media should not be shown in the media viewer!' )
        
    elif action == CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON:
        
        ( width, height ) = OPEN_EXTERNALLY_BUTTON_SIZE
        
        if media.GetMime() in HC.MIMES_WITH_THUMBNAILS:
            
            ( thumb_width, thumb_height ) = HydrusImageHandling.GetThumbnailResolution( media.GetResolution(), HG.client_controller.options[ 'thumbnail_dimensions' ] )
            
            height = height + thumb_height
            
        
        return ( width, height )
        
    else:
        
        ( media_width, media_height ) = CalculateMediaSize( media, zoom )
        
        if ShouldHaveAnimationBar( media ):
            
            media_height += ANIMATED_SCANBAR_HEIGHT
            
        
        return ( media_width, media_height )
        
    
def CalculateMediaSize( media, zoom ):
    
    ( original_width, original_height ) = media.GetResolution()
    
    media_width = int( round( zoom * original_width ) )
    media_height = int( round( zoom * original_height ) )
    
    return ( media_width, media_height )
    
def IsStaticImage( media ):
    
    return media.GetMime() in HC.IMAGES and not ShouldHaveAnimationBar( media )
    
def ShouldHaveAnimationBar( media ):
    
    is_animated_gif = media.GetMime() == HC.IMAGE_GIF and media.HasDuration()
    
    is_animated_flash = media.GetMime() == HC.APPLICATION_FLASH and media.HasDuration()
    
    is_native_video = media.GetMime() in HC.NATIVE_VIDEO
    
    num_frames = media.GetNumFrames()
    
    has_more_than_one_frame = num_frames is not None and num_frames > 1
    
    return is_animated_gif or is_animated_flash or is_native_video
    
class Animation( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._media = None
        
        self._drag_happened = False
        self._left_down_event = None
        
        self._something_valid_has_been_drawn = False
        self._has_played_once_through = False
        
        self._num_frames = 1
        
        self._current_frame_index = 0
        self._current_frame_drawn = False
        self._current_timestamp_ms = None
        self._next_frame_due_at = HydrusData.GetNowPrecise()
        self._slow_frame_score = 1.0
        
        self._paused = True
        
        self._video_container = None
        
        self._canvas_bmp = None
        self._frame_bmp = None
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventPropagateMouse )
        self.Bind( wx.EVT_KEY_UP, self.EventPropagateKey )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _DrawFrame( self, dc ):
        
        current_frame = self._video_container.GetFrame( self._current_frame_index )
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        ( frame_width, frame_height ) = current_frame.GetSize()
        
        if self._frame_bmp is not None and self._frame_bmp.GetSize() != current_frame.GetSize():
            
            HG.client_controller.bitmap_manager.ReleaseBitmap( self._frame_bmp )
            
            self._frame_bmp = None
            
        
        if self._frame_bmp is None:
            
            self._frame_bmp = HG.client_controller.bitmap_manager.GetBitmap( frame_width, frame_height, current_frame.GetDepth() * 8 )
            
            #self._frame_bmp = wx.Bitmap( frame_width, frame_height, current_frame.GetDepth() * 8 )
            
        
        current_frame.CopyToWxBitmap( self._frame_bmp )
        
        # since stretchblit is unreliable, and since stretched drawing is so slow anyway, let's do it at the numpy_level
        # so this calls for 'copy this clipped region to this bmp'
        # the frame container clips the numpy_image, resizes up in cv, fills the bmp
        # then we blit in 0.001ms no prob
        
        if HC.PLATFORM_OSX or HC.PLATFORM_LINUX:
            
            # for some reason, stretchblit just draws white for os x
            # and for ubuntu 16.04, it only handles the first frame!
            # maybe a wx.copy problem?
            # or a mask?
            # os x double buffering something?
            # apparently some os x blit bindings might just be missing
            
            scale = my_width / frame_width
            
            dc.SetUserScale( scale, scale )
            
            dc.DrawBitmap( self._frame_bmp, 0, 0 )
            
            dc.SetUserScale( 1.0, 1.0 )
            
        else:
            
            # next step here is to deal with superzoom cleverly, by having a clipped bmp
            # only blit from the clipped section of the src to our clipped bmp
            # on resize, get the parent canvas, get its clienttoscreen size/pos, compare that with our own, clip a bmp, something like that.
            # think we'll have to initialise the dc with that in mind, moving our smaller bmp to the correct virtual location on the window
            # I think this is dc.SetDeviceOrigin
            # and do something similar for staticimage
            # will need to setdirty on drag that reveals offscreen region
            # hence prob a good idea to give the bmp 100px or so spare offscreen buffer, to reduce redraw spam, if that can be neatly done
            
            mdc = wx.MemoryDC( self._frame_bmp )
            
            dc.StretchBlit( 0, 0, my_width, my_height, mdc, 0, 0, frame_width, frame_height )
            
        
        self._current_frame_drawn = True
        
        next_frame_time_s = self._video_container.GetDuration( self._current_frame_index ) / 1000.0
        
        next_frame_ideally_due = self._next_frame_due_at + next_frame_time_s
        
        if HydrusData.TimeHasPassedPrecise( next_frame_ideally_due ):
            
            self._next_frame_due_at = HydrusData.GetNowPrecise() + next_frame_time_s
            
        else:
            
            self._next_frame_due_at = next_frame_ideally_due
            
        
        self._something_valid_has_been_drawn = True
        
    
    def _DrawABlankFrame( self, dc ):
        
        new_options = HG.client_controller.new_options
        
        dc.SetBackground( wx.Brush( new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) ) )
        
        dc.Clear()
        
        self._something_valid_has_been_drawn = True
        
    
    def CurrentFrame( self ):
        
        return self._current_frame_index
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventPaint( self, event ):
        
        if self._canvas_bmp is None:
            
            return
            
        
        if self._video_container is None and self._media is not None:
            
            self._video_container = ClientRendering.RasterContainerVideo( self._media, self.GetClientSize(), init_position = self._current_frame_index )
            
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if not self._something_valid_has_been_drawn:
            
            self._DrawABlankFrame( dc )
            
        
    
    def EventPropagateKey( self, event ):
        
        event.ResumePropagation( 1 )
        event.Skip()
        
    
    def EventPropagateMouse( self, event ):
        
        if not ( event.ShiftDown() or event.CmdDown() or event.AltDown() ):
            
            if event.LeftDClick():
                
                hash = self._media.GetHash()
                mime = self._media.GetMime()
                
                client_files_manager = HG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                new_options = HG.client_controller.new_options
                
                launch_path = new_options.GetMimeLaunch( mime )
                
                HydrusPaths.LaunchFile( path, launch_path )
                
                self.Pause()
                
                return
                
            elif event.LeftDown():
                
                self.PausePlay()
                
                self.GetParent().BeginDrag()
                
                return
                
            
        
        screen_position = ClientGUIFunctions.ClientToScreen( self, event.GetPosition() )
        ( x, y ) = self.GetParent().ScreenToClient( screen_position )
        
        event.SetX( x )
        event.SetY( y )
        
        event.ResumePropagation( 1 )
        event.Skip()
        
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if my_width > 0 and my_height > 0:
            
            if self._canvas_bmp is None:
                
                make_new_one = True
                
            else:
                
                ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
                
                make_new_one = my_width != current_bmp_width or my_height != current_bmp_height
                
            
            if make_new_one:
                
                if self._canvas_bmp is not None:
                    
                    HG.client_controller.bitmap_manager.ReleaseBitmap( self._canvas_bmp )
                    
                
                self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( my_width, my_height, 24 )
                
                self._current_frame_drawn = False
                self._something_valid_has_been_drawn = False
                
                self.Refresh()
                
                if self._media is not None:
                    
                    ( media_width, media_height ) = self._media.GetResolution()
                    
                    if self._video_container is not None:
                        
                        ( renderer_width, renderer_height ) = self._video_container.GetSize()
                        
                        we_just_zoomed_in = my_width > renderer_width or my_height > renderer_height
                        we_just_zoomed_out = my_width < renderer_width or my_height < renderer_height
                        
                        if we_just_zoomed_in:
                            
                            if self._video_container.IsScaled():
                                
                                target_width = min( media_width, my_width )
                                target_height = min( media_height, my_height )
                                
                                self._video_container.Stop()
                                
                                self._video_container = ClientRendering.RasterContainerVideo( self._media, ( target_width, target_height ), init_position = self._current_frame_index )
                                
                            
                        elif we_just_zoomed_out:
                            
                            if my_width < media_width or my_height < media_height: # i.e. new zoom is scaled
                                
                                self._video_container.Stop()
                                
                                self._video_container = ClientRendering.RasterContainerVideo( self._media, ( my_width, my_height ), init_position = self._current_frame_index )
                                
                            
                        
                    
                
            
        
    
    def GetAnimationBarStatus( self ):
        
        if self._video_container is None:
            
            buffer_indices = None
            
        else:
            
            buffer_indices = self._video_container.GetBufferIndices()
            
            if self._current_timestamp_ms is None and self._video_container.IsInitialised():
                
                self._current_timestamp_ms = self._video_container.GetTimestampMS( self._current_frame_index )
                
            
        
        return ( self._current_frame_index, self._current_timestamp_ms, self._paused, buffer_indices )
        
    
    def GotoFrame( self, frame_index ):
        
        if self._video_container is not None and self._video_container.IsInitialised():
            
            if frame_index != self._current_frame_index:
                
                self._current_frame_index = frame_index
                self._current_timestamp_ms = None
                
                self._next_frame_due_at = HydrusData.GetNowPrecise()
                
                self._video_container.GetReadyForFrame( self._current_frame_index )
                
                self._current_frame_drawn = False
                
            
            self._paused = True
            
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._has_played_once_through
        
    
    def IsPlaying( self ):
        
        return not self._paused
        
    
    def Play( self ):
        
        self._paused = False
        
    
    def Pause( self ):
        
        self._paused = True
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def SetMedia( self, media, start_paused = False ):
        
        self._media = media
        
        self._drag_happened = False
        self._left_down_event = None
        
        self._something_valid_has_been_drawn = False
        self._has_played_once_through = False
        
        if self._media is not None:
            
            self._num_frames = self._media.GetNumFrames()
            
        else:
            
            self._num_frames = 1
            
        
        self._current_frame_index = int( ( self._num_frames - 1 ) * HC.options[ 'animation_start_position' ] )
        self._current_frame_drawn = False
        self._current_timestamp_ms = None
        self._next_frame_due_at = HydrusData.GetNowPrecise()
        self._slow_frame_score = 1.0
        
        self._paused = start_paused
        
        if self._video_container is not None:
            
            self._video_container.Stop()
            
        
        self._video_container = None
        
        self._frame_bmp = None
        
        if self._media is None:
            
            HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
        else:
            
            HG.client_controller.gui.RegisterAnimationUpdateWindow( self )
            
            self.Refresh()
            
        
    
    def SetNoneMedia( self ):
        
        self.SetMedia( None )
        
    
    def TIMERAnimationUpdate( self ):
        
        if self._media is None:
            
            return
            
        
        try:
            
            if self.IsShownOnScreen():
                
                if self._current_frame_drawn:
                    
                    if not self._paused and HydrusData.TimeHasPassedPrecise( self._next_frame_due_at ):
                        
                        num_frames = self._media.GetNumFrames()
                        
                        self._current_frame_index = ( self._current_frame_index + 1 ) % num_frames
                        
                        if self._current_frame_index == 0:
                            
                            self._current_timestamp_ms = 0
                            self._has_played_once_through = True
                            
                        else:
                            
                            if self._current_timestamp_ms is not None and self._video_container is not None and self._video_container.IsInitialised():
                                
                                duration_ms = self._video_container.GetDuration( self._current_frame_index - 1 )
                                
                                self._current_timestamp_ms += duration_ms
                                
                            
                        
                        self._current_frame_drawn = False
                        
                    
                
                if self._video_container is not None:
                    
                    if not self._current_frame_drawn:
                        
                        if self._video_container.HasFrame( self._current_frame_index ):
                            
                            dc = wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
                            
                            self._DrawFrame( dc )
                            
                        
                    
                
            
        except:
            
            HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
            raise
            
        
    
class AnimationBar( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._dirty = False
        
        self._canvas_bmp = None
        
        self.SetCursor( wx.Cursor( wx.CURSOR_ARROW ) )
        
        self._media_window = None
        self._duration_ms = 1000
        self._num_frames = 1
        self._last_drawn_info = None
        
        self._has_experienced_mouse_down = False
        self._currently_in_a_drag = False
        self._it_was_playing = False
        
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse )
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _DrawBlank( self, dc ):
        
        new_options = HG.client_controller.new_options
        
        dc.SetBackground( wx.Brush( new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) ) )
        
        dc.Clear()
        
        self._dirty = False
        
    
    def _GetAnimationBarStatus( self ):
        
        if FLASHWIN_OK and isinstance( self._media_window, wx.lib.flashwin.FlashWindow ):
            
            current_frame = self._media_window.CurrentFrame()
            current_timestamp_ms = None
            paused = False
            buffer_indices = None
            
            return ( current_frame, current_timestamp_ms, paused, buffer_indices )
            
        else:
            
            return self._media_window.GetAnimationBarStatus()
            
        
    
    def _GetXFromFrameIndex( self, index, width_offset = 0 ):
        
        if self._num_frames < 2:
            
            return 0
            
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        return int( ( my_width - width_offset ) * index / ( self._num_frames - 1 ) )
        
    
    def _Redraw( self, dc ):
        
        self._last_drawn_info = self._GetAnimationBarStatus()
        
        ( current_frame_index, current_timestamp_ms, paused, buffer_indices )  = self._last_drawn_info
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        dc.SetPen( wx.TRANSPARENT_PEN )
        
        background_colour = wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE )
        
        if paused:
            
            background_colour = ClientData.GetLighterDarkerColour( background_colour )
            
        
        dc.SetBackground( wx.Brush( background_colour ) )
        
        dc.Clear()
        
        #
        
        if buffer_indices is not None:
            
            ( start_index, rendered_to_index, end_index ) = buffer_indices
            
            if ClientRendering.FrameIndexOutOfRange( rendered_to_index, start_index, end_index ):
                
                rendered_to_index = start_index
                
            
            start_x = self._GetXFromFrameIndex( start_index )
            rendered_to_x = self._GetXFromFrameIndex( rendered_to_index )
            end_x = self._GetXFromFrameIndex( end_index )
            
            if start_x != rendered_to_x:
                
                rendered_colour = ClientData.GetDifferentLighterDarkerColour( background_colour )
                
                dc.SetBrush( wx.Brush( rendered_colour ) )
                
                if rendered_to_x > start_x:
                    
                    dc.DrawRectangle( start_x, 0, rendered_to_x - start_x, ANIMATED_SCANBAR_HEIGHT )
                    
                else:
                    
                    dc.DrawRectangle( start_x, 0, my_width - start_x, ANIMATED_SCANBAR_HEIGHT )
                    
                    dc.DrawRectangle( 0, 0, rendered_to_x, ANIMATED_SCANBAR_HEIGHT )
                    
                
            
            if rendered_to_x != end_x:
                
                to_be_rendered_colour = ClientData.GetDifferentLighterDarkerColour( background_colour, 1 )
                
                dc.SetBrush( wx.Brush( to_be_rendered_colour ) )
                
                if end_x > rendered_to_x:
                    
                    dc.DrawRectangle( rendered_to_x, 0, end_x - rendered_to_x, ANIMATED_SCANBAR_HEIGHT )
                    
                else:
                    
                    dc.DrawRectangle( rendered_to_x, 0, my_width - rendered_to_x, ANIMATED_SCANBAR_HEIGHT )
                    
                    dc.DrawRectangle( 0, 0, end_x, ANIMATED_SCANBAR_HEIGHT )
                    
                
            
        
        dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNSHADOW ) ) )
        
        caret_x = self._GetXFromFrameIndex( current_frame_index, width_offset = ANIMATED_SCANBAR_CARET_WIDTH )
        
        dc.DrawRectangle( caret_x, 0, ANIMATED_SCANBAR_CARET_WIDTH, ANIMATED_SCANBAR_HEIGHT )
        
        #
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        s = HydrusData.ConvertValueRangeToPrettyString( current_frame_index + 1, self._num_frames )
        
        if current_timestamp_ms is not None:
            
            s += ' - {}'.format( HydrusData.ConvertValueRangeToScanbarTimestampsMS( current_timestamp_ms, self._duration_ms ) )
            
        
        ( x, y ) = dc.GetTextExtent( s )
        
        dc.DrawText( s, my_width - x - 3, 3 )
        
        self._dirty = False
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventMouse( self, event ):
        
        if self._media_window is not None:
            
            if not self._media_window:
                
                self.SetNoneMedia()
                
                return
                
            
            CC.CAN_HIDE_MOUSE = False
            
            if event.ButtonDown( wx.MOUSE_BTN_ANY ):
                
                self._has_experienced_mouse_down = True
                
            
            # sometimes, this can inherit mouse-down from previous filter or embed button reveal, resulting in undesired scan
            
            if not self._has_experienced_mouse_down:
                
                return
                
            
            ( my_width, my_height ) = self.GetClientSize()
            
            if event.Dragging():
                
                self._currently_in_a_drag = True
                
            
            a_button_is_down = event.LeftIsDown() or event.MiddleIsDown() or event.RightIsDown()
            
            if a_button_is_down:
                
                if not self._currently_in_a_drag:
                    
                    self._it_was_playing = self._media_window.IsPlaying()
                    
                
                ( x, y ) = event.GetPosition()
                
                compensated_x_position = x - ( ANIMATED_SCANBAR_CARET_WIDTH / 2 )
                
                proportion = ( compensated_x_position ) / ( my_width - ANIMATED_SCANBAR_CARET_WIDTH )
                
                if proportion < 0: proportion = 0
                if proportion > 1: proportion = 1
                
                current_frame_index = int( proportion * ( self._num_frames - 1 ) + 0.5 )
                
                self._dirty = True
                
                self.Refresh()
                
                self._media_window.GotoFrame( current_frame_index )
                
            elif event.ButtonUp( wx.MOUSE_BTN_ANY ):
                
                if self._it_was_playing:
                    
                    self._media_window.Play()
                    
                
                self._currently_in_a_drag = False
                
            
        
    
    def EventPaint( self, event ):
        
        if self._canvas_bmp is not None:
            
            dc = wx.BufferedPaintDC( self, self._canvas_bmp )
            
            if self._dirty:
                
                if self._media_window is None:
                    
                    self._DrawBlank( dc )
                    
                else:
                    
                    self._Redraw( dc )
                    
                
            
        
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if my_width > 0 and my_height > 0:
            
            if self._canvas_bmp is None:
                
                make_new_one = True
                
            else:
                
                ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
                
                make_new_one = my_width != current_bmp_width or my_height != current_bmp_height
                
            
            if make_new_one:
                
                if self._canvas_bmp is not None:
                    
                    HG.client_controller.bitmap_manager.ReleaseBitmap( self._canvas_bmp )
                    
                
                self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( my_width, my_height, 24 )
                
                self._dirty = True
                
                self.Refresh()
                
            
        
    
    def SetMediaAndWindow( self, media, media_window ):
        
        self._media_window = media_window
        self._duration_ms = max( media.GetDuration(), 1 )
        self._num_frames = max( media.GetNumFrames(), 1 )
        self._last_drawn_info = None
        
        self._has_experienced_mouse_down = False
        self._currently_in_a_drag = False
        self._it_was_playing = False
        
        HG.client_controller.gui.RegisterAnimationUpdateWindow( self )
        
        self._dirty = True
        
        self.Refresh()
        
    
    def SetNoneMedia( self ):
        
        self._media_window = None
        
        HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
        
        self._dirty = True
        
        self.Refresh()
        
    
    def TIMERAnimationUpdate( self ):
        
        if self.IsShownOnScreen():
            
            if not self._media_window:
                
                self.SetNoneMedia()
                
                return
                
            
            try:
                
                frame_index = self._media_window.CurrentFrame()
                
            except AttributeError:
                
                text = 'The flash window produced an unusual error that probably means it never initialised properly. This is usually because Flash has not been installed for Internet Explorer. '
                text += os.linesep * 2
                text += 'Please close the client, open Internet Explorer, and install flash from Adobe\'s site and then try again. If that does not work, please tell the hydrus developer.'
                
                HydrusData.ShowText( text )
                
                raise
                
            
            if self._last_drawn_info != self._GetAnimationBarStatus():
                
                self._dirty = True
                
                self.Refresh()
                
            
        
    
class CanvasFrame( ClientGUITopLevelWindows.FrameThatResizes ):
    
    def __init__( self, parent ):
        
        if HC.PLATFORM_OSX:
            
            float_on_parent = True
            
        else:
            
            float_on_parent = False
            
        
        ClientGUITopLevelWindows.FrameThatResizes.__init__( self, parent, 'hydrus client media viewer', 'media_viewer', float_on_parent = float_on_parent )
        
        self._canvas_window = None
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'media_viewer' ] )
        
    
    def Close( self ):
        
        if HC.PLATFORM_OSX and self.IsFullScreen():
            
            self.ShowFullScreen( False, wx.FULLSCREEN_ALL )
            
        
        self._canvas_window.CleanBeforeDestroy()
        
        self.DestroyLater()
        
    
    def FullscreenSwitch( self ):
        
        if self.IsFullScreen():
            
            self.ShowFullScreen( False, wx.FULLSCREEN_ALL )
            
        else:
            
            self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
            
        
        self._canvas_window.ResetDragDelta()
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'switch_between_fullscreen_borderless_and_regular_framed_window':
                
                self.FullscreenSwitch()
                
            elif action == 'flip_darkmode':
                
                HG.client_controller.gui.FlipDarkmode()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def SetCanvas( self, canvas_window ):
        
        self._canvas_window = canvas_window
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._canvas_window, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        ClientGUITopLevelWindows.SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self.Show( True )
        
        wx.GetApp().SetTopWindow( self )
        
        self.Bind( wx.EVT_CLOSE, self._canvas_window.EventClose )
        
    
    def TakeFocusForUser( self ):
        
        self._canvas_window.SetFocus()
        
    
class Canvas( wx.Window ):
    
    BORDER = wx.SIMPLE_BORDER
    PREVIEW_WINDOW = False
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent, style = self.BORDER )
        
        self._file_service_key = CC.LOCAL_FILE_SERVICE_KEY
        
        self._current_media_start_time = HydrusData.GetNow()
        
        self._reserved_shortcut_names = []
        
        self._reserved_shortcut_names.append( 'media' )
        self._reserved_shortcut_names.append( 'media_viewer' )
        
        self._new_options = HG.client_controller.new_options
        
        self._custom_shortcut_names = self._new_options.GetStringList( 'default_media_viewer_custom_shortcuts' )
        
        self._canvas_key = HydrusData.GenerateKey()
        
        self._maintain_pan_and_zoom = False
        
        self._dirty = True
        self._closing = False
        
        self._service_keys_to_services = {}
        
        self._current_media = None
        self._media_container = MediaContainer( self )
        self._current_zoom = 1.0
        self._canvas_zoom = 1.0
        
        self._last_drag_coordinates = None
        self._current_drag_is_touch = False
        self._last_motion_coordinates = ( 0, 0 )
        self._total_drag_delta = ( 0, 0 )
        
        self._UpdateBackgroundColour()
        
        self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( 20, 20, 24 )
        
        self.Bind( wx.EVT_SIZE, self.EventResize )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        HG.client_controller.sub( self, 'ZoomIn', 'canvas_zoom_in' )
        HG.client_controller.sub( self, 'ZoomOut', 'canvas_zoom_out' )
        HG.client_controller.sub( self, 'ZoomSwitch', 'canvas_zoom_switch' )
        HG.client_controller.sub( self, 'OpenExternally', 'canvas_open_externally' )
        HG.client_controller.sub( self, 'ManageTags', 'canvas_manage_tags' )
        HG.client_controller.sub( self, 'ProcessApplicationCommand', 'canvas_application_command' )
        HG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        HG.client_controller.sub( self, '_SetDirty', 'notify_new_colourset' )
        
    
    def _Archive( self ):
        
        if self._current_media is not None:
            
            HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( self._current_media.GetHash(), ) ) ] } )
            
        
    
    def _CanDisplayMedia( self, media ):
        
        if media is None:
            
            return True
            
        
        media = media.GetDisplayMedia()
        
        locations_manager = media.GetLocationsManager()
        
        if not locations_manager.IsLocal():
            
            return False
            
        
        if self._GetShowAction( media ) in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            return False
            
        
        return True
        
    
    def _CopyBMPToClipboard( self ):
        
        if self._current_media is not None:
            
            if self._current_media.GetMime() in HC.IMAGES and self._current_media.GetDuration() is None:
                
                HG.client_controller.pub( 'clipboard', 'bmp', self._current_media )
                
            else:
                
                wx.MessageBox( 'Sorry, cannot take bmps of anything but static images right now!' )
                
            
        
    
    def _CopyHashToClipboard( self, hash_type ):
        
        sha256_hash = self._current_media.GetHash()
        
        if hash_type == 'sha256':
            
            hex_hash = sha256_hash.hex()
            
        else:
            
            if self._current_media.GetLocationsManager().IsLocal():
                
                ( other_hash, ) = HG.client_controller.Read( 'file_hashes', ( sha256_hash, ), 'sha256', hash_type )
                
                hex_hash = other_hash.hex()
                
            else:
                
                wx.MessageBox( 'Unfortunately, you do not have that file in your database, so its non-sha256 hashes are unknown.' )
                
                return
                
            
        
        HG.client_controller.pub( 'clipboard', 'text', hex_hash )
        
    
    def _CopyFileToClipboard( self ):
        
        if self._current_media is not None:
            
            client_files_manager = HG.client_controller.client_files_manager
            
            paths = [ client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() ) ]
            
            HG.client_controller.pub( 'clipboard', 'paths', paths )
            
        
    
    def _CopyPathToClipboard( self ):
        
        if self._current_media is not None:
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() )
            
            HG.client_controller.pub( 'clipboard', 'text', path )
            
        
    
    def _Delete( self, media = None, default_reason = None, file_service_key = None ):
        
        if media is None:
            
            if self._current_media is None:
                
                return False
                
            
            media = [ self._current_media ]
            
        
        if default_reason is None:
            
            default_reason = 'Deleted from Preview or Media Viewer.'
            
        
        try:
            
            ( involves_physical_delete, jobs ) = ClientGUIDialogsQuick.GetDeleteFilesJobs( self, media, default_reason, suggested_file_service_key = file_service_key )
            
        except HydrusExceptions.CancelledException:
            
            return False
            
        
        self.SetFocus() # annoying bug because of the modal dialog
        
        def do_it( jobs ):
            
            for service_keys_to_content_updates in jobs:
                
                HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
            
        
        HG.client_controller.CallToThread( do_it, jobs )
        
        return True
        
    
    def _DoManualPan( self, delta_x_step, delta_y_step ):
        
        if self._current_media is None:
            
            return
            
        
        ( my_x, my_y ) = self.GetClientSize()
        ( media_x, media_y ) = self._media_container.GetClientSize()
        
        x_pan_distance = min( my_x // 12, media_x // 12 )
        y_pan_distance = min( my_y // 12, media_y // 12 )
        
        delta_x = delta_x_step * x_pan_distance
        delta_y = delta_y_step * y_pan_distance
        
        ( old_delta_x, old_delta_y ) = self._total_drag_delta
        
        self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
        
        self._DrawCurrentMedia()
        
    
    def _DrawBackgroundBitmap( self, dc ):
        
        background_colour = self._GetBackgroundColour()
        
        dc.SetBackground( wx.Brush( background_colour ) )
        
        dc.Clear()
        
        self._DrawBackgroundDetails( dc )
        
        self._dirty = False
        
    
    def _DrawBackgroundDetails( self, dc ):
        
        pass
        
    
    def _DrawCurrentMedia( self ):
        
        if self._current_media is None:
            
            return
            
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if my_width > 0 and my_height > 0:
            
            self._SizeAndPositionMediaContainer()
            
        
    
    def _GenerateOrderedShortcutNames( self ):
        
        # do custom first, then let the more specialised take priority
        
        shortcut_names = self._reserved_shortcut_names + self._custom_shortcut_names
        
        shortcut_names.reverse()
        
        return shortcut_names
        
    
    def _GetBackgroundColour( self ):
        
        return self._new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
    
    def _GetShowAction( self, media ):
        
        if media is None:
            
            return CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW
            
        
        mime = media.GetMime()
        
        if mime == HC.APPLICATION_HYDRUS_CLIENT_COLLECTION:
            
            return CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW
            
        
        if self.PREVIEW_WINDOW:
            
            return self._new_options.GetPreviewShowAction( mime )
            
        else:
            
            return self._new_options.GetMediaShowAction( mime )
            
        
    
    def _GetIndexString( self ):
        
        return ''
        
    
    def _GetMediaContainerSizeAndPosition( self ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        action = self._GetShowAction( self._current_media )
        
        ( media_width, media_height ) = CalculateMediaContainerSize( self._current_media, self._current_zoom, action )
        
        ( drag_x, drag_y ) = self._total_drag_delta
        
        x_offset = ( my_width - media_width ) // 2 + drag_x
        y_offset = ( my_height - media_height ) // 2 + drag_y
        
        new_size = ( media_width, media_height )
        new_position = ( x_offset, y_offset )
        
        return ( new_size, new_position )
        
    
    def _Inbox( self ):
        
        if self._current_media is None:
            
            return
            
        
        HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, ( self._current_media.GetHash(), ) ) ] } )
        
    
    def _IsZoomable( self ):
        
        if self._current_media is None:
            
            return False
            
        
        return self._GetShowAction( self._current_media ) not in ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW )
        
    
    def _IShouldCatchShortcutEvent( self, event = None ):
        
        return ClientGUIShortcuts.IShouldCatchShortcutEvent( self, event = event, child_tlp_classes_who_can_pass_up = ( ClientGUIHoverFrames.FullscreenHoverFrame, ) )
        
    
    def _MaintainZoom( self, previous_media ):
        
        if previous_media is None:
            
            self._ReinitZoom()
            
        else:
            
            if self._current_media is None:
                
                return
                
            
            ( previous_width, previous_height ) = previous_media.GetResolution()
            ( current_width, current_height ) = self._current_media.GetResolution()
            
            previous_ratio = previous_width / previous_height
            current_ratio = current_width / current_height
            
            if previous_ratio == current_ratio:
                
                # if this new one is half the size, the new zoom needs to be twice as much to be the same size
                
                zoom_ratio = previous_width / current_width
                
                ultimate_canvas_zoom = self._current_zoom * zoom_ratio
                
                self._ReinitZoom()
                
                self._current_zoom = ultimate_canvas_zoom
                
                HG.client_controller.pub( 'canvas_new_zoom', self._canvas_key, self._current_zoom )
                
            else:
                
                self._ResetDragDelta()
                
                self._ReinitZoom()
                
            
        
    
    def _ManageNotes( self ):
        
        def wx_do_it( media, notes ):
            
            if not self:
                
                return
                
            
            title = 'manage notes'
            
            with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg, [ 'manage_file_notes' ] )
                
                control = wx.TextCtrl( panel, style = wx.TE_MULTILINE )
                
                size = ClientGUIFunctions.ConvertTextToPixels( control, ( 80, 14 ) )
                
                control.SetInitialSize( size )
                
                control.SetValue( notes )
                
                panel.SetControl( control )
                
                dlg.SetPanel( panel )
                
                wx.CallAfter( control.SetFocus )
                wx.CallAfter( control.SetInsertionPointEnd )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    notes = control.GetValue()
                    
                    hash = media.GetHash()
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( notes, hash ) ) ]
                    
                    service_keys_to_content_updates = { CC.LOCAL_NOTES_SERVICE_KEY : content_updates }
                    
                    HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                    
                
            
        
        def thread_wait( media ):
            
            # if it ultimately makes sense, I can load/cache notes in the media result
            
            notes = HG.client_controller.Read( 'file_notes', media.GetHash() )
            
            wx.CallAfter( wx_do_it, media, notes )
            
        
        if self._current_media is None:
            
            return
            
        
        HG.client_controller.CallToThread( thread_wait, self._current_media )
        
    
    def _ManageRatings( self ):
        
        if self._current_media is None:
            
            return
            
        
        if len( HG.client_controller.services_manager.GetServices( HC.RATINGS_SERVICES ) ) > 0:
            
            with ClientGUIDialogsManage.DialogManageRatings( self, ( self._current_media, ) ) as dlg:
                
                dlg.ShowModal()
                
            
        
    
    def _ManageTags( self ):
        
        if self._current_media is None:
            
            return
            
        
        for child in self.GetChildren():
            
            if isinstance( child, ClientGUITopLevelWindows.FrameThatTakesScrollablePanel ):
                
                panel = child.GetPanel()
                
                if isinstance( panel, ClientGUITags.ManageTagsPanel ):
                    
                    panel.SetFocus()
                    
                    return
                    
                
            
        
        # take any focus away from hover window, which will mess up window order when it hides due to the new frame
        self.SetFocus()
        
        title = 'manage tags'
        frame_key = 'manage_tags_frame'
        
        manage_tags = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUITags.ManageTagsPanel( manage_tags, self._file_service_key, ( self._current_media, ), immediate_commit = True, canvas_key = self._canvas_key )
        
        manage_tags.SetPanel( panel )
        
    
    def _ManageURLs( self ):
        
        if self._current_media is None:
            
            return
            
        
        title = 'manage known urls'
        
        with ClientGUITopLevelWindows.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageURLsPanel( dlg, ( self._current_media, ) )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _MediaFocusWentToExternalProgram( self ):
        
        if self._current_media is None:
            
            return
            
        
        mime = self._current_media.GetMime()
        
        if mime == HC.APPLICATION_FLASH:
            
            self._media_container.SetEmbedButton()
            
        elif self._current_media.HasDuration():
            
            self._media_container.Pause()
            
        
    
    def _MouseIsOverFlash( self ):
        
        if self._current_media is not None and self._current_media.GetMime() == HC.APPLICATION_FLASH:
            
            if self.MouseIsOverMedia():
                
                return True
                
            
        
        return False
        
    
    def _OpenExternally( self ):
        
        if self._current_media is None:
            
            return
            
        
        hash = self._current_media.GetHash()
        mime = self._current_media.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        launch_path = self._new_options.GetMimeLaunch( mime )
        
        HydrusPaths.LaunchFile( path, launch_path )
        
        self._MediaFocusWentToExternalProgram()
        
    
    def _OpenFileInWebBrowser( self ):
        
        if self._current_media is not None:
            
            hash = self._current_media.GetHash()
            mime = self._current_media.GetMime()
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( hash, mime )
            
            ClientPaths.LaunchPathInWebBrowser( path )
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def _OpenFileLocation( self ):
        
        if self._current_media is not None:
            
            hash = self._current_media.GetHash()
            mime = self._current_media.GetMime()
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( hash, mime )
            
            HydrusPaths.OpenFileLocation( path )
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def _OpenKnownURL( self ):
        
        if self._current_media is not None:
            
            ClientGUIMedia.DoOpenKnownURLFromShortcut( self, self._current_media )
            
        
    
    def _PauseCurrentMedia( self ):
        
        if self._current_media is None:
            
            return
            
        
        self._media_container.Pause()
        
    
    def _PrefetchNeighbours( self ):
        
        pass
        
    
    def _ProcessShortcut( self, shortcut ):
        
        shortcut_processed = False
        
        shortcut_names = self._GenerateOrderedShortcutNames()
        
        command = HG.client_controller.GetCommandFromShortcut( shortcut_names, shortcut )
        
        if command is not None:
            
            command_processed = self.ProcessApplicationCommand( command )
            
            shortcut_processed = command_processed
            
        
        return shortcut_processed
        
    
    def _ReinitZoom( self ):
        
        if self._current_media is None:
            
            return
            
        
        show_action = self._GetShowAction( self._current_media )
        
        ( self._current_zoom, self._canvas_zoom ) = CalculateCanvasZooms( self, self._current_media, show_action )
        
        HG.client_controller.pub( 'canvas_new_zoom', self._canvas_key, self._current_zoom )
        
    
    def _ResetDragDelta( self ):
        
        self._total_drag_delta = ( 0, 0 )
        self._last_drag_coordinates = None
        
    
    def _SaveCurrentMediaViewTime( self ):
        
        now = HydrusData.GetNow()
        
        viewtime_delta = now - self._current_media_start_time
        
        self._current_media_start_time = now
        
        if self._current_media is None:
            
            return
            
        
        if self.PREVIEW_WINDOW:
            
            viewtype = 'preview'
            
        else:
            
            if isinstance( self, CanvasFilterDuplicates ):
                
                viewtype = 'media_duplicates_filter'
                
            else:
                
                viewtype = 'media'
                
            
        
        hash = self._current_media.GetHash()
        
        HG.client_controller.file_viewing_stats_manager.FinishViewing( viewtype, hash, viewtime_delta )
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
        self.Refresh()
        
    
    def _SizeAndPositionMediaContainer( self ):
        
        if self._current_media is None:
            
            return
            
        
        ( new_size, new_position ) = self._GetMediaContainerSizeAndPosition()
        
        if new_size != self._media_container.GetSize():
            
            self._media_container.SetSize( new_size )
            
        
        if new_position == self._media_container.GetPosition():
            
            if HC.PLATFORM_OSX:
                
                self._media_container.Refresh()
                
            
        else:
            
            self._media_container.SetPosition( new_position )
            
        
    
    def _TryToChangeZoom( self, new_zoom ):
        
        if self._current_media is None:
            
            return
            
        
        if self._current_media.GetMime() == HC.APPLICATION_FLASH:
            
            # we want to preserve whitespace around flash
            
            ( my_width, my_height ) = self.GetClientSize()
            
            action = self._GetShowAction( self._current_media )
            
            ( new_media_width, new_media_height ) = CalculateMediaContainerSize( self._current_media, new_zoom, action )
            
            if new_media_width >= my_width or new_media_height >= my_height:
                
                return
                
            
        
        ( drag_x, drag_y ) = self._total_drag_delta
        
        zoom_ratio = new_zoom / self._current_zoom
        
        self._total_drag_delta = ( int( drag_x * zoom_ratio ), int( drag_y * zoom_ratio ) )
        
        self._current_zoom = new_zoom
        
        HG.client_controller.pub( 'canvas_new_zoom', self._canvas_key, self._current_zoom )
        
        self._SetDirty()
        
    
    def _Undelete( self ):
        
        locations_manager = self._current_media.GetLocationsManager()
        
        if CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
            
            do_it = False
            
            if not HC.options[ 'confirm_trash' ]:
                
                do_it = True
                
            else:
                
                with ClientGUIDialogs.DialogYesNo( self, 'Undelete this file?' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        do_it = True
                        
                    
                
            
            if do_it:
                
                HG.client_controller.Write( 'content_updates', { CC.TRASH_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, ( self._current_media.GetHash(), ) ) ] } )
                
            
            self.SetFocus() # annoying bug because of the modal dialog
            
        
    
    def _UpdateBackgroundColour( self ):
        
        colour = self._GetBackgroundColour()
        
        self.SetBackgroundColour( colour )
        
        self.Refresh()
        
    
    def _ZoomIn( self ):
        
        if self._current_media is not None and self._IsZoomable():
            
            ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = self._new_options.GetMediaZoomOptions( self._current_media.GetMime() )
            
            if exact_zooms_only:
                
                exact_zoom = 1.0
                
                if exact_zoom <= self._current_zoom:
                    
                    while exact_zoom <= self._current_zoom:
                        
                        exact_zoom *= 2
                        
                    
                else:
                    
                    while exact_zoom / 2 > self._current_zoom:
                        
                        exact_zoom /= 2
                        
                    
                
                possible_zooms = [ exact_zoom ]
                
            else:
                
                possible_zooms = self._new_options.GetMediaZooms()
                
            
            possible_zooms.append( self._canvas_zoom )
            
            bigger_zooms = [ zoom for zoom in possible_zooms if zoom > self._current_zoom ]
            
            if len( bigger_zooms ) > 0:
                
                new_zoom = min( bigger_zooms )
                
                self._TryToChangeZoom( new_zoom )
                
            
        
    
    def _ZoomOut( self ):
        
        if self._current_media is not None and self._IsZoomable():
            
            ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = self._new_options.GetMediaZoomOptions( self._current_media.GetMime() )
            
            if exact_zooms_only:
                
                exact_zoom = 1.0
                
                if exact_zoom < self._current_zoom:
                    
                    while exact_zoom * 2 < self._current_zoom:
                        
                        exact_zoom *= 2
                        
                    
                else:
                    
                    while exact_zoom >= self._current_zoom:
                        
                        exact_zoom /= 2
                        
                    
                
                possible_zooms = [ exact_zoom ]
                
            else:
                
                possible_zooms = self._new_options.GetMediaZooms()
                
            
            possible_zooms.append( self._canvas_zoom )
            
            smaller_zooms = [ zoom for zoom in possible_zooms if zoom < self._current_zoom ]
            
            if len( smaller_zooms ) > 0:
                
                new_zoom = max( smaller_zooms )
                
                self._TryToChangeZoom( new_zoom )
                
            
        
    
    def _ZoomSwitch( self ):
        
        if self._current_media is not None and self._IsZoomable():
            
            if self._canvas_zoom == 1.0 and self._current_zoom == 1.0:
                
                return
                
            
            ( my_width, my_height ) = self.GetClientSize()
            
            ( media_width, media_height ) = self._current_media.GetResolution()
            
            if self._current_zoom == 1.0:
                
                new_zoom = self._canvas_zoom
                
            else:
                
                new_zoom = 1.0
                
            
            if new_zoom <= self._canvas_zoom:
                
                self._ResetDragDelta()
                
            
            self._TryToChangeZoom( new_zoom )
            
        
    
    def CleanBeforeDestroy( self ):
        
        self.SetMedia( None )
        
    
    def EventCharHook( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            shortcut = ClientGUIShortcuts.ConvertKeyEventToShortcut( event )
            
            if shortcut is not None:
                
                shortcut_processed = self._ProcessShortcut( shortcut )
                
                if shortcut_processed:
                    
                    return
                    
                
            
        
        event.Skip()
        
    
    def BeginDrag( self, pos = None ):
        
        if pos is None:
            
            ( x, y ) = self.ScreenToClient( wx.GetMousePosition() )
            
        else:
            
            ( x, y ) = pos
            
        
        self._last_drag_coordinates = ( x, y )
        self._current_drag_is_touch = False
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventPaint( self, event ):
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if self._dirty:
            
            self._DrawBackgroundBitmap( dc )
            
            if self._current_media is not None:
                
                self._DrawCurrentMedia()
                
            
        
    
    def EventResize( self, event ):
        
        if not self._closing:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            HG.client_controller.bitmap_manager.ReleaseBitmap( self._canvas_bmp )
            
            self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( my_width, my_height, 24 )
            
            if self._current_media is not None:
                
                ( media_width, media_height ) = self._media_container.GetClientSize()
                
                if my_width != media_width or my_height != media_height:
                    
                    self._ReinitZoom()
                    
                
            
            self._SetDirty()
            
        
        event.Skip()
        
    
    def FlipActiveCustomShortcutName( self, name ):
        
        if name in self._custom_shortcut_names:
            
            self._custom_shortcut_names.remove( name )
            
        else:
            
            self._custom_shortcut_names.append( name )
            
            self._custom_shortcut_names.sort()
            
        
    
    def GetActiveCustomShortcutNames( self ):
        
        return self._custom_shortcut_names
        
    
    def KeepCursorAlive( self ):
        
        pass
        
    
    def ManageTags( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ManageTags()
            
        
    
    def MouseIsNearAnimationBar( self ):
        
        if self._current_media is None:
            
            return False
            
        else:
            
            return self._media_container.MouseIsNearAnimationBar()
            
        
    
    def MouseIsOverMedia( self ):
        
        if self._current_media is None:
            
            return False
            
        else:
            
            ( x, y ) = self._media_container.GetScreenPosition()
            ( width, height ) = self._media_container.GetSize()
            
            ( mouse_x, mouse_y ) = wx.GetMousePosition()
            
            if mouse_x >= x and mouse_x <= x + width and mouse_y >= y and mouse_y <= y + height:
                
                return True
                
            
            return False
            
        
    
    def OpenExternally( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._OpenExternally()
            
        
    
    def ProcessApplicationCommand( self, command, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'manage_file_ratings':
                
                self._ManageRatings()
                
            elif action == 'manage_file_tags':
                
                self._ManageTags()
                
            elif action == 'manage_file_urls':
                
                self._ManageURLs()
                
            elif action == 'manage_file_notes':
                
                self._ManageNotes()
                
            elif action == 'open_known_url':
                
                self._OpenKnownURL()
                
            elif action == 'archive_file':
                
                self._Archive()
                
            elif action == 'copy_bmp':
                
                self._CopyBMPToClipboard()
                
            elif action == 'copy_file':
                
                self._CopyFileToClipboard()
                
            elif action == 'copy_path':
                
                self._CopyPathToClipboard()
                
            elif action == 'copy_sha256_hash':
                
                self._CopyHashToClipboard( 'sha256' )
                
            elif action == 'delete_file':
                
                self._Delete()
                
            elif action == 'inbox_file':
                
                self._Inbox()
                
            elif action == 'open_file_in_external_program':
                
                self._OpenExternally()
                
            elif action == 'pan_up':
                
                self._DoManualPan( 0, -1 )
                
            elif action == 'pan_down':
                
                self._DoManualPan( 0, 1 )
                
            elif action == 'pan_left':
                
                self._DoManualPan( -1, 0 )
                
            elif action == 'pan_right':
                
                self._DoManualPan( 1, 0 )
                
            elif action == 'pause_media':
                
                self._PauseCurrentMedia()
                
            elif action == 'move_animation_to_previous_frame':
                
                self._media_container.GotoPreviousOrNextFrame( -1 )
                
            elif action == 'move_animation_to_next_frame':
                
                self._media_container.GotoPreviousOrNextFrame( 1 )
                
            elif action == 'zoom_in':
                
                self._ZoomIn()
                
            elif action == 'zoom_out':
                
                self._ZoomOut()
                
            elif action == 'switch_between_100_percent_and_canvas_zoom':
                
                self._ZoomSwitch()
                
            else:
                
                command_processed = False
                
            
        elif command_type == CC.APPLICATION_COMMAND_TYPE_CONTENT:
            
            if self._current_media is None:
                
                return
                
            
            command_processed = ClientGUIFunctions.ApplyContentApplicationCommandToMedia( self, command, ( self._current_media, ) )
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def ResetDragDelta( self ):
        
        self._ResetDragDelta()
        
    
    def SetMedia( self, media ):
        
        if media is not None:
            
            media = media.GetDisplayMedia()
            
            if not self._CanDisplayMedia( media ):
                
                media = None
                
            
        
        if media != self._current_media:
            
            HG.client_controller.ResetIdleTimer()
            
            self._SaveCurrentMediaViewTime()
            
            previous_media = self._current_media
            
            self._current_media = media
            
            if not self._maintain_pan_and_zoom:
                
                self._ResetDragDelta()
                
            
            if self._current_media is None:
                
                self._media_container.SetNoneMedia()
                
            else:
                
                if previous_media is not None and self._maintain_pan_and_zoom:
                    
                    self._MaintainZoom( previous_media )
                    
                else:
                    
                    self._ReinitZoom()
                    
                
                ( initial_size, initial_position ) = self._GetMediaContainerSizeAndPosition()
                
                ( initial_width, initial_height ) = initial_size
                
                if self._current_media.GetLocationsManager().IsLocal() and initial_width > 0 and initial_height > 0:
                    
                    show_action = self._GetShowAction( self._current_media )
                    
                    self._media_container.SetMedia( self._current_media, initial_size, initial_position, show_action )
                    
                    self._PrefetchNeighbours()
                    
                else:
                    
                    self._current_media = None
                    
                
            
            HG.client_controller.pub( 'canvas_new_display_media', self._canvas_key, self._current_media )
            
            HG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self._SetDirty()
            
        
    
    def ZoomIn( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ZoomIn()
            
        
    
    def ZoomOut( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ZoomOut()
            
        
    
    def ZoomSwitch( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ZoomSwitch()
            
        
    
class CanvasPanel( Canvas ):
    
    PREVIEW_WINDOW = True
    
    def __init__( self, parent, page_key ):
        
        Canvas.__init__( self, parent )
        
        self._page_key = page_key
        
        HG.client_controller.sub( self, 'MediaFocusWentToExternalProgram', 'media_focus_went_to_external_program' )
        HG.client_controller.sub( self, 'PreviewChanged', 'preview_changed' )
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
    
    def EventShowMenu( self, event ):
        
        if self._current_media is not None:
            
            new_options = HG.client_controller.new_options
            
            advanced_mode = new_options.GetBoolean( 'advanced_mode' )
            
            services = HG.client_controller.services_manager.GetServices()
            
            locations_manager = self._current_media.GetLocationsManager()
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            menu = wx.Menu()
            
            for line in self._current_media.GetPrettyInfoLines():
                
                ClientGUIMenus.AppendMenuLabel( menu, line, line )
                
            
            ClientGUIMedia.AddFileViewingStatsMenu( menu, self._current_media )
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            manage_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, manage_menu, 'tags', 'Manage this file\'s tags.', self._ManageTags )
            
            if i_can_post_ratings:
                
                ClientGUIMenus.AppendMenuItem( self, manage_menu, 'ratings', 'Manage this file\'s ratings.', self._ManageRatings )
                
            
            ClientGUIMenus.AppendMenuItem( self, manage_menu, 'known urls', 'Manage this file\'s known URLs.', self._ManageURLs )
            
            ClientGUIMenus.AppendMenuItem( self, manage_menu, 'notes', 'Manage this file\'s notes.', self._ManageNotes )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._current_media.HasInbox():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'archive', 'Archive this file.', self._Archive )
                
            
            if self._current_media.HasArchive():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'inbox', 'Send this files back to the inbox.', self._Inbox )
                
            
            if CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'delete', 'Delete this file.', self._Delete, file_service_key = CC.LOCAL_FILE_SERVICE_KEY )
                
            elif CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'delete completely', 'Physically delete this file from disk.', self._Delete, file_service_key = CC.TRASH_SERVICE_KEY )
                ClientGUIMenus.AppendMenuItem( self, menu, 'undelete', 'Take this file out of the trash.', self._Undelete )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'open externally', 'Open this file in your OS\'s default program.', self._OpenExternally )
            
            ClientGUIMedia.AddKnownURLsViewCopyMenu( self, menu, self._current_media )
            
            share_menu = wx.Menu()
            
            show_open_in_web = True
            show_open_in_explorer = advanced_mode and not HC.PLATFORM_LINUX
            
            if show_open_in_web or show_open_in_explorer:
                
                open_menu = wx.Menu()
                
                if show_open_in_web:
                    
                    ClientGUIMenus.AppendMenuItem( self, open_menu, 'in web browser', 'Show this file in your OS\'s web browser.', self._OpenFileInWebBrowser )
                    
                
                if show_open_in_explorer:
                    
                    ClientGUIMenus.AppendMenuItem( self, open_menu, 'in file browser', 'Show this file in your OS\'s file browser.', self._OpenFileLocation )
                    
                
                ClientGUIMenus.AppendMenu( share_menu, open_menu, 'open' )
                
            
            copy_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, copy_menu, 'file', 'Copy this file to your clipboard.', self._CopyFileToClipboard )
            
            copy_hash_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha256 (hydrus default)', 'Open this file\'s SHA256 hash.', self._CopyHashToClipboard, 'sha256' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'md5', 'Open this file\'s MD5 hash.', self._CopyHashToClipboard, 'md5' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha1', 'Open this file\'s SHA1 hash.', self._CopyHashToClipboard, 'sha1' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha512', 'Open this file\'s SHA512 hash.', self._CopyHashToClipboard, 'sha512' )
            
            ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
            
            if self._current_media.GetMime() in HC.IMAGES and self._current_media.GetDuration() is None:
                
                ClientGUIMenus.AppendMenuItem( self, copy_menu, 'image (bitmap)', 'Copy this file to your clipboard as a bmp.', self._CopyBMPToClipboard )
                
            
            ClientGUIMenus.AppendMenuItem( self, copy_menu, 'path', 'Copy this file\'s path to your clipboard.', self._CopyPathToClipboard )
            
            ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
            
            ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
            
            HG.client_controller.PopupMenu( self, menu )
            
            event.Skip()
            
        
    
    def MediaFocusWentToExternalProgram( self, page_key ):
        
        if page_key == self._page_key:
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def PreviewChanged( self, page_key, media ):
        
        if HC.options[ 'hide_preview' ]:
            
            return
            
        
        if page_key == self._page_key:
            
            self.SetMedia( media )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._SetDirty()
                
            
        
    
class CanvasWithDetails( Canvas ):
    
    BORDER = wx.NO_BORDER
    
    def _DrawAdditionalTopMiddleInfo( self, dc, current_y ):
        
        pass
        
    
    def _DrawBackgroundDetails( self, dc ):
        
        if self._current_media is None:
            
            text = self._GetNoMediaText()
            
            ( width, height ) = dc.GetTextExtent( text )
            
            ( my_width, my_height ) = self.GetClientSize()
            
            x = ( my_width - width ) // 2
            y = ( my_height - height ) // 2
            
            dc.DrawText( text, x, y )
            
        else:
            
            ( client_width, client_height ) = self.GetClientSize()
            
            # tags on the top left
            
            dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
            
            tags_manager = self._current_media.GetTagsManager()
            
            current = tags_manager.GetCurrent()
            pending = tags_manager.GetPending()
            petitioned = tags_manager.GetPetitioned()
            
            tags_i_want_to_display = set()
            
            tags_i_want_to_display.update( current )
            tags_i_want_to_display.update( pending )
            tags_i_want_to_display.update( petitioned )
            
            tags_i_want_to_display = list( tags_i_want_to_display )
            
            ClientTags.SortTags( HC.options[ 'default_tag_sort' ], tags_i_want_to_display )
            
            current_y = 3
            
            namespace_colours = HC.options[ 'namespace_colours' ]
            
            for tag in tags_i_want_to_display:
                
                display_string = ClientTags.RenderTag( tag, True )
                
                if tag in pending:
                    
                    display_string += ' (+)'
                    
                
                if tag in petitioned:
                    
                    display_string += ' (-)'
                    
                
                ( namespace, subtag ) = HydrusTags.SplitTag( tag )
                
                if namespace in namespace_colours:
                    
                    ( r, g, b ) = namespace_colours[ namespace ]
                    
                else:
                    
                    ( r, g, b ) = namespace_colours[ None ]
                    
                
                dc.SetTextForeground( wx.Colour( r, g, b ) )
                
                ( x, y ) = dc.GetTextExtent( display_string )
                
                dc.DrawText( display_string, 5, current_y )
                
                current_y += y
                
            
            dc.SetTextForeground( self._new_options.GetColour( CC.COLOUR_MEDIA_TEXT ) )
            
            # top right
            
            current_y = 2
            
            # ratings
            
            services_manager = HG.client_controller.services_manager
            
            like_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ), randomised = False )
            
            like_services.reverse()
            
            like_rating_current_x = client_width - 16
            
            for like_service in like_services:
                
                service_key = like_service.GetServiceKey()
                
                rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), service_key )
                
                ClientRatings.DrawLike( dc, like_rating_current_x, current_y, service_key, rating_state )
                
                like_rating_current_x -= 16
                
            
            if len( like_services ) > 0:
                
                current_y += 20
                
            
            numerical_services = services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ), randomised = False )
            
            for numerical_service in numerical_services:
                
                service_key = numerical_service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), service_key )
                
                numerical_width = ClientRatings.GetNumericalWidth( service_key )
                
                ClientRatings.DrawNumerical( dc, client_width - numerical_width, current_y, service_key, rating_state, rating )
                
                current_y += 20
                
            
            # icons
            
            icons_to_show = []
            
            if CC.TRASH_SERVICE_KEY in self._current_media.GetLocationsManager().GetCurrent():
                
                icons_to_show.append( CC.GlobalBMPs.trash )
                
            
            if self._current_media.HasInbox():
                
                icons_to_show.append( CC.GlobalBMPs.inbox )
                
            
            if len( icons_to_show ) > 0:
                
                icon_x = 0
                
                for icon in icons_to_show:
                    
                    dc.DrawBitmap( icon, client_width + icon_x - 18, current_y )
                    
                    icon_x -= 18
                    
                
                current_y += 18
                
            
            # repo strings
            
            remote_strings = self._current_media.GetLocationsManager().GetRemoteLocationStrings()
            
            for remote_string in remote_strings:
                
                ( text_width, text_height ) = dc.GetTextExtent( remote_string )
                
                dc.DrawText( remote_string, client_width - text_width - 3, current_y )
                
                current_y += text_height + 4
                
            
            # urls
            
            urls = self._current_media.GetLocationsManager().GetURLs()
            
            url_tuples = HG.client_controller.network_engine.domain_manager.ConvertURLsToMediaViewerTuples( urls )
            
            for ( display_string, url ) in url_tuples:
                
                ( text_width, text_height ) = dc.GetTextExtent( display_string )
                
                dc.DrawText( display_string, client_width - text_width - 3, current_y )
                
                current_y += text_height + 4
                
            
            # top-middle
            
            current_y = 3
            
            title_string = self._current_media.GetTitleString()
            
            if len( title_string ) > 0:
                
                ( x, y ) = dc.GetTextExtent( title_string )
                
                dc.DrawText( title_string, ( client_width - x ) // 2, current_y )
                
                current_y += y + 3
                
            
            info_string = self._GetInfoString()
            
            ( x, y ) = dc.GetTextExtent( info_string )
            
            dc.DrawText( info_string, ( client_width - x ) // 2, current_y )
            
            current_y += y + 3
            
            self._DrawAdditionalTopMiddleInfo( dc, current_y )
            
            # bottom-right index
            
            index_string = self._GetIndexString()
            
            if len( index_string ) > 0:
                
                ( x, y ) = dc.GetTextExtent( index_string )
                
                dc.DrawText( index_string, client_width - x - 3, client_height - y - 3 )
                
            
        
    
    def _GetInfoString( self ):
        
        lines = self._current_media.GetPrettyInfoLines()
        
        lines.insert( 1, ClientData.ConvertZoomToPercentage( self._current_zoom ) )
        
        info_string = ' | '.join( lines )
        
        return info_string
        
    
    def _GetNoMediaText( self ):
        
        return 'No media to display'
        
    
class CanvasWithHovers( CanvasWithDetails ):
    
    def __init__( self, parent ):
        
        CanvasWithDetails.__init__( self, parent )
        
        self._hover_commands = self._GenerateHoverTopFrame()
        self._hover_tags = ClientGUIHoverFrames.FullscreenHoverFrameTags( self, self, self._canvas_key )
        
        ratings_services = HG.client_controller.services_manager.GetServices( ( HC.RATINGS_SERVICES ) )
        
        self._hover_ratings = ClientGUIHoverFrames.FullscreenHoverFrameTopRight( self, self, self._canvas_key )
        
        #
        
        self._timer_cursor_hide_job = None
        
        self.Bind( wx.EVT_MOTION, self.EventDrag )
        
        HG.client_controller.sub( self, 'Close', 'canvas_close' )
        HG.client_controller.sub( self, 'FullscreenSwitch', 'canvas_fullscreen_switch' )
        
    
    def _Close( self ):
        
        self._closing = True
        
        self.GetParent().Close()
        
    
    def _GenerateHoverTopFrame( self ):
        
        raise NotImplementedError()
        
    
    def Close( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Close()
            
        
    
    def EventDragBegin( self, event ):
        
        ( x, y ) = event.GetPosition()
        
        self.BeginDrag( ( x, y ) )
        
        event.Skip()
        
    
    def EventDragEnd( self, event ):
        
        self._last_drag_coordinates = None
        
        event.Skip()
        
    
    def EventDrag( self, event ):
        
        CC.CAN_HIDE_MOUSE = True
        
        ( x, y ) = event.GetPosition()
        
        show_mouse = self.GetCursor() == wx.Cursor( wx.CURSOR_ARROW )
        
        is_dragging = event.Dragging() and self._last_drag_coordinates is not None
        has_moved = ( x, y ) != self._last_motion_coordinates
        
        if is_dragging:
            
            ( old_x, old_y ) = self._last_drag_coordinates
            
            ( delta_x, delta_y ) = ( x - old_x, y - old_y )
            
            delta_distance = ( ( delta_x ** 2 ) + ( delta_y ** 2 ) ) ** 0.5
            
            if delta_distance > 0:
                
                touchscreen_canvas_drags_unanchor = HG.client_controller.new_options.GetBoolean( 'touchscreen_canvas_drags_unanchor' )
                
                if not self._current_drag_is_touch and delta_distance > 50:
                    
                    # if user is able to generate such a large distance, they are almost certainly touching
                    
                    self._current_drag_is_touch = True
                    
                
                # touch events obviously don't mix with warping well. the touch just warps it back and again and we get a massive delta!
                
                touch_anchor_override = touchscreen_canvas_drags_unanchor and self._current_drag_is_touch
                anchor_and_hide_canvas_drags = HG.client_controller.new_options.GetBoolean( 'anchor_and_hide_canvas_drags' )
                
                if anchor_and_hide_canvas_drags and not touch_anchor_override:
                    
                    show_mouse = False
                    
                    self.WarpPointer( old_x, old_y )
                    
                else:
                    
                    show_mouse = True
                    
                    self._last_drag_coordinates = ( x, y )
                    
                
                ( old_delta_x, old_delta_y ) = self._total_drag_delta
                
                self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
                
                self._DrawCurrentMedia()
                
            
        elif has_moved:
            
            self._last_motion_coordinates = ( x, y )
            
            show_mouse = True
            
        
        if show_mouse:
            
            self.SetCursor( wx.Cursor( wx.CURSOR_ARROW ) )
            
            self._PutOffCursorHide()
            
        else:
            
            self.SetCursor( wx.Cursor( wx.CURSOR_BLANK ) )
            
        
    
    def FullscreenSwitch( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self.GetParent().FullscreenSwitch()
            
        
    
    def _PutOffCursorHide( self ):
        
        if self._timer_cursor_hide_job is not None:
            
            self._timer_cursor_hide_job.Cancel()
            
        
        self._timer_cursor_hide_job = HG.client_controller.CallLaterWXSafe( self, 0.8, self._HideCursor )
        
    
    def _HideCursor( self ):
        
        if not CC.CAN_HIDE_MOUSE:
            
            return
            
        
        if HG.client_controller.MenuIsOpen():
            
            self._PutOffCursorHide()
            
        else:
            
            self.SetCursor( wx.Cursor( wx.CURSOR_BLANK ) )
            
        
    
class CanvasFilterDuplicates( CanvasWithHovers ):
    
    def __init__( self, parent, file_search_context, both_files_match ):
        
        CanvasWithHovers.__init__( self, parent )
        
        self._hover_duplicates = ClientGUIHoverFrames.FullscreenHoverFrameRightDuplicates( self, self, self._canvas_key )
        
        self._file_search_context = file_search_context
        self._both_files_match = both_files_match
        
        self._maintain_pan_and_zoom = True
        
        self._currently_fetching_pairs = False
        
        self._unprocessed_pairs = []
        self._current_pair = None
        self._processed_pairs = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        
        file_service_key = self._file_search_context.GetFileServiceKey()
        
        self._media_list = ClientMedia.ListeningMediaList( file_service_key, [] )
        
        self._reserved_shortcut_names.append( 'media_viewer_browser' )
        self._reserved_shortcut_names.append( 'duplicate_filter' )
        
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse )
        
        # add support for 'f' to borderless
        # add support for F4 and other general shortcuts so people can do edits before processing
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        HG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        HG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_next' )
        HG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_previous' )
        
        wx.CallAfter( self._ShowNewPair )
        
    
    def _Close( self ):
        
        num_committable = self._GetNumCommittableDecisions()
        
        if num_committable > 0:
            
            label = 'commit ' + HydrusData.ToHumanInt( num_committable ) + ' decisions?'
            
            result = ClientGUIDialogsQuick.GetFinishFilteringAnswer( self, label )
            
            if result == wx.ID_CANCEL:
                
                close_was_triggered_by_everything_being_processed = len( self._unprocessed_pairs ) == 0
                
                if close_was_triggered_by_everything_being_processed:
                    
                    self._GoBack()
                    
                
                return
                
            elif result == wx.ID_YES:
                
                self._CommitProcessed()
                
            
        
        ClientMedia.hashes_to_jpeg_quality = {} # clear the cache
        
        HG.client_controller.pub( 'refresh_dupe_page_numbers' )
        
        CanvasWithHovers._Close( self )
        
    
    def _CommitProcessed( self ):
        
        pair_info = []
        
        for ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) in self._processed_pairs:
            
            if duplicate_type is None or was_auto_skipped:
                
                continue # it was a 'skip' decision
                
            
            first_hash = first_media.GetHash()
            second_hash = second_media.GetHash()
            
            pair_info.append( ( duplicate_type, first_hash, second_hash, service_keys_to_content_updates ) )
            
        
        if len( pair_info ) > 0:
            
            HG.client_controller.WriteSynchronous( 'duplicate_pair_status', pair_info )
            
        
        self._processed_pairs = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        
    
    def _CurrentMediaIsBetter( self, delete_second = True ):
        
        self._ProcessPair( HC.DUPLICATE_BETTER, delete_second = delete_second )
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return
            
        
        text = 'Delete just this file, or both?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete just this one', 'current' ) )
        yes_tuples.append( ( 'delete both', 'both' ) )
        
        with ClientGUIDialogs.DialogYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                value = dlg.GetValue()
                
                if value == 'current':
                    
                    media = [ self._current_media ]
                    
                    default_reason = 'Deleted manually in Duplicate Filter.'
                    
                elif value == 'both':
                    
                    media = [ self._current_media, self._media_list.GetNext( self._current_media ) ]
                    
                    default_reason = 'Deleted manually in Duplicate Filter, along with its potential duplicate.'
                    
                else:
                    
                    return False
                    
                
            else:
                
                return False
                
            
        
        deleted = CanvasWithHovers._Delete( self, media = media, default_reason = default_reason, file_service_key = file_service_key )
        
        if deleted:
            
            self._SkipPair()
            
        
        return True
        
    
    def _DoCustomAction( self ):
        
        if self._current_media is None:
            
            return
            
        
        duplicate_types = [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE ]
        
        choice_tuples = [ ( HC.duplicate_type_string_lookup[ duplicate_type ], duplicate_type ) for duplicate_type in duplicate_types ]
        
        try:
            
            duplicate_type = ClientGUIDialogsQuick.SelectFromList( self, 'select duplicate type', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        new_options = HG.client_controller.new_options
        
        if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
            
            duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit duplicate merge options' ) as dlg_2:
                
                panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg_2, duplicate_type, duplicate_action_options, for_custom_action = True )
                
                dlg_2.SetPanel( panel )
                
                if dlg_2.ShowModal() == wx.ID_OK:
                    
                    duplicate_action_options = panel.GetValue()
                    
                else:
                    
                    return
                    
                
            
        else:
            
            duplicate_action_options = None
            
        
        text = 'Delete any of the files?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete this one', 'delete_first' ) )
        yes_tuples.append( ( 'delete the other', 'delete_second' ) )
        yes_tuples.append( ( 'delete both', 'delete_both' ) )
        
        delete_first = False
        delete_second = False
        delete_both = False
        
        with ClientGUIDialogs.DialogYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                value = dlg.GetValue()
                
                if value == 'delete_first':
                    
                    delete_first = True
                    
                elif value == 'delete_second':
                    
                    delete_second = True
                    
                elif value == 'delete_both':
                    
                    delete_both = True
                    
                else:
                    
                    return
                    
                
            else:
                
                return
                
            
        
        self._ProcessPair( duplicate_type, delete_first = delete_first, delete_second = delete_second, delete_both = delete_both, duplicate_action_options = duplicate_action_options )
        
    
    def _DrawBackgroundDetails( self, dc ):
        
        if self._currently_fetching_pairs:
            
            text = 'Loading pairs\u2026'
            
            ( width, height ) = dc.GetTextExtent( text )
            
            ( my_width, my_height ) = self.GetClientSize()
            
            x = ( my_width - width ) // 2
            y = ( my_height - height ) // 2
            
            dc.DrawText( text, x, y )
            
        else:
            
            CanvasWithHovers._DrawBackgroundDetails( self, dc )
            
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUIHoverFrames.FullscreenHoverFrameTopDuplicatesFilter( self, self, self._canvas_key )
        
    
    def _GetBackgroundColour( self ):
        
        normal_colour = self._new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
        if self._current_media is None:
            
            return normal_colour
            
        else:
            
            if self._current_media == self._media_list.GetFirst():
                
                return normal_colour
                
            else:
                
                new_options = HG.client_controller.new_options
                
                duplicate_intensity = new_options.GetNoneableInteger( 'duplicate_background_switch_intensity' )
                
                return ClientData.GetLighterDarkerColour( normal_colour, duplicate_intensity )
                
            
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None:
            
            return '-'
            
        else:
            
            progress = len( self._processed_pairs ) + 1 # +1 here actually counts for the one currently displayed
            total = progress + len( self._unprocessed_pairs )
            
            index_string = HydrusData.ConvertValueRangeToPrettyString( progress, total )
            
            if self._current_media == self._media_list.GetFirst():
                
                return 'A - ' + index_string
                
            else:
                
                return 'B - ' + index_string
                
            
        
    
    def _GetNoMediaText( self ):
        
        return 'Looking for pairs to compare--please wait.'
        
    
    def _GetNumCommittableDecisions( self ):
        
        return len( [ 1 for ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) in self._processed_pairs if duplicate_type is not None ] )
        
    
    def _GoBack( self ):
        
        if len( self._processed_pairs ) > 0:
            
            self._unprocessed_pairs.append( self._current_pair )
            
            ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) = self._processed_pairs.pop()
            
            self._unprocessed_pairs.append( hash_pair )
            
            while was_auto_skipped:
                
                ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) = self._processed_pairs.pop()
                
                self._unprocessed_pairs.append( hash_pair )
                
            
            self._hashes_due_to_be_deleted_in_this_batch.difference_update( hash_pair )
            
            self._ShowNewPair()
            
        
    
    def _MediaAreAlternates( self ):
        
        self._ProcessPair( HC.DUPLICATE_ALTERNATE )
        
    
    def _MediaAreFalsePositive( self ):
        
        self._ProcessPair( HC.DUPLICATE_FALSE_POSITIVE )
        
    
    def _MediaAreTheSame( self ):
        
        self._ProcessPair( HC.DUPLICATE_SAME_QUALITY )
        
    
    def _ProcessPair( self, duplicate_type, delete_first = False, delete_second = False, delete_both = False, duplicate_action_options = None ):
        
        if self._current_media is None:
            
            return
            
        
        if duplicate_action_options is None:
            
            if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( HG.client_controller.new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
                
                new_options = HG.client_controller.new_options
                
                duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
                
            else:
                
                duplicate_action_options = ClientDuplicates.DuplicateActionOptions()
                
            
        
        first_media = self._current_media
        second_media = self._media_list.GetNext( first_media )
        
        was_auto_skipped = False
        
        if delete_first or delete_second or delete_both:
            
            if delete_first or delete_both:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( first_media.GetHashes() )
                
            
            if delete_second or delete_both:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( second_media.GetHashes() )
                
            
            if duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_WORSE ):
                
                file_deletion_reason = 'better/worse'
                
                if delete_second:
                    
                    file_deletion_reason += ', worse file deleted'
                    
                
            else:
                
                file_deletion_reason = HC.duplicate_type_string_lookup[ duplicate_type ]
                
            
            if delete_both:
                
                file_deletion_reason += ', both files deleted'
                
            
            file_deletion_reason = 'Deleted in Duplicate Filter ({}).'.format( file_deletion_reason )
            
        else:
            
            file_deletion_reason = None
            
        
        service_keys_to_content_updates = duplicate_action_options.ProcessPairIntoContentUpdates( first_media, second_media, delete_first = delete_first, delete_second = delete_second, delete_both = delete_both, file_deletion_reason = file_deletion_reason )
        
        self._processed_pairs.append( ( self._current_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) )
        
        self._ShowNewPair()
        
    
    def _ShowNewPair( self ):
        
        if self._currently_fetching_pairs:
            
            return
            
        
        num_committable = self._GetNumCommittableDecisions()
        
        if len( self._unprocessed_pairs ) == 0 and num_committable > 0:
            
            label = 'commit ' + HydrusData.ToHumanInt( num_committable ) + ' decisions and continue?'
            
            result = ClientGUIDialogsQuick.GetInterstitialFilteringAnswer( self, label )
            
            if result == wx.ID_YES:
                
                self._CommitProcessed()
                
            else:
                
                ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) = self._processed_pairs.pop()
                
                self._unprocessed_pairs.append( hash_pair )
                
                while was_auto_skipped:
                    
                    ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) = self._processed_pairs.pop()
                    
                    self._unprocessed_pairs.append( hash_pair )
                    
                
                self._hashes_due_to_be_deleted_in_this_batch.difference_update( hash_pair )
                
            
        
        file_service_key = self._file_search_context.GetFileServiceKey()
        
        if len( self._unprocessed_pairs ) == 0:
            
            self._hashes_due_to_be_deleted_in_this_batch = set()
            self._processed_pairs = [] # just in case someone 'skip'ed everything in the last batch, so this never got cleared above
            
            self.SetMedia( None )
            
            self._media_list = ClientMedia.ListeningMediaList( file_service_key, [] )
            
            self._currently_fetching_pairs = True
            
            HG.client_controller.CallToThread( self.THREADFetchPairs, self._file_search_context, self._both_files_match )
            
            self._SetDirty()
            
        else:
            
            def pair_is_good( pair ):
                
                ( first_hash, second_hash ) = pair
                
                if first_hash in self._hashes_due_to_be_deleted_in_this_batch or second_hash in self._hashes_due_to_be_deleted_in_this_batch:
                    
                    return False
                    
                
                ( first_media_result, second_media_result ) = HG.client_controller.Read( 'media_results', pair )
                
                first_media = ClientMedia.MediaSingleton( first_media_result )
                second_media = ClientMedia.MediaSingleton( second_media_result )
                
                if not self._CanDisplayMedia( first_media ) or not self._CanDisplayMedia( second_media ):
                    
                    return False
                    
                
                return True
                
            
            potential_pair = self._unprocessed_pairs.pop()
            
            while not pair_is_good( potential_pair ):
                
                was_auto_skipped = True
                
                self._processed_pairs.append( ( potential_pair, None, None, None, {}, was_auto_skipped ) )
                
                if len( self._unprocessed_pairs ) == 0:
                    
                    if len( self._processed_pairs ) == 0:
                        
                        wx.MessageBox( 'It seems an entire batch of pairs were unable to be displayed. The duplicate filter will now close. Please inform hydrus dev of this.' )
                        
                        self._Close()
                        
                        return
                        
                    else:
                        
                        self._ShowNewPair() # there are no useful decisions left in the queue, so let's reset
                        
                        return
                        
                    
                
                potential_pair = self._unprocessed_pairs.pop()
                
            
            self._current_pair = potential_pair
            
            ( first_media_result, second_media_result ) = HG.client_controller.Read( 'media_results', self._current_pair )
            
            if not ( first_media_result.GetLocationsManager().IsLocal() and second_media_result.GetLocationsManager().IsLocal() ):
                
                wx.MessageBox( 'At least one of the potential files in this pair was not in this client. Likely it was very recently deleted through a different process. Your decisions until now will be saved, and then the duplicate filter will close.' )
                
                self._CommitProcessed()
                
                self._Close()
                
                return
                
            
            first_media = ClientMedia.MediaSingleton( first_media_result )
            second_media = ClientMedia.MediaSingleton( second_media_result )
            
            score = ClientMedia.GetDuplicateComparisonScore( first_media, second_media )
            
            if score > 0:
                
                media_results_with_better_first = ( first_media_result, second_media_result )
                
            else:
                
                media_results_with_better_first = ( second_media_result, first_media_result )
                
            
            self._media_list = ClientMedia.ListeningMediaList( file_service_key, media_results_with_better_first )
            
            self.SetMedia( self._media_list.GetFirst() )
            
            self._ResetDragDelta()
            
            self._ReinitZoom()
            
        
    
    def _SkipPair( self ):
        
        if self._current_media is None:
            
            return
            
        
        was_auto_skipped = False
        
        self._processed_pairs.append( ( self._current_pair, None, None, None, {}, was_auto_skipped ) )
        
        self._ShowNewPair()
        
    
    def _SwitchMedia( self ):
        
        if self._current_media is not None:
            
            try:
                
                other_media = self._media_list.GetNext( self._current_media )
                
                self.SetMedia( other_media )
                
            except HydrusExceptions.DataMissing:
                
                return
                
            
        
    
    def Archive( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Archive()
            
        
    
    def Delete( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Delete()
            
        
    
    def EventCharHook( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ):
                
                self._Close()
                
            else:
                
                ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
                
                if modifier == wx.ACCEL_NORMAL and key in CC.DELETE_KEYS:
                    
                    self._Delete()
                    
                elif modifier == wx.ACCEL_SHIFT and key in CC.DELETE_KEYS:
                    
                    self._Undelete()
                    
                else:
                    
                    CanvasWithHovers.EventCharHook( self, event )
                    
                
            
        else:
            
            event.Skip()
            
        
    
    def EventClose( self, event ):
        
        self._Close()
        
    
    def EventMouse( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            if event.ShiftDown():
                
                caught = True
                
                if event.LeftDown():
                    
                    self.EventDragBegin( event )
                    
                elif event.LeftUp():
                    
                    self.EventDragEnd( event )
                    
                elif event.Dragging():
                    
                    self.EventDrag( event )
                    
                else:
                    
                    caught = False
                    
                
                if caught:
                    
                    return
                    
                
            
            shortcut = ClientGUIShortcuts.ConvertMouseEventToShortcut( event )
            
            if shortcut is not None:
                
                shortcut_processed = self._ProcessShortcut( shortcut )
                
                if shortcut_processed:
                    
                    return
                    
                
            
            if event.GetWheelRotation() != 0:
                
                self._SwitchMedia()
                
            else:
                
                event.Skip()
                
            
        else:
            
            event.Skip()
            
        
    
    def Inbox( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Inbox()
            
        
    
    def ProcessApplicationCommand( self, command, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'duplicate_filter_this_is_better_and_delete_other':
                
                self._CurrentMediaIsBetter( delete_second = True )
                
            elif action == 'duplicate_filter_this_is_better_but_keep_both':
                
                self._CurrentMediaIsBetter( delete_second = False )
                
            elif action == 'duplicate_filter_exactly_the_same':
                
                self._MediaAreTheSame()
                
            elif action == 'duplicate_filter_alternates':
                
                self._MediaAreAlternates()
                
            elif action == 'duplicate_filter_false_positive':
                
                self._MediaAreFalsePositive()
                
            elif action == 'duplicate_filter_custom_action':
                
                self._DoCustomAction()
                
            elif action == 'duplicate_filter_skip':
                
                self._SkipPair()
                
            elif action == 'duplicate_filter_back':
                
                self._GoBack()
                
            elif action in ( 'view_first', 'view_last', 'view_previous', 'view_next' ):
                
                self._SwitchMedia()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasWithHovers.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        def catch_up():
            
            # ugly, but it will do for now
            
            if len( self._media_list ) < 2:
                
                self._ShowNewPair()
                
            else:
                
                self._SetDirty()
                
            
        
        HG.client_controller.CallLaterWXSafe( self, 0.1, catch_up )
        
    
    def SetMedia( self, media ):
        
        CanvasWithHovers.SetMedia( self, media )
        
        if media is not None:
            
            shown_media = self._current_media
            comparison_media = self._media_list.GetNext( shown_media )
            
            if shown_media != comparison_media:
                
                HG.client_controller.pub( 'canvas_new_duplicate_pair', self._canvas_key, shown_media, comparison_media )
                
            
        
    
    def SwitchMedia( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._SwitchMedia()
            
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
    def THREADFetchPairs( self, file_search_context, both_files_match ):
        
        def wx_close():
            
            if not self:
                
                return
                
            
            wx.MessageBox( 'All pairs have been filtered!' )
            
            self._Close()
            
        
        def wx_continue( unprocessed_pairs ):
            
            if not self:
                
                return
                
            
            self._unprocessed_pairs = unprocessed_pairs
            
            self._currently_fetching_pairs = False
            
            self._ShowNewPair()
            
        
        result = HG.client_controller.Read( 'duplicate_pairs_for_filtering', file_search_context, both_files_match )
        
        if len( result ) == 0:
            
            wx.CallAfter( wx_close )
            
        else:
            
            wx.CallAfter( wx_continue, result )
            
        
    
class CanvasMediaList( ClientMedia.ListeningMediaList, CanvasWithHovers ):
    
    def __init__( self, parent, page_key, media_results ):
        
        CanvasWithHovers.__init__( self, parent )
        ClientMedia.ListeningMediaList.__init__( self, CC.LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._page_key = page_key
        
        self._just_started = True
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
        self.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
        
        HG.client_controller.pub( 'set_focus', self._page_key, None )
        
    
    def _Close( self ):
        
        HG.client_controller.pub( 'set_focus', self._page_key, self._current_media )
        
        CanvasWithHovers._Close( self )
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None:
            
            index_string = '-/' + HydrusData.ToHumanInt( len( self._sorted_media ) )
            
        else:
            
            index_string = HydrusData.ConvertValueRangeToPrettyString( self._sorted_media.index( self._current_media ) + 1, len( self._sorted_media ) )
            
        
        return index_string
        
    
    def _PrefetchNeighbours( self ):
        
        media_looked_at = set()
        
        to_render = []
        
        previous = self._current_media
        next = self._current_media
        
        delay_base = 0.1
        
        num_to_go_back = 3
        num_to_go_forward = 5
        
        # if media_looked_at nukes the list, we want shorter delays, so do next first
        
        for i in range( num_to_go_forward ):
            
            next = self._GetNext( next )
            
            if next in media_looked_at:
                
                break
                
            else:
                
                media_looked_at.add( next )
                
            
            delay = delay_base * ( i + 1 )
            
            to_render.append( ( next, delay ) )
            
        
        for i in range( num_to_go_back ):
            
            previous = self._GetPrevious( previous )
            
            if previous in media_looked_at:
                
                break
                
            else:
                
                media_looked_at.add( previous )
                
            
            delay = delay_base * 2 * ( i + 1 )
            
            to_render.append( ( previous, delay ) )
            
        
        image_cache = HG.client_controller.GetCache( 'images' )
        
        for ( media, delay ) in to_render:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            if IsStaticImage( media ):
                
                if not image_cache.HasImageRenderer( hash ):
                    
                    HG.client_controller.CallLaterWXSafe( self, delay, image_cache.GetImageRenderer, media )
                    
                
            
        
    
    def _Remove( self ):
        
        next_media = self._GetNext( self._current_media )
        
        if next_media == self._current_media:
            
            next_media = None
            
        
        hashes = { self._current_media.GetHash() }
        
        HG.client_controller.pub( 'remove_media', self._page_key, hashes )
        
        singleton_media = { self._current_media }
        
        ClientMedia.ListeningMediaList._RemoveMediaDirectly( self, singleton_media, {} )
        
        if self.HasNoMedia():
            
            self._Close()
            
        elif self.HasMedia( self._current_media ):
            
            HG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self._SetDirty()
            
        else:
            
            self.SetMedia( next_media )
            
        
    
    def _ShowFirst( self ):
        
        self.SetMedia( self._GetFirst() )
        
    
    def _ShowLast( self ):
        
        self.SetMedia( self._GetLast() )
        
    
    def _ShowNext( self ):
        
        self.SetMedia( self._GetNext( self._current_media ) )
        
    
    def _ShowPrevious( self ):
        
        self.SetMedia( self._GetPrevious( self._current_media ) )
        
    
    def _StartSlideshow( self, interval ):
        
        pass
        
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            ClientMedia.ListeningMediaList.AddMediaResults( self, media_results )
            
            HG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self._SetDirty()
            
        
    
    def EventClose( self, event ):
        
        self._Close()
        
    
    def EventFullscreenSwitch( self, event ):
        
        self.GetParent().FullscreenSwitch()
        
    
    def KeepCursorAlive( self ):
        
        self._PutOffCursorHide()
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self.HasMedia( self._current_media ):
            
            next_media = self._GetNext( self._current_media )
            
            if next_media == self._current_media:
                
                next_media = None
                
            
        else:
            
            next_media = None
            
        
        ClientMedia.ListeningMediaList.ProcessContentUpdates( self, service_keys_to_content_updates )
        
        if self.HasNoMedia():
            
            self._Close()
            
        elif self.HasMedia( self._current_media ):
            
            HG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self._SetDirty()
            
        elif self.HasMedia( next_media ):
            
            self.SetMedia( next_media )
            
        else:
            
            self.SetMedia( self._GetFirst() )
            
        
    
class CanvasMediaListFilterArchiveDelete( CanvasMediaList ):
    
    def __init__( self, parent, page_key, media_results ):
        
        CanvasMediaList.__init__( self, parent, page_key, media_results )
        
        self._reserved_shortcut_names.append( 'archive_delete_filter' )
        
        self._kept = set()
        self._deleted = set()
        
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse )
        
        HG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        HG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
        wx.CallAfter( self.SetMedia, self._GetFirst() ) # don't set this until we have a size > (20, 20)!
        
    
    def _Back( self ):
        
        if self._IShouldCatchShortcutEvent():
            
            if self._current_media == self._GetFirst():
                
                return
                
            else:
                
                self._ShowPrevious()
                
                self._kept.discard( self._current_media )
                self._deleted.discard( self._current_media )
                
            
        
    
    def _Close( self ):
        
        if self._IShouldCatchShortcutEvent():
            
            if len( self._kept ) > 0 or len( self._deleted ) > 0:
                
                label = 'keep ' + HydrusData.ToHumanInt( len( self._kept ) ) + ' and delete ' + HydrusData.ToHumanInt( len( self._deleted ) ) + ' files?'
                
                result = ClientGUIDialogsQuick.GetFinishFilteringAnswer( self, label )
                
                if result == wx.ID_CANCEL:
                    
                    if self._current_media in self._kept:
                        
                        self._kept.remove( self._current_media )
                        
                    
                    if self._current_media in self._deleted:
                        
                        self._deleted.remove( self._current_media )
                        
                    
                    return
                    
                elif result == wx.ID_YES:
                    
                    def process_in_thread( service_keys_and_content_updates ):
                        
                        for ( service_key, content_update ) in service_keys_and_content_updates:
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', { service_key : [ content_update ] } )
                            
                        
                    
                    self._deleted_hashes = [ media.GetHash() for media in self._deleted ]
                    self._kept_hashes = [ media.GetHash() for media in self._kept ]
                    
                    service_keys_and_content_updates = []
                    
                    reason = 'Deleted in Archive/Delete filter.'
                    
                    for chunk_of_hashes in HydrusData.SplitListIntoChunks( self._deleted_hashes, 64 ):
                        
                        service_keys_and_content_updates.append( ( CC.LOCAL_FILE_SERVICE_KEY, HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes, reason = reason ) ) )
                        
                    
                    service_keys_and_content_updates.append( ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, self._kept_hashes ) ) )
                    
                    HG.client_controller.CallToThread( process_in_thread, service_keys_and_content_updates )
                    
                    self._kept = set()
                    self._deleted = set()
                    
                    self._current_media = self._GetFirst() # so the pubsub on close is better
                    
                    if HC.options[ 'remove_filtered_files' ]:
                        
                        all_hashes = set()
                        
                        all_hashes.update( self._deleted_hashes )
                        all_hashes.update( self._kept_hashes )
                        
                        HG.client_controller.pub( 'remove_media', self._page_key, all_hashes )
                        
                    
                
            
            CanvasMediaList._Close( self )
            
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return False
            
        
        self._deleted.add( self._current_media )
        
        if self._current_media == self._GetLast(): self._Close()
        else: self._ShowNext()
        
        return True
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUIHoverFrames.FullscreenHoverFrameTopArchiveDeleteFilter( self, self, self._canvas_key )
        
    
    def _Keep( self ):
        
        self._kept.add( self._current_media )
        
        if self._current_media == self._GetLast(): self._Close()
        else: self._ShowNext()
        
    
    def _Skip( self ):
        
        if self._current_media == self._GetLast():
            
            self._Close()
            
        else:
            
            self._ShowNext()
            
        
    
    def Keep( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Keep()
            
        
    
    def Back( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Back()
            
        
    
    def Delete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Delete()
            
        
    
    def EventBack( self, event ):
        
        self._Back()
        
    
    def EventCharHook( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
            
            if modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self._Close()
            else:
                
                CanvasMediaList.EventCharHook( self, event )
                
            
        else:
            
            event.Skip()
            
        
    
    def EventDelete( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            self._Delete()
            
        else:
            
            event.Skip()
            
        
    
    def EventMouse( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            if event.ShiftDown():
                
                caught = True
                
                if event.LeftDown():
                    
                    self.EventDragBegin( event )
                    
                elif event.LeftUp():
                    
                    self.EventDragEnd( event )
                    
                elif event.Dragging():
                    
                    self.EventDrag( event )
                    
                else:
                    
                    caught = False
                    
                
                if caught:
                    
                    return
                    
                
            
            shortcut = ClientGUIShortcuts.ConvertMouseEventToShortcut( event )
            
            if shortcut is not None:
                
                shortcut_processed = self._ProcessShortcut( shortcut )
                
                if shortcut_processed:
                    
                    return
                    
                
            
        
        event.Skip()
        
    
    def EventSkip( self, event ):
        
        self._Skip()
        
    
    def EventUndelete( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            self._Undelete()
            
        else:
            
            event.Skip()
            
        
    
    def ProcessApplicationCommand( self, command, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action in ( 'archive_delete_filter_keep', 'archive_file' ):
                
                self._Keep()
                
            elif action in ( 'archive_delete_filter_delete', 'delete_file' ):
                
                self._Delete()
                
            elif action == 'archive_delete_filter_skip':
                
                self._Skip()
                
            elif action == 'archive_delete_filter_back':
                
                self._Back()
                
            elif action == 'launch_the_archive_delete_filter':
                
                self._Close()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasMediaList.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def Skip( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Skip()
            
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
class CanvasMediaListNavigable( CanvasMediaList ):
    
    def __init__( self, parent, page_key, media_results ):
        
        CanvasMediaList.__init__( self, parent, page_key, media_results )
        
        self._reserved_shortcut_names.append( 'media_viewer_browser' )
        
        HG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        HG.client_controller.sub( self, 'ShowNext', 'canvas_show_next' )
        HG.client_controller.sub( self, 'ShowPrevious', 'canvas_show_previous' )
        HG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUIHoverFrames.FullscreenHoverFrameTopNavigableList( self, self, self._canvas_key )
        
    
    def Archive( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Archive()
            
        
    
    def Delete( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Delete()
            
        
    
    def EventArchive( self, event ):
        
        self._Archive()
        
    
    def EventDelete( self, event ):
        
        self._Delete()
        
    
    def EventNext( self, event ):
        
        self._ShowNext()
        
    
    def EventPrevious( self, event ):
        
        self._ShowPrevious()
        
    
    def Inbox( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Inbox()
            
        
    
    def ProcessApplicationCommand( self, command, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'remove_file_from_view':
                
                self._Remove()
                
            elif action == 'view_first':
                
                self._ShowFirst()
                
            elif action == 'view_last':
                
                self._ShowLast()
                
            elif action == 'view_previous':
                
                self._ShowPrevious()
                
            elif action == 'view_next':
                
                self._ShowNext()
                
            elif action == 'remove_file_from_view':
                
                self._Remove()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasMediaList.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def ShowFirst( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowFirst()
            
        
    
    def ShowLast( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowLast()
            
        
    
    def ShowNext( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowNext()
            
        
    
    def ShowPrevious( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowPrevious()
            
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
class CanvasMediaListBrowser( CanvasMediaListNavigable ):
    
    def __init__( self, parent, page_key, media_results, first_hash ):
        
        CanvasMediaListNavigable.__init__( self, parent, page_key, media_results )
        
        self._timer_slideshow_job = None
        self._timer_slideshow_interval = 0
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventClose )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventClose )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        if first_hash is None:
            
            first_media = self._GetFirst()
            
        else:
            
            try:
                
                first_media = self._GetMedia( { first_hash } )[0]
                
            except:
                
                first_media = self._GetFirst()
                
            
        
        wx.CallAfter( self.SetMedia, first_media ) # don't set this until we have a size > (20, 20)!
        
        HG.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        
    
    def _PausePlaySlideshow( self ):
        
        if self._timer_slideshow_job is not None:
            
            self._StopSlideshow()
            
        elif self._timer_slideshow_interval > 0:
            
            self._StartSlideshow( self._timer_slideshow_interval )
            
        
    
    def _StartSlideshow( self, interval = None ):
        
        self._StopSlideshow()
        
        if interval is None:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter the interval, in seconds.', default = '15' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    try:
                        
                        interval = float( dlg.GetValue() )
                        
                    except:
                        
                        return
                        
                    
                
            
        
        if interval > 0:
            
            self._timer_slideshow_interval = interval
            
            self._timer_slideshow_job = HG.client_controller.CallLaterWXSafe( self, self._timer_slideshow_interval, self.DoSlideshow )
            
        
    
    def _StopSlideshow( self ):
        
        if self._timer_slideshow_job is not None:
            
            self._timer_slideshow_job.Cancel()
            
            self._timer_slideshow_job = None
            
        
    
    def DoSlideshow( self ):
        
        try:
            
            if self._current_media is not None and self._timer_slideshow_job is not None:
                
                if self._media_container.ReadyToSlideshow() and not HG.client_controller.MenuIsOpen():
                    
                    self._ShowNext()
                    
                    self._timer_slideshow_job = HG.client_controller.CallLaterWXSafe( self, self._timer_slideshow_interval, self.DoSlideshow )
                    
                else:
                    
                    self._timer_slideshow_job = HG.client_controller.CallLaterWXSafe( self, 0.5, self.DoSlideshow )
                    
                
            
        except:
            
            self._timer_slideshow_job = None
            
            raise
            
        
    
    def EventCharHook( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
            
            if modifier == wx.ACCEL_NORMAL and key in CC.DELETE_KEYS: self._Delete()
            elif modifier == wx.ACCEL_SHIFT and key in CC.DELETE_KEYS: self._Undelete()
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE ): self._PausePlaySlideshow()
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self._Close()
            else:
                
                CanvasMediaListNavigable.EventCharHook( self, event )
                
            
        else:
            
            event.Skip()
            
        
    
    def EventMouseWheel( self, event ):
        
        if self._IShouldCatchShortcutEvent( event = event ):
            
            if event.CmdDown():
                
                if event.GetWheelRotation() > 0:
                    
                    self._ZoomIn()
                    
                else:
                    
                    self._ZoomOut()
                    
                
            else:
                
                if event.GetWheelRotation() > 0:
                    
                    self._ShowPrevious()
                    
                else:
                    
                    self._ShowNext()
                    
                
            
        else:
            
            event.Skip()
            
        
    
    def EventShowMenu( self, event ):
        
        if self._current_media is not None:
            
            new_options = HG.client_controller.new_options
            
            advanced_mode = new_options.GetBoolean( 'advanced_mode' )
        
            services = HG.client_controller.services_manager.GetServices()
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            self._last_drag_coordinates = None # to stop successive right-click drag warp bug
            
            locations_manager = self._current_media.GetLocationsManager()
            
            menu = wx.Menu()
            
            for line in self._current_media.GetPrettyInfoLines():
                
                ClientGUIMenus.AppendMenuLabel( menu, line, line )
                
            
            ClientGUIMedia.AddFileViewingStatsMenu( menu, self._current_media )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._IsZoomable():
                
                ClientGUIMenus.AppendMenuLabel( menu, 'current zoom: ' + ClientData.ConvertZoomToPercentage( self._current_zoom ) )
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'zoom in', 'Zoom the media in.', self._ZoomIn )
                ClientGUIMenus.AppendMenuItem( self, menu, 'zoom out', 'Zoom the media out.', self._ZoomOut )
                
                if self._current_media.GetMime() != HC.APPLICATION_FLASH:
                    
                    if self._current_zoom != 1.0:
                        
                        ClientGUIMenus.AppendMenuItem( self, menu, 'zoom to 100%', 'Set the zoom to 100%.', self._ZoomSwitch )
                        
                    elif self._current_zoom != self._canvas_zoom:
                        
                        ClientGUIMenus.AppendMenuItem( self, menu, 'zoom fit', 'Set the zoom so the media fits the canvas.', self._ZoomSwitch )
                        
                    
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            manage_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, manage_menu, 'tags', 'Manage this file\'s tags.', self._ManageTags )
            
            if i_can_post_ratings:
                
                ClientGUIMenus.AppendMenuItem( self, manage_menu, 'ratings', 'Manage this file\'s ratings.', self._ManageRatings )
                
            
            ClientGUIMenus.AppendMenuItem( self, manage_menu, 'known urls', 'Manage this file\'s known urls.', self._ManageURLs )
            ClientGUIMenus.AppendMenuItem( self, manage_menu, 'notes', 'Manage this file\'s notes.', self._ManageNotes )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._current_media.HasInbox():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'archive', 'Archive this file, taking it out of the inbox.', self._Archive )
                
            elif self._current_media.HasArchive():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'return to inbox', 'Put this file back in the inbox.', self._Inbox )
                
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'remove from view', 'Remove this file from the list you are viewing.', self._Remove )
            
            if CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'delete', 'Send this file to the trash.', self._Delete, file_service_key = CC.LOCAL_FILE_SERVICE_KEY )
                
            elif CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'delete from trash now', 'Delete this file immediately. This cannot be undone.', self._Delete, file_service_key = CC.TRASH_SERVICE_KEY )
                ClientGUIMenus.AppendMenuItem( self, menu, 'undelete', 'Take this file out of the trash, returning it to its original file service.', self._Undelete )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'open externally', 'Open this file in the default external program.', self._OpenExternally )
            
            ClientGUIMedia.AddKnownURLsViewCopyMenu( self, menu, self._current_media )
            
            share_menu = wx.Menu()
            
            show_open_in_web = True
            show_open_in_explorer = advanced_mode and not HC.PLATFORM_LINUX
            
            if show_open_in_web or show_open_in_explorer:
                
                open_menu = wx.Menu()
                
                if show_open_in_web:
                    
                    ClientGUIMenus.AppendMenuItem( self, open_menu, 'in web browser', 'Show this file in your OS\'s web browser.', self._OpenFileInWebBrowser )
                    
                
                if show_open_in_explorer:
                    
                    ClientGUIMenus.AppendMenuItem( self, open_menu, 'in file browser', 'Show this file in your OS\'s file browser.', self._OpenFileLocation )
                    
                
                ClientGUIMenus.AppendMenu( share_menu, open_menu, 'open' )
                
            
            copy_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, copy_menu, 'file', 'Copy this file to your clipboard.', self._CopyFileToClipboard )
            
            copy_hash_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha256 (hydrus default)', 'Copy this file\'s SHA256 hash to your clipboard.', self._CopyHashToClipboard, 'sha256' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'md5', 'Copy this file\'s MD5 hash to your clipboard.', self._CopyHashToClipboard, 'md5' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha1', 'Copy this file\'s SHA1 hash to your clipboard.', self._CopyHashToClipboard, 'sha1' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha512', 'Copy this file\'s SHA512 hash to your clipboard.', self._CopyHashToClipboard, 'sha512' )
            
            ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
            
            if self._current_media.GetMime() in HC.IMAGES and self._current_media.GetDuration() is None:
                
                ClientGUIMenus.AppendMenuItem( self, copy_menu, 'image (bitmap)', 'Copy this file to your clipboard as a BMP image.', self._CopyBMPToClipboard )
                
            
            ClientGUIMenus.AppendMenuItem( self, copy_menu, 'path', 'Copy this file\'s path to your clipboard.', self._CopyPathToClipboard )
            
            ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
            
            ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            slideshow = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, slideshow, '1 second', 'Start a slideshow with a one second interval.', self._StartSlideshow, 1.0 )
            ClientGUIMenus.AppendMenuItem( self, slideshow, '5 second', 'Start a slideshow with a five second interval.', self._StartSlideshow, 5.0 )
            ClientGUIMenus.AppendMenuItem( self, slideshow, '10 second', 'Start a slideshow with a ten second interval.', self._StartSlideshow, 10.0 )
            ClientGUIMenus.AppendMenuItem( self, slideshow, '30 second', 'Start a slideshow with a thirty second interval.', self._StartSlideshow, 30.0 )
            ClientGUIMenus.AppendMenuItem( self, slideshow, '60 second', 'Start a slideshow with a one minute interval.', self._StartSlideshow, 60.0 )
            ClientGUIMenus.AppendMenuItem( self, slideshow, 'very fast', 'Start a very fast slideshow.', self._StartSlideshow, 0.08 )
            ClientGUIMenus.AppendMenuItem( self, slideshow, 'custom interval', 'Start a slideshow with a custom interval.', self._StartSlideshow )
            
            ClientGUIMenus.AppendMenu( menu, slideshow, 'start slideshow' )
            
            if self._timer_slideshow_job is not None:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'stop slideshow', 'Stop the current slideshow.', self._PausePlaySlideshow )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self.GetParent().IsFullScreen():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'exit fullscreen', 'Make this media viewer a regular window with borders.', self.GetParent().FullscreenSwitch )
                
            else:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'go fullscreen', 'Make this media viewer a fullscreen window without borders.', self.GetParent().FullscreenSwitch )
                
            
            HG.client_controller.PopupMenu( self, menu )
            
        
        event.Skip()
        
    
class MediaContainer( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._media = None
        self._show_action = None
        
        self._media_window = None
        
        self._embed_button = EmbedButton( self )
        self._embed_button.Bind( wx.EVT_LEFT_DOWN, self.EventEmbedButton )
        
        self._animation_window = Animation( self )
        self._animation_bar = AnimationBar( self )
        self._static_image_window = StaticImage( self )
        
        self._animation_window.Hide()
        self._animation_bar.Hide()
        self._static_image_window.Hide()
        
        self.Hide()
        
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventPropagateMouse )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _DestroyOrHideThisMediaWindow( self, media_window ):
        
        if media_window is not None:
            
            if isinstance( media_window, ( Animation, StaticImage ) ):
                
                media_window.SetNoneMedia()
                media_window.Hide()
                
            else:
                
                media_window.DestroyLater()
                
            
        
    
    def _HideAnimationBar( self ):
        
        self._animation_bar.SetNoneMedia()
        
        self._animation_bar.Hide()
        
    
    def _MakeMediaWindow( self ):
        
        old_media_window = self._media_window
        destroy_old_media_window = True
        
        ( media_initial_size, media_initial_position ) = ( self.GetClientSize(), ( 0, 0 ) )
        
        if self._media.GetMime() == HC.APPLICATION_FLASH and not FLASHWIN_OK:
            
            self._show_action = CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON
            
        
        if self._show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            raise Exception( 'This media should not be shown in the media viewer!' )
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON:
            
            self._media_window = OpenExternallyPanel( self, self._media )
            
            self._HideAnimationBar()
            
        else:
            
            start_paused = self._show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL_PAUSED, CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED )
            
            if ShouldHaveAnimationBar( self._media ) or self._media.GetMime() == HC.APPLICATION_FLASH:
                
                if ShouldHaveAnimationBar( self._media ):
                    
                    ( x, y ) = media_initial_size
                    
                    media_initial_size = ( x, y - ANIMATED_SCANBAR_HEIGHT )
                    
                
                if self._media.GetMime() == HC.APPLICATION_FLASH:
                    
                    if isinstance( self._media_window, wx.lib.flashwin.FlashWindow ):
                        
                        destroy_old_media_window = False
                        
                    else:
                        
                        self._media_window = wx.lib.flashwin.FlashWindow( self, size = media_initial_size, pos = media_initial_position )
                        
                        if self._media_window is None:
                            
                            raise Exception( 'Failed to initialise the flash window' )
                            
                        
                    
                    client_files_manager = HG.client_controller.client_files_manager
                    
                    self._media_window.LoadMovie( 0, client_files_manager.GetFilePath( self._media.GetHash(), HC.APPLICATION_FLASH ) )
                    
                else:
                    
                    if isinstance( self._media_window, Animation ):
                        
                        destroy_old_media_window = False
                        
                    else:
                        
                        self._animation_window.Show()
                        
                        self._media_window = self._animation_window
                        
                    
                    self._media_window.SetMedia( self._media, start_paused = start_paused )
                    
                
                if ShouldHaveAnimationBar( self._media ):
                    
                    self._animation_bar.Show()
                    
                    self._animation_bar.SetMediaAndWindow( self._media, self._media_window )
                    
                else:
                    
                    self._HideAnimationBar()
                    
                
            else:
                
                if isinstance( self._media_window, StaticImage ):
                    
                    destroy_old_media_window = False
                    
                else:
                    
                    self._static_image_window.Show()
                    
                    self._media_window = self._static_image_window
                    
                
                self._media_window.SetMedia( self._media )
                
                self._HideAnimationBar()
                
            
        
        if old_media_window is not None and destroy_old_media_window:
            
            self._DestroyOrHideThisMediaWindow( old_media_window )
            
        
    
    def _SizeAndPositionChildren( self ):
        
        if self._media is not None:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            if self._media_window is None:
                
                self._embed_button.SetSize( ( my_width, my_height ) )
                self._embed_button.SetPosition( ( 0, 0 ) )
                
            else:
                
                is_open_externally = isinstance( self._media_window, OpenExternallyPanel )
                
                ( media_width, media_height ) = ( my_width, my_height )
                
                if ShouldHaveAnimationBar( self._media ) and not is_open_externally:
                    
                    media_height -= ANIMATED_SCANBAR_HEIGHT
                    
                    self._animation_bar.SetSize( ( my_width, ANIMATED_SCANBAR_HEIGHT ) )
                    self._animation_bar.SetPosition( ( 0, my_height - ANIMATED_SCANBAR_HEIGHT ) )
                    
                
                self._media_window.SetSize( ( media_width, media_height ) )
                self._media_window.SetPosition( ( 0, 0 ) )
                
            
        
    
    def BeginDrag( self ):
        
        self.GetParent().BeginDrag()
        
    
    def EventEmbedButton( self, event ):
        
        self._embed_button.Hide()
        
        self._MakeMediaWindow()
        
        self._SizeAndPositionChildren()
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventPropagateMouse( self, event ):
        
        if self._media is not None:
            
            mime = self._media.GetMime()
            
            if mime in HC.IMAGES or mime in HC.VIDEO:
                
                screen_position = ClientGUIFunctions.ClientToScreen( self, event.GetPosition() )
                ( x, y ) = self.GetParent().ScreenToClient( screen_position )
                
                event.SetX( x )
                event.SetY( y )
                
                event.ResumePropagation( 1 )
                event.Skip()
                
            
        
    
    def EventResize( self, event ):
        
        if self._media is not None:
            
            self._SizeAndPositionChildren()
            
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        if self._media is not None:
            
            if ShouldHaveAnimationBar( self._media ):
                
                current_frame_index = self._media_window.CurrentFrame()
                
                num_frames = self._media.GetNumFrames()
                
                if direction == 1:
                    
                    if current_frame_index == num_frames - 1:
                        
                        current_frame_index = 0
                        
                    else:
                        
                        current_frame_index += 1
                        
                    
                else:
                    
                    if current_frame_index == 0:
                        
                        current_frame_index = num_frames - 1
                        
                    else:
                        
                        current_frame_index -= 1
                        
                    
                
                self._media_window.GotoFrame( current_frame_index )
                
            
        
    
    def MouseIsNearAnimationBar( self ):
        
        if self._media is None:
            
            return False
            
        else:
            
            if ShouldHaveAnimationBar( self._media ):
                
                ( x, y ) = self._animation_bar.GetScreenPosition()
                ( width, height ) = self._animation_bar.GetSize()
                
                ( mouse_x, mouse_y ) = wx.GetMousePosition()
                
                buffer_distance = 100
                
                if mouse_x >= x - buffer_distance and mouse_x <= x + width + buffer_distance and mouse_y >= y - buffer_distance and mouse_y <= y + height + buffer_distance:
                    
                    return True
                    
                
            
            return False
            
        
    
    def Pause( self ):
        
        if self._media is not None:
            
            if isinstance( self._media_window, Animation ):
                
                self._media_window.Pause()
                
            
        
    
    def ReadyToSlideshow( self ):
        
        if self._media is None:
            
            return False
            
        else:
            
            if isinstance( self._media_window, Animation ):
                
                if self._media_window.IsPlaying() and not self._media_window.HasPlayedOnceThrough():
                    
                    return False
                    
                
            
            if isinstance( self._media_window, StaticImage ):
                
                if not self._media_window.IsRendered():
                    
                    return False
                    
                
            
            return True
            
        
    
    def SetEmbedButton( self ):
        
        self._HideAnimationBar()
        
        self._DestroyOrHideThisMediaWindow( self._media_window )
        
        self._media_window = None
        
        self._embed_button.SetMedia( self._media )
        
        self._embed_button.Show()
        
    
    def SetMedia( self, media, initial_size, initial_position, show_action ):
        
        self._media = media
        
        self.Show()
        
        self._show_action = show_action
        
        if self._show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED ):
            
            self.SetEmbedButton()
            
        else:
            
            self._embed_button.Hide()
            
            self._MakeMediaWindow()
            
        
        self.SetSize( initial_size )
        self.SetPosition( initial_position )
        
        self._SizeAndPositionChildren()
        
    
    def SetNoneMedia( self ):
        
        self._media = None
        
        self._HideAnimationBar()
        
        self._DestroyOrHideThisMediaWindow( self._media_window )
        
        self._media_window = None
        
        self.Hide()
        
    
class EmbedButton( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._media = None
        
        self._dirty = False
        
        self._canvas_bmp = None
        self._thumbnail_bmp = None
        
        self.SetCursor( wx.Cursor( wx.CURSOR_HAND ) )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        HG.client_controller.sub( self, '_SetDirty', 'notify_new_colourset' )
        
    
    def _Redraw( self, dc ):
        
        ( x, y ) = self.GetClientSize()
        
        center_x = x // 2
        center_y = y // 2
        radius = min( 50, center_x, center_y ) - 5
        
        new_options = HG.client_controller.new_options
        
        dc.SetBackground( wx.Brush( new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) ) )
        
        dc.Clear()
        
        if self._thumbnail_bmp is not None:
            
            if ShouldHaveAnimationBar( self._media ):
                
                # animations will have the animation bar space underneath in this case, so colour it in
                dc.SetBackground( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) ) )
                
                dc.DrawRectangle( 0, y - ANIMATED_SCANBAR_HEIGHT, x, ANIMATED_SCANBAR_HEIGHT )
                
            
            ( thumb_width, thumb_height ) = self._thumbnail_bmp.GetSize()
            
            scale = x / thumb_width
            
            dc.SetUserScale( scale, scale )
            
            dc.DrawBitmap( self._thumbnail_bmp, 0, 0 )
            
            dc.SetUserScale( 1.0, 1.0 )
            
        
        dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) ) )
        
        dc.DrawCircle( center_x, center_y, radius )
        
        dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) ) )
        
        # play symbol is a an equilateral triangle
        
        triangle_side = radius * 0.8
        
        half_triangle_side = int( triangle_side // 2 )
        
        cos30 = 0.866
        
        triangle_width = triangle_side * cos30
        
        third_triangle_width = int( triangle_width // 3 )
        
        points = []
        
        points.append( ( center_x - third_triangle_width, center_y - half_triangle_side ) )
        points.append( ( center_x + third_triangle_width * 2, center_y ) )
        points.append( ( center_x - third_triangle_width, center_y + half_triangle_side ) )
        
        dc.DrawPolygon( points )
        
        #
        
        dc.SetPen( wx.Pen( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNSHADOW ) ) )
        
        dc.SetBrush( wx.TRANSPARENT_BRUSH )
        
        dc.DrawRectangle( 0, 0, x, y )
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
        self.Refresh()
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventPaint( self, event ):
        
        if self._canvas_bmp is not None:
            
            dc = wx.BufferedPaintDC( self, self._canvas_bmp )
            
            if self._dirty:
                
                self._Redraw( dc )
                
            
        
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if my_width > 0 and my_height > 0:
            
            if self._canvas_bmp is None:
                
                make_new_one = True
                
            else:
                
                ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
                
                make_new_one = my_width != current_bmp_width or my_height != current_bmp_height
                
            
            if make_new_one:
                
                if self._canvas_bmp is not None:
                    
                    HG.client_controller.bitmap_manager.ReleaseBitmap( self._canvas_bmp )
                    
                
                self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( my_width, my_height, 24 )
                
                self._SetDirty()
                
            
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        if self._media is None:
            
            needs_thumb = False
            
        else:
            
            needs_thumb = self._media.GetLocationsManager().IsLocal() and self._media.GetMime() in HC.MIMES_WITH_THUMBNAILS
            
        
        if needs_thumb:
            
            mime = self._media.GetMime()
            
            thumbnail_path = HG.client_controller.client_files_manager.GetThumbnailPath( self._media )
            
            self._thumbnail_bmp = ClientRendering.GenerateHydrusBitmap( thumbnail_path, mime ).GetWxBitmap()
            
            self._SetDirty()
            
        else:
            
            self._thumbnail_bmp = None
            
        
    
class OpenExternallyPanel( wx.Panel ):
    
    def __init__( self, parent, media ):
        
        wx.Panel.__init__( self, parent )
        
        self._new_options = HG.client_controller.new_options
        
        self.SetBackgroundColour( self._new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) )
        
        self._media = media
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        if self._media.GetLocationsManager().IsLocal() and self._media.GetMime() in HC.MIMES_WITH_THUMBNAILS:
            
            mime = self._media.GetMime()
            
            thumbnail_path = HG.client_controller.client_files_manager.GetThumbnailPath( self._media )
            
            bmp = ClientRendering.GenerateHydrusBitmap( thumbnail_path, mime ).GetWxBitmap()
            
            thumbnail_window = ClientGUICommon.BufferedWindowIcon( self, bmp )
            
            thumbnail_window.Bind( wx.EVT_LEFT_DOWN, self.EventButton )
            
            vbox.Add( thumbnail_window, CC.FLAGS_CENTER )
            
        
        m_text = HC.mime_string_lookup[ media.GetMime() ]
        
        button = wx.Button( self, label = 'open ' + m_text + ' externally', size = OPEN_EXTERNALLY_BUTTON_SIZE )
        
        vbox.Add( button, CC.FLAGS_CENTER )
        
        self.SetSizer( vbox )
        
        self.SetCursor( wx.Cursor( wx.CURSOR_HAND ) )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventButton )
        button.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        launch_path = self._new_options.GetMimeLaunch( mime )
        
        HydrusPaths.LaunchFile( path, launch_path )
        
    
class StaticImage( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._dirty = True
        
        self._media = None
        
        self._first_background_drawn = False
        
        self._image_renderer = None
        
        self._is_rendered = False
        
        self._canvas_bmp = None
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventPropagateMouse )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _DrawBackground( self, dc ):
        
        new_options = HG.client_controller.new_options
        
        dc.SetBackground( wx.Brush( new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) ) )
        
        dc.Clear()
        
        self._first_background_drawn = True
        
    
    def _Redraw( self, dc ):
        
        if self._image_renderer is not None and self._image_renderer.IsReady():
            
            self._DrawBackground( dc )
            
            wx_bitmap = self._image_renderer.GetWXBitmap( self._canvas_bmp.GetSize() )
            
            dc.DrawBitmap( wx_bitmap, 0, 0 )
            
            HG.client_controller.bitmap_manager.ReleaseBitmap( wx_bitmap )
            
            self._is_rendered = True
            
        else:
            
            if not self._first_background_drawn:
                
                self._DrawBackground( dc )
                
            
        
        self._dirty = False
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
        self.Refresh()
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventPaint( self, event ):
        
        if self._canvas_bmp is None:
            
            return
            
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if self._dirty:
            
            self._Redraw( dc )
            
        
    
    def EventPropagateMouse( self, event ):
        
        screen_position = ClientGUIFunctions.ClientToScreen( self, event.GetPosition() )
        ( x, y ) = self.GetParent().ScreenToClient( screen_position )
        
        event.SetX( x )
        event.SetY( y )
        
        event.ResumePropagation( 1 )
        event.Skip()
        
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if my_width > 0 and my_height > 0:
            
            if self._canvas_bmp is None:
                
                make_new_one = True
                
            else:
                
                ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
                
                make_new_one = my_width != current_bmp_width or my_height != current_bmp_height
                
            
            if make_new_one:
                
                if self._canvas_bmp is not None:
                    
                    HG.client_controller.bitmap_manager.ReleaseBitmap( self._canvas_bmp )
                    
                
                self._canvas_bmp = HG.client_controller.bitmap_manager.GetBitmap( my_width, my_height, 24 )
                
                self._first_background_drawn = False
                
                self._SetDirty()
                
            
        
    
    def IsRendered( self ):
        
        return self._is_rendered
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        image_cache = HG.client_controller.GetCache( 'images' )
        
        self._image_renderer = image_cache.GetImageRenderer( self._media )
        
        self._is_rendered = False
        
        if not self._image_renderer.IsReady():
            
            HG.client_controller.gui.RegisterAnimationUpdateWindow( self )
            
        
        self._SetDirty()
        
    
    def SetNoneMedia( self ):
        
        self._media = None
        self._image_renderer = None
        self._is_rendered = False
        self._first_background_drawn = False
        
    
    def TIMERAnimationUpdate( self ):
        
        try:
            
            if self._image_renderer is None or self._image_renderer.IsReady():
                
                self._SetDirty()
                
                HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
                
            
        except:
            
            HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
            raise
            
        
    
