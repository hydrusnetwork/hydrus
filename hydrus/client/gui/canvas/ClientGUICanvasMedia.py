import itertools
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

try:
    
    # this appears to be Python 3.8+ and/or the equivalent Qt versions
    
    from qtpy import QtMultimediaWidgets as QMW
    from qtpy import QtMultimedia as QM
    
except:
    
    pass
    

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientRendering
from hydrus.client import ClientUgoiraHandling
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtInit
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUIMPV
from hydrus.client.gui.media import ClientGUIMediaControls
from hydrus.client.gui.media import ClientGUIMediaVolume
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaResult

ZOOM_CENTERPOINT_MEDIA_CENTER = 0
ZOOM_CENTERPOINT_VIEWER_CENTER = 1
ZOOM_CENTERPOINT_MOUSE = 2
ZOOM_CENTERPOINT_MEDIA_TOP_LEFT = 3

ZOOM_CENTERPOINT_TYPES = ( ZOOM_CENTERPOINT_VIEWER_CENTER, ZOOM_CENTERPOINT_MOUSE, ZOOM_CENTERPOINT_MEDIA_CENTER, ZOOM_CENTERPOINT_MEDIA_TOP_LEFT )

zoom_centerpoints_str_lookup = {}

zoom_centerpoints_str_lookup[ ZOOM_CENTERPOINT_MEDIA_CENTER ] = 'media center'
zoom_centerpoints_str_lookup[ ZOOM_CENTERPOINT_VIEWER_CENTER ] = 'viewer center'
zoom_centerpoints_str_lookup[ ZOOM_CENTERPOINT_MOUSE ] = 'mouse (or viewer center if mouse outside)'
zoom_centerpoints_str_lookup[ ZOOM_CENTERPOINT_MEDIA_TOP_LEFT ] = 'media top-left'

MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE = 0
MEDIA_VIEWER_ZOOM_TYPE_CANVAS = 1
MEDIA_VIEWER_ZOOM_TYPE_100 = 2
MEDIA_VIEWER_ZOOM_TYPE_FILL_X = 3
MEDIA_VIEWER_ZOOM_TYPE_FILL_Y = 4
MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO = 5

MEDIA_VIEWER_ZOOM_TYPES = ( MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE, MEDIA_VIEWER_ZOOM_TYPE_100, MEDIA_VIEWER_ZOOM_TYPE_CANVAS, MEDIA_VIEWER_ZOOM_TYPE_FILL_X, MEDIA_VIEWER_ZOOM_TYPE_FILL_Y, MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO )

media_viewer_zoom_type_str_lookup = {
    MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE : 'default for filetype',
    MEDIA_VIEWER_ZOOM_TYPE_CANVAS : 'canvas fit',
    MEDIA_VIEWER_ZOOM_TYPE_100 : '100% zoom',
    MEDIA_VIEWER_ZOOM_TYPE_FILL_X : 'fill horizontally',
    MEDIA_VIEWER_ZOOM_TYPE_FILL_Y : 'fill vertically',
    MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO : 'canvas fill'
}

media_viewer_zoom_type_description_lookup = {
    MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE : 'Allow the per-filetype rules to apply, no override.',
    MEDIA_VIEWER_ZOOM_TYPE_CANVAS : 'Fit the media to the viewer, so it is as big as it can be.',
    MEDIA_VIEWER_ZOOM_TYPE_100 : 'Set the zoom level to 100%.',
    MEDIA_VIEWER_ZOOM_TYPE_FILL_X : 'Scale the media to fill the viewer width, even if that means it overflows.',
    MEDIA_VIEWER_ZOOM_TYPE_FILL_Y : 'Scale the media to fill the viewer height, even if that means it overflows.',
    MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO : 'Scale the media up to completely fill the whole viewer, even if that means it overflows.'
}

media_viewer_zoom_type_to_cac_simple_commands = {
    MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE : CAC.SIMPLE_ZOOM_DEFAULT_VIEWER_CENTER,
    MEDIA_VIEWER_ZOOM_TYPE_CANVAS : CAC.SIMPLE_ZOOM_CANVAS_VIEWER_CENTER,
    MEDIA_VIEWER_ZOOM_TYPE_100 : CAC.SIMPLE_ZOOM_100_CENTER,
    MEDIA_VIEWER_ZOOM_TYPE_FILL_X : CAC.SIMPLE_ZOOM_CANVAS_FILL_X_VIEWER_CENTER,
    MEDIA_VIEWER_ZOOM_TYPE_FILL_Y : CAC.SIMPLE_ZOOM_CANVAS_FILL_Y_VIEWER_CENTER,
    MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO : CAC.SIMPLE_ZOOM_CANVAS_FILL_AUTO_VIEWER_CENTER
}

OPEN_EXTERNALLY_BUTTON_SIZE = ( 200, 45 )
OPEN_EXTERNALLY_MAX_THUMBNAIL_SIZE = ( 200, 200 )

def CalculateCanvasMediaSize( media, canvas_size: QC.QSize, show_action ):
    
    canvas_width = canvas_size.width()
    canvas_height = canvas_size.height()
    
    '''if ClientGUICanvasMedia.ShouldHaveAnimationBar( media, show_action ):
        
        animated_scanbar_height = CG.client_controller.new_options.GetInteger( 'animated_scanbar_height' )
        
        canvas_height -= animated_scanbar_height
        '''
    
    canvas_width = max( canvas_width, 80 )
    canvas_height = max( canvas_height, 60 )
    
    return ( canvas_width, canvas_height )
    

def CalculateCanvasZooms( canvas_size: QC.QSize, canvas_type: int, device_pixel_ratio: float, media, show_action ) -> dict[ int, int ]:
    
    zoom_types_to_zooms = {
        MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE : 1.0,
        MEDIA_VIEWER_ZOOM_TYPE_CANVAS : 1.0,
        MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO : 1.0,
        MEDIA_VIEWER_ZOOM_TYPE_FILL_X : 1.0,
        MEDIA_VIEWER_ZOOM_TYPE_FILL_Y : 1.0,
        MEDIA_VIEWER_ZOOM_TYPE_100 : 1.0
    }
    
    if media is None:
        
        return zoom_types_to_zooms
        
    
    if show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
        
        return zoom_types_to_zooms
        
    
    new_options = CG.client_controller.new_options
    
    ( media_width, media_height ) = CalculateMediaSize( media, 1.0 )
    
    ( canvas_width, canvas_height ) = CalculateCanvasMediaSize( media, canvas_size, show_action )
    
    raw_canvas_width = canvas_width * device_pixel_ratio
    raw_canvas_height = canvas_height * device_pixel_ratio
    
    width_zoom = raw_canvas_width / media_width
    
    height_zoom = raw_canvas_height / media_height
    
    canvas_zoom = min( ( width_zoom, height_zoom ) )
    
    image_aspect = media_width / media_height
    canvas_aspect = raw_canvas_width / raw_canvas_height
    
    #overfill the canvas
    if image_aspect > canvas_aspect:
        
        fill_auto_zoom = height_zoom
        
    else:
        
        fill_auto_zoom = width_zoom
        
    
    zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ] = canvas_zoom
    zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_FILL_X ] = width_zoom
    zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_FILL_Y ] = height_zoom
    zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO ] = fill_auto_zoom
    
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
            
        
    
    if media.GetMime() in HC.AUDIO:
        
        scale_up_action = CC.MEDIA_VIEWER_SCALE_100
        scale_down_action = CC.MEDIA_VIEWER_SCALE_TO_CANVAS
        
    elif canvas_type == CC.CANVAS_PREVIEW:
        
        scale_up_action = preview_scale_up
        scale_down_action = preview_scale_down
        
    else:
        
        scale_up_action = media_scale_up
        scale_down_action = media_scale_down
        
    
    can_be_scaled_down = media_width > raw_canvas_width or media_height > raw_canvas_height
    can_be_scaled_up = media_width < raw_canvas_width and media_height < raw_canvas_height
    
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
        
    
    zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE ] = default_zoom
    
    return zoom_types_to_zooms
    

def CalculateMediaContainerSize( media, device_pixel_ratio: float, zoom, show_action ) -> QC.QSize:
    
    if show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
        
        raise Exception( 'This media should not be shown in the media viewer!' )
        
    elif show_action == CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON:
        
        ( width, height ) = OPEN_EXTERNALLY_BUTTON_SIZE
        
        # Note that this handles a zipfile default thumb too. by sending None resolution to GetThumbnailResolution, it falls back to default dimensions
        # imperfect, but overall fine for most situations
        
        bounding_dimensions = CG.client_controller.options[ 'thumbnail_dimensions' ]
        thumbnail_scale_type = CG.client_controller.new_options.GetInteger( 'thumbnail_scale_type' )
        
        # we want the device independant size here, not actual pixels, so want to keep this 100
        #thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
        thumbnail_dpr_percent = 100
        
        ( thumb_width, thumb_height ) = HydrusImageHandling.GetThumbnailResolution( media.GetResolution(), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
        
        height = height + min( OPEN_EXTERNALLY_MAX_THUMBNAIL_SIZE[1], thumb_height )
        
        return QC.QSize( width, height )
        
    else:
        
        ( raw_media_width, raw_media_height ) = CalculateMediaSize( media, zoom )
        
        media_width = int( raw_media_width / device_pixel_ratio )
        media_height = int( raw_media_height / device_pixel_ratio )
        
        return QC.QSize( media_width, media_height )
        
    

def CalculateMediaSize( media, zoom ):
    
    if media.GetMime() in HC.AUDIO or not media.HasUsefulResolution():
        
        ( original_width, original_height ) = ( 360, 240 )
        
        if zoom >= 1:
            
            # audio player can only be scaled down, not up
            return ( original_width, original_height )
            
        
    else:
        
        ( original_width, original_height ) = media.GetResolution()
        
    
    media_width = int( round( zoom * original_width ) )
    media_height = int( round( zoom * original_height ) )
    
    media_width = max( 1, media_width )
    media_height = max( 1, media_height )
    
    return ( media_width, media_height )
    

def ShouldHaveAnimationBar( media, show_action ):
    
    if media is None:
        
        return False
        
    
    if show_action not in ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER ):
        
        return False
        
    
    if not media.HasDuration() and media.GetMime() is not HC.ANIMATION_UGOIRA:
        
        return False
        
    
    is_animation = media.GetMime() in HC.VIEWABLE_ANIMATIONS
    is_audio = media.GetMime() in HC.AUDIO
    is_video = media.GetMime() in HC.VIDEO
    
    if show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER ):
        
        if is_animation or is_audio or is_video:
            
            return True
            
        
    elif show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE:
        
        if is_animation or is_video:
            
            return True
            
        
    
    return False
    

def WeAreExpectingToLoadThisMediaFile( media_result: ClientMediaResult.MediaResult, canvas_type: int ) -> bool:
    
    ( media_show_action, media_start_paused, media_start_with_embed ) = ClientMedia.GetShowAction( media_result, canvas_type )
    
    if media_show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER ):
        
        return True
        
    
    return False
    

