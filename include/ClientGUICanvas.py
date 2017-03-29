import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import ClientCaches
import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIDialogsManage
import ClientGUIHoverFrames
import ClientGUIMenus
import ClientGUIScrolledPanelsManagement
import ClientGUITopLevelWindows
import ClientMedia
import ClientRatings
import ClientRendering
import ClientTags
import gc
import HydrusImageHandling
import HydrusPaths
import HydrusTags
import os
import wx

if HC.PLATFORM_WINDOWS: import wx.lib.flashwin

ID_TIMER_VIDEO = wx.NewId()
ID_TIMER_RENDER_WAIT = wx.NewId()
ID_TIMER_ANIMATION_BAR_UPDATE = wx.NewId()
ID_TIMER_SLIDESHOW = wx.NewId()
ID_TIMER_CURSOR_HIDE = wx.NewId()
ID_TIMER_HOVER_SHOW = wx.NewId()

ANIMATED_SCANBAR_HEIGHT = 20
ANIMATED_SCANBAR_CARET_WIDTH = 10

OPEN_EXTERNALLY_BUTTON_SIZE = ( 200, 45 )

def CalculateCanvasMediaSize( media, ( canvas_width, canvas_height ) ):
    
    if ShouldHaveAnimationBar( media ):
        
        canvas_height -= ANIMATED_SCANBAR_HEIGHT
        
    
    if media.GetMime() == HC.APPLICATION_FLASH:
        
        canvas_height -= 10
        canvas_width -= 10
        
    
    return ( canvas_width, canvas_height )
    
def CalculateCanvasZooms( canvas, media, show_action ):
    
    if media is None:
        
        return ( 1.0, 1.0 )
        
    
    if show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
        
        return ( 1.0, 1.0 )
        
    
    ( media_width, media_height ) = media.GetResolution()
    
    if media_width == 0 or media_height == 0:
        
        return ( 1.0, 1.0 )
        
    
    new_options = HydrusGlobals.client_controller.GetNewOptions()
    
    ( canvas_width, canvas_height ) = CalculateCanvasMediaSize( media, canvas.GetClientSize() )
    
    width_zoom = canvas_width / float( media_width )
    
    height_zoom = canvas_height / float( media_height )
    
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
            
            ( thumb_width, thumb_height ) = HydrusImageHandling.GetThumbnailResolution( media.GetResolution(), HC.UNSCALED_THUMBNAIL_DIMENSIONS )
            
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
    
def ShouldHaveAnimationBar( media ):
    
    is_animated_gif = media.GetMime() == HC.IMAGE_GIF and media.HasDuration()
    
    is_animated_flash = media.GetMime() == HC.APPLICATION_FLASH and media.HasDuration()
    
    is_native_video = media.GetMime() in HC.NATIVE_VIDEO
    
    has_more_than_one_frame = media.GetNumFrames() > 1
    
    return is_animated_gif or is_animated_flash or is_native_video
    
class Animation( wx.Window ):
    
    TIMER_MS = 5
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._media = None
        
        self._animation_bar = None
        
        self._drag_happened = False
        self._left_down_event = None
        
        self._a_frame_has_been_drawn = False
        self._has_played_once_through = False
        
        self._num_frames = 1
        
        self._current_frame_index = 0
        self._current_frame_drawn = False
        self._next_frame_due_at = HydrusData.GetNowPrecise()
        self._slow_frame_score = 1.0
        
        self._paused = True
        
        self._video_container = None
        
        self._canvas_bmp = None
        self._frame_bmp = None
        
        self._timer_video = wx.Timer( self, id = ID_TIMER_VIDEO )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_TIMER, self.TIMEREventVideo, id = ID_TIMER_VIDEO )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventPropagateMouse )
        self.Bind( wx.EVT_KEY_UP, self.EventPropagateKey )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def __del__( self ):
        
        if self._video_container is not None:
            
            self._video_container.Stop()
            
        
        if self._frame_bmp is not None:
            
            self._frame_bmp.Destroy()
            
        
        if self._canvas_bmp is not None:
            
            self._canvas_bmp.Destroy()
            
        
        wx.CallLater( 500, gc.collect )
        
    
    def _DrawFrame( self, dc ):
        
        current_frame = self._video_container.GetFrame( self._current_frame_index )
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        ( frame_width, frame_height ) = current_frame.GetSize()
        
        if self._frame_bmp is None or self._frame_bmp.GetSize() != current_frame.GetSize():
            
            self._frame_bmp = wx.EmptyBitmap( frame_width, frame_height, current_frame.GetDepth() * 8 )
            
        
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
            
            scale = float( my_width ) / frame_width
            
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
            
        
        if self._animation_bar is not None:
            
            self._animation_bar.GotoFrame( self._current_frame_index )
            
        
        self._current_frame_drawn = True
        
        next_frame_time_s = self._video_container.GetDuration( self._current_frame_index ) / 1000.0
        
        next_frame_ideally_due = self._next_frame_due_at + next_frame_time_s
        
        if HydrusData.TimeHasPassedPrecise( next_frame_ideally_due ):
            
            self._next_frame_due_at = HydrusData.GetNowPrecise() + next_frame_time_s
            
        else:
            
            self._next_frame_due_at = next_frame_ideally_due
            
        
        self._a_frame_has_been_drawn = True
        
    
    def _DrawWhite( self, dc ):
        
        dc.SetBackground( wx.Brush( wx.Colour( *HC.options[ 'gui_colours' ][ 'media_background' ] ) ) )
        
        dc.Clear()
        
    
    def _TellAnimationBarAboutPausedStatus( self ):
        
        if self._animation_bar is not None:
            
            self._animation_bar.SetPaused( self._paused )
            
        
    
    def CurrentFrame( self ):
        
        return self._current_frame_index
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventPaint( self, event ):
        
        if self._video_container is None:
            
            self._video_container = ClientRendering.RasterContainerVideo( self._media, self.GetClientSize(), init_position = self._current_frame_index )
            
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if not self._a_frame_has_been_drawn:
            
            self._DrawWhite( dc )
            
        
    
    def EventPropagateKey( self, event ):
        
        event.ResumePropagation( 1 )
        event.Skip()
        
    
    def EventPropagateMouse( self, event ):
        
        if self._animation_bar is not None:
            
            etype = event.GetEventType()
            
            if not ( event.ShiftDown() or event.CmdDown() or event.AltDown() ):
                
                if etype == wx.wxEVT_LEFT_DOWN:
                    
                    self.PausePlay()
                    
                    self.GetParent().BeginDrag()
                    
                    return
                    
                
            
        
        screen_position = self.ClientToScreen( event.GetPosition() )
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
                    
                    wx.CallAfter( self._canvas_bmp.Destroy )
                    
                
                self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
                
                self._current_frame_drawn = False
                self._a_frame_has_been_drawn = False
                
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
                                
                            
                        
                    
                
            
        
    
    def GotoFrame( self, frame_index ):
        
        if self._video_container is not None and self._video_container.IsInitialised():
            
            if frame_index != self._current_frame_index:
                
                self._current_frame_index = frame_index
                
                self._video_container.GetReadyForFrame( self._current_frame_index )
                
                self._current_frame_drawn = False
                
            
            self._paused = True
            
            self._TellAnimationBarAboutPausedStatus()
            
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._has_played_once_through
        
    
    def IsPlaying( self ):
        
        return not self._paused
        
    
    def Play( self ):
        
        self._paused = False
        
        self._TellAnimationBarAboutPausedStatus()
        
    
    def Pause( self ):
        
        self._paused = True
        
        self._TellAnimationBarAboutPausedStatus()
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
        self._TellAnimationBarAboutPausedStatus()
        
    
    def SetAnimationBar( self, animation_bar ):
        
        self._animation_bar = animation_bar
        
        if self._animation_bar is not None:
            
            self._animation_bar.GotoFrame( self._current_frame_index )
            
            self._TellAnimationBarAboutPausedStatus()
            
        
    
    def SetMedia( self, media, start_paused ):
        
        self._media = media
        
        self._drag_happened = False
        self._left_down_event = None
        
        self._a_frame_has_been_drawn = False
        self._has_played_once_through = False
        
        self._num_frames = self._media.GetNumFrames()
        
        self._current_frame_index = int( ( self._num_frames - 1 ) * HC.options[ 'animation_start_position' ] )
        self._current_frame_drawn = False
        self._next_frame_due_at = HydrusData.GetNowPrecise()
        self._slow_frame_score = 1.0
        
        self._paused = start_paused
        
        if self._video_container is not None:
            
            self._video_container.Stop()
            
        
        self._video_container = None
        
        self._frame_bmp = None
        
        self._timer_video.Start( self.TIMER_MS, wx.TIMER_CONTINUOUS )
        
        self.Refresh()
        
    
    def TIMEREventVideo( self, event ):
        
        try:
            
            if self.IsShownOnScreen():
                
                if self._current_frame_drawn:
                    
                    if not self._paused and HydrusData.TimeHasPassedPrecise( self._next_frame_due_at - self.TIMER_MS / 1000.0 ):
                        
                        num_frames = self._media.GetNumFrames()
                        
                        self._current_frame_index = ( self._current_frame_index + 1 ) % num_frames
                        
                        if self._current_frame_index == 0:
                            
                            self._has_played_once_through = True
                            
                        
                        self._current_frame_drawn = False
                        
                    
                
                if self._video_container is not None:
                    
                    if not self._current_frame_drawn:
                        
                        if self._video_container.HasFrame( self._current_frame_index ):
                            
                            dc = wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
                            
                            self._DrawFrame( dc )
                            
                        
                    
                    if self._animation_bar is not None:
                        
                        buffer_indices = self._video_container.GetBufferIndices()
                        
                        self._animation_bar.SetBufferIndices( buffer_indices )
                        
                    
                
            
        except wx.PyDeadObjectError:
            
            self._timer_video.Stop()
            
        except:
            
            self._timer_video.Stop()
            
            raise
            
        
    
class AnimationBar( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._dirty = False
        
        self._canvas_bmp = None
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
        
        self._media_window = None
        self._paused = False
        self._num_frames = 1
        self._current_frame_index = 0
        self._buffer_indices = None
        
        self._has_experienced_mouse_down = False
        self._currently_in_a_drag = False
        self._it_was_playing = False
        
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse )
        self.Bind( wx.EVT_TIMER, self.TIMERFlashIndexUpdate, id = ID_TIMER_ANIMATION_BAR_UPDATE )
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        self._flash_index_update_timer = wx.Timer( self, id = ID_TIMER_ANIMATION_BAR_UPDATE )
        
    
    def _GetXFromFrameIndex( self, index, width_offset = 0 ):
        
        if self._num_frames < 2:
            
            return 0
            
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        return int( float( my_width - width_offset ) * float( index ) / float( self._num_frames - 1 ) )
        
    
    def _Redraw( self, dc ):
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        dc.SetPen( wx.TRANSPARENT_PEN )
        
        background_colour = wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE )
        
        if self._paused:
            
            ( r, g, b ) = background_colour.Get()
            
            r = int( r * 0.85 )
            g = int( g * 0.85 )
            b = int( b * 0.85 )
            
            background_colour = wx.Colour( r, g, b )
            
        
        dc.SetBackground( wx.Brush( background_colour ) )
        
        dc.Clear()
        
        #
        
        if self._buffer_indices is not None:
            
            ( start_index, rendered_to_index, end_index ) = self._buffer_indices
            
            start_x = self._GetXFromFrameIndex( start_index )
            rendered_to_x = self._GetXFromFrameIndex( rendered_to_index )
            end_x = self._GetXFromFrameIndex( end_index )
            
            if start_x != rendered_to_x:
                
                ( r, g, b ) = background_colour.Get()
                
                r = int( r * 0.85 )
                g = int( g * 0.85 )
                
                rendered_colour = wx.Colour( r, g, b )
                
                dc.SetBrush( wx.Brush( rendered_colour ) )
                
                if rendered_to_x > start_x:
                    
                    dc.DrawRectangle( start_x, 0, rendered_to_x - start_x, ANIMATED_SCANBAR_HEIGHT )
                    
                else:
                    
                    dc.DrawRectangle( start_x, 0, my_width - start_x, ANIMATED_SCANBAR_HEIGHT )
                    
                    dc.DrawRectangle( 0, 0, rendered_to_x, ANIMATED_SCANBAR_HEIGHT )
                    
                
            
            if rendered_to_x != end_x:
                
                ( r, g, b ) = background_colour.Get()
                
                r = int( r * 0.93 )
                g = int( g * 0.93 )
                
                to_be_rendered_colour = wx.Colour( r, g, b )
                
                dc.SetBrush( wx.Brush( to_be_rendered_colour ) )
                
                if end_x > rendered_to_x:
                    
                    dc.DrawRectangle( rendered_to_x, 0, end_x - rendered_to_x, ANIMATED_SCANBAR_HEIGHT )
                    
                else:
                    
                    dc.DrawRectangle( rendered_to_x, 0, my_width - rendered_to_x, ANIMATED_SCANBAR_HEIGHT )
                    
                    dc.DrawRectangle( 0, 0, end_x, ANIMATED_SCANBAR_HEIGHT )
                    
                
            
        
        dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNSHADOW ) ) )
        
        caret_x = self._GetXFromFrameIndex( self._current_frame_index, width_offset = ANIMATED_SCANBAR_CARET_WIDTH )
        
        dc.DrawRectangle( caret_x, 0, ANIMATED_SCANBAR_CARET_WIDTH, ANIMATED_SCANBAR_HEIGHT )
        
        #
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        s = HydrusData.ConvertValueRangeToPrettyString( self._current_frame_index + 1, self._num_frames )
        
        ( x, y ) = dc.GetTextExtent( s )
        
        dc.DrawText( s, my_width - x - 3, 3 )
        
        self._dirty = False
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventMouse( self, event ):
        
        if self._media_window is not None:
            
            CC.CAN_HIDE_MOUSE = False
            
            if event.ButtonDown( wx.MOUSE_BTN_ANY ):
                
                self._has_experienced_mouse_down = True
                
            
            # sometimes, this can inherit mouse-down from previous filter or embed button reveal, resulting in undesired scan
            
            if not self._has_experienced_mouse_down:
                
                return
                
            
            ( my_width, my_height ) = self.GetClientSize()
            
            if event.Dragging():
                
                self._currently_in_a_drag = True
                
            
            if event.ButtonIsDown( wx.MOUSE_BTN_ANY ):
                
                if not self._currently_in_a_drag:
                    
                    self._it_was_playing = self._media_window.IsPlaying()
                    
                
                ( x, y ) = event.GetPosition()
                
                compensated_x_position = x - ( ANIMATED_SCANBAR_CARET_WIDTH / 2 )
                
                proportion = float( compensated_x_position ) / float( my_width - ANIMATED_SCANBAR_CARET_WIDTH )
                
                if proportion < 0: proportion = 0
                if proportion > 1: proportion = 1
                
                self._current_frame_index = int( proportion * ( self._num_frames - 1 ) + 0.5 )
                
                self._dirty = True
                
                self.Refresh()
                
                self._media_window.GotoFrame( self._current_frame_index )
                
            elif event.ButtonUp( wx.MOUSE_BTN_ANY ):
                
                if self._it_was_playing:
                    
                    self._media_window.Play()
                    
                
                self._currently_in_a_drag = False
                
            
        
    
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
                    
                    wx.CallAfter( self._canvas_bmp.Destroy )
                    
                
                self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
                
                self._dirty = True
                
                self.Refresh()
                
            
        
    
    def GotoFrame( self, frame_index ):
        
        self._current_frame_index = frame_index
        
        self._dirty = True
        
        self.Refresh()
        
    
    def SetBufferIndices( self, buffer_indices ):
        
        if buffer_indices != self._buffer_indices:
            
            self._buffer_indices = buffer_indices
            
            self._dirty = True
            
            self.Refresh()
            
        
    
    def SetMediaAndWindow( self, media, media_window ):
        
        self._media_window = media_window
        self._paused = False
        self._num_frames = max( media.GetNumFrames(), 1 )
        self._current_frame_index = 0
        self._buffer_indices = None
        
        self._has_experienced_mouse_down = False
        self._currently_in_a_drag = False
        self._it_was_playing = False
        
        if media.GetMime() == HC.APPLICATION_FLASH:
            
            self._flash_index_update_timer.Start( 100, wx.TIMER_CONTINUOUS )
            
        else:
            
            self._flash_index_update_timer.Stop()
            
        
        self._dirty = True
        
    
    def SetNoneMedia( self ):
        
        self._media_window = None
        
        self._flash_index_update_timer.Stop()
        
    
    def SetPaused( self, paused ):
        
        self._paused = paused
        
        self._dirty = True
        
        self.Refresh()
        
    
    def TIMERFlashIndexUpdate( self, event ):
        
        try:
            
            if self.IsShownOnScreen():
                
                try:
                    
                    frame_index = self._media_window.CurrentFrame()
                    
                except AttributeError:
                    
                    text = 'The flash window produced an unusual error that probably means it never initialised properly. This is usually because Flash has not been installed for Internet Explorer. '
                    text += os.linesep * 2
                    text += 'Please close the client, open Internet Explorer, and install flash from Adobe\'s site and then try again. If that does not work, please tell the hydrus developer.'
                    
                    HydrusData.ShowText( text )
                    
                    raise
                    
                
                if frame_index != self._current_frame_index:
                    
                    self._current_frame_index = frame_index
                    
                    self._dirty = True
                    
                    self.Refresh()
                    
                
            
        except wx.PyDeadObjectError:
            
            self._flash_index_update_timer.Stop()
            
        except:
            
            self._flash_index_update_timer.Stop()
            
            raise
            
        
    