class Animation( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    
    def __init__( self, parent, canvas_type, background_colour_generator ):
        
        super().__init__( parent )
        
        self._canvas_type = canvas_type
        self._background_colour_generator = background_colour_generator
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
        self.setMouseTracking( True )
        
        self._media = None
        
        self._last_device_pixel_ratio = self.devicePixelRatio()
        
        self._have_drawn_background_once = False
        self._playthrough_count = 0
        
        self._num_frames = 1
        
        self._frame_durations_ms = None
        
        self._stop_for_slideshow = False
        
        self._current_frame_index = 0
        self._current_frame_drawn = False
        self._current_timestamp_ms = None
        self._next_frame_due_at = HydrusTime.GetNowPrecise()
        self._slow_frame_score = 1.0
        
        self._paused = True
        
        self._video_container = None
        
        self._canvas_qt_pixmap = None
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            shortcut_set = 'media_viewer_media_window'
            
        else:
            
            shortcut_set = 'preview_media_window'
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ shortcut_set ], catch_mouse = True )
        
    
    def _ClearCanvasBitmap( self ):
        
        if self._canvas_qt_pixmap is not None:
            
            self._canvas_qt_pixmap = None
            
        
    
    def _GetRawPixelSize( self ) -> QC.QSize:
        
        return self.size() * self.devicePixelRatio()
        
    
    def _ReinitForResizeOrDPRChange( self ):
        
        my_raw_size = self._GetRawPixelSize()
        
        my_raw_width = my_raw_size.width()
        my_raw_height = my_raw_size.height()
        
        self._ClearCanvasBitmap()
        
        self._last_device_pixel_ratio = self.devicePixelRatio()
        
        self._current_frame_drawn = False
        self._have_drawn_background_once = False
        
        self.update()
        
        if self._media is not None:
            
            ( media_width, media_height ) = self._media.GetResolution()
            
            if self._video_container is not None:
                
                ( renderer_width, renderer_height ) = self._video_container.GetSize()
                
                we_just_zoomed_in = my_raw_width > renderer_width or my_raw_height > renderer_height
                we_just_zoomed_out = my_raw_width < renderer_width or my_raw_height < renderer_height
                
                if we_just_zoomed_in:
                    
                    if self._video_container.IsScaled():
                        
                        target_width = min( media_width, my_raw_width )
                        target_height = min( media_height, my_raw_height )
                        
                        self._video_container.Stop()
                        
                        self._video_container = ClientRendering.RasterContainerVideo( self._media, ( target_width, target_height ), init_position = self._current_frame_index, frame_durations_ms = self._frame_durations_ms )
                        
                    
                elif we_just_zoomed_out:
                    
                    if my_raw_width < media_width or my_raw_height < media_height: # i.e. new zoom is scaled
                        
                        self._video_container.Stop()
                        
                        self._video_container = ClientRendering.RasterContainerVideo( self._media, ( my_raw_width, my_raw_height ), init_position = self._current_frame_index, frame_durations_ms = self._frame_durations_ms )
                        
                    
                
            
        
    
    def _TryToDrawCanvasBitmap( self ):
        
        my_raw_size = self._GetRawPixelSize()
        
        my_raw_width = my_raw_size.width()
        my_raw_height = my_raw_size.height()
        
        if self._video_container is None:
            
            self._video_container = ClientRendering.RasterContainerVideo( self._media, ( my_raw_width, my_raw_height ), init_position = self._current_frame_index, frame_durations_ms = self._frame_durations_ms )
            
        
        if not self._video_container.HasFrame( self._current_frame_index ):
            
            return
            
        
        if self._canvas_qt_pixmap is None:
            
            self._canvas_qt_pixmap = CG.client_controller.bitmap_manager.GetQtPixmap( my_raw_width, my_raw_height )
            
        
        self._canvas_qt_pixmap.setDevicePixelRatio( self.devicePixelRatio() )
        
        painter = QG.QPainter( self._canvas_qt_pixmap )
        
        # this makes transparency work nice, so just force it
        self._DrawABlankFrame( painter )
        
        current_frame = self._video_container.GetFrame( self._current_frame_index )
        
        current_frame_image = current_frame.GetQtImage()
        
        painter.setRenderHint( QG.QPainter.RenderHint.SmoothPixmapTransform, True )

        # note we draw to self.rect(), which is in DPR coordinates. the pixmap needs to be DPR'd by here mate, this caught us up before
        painter.drawImage( self.rect(), current_frame_image )
        
        self._current_frame_drawn = True
        
        next_frame_duration_s = HydrusTime.SecondiseMSFloat( self._video_container.GetDurationMS( self._current_frame_index ) )
        
        next_frame_ideally_due = self._next_frame_due_at + next_frame_duration_s
        
        if HydrusTime.TimeHasPassedPrecise( next_frame_ideally_due ):
            
            self._next_frame_due_at = HydrusTime.GetNowPrecise() + next_frame_duration_s
            
        else:
            
            self._next_frame_due_at = next_frame_ideally_due
            
        
    
    def _DrawABlankFrame( self, painter ):
        
        if self._background_colour_generator.CanDoTransparencyCheckerboard() and self._media is not None and self._media.GetFileInfoManager().has_transparency:
            
            light_grey = QG.QColor( 237, 237, 237 )
            dark_grey = QG.QColor( 222, 222, 222 )
            
            painter.setBackground( QG.QBrush( light_grey ) )
            
            painter.eraseRect( painter.viewport() )
            
            # 16x16 boxes, light grey in top right
            BOX_LENGTH = int( 16 * self.devicePixelRatio() )
            
            painter_width = painter.viewport().width()
            painter_height = painter.viewport().height()
            
            num_cols = painter_width // BOX_LENGTH
            
            if painter_width % BOX_LENGTH > 0:
                
                num_cols += 1
                
            
            num_rows = painter_height // BOX_LENGTH
            
            if painter_height % BOX_LENGTH > 0:
                
                num_rows += 1
                
            
            painter.setBrush( QG.QBrush( dark_grey ) )
            painter.setPen( QG.QPen( QC.Qt.PenStyle.NoPen ) )
            
            for y_index in range( num_rows ):
                
                for x_index in range( num_cols ):
                    
                    if ( x_index + y_index ) % 2 == 1:
                        
                        rect = QC.QRect( x_index * BOX_LENGTH, y_index * BOX_LENGTH, BOX_LENGTH, BOX_LENGTH )
                        
                        if painter.viewport().intersects( rect ):
                            
                            painter.drawRect( rect )
                            
                        
                    
                
            
            self._have_drawn_background_once = True
            
            return
            
        
        colour = self._background_colour_generator.GetColour()
        
        painter.setBackground( QG.QBrush( colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        self._have_drawn_background_once = True
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def CurrentFrame( self ):
        
        return self._current_frame_index
        
    
    def GetAnimationBarStatus( self ):
        
        if self._video_container is None:
            
            buffer_indices = None
            
        else:
            
            buffer_indices = self._video_container.GetBufferIndices()
            
            if self._current_timestamp_ms is None and self._video_container.IsInitialised():
                
                self._current_timestamp_ms = self._video_container.GetTimestampMS( self._current_frame_index )
                
            
        
        return ( self._current_frame_index, self._current_timestamp_ms, self._paused, buffer_indices )
        
    
    def GotoFrame( self, frame_index, pause_afterwards = True ):
        
        if self._video_container is not None and self._video_container.IsInitialised():
            
            if frame_index != self._current_frame_index:
                
                self._current_frame_index = frame_index
                self._current_timestamp_ms = None
                
                self._next_frame_due_at = HydrusTime.GetNowPrecise()
                
                self._video_container.GetReadyForFrame( self._current_frame_index )
                
                self._current_frame_drawn = False
                
                self.update()
                
            
            if pause_afterwards:
                
                self._paused = True
                
            
        
    
    def GotoTimestamp( self, timestamp_ms, round_direction, pause_afterwards = True ):
        
        if self._video_container is not None and self._video_container.IsInitialised():
            
            frame_index = self._video_container.GetFrameIndex( timestamp_ms )
            
            if frame_index == self._current_frame_index:
                
                frame_index += round_direction
                
            
            frame_index = max( 0, frame_index )
            
            if frame_index > self._media.GetNumFrames() - 1:
                
                frame_index = 0
                
            
            self.GotoFrame( frame_index, pause_afterwards = pause_afterwards )
            
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._playthrough_count > 0
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def paintEvent( self, event ):
        
        if self.devicePixelRatio() != self._last_device_pixel_ratio:
            
            self._ReinitForResizeOrDPRChange()
            
        
        if not self._current_frame_drawn:
            
            self._TryToDrawCanvasBitmap()
            
        
        painter = QG.QPainter( self )
        
        if self._canvas_qt_pixmap is None:
            
            self._DrawABlankFrame( painter )
            
        else:
            
            painter.drawPixmap( self.rect(), self._canvas_qt_pixmap )
            
        
    
    def Pause( self ):
        
        self._paused = True
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def Play( self ):
        
        self._paused = False
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_PAUSE_MEDIA:
                
                self.Pause()
                
            elif action == CAC.SIMPLE_PAUSE_PLAY_MEDIA:
                
                self.PausePlay()
                
            elif action == CAC.SIMPLE_MEDIA_SEEK_DELTA:
                
                ( direction, duration_ms ) = command.GetSimpleData()
                
                self.SeekDelta( direction, duration_ms )
                
            elif action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER and self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
                
                self.window().close()
                
            elif action == CAC.SIMPLE_LAUNCH_MEDIA_VIEWER and self._canvas_type == CC.CANVAS_PREVIEW:
                
                self.launchMediaViewer.emit()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def resizeEvent( self, event ):
        
        size = self.size()
        
        my_raw_width = size.width()
        my_raw_height = size.height()
        
        if my_raw_width > 0 and my_raw_height > 0:
            
            if size != event.oldSize():
                
                self._ReinitForResizeOrDPRChange()
                
            
        
    
    def SeekDelta( self, direction, duration_ms ):
        
        if self._current_timestamp_ms is not None and self._video_container is not None and self._video_container.IsInitialised():
            
            new_ts = max( 0, self._current_timestamp_ms + ( direction * duration_ms ) )
            
            self.GotoTimestamp( new_ts, direction, pause_afterwards = False )
            
        
    
    def SetBackgroundColourGenerator( self, background_colour_generator ):
        
        self._background_colour_generator = background_colour_generator
        
    
    def StopForSlideshow( self, value ):
        
        self._stop_for_slideshow = value
        
    
    def SetMedia( self, media: typing.Optional[ ClientMedia.MediaSingleton ], start_paused = False ):
        
        if media == self._media:
            
            return
            
        
        self._media = media
        
        self._ClearCanvasBitmap()
        
        self._have_drawn_background_once = False
        self._playthrough_count = 0
        
        self._stop_for_slideshow = False
        
        self._current_frame_index = int( ( self._num_frames - 1 ) * HC.options[ 'animation_start_position' ] )
        self._current_frame_drawn = False
        self._current_timestamp_ms = None
        self._next_frame_due_at = HydrusTime.GetNowPrecise()
        self._slow_frame_score = 1.0
        
        self._paused = start_paused
        
        if self._video_container is not None:
            
            self._video_container.Stop()
            
        
        self._video_container = None
        
        self._frame_durations_ms = None
        self._duration_ms = None
        
        if self._media is None:
            
            self._num_frames = 1
            
            CG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
        else:
            
            self._num_frames = self._media.GetNumFrames()
            
            self._duration_ms = self._media.GetDurationMS()
            
            if self._media.GetMime() == HC.ANIMATION_UGOIRA:
                
                self._frame_durations_ms = ClientUgoiraHandling.GetFrameDurationsMSUgoira( media.GetMediaResult() )
                
            
            if self._duration_ms is None and self._frame_durations_ms is not None:
                
                self._duration_ms = sum( self._frame_durations_ms )
                
            
            CG.client_controller.gui.RegisterAnimationUpdateWindow( self )
            
            self.update()
            
        
        
    def GetDurationMS( self ):
        
        return self._duration_ms
        
    
    def GetNumFrames( self ):
        
        return self._num_frames
        
    
    def TIMERAnimationUpdate( self ):
        
        if self._media is None:
            
            return
            
        
        try:
            
            if self.isVisible():
                
                if self._current_frame_drawn:
                    
                    if not self._paused and HydrusTime.TimeHasPassedPrecise( self._next_frame_due_at ):
                        
                        num_frames = self._media.GetNumFrames()
                        
                        next_frame_index = ( self._current_frame_index + 1 ) % num_frames
                        
                        if next_frame_index == 0:
                            
                            self._playthrough_count += 1
                            
                            do_times_to_play_animation_pause = False
                            
                            if self._media.GetMime() in HC.VIEWABLE_ANIMATIONS and not CG.client_controller.new_options.GetBoolean( 'always_loop_gifs' ):
                                
                                times_to_play_animation = self._video_container.GetTimesToPlayAnimation()
                                
                                # 0 is infinite
                                if times_to_play_animation != 0 and self._playthrough_count >= times_to_play_animation:
                                    
                                    do_times_to_play_animation_pause = True
                                    
                                
                            
                            if self._stop_for_slideshow or do_times_to_play_animation_pause:
                                
                                self._paused = True
                                
                            else:
                                
                                self._current_frame_index = next_frame_index
                                self._current_timestamp_ms = 0
                                
                            
                        else:
                            
                            self._current_frame_index = next_frame_index
                            
                            if self._current_timestamp_ms is not None and self._video_container is not None and self._video_container.IsInitialised():
                                
                                duration_ms = self._video_container.GetDurationMS( self._current_frame_index - 1 )
                                
                                self._current_timestamp_ms += duration_ms
                                
                            
                        
                        self._current_frame_drawn = False
                        
                    
                
                if self._video_container is not None:
                    
                    if not self._current_frame_drawn:
                        
                        if self._video_container.HasFrame( self._current_frame_index ):
                            
                            self.update()
                            
                        
                    
                
            
        except:
            
            CG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
            raise
            
        
    
class AnimationBar( QW.QWidget ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._qss_colours = {
            'hab_border' : QG.QColor( 0, 0, 0 ),
            'hab_background' : QG.QColor( 240, 240, 240 ),
            'hab_nub' : QG.QColor( 96, 96, 96 )
        }
        
        self.setObjectName( 'HydrusAnimationBar' )
        
        self.setCursor( QG.QCursor( QC.Qt.CursorShape.ArrowCursor ) )
        
        self.setSizePolicy( QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Fixed )
        
        self._media_window = None
        self._duration_ms = 1000
        self._num_frames = 1
        self._last_drawn_info = None
        self._next_draw_info = None
        self._show_gubbins = True
        
        self._show_text = True
        
        self._currently_in_a_drag = False
        self._it_was_playing_before_drag = False
        
    
    def _DoAnimationStatusUpdate( self ):
        
        if self._CurrentMediaWindowIsBad():
            
            return
            
        
        # we must never call this method in the paintEvent
        current_animation_bar_status = self._media_window.GetAnimationBarStatus()
        
        if self._last_drawn_info != current_animation_bar_status:
            
            self._next_draw_info = current_animation_bar_status
            
            self.update()
            
        
    
    def _DrawBlank( self, painter ):
        
        self.setProperty( 'playing', False )
        
        background_colour = self._qss_colours[ 'hab_background' ]
        
        painter.setBackground( background_colour )
        
        painter.eraseRect( painter.viewport() )
        
    
    def _GetXFromFrameIndex( self, index, width_offset = 0 ):
        
        if self._num_frames is None or self._num_frames < 2:
            
            return 0
            
        
        my_width = self.size().width()
        
        return int( ( my_width - width_offset ) * index / ( self._num_frames - 1 ) )
        
    
    def _GetXFromTimestamp( self, timestamp_ms, width_offset = 0 ):
        
        my_width = self.size().width()
        
        return int( ( my_width - width_offset ) * timestamp_ms / self._duration_ms )
        
    
    def _CurrentMediaWindowIsBad( self ):
        
        if self._media_window is None:
            
            return True
            
        
        if not QP.isValid( self._media_window ):
            
            self.ClearMedia()
            
            return True
            
        
        return False
        
    
    def _Redraw( self, painter ):
        
        # making an extra note here: do not under any circumstances query the mpv window during our paint event
        # it leads to the QBackingStore::endPaint() errors when mpv is unhappy/unloaded
        # always fetch that info and handle various error states in the TIMERAnimationUpdate and just draw cached info here
        
        ( current_frame_index, current_timestamp_ms, paused, buffer_indices )  = self._next_draw_info
        
        self.setProperty( 'playing', not paused )
        
        my_width = self.size().width()
        my_height = self.size().height()
        
        background_colour = self._qss_colours[ 'hab_background' ]
        
        if paused:
            
            background_colour = ClientGUIFunctions.GetLighterDarkerColour( background_colour )
            
        
        painter.setBackground( QG.QBrush( background_colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        #
        
        if self._show_gubbins:
            
            if buffer_indices is not None:
                
                ( start_index, rendered_to_index, end_index ) = buffer_indices
                
                if ClientRendering.FrameIndexOutOfRange( rendered_to_index, start_index, end_index ):
                    
                    rendered_to_index = start_index
                    
                
                start_x = self._GetXFromFrameIndex( start_index )
                rendered_to_x = self._GetXFromFrameIndex( rendered_to_index )
                end_x = self._GetXFromFrameIndex( end_index )
                
                if start_x != rendered_to_x:
                    
                    rendered_colour = ClientGUIFunctions.GetDifferentLighterDarkerColour( background_colour )
                    
                    if rendered_to_x > start_x:
                        
                        painter.fillRect( start_x, 0, rendered_to_x - start_x, my_height, rendered_colour )
                        
                    else:
                        
                        painter.fillRect( start_x, 0, my_width - start_x, my_height, rendered_colour )
                        
                        painter.fillRect( 0, 0, rendered_to_x, my_height, rendered_colour )
                        
                    
                
                if rendered_to_x != end_x:
                    
                    to_be_rendered_colour = ClientGUIFunctions.GetDifferentLighterDarkerColour( background_colour, 1 )
                    
                    if end_x > rendered_to_x:
                        
                        painter.fillRect( rendered_to_x, 0, end_x - rendered_to_x, my_height, to_be_rendered_colour )
                        
                    else:
                        
                        painter.fillRect( rendered_to_x, 0, my_width - rendered_to_x, my_height, to_be_rendered_colour )
                        
                        painter.fillRect( 0, 0, end_x, my_height, to_be_rendered_colour )
                        
                    
                
            
            animated_scanbar_nub_width = CG.client_controller.new_options.GetInteger( 'animated_scanbar_nub_width' )
            
            num_frames_are_useful = self._num_frames is not None and self._num_frames > 1
            
            nub_x = None
            
            if num_frames_are_useful and current_frame_index is not None:
                
                nub_x = self._GetXFromFrameIndex( current_frame_index, width_offset = animated_scanbar_nub_width )
                
            elif self._duration_ms is not None and current_timestamp_ms is not None:
                
                nub_x = self._GetXFromTimestamp( current_timestamp_ms, width_offset = animated_scanbar_nub_width )
                
            
            if nub_x is not None:
                
                painter.fillRect( nub_x, 0, animated_scanbar_nub_width, my_height, self._qss_colours[ 'hab_nub' ] )
                
            
            #
            
            if self._show_text:
                
                progress_strings = []
                
                if num_frames_are_useful:
                    
                    progress_strings.append( HydrusNumbers.ValueRangeToPrettyString( current_frame_index + 1, self._num_frames ) )
                    
                
                if current_timestamp_ms is not None:
                    
                    progress_strings.append( HydrusTime.ValueRangeToScanbarTimestampsMS( current_timestamp_ms, self._duration_ms ) )
                    
                
                s = ' - '.join( progress_strings )
                
                if len( s ) > 0:
                    
                    ( text_size, s ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, s )
                    
                    x = my_width - text_size.width() - 3
                    y = round( ( my_height - text_size.height() ) / 2 )
                    
                    ClientGUIFunctions.DrawText( painter, x, y, s )
                    
                
            
        
        #
        
        painter.setBrush( QC.Qt.BrushStyle.NoBrush )
        
        painter.setPen( QG.QPen( self._qss_colours[ 'hab_border' ] ) )
        
        painter.drawRect( 0, 0, my_width - 1, my_height - 1 )
        
    
    def _ScanToCurrentMousePos( self ):
        
        my_width = self.size().width()
        
        mouse_pos = self.mapFromGlobal( QG.QCursor.pos() )
        
        animated_scanbar_nub_width = CG.client_controller.new_options.GetInteger( 'animated_scanbar_nub_width' )
        
        compensated_x_position = mouse_pos.x() - ( animated_scanbar_nub_width / 2 )
        
        proportion = ( compensated_x_position ) / ( my_width - animated_scanbar_nub_width )
        
        proportion = max( proportion, 0.0 )
        proportion = min( 1.0, proportion )
        
        self.update()
        
        if isinstance( self._media_window, Animation ):
            
            current_frame_index = int( proportion * ( self._num_frames - 1 ) + 0.5 )
            
            self._media_window.GotoFrame( current_frame_index )
            
        elif isinstance( self._media_window, ( ClientGUIMPV.MPVWidget, QtMediaPlayer ) ):
            
            time_index_ms = int( proportion * self._duration_ms )
            
            self._media_window.Seek( time_index_ms )
            
        
    
    def ClearMedia( self ):
        
        self._media_window = None
        self._show_gubbins = True
        
        CG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
        
        self.update()
        
    
    def DoingADrag( self ):
        
        return self._currently_in_a_drag
        
    
    def mouseMoveEvent( self, event ):
        
        if self._CurrentMediaWindowIsBad():
            
            return
            
        
        CC.CAN_HIDE_MOUSE = False
        
        if self._currently_in_a_drag:
            
            if event.buttons() == QC.Qt.MouseButton.NoButton:
                
                self._currently_in_a_drag = False
                
                return
                
            
            self._ScanToCurrentMousePos()
            
        
    
    def mousePressEvent( self, event ):
        
        if self._CurrentMediaWindowIsBad():
            
            return
            
        
        CC.CAN_HIDE_MOUSE = False
        
        self._it_was_playing_before_drag = not self._media_window.IsPaused()
        
        if self._it_was_playing_before_drag:
            
            self._media_window.Pause()
            
        
        self._currently_in_a_drag = True
        
        self._ScanToCurrentMousePos()
        
    
    def mouseReleaseEvent( self, event ):
        
        CC.CAN_HIDE_MOUSE = True
        
        if self._currently_in_a_drag:
            
            if self._it_was_playing_before_drag:
                
                if not self._CurrentMediaWindowIsBad():
                    
                    self._media_window.Play()
                    
                
            
            self._currently_in_a_drag = False
            
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        if self._CurrentMediaWindowIsBad() or self._next_draw_info is None:
            
            self._DrawBlank( painter )
            
            self._next_draw_info = None
            
        else:
            
            self._Redraw( painter )
            
        
        self._last_drawn_info = self._next_draw_info
        
    
    def setGubbinsVisible( self, show: bool ):
        
        self._show_gubbins = show
        
        self._DoAnimationStatusUpdate()
        
        self.update()
        
    
    def SetMediaAndWindow( self, media, media_window, ):
        
        self._media_window = media_window
        
        num_frames = media.GetNumFrames()
        
        if num_frames is None:
            
            self._num_frames = num_frames
            
        else:
            
            self._num_frames = max( num_frames, 1 )
        
        duration_ms = media.GetDurationMS()
        
        if duration_ms is None and isinstance(media_window, Animation):
            
            duration_ms = media_window.GetDurationMS()
            
        
        self._duration_ms = max( duration_ms, 1 )
        
        self._currently_in_a_drag = False
        self._it_was_playing_before_drag = False
        
        CG.client_controller.gui.RegisterAnimationUpdateWindow( self )
        
        self._next_draw_info = None
        
        self._show_gubbins = True
        
        self._DoAnimationStatusUpdate()
        
        self.update()
        
    
    def SetShowText( self, show_text: bool ):
        
        self._show_text = show_text
        
    
    def TIMERAnimationUpdate( self ):
        
        if self._CurrentMediaWindowIsBad():
            
            self.ClearMedia()
            
            return
            
        
        self._DoAnimationStatusUpdate()
        
    
    def get_hab_background( self ):
        
        return self._qss_colours[ 'hab_background' ]
        
    
    def get_hab_border( self ):
        
        return self._qss_colours[ 'hab_border' ]
        
    
    def get_hab_nub( self ):
        
        return self._qss_colours[ 'hab_nub' ]
        
    
    def set_hab_background( self, colour ):
        
        self._qss_colours[ 'hab_background' ] = colour
        
    
    def set_hab_border( self, colour ):
        
        self._qss_colours[ 'hab_border' ] = colour
        
    
    def set_hab_nub( self, colour ):
        
        self._qss_colours[ 'hab_nub' ] = colour
        
    
    hab_border = QC.Property( QG.QColor, get_hab_border, set_hab_border )
    hab_background = QC.Property( QG.QColor, get_hab_background, set_hab_background )
    hab_nub = QC.Property( QG.QColor, get_hab_nub, set_hab_nub )
    

# cribbing from here https://doc.qt.io/qt-5/layout.html#how-to-write-a-custom-layout-manager
class MediaContainerLayout( QW.QLayout ):
    
    def __init__( self, static_image ):
        
        super().__init__()
        
        self._static_image = static_image
        
        self._layout_items = [ static_image ]
        
    

class MediaContainer( QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    readyForNeighbourPrefetch = QC.Signal()
    
    zoomChanged = QC.Signal( int, float )
    
    def __init__( self, parent, canvas_type, background_colour_generator, additional_event_filter: QC.QObject ):
        
        super().__init__( parent )
        
        self._canvas_type = canvas_type
        
        if HC.PLATFORM_MACOS and not HG.macos_antiflicker_test:
            
            # does modern macOS still go 100% CPU when this is off?
            # yes :^(
            # try again with more layout tech on the full canvas
            
            self.setAttribute( QC.Qt.WidgetAttribute.WA_OpaquePaintEvent, True )
            
        
        self._background_colour_generator = background_colour_generator
        
        self.setSizePolicy( QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Fixed )
        
        self._media = None
        self._show_action = CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW
        self._start_paused = False
        self._start_with_embed = False
        
        self._current_zoom = 1.0
        
        self._zoom_types_to_zooms = {
            MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE : 1.0,
            MEDIA_VIEWER_ZOOM_TYPE_CANVAS : 1.0,
            MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO : 1.0,
            MEDIA_VIEWER_ZOOM_TYPE_FILL_X : 1.0,
            MEDIA_VIEWER_ZOOM_TYPE_FILL_Y : 1.0,
            MEDIA_VIEWER_ZOOM_TYPE_100 : 1.0
        }
        
        self._current_zoom_type = self._GetDefaultZoomType()
        
        self._media_window = None
        
        self._embed_button = EmbedButton( self, self._background_colour_generator )
        self._embed_button_widget_event_filter = QP.WidgetEventFilter( self._embed_button )
        self._embed_button_widget_event_filter.EVT_LEFT_DOWN( self.EventEmbedButton )
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
        self.setMouseTracking( True )
        
        self._additional_event_filter = additional_event_filter
        
        self._animation_window = Animation( self, self._canvas_type, self._background_colour_generator )
        
        self._static_image_window = StaticImage( self, self._canvas_type, self._background_colour_generator )
        
        self._static_image_window.readyForNeighbourPrefetch.connect( self.readyForNeighbourPrefetch )
        
        self._controls_bar = QW.QWidget( self )
        self._controls_bar_show_full = True
        
        # We need this to force-fill some blanks at times
        self.setAutoFillBackground( True )
        
        self._animation_bar = AnimationBar( self._controls_bar )
        self._volume_control = ClientGUIMediaControls.VolumeControl( self._controls_bar, self._canvas_type, direction = 'up' )
        
        self._volume_control.setCursor( QC.Qt.CursorShape.ArrowCursor )
        
        #
        
        hbox = QP.HBoxLayout( margin = 0, spacing = 0 )
        
        QP.AddToLayout( hbox, self._animation_bar, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( hbox, self._volume_control, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._controls_bar.setLayout( hbox )
        
        #
        
        self._animation_window.hide()
        
        self._controls_bar.hide()
        
        self._static_image_window.hide()
        self._embed_button.hide()
        
        self.hide()
        
        CG.client_controller.sub( self, 'Pause', 'pause_all_media' )
        
    
    def _DestroyOrHideThisMediaWindow( self, media_window ):
        
        if media_window is not None:
            
            launch_media_viewer_classes = ( Animation, ClientGUIMPV.MPVWidget, StaticImage, QtMediaPlayer )
            
            media_window.removeEventFilter( self._additional_event_filter )
            
            if isinstance( media_window, launch_media_viewer_classes ):
                
                try:
                    
                    media_window.launchMediaViewer.disconnect( self.launchMediaViewer )
                    
                except RuntimeError:
                    
                    pass # lmao, weird 'Failed to disconnect signal launchMediaViewer()' error I couldn't figure out, I guess some out-of-order deleteLater gubbins
                    
                
                media_window.ClearMedia()
                
                if isinstance( media_window, StaticImage ):
                    
                    media_window.repaint()
                    
                
                media_window.hide()
                
                if isinstance( media_window, ClientGUIMPV.MPVWidget ):
                    
                    CG.client_controller.gui.ReleaseMPVWidget( media_window )
                    
                
                if isinstance( media_window, QtMediaPlayer ):
                    
                    CG.client_controller.gui.ReleaseQtMediaPlayer( media_window )
                    
                
            else:
                
                media_window.deleteLater()
                
            
        
    
    def _GetDefaultZoomType( self ):
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            return CG.client_controller.new_options.GetInteger( 'media_viewer_default_zoom_type_override' )
            
        else:
            
            return CG.client_controller.new_options.GetInteger( 'preview_default_zoom_type_override' )
            
        

    def _GetMaxZoomDimension( self ):
        
        if self._show_action in ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER ) or isinstance( self._media_window, Animation ):
            
            return 8000
            
        else:
            
            return 32000
            
        
    
    def _MakeMediaWindow( self ):
        
        old_media_window = self._media_window
        
        do_neighbour_prefetch_emit = True
        
        if self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV and not ClientGUIMPV.MPV_IS_AVAILABLE:
            
            self._show_action = CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON
            
            HydrusData.ShowText( 'MPV is not available!' )
            
        
        if self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER and QtInit.WE_ARE_QT5:
            
            self._show_action = CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON
            
            HydrusData.ShowText( 'Qt Media Player is only available on Qt6!' )
            
        
        if self._show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            raise Exception( 'This media should not be shown in the media viewer!' )
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON:
            
            self._media_window = OpenExternallyPanel( self, self._media )
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE:
            
            if self._media.IsStaticImage():
                
                if None in self._media.GetResolution():
                    
                    raise Exception( 'This media has no resolution!' )
                    
                
                if isinstance( self._media_window, StaticImage ):
                    
                    self._media_window.hide()
                    
                else:
                    
                    self._media_window = self._static_image_window
                    
                
                self._media_window.SetMedia( self._media )
                
                do_neighbour_prefetch_emit = False
                
            else:
                
                if isinstance( self._media_window, Animation ):
                    
                    self._media_window.hide()
                    
                else:
                    
                    self._media_window = self._animation_window
                    
                
                self._media_window.SetMedia( self._media, start_paused = self._start_paused )
                
                self._media_window.lower()
                
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV:
            
            self._media_window = CG.client_controller.gui.GetMPVWidget( self )
            
            self._media_window.SetCanvasType( self._canvas_type )
            
            self._media_window.SetMedia( self._media, start_paused = self._start_paused )
            
            self._media_window.lower()
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER:
            
            self._media_window = QtMediaPlayer( self, self._canvas_type, self._background_colour_generator )
            
            self._media_window.SetMedia( self._media, start_paused = self._start_paused )
            
            self._media_window.lower()
            
        
        if ShouldHaveAnimationBar( self._media, self._show_action ):
            
            self._animation_bar.SetMediaAndWindow( self._media, self._media_window )
            
        else:
            
            self._animation_bar.ClearMedia()
            
        
        self._ShowHideControlBar()
        
        media_window_changed = old_media_window != self._media_window
        
        # this has to go after setcanvastype on the mpv window so the filters are in the correct order
        if media_window_changed:
            
            self._media_window.installEventFilter( self._additional_event_filter )
            
            launch_media_viewer_classes = ( Animation, ClientGUIMPV.MPVWidget, StaticImage, QtMediaPlayer )
            
            if isinstance( self._media_window, launch_media_viewer_classes ):
                
                self._media_window.launchMediaViewer.connect( self.launchMediaViewer )
                
            
            self._DestroyOrHideThisMediaWindow( old_media_window )
            
            # this forces a flush of the last valid background bmp, so we don't get a flicker of a file from five files ago when we last saw a static image
            self.repaint()
            
        
        if do_neighbour_prefetch_emit:
            
            self.readyForNeighbourPrefetch.emit()
            
        
    
    def _MoveDelta( self, delta: QC.QPoint ):
        
        if delta.isNull():
            
            return
            
        
        self.move( self.pos() + delta )
        
    
    def _SetZoom( self, zoom: float, move_delta = None ):
        
        self._current_zoom = zoom
        
        size_hint = self.sizeHint()
        
        if self.size() != size_hint:
            
            if move_delta is not None and not move_delta.isNull():
                
                if isinstance( self._media_window, ClientGUIMPV.MPVWidget ) and CG.client_controller.new_options.GetBoolean( 'do_not_setgeometry_on_an_mpv' ):
                    
                    self._MoveDelta( move_delta )
                    self.resize( size_hint )
                    
                else:
                    
                    self.setGeometry( QC.QRect( self.pos() + move_delta, size_hint ) )
                    
                
            else:
                
                self.resize( size_hint )
                
            
            self._SizeAndPositionChildren()
            
            if HC.PLATFORM_MACOS:
                
                self.update()
                
            
        else:
            
            if move_delta is not None:
                
                self._MoveDelta( move_delta )
                
            
        
        self.zoomChanged.emit( self._current_zoom_type, self._current_zoom )
        
    
    def _ShowHideControlBar( self ):
        
        is_near = False
        show_small_instead_of_hiding = None
        force_show = False
        
        if not ShouldHaveAnimationBar( self._media, self._show_action ):
            
            should_show_controls = False
            
        else:
            
            is_near = self.MouseIsNearAnimationBar()
            show_small_instead_of_hiding = CG.client_controller.new_options.GetNoneableInteger( 'animated_scanbar_hide_height' ) is not None
            force_show = self._volume_control.PopupIsVisible() or self._animation_bar.DoingADrag() or CG.client_controller.new_options.GetBoolean( 'force_animation_scanbar_show' )
            
            should_show_controls = is_near or show_small_instead_of_hiding or force_show
            
        
        if should_show_controls:
            
            should_show_full = is_near or force_show
            
            if should_show_full != self._controls_bar_show_full:
                
                self._controls_bar_show_full = should_show_full
                
                self._animation_bar.SetShowText( self._controls_bar_show_full )
                
                self._volume_control.setEnabled( self._controls_bar_show_full )
                
                self._SizeAndPositionChildren()
                
                # TODO: investigate this
                # ok we do seem to have a flicker here, most obvious when going from small to full size on a quick animation. we get a frame of where the top half was before. some bitmap memory issue I guess
                # a forced repaint of the animation bar here does not fix it, so I suspect this is related to the disconnected layout nonsense I am doing
                # TODO: if and when fixed, investigate if setGubbinsVisible is still a useful thing
                
            
            do_layout = False
            
            if self._controls_bar.isHidden():
                
                self._controls_bar.setVisible( True )
                self._controls_bar.raise_()
                
                self._animation_bar.setGubbinsVisible( True )
                self._animation_bar.repaint() # this is probably not needed
                
                do_layout = True
                
            
            should_show_volume = self.ShouldHaveVolumeControl()
            
            volume_currently_visible = not self._volume_control.isHidden()
            
            if volume_currently_visible != should_show_volume:
                
                self._volume_control.setVisible( should_show_volume )
                
                do_layout = True
                
            
            self._controls_bar.layout()
            
        else:
            
            if not self._controls_bar.isHidden():
                
                # ok, repaint here forces a clear paint event NOW, before we hide.
                # this ensures that when we show again, we won't have the nub in the wrong place for a frame before it repaints
                # we'll have no nub, but this is less noticeable
                
                self._animation_bar.setGubbinsVisible( False )
                self._animation_bar.repaint() # this is probably not needed
                
                self._controls_bar.setVisible( False )
                
                self._volume_control.setVisible( False )
                
                self._controls_bar.layout() # this is probably not needed
                
            
        
    
    def _SizeAndPositionChildren( self ):
        
        if self._media is not None:
            
            self._embed_button.setFixedSize( self.size() )
            self._embed_button.move( QC.QPoint( 0, 0 ) )
            
            if self._media_window is not None:
                
                self._media_window.setFixedSize( self.size() )
                self._media_window.move( QC.QPoint( 0, 0 ) )
                
            
            controls_bar_rect = self.GetIdealControlsBarRect( full_size = self._controls_bar_show_full )
            
            if controls_bar_rect.size() != self._controls_bar.size():
                
                self._controls_bar.setFixedSize( controls_bar_rect.size() )
                
            
            self._controls_bar.move( controls_bar_rect.topLeft() )
            
        
    
    def _TryToChangeZoom( self, new_zoom, zoom_center_type_override = None ):
        
        if not self.IsZoomable():
            
            return
            
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        my_dpr = self.devicePixelRatio()
        
        new_media_window_size = CalculateMediaContainerSize( self._media, my_dpr, new_zoom, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE )
        
        new_my_width = new_media_window_size.width()
        new_my_height = new_media_window_size.height()
        
        max_zoom_dimension = self._GetMaxZoomDimension()
        
        if new_my_width > max_zoom_dimension or new_my_height > max_zoom_dimension:
            
            limit_max_zoom_types_to_zooms = CalculateCanvasZooms( QC.QSize( max_zoom_dimension, max_zoom_dimension ), self._canvas_type, my_dpr, self._media, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE )
            
            new_zoom = limit_max_zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ]
            
            new_media_window_size = CalculateMediaContainerSize( self._media, my_dpr, new_zoom, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE )
            
            new_my_width = new_media_window_size.width()
            new_my_height = new_media_window_size.height()
            
        
        if new_zoom == self._current_zoom:
            
            # to handle a change in zoom type but no zoom
            self.zoomChanged.emit( self._current_zoom_type, self._current_zoom )
            
            return
            
        
        canvas_size = self.parentWidget().size()
        
        old_size_bigger = canvas_size.width() < my_width or canvas_size.height() < my_height
        new_size_fits = canvas_size.width() >= new_my_width and canvas_size.height() >= new_my_height
        
        #
        
        zoom_position_delta = QC.QPoint( 0, 0 )
        
        if my_width > 0 and my_height > 0:
            
            if zoom_center_type_override is None:
                
                zoom_center_type = CG.client_controller.new_options.GetInteger( 'media_viewer_zoom_center' )
                
            else:
                
                zoom_center_type = zoom_center_type_override
                
            
            my_pos = self.pos()
            
            # viewer center is the default
            zoom_centerpoint = QC.QPoint( canvas_size.width() // 2, canvas_size.height() // 2 )
            
            if zoom_center_type == ZOOM_CENTERPOINT_MEDIA_CENTER:
                
                zoom_centerpoint = my_pos + QC.QPoint( my_width // 2, my_height // 2 )
                
            elif zoom_center_type == ZOOM_CENTERPOINT_MEDIA_TOP_LEFT:
                
                zoom_centerpoint = my_pos
                
            elif zoom_center_type == ZOOM_CENTERPOINT_MOUSE:
                
                mouse_pos = self.parentWidget().mapFromGlobal( QG.QCursor.pos() )
                
                if self.parent().rect().contains( mouse_pos ):
                    
                    zoom_centerpoint = mouse_pos
                    
                
            
            # probably a simpler way to calc this, but hey
            widths_centerpoint_is_from_pos = ( zoom_centerpoint.x() - my_pos.x() ) / my_width
            heights_centerpoint_is_from_pos = ( zoom_centerpoint.y() - my_pos.y() ) / my_height
            
            zoom_width_delta = my_width - new_my_width
            zoom_height_delta = my_height - new_my_height
            
            zoom_position_delta = QC.QPoint( int( zoom_width_delta * widths_centerpoint_is_from_pos ), int( zoom_height_delta * heights_centerpoint_is_from_pos ) )
            
        
        #
        
        # ok we had a crazy problem where after showing and hiding an mpv window, some rendering flag gets set which caused move/resize calls to be repainted immediately after call, causing move/resize flicker
        # so now we set the geometry in one weird trick, and it seems Qt at the C++ level wraps it into the same update with that mystery flag on
        self._SetZoom( new_zoom, move_delta = zoom_position_delta )
        
        self.RescueIfOffScreen()
        
        # due to the foolish 'giganto window' system for large zooms, some auto-update stuff doesn't work right if the convas rect is contained by the media rect, so do a refresh here
        if new_zoom > self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ]:
            
            self.update()
            
        
    
    def BeginDrag( self ):
        
        self.parentWidget().BeginDrag()
        
    
    def ClearMedia( self ):
        
        self._media = None
        
        self._animation_bar.ClearMedia()
        
        self._controls_bar.hide()
        
        self._DestroyOrHideThisMediaWindow( self._media_window )
        
        self._media_window = None
        
        CG.client_controller.gui.UnregisterUIUpdateWindow( self )
        
        self.hide()
        
    
    def CurrentlyPresentingMediaWithDuration( self ):
        
        return isinstance( self._media_window, ( Animation, ClientGUIMPV.MPVWidget, QtMediaPlayer ) )
        
    
    def DoEdgePan( self, pan_type: int ):
        
        if self._media is None:
            
            return
            
        
        canvas_size = self.parentWidget().size()
        my_size = self.size()
        my_pos = self.pos()
        
        delta_x = 0
        delta_y = 0
        
        if pan_type == CAC.SIMPLE_PAN_TOP_EDGE:
            
            delta_y = - my_pos.y()
            
        elif pan_type == CAC.SIMPLE_PAN_LEFT_EDGE:
            
            delta_x = - my_pos.x()
            
        elif pan_type == CAC.SIMPLE_PAN_BOTTOM_EDGE:
            
            delta_y = canvas_size.height() - ( my_pos.y() + my_size.height() )
            
        elif pan_type == CAC.SIMPLE_PAN_RIGHT_EDGE:
            
            delta_x = canvas_size.width() - ( my_pos.x() + my_size.width() )
            
        elif pan_type == CAC.SIMPLE_PAN_VERTICAL_CENTER:
            
            delta_y = round( canvas_size.height() / 2 ) - ( my_pos.y() + round( my_size.height() / 2 ) )
            
        elif pan_type == CAC.SIMPLE_PAN_HORIZONTAL_CENTER:
            
            delta_x = round( canvas_size.width() / 2 ) - ( my_pos.x() + round( my_size.width() / 2 ) )
            
        
        delta = QC.QPoint( delta_x, delta_y )
        
        self._MoveDelta( delta )
        
    
    def DoManualPan( self, delta_x_step, delta_y_step ):
        
        if self._media is None:
            
            return
            
        
        canvas_size = self.parentWidget().size()
        my_size = self.size()
        
        x_pan_distance = min( canvas_size.width(), my_size.width() ) // 12
        y_pan_distance = min( canvas_size.height(), my_size.height() ) // 12
        
        delta_x = delta_x_step * x_pan_distance
        delta_y = delta_y_step * y_pan_distance
        
        delta = QC.QPoint( delta_x, delta_y )
        
        self._MoveDelta( delta )
        
    
    def EventEmbedButton( self, event ):
        
        self._embed_button.hide()
        
        self._MakeMediaWindow()
        
        self._SizeAndPositionChildren()
        
        if self._media_window is not None:
            
            self._media_window.show()
            
        
    
    def GetCanvasZoom( self ) -> float:
        
        return self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ]
        
    
    def GetCurrentZoom( self ) -> float:
        
        return self._current_zoom
        
    
    def GetIdealControlsBarRect( self, full_size = True ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        if full_size:
            
            animated_scanbar_height = CG.client_controller.new_options.GetInteger( 'animated_scanbar_height' )
            
        else:
            
            animated_scanbar_height = CG.client_controller.new_options.GetNoneableInteger( 'animated_scanbar_hide_height' )
            
            if animated_scanbar_height is None:
                
                animated_scanbar_height = 5
                
            
        
        return QC.QRect(
            QC.QPoint( 0, my_height - animated_scanbar_height ),
            QC.QSize( my_width, animated_scanbar_height )
    )
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        if self._media is not None:
            
            if ShouldHaveAnimationBar( self._media, self._show_action ):
                
                if isinstance( self._media_window, Animation ):
                    
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
                    
                elif isinstance( self._media_window, ClientGUIMPV.MPVWidget ):
                    
                    self._media_window.GotoPreviousOrNextFrame( direction )
                    
                
            
        
    
    def HasPlayedOnceThrough( self ):
        
        if self.CurrentlyPresentingMediaWithDuration():
            
            return self._media_window.HasPlayedOnceThrough()
            
        
        return True
        
    
    def IsAtMaxZoom( self ):
        
        possible_zooms = CG.client_controller.new_options.GetMediaZooms()
        
        max_zoom = max( possible_zooms )
        
        max_zoom_dimension = self._GetMaxZoomDimension()
        
        return self._current_zoom == max_zoom or self.width() == max_zoom_dimension or self.height() == max_zoom_dimension
        
    
    def IsPaused( self ):
        
        if self.CurrentlyPresentingMediaWithDuration():
            
            return self._media_window.IsPaused()
            
        
        return False
        
    
    def IsZoomable( self ):
        
        if self._media is None:
            
            return False
            
        
        return self._show_action not in ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW )
        
    
    def minimumSizeHint( self ) -> QC.QSize:
        
        return self.sizeHint()
        
    
    def MouseIsNearAnimationBar( self ):
        
        if self._media is None:
            
            return False
            
        
        if ShouldHaveAnimationBar( self._media, self._show_action ):
            
            canvas_widget = self.parentWidget()
            
            if not ClientGUIFunctions.MouseIsOverWidget( canvas_widget ):
                
                return False
                
            
            # there's some minor update stuff here now the scanbar can be hidden. its geometry may not update until later, so we need to map coordinates from widgets we know are in view instead!
            
            container_mouse_pos = self.mapFromGlobal( QG.QCursor.pos() )
            
            controls_bar_rect = self.GetIdealControlsBarRect()
            
            buffer = 100
            
            test_rect = controls_bar_rect.adjusted( -buffer // 2, -buffer, buffer // 2, buffer // 5 )
            
            return test_rect.contains( container_mouse_pos )
            
        
        return False
        
    
    def MoveDelta( self, delta: QC.QPoint ):
        
        self._MoveDelta( delta )
        
    
    def Pause( self ):
        
        if self._media is not None:
            
            if self.CurrentlyPresentingMediaWithDuration():
                
                self._media_window.Pause()
                
            
        
    
    def PausePlay( self ):
        
        if self._media is not None:
            
            if self.CurrentlyPresentingMediaWithDuration():
                
                self._media_window.PausePlay()
                
            
        
    
    def RescueIfOffScreen( self ):
        
        my_ideal_size = self.sizeHint()
        
        canvas_rect = self.parentWidget().rect()
        ideal_media_rect = QC.QRect( self.pos(), my_ideal_size )
        
        if not canvas_rect.intersects( ideal_media_rect ):
            
            # up/down
            
            height_buffer = min( ideal_media_rect.height(), self.height() // 5 )
            
            if ideal_media_rect.bottom() < canvas_rect.top():
                
                ideal_media_rect.moveBottom( canvas_rect.top() + height_buffer )
                
            elif ideal_media_rect.top() > canvas_rect.bottom():
                
                ideal_media_rect.moveTop( canvas_rect.bottom() - height_buffer )
                
            
            # left/right
            
            width_buffer = min( ideal_media_rect.width(), self.width() // 5 )
            
            if ideal_media_rect.right() < canvas_rect.left():
                
                ideal_media_rect.moveRight( canvas_rect.left() + width_buffer )
                
            elif ideal_media_rect.left() > canvas_rect.right():
                
                ideal_media_rect.moveLeft( canvas_rect.right() - width_buffer )
                
            
        
        ideal_pos = ideal_media_rect.topLeft()
        
        if ideal_pos != self.pos():
            
            self.move( ideal_pos )
            
        
    
    def ResetCenterPosition( self ):
        
        if self._media is None:
            
            return
            
        
        canvas_size = self.parentWidget().size()
        
        ideal_size = self.sizeHint()
        
        x = ( canvas_size.width() - ideal_size.width() ) // 2
        y = ( canvas_size.height() - ideal_size.height() ) // 2
        
        ideal_pos =  QC.QPoint( x, y )
        
        if ideal_pos != self.pos():
            
            self.move( ideal_pos )
            
        
    
    def resizeEvent( self, event ):
        
        if self._media is not None:
            
            self._SizeAndPositionChildren()
            
        
    
    def SeekDelta( self, direction, duration_ms ):
        
        if self._media is not None:
            
            if self.CurrentlyPresentingMediaWithDuration():
                
                self._media_window.SeekDelta( direction, duration_ms )
                
            
        
    
    def SetBackgroundColourGenerator( self, background_colour_generator ):
        
        self._background_colour_generator = background_colour_generator
        
        self._embed_button.SetBackgroundColourGenerator( self._background_colour_generator )
        self._animation_window.SetBackgroundColourGenerator( self._background_colour_generator )
        self._static_image_window.SetBackgroundColourGenerator( self._background_colour_generator )
        
    
    def SetMedia( self, media: ClientMedia.MediaSingleton, maintain_zoom, maintain_zoom_type, maintain_pan, start_paused = None ):
        
        previous_media = self._media
        
        self._media = media
        
        ( self._show_action, self._start_paused, self._start_with_embed ) = ClientMedia.GetShowAction( self._media.GetMediaResult(), self._canvas_type )
        
        if start_paused is not None:
            
            self._start_paused = start_paused
            
        
        if self._show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            self._show_action = CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON
            
        
        if self._start_with_embed:
            
            self._animation_bar.ClearMedia()
            
            self._controls_bar.hide()
            
            self._DestroyOrHideThisMediaWindow( self._media_window )
            
            self._media_window = None
            
            self._embed_button.SetMedia( self._media )
            
            self._embed_button.show()
            
        else:
            
            self._embed_button.hide()
            
            self._MakeMediaWindow()
            
        
        if maintain_zoom and previous_media is not None:
            
            self.ZoomMaintainingZoom( previous_media )
            
        elif maintain_zoom_type:
            
            self.ZoomToZoomType()
            
        else:
            
            self.ZoomReinit()
            
        
        if previous_media is None or not maintain_pan:
            
            self.ResetCenterPosition()
            
        
        self._SizeAndPositionChildren()
        
        if self._media_window is not None:
            
            self._media_window.show()
            
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
        self.show()
        
    
    def ShouldHaveVolumeControl( self ):
        
        if self._media is None:
            
            return False
            
        
        return isinstance( self._media_window, ClientGUIMPV.MPVWidget ) and self._media.HasAudio()
        
    
    def sizeHint(self) -> QC.QSize:
        
        if self._media is None or self._show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            return QC.QSize( 0, 0 )
            
        
        my_dpr = self.devicePixelRatio()
        
        return CalculateMediaContainerSize( self._media, my_dpr, self._current_zoom, self._show_action )
        
    
    def SizeSelfToMedia( self ):
        
        if self._media is None:
            
            return
            
        
        media_size = self._media_window.size()
        media_width = media_size.width()
        media_height = media_size.height()
        
        if media_width is None or media_height is None:
            
            return
            
        
        media_win_pos = self._media_window.mapToGlobal( QC.QPoint( 0, 0 ) )
        
        frame_geometry = self.window().frameGeometry()
        window_geometry = self.window().geometry()
        title_bar_offset = frame_geometry.top() - window_geometry.top()
        
        adjusted_pos = QC.QPoint(media_win_pos.x(), media_win_pos.y() + title_bar_offset)
        
        self.window().showNormal()
        
        self.window().resize( media_width, media_height )
        self.window().move( adjusted_pos )
        
        self.ResetCenterPosition()
        self._SizeAndPositionChildren()
        
    
    def StopForSlideshow( self, value ):
        
        if self.CurrentlyPresentingMediaWithDuration():
            
            self._media_window.StopForSlideshow( value )
            
        
    
    def ZoomIn( self, zoom_center_type_override = None ):
        
        if not self.IsZoomable():
            
            return
            
        
        ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = CG.client_controller.new_options.GetMediaZoomOptions( self._media.GetMime() )
        
        possible_zooms = CG.client_controller.new_options.GetMediaZooms()
        
        if exact_zooms_only:
            
            exact_zoom = 1.0
            
            if exact_zoom <= self._current_zoom:
                
                while exact_zoom <= self._current_zoom:
                    
                    exact_zoom *= 2
                    
                
            else:
                
                while exact_zoom / 2 > self._current_zoom:
                    
                    exact_zoom /= 2
                    
                
            
            max_zoom = max( possible_zooms )
            
            if exact_zoom > max_zoom:
                
                return
                
            
            possible_zooms = [ exact_zoom ]
            
        
        possible_zooms.append( self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ] )
        
        bigger_zooms = [ zoom for zoom in possible_zooms if zoom > self._current_zoom ]
        
        if len( bigger_zooms ) > 0:
            
            new_zoom = min( bigger_zooms )
            
            self._TryToChangeZoom( new_zoom, zoom_center_type_override = zoom_center_type_override )
            
        
    
    def ZoomMaintainingZoom( self, previous_media: ClientMedia.MediaSingleton ):
        
        if self._media is None:
            
            return
            
        
        if previous_media is None or not previous_media.HasUsefulResolution() or not self._media.HasUsefulResolution():
            
            self.ZoomReinit()
            
            return
            
        
        # set up canvas zoom
        
        canvas_size = self.parentWidget().size()
        
        my_dpr = self.devicePixelRatio()
        
        ( media_show_action, media_start_paused, media_start_with_embed ) = ClientMedia.GetShowAction( self._media.GetMediaResult(), self._canvas_type )
        
        if media_show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            self.ZoomReinit()
            
            return
            
        
        self._zoom_types_to_zooms = CalculateCanvasZooms( canvas_size, self._canvas_type, my_dpr, self._media, media_show_action )
        
        previous_current_zoom = self._current_zoom
        
        ( previous_show_action, previous_start_paused, previous_start_with_embed ) = ClientMedia.GetShowAction( previous_media.GetMediaResult(), self._canvas_type )
        
        previous_zoom_types_to_zooms = CalculateCanvasZooms( canvas_size, self._canvas_type, my_dpr, previous_media, previous_show_action )
        
        # previously, we always matched width, but this causes a problem in dupe viewer when B has a little watermark on the bottom, spilling below bottom of screen
        # I think in future we will have more options regarding all this, and this method will change significantly
        # however for now we really just want a hardcoded ok solution for all situations, so let's just hook on default canvas zoom situation
        
        ( previous_width, previous_height ) = CalculateMediaSize( previous_media, self._current_zoom )
        
        ( previous_media_100_width, previous_media_100_height ) = previous_media.GetResolution()
        ( current_media_100_width, current_media_100_height ) = self._media.GetResolution()
        
        width_locked_zoom = previous_width / current_media_100_width
        height_locked_zoom = previous_height / current_media_100_height
        
        width_locked_size = CalculateMediaContainerSize( self._media, my_dpr, width_locked_zoom, media_show_action )
        height_locked_size = CalculateMediaContainerSize( self._media, my_dpr, height_locked_zoom, media_show_action )
        
        # if landscape, go height, portrait, go width
        if previous_media_100_width > previous_media_100_height and current_media_100_width > current_media_100_height:
            
            lock_height = True
            
        elif previous_media_100_width < previous_media_100_height and current_media_100_width < current_media_100_height:
            
            lock_height = False
            
        else:
            
            # for weird stuff, we'll choose the smaller of the two ratios
            
            width_difference = max( previous_media_100_width, current_media_100_width ) / min( previous_media_100_width, current_media_100_width )
            height_difference = max( previous_media_100_height, current_media_100_height ) / min( previous_media_100_height, current_media_100_height )
            
            lock_height = height_difference <= width_difference
            
        
        # however we don't want to accidentally zoom in if the media we are switching to is larger. it'll spill over the bottom of the canvas
        # therefore let's have a little safety check
        
        if previous_current_zoom == previous_zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE ] and previous_current_zoom <= previous_zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ] * 1.05:
            
            # we were looking at the default zoom, near or at canvas edge(s), probably hadn't zoomed before switching comparison
            # we want to make sure our comparison does not spill over the canvas edge
            
            close_to_vertical_edge = canvas_size.height() * 0.95 <= self.height() <= canvas_size.height() * 1.05
            vertical_spillover_could_be_deceptive = self.height() < width_locked_size.height() < self.height() * 1.1
            
            # locking by width will spill over bottom of screen
            if close_to_vertical_edge and vertical_spillover_could_be_deceptive:
                
                lock_height = True
                
            
            close_to_horizontal_edge = canvas_size.width() * 0.95 <= self.width() <= canvas_size.width() * 1.05
            horizontal_spillover_could_be_deceptive = self.width() < height_locked_size.width() < self.width() * 1.1
            
            # locking by height will spill over right of screen
            if close_to_horizontal_edge and horizontal_spillover_could_be_deceptive:
                
                lock_height = False
                
            
        
        if lock_height:
            
            current_zoom = height_locked_zoom
            
        else:
            
            current_zoom = width_locked_zoom
            
        
        self._SetZoom( current_zoom )
        
    
    def Zoom100( self, zoom_center_type_override = None ):
        
        self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_100
        
        self._TryToChangeZoom( 1.0, zoom_center_type_override = zoom_center_type_override )
        
    
    def ZoomCanvas( self, zoom_center_type_override = None ):
        
        self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_CANVAS

        self._TryToChangeZoom( self._zoom_types_to_zooms[ self._current_zoom_type ], zoom_center_type_override = zoom_center_type_override )
        
    
    def ZoomCanvasFillX( self, zoom_center_type_override = None ):
        
        self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_FILL_X

        self._TryToChangeZoom( self._zoom_types_to_zooms[ self._current_zoom_type ], zoom_center_type_override = zoom_center_type_override )
        
    
    def ZoomCanvasFillY( self, zoom_center_type_override = None ):
        
        self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_FILL_Y

        self._TryToChangeZoom( self._zoom_types_to_zooms[ self._current_zoom_type ], zoom_center_type_override = zoom_center_type_override )
        
    
    def ZoomCanvasFillAuto( self, zoom_center_type_override = None ):
        
        self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO

        self._TryToChangeZoom( self._zoom_types_to_zooms[ self._current_zoom_type ], zoom_center_type_override = zoom_center_type_override )
        
    
    def ZoomDefault( self, zoom_center_type_override = None ):
        
        self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE
        
        self._TryToChangeZoom( self._zoom_types_to_zooms[ self._current_zoom_type ], zoom_center_type_override = zoom_center_type_override )
        
    
    def ZoomMax( self ):
        
        if not self.IsZoomable():
            
            return
            
        
        possible_zooms = CG.client_controller.new_options.GetMediaZooms()
        
        max_zoom = max( possible_zooms )
        
        ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = CG.client_controller.new_options.GetMediaZoomOptions( self._media.GetMime() )
        
        if exact_zooms_only:
            
            exact_zoom = 1.0
            
            while exact_zoom * 2 <= max_zoom:
                
                exact_zoom *= 2
                
            
            max_zoom = exact_zoom
            
        
        new_zoom = max_zoom
        
        if self._current_zoom != new_zoom:
            
            self._TryToChangeZoom( new_zoom )
            
        
    
    def ZoomOut( self, zoom_center_type_override = None ):
        
        if not self.IsZoomable():
            
            return
            
        
        ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = CG.client_controller.new_options.GetMediaZoomOptions( self._media.GetMime() )
        
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
            
            possible_zooms = CG.client_controller.new_options.GetMediaZooms()
            
        
        possible_zooms.append( self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ] )
        
        smaller_zooms = [ zoom for zoom in possible_zooms if zoom < self._current_zoom ]
        
        if len( smaller_zooms ) > 0:
            
            new_zoom = max( smaller_zooms )
            
            self._TryToChangeZoom( new_zoom, zoom_center_type_override = zoom_center_type_override )
            
        
    
    def ZoomReinit( self ):
        
        if self._media is None:
            
            return
            
        
        canvas_size = self.parentWidget().size()
        my_dpr = self.devicePixelRatio()
        
        self._zoom_types_to_zooms = CalculateCanvasZooms( canvas_size, self._canvas_type, my_dpr, self._media, self._show_action )
        
        self._current_zoom_type = self._GetDefaultZoomType()
        
        self._SetZoom( self._zoom_types_to_zooms [ self._current_zoom_type ] )
        
    
    def ZoomSwitch( self, zoom_center_type_override = None ):
        
        if not self.IsZoomable():
            
            return
            
        
        if self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ] == 1.0 and self._current_zoom == 1.0:
            
            return
            
        
        if self._current_zoom == 1.0:
            
            new_zoom = self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ]

            self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_CANVAS
            
        else:
            
            new_zoom = 1.0
            
            self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_100
        
        self._TryToChangeZoom( new_zoom, zoom_center_type_override = zoom_center_type_override )
        
        if new_zoom <= self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ]:
            
            self.ResetCenterPosition()

    def ZoomSwitchCanvasThenFill( self, zoom_center_type_override = None ):
        
        if not self.IsZoomable():
            
            return
            
        
        if self._current_zoom == 1.0:
            
            new_zoom = self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ]

            self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_CANVAS
            
        elif self._current_zoom_type == MEDIA_VIEWER_ZOOM_TYPE_CANVAS:
            
            new_zoom = self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO ]
            
            self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_FILL_AUTO
            
        else:
            
            new_zoom = 1.0

            self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_100
            
        
        self._TryToChangeZoom( new_zoom, zoom_center_type_override = zoom_center_type_override )
        
        self.ResetCenterPosition()
        
    
    def ZoomSwitch100Max( self ):
        
        self.ZoomSwitchMax( 1.0 )
        
    
    def ZoomSwitchCanvasMax( self ):
        
        self.ZoomSwitchMax( self._zoom_types_to_zooms[ MEDIA_VIEWER_ZOOM_TYPE_CANVAS ] )
        
    
    def ZoomSwitchMax( self, switch_base: float ):
        
        if not self.IsZoomable():
            
            return
            
        
        if self._current_zoom == switch_base:
            
            possible_zooms = CG.client_controller.new_options.GetMediaZooms()
            
            max_zoom = max( possible_zooms )
            
            ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = CG.client_controller.new_options.GetMediaZoomOptions( self._media.GetMime() )
            
            if exact_zooms_only:
                
                exact_zoom = 1.0
                
                while exact_zoom * 2 <= max_zoom:
                    
                    exact_zoom *= 2
                    
                
                max_zoom = exact_zoom
                
            
            new_zoom = max_zoom

            self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_CANVAS
            
        else:
            
            new_zoom = switch_base

            self._current_zoom_type = MEDIA_VIEWER_ZOOM_TYPE_100
            
        
        self._TryToChangeZoom( new_zoom )
        
        if new_zoom == switch_base:
            
            self.ResetCenterPosition()
            
        
    def ZoomToZoomPercent ( self, new_zoom, zoom_center_type_override = None  ):
        
        self._TryToChangeZoom( new_zoom, zoom_center_type_override )
        
    
    def ZoomToZoomType( self, zoom_type = None ):
        
        if zoom_type is None:
            
            zoom_type = self._current_zoom_type
            
        
        if self._media is None:
            
            return
            
        
        # set up canvas zoom
        
        canvas_size = self.parentWidget().size()
        
        my_dpr = self.devicePixelRatio()
        
        ( media_show_action, media_start_paused, media_start_with_embed ) = ClientMedia.GetShowAction( self._media.GetMediaResult(), self._canvas_type )
        
        self._zoom_types_to_zooms = CalculateCanvasZooms( canvas_size, self._canvas_type, my_dpr, self._media, media_show_action )
        
        self._current_zoom_type = zoom_type
        
        self._SetZoom( self._zoom_types_to_zooms[ self._current_zoom_type ] )
        
    
    def TIMERUIUpdate( self ):
        
        self._ShowHideControlBar()
        
    