class Canvas( wx.Window ):
    
    BORDER = wx.SIMPLE_BORDER
    PREVIEW_WINDOW = False
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent, style = self.BORDER )
        
        self._file_service_key = CC.LOCAL_FILE_SERVICE_KEY
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self._canvas_key = HydrusData.GenerateKey()
        
        self._dirty = True
        self._closing = False
        
        self._service_keys_to_services = {}
        
        self._current_media = None
        self._media_container = MediaContainer( self )
        self._current_zoom = 1.0
        self._canvas_zoom = 1.0
        
        self._last_drag_coordinates = None
        self._last_motion_coordinates = ( 0, 0 )
        self._total_drag_delta = ( 0, 0 )
        
        self.SetBackgroundColour( wx.Colour( *HC.options[ 'gui_colours' ][ 'media_background' ] ) )
        
        self._canvas_bmp = wx.EmptyBitmap( 20, 20, 24 )
        
        self.Bind( wx.EVT_SIZE, self.EventResize )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        HydrusGlobals.client_controller.sub( self, 'ZoomIn', 'canvas_zoom_in' )
        HydrusGlobals.client_controller.sub( self, 'ZoomOut', 'canvas_zoom_out' )
        HydrusGlobals.client_controller.sub( self, 'ZoomSwitch', 'canvas_zoom_switch' )
        HydrusGlobals.client_controller.sub( self, 'OpenExternally', 'canvas_open_externally' )
        HydrusGlobals.client_controller.sub( self, 'ManageTags', 'canvas_manage_tags' )
        
    
    def _Archive( self ):
        
        HydrusGlobals.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( self._current_media.GetHash(), ) ) ] } )
        
    
    def _CopyBMPToClipboard( self ):
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'bmp', self._current_media )
        
    
    def _CopyHashToClipboard( self, hash_type ):
        
        sha256_hash = self._current_media.GetHash()
        
        if hash_type == 'sha256':
            
            hex_hash = sha256_hash.encode( 'hex' )
            
        else:
            
            if self._current_media.GetLocationsManager().IsLocal():
                
                ( other_hash, ) = HydrusGlobals.client_controller.Read( 'file_hashes', ( sha256_hash, ), 'sha256', hash_type )
                
                hex_hash = other_hash.encode( 'hex' )
                
            else:
                
                wx.MessageBox( 'Unfortunately, you do not have that file in your database, so its non-sha256 hashes are unknown.' )
                
                return
                
            
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', hex_hash )
        
    
    def _CopyFileToClipboard( self ):
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        paths = [ client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() ) ]
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'paths', paths )
        
    
    def _CopyPathToClipboard( self ):
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        path = client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() )
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', path )
        
    
    def _Delete( self, service_key = None ):
        
        do_it = False
        
        if service_key is None:
            
            locations_manager = self._current_media.GetLocationsManager()
            
            if CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent():
                
                service_key = CC.LOCAL_FILE_SERVICE_KEY
                
            elif CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
                
                service_key = CC.TRASH_SERVICE_KEY
                
            else:
                
                return
                
            
        
        if service_key == CC.LOCAL_FILE_SERVICE_KEY:
            
            if not HC.options[ 'confirm_trash' ]:
                
                do_it = True
                
            
            text = 'Send this file to the trash?'
            
        elif service_key == CC.TRASH_SERVICE_KEY:
            
            text = 'Permanently delete this file?'
            
        
        if not do_it:
            
            with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    do_it = True
                    
                
            
            self.SetFocus() # annoying bug because of the modal dialog
            
        
        if do_it:
            
            hashes = { self._current_media.GetHash() }
            
            HydrusGlobals.client_controller.Write( 'content_updates', { service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes ) ] } )
            
        
    
    def _DrawBackgroundBitmap( self, dc ):
        
        dc.SetBackground( wx.Brush( wx.Colour( *HC.options[ 'gui_colours' ][ 'media_background' ] ) ) )
        
        dc.Clear()
        
        self._DrawBackgroundDetails( dc )
        
        self._dirty = False
        
    
    def _DrawBackgroundDetails( self, dc ): pass
    
    def _DrawCurrentMedia( self ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if my_width > 0 and my_height > 0:
            
            if self._current_media is not None:
                
                self._SizeAndPositionMediaContainer()
                
            
        
    
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
        
        x_offset = ( my_width - media_width ) / 2 + drag_x
        y_offset = ( my_height - media_height ) / 2 + drag_y
        
        new_size = ( media_width, media_height )
        new_position = ( x_offset, y_offset )
        
        return ( new_size, new_position )
        
    
    def _HydrusShouldNotProcessInput( self ):
        
        if HydrusGlobals.client_controller.MenuIsOpen():
            
            return True
            
        
        if HydrusGlobals.do_not_catch_char_hook:
            
            HydrusGlobals.do_not_catch_char_hook = False
            
            return True
            
        
        if self._current_media is not None and self._current_media.GetMime() == HC.APPLICATION_FLASH:
            
            if self.MouseIsOverMedia():
                
                return True
                
            
        
        return False
        
    
    def _Inbox( self ):
        
        HydrusGlobals.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, ( self._current_media.GetHash(), ) ) ] } )
        
    
    def _IsZoomable( self ):
        
        return self._GetShowAction( self._current_media ) not in ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW )
        
    
    def _ManageRatings( self ):
    
        if len( HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.RATINGS_SERVICES ) ) > 0:
            
            if self._current_media is not None:
                
                with ClientGUIDialogsManage.DialogManageRatings( self, ( self._current_media, ) ) as dlg: dlg.ShowModal()
                
            
        
    
    def _ManageTags( self ):
        
        if self._current_media is not None:
            
            # take any focus away from hover window, which will mess up window order when it hides due to the new frame
            self.SetFocus()
            
            title = 'manage tags'
            frame_key = 'manage_tags_frame'
            
            manage_tags = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
            
            panel = ClientGUIScrolledPanelsManagement.ManageTagsPanel( manage_tags, self._file_service_key, ( self._current_media, ), immediate_commit = True, canvas_key = self._canvas_key )
            
            manage_tags.SetPanel( panel )
            
        
    
    def _OpenExternally( self ):
        
        if self._current_media is not None:
            
            hash = self._current_media.GetHash()
            mime = self._current_media.GetMime()
            
            client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
            
            path = client_files_manager.GetFilePath( hash, mime )
            
            HydrusPaths.LaunchFile( path )
            
            if self._current_media.HasDuration() and mime != HC.APPLICATION_FLASH:
                
                self._media_container.Pause()
                
            
        
    
    def _PrefetchNeighbours( self ):
        
        pass
        
    
    def _ReinitZoom( self ):
        
        show_action = self._GetShowAction( self._current_media )
        
        ( self._current_zoom, self._canvas_zoom ) = CalculateCanvasZooms( self, self._current_media, show_action )
        
        HydrusGlobals.client_controller.pub( 'canvas_new_zoom', self._canvas_key, self._current_zoom )
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
        self.Refresh()
        
    
    def _SetZoom( self, new_zoom ):

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
        
        HydrusGlobals.client_controller.pub( 'canvas_new_zoom', self._canvas_key, self._current_zoom )
        
        self._SetDirty()
        
    
    def _SizeAndPositionMediaContainer( self ):
        
        ( new_size, new_position ) = self._GetMediaContainerSizeAndPosition()
        
        if new_size != self._media_container.GetSize(): self._media_container.SetSize( new_size )
        
        if HC.PLATFORM_OSX and new_position == self._media_container.GetPosition(): self._media_container.Refresh()
        
        if new_position != self._media_container.GetPosition(): self._media_container.SetPosition( new_position )
        
    
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
                
                HydrusGlobals.client_controller.Write( 'content_updates', { CC.TRASH_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, ( self._current_media.GetHash(), ) ) ] } )
                
            
            self.SetFocus() # annoying bug because of the modal dialog
            
        
    
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
                
                self._SetZoom( new_zoom )
                
            
        
    
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
                
                self._SetZoom( new_zoom )
                
            
        
    
    def _ZoomSwitch( self ):
        
        if self._current_media is not None and self._IsZoomable() and self._canvas_zoom != 1.0:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            ( media_width, media_height ) = self._current_media.GetResolution()
            
            if self._current_zoom == 1.0:
                
                new_zoom = self._canvas_zoom
                
            else:
                
                new_zoom = 1.0
                
            
            if new_zoom <= self._canvas_zoom:
                
                self._total_drag_delta = ( 0, 0 )
                
            
            self._SetZoom( new_zoom )
            
        
    
    def BeginDrag( self, pos = None ):
        
        if pos is None:
            
            ( x, y ) = self.ScreenToClient( wx.GetMousePosition() )
            
        else:
            
            ( x, y ) = pos
            
        
        self._last_drag_coordinates = ( x, y )
        
        
    
    def EventEraseBackground( self, event ): pass
    
    def EventPaint( self, event ):
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if self._dirty:
            
            self._DrawBackgroundBitmap( dc )
            
            if self._current_media is not None:
                
                self._DrawCurrentMedia()
                
            
        
    
    def EventResize( self, event ):
        
        if not self._closing:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            self._canvas_bmp.Destroy()
            
            self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
            
            if self._current_media is not None:
                
                ( media_width, media_height ) = self._media_container.GetClientSize()
                
                if my_width != media_width or my_height != media_height:
                    
                    self._ReinitZoom()
                    
                
            
            self._SetDirty()
            
        
        event.Skip()
        
    
    def KeepCursorAlive( self ): pass
    
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
            
        
    
    def SetMedia( self, media ):
        
        if media is not None:
            
            locations_manager = media.GetLocationsManager()
            
            if not locations_manager.IsLocal():
                
                media = None
                
            elif self._GetShowAction( media.GetDisplayMedia() ) in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
                
                media = None
                
            
        
        if media != self._current_media:
            
            HydrusGlobals.client_controller.ResetIdleTimer()
            
            self._current_media = media
            self._total_drag_delta = ( 0, 0 )
            self._last_drag_coordinates = None
            
            if self._current_media is None:
                
                self._media_container.SetNoneMedia()
                
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
                    
                
            
            HydrusGlobals.client_controller.pub( 'canvas_new_display_media', self._canvas_key, self._current_media )
            
            HydrusGlobals.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
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
        
        HydrusGlobals.client_controller.sub( self, 'FocusChanged', 'focus_changed' )
        HydrusGlobals.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def EventMenu( self, event ):
        
        # is None bit means this is prob from a keydown->menu event
        if event.GetEventObject() is None and self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
            
            if action is not None:
                
                ( command, data ) = action
                
                if command == 'archive': self._Archive()
                elif command == 'copy_bmp': self._CopyBMPToClipboard()
                elif command == 'copy_files': self._CopyFileToClipboard()
                elif command == 'copy_hash': self._CopyHashToClipboard( data )
                elif command == 'copy_path': self._CopyPathToClipboard()
                elif command == 'delete': self._Delete( data )
                elif command == 'inbox': self._Inbox()
                elif command == 'manage_ratings': self._ManageRatings()
                elif command == 'manage_tags': wx.CallAfter( self._ManageTags )
                elif command == 'open_externally': self._OpenExternally()
                elif command == 'undelete': self._Undelete()
                else: event.Skip()
                
            
        
    
    def EventShowMenu( self, event ):
        
        if self._current_media is not None:
            
            services = HydrusGlobals.client_controller.GetServicesManager().GetServices()
            
            locations_manager = self._current_media.GetLocationsManager()
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            menu = wx.Menu()
            
            for line in self._current_media.GetPrettyInfoLines():
                
                ClientGUIMenus.AppendMenuLabel( menu, line, line )
                
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if i_can_post_ratings:
                
                manage_menu = wx.Menu()
                
                ClientGUIMenus.AppendMenuItem( self, manage_menu, 'tags', 'Manage tags for the selected files.', self._ManageTags )
                ClientGUIMenus.AppendMenuItem( self, manage_menu, 'ratings', 'Manage ratings for the selected files.', self._ManageRatings )
                
                ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
                
            else:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'manage tags', 'Manage tags for the selected files.', self._ManageTags )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._current_media.HasInbox():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'archive', 'Archive the selected files.', self._Archive )
                
            
            if self._current_media.HasArchive():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'inbox', 'Send the selected files back to the inbox.', self._Inbox )
                
            
            if CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'delete', 'Delete the selected files.', self._Delete, CC.LOCAL_FILE_SERVICE_KEY )
                
            elif CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'delete completely', 'Physically delete the selected files from disk.', self._Delete, CC.TRASH_SERVICE_KEY )
                ClientGUIMenus.AppendMenuItem( self, menu, 'undelete', 'Take the selected files out of the trash.', self._Undelete )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'open externally', 'Open the file in your OS\'s default program.', self._OpenExternally )
            
            share_menu = wx.Menu()
            
            copy_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, copy_menu, 'file', 'Copy the file to your clipboard.', self._CopyFileToClipboard )
            
            copy_hash_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha256 (hydrus default)', 'Open the file\'s SHA256 hash.', self._CopyHashToClipboard, 'sha256' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'md5', 'Open the file\'s MD5 hash.', self._CopyHashToClipboard, 'md5' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha1', 'Open the file\'s SHA1 hash.', self._CopyHashToClipboard, 'sha1' )
            ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha512', 'Open the file\'s SHA512 hash.', self._CopyHashToClipboard, 'sha512' )
            
            ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
            
            if self._current_media.GetMime() in HC.IMAGES and self._current_media.GetDuration() is None:
                
                ClientGUIMenus.AppendMenuItem( self, copy_menu, 'image', 'Copy the file to your clipboard as a bmp.', self._CopyBMPToClipboard )
                
            
            ClientGUIMenus.AppendMenuItem( self, copy_menu, 'path', 'Copy the file\'s path to your clipboard.', self._CopyPathToClipboard )
            
            ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
            
            ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
            
            HydrusGlobals.client_controller.PopupMenu( self, menu )
            
            event.Skip()
            
        
    
    def FocusChanged( self, page_key, media ):
        
        if HC.options[ 'hide_preview' ]:
            
            return
            
        
        if page_key == self._page_key:
            
            self.SetMedia( media )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._SetDirty()
                
            
        
    
class CanvasWithDetails( Canvas ):
    
    BORDER = wx.NO_BORDER
    
    def _DrawBackgroundDetails( self, dc ):
        
        if self._current_media is not None:
            
            ( client_width, client_height ) = self.GetClientSize()
            
            # tags on the top left
            
            dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
            
            tags_manager = self._current_media.GetDisplayMedia().GetTagsManager()
            
            current = tags_manager.GetCurrent()
            pending = tags_manager.GetPending()
            petitioned = tags_manager.GetPetitioned()
            
            tags_i_want_to_display = set()
            
            tags_i_want_to_display.update( current )
            tags_i_want_to_display.update( pending )
            tags_i_want_to_display.update( petitioned )
            
            tags_i_want_to_display = list( tags_i_want_to_display )
            
            ClientData.SortTagsList( tags_i_want_to_display, HC.options[ 'default_tag_sort' ] )
            
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
                
            
            dc.SetTextForeground( wx.Colour( *HC.options[ 'gui_colours' ][ 'media_text' ] ) )
            
            # top right
            
            current_y = 2
            
            # icons
            
            icons_to_show = []
            
            if CC.TRASH_SERVICE_KEY in self._current_media.GetLocationsManager().GetCurrent():
                
                icons_to_show.append( CC.GlobalBMPs.trash )
                
            
            if self._current_media.HasInbox():
                
                icons_to_show.append( CC.GlobalBMPs.inbox )
                
            
            if len( icons_to_show ) > 0:
                
                icon_x = 0
                
                for icon in icons_to_show:
                    
                    dc.DrawBitmap( icon, client_width + icon_x - 18, 2 )
                    
                    icon_x -= 18
                    
                
                current_y += 18
                
            
            # repo strings
            
            remote_strings = self._current_media.GetLocationsManager().GetRemoteLocationStrings()
            
            for remote_string in remote_strings:
                
                ( text_width, text_height ) = dc.GetTextExtent( remote_string )
                
                dc.DrawText( remote_string, client_width - text_width - 3, current_y )
                
                current_y += text_height + 4
                
            
            # ratings
            
            services_manager = HydrusGlobals.client_controller.GetServicesManager()
            
            like_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ), randomised = False )
            
            like_services.reverse()
            
            like_rating_current_x = client_width - 16
            
            for like_service in like_services:
                
                service_key = like_service.GetServiceKey()
                
                rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), service_key )
                
                ClientRatings.DrawLike( dc, like_rating_current_x, current_y, service_key, rating_state )
                
                like_rating_current_x -= 16
                
            
            if len( like_services ) > 0: current_y += 20
            
            numerical_services = services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ), randomised = False )
            
            for numerical_service in numerical_services:
                
                service_key = numerical_service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), service_key )
                
                numerical_width = ClientRatings.GetNumericalWidth( service_key )
                
                ClientRatings.DrawNumerical( dc, client_width - numerical_width, current_y, service_key, rating_state, rating )
                
                current_y += 20
                
            
            # middle
            
            current_y = 3
            
            title_string = self._current_media.GetTitleString()
            
            if len( title_string ) > 0:
                
                ( x, y ) = dc.GetTextExtent( title_string )
                
                dc.DrawText( title_string, ( client_width - x ) / 2, current_y )
                
                current_y += y + 3
                
            
            info_string = self._GetInfoString()
            
            ( x, y ) = dc.GetTextExtent( info_string )
            
            dc.DrawText( info_string, ( client_width - x ) / 2, current_y )
            
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
        
    
class CanvasFrame( ClientGUITopLevelWindows.FrameThatResizes ):
    
    def __init__( self, parent ):
        
        if HC.PLATFORM_OSX:
            
            float_on_parent = True
            
        else:
            
            float_on_parent = False
            
        
        ClientGUITopLevelWindows.FrameThatResizes.__init__( self, parent, 'hydrus client media viewer', 'media_viewer', float_on_parent = float_on_parent )
        
    
    def Close( self ):
        
        if HC.PLATFORM_OSX and self.IsFullScreen():
            
            self.ShowFullScreen( False, wx.FULLSCREEN_ALL )
            
        
        self.Destroy()
        
    
    def FullscreenSwitch( self ):
        
        if self.IsFullScreen():
            
            self.ShowFullScreen( False, wx.FULLSCREEN_ALL )
            
        else:
            
            self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
            
        
    
    def SetCanvas( self, canvas_window ):
        
        self._canvas_window = canvas_window
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._canvas_window, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        ClientGUITopLevelWindows.SetTLWSizeAndPosition( self, self._frame_key )
        
        self.Show( True )
        
        wx.GetApp().SetTopWindow( self )
        
        self.Bind( wx.EVT_CLOSE, self._canvas_window.EventClose )
        
    
class CanvasWithHovers( CanvasWithDetails ):
    
    def __init__( self, parent ):
        
        CanvasWithDetails.__init__( self, parent )
        
        self._hover_commands = self._GenerateHoverTopFrame()
        self._hover_tags = ClientGUIHoverFrames.FullscreenHoverFrameTags( self, self._canvas_key )
        
        ratings_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.RATINGS_SERVICES ) )
        
        if len( ratings_services ) > 0:
            
            self._hover_ratings = ClientGUIHoverFrames.FullscreenHoverFrameRatings( self, self._canvas_key )
            
        
    
    def _GenerateHoverTopFrame( self ):
        
        raise NotImplementedError()
        
    