class EmbedButton( QW.QWidget ):
    
    def __init__( self, parent, background_colour_generator ):
        
        super().__init__( parent )
        
        self._background_colour_generator = background_colour_generator
        
        self._media = None
        
        self._thumbnail_qt_pixmap = None
        
        self.setCursor( QG.QCursor( QC.Qt.CursorShape.PointingHandCursor ) )
        
        CG.client_controller.sub( self, 'update', 'notify_new_colourset' )
        
    
    def _Redraw( self, painter ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        center_x = my_width // 2
        center_y = my_height // 2
        radius = min( 50, center_x, center_y ) - 5
        
        new_options = CG.client_controller.new_options
        
        colour = self._background_colour_generator.GetColour()
        
        painter.setBackground( QG.QBrush( colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._thumbnail_qt_pixmap is not None:
            
            scale = my_width / self._thumbnail_qt_pixmap.width()
            
            painter.setTransform( QG.QTransform().scale( scale, scale ) )
            
            painter.drawPixmap( 0, 0, self._thumbnail_qt_pixmap )
            
            painter.setTransform( QG.QTransform().scale( 1.0, 1.0 ) )
            
        
        painter.setBrush( QG.QBrush( QG.QPalette().color( QG.QPalette.ColorRole.Button ) ) )
        
        painter.drawEllipse( QC.QPointF( center_x, center_y ), radius, radius )
        
        painter.setBrush( QG.QBrush( QG.QPalette().color( QG.QPalette.ColorRole.Window ) ) )
        
        # play symbol is a an equilateral triangle
        
        triangle_side = radius * 0.8
        
        half_triangle_side = int( triangle_side // 2 )
        
        cos30 = 0.866
        
        triangle_width = triangle_side * cos30
        
        third_triangle_width = int( triangle_width // 3 )
        
        points = []
        
        points.append( QC.QPoint( center_x - third_triangle_width, center_y - half_triangle_side ) )
        points.append( QC.QPoint( center_x + third_triangle_width * 2, center_y ) )
        points.append( QC.QPoint( center_x - third_triangle_width, center_y + half_triangle_side ) )
        
        painter.drawPolygon( QG.QPolygon( points ) )
        
        #
        
        painter.setPen( QG.QPen( QG.QPalette().color( QG.QPalette.ColorRole.Shadow ) ) )

        painter.setBrush( QC.Qt.BrushStyle.NoBrush )
        
        painter.drawRect( 0, 0, my_width, my_height )
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._Redraw( painter )
        
    
    def SetBackgroundColourGenerator( self, background_colour_generator ):
        
        self._background_colour_generator = background_colour_generator
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        if self._media is None:
            
            needs_thumb = False
            
        else:
            
            needs_thumb = self._media.GetLocationsManager().IsLocal() and self._media.GetMime() in HC.MIMES_WITH_THUMBNAILS
            
        
        if needs_thumb:
            
            thumbnail_path = CG.client_controller.client_files_manager.GetThumbnailPath( self._media.GetDisplayMedia().GetMediaResult() )
            
            thumbnail_mime = HydrusFileHandling.GetThumbnailMime( thumbnail_path )
            
            self._thumbnail_qt_pixmap = ClientRendering.GenerateHydrusBitmap( thumbnail_path, thumbnail_mime ).GetQtPixmap()
            
            self.update()
            
        else:
            
            self._thumbnail_qt_pixmap = None
            
        
    

class OpenExternallyPanel( QW.QWidget ):
    
    def __init__( self, parent, media ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        self._media = media
        
        vbox = QP.VBoxLayout()
        
        if self._media.GetLocationsManager().IsLocal():
            
            qt_pixmap = CG.client_controller.thumbnails_cache.GetThumbnail( media.GetDisplayMedia().GetMediaResult() ).GetQtPixmap()
            
            thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
            
            if thumbnail_dpr_percent != 100:
                
                qt_pixmap.setDevicePixelRatio( thumbnail_dpr_percent / 100 )
                
            
            if qt_pixmap.width() > OPEN_EXTERNALLY_MAX_THUMBNAIL_SIZE[0] or qt_pixmap.height() > OPEN_EXTERNALLY_MAX_THUMBNAIL_SIZE[1]:
                
                qt_pixmap.scaled( OPEN_EXTERNALLY_MAX_THUMBNAIL_SIZE[0], OPEN_EXTERNALLY_MAX_THUMBNAIL_SIZE[1], QC.Qt.AspectRatioMode.KeepAspectRatio, QC.Qt.TransformationMode.SmoothTransformation )
                
            
            thumbnail_window = QW.QLabel( self, pixmap = qt_pixmap )
            
            QP.AddToLayout( vbox, thumbnail_window, CC.FLAGS_CENTER )
            
        
        m_text = HC.mime_string_lookup[ media.GetMime() ]
        
        button = QW.QPushButton( 'open {} externally'.format( m_text ), self )
        
        button.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        
        QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self.setCursor( QG.QCursor( QC.Qt.CursorShape.PointingHandCursor ) )
        
        button.clicked.connect( self.LaunchFile )
        
    
    def mousePressEvent( self, event ):
        
        if not ( event.modifiers() & ( QC.Qt.KeyboardModifier.ShiftModifier | QC.Qt.KeyboardModifier.ControlModifier | QC.Qt.KeyboardModifier.AltModifier ) ) and event.button() == QC.Qt.MouseButton.LeftButton:
            
            self.LaunchFile()
            
        else:
            
            event.ignore()
            
        
    
    def LaunchFile( self ):
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        client_files_manager = CG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        launch_path = self._new_options.GetMimeLaunch( mime )
        
        HydrusPaths.LaunchFile( path, launch_path )
        
    

class QtMediaPlayer( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, canvas_type, background_colour_generator ):
        
        super().__init__( parent )
        
        self._canvas_type = canvas_type
        self._background_colour_generator = background_colour_generator
        
        self._my_audio_output = QM.QAudioOutput( self )
        self._my_video_output = QMW.QVideoWidget( self )
        self._my_audio_placeholder = QW.QWidget( self )
        
        QP.SetBackgroundColour( self._my_audio_placeholder, QG.QColor( 0, 0, 0 ) )
        
        # perhaps this stops the always on top behaviour, says several places, but it doesn't for me!
        #self._my_video_output.setAttribute( QC.Qt.WA_TranslucentBackground, False )
        
        self._media_player = QM.QMediaPlayer( self )
        
        self._media_player.mediaStatusChanged.connect( self._MediaStatusChanged )
        
        self._we_are_initialised = True
        
        self._stop_for_slideshow = False
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._my_video_output, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( vbox, self._my_audio_placeholder, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._media = None
        
        self._playthrough_count = 0
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            shortcut_set = 'media_viewer_media_window'
            
        else:
            
            shortcut_set = 'preview_media_window'
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ shortcut_set ], catch_mouse = True )
        
        CG.client_controller.sub( self, 'UpdateAudioMute', 'new_audio_mute' )
        CG.client_controller.sub( self, 'UpdateAudioVolume', 'new_audio_volume' )
        
    
    def _MediaStatusChanged( self, status ):
        
        if status == QM.QMediaPlayer.MediaStatus.EndOfMedia:
            
            self._playthrough_count += 1
            
            self._media_player.setPosition( 0 )
            
            if not self._stop_for_slideshow:
                
                self._media_player.play()
                
            
        
    
    def GetAnimationBarStatus( self ):
        
        buffer_indices = None
        
        if self._media is None:
            
            current_frame_index = 0
            current_timestamp_ms = 0
            paused = True
            
        else:
            
            current_timestamp_ms = self._media_player.position()
            
            num_frames = self._media.GetNumFrames()
            
            if num_frames is None or num_frames == 1:
                
                current_frame_index = 0
                
            else:
                
                current_frame_index = int( round( ( current_timestamp_ms / self._media.GetDurationMS() ) * num_frames ) )
                
                current_frame_index = min( current_frame_index, num_frames - 1 )
                
            
            current_timestamp_ms = min( current_timestamp_ms, self._media.GetDurationMS() )
            
            paused = self.IsPaused()
            
        
        return ( current_frame_index, current_timestamp_ms, paused, buffer_indices )
        
    
    def ClearMedia( self ):
        
        if self._media is not None:
            
            self._media = None
            
            # ok in my experience setting media_player.setSource to anything after a first load is pretty buggy!
            # it can just straight up hang forever. either to a null QUrl or another file
            # it seems to be it doesn't like unloading some files
            # so, let's spawn a new one every time
            # EDIT: ok going from one vid to another can cause crashes, so we are moving to a system where each QtMediaPlayer just gets one use. we'll make a new one every time
            
            self._media_player.stop()
            
            #self._media_player.setParent( None )
            
            #CG.client_controller.CallAfter( self, self._media_player.deleteLater )
            
            #self._media_player = QM.QMediaPlayer( self )
            
            #self._media_player.mediaStatusChanged.connect( self._MediaStatusChanged )
            
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._playthrough_count > 0
        
    
    def IsCompletelyUnloaded( self ):
        
        return self._media_player.mediaStatus() == QM.QMediaPlayer.MediaStatus.NoMedia
        
    
    def IsPaused( self ):
        
        # don't use isPlaying(), Qt 6.4.1 doesn't support it lol
        return self._media_player.playbackState() != QM.QMediaPlayer.PlaybackState.PlayingState
        
    
    def Pause( self ):
        
        self._media_player.pause()
        
    
    def PausePlay( self ):
        
        if self.IsPaused():
            
            self.Play()
            
        else:
            
            self.Pause()
            
        
    
    def Play( self ):
        
        self._media_player.play()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_PAUSE_MEDIA:
                
                self.Pause()
                
            elif action == CAC.SIMPLE_PAUSE_PLAY_MEDIA:
                
                self.PausePlay()
                
            elif action == CAC.SIMPLE_MEDIA_SEEK_DELTA:
                
                ( direction, duration_ms ) = command.GetSimpleData()
                
                self.SeekDelta( direction, duration_ms )
                
            elif action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER and self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
                
                self.window().close()
                
            elif action == CAC.SIMPLE_LAUNCH_MEDIA_VIEWER and self._canvas_type == CC.CANVAS_PREVIEW:
                
                self.launchMediaViewer.emit()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def Seek( self, position_ms ):
        
        self._media_player.setPosition( position_ms )
        
    
    def SeekDelta( self, direction, duration_ms ):
        
        if self._media is None:
            
            return
            
        
        current_timestamp_ms = self._media_player.position()
        
        new_timestamp_ms = max( 0, current_timestamp_ms + ( direction * duration_ms ) )
        
        if new_timestamp_ms > self._media.GetDurationMS():
            
            new_timestamp_ms = 0
            
        
        self.Seek( new_timestamp_ms )
        
    
    def SetBackgroundColourGenerator( self, background_colour_generator ):
        
        self._background_colour_generator = background_colour_generator
        
    
    def SetMedia( self, media: ClientMedia.MediaSingleton, start_paused = False ):
        
        if media == self._media:
            
            return
            
        
        self.ClearMedia()
        
        self._media = media
        
        self._stop_for_slideshow = False
        
        has_audio = self._media.HasAudio()
        is_audio = self._media.GetMime() in HC.AUDIO
        
        if has_audio:
            
            self._media_player.setAudioOutput( self._my_audio_output )
            
        
        if not is_audio:
            
            self._media_player.setVideoOutput( self._my_video_output )
            
        
        self._my_video_output.setVisible( not is_audio )
        self._my_audio_placeholder.setVisible( is_audio )
        
        path = CG.client_controller.client_files_manager.GetFilePath( self._media.GetHash(), self._media.GetMime() )
        
        self._media_player.setSource( QC.QUrl.fromLocalFile( path ) )
        
        if not start_paused:
            
            self._media_player.play()
            
        
        self._my_audio_output.setVolume( ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type ) )
        self._my_audio_output.setMuted( ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type ) )
        
    
    def StopForSlideshow( self, value ):
        
        self._stop_for_slideshow = value
        
    
    def TryToUnload( self ):
        
        # this call is crashtastic, so don't inject it while the player is buffering or whatever
        if self._media_player.mediaStatus() in ( QM.QMediaPlayer.MediaStatus.LoadedMedia, QM.QMediaPlayer.MediaStatus.EndOfMedia, QM.QMediaPlayer.MediaStatus.InvalidMedia ):
            
            self._media_player.setSource( '' )
            
        
    
    def UpdateAudioMute( self ):
        
        self._my_audio_output.setMuted( ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type ) )
        

    def UpdateAudioVolume( self ):
        
        self._my_audio_output.setVolume( ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type ) )
        
    

class StaticImage( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    readyForNeighbourPrefetch = QC.Signal()
    
    def __init__( self, parent, canvas_type, background_colour_generator ):
        
        super().__init__( parent )
        
        self._canvas_type = canvas_type
        self._background_colour_generator = background_colour_generator
        
        if HC.PLATFORM_MACOS and not HG.macos_antiflicker_test:
            
            self.setAttribute( QC.Qt.WidgetAttribute.WA_OpaquePaintEvent, True )
            
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
        self.setMouseTracking( True )
        
        self._media = None
        
        self._image_renderer = None
        
        self._last_device_pixel_ratio = self.devicePixelRatio()
        
        self._image_tiles_cache = CG.client_controller.image_tiles_cache
        
        self._canvas_tiles = {}
        
        self._is_rendered = False
        
        self._raw_canvas_tile_size = QC.QSize( 768, 768 )
        self._device_canvas_tile_size = self._raw_canvas_tile_size / self._last_device_pixel_ratio
        
        self._zoom = 1.0
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            shortcut_set = 'media_viewer_media_window'
            
        else:
            
            shortcut_set = 'preview_media_window'
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ shortcut_set ], catch_mouse = True )
        
        CG.client_controller.sub( self, 'NotifyImageTileCacheCleared', 'clear_image_tile_cache' )
        CG.client_controller.sub( self, 'NotifyImageCacheCleared', 'clear_image_cache' )
        
    
    def _ClearCanvasTileCache( self ):
        
        my_raw_size = self._GetRawPixelSize()
        
        if self._media is None or self.width() == 0 or self.height() == 0:
            
            self._zoom = 1.0
            tile_dimension = 0
            
        else:
            
            ( media_width, media_height ) = self._media.GetResolution()
            
            self._zoom = my_raw_size.width() / media_width
            
            # it is most convenient to have tiles that line up with the current zoom ratio
            # 768 is a convenient size for meaty GPU blitting, but as a number it doesn't make for nice multiplication
            
            # a 'nice' size is one that divides nicely by our zoom, so that integer translations between canvas and native res aren't losing too much in the float remainder
            
            # the trick of going ( 123456 // 16 ) * 16 to give you a nice multiple of 16 does not work with floats like 1.4 lmao.
            # what we can do instead is phrase 1.4 as 7/5 and use 7 as our int. any number cleanly divisible by 7 is cleanly divisible by 1.4
            
            ideal_tile_dimension = CG.client_controller.new_options.GetInteger( 'ideal_tile_dimension' )
            
            nice_number = HydrusData.GetNicelyDivisibleNumberForZoom( self._zoom / self.devicePixelRatio(), ideal_tile_dimension )
            
            if nice_number == -1:
                
                # we are in extreme zoom land. nice multiples are impossible with reasonable size tiles, so we'll have to settle for some problems
                # a future solution is to get a bigger zoom and scale down
                # a future solution is to just make overlapping screen covering tiles and never deal with seams lmao
                
                tile_dimension = ideal_tile_dimension
                
            else:
                
                tile_dimension = ( ideal_tile_dimension // nice_number ) * nice_number
                
            
            tile_dimension = max( min( tile_dimension, 2048 ), 1 )
            
            if HG.canvas_tile_outline_mode:
                
                HydrusData.ShowText( '{} from zoom {} and nice number {}'.format( tile_dimension, self._zoom, nice_number ) )
                
            
        
        self._raw_canvas_tile_size = QC.QSize( tile_dimension, tile_dimension )
        
        self._canvas_tiles = {}
        
        self._last_device_pixel_ratio = self.devicePixelRatio()
        
        self._device_canvas_tile_size = self._raw_canvas_tile_size / self._last_device_pixel_ratio
        
        self._is_rendered = False
        
    
    def _DrawBackground( self, painter, topLeftOffset = None ):
        
        if self._background_colour_generator.CanDoTransparencyCheckerboard() and self._media is not None and self._media.GetFileInfoManager().has_transparency:
            
            light_grey = QG.QColor( 237, 237, 237 )
            dark_grey = QG.QColor( 222, 222, 222 )
            
            painter.setBackground( QG.QBrush( light_grey ) )
            
            painter.eraseRect( painter.viewport() )
            
            # 16x16 boxes, light grey in top right
            BOX_LENGTH = int( 16 * self.devicePixelRatio() )
            
            # there's a way to do this with viewports or transforms or something, but I don't know mate
            if topLeftOffset is None:
                
                rectTopLeftAdjust = QC.QPoint( 0, 0 )
                
            else:
                
                x = topLeftOffset.x() % ( BOX_LENGTH * 2 )
                y = topLeftOffset.y() % ( BOX_LENGTH * 2 )
                
                x_adjust = - x if x > 0 else 0
                y_adjust = - y if y > 0 else 0
                
                rectTopLeftAdjust = QC.QPoint( x_adjust, y_adjust )
                
            
            painter_width = painter.viewport().width() + abs( rectTopLeftAdjust.x() )
            painter_height = painter.viewport().height() + abs( rectTopLeftAdjust.y() )
            
            num_cols = painter_width // BOX_LENGTH
            
            if painter_width % BOX_LENGTH > 0:
                
                num_cols += 1
                
            
            num_rows = painter_height // BOX_LENGTH
            
            if painter_height % BOX_LENGTH > 0:
                
                num_rows += 1
                
            
            painter.setBrush( QG.QBrush( dark_grey ) )
            painter.setPen( QG.QPen( QC.Qt.PenStyle.NoPen ) )
            
            for y_index in range( num_rows ):
                
                for x_index in range( num_cols ):
                    
                    if ( x_index + y_index ) % 2 == 1:
                        
                        rect = QC.QRect( x_index * BOX_LENGTH, y_index * BOX_LENGTH, BOX_LENGTH, BOX_LENGTH )
                        
                        rect.moveTo( rect.topLeft() + rectTopLeftAdjust )
                        
                        if painter.viewport().intersects( rect ):
                            
                            painter.drawRect( rect )
                            
                        
                    
                
            
            return
            
        
        colour = self._background_colour_generator.GetColour()
        
        painter.setBackground( QG.QBrush( colour ) )
        
        painter.eraseRect( painter.viewport() )
        
    
    def _DrawTile( self, tile_coordinate ):
        
        ( native_clip_rect, raw_canvas_clip_rect ) = self._GetRawClipRectsFromTileCoordinates( tile_coordinate )
        
        raw_width = raw_canvas_clip_rect.width()
        raw_height = raw_canvas_clip_rect.height()
        
        tile_pixmap = CG.client_controller.bitmap_manager.GetQtPixmap( raw_width, raw_height )
        
        painter = QG.QPainter( tile_pixmap )
        
        self._DrawBackground( painter, topLeftOffset = raw_canvas_clip_rect.topLeft() )
        
        tile = self._image_tiles_cache.GetTile( self._image_renderer, self._media.GetMediaResult(), native_clip_rect, raw_canvas_clip_rect.size() )
        
        painter.drawPixmap( 0, 0, tile.qt_pixmap )
        
        if HG.canvas_tile_outline_mode:
            
            painter.setPen( QG.QPen( QG.QColor( 0, 127, 255 ) ) )
            painter.setBrush( QC.Qt.BrushStyle.NoBrush )
            
            painter.drawRect( tile_pixmap.rect() )
            
        
        self._canvas_tiles[ tile_coordinate ] = ( tile_pixmap, raw_canvas_clip_rect.topLeft() )
        
    
    def _GetRawClipRectsFromTileCoordinates( self, tile_coordinate ) -> tuple[ QC.QRect, QC.QRect ]:
        
        ( tile_x, tile_y ) = tile_coordinate
        
        my_raw_size = self._GetRawPixelSize()
        
        my_raw_width = my_raw_size.width()
        my_raw_height = my_raw_size.height()
        
        ( normal_raw_canvas_width, normal_raw_canvas_height ) = ( self._raw_canvas_tile_size.width(), self._raw_canvas_tile_size.height() )
        
        ( media_width, media_height ) = self._media.GetResolution()
        
        raw_canvas_x = tile_x * self._raw_canvas_tile_size.width()
        raw_canvas_y = tile_y * self._raw_canvas_tile_size.height()
        
        raw_canvas_topLeft = QC.QPoint( raw_canvas_x, raw_canvas_y )
        
        raw_canvas_width = normal_raw_canvas_width
        
        if raw_canvas_x + normal_raw_canvas_width > my_raw_width:
            
            # this is the rightmost tile and should be shrunk
            
            raw_canvas_width = my_raw_width % normal_raw_canvas_width
            
        
        raw_canvas_height = normal_raw_canvas_height
        
        if raw_canvas_y + normal_raw_canvas_height > my_raw_height:
            
            # this is the bottommost tile and should be shrunk
            
            raw_canvas_height = my_raw_height % normal_raw_canvas_height
            
        
        raw_canvas_width = max( 1, raw_canvas_width )
        raw_canvas_height = max( 1, raw_canvas_height )
        
        # if we are the last row/column our size is not this!
        
        raw_canvas_size = QC.QSize( raw_canvas_width, raw_canvas_height )
        
        raw_canvas_clip_rect = QC.QRect( raw_canvas_topLeft, raw_canvas_size )
        
        native_clip_rect = QC.QRect( raw_canvas_topLeft / self._zoom, raw_canvas_size / self._zoom )
        
        # dealing with rounding errors with zoom calc
        if native_clip_rect.width() + native_clip_rect.x() > media_width:
            
            native_clip_rect.setWidth( media_width - native_clip_rect.x() )
            
        
        if native_clip_rect.height() + native_clip_rect.y() > media_height:
            
            native_clip_rect.setHeight( media_height - native_clip_rect.y() )
            
        
        if native_clip_rect.width() == 0:
            
            native_clip_rect.setX( max( native_clip_rect.x() - 1, 0 ) )
            native_clip_rect.setWidth( 1 )
            
        
        if native_clip_rect.height() == 0:
            
            native_clip_rect.setY( max( native_clip_rect.y() - 1, 0 ) )
            native_clip_rect.setHeight( 1 )
            
        
        return ( native_clip_rect, raw_canvas_clip_rect )
        
    
    def _GetRawPixelSize( self ) -> QC.QSize:
        
        return self.size() * self.devicePixelRatio()
        
    
    def _GetTileCoordinateFromPoint( self, device_pos: QC.QPoint ):
        
        raw_pos = device_pos * self.devicePixelRatio()
        
        tile_x = raw_pos.x() // self._raw_canvas_tile_size.width()
        tile_y = raw_pos.y() // self._raw_canvas_tile_size.height()
        
        return ( tile_x, tile_y )
        
    
    def _GetTileCoordinatesInView( self, device_rect: QC.QRect ):
        
        if self.width() == 0 or self.height() == 0 or self._raw_canvas_tile_size.width() == 0 or self._raw_canvas_tile_size.height() == 0:
            
            return []
            
        
        topLeft_tile_coordinate = self._GetTileCoordinateFromPoint( device_rect.topLeft() )
        bottomRight_tile_coordinate = self._GetTileCoordinateFromPoint( device_rect.bottomRight() )
        
        i = itertools.product(
            range( topLeft_tile_coordinate[0], bottomRight_tile_coordinate[0] + 1 ),
            range( topLeft_tile_coordinate[1], bottomRight_tile_coordinate[1] + 1 )
    )
        
        return list( i )
        
    
    def ClearMedia( self ):
        
        self._media = None
        self._image_renderer = None
        
        self._ClearCanvasTileCache()
        
        self.update()
        
    
    def paintEvent( self, event ):
        
        if self.devicePixelRatio() != self._last_device_pixel_ratio:
            
            self._ClearCanvasTileCache()
            
        
        painter = QG.QPainter( self )
        
        if self._image_renderer is None or not self._image_renderer.IsReady():
            
            self._DrawBackground( painter )
            
            return
            
        
        try:
            
            dirty_tile_coordinates = self._GetTileCoordinatesInView( event.rect() )
            
            for dirty_tile_coordinate in dirty_tile_coordinates:
                
                if dirty_tile_coordinate not in self._canvas_tiles:
                    
                    self._DrawTile( dirty_tile_coordinate )
                    
                
            
            my_dpr = self.devicePixelRatio()
            
            visible_bounding_rect = self.visibleRegion().boundingRect()
            visible_bounding_rect_topLeft = visible_bounding_rect.topLeft()
            
            for dirty_tile_coordinate in dirty_tile_coordinates:
                
                ( tile, raw_pos ) = self._canvas_tiles[ dirty_tile_coordinate ]
                
                raw_pos_f = QC.QPointF( raw_pos )
                
                device_pos_f = typing.cast( QC.QPointF, raw_pos_f / my_dpr )
                
                tile.setDevicePixelRatio( my_dpr )
                
                adjust_pos_f = QC.QPointF()
                
                if my_dpr % 1 != 0.0:
                    
                    #
                    #   ,ad8888ba,           88888888ba  88                       88
                    #  d8"'    `"8b    ,d    88      "8b ""                       88
                    # d8'        `8b   88    88      ,8P                          88
                    # 88          88 MM88MMM 88aaaaaa8P' 88 8b,     ,d8 ,adPPYba, 88 ,adPPYba,
                    # 88          88   88    88""""""'   88  `Y8, ,8P' a8P_____88 88 I8[    ""
                    # Y8,    "88,,8P   88    88          88   )888(   8PP""""""" 88  `"Y8ba,
                    #  Y8a.    Y88P    88,   88          88  ,d8" "8b, "8b,   ,aa 88 aa    ]8I
                    #   `"Y8888Y"Y8a   "Y888 88          88 8P'     `Y8 `"Ybbd8"' 88 `"YbbdP"'
                    #
                    
                    # Ok, what is going on here is that if you have an ugly UI scale, like 125%, when a bitmap has to be drawn starting offscreen, Qt rounds the starting coordinate down every n pixels of offset
                    # something gets cut off somewhere, I guess every 5 pixels for 125%, 3 for 150%, and you get a blank/white line on the first set of tiles to be stitched as you drag around, flickering every n pixels
                    # therefore, we engage in some sordid hexxing here: if the current tile starts offscreen, we move it on a real pixel
                    # I haven't seen massive warping here, but maybe it stands out on cleaner vectors on low res displays. if so, I'll revisit and try to determine the actual nth pixel to activate this
                    
                    if device_pos_f.x() < visible_bounding_rect_topLeft.x():
                        
                        adjust_pos_f.setX( 1 / my_dpr )
                        
                    
                    if device_pos_f.y() < visible_bounding_rect_topLeft.y():
                        
                        adjust_pos_f.setY( 1 / my_dpr )
                        
                    
                
                painter.drawPixmap( device_pos_f + adjust_pos_f, tile )
                
                tile.setDevicePixelRatio( 1.0 )
                
            
            all_visible_tile_coordinates = self._GetTileCoordinatesInView( visible_bounding_rect )
            
            deletee_tile_coordinates = set( self._canvas_tiles.keys() ).difference( all_visible_tile_coordinates )
            
            for deletee_tile_coordinate in deletee_tile_coordinates:
                
                del self._canvas_tiles[ deletee_tile_coordinate ]
                
            
            if not self._is_rendered:
                
                self.readyForNeighbourPrefetch.emit()
                
                self._is_rendered = True
                
            
        except Exception as e:
            
            HydrusData.PrintException( e, do_wait = False )
            
            return
            
        
    
    def resizeEvent( self, event ):
        
        self._ClearCanvasTileCache()
        
    
    def showEvent( self, event ):
        
        self._ClearCanvasTileCache()
        
    
    def IsRendered( self ):
        
        return self._is_rendered
        
    
    def NotifyImageCacheCleared( self ):
        
        if self._media is not None:
            
            self._ClearCanvasTileCache()
            
            images_cache = CG.client_controller.images_cache
            
            self._image_renderer = images_cache.GetImageRenderer( self._media.GetMediaResult() )
            
            if not self._image_renderer.IsReady():
                
                CG.client_controller.gui.RegisterAnimationUpdateWindow( self )
                
            
            self.update()
            
        
    
    def NotifyImageTileCacheCleared( self ):
        
        if self._media is not None:
            
            self._ClearCanvasTileCache()
            
            self.update()
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER and self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
                
                self.window().close()
                
            elif action == CAC.SIMPLE_LAUNCH_MEDIA_VIEWER and self._canvas_type == CC.CANVAS_PREVIEW:
                
                self.launchMediaViewer.emit()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def SetBackgroundColourGenerator( self, background_colour_generator ):
        
        self._background_colour_generator = background_colour_generator
        
    
    def SetMedia( self, media ):
        
        if media == self._media:
            
            return
            
        
        self._ClearCanvasTileCache()
        
        self._media = media
        
        images_cache = CG.client_controller.images_cache
        
        self._image_renderer = images_cache.GetImageRenderer( self._media.GetMediaResult() )
        
        if not self._image_renderer.IsReady():
            
            CG.client_controller.gui.RegisterAnimationUpdateWindow( self )
            
        
        self.update()
        
    
    def TIMERAnimationUpdate( self ):
        
        try:
            
            if self._image_renderer is None or self._image_renderer.IsReady():
                
                self.update()
                
                CG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
                
            
        except:
            
            CG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
            raise
            
        
    