class CanvasFilterDuplicates( CanvasWithHovers ):
    
    def __init__( self, parent, file_service_key ):
        
        CanvasWithHovers.__init__( self, parent )
        
        self._file_service_key = file_service_key
        
        self._media_list = ClientMedia.ListeningMediaList( self._file_service_key, [] )
        
        self._hover_commands.AddCommand( 'this is better', self._CurrentMediaIsBetter )
        self._hover_commands.AddCommand( 'exact duplicates', self._MediaAreTheSame )
        self._hover_commands.AddCommand( 'alternates', self._MediaAreAlternates )
        self._hover_commands.AddCommand( 'custom action', self._DoCustomAction )
        
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        # add support for 'f' to borderless
        # add support for F4 and other general shortcuts so people can do edits before processing
        
        wx.CallAfter( self._ShowNewPair ) # don't set this until we have a size > (20, 20)!
        
        HydrusGlobals.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HydrusGlobals.client_controller.sub( self, 'SwitchMedia', 'canvas_show_next' )
        HydrusGlobals.client_controller.sub( self, 'SwitchMedia', 'canvas_show_previous' )
        HydrusGlobals.client_controller.sub( self, 'ShowNewPair', 'canvas_show_new_pair' )
        
    
    def _Close( self ):
        
        self._closing = True
        
        self.GetParent().Close()
        
    
    def _CurrentMediaIsBetter( self ):
        
        pass
        
        self._ShowNewPair()
        
    
    def _DoCustomAction( self ):
        
        pass
        
        # launch the dialog to choose exactly what happens
        # if OK on that:
        self._ShowNewPair()
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUIHoverFrames.FullscreenHoverFrameTopDuplicatesFilter( self, self._canvas_key )
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None:
            
            return '-'
            
        else:
            
            if self._media_list.GetFirst() == self._current_media:
                
                return 'A'
                
            else:
                
                return 'B'
                
            
        
    
    def _MediaAreAlternates( self ):
        
        pass
        
        self._ShowNewPair()
        
    
    def _MediaAreTheSame( self ):
        
        pass
        
        self._ShowNewPair()
        
    
    def _ShowNewPair( self ):
        
        result = HydrusGlobals.client_controller.Read( 'duplicate_pair', self._file_service_key, HC.DUPLICATE_UNKNOWN )
        
        if result is None:
            
            self._Close()
            
        else:
            
            media_results = result
            
            self._media_list = ClientMedia.ListeningMediaList( self._file_service_key, media_results )
            
            self.SetMedia( self._media_list.GetFirst() )
            
        
    
    def _SwitchMedia( self ):
        
        if self._current_media is not None:
            
            self.SetMedia( self._media_list.GetNext( self._current_media ) )
            
        
    
    def EventCharHook( self, event ):
        
        ( modifier, key ) = ClientData.GetShortcutFromEvent( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ):
            
            self._Close()
            
        
    
    def EventClose( self, event ):
        
        self._Close()
        
    
    def EventMouseWheel( self, event ):
        
        if self._HydrusShouldNotProcessInput():
            
            event.Skip()
            
        else:
            
            self._SwitchMedia()
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        def catch_up():
            
            # ugly, but it will do for now
            
            if len( self._media_list ) < 2:
                
                self._ShowNewPair()
                
            else:
                
                self._SetDirty()
                
            
        
        
        wx.CallLater( 100, catch_up )
        
    
    def ShowNewPair( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowNewPair()
            
        
    
    def SwitchMedia( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._SwitchMedia()
            
        
    
class CanvasMediaList( ClientMedia.ListeningMediaList, CanvasWithHovers ):
    
    def __init__( self, parent, page_key, media_results ):
        
        CanvasWithHovers.__init__( self, parent )
        ClientMedia.ListeningMediaList.__init__( self, CC.LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._page_key = page_key
        
        self._just_started = True
        
        self._timer_cursor_hide = wx.Timer( self, id = ID_TIMER_CURSOR_HIDE )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventCursorHide, id = ID_TIMER_CURSOR_HIDE )
        
        self.Bind( wx.EVT_MOTION, self.EventDrag )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
        self.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
        
        HydrusGlobals.client_controller.pub( 'set_focus', self._page_key, None )
        
        HydrusGlobals.client_controller.sub( self, 'Close', 'canvas_close' )
        HydrusGlobals.client_controller.sub( self, 'FullscreenSwitch', 'canvas_fullscreen_switch' )
        
    
    def _Close( self ):
        
        self._closing = True
        
        HydrusGlobals.client_controller.pub( 'set_focus', self._page_key, self._current_media )
        
        self.GetParent().Close()
        
    
    def _DoManualPan( self, delta_x_step, delta_y_step ):
        
        ( my_x, my_y ) = self.GetClientSize()
        ( media_x, media_y ) = self._media_container.GetClientSize()
        
        x_pan_distance = min( my_x / 12, media_x / 12 )
        y_pan_distance = min( my_y / 12, media_y / 12 )
        
        delta_x = delta_x_step * x_pan_distance
        delta_y = delta_y_step * y_pan_distance
        
        ( old_delta_x, old_delta_y ) = self._total_drag_delta
        
        self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
        
        self._DrawCurrentMedia()
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None:
            
            index_string = '-/' + HydrusData.ConvertIntToPrettyString( len( self._sorted_media ) )
            
        else:
            
            index_string = HydrusData.ConvertValueRangeToPrettyString( self._sorted_media.index( self._current_media ) + 1, len( self._sorted_media ) )
            
        
        return index_string
        
    
    def _PrefetchNeighbours( self ):
        
        media_looked_at = set()
        
        to_render = []
        
        previous = self._current_media
        next = self._current_media
        
        if self._just_started:
            
            delay_base = 800
            
            num_to_go_back = 1
            num_to_go_forward = 1
            
            self._just_started = False
            
        else:
            
            delay_base = 400
            
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
            
        
        ( my_width, my_height ) = self.GetClientSize()
        
        image_cache = HydrusGlobals.client_controller.GetCache( 'images' )
        
        for ( media, delay ) in to_render:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            if mime in ( HC.IMAGE_JPEG, HC.IMAGE_PNG ):
                
                if not image_cache.HasImageRenderer( hash ):
                    
                    wx.CallLater( delay, image_cache.GetImageRenderer, media )
                    
                
            
        
    
    def _Remove( self ):
        
        next_media = self._GetNext( self._current_media )
        
        if next_media == self._current_media: next_media = None
        
        hashes = { self._current_media.GetHash() }
        
        HydrusGlobals.client_controller.pub( 'remove_media', self._page_key, hashes )
        
        singleton_media = { self._current_media }
        
        ClientMedia.ListeningMediaList._RemoveMedia( self, singleton_media, {} )
        
        if self.HasNoMedia():
            
            self._Close()
            
        elif self.HasMedia( self._current_media ):
            
            HydrusGlobals.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self._SetDirty()
            
        else:
            
            self.SetMedia( next_media )
            
        
    
    def _ShowFirst( self ): self.SetMedia( self._GetFirst() )
    
    def _ShowLast( self ): self.SetMedia( self._GetLast() )
    
    def _ShowNext( self ): self.SetMedia( self._GetNext( self._current_media ) )
    
    def _ShowPrevious( self ): self.SetMedia( self._GetPrevious( self._current_media ) )
    
    def _StartSlideshow( self, interval ): pass
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            ClientMedia.ListeningMediaList.AddMediaResults( self, media_results )
            
            HydrusGlobals.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self._SetDirty()
            
        
    
    def Close( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Close()
            
        
    
    def EventClose( self, event ):
        
        self._Close()
        
    
    def EventDrag( self, event ):
        
        CC.CAN_HIDE_MOUSE = True
        
        ( x, y ) = event.GetPosition()
        
        show_mouse = False
        
        if ( x, y ) != self._last_motion_coordinates:
            
            self._last_motion_coordinates = ( x, y )
            
            show_mouse = True
            
        
        if event.Dragging() and self._last_drag_coordinates is not None:
            
            ( old_x, old_y ) = self._last_drag_coordinates
            
            ( delta_x, delta_y ) = ( x - old_x, y - old_y )
            
            if HC.PLATFORM_WINDOWS:
                
                show_mouse = False
                
                self.WarpPointer( old_x, old_y )
                
            else:
                
                show_mouse = True
                
                self._last_drag_coordinates = ( x, y )
                
            
            ( old_delta_x, old_delta_y ) = self._total_drag_delta
            
            self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
            
            self._DrawCurrentMedia()
            
        
        if show_mouse:
            
            self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
            
            self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
            
        else:
            
            self.SetCursor( wx.StockCursor( wx.CURSOR_BLANK ) )
            
        
    
    def EventDragBegin( self, event ):
        
        ( x, y ) = event.GetPosition()
        
        self.BeginDrag( ( x, y ) )
        
        event.Skip()
        
    
    def EventDragEnd( self, event ):
        
        self._last_drag_coordinates = None
        
        event.Skip()
        
    
    def EventFullscreenSwitch( self, event ):
        
        self.GetParent().FullscreenSwitch()
        
    
    def FullscreenSwitch( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self.GetParent().FullscreenSwitch()
            
        
    
    def KeepCursorAlive( self ): self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self.HasMedia( self._current_media ):
            
            next_media = self._GetNext( self._current_media )
            
            if next_media == self._current_media: next_media = None
            
        else:
            
            next_media = None
            
        
        ClientMedia.ListeningMediaList.ProcessContentUpdates( self, service_keys_to_content_updates )
        
        if self.HasNoMedia():
            
            self._Close()
            
        elif self.HasMedia( self._current_media ):
            
            HydrusGlobals.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self._SetDirty()
            
        elif self.HasMedia( next_media ):
            
            self.SetMedia( next_media )
            
        else:
            
            self.SetMedia( self._GetFirst() )
            
        
    
    def TIMEREventCursorHide( self, event ):
        
        try:
            
            if not CC.CAN_HIDE_MOUSE:
                
                return
                
            
            if HydrusGlobals.client_controller.MenuIsOpen():
                
                self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
                
            else:
                
                self.SetCursor( wx.StockCursor( wx.CURSOR_BLANK ) )
                
            
        except wx.PyDeadObjectError:
            
            self._timer_cursor_hide.Stop()
            
        except:
            
            self._timer_cursor_hide.Stop()
            
            raise
            
        
    
class CanvasMediaListFilterInbox( CanvasMediaList ):
    
    def __init__( self, parent, page_key, media_results ):
        
        CanvasMediaList.__init__( self, parent, page_key, media_results )
        
        self._kept = set()
        self._deleted = set()
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventMouseKeep )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventMouseKeep )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventBack )
        self.Bind( wx.EVT_MIDDLE_DCLICK, self.EventBack )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventDelete )
        self.Bind( wx.EVT_RIGHT_DCLICK, self.EventDelete )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        HydrusGlobals.client_controller.sub( self, 'Keep', 'canvas_archive' )
        HydrusGlobals.client_controller.sub( self, 'Delete', 'canvas_delete' )
        HydrusGlobals.client_controller.sub( self, 'Skip', 'canvas_show_next' )
        HydrusGlobals.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        HydrusGlobals.client_controller.sub( self, 'Back', 'canvas_show_previous' )
        
        wx.CallAfter( self.SetMedia, self._GetFirst() ) # don't set this until we have a size > (20, 20)!
        
    
    def _Back( self ):
        
        if not self._HydrusShouldNotProcessInput():
            
            if self._current_media == self._GetFirst(): return
            else:
                
                self._ShowPrevious()
                
                self._kept.discard( self._current_media )
                self._deleted.discard( self._current_media )
                
            
        
    
    def _Close( self ):
        
        if not self._HydrusShouldNotProcessInput():
            
            if len( self._kept ) > 0 or len( self._deleted ) > 0:
                
                with ClientGUIDialogs.DialogFinishFiltering( self, len( self._kept ), len( self._deleted ) ) as dlg:
                    
                    modal = dlg.ShowModal()
                    
                    if modal == wx.ID_CANCEL:
                        
                        if self._current_media in self._kept: self._kept.remove( self._current_media )
                        if self._current_media in self._deleted: self._deleted.remove( self._current_media )
                        
                    else:
                        
                        if modal == wx.ID_YES:
                            
                            def process_in_thread( service_keys_and_content_updates ):
                                
                                for ( service_key, content_update ) in service_keys_and_content_updates:
                                    
                                    HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', { service_key : [ content_update ] } )
                                    
                                
                            
                            self._deleted_hashes = [ media.GetHash() for media in self._deleted ]
                            self._kept_hashes = [ media.GetHash() for media in self._kept ]
                            
                            service_keys_and_content_updates = []
                            
                            for chunk_of_hashes in HydrusData.SplitListIntoChunks( self._deleted_hashes, 64 ):
                                
                                service_keys_and_content_updates.append( ( CC.LOCAL_FILE_SERVICE_KEY, HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) ) )
                                
                            
                            service_keys_and_content_updates.append( ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, self._kept_hashes ) ) )
                            
                            HydrusGlobals.client_controller.CallToThread( process_in_thread, service_keys_and_content_updates )
                            
                            self._kept = set()
                            self._deleted = set()
                            
                            self._current_media = self._GetFirst() # so the pubsub on close is better
                            
                            if HC.options[ 'remove_filtered_files' ]:
                                
                                all_hashes = set()
                                
                                all_hashes.update( self._deleted_hashes )
                                all_hashes.update( self._kept_hashes )
                                
                                HydrusGlobals.client_controller.pub( 'remove_media', self._page_key, all_hashes )
                                
                            
                        
                        CanvasMediaList._Close( self )
                        
                    
                
            else:
                
                CanvasMediaList._Close( self )
                
            
        
    
    def _Delete( self ):
        
        self._deleted.add( self._current_media )
        
        if self._current_media == self._GetLast(): self._Close()
        else: self._ShowNext()
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUIHoverFrames.FullscreenHoverFrameTopInboxFilter( self, self._canvas_key )
        
    
    def _Keep( self ):
        
        self._kept.add( self._current_media )
        
        if self._current_media == self._GetLast(): self._Close()
        else: self._ShowNext()
        
    
    def _Skip( self ):
        
        if not self._HydrusShouldNotProcessInput():
            
            if self._current_media == self._GetLast(): self._Close()
            else: self._ShowNext()
            
        
    
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
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else:
        
            ( modifier, key ) = ClientData.GetShortcutFromEvent( event )
            
            if modifier == wx.ACCEL_NORMAL and key == wx.WXK_SPACE: self._Keep()
            elif modifier == wx.ACCEL_NORMAL and key in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
            elif modifier == wx.ACCEL_NORMAL and key in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
            elif modifier == wx.ACCEL_NORMAL and key == ord( 'Z' ): self._ZoomSwitch()
            elif modifier == wx.ACCEL_NORMAL and key == wx.WXK_BACK: self._Back()
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self._Close()
            elif modifier == wx.ACCEL_NORMAL and key in CC.DELETE_KEYS: self.EventDelete( event )
            elif modifier == wx.ACCEL_CTRL and key == ord( 'C' ): self._CopyFileToClipboard()
            elif not event.ShiftDown() and key in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ): self.EventSkip( event )
            else:
                
                key_dict = HC.options[ 'shortcuts' ][ modifier ]
                
                if key in key_dict:
                    
                    action = key_dict[ key ]
                    
                    self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( action ) ) )
                    
                else:
                    
                    event.Skip()
                    
                
            
        
    
    def EventDelete( self, event ):
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else: self._Delete()
        
    
    def EventMouseKeep( self, event ):
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            if event.ShiftDown(): self.EventDragBegin( event )
            else: self._Keep()
            
        
    
    def EventMenu( self, event ):
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
            
            if action is not None:
                
                ( command, data ) = action
                
                if command == 'archive': self._Keep()
                elif command == 'back': self._Back()
                elif command == 'close': self._Close()
                elif command == 'delete': self.EventDelete( event )
                elif command == 'fullscreen_switch': self.GetParent().FullscreenSwitch()
                elif command == 'filter': self._Close()
                elif command == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                elif command == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                elif command == 'manage_ratings': self._ManageRatings()
                elif command == 'manage_tags': wx.CallAfter( self._ManageTags )
                elif command in ( 'pan_up', 'pan_down', 'pan_left', 'pan_right' ):
                    
                    if command == 'pan_up': self._DoManualPan( 0, -1 )
                    elif command == 'pan_down': self._DoManualPan( 0, 1 )
                    elif command == 'pan_left': self._DoManualPan( -1, 0 )
                    elif command == 'pan_right': self._DoManualPan( 1, 0 )
                    
                elif command == 'zoom_in': self._ZoomIn()
                elif command == 'zoom_out': self._ZoomOut()
                else: event.Skip()
                
            
        
    
    def EventMouseWheel( self, event ):
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            if event.CmdDown():
                
                if event.GetWheelRotation() > 0: self._ZoomIn()
                else: self._ZoomOut()
                
            
        
    
    def EventSkip( self, event ):
        
        self._Skip()
        
    
    def EventUndelete( self, event ):
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else: self._Undelete()
        
    
    def Skip( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Skip()
            
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
class CanvasMediaListNavigable( CanvasMediaList ):
    
    def __init__( self, parent, page_key, media_results ):
        
        CanvasMediaList.__init__( self, parent, page_key, media_results )
        
        HydrusGlobals.client_controller.sub( self, 'Archive', 'canvas_archive' )
        HydrusGlobals.client_controller.sub( self, 'Delete', 'canvas_delete' )
        HydrusGlobals.client_controller.sub( self, 'Inbox', 'canvas_inbox' )
        HydrusGlobals.client_controller.sub( self, 'ShowFirst', 'canvas_show_first' )
        HydrusGlobals.client_controller.sub( self, 'ShowLast', 'canvas_show_last' )
        HydrusGlobals.client_controller.sub( self, 'ShowNext', 'canvas_show_next' )
        HydrusGlobals.client_controller.sub( self, 'ShowPrevious', 'canvas_show_previous' )
        HydrusGlobals.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUIHoverFrames.FullscreenHoverFrameTopNavigableList( self, self._canvas_key )
        
    
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
        
        self._timer_slideshow = wx.Timer( self, id = ID_TIMER_SLIDESHOW )
        self._timer_slideshow_interval = 0
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventSlideshow, id = ID_TIMER_SLIDESHOW )
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventClose )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventClose )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        if first_hash is None:
            
            first_media = self._GetFirst()
            
        else:
            
            try:
                
                first_media = self._GetMedia( { first_hash } )[0]
                
            except:
                
                first_media = self._GetFirst()
                
            
        
        wx.CallAfter( self.SetMedia, first_media ) # don't set this until we have a size > (20, 20)!
        
        HydrusGlobals.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        
    
    def _PausePlaySlideshow( self ):
        
        if self._timer_slideshow.IsRunning():
            
            self._timer_slideshow.Stop()
            
        elif self._timer_slideshow.GetInterval() > 0:
            
            self._timer_slideshow.Start()
            
        
    
    def _StartSlideshow( self, interval = None ):
        
        self._timer_slideshow.Stop()
        
        if interval is None:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter the interval, in seconds.', default = '15' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    try:
                        
                        interval = int( float( dlg.GetValue() ) * 1000 )
                        
                    except:
                        
                        return
                        
                    
                
            
        
        if interval > 0:
            
            self._timer_slideshow_interval = interval
            
            self._timer_slideshow.Start( self._timer_slideshow_interval, wx.TIMER_CONTINUOUS )
            
        
    
    def EventCharHook( self, event ):
        
        if self._HydrusShouldNotProcessInput():
            
            event.Skip()
            
        else:
            
            ( modifier, key ) = ClientData.GetShortcutFromEvent( event )
            
            if modifier == wx.ACCEL_NORMAL and key in CC.DELETE_KEYS: self._Delete()
            elif modifier == wx.ACCEL_SHIFT and key in CC.DELETE_KEYS: self._Undelete()
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE ): wx.CallAfter( self._PausePlaySlideshow )
            elif modifier == wx.ACCEL_NORMAL and key in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
            elif modifier == wx.ACCEL_NORMAL and key in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
            elif modifier == wx.ACCEL_NORMAL and key == ord( 'Z' ): self._ZoomSwitch()
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self._Close()
            elif modifier == wx.ACCEL_CTRL and key == ord( 'C' ): self._CopyFileToClipboard()
            else:
                
                key_dict = HC.options[ 'shortcuts' ][ modifier ]
                
                if key in key_dict:
                    
                    action = key_dict[ key ]
                    
                    self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( action ) ) )
                    
                else:
                    
                    event.Skip()
                    
                
            
        
    
    def EventMenu( self, event ):
        
        # is None bit means this is prob from a keydown->menu event
        if event.GetEventObject() is None and self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
            
            if action is not None:
                
                ( command, data ) = action
                
                if command == 'archive': self._Archive()
                elif command == 'copy_bmp': self._CopyBMPToClipboard()
                elif command == 'copy_files': self._CopyFileToClipboard()
                elif command == 'copy_hash': self._CopyHashToClipboard( data )
                elif command == 'copy_path': self._CopyPathToClipboard()
                elif command == 'delete': self._Delete( data )
                elif command == 'fullscreen_switch': self.GetParent().FullscreenSwitch()
                elif command == 'first': self._ShowFirst()
                elif command == 'last': self._ShowLast()
                elif command == 'previous': self._ShowPrevious()
                elif command == 'next': self._ShowNext()
                elif command == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                elif command == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                elif command == 'inbox': self._Inbox()
                elif command == 'manage_ratings': self._ManageRatings()
                elif command == 'manage_tags': wx.CallLater( 1, self._ManageTags )
                elif command == 'open_externally': self._OpenExternally()
                elif command in ( 'pan_up', 'pan_down', 'pan_left', 'pan_right' ):
                    
                    if command == 'pan_up': self._DoManualPan( 0, -1 )
                    elif command == 'pan_down': self._DoManualPan( 0, 1 )
                    elif command == 'pan_left': self._DoManualPan( -1, 0 )
                    elif command == 'pan_right': self._DoManualPan( 1, 0 )
                    
                elif command == 'remove': self._Remove()
                elif command == 'slideshow': wx.CallLater( 1, self._StartSlideshow, data )
                elif command == 'slideshow_pause_play': wx.CallLater( 1, self._PausePlaySlideshow )
                elif command == 'undelete': self._Undelete()
                elif command == 'zoom_in': self._ZoomIn()
                elif command == 'zoom_out': self._ZoomOut()
                elif command == 'zoom_switch': self._ZoomSwitch()
                else: event.Skip()
                
            
        
    
    def EventMouseWheel( self, event ):
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            if event.CmdDown():
                
                if event.GetWheelRotation() > 0: self._ZoomIn()
                else: self._ZoomOut()
                
            else:
                
                if event.GetWheelRotation() > 0: self._ShowPrevious()
                else: self._ShowNext()
                
            
        
    
    def EventShowMenu( self, event ):
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices()
        
        local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
        
        i_can_post_ratings = len( local_ratings_services ) > 0
        
        self._last_drag_coordinates = None # to stop successive right-click drag warp bug
        
        locations_manager = self._current_media.GetLocationsManager()
        
        menu = wx.Menu()
        
        for line in self._current_media.GetPrettyInfoLines():
            
            menu.Append( CC.ID_NULL, line )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if self._IsZoomable():
            
            menu.Append( CC.ID_NULL, 'current zoom: ' + ClientData.ConvertZoomToPercentage( self._current_zoom ) )
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'zoom_in' ), 'zoom in' )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'zoom_out' ), 'zoom out' )
            
            if self._current_media.GetMime() != HC.APPLICATION_FLASH:
                
                ( my_width, my_height ) = self.GetClientSize()
                
                ( media_width, media_height ) = self._current_media.GetResolution()
                
                if self._current_zoom == 1.0:
                    
                    if media_width > my_width or media_height > my_height:
                        
                        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'zoom_switch' ), 'zoom fit' )
                        
                    
                else:
                    
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'zoom_switch' ), 'zoom full' )
                    
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        if i_can_post_ratings:
            
            manage_menu = wx.Menu()
            
            manage_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'manage_tags' ), 'tags' )
            manage_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'manage_ratings' ), 'ratings' )
            
            menu.AppendMenu( CC.ID_NULL, 'manage', manage_menu )
            
        else:
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'manage_tags' ), 'manage tags' )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if self._current_media.HasInbox(): menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'archive' ), '&archive' )
        if self._current_media.HasArchive(): menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'inbox' ), 'return to &inbox' )
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'remove' ), '&remove' )
        
        if CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent():
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'delete', CC.LOCAL_FILE_SERVICE_KEY ), '&delete' )
            
        elif CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'delete', CC.TRASH_SERVICE_KEY ), '&delete from trash now' )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'undelete' ), '&undelete' )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'open_externally' ), '&open externally' )
        
        share_menu = wx.Menu()
        
        copy_menu = wx.Menu()
        
        copy_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_files' ), 'file' )
        
        copy_hash_menu = wx.Menu()
        
        copy_hash_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_hash', 'sha256' ) , 'sha256 (hydrus default)' )
        copy_hash_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_hash', 'md5' ) , 'md5' )
        copy_hash_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_hash', 'sha1' ) , 'sha1' )
        copy_hash_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_hash', 'sha512' ) , 'sha512' )
        
        copy_menu.AppendMenu( CC.ID_NULL, 'hash', copy_hash_menu )
        
        if self._current_media.GetMime() in HC.IMAGES and self._current_media.GetDuration() is None:
            
            copy_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_bmp' ), 'image' )
            
        
        copy_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_path' ), 'path' )
        
        share_menu.AppendMenu( CC.ID_NULL, 'copy', copy_menu )
        
        menu.AppendMenu( CC.ID_NULL, 'share', share_menu )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        slideshow = wx.Menu()
        
        slideshow.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'slideshow', 1000 ), '1 second' )
        slideshow.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'slideshow', 5000 ), '5 seconds' )
        slideshow.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'slideshow', 10000 ), '10 seconds' )
        slideshow.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'slideshow', 30000 ), '30 seconds' )
        slideshow.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'slideshow', 60000 ), '60 seconds' )
        slideshow.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'slideshow', 80 ), 'william gibson' )
        slideshow.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'slideshow' ), 'custom interval' )
        
        menu.AppendMenu( CC.ID_NULL, 'start slideshow', slideshow )
        
        if self._timer_slideshow.IsRunning():
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'slideshow_pause_play' ), 'stop slideshow' )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if self.GetParent().IsFullScreen():
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'fullscreen_switch' ), 'exit fullscreen' )
            
        else:
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'fullscreen_switch' ), 'go fullscreen' )
            
        
        HydrusGlobals.client_controller.PopupMenu( self, menu )
        
        event.Skip()
        
    
    def TIMEREventSlideshow( self, event ):
        
        try:
            
            if self._current_media is not None:
                
                if self._media_container.ReadyToSlideshow() and not HydrusGlobals.client_controller.MenuIsOpen():
                    
                    self._ShowNext()
                    
                    self._timer_slideshow.Start( self._timer_slideshow_interval, wx.TIMER_CONTINUOUS )
                    
                else:
                    
                    self._timer_slideshow.Start( 1000, wx.TIMER_CONTINUOUS )
                    
                
            
        except wx.PyDeadObjectError:
            
            self._timer_slideshow.Stop()
            
        except:
            
            self._timer_slideshow.Stop()
            
            raise
            
        
    
class CanvasMediaListCustomFilter( CanvasMediaListNavigable ):
    
    def __init__( self, parent, page_key, media_results, shortcuts ):
        
        CanvasMediaListNavigable.__init__( self, parent, page_key, media_results )
        
        self._shortcuts = shortcuts
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventClose )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventClose )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        wx.CallAfter( self.SetMedia, self._GetFirst() ) # don't set this until we have a size > (20, 20)!
        
        self._hover_commands.AddCommand( 'edit shortcuts', self.EditShortcuts )
        
        HydrusGlobals.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        
    
    def _CopyPathToClipboard( self ):
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        path = client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() )
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', path )
        
    
    def _Inbox( self ):
        
        HydrusGlobals.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, ( self._current_media.GetHash(), ) ) ] } )
        
    
    def EditShortcuts( self ):
        
        with ClientGUIDialogs.DialogShortcuts( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._shortcuts = dlg.GetShortcuts()
                
            
        
    
    def EventCharHook( self, event ):
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            ( modifier, key ) = ClientData.GetShortcutFromEvent( event )
            
            action = self._shortcuts.GetKeyboardAction( modifier, key )
            
            if action is not None:
                
                ( service_key, data ) = action
                
                if service_key is None:
                    
                    if data == 'archive': self._Archive()
                    elif data == 'delete': self._Delete()
                    elif data == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                    elif data == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                    elif data == 'fullscreen_switch': self.GetParent().FullscreenSwitch()
                    elif data == 'inbox': self._Inbox()
                    elif data == 'manage_ratings': self._ManageRatings()
                    elif data == 'manage_tags': wx.CallLater( 1, self._ManageTags )
                    elif data in ( 'pan_up', 'pan_down', 'pan_left', 'pan_right' ):
                        
                        if data == 'pan_up': self._DoManualPan( 0, -1 )
                        elif data == 'pan_down': self._DoManualPan( 0, 1 )
                        elif data == 'pan_left': self._DoManualPan( -1, 0 )
                        elif data == 'pan_right': self._DoManualPan( 1, 0 )
                        
                    elif data == 'remove': self._Remove()
                    elif data == 'first': self._ShowFirst()
                    elif data == 'last': self._ShowLast()
                    elif data == 'previous': self._ShowPrevious()
                    elif data == 'next': self._ShowNext()
                    
                else:
                    
                    service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
                    
                    service_type = service.GetServiceType()
                    
                    hashes = ( self._current_media.GetHash(), )
                    
                    if service_type in HC.TAG_SERVICES:
                        
                        tag = data
                        
                        tags_manager = self._current_media.GetTagsManager()
                        
                        current = tags_manager.GetCurrent()
                        pending = tags_manager.GetPending()
                        petitioned = tags_manager.GetPetitioned()
                        
                        if service_type == HC.LOCAL_TAG:
                            
                            tags = [ tag ]
                            
                            if tag in current:
                                
                                content_update_action = HC.CONTENT_UPDATE_DELETE
                                
                            else:
                                
                                content_update_action = HC.CONTENT_UPDATE_ADD
                                
                                tag_parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                                
                                parents = tag_parents_manager.GetParents( service_key, tag )
                                
                                tags.extend( parents )
                                
                            
                            rows = [ ( tag, hashes ) for tag in tags ]
                            
                        else:
                            
                            if tag in current:
                                
                                if tag in petitioned:
                                    
                                    content_update_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                                    
                                    rows = [ ( tag, hashes ) ]
                                    
                                else:
                                    
                                    message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                                    
                                    with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                                        
                                        if dlg.ShowModal() == wx.ID_OK:
                                            
                                            content_update_action = HC.CONTENT_UPDATE_PETITION
                                            
                                            rows = [ ( dlg.GetValue(), tag, hashes ) ]
                                            
                                        else: return
                                        
                                    
                                
                            else:
                                
                                tags = [ tag ]
                                
                                if tag in pending: content_update_action = HC.CONTENT_UPDATE_RESCIND_PEND
                                else:
                                    
                                    content_update_action = HC.CONTENT_UPDATE_PEND
                                    
                                    tag_parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                                    
                                    parents = tag_parents_manager.GetParents( service_key, tag )
                                    
                                    tags.extend( parents )
                                    
                                
                                rows = [ ( tag, hashes ) for tag in tags ]
                                
                            
                        
                        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_update_action, row ) for row in rows ]
                        
                    elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                        
                        # maybe this needs to be more complicated, if action is, say, remove the rating?
                        # ratings needs a good look at anyway
                        
                        rating = data
                        
                        row = ( rating, hashes )
                        
                        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) ]
                        
                    
                    HydrusGlobals.client_controller.Write( 'content_updates', { service_key : content_updates } )
                    
                
            else:
                
                if modifier == wx.ACCEL_NORMAL and key in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
                elif modifier == wx.ACCEL_NORMAL and key in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
                elif modifier == wx.ACCEL_NORMAL and key == ord( 'Z' ): self._ZoomSwitch()
                elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self._Close()
                elif modifier == wx.ACCEL_CTRL and key == ord( 'C' ): self._CopyFileToClipboard()
                else:
                    
                    key_dict = HC.options[ 'shortcuts' ][ modifier ]
                    
                    if key in key_dict:
                        
                        action = key_dict[ key ]
                        
                        self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( action ) ) )
                        
                    else: event.Skip()
                    
                
            
        
    
    def EventMenu( self, event ):
        
        # is None bit means this is prob from a keydown->menu event
        if event.GetEventObject() is None and self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
            
            if action is not None:
                
                ( command, data ) = action
                
                if command == 'archive': self._Archive()
                elif command == 'copy_bmp': self._CopyBMPToClipboard()
                elif command == 'copy_files': self._CopyFileToClipboard()
                elif command == 'copy_hash': self._CopyHashToClipboard( data )
                elif command == 'copy_path': self._CopyPathToClipboard()
                elif command == 'delete': self._Delete( data )
                elif command == 'fullscreen_switch': self.GetParent().FullscreenSwitch()
                elif command == 'first': self._ShowFirst()
                elif command == 'last': self._ShowLast()
                elif command == 'previous': self._ShowPrevious()
                elif command == 'next': self._ShowNext()
                elif command == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                elif command == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                elif command == 'inbox': self._Inbox()
                elif command == 'manage_ratings': self._ManageRatings()
                elif command == 'manage_tags': wx.CallLater( 1, self._ManageTags )
                elif command == 'open_externally': self._OpenExternally()
                elif command == 'remove': self._Remove()
                elif command == 'undelete': self._Undelete()
                elif command == 'zoom_in': self._ZoomIn()
                elif command == 'zoom_out': self._ZoomOut()
                elif command == 'zoom_switch': self._ZoomSwitch()
                else: event.Skip()
                
            
        
    
    def EventMouseWheel( self, event ):
        
        if self._HydrusShouldNotProcessInput(): event.Skip()
        else:
            
            if event.CmdDown():
                
                if event.GetWheelRotation() > 0: self._ZoomIn()
                else: self._ZoomOut()
                
            else:
                
                if event.GetWheelRotation() > 0: self._ShowPrevious()
                else: self._ShowNext()
                
            
        
    
    def EventShowMenu( self, event ):
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices()
        
        local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
        
        i_can_post_ratings = len( local_ratings_services ) > 0
        
        locations_manager = self._current_media.GetLocationsManager()
        
        #
        
        self._last_drag_coordinates = None # to stop successive right-click drag warp bug
        
        menu = wx.Menu()
        
        for line in self._current_media.GetPrettyInfoLines():
            
            menu.Append( CC.ID_NULL, line )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if self._IsZoomable():
            
            menu.Append( CC.ID_NULL, 'current zoom: ' + ClientData.ConvertZoomToPercentage( self._current_zoom ) )
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'zoom_in' ), 'zoom in' )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'zoom_out' ), 'zoom out' )
            
            #
            
            if self._current_media.GetMime() != HC.APPLICATION_FLASH:
                
                ( my_width, my_height ) = self.GetClientSize()
                
                ( media_width, media_height ) = self._current_media.GetResolution()
                
                if self._current_zoom == 1.0:
                    
                    if media_width > my_width or media_height > my_height:
                        
                        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'zoom_switch' ), 'zoom fit' )
                        
                    
                else:
                    
                    menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'zoom_switch' ), 'zoom full' )
                    
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if i_can_post_ratings:
            
            manage_menu = wx.Menu()
            
            manage_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'manage_tags' ), 'tags' )
            manage_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'manage_ratings' ), 'ratings' )
            
            menu.AppendMenu( CC.ID_NULL, 'manage', manage_menu )
            
        else:
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'manage_tags' ), 'manage tags' )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if self._current_media.HasInbox(): menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'archive' ), '&archive' )
        if self._current_media.HasArchive(): menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'inbox' ), 'return to &inbox' )
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'remove' ), '&remove' )
        
        if CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent():
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'delete', CC.LOCAL_FILE_SERVICE_KEY ), '&delete' )
            
        elif CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'delete', CC.TRASH_SERVICE_KEY ), '&delete from trash now' )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'undelete' ), '&undelete' )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'open_externally' ), '&open externally' )
        
        share_menu = wx.Menu()
        
        copy_menu = wx.Menu()
        
        copy_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_files' ), 'file' )
        
        copy_hash_menu = wx.Menu()
        
        copy_hash_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_hash', 'sha256' ) , 'sha256 (hydrus default)' )
        copy_hash_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_hash', 'md5' ) , 'md5' )
        copy_hash_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_hash', 'sha1' ) , 'sha1' )
        copy_hash_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_hash', 'sha512' ) , 'sha512' )
        
        copy_menu.AppendMenu( CC.ID_NULL, 'hash', copy_hash_menu )
        
        if self._current_media.GetMime() in HC.IMAGES and self._current_media.GetDuration() is None: copy_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_bmp' ), 'image' )
        copy_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_path' ), 'path' )
        copy_menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_local_url' ), 'local url' )
        
        share_menu.AppendMenu( CC.ID_NULL, 'copy', copy_menu )
        
        menu.AppendMenu( CC.ID_NULL, 'share', share_menu )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if self.GetParent().IsFullScreen():
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'fullscreen_switch' ), 'exit fullscreen' )
            
        else:
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'fullscreen_switch' ), 'go fullscreen' )
            
        
        HydrusGlobals.client_controller.PopupMenu( self, menu )
        
        event.Skip()
        
    
class MediaContainer( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._media = None
        self._show_action = None
        
        self._media_window = None
        
        self._embed_button = EmbedButton( self )
        self._embed_button.Bind( wx.EVT_LEFT_DOWN, self.EventEmbedButton )
        
        self._animation_bar = AnimationBar( self )
        
        self.Hide()
        
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventPropagateMouse )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _DestroyThisMediaWindow( self, media_window ):
        
        if media_window is not None:
            
            media_window.Hide()
            
            wx.CallLater( 50, media_window.Destroy )
            
        
    
    def _HideAnimationBar( self ):
        
        self._animation_bar.SetNoneMedia()
        
        self._animation_bar.Hide()
        
    
    def _MakeMediaWindow( self ):
        
        old_media_window = self._media_window
        destroy_old_media_window = True
        
        ( media_initial_size, media_initial_position ) = ( self.GetClientSize(), ( 0, 0 ) )
        
        if self._show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            raise Exception( 'This media should not be shown in the media viewer!' )
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON:
            
            self._media_window = OpenExternallyPanel( self, self._media )
            
        else:
            
            start_paused = self._show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL_PAUSED, CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED )
            
            if ShouldHaveAnimationBar( self._media ) or self._media.GetMime() == HC.APPLICATION_FLASH:
                
                if ShouldHaveAnimationBar( self._media ):
                    
                    ( x, y ) = media_initial_size
                    
                    media_initial_size = ( x, y - ANIMATED_SCANBAR_HEIGHT )
                    
                
                if self._media.GetMime() == HC.APPLICATION_FLASH:
                    
                    self._media_window = wx.lib.flashwin.FlashWindow( self, size = media_initial_size, pos = media_initial_position )
                    
                    if self._media_window is None:
                        
                        raise Exception( 'Failed to initialise the flash window' )
                        
                    
                    client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                    
                    self._media_window.movie = client_files_manager.GetFilePath( self._media.GetHash(), HC.APPLICATION_FLASH )
                    
                else:
                    
                    if isinstance( self._media_window, Animation ):
                        
                        destroy_old_media_window = False
                        
                    else:
                        
                        self._media_window = Animation( self )
                        
                        self._media_window.SetAnimationBar( self._animation_bar )
                        
                    
                    self._media_window.SetMedia( self._media, start_paused )
                    
                
                if ShouldHaveAnimationBar( self._media ):
                    
                    self._animation_bar.Show()
                    
                    self._animation_bar.SetMediaAndWindow( self._media, self._media_window )
                    
                else:
                    
                    self._HideAnimationBar()
                    
                
            else:
                
                if isinstance( self._media_window, StaticImage ):
                    
                    destroy_old_media_window = False
                    
                else:
                    
                    self._media_window = StaticImage( self )
                    
                
                self._media_window.SetMedia( self._media )
                
                self._HideAnimationBar()
                
            
        
        if old_media_window is not None and destroy_old_media_window:
            
            self._DestroyThisMediaWindow( old_media_window )
            
        
    
    def _SizeAndPositionChildren( self ):
        
        if self._media is not None:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            if self._media_window is None:
                
                self._embed_button.SetSize( ( my_width, my_height ) )
                
            else:
                
                ( media_width, media_height ) = ( my_width, my_height )
                
                if ShouldHaveAnimationBar( self._media ):
                    
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
                
                screen_position = self.ClientToScreen( event.GetPosition() )
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
                    
                    if current_frame_index == num_frames - 1: current_frame_index = 0
                    else: current_frame_index += 1
                    
                else:
                    
                    if current_frame_index == 0: current_frame_index = num_frames - 1
                    else: current_frame_index -= 1
                    
                
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
            
        
    
    def SetMedia( self, media, initial_size, initial_position, show_action ):
        
        self._media = media
        
        self.Show()
        
        self._show_action = show_action
        
        if self._show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED ):
            
            self._HideAnimationBar()
            
            self._DestroyThisMediaWindow( self._media_window )
            
            self._media_window = None
            
            self._embed_button.SetMedia( self._media )
            
            self._embed_button.Show()
            
        else:
            
            self._embed_button.Hide()
            
            self._MakeMediaWindow()
            
        
        self.SetSize( initial_size )
        self.SetPosition( initial_position )
        
        self._SizeAndPositionChildren()
        
    
    def SetNoneMedia( self ):
        
        self._media = None
        
        self._DestroyThisMediaWindow( self._media_window )
        
        self._media_window = None
        
        self.Hide()
        
    
class EmbedButton( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._media = None
        
        self._dirty = False
        
        self._canvas_bmp = None
        self._thumbnail_bmp = None
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_HAND ) )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _Redraw( self, dc ):
        
        ( x, y ) = self.GetClientSize()
        
        center_x = x / 2
        center_y = y / 2
        radius = min( 50, center_x, center_y ) - 5
        
        dc.SetBackground( wx.Brush( wx.Colour( *HC.options[ 'gui_colours' ][ 'media_background' ] ) ) )
        
        dc.Clear()
        
        if self._thumbnail_bmp is not None:
            
            # animations will have the animation bar space underneath in this case, so colour it in
            dc.SetBackground( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) ) )
            
            dc.DrawRectangle( 0, y - ANIMATED_SCANBAR_HEIGHT, x, ANIMATED_SCANBAR_HEIGHT )
            
            ( thumb_width, thumb_height ) = self._thumbnail_bmp.GetSize()
            
            scale = x / float( thumb_width )
            
            dc.SetUserScale( scale, scale )
            
            dc.DrawBitmap( self._thumbnail_bmp, 0, 0 )
            
            dc.SetUserScale( 1.0, 1.0 )
            
        
        dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) ) )
        
        dc.DrawCircle( center_x, center_y, radius )
        
        dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) ) )
        
        # play symbol is a an equilateral triangle
        
        triangle_side = radius * 0.8
        
        half_triangle_side = int( triangle_side / 2 )
        
        cos30 = 0.866
        
        triangle_width = triangle_side * cos30
        
        third_triangle_width = int( triangle_width / 3 )
        
        points = []
        
        points.append( ( center_x - third_triangle_width, center_y - half_triangle_side ) )
        points.append( ( center_x + third_triangle_width * 2, center_y ) )
        points.append( ( center_x - third_triangle_width, center_y + half_triangle_side ) )
        
        dc.DrawPolygon( points )
        
        #
        
        dc.SetPen( wx.Pen( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNSHADOW ) ) )
        
        dc.SetBrush( wx.TRANSPARENT_BRUSH )
        
        dc.DrawRectangle( 0, 0, x, y )
        
        self._dirty = False
        
    
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
                    
                    wx.CallAfter( self._canvas_bmp.Destroy )
                    
                
                self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
                
                self._dirty = True
                
                self.Refresh()
                
            
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        if self._media is None:
            
            needs_thumb = False
            
        else:
            
            needs_thumb = self._media.GetLocationsManager().IsLocal() and self._media.GetMime() in HC.MIMES_WITH_THUMBNAILS
            
        
        if needs_thumb:
            
            hash = self._media.GetHash()
            
            thumbnail_path = HydrusGlobals.client_controller.GetClientFilesManager().GetFullSizeThumbnailPath( hash )
            
            self._thumbnail_bmp = ClientRendering.GenerateHydrusBitmap( thumbnail_path ).GetWxBitmap()
            
        else:
            
            self._thumbnail_bmp = None
            
        
    
class OpenExternallyPanel( wx.Panel ):
    
    def __init__( self, parent, media ):
        
        wx.Panel.__init__( self, parent )
        
        self.SetBackgroundColour( wx.Colour( *HC.options[ 'gui_colours' ][ 'media_background' ] ) )
        
        self._media = media
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        if self._media.GetLocationsManager().IsLocal() and self._media.GetMime() in HC.MIMES_WITH_THUMBNAILS:
            
            hash = self._media.GetHash()
            
            thumbnail_path = HydrusGlobals.client_controller.GetClientFilesManager().GetFullSizeThumbnailPath( hash )
            
            bmp = ClientRendering.GenerateHydrusBitmap( thumbnail_path ).GetWxBitmap()
            
            thumbnail = ClientGUICommon.BufferedWindowIcon( self, bmp )
            
            thumbnail.Bind( wx.EVT_LEFT_DOWN, self.EventButton )
            
            vbox.AddF( thumbnail, CC.FLAGS_CENTER )
            
        
        m_text = HC.mime_string_lookup[ media.GetMime() ]
        
        button = wx.Button( self, label = 'open ' + m_text + ' externally', size = OPEN_EXTERNALLY_BUTTON_SIZE )
        
        vbox.AddF( button, CC.FLAGS_CENTER )
        
        self.SetSizer( vbox )
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_HAND ) )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventButton )
        button.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        HydrusPaths.LaunchFile( path )
        
    
class StaticImage( wx.Window ):
    
    def __init__( self, parent ):
        
        wx.Window.__init__( self, parent )
        
        self._dirty = True
        
        self._media = None
        
        self._first_background_drawn = False
        
        self._image_renderer = None
        
        self._is_rendered = False
        
        self._canvas_bmp = None
        
        self._timer_render_wait = wx.Timer( self, id = ID_TIMER_RENDER_WAIT )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_TIMER, self.TIMEREventRenderWait, id = ID_TIMER_RENDER_WAIT )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventPropagateMouse )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _DrawBackground( self, dc ):
        
        dc.SetBackground( wx.Brush( wx.Colour( *HC.options[ 'gui_colours' ][ 'media_background' ] ) ) )
        
        dc.Clear()
        
        self._first_background_drawn = True
        
    
    def _Redraw( self, dc ):
        
        if self._image_renderer is not None and self._image_renderer.IsReady():
            
            self._DrawBackground( dc )
            
            wx_bitmap = self._image_renderer.GetWXBitmap( self._canvas_bmp.GetSize() )
            
            dc.DrawBitmap( wx_bitmap, 0, 0 )
            
            wx_bitmap.Destroy()
            
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
        
        dc = wx.BufferedPaintDC( self, self._canvas_bmp )
        
        if self._dirty:
            
            self._Redraw( dc )
            
        
    
    def EventPropagateMouse( self, event ):
        
        screen_position = self.ClientToScreen( event.GetPosition() )
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
                    
                    wx.CallAfter( self._canvas_bmp.Destroy )
                    
                
                self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
                
                self._first_background_drawn = False
                
                self._SetDirty()
                
            
        
    
    def IsRendered( self ):
        
        return self._is_rendered
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        image_cache = HydrusGlobals.client_controller.GetCache( 'images' )
        
        self._image_renderer = image_cache.GetImageRenderer( self._media )
        
        self._is_rendered = False
        
        if not self._image_renderer.IsReady():
            
            self._timer_render_wait.Start( 16, wx.TIMER_CONTINUOUS )
            
        
        self._dirty = True
        
        self.Refresh()
        
    
    def TIMEREventRenderWait( self, event ):
        
        try:
            
            if self._image_renderer.IsReady():
                
                self._SetDirty()
                
                self._timer_render_wait.Stop()
                
            
        except wx.PyDeadObjectError:
            
            self._timer_render_wait.Stop()
            
        except:
            
            self._timer_render_wait.Stop()
            
            raise
            
        
    
