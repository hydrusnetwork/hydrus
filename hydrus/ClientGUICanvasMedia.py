from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIMedia
from . import ClientGUIMediaControls
from . import ClientGUIMPV
from . import ClientGUIShortcuts
from . import ClientMedia
from . import ClientRendering
from . import HydrusPaths
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP
import typing

def ShouldHaveAnimationBar( media, show_action ):
    
    if show_action not in ( CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV ):
        
        return False
        
    
    is_animated_image = media.GetMime() in HC.ANIMATIONS
    is_audio = media.GetMime() in HC.AUDIO
    is_video = media.GetMime() in HC.VIDEO
    
    if show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV:
        
        if ( is_animated_image or is_audio or is_video ) and media.HasDuration():
            
            return True
            
        
    elif show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE:
        
        num_frames = media.GetNumFrames()
        
        has_some_frames = num_frames is not None and num_frames > 1
        
        if ( is_animated_image or is_video ) and has_some_frames:
            
            return True
            
        
    
    return False
    
class Animation( QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    
    def __init__( self, parent, canvas_type ):
        
        QW.QWidget.__init__( self, parent )
        
        self._canvas_type = canvas_type
        
        self.setMouseTracking( True )
        
        self._media = None
        
        self._left_down_event = None
        
        self._something_valid_has_been_drawn = False
        self._playthrough_count = 0
        
        self._num_frames = 1
        
        self._stop_for_slideshow = False
        
        self._current_frame_index = 0
        self._current_frame_drawn = False
        self._current_timestamp_ms = None
        self._next_frame_due_at = HydrusData.GetNowPrecise()
        self._slow_frame_score = 1.0
        
        self._paused = True
        
        self._video_container = None
        
        self._canvas_qt_pixmap = None
        
        if self._canvas_type == ClientGUICommon.CANVAS_MEDIA_VIEWER:
            
            shortcut_set = 'media_viewer_media_window'
            
        else:
            
            shortcut_set = 'preview_media_window'
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ shortcut_set ], catch_mouse = True )
        
    
    def _ClearCanvasBitmap( self ):
        
        if self._canvas_qt_pixmap is not None:
            
            self._canvas_qt_pixmap = None
            
        
    
    def _TryToDrawCanvasBitmap( self ):
        
        if self._video_container is None:
            
            size = self.size()
            
            width = size.width()
            height = size.height()
            
            self._video_container = ClientRendering.RasterContainerVideo( self._media, ( width, height ), init_position = self._current_frame_index )
            
        
        if not self._video_container.HasFrame( self._current_frame_index ):
            
            return
            
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        if self._canvas_qt_pixmap is None:
            
            self._canvas_qt_pixmap = HG.client_controller.bitmap_manager.GetQtPixmap( my_width, my_height )
            
        
        painter = QG.QPainter( self._canvas_qt_pixmap )
        
        current_frame = self._video_container.GetFrame( self._current_frame_index )
        
        ( frame_width, frame_height ) = current_frame.GetSize()
        
        scale = my_width / frame_width
        
        painter.setTransform( QG.QTransform().scale( scale, scale ) )
        
        current_frame_image = current_frame.GetQtImage()
        
        painter.drawImage( 0, 0, current_frame_image )
        
        painter.setTransform( QG.QTransform().scale( 1.0, 1.0 ) )
        
        self._current_frame_drawn = True
        
        next_frame_time_s = self._video_container.GetDuration( self._current_frame_index ) / 1000.0
        
        next_frame_ideally_due = self._next_frame_due_at + next_frame_time_s
        
        if HydrusData.TimeHasPassedPrecise( next_frame_ideally_due ):
            
            self._next_frame_due_at = HydrusData.GetNowPrecise() + next_frame_time_s
            
        else:
            
            self._next_frame_due_at = next_frame_ideally_due
            
        
        self._something_valid_has_been_drawn = True
        
    
    def _DrawABlankFrame( self, painter ):
        
        new_options = HG.client_controller.new_options
        
        painter.setBackground( QG.QBrush( new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        self._something_valid_has_been_drawn = True
        
    
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
        
        return self._playthrough_count > 0
        
    
    def IsPlaying( self ):
        
        return not self._paused
        
    
    def paintEvent( self, event ):
        
        if not self._current_frame_drawn:
            
            self._TryToDrawCanvasBitmap()
            
        
        painter = QG.QPainter( self )
        
        if self._canvas_qt_pixmap is None:
            
            self._DrawABlankFrame( painter )
            
        else:
            
            painter.drawPixmap( 0, 0, self._canvas_qt_pixmap )
            
        
    
    def Pause( self ):
        
        self._paused = True
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def Play( self ):
        
        self._paused = False
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'pause_media':
                
                self.Pause()
                
            elif action == 'pause_play_media':
                
                self.PausePlay()
                
            elif action == 'open_file_in_external_program':
                
                if self._media is not None:
                    
                    self.Pause()
                    
                    ClientGUIMedia.OpenExternally( self._media )
                    
                
            elif action == 'close_media_viewer' and self._canvas_type == ClientGUICommon.CANVAS_MEDIA_VIEWER:
                
                self.window().close()
                
            elif action == 'launch_media_viewer' and self._canvas_type == ClientGUICommon.CANVAS_PREVIEW:
                
                self.launchMediaViewer.emit()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def resizeEvent( self, event ):
        
        size = self.size()
        
        my_width = size.width()
        my_height = size.height()
        
        if my_width > 0 and my_height > 0:
            
            if self.size() != event.oldSize():
                
                self._ClearCanvasBitmap()
                
                self._current_frame_drawn = False
                self._something_valid_has_been_drawn = False
                
                self.update()
                
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
                                
                            
                        
                    
                
            
        
    
    def StopForSlideshow( self, value ):
        
        self._stop_for_slideshow = value
        
    
    def SetMedia( self, media, start_paused = False ):
        
        if media == self._media:
            
            return
            
        
        self._media = media
        
        self._left_down_event = None
        
        self._ClearCanvasBitmap()
        
        self._something_valid_has_been_drawn = False
        self._playthrough_count = 0
        
        self._stop_for_slideshow = False
        
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
        
        if self._media is None:
            
            HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
        else:
            
            HG.client_controller.gui.RegisterAnimationUpdateWindow( self )
            
            self.update()
            
        
    
    def TIMERAnimationUpdate( self ):
        
        if self._media is None:
            
            return
            
        
        try:
            
            if self.isVisible():
                
                if self._current_frame_drawn:
                    
                    if not self._paused and HydrusData.TimeHasPassedPrecise( self._next_frame_due_at ):
                        
                        num_frames = self._media.GetNumFrames()
                        
                        next_frame_index = ( self._current_frame_index + 1 ) % num_frames
                        
                        if next_frame_index == 0:
                            
                            self._playthrough_count += 1
                            
                            do_times_to_play_gif_pause = False
                            
                            if self._media.GetMime() == HC.IMAGE_GIF and not HG.client_controller.new_options.GetBoolean( 'always_loop_gifs' ):
                                
                                times_to_play_gif = self._video_container.GetTimesToPlayGIF()
                                
                                # 0 is infinite
                                if times_to_play_gif != 0 and self._playthrough_count >= times_to_play_gif:
                                    
                                    do_times_to_play_gif_pause = True
                                    
                                
                            
                            if self._stop_for_slideshow or do_times_to_play_gif_pause:
                                
                                self._paused = True
                                
                            else:
                                
                                self._current_frame_index = next_frame_index
                                self._current_timestamp_ms = 0
                                
                            
                        else:
                            
                            self._current_frame_index = next_frame_index
                            
                            if self._current_timestamp_ms is not None and self._video_container is not None and self._video_container.IsInitialised():
                                
                                duration_ms = self._video_container.GetDuration( self._current_frame_index - 1 )
                                
                                self._current_timestamp_ms += duration_ms
                                
                            
                        
                        self._current_frame_drawn = False
                        
                    
                
                if self._video_container is not None:
                    
                    if not self._current_frame_drawn:
                        
                        if self._video_container.HasFrame( self._current_frame_index ):
                            
                            self.update()
                            
                        
                    
                
            
        except:
            
            HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
            raise
            
        
    
class AnimationBar( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self.setCursor( QG.QCursor( QC.Qt.ArrowCursor ) )
        
        self._media_window = None
        self._duration_ms = 1000
        self._num_frames = 1
        self._last_drawn_info = None
        
        self._has_experienced_mouse_down = False
        self._currently_in_a_drag = False
        self._it_was_playing = False
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        self._widget_event_filter.EVT_MOUSE_EVENTS( self.EventMouse )    
        
    
    def _DrawBlank( self, painter ):
        
        new_options = HG.client_controller.new_options
        
        painter.setBackground( QG.QBrush( new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) ) )
        
        painter.eraseRect( painter.viewport() )
        
    
    def _GetAnimationBarStatus( self ):
        
        return self._media_window.GetAnimationBarStatus() 
        
    
    def _GetXFromFrameIndex( self, index, width_offset = 0 ):
        
        if self._num_frames is None or self._num_frames < 2:
            
            return 0
            
        
        my_width = self.size().width()
        
        return int( ( my_width - width_offset ) * index / ( self._num_frames - 1 ) )
        
    
    def _GetXFromTimestamp( self, timestamp_ms, width_offset = 0 ):
        
        my_width = self.size().width()
        
        return int( ( my_width - width_offset ) * timestamp_ms / self._duration_ms )
        
    
    def _Redraw( self, painter ):
        
        self._last_drawn_info = self._GetAnimationBarStatus()
        
        ( current_frame_index, current_timestamp_ms, paused, buffer_indices )  = self._last_drawn_info
        
        my_width = self.size().width()
        
        painter.setPen( QC.Qt.NoPen )
        
        background_colour = QP.GetSystemColour( QG.QPalette.Button )
        
        if paused:
            
            background_colour = ClientData.GetLighterDarkerColour( background_colour )
            
        
        painter.setBackground( QG.QBrush( background_colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        #
        
        animated_scanbar_height = HG.client_controller.new_options.GetInteger( 'animated_scanbar_height' )
        
        if buffer_indices is not None:
            
            ( start_index, rendered_to_index, end_index ) = buffer_indices
            
            if ClientRendering.FrameIndexOutOfRange( rendered_to_index, start_index, end_index ):
                
                rendered_to_index = start_index
                
            
            start_x = self._GetXFromFrameIndex( start_index )
            rendered_to_x = self._GetXFromFrameIndex( rendered_to_index )
            end_x = self._GetXFromFrameIndex( end_index )
            
            if start_x != rendered_to_x:
                
                rendered_colour = ClientData.GetDifferentLighterDarkerColour( background_colour )
                
                painter.setBrush( QG.QBrush( rendered_colour ) )
                
                if rendered_to_x > start_x:
                    
                    painter.drawRect( start_x, 0, rendered_to_x - start_x, animated_scanbar_height )
                    
                else:
                    
                    painter.drawRect( start_x, 0, my_width - start_x, animated_scanbar_height )
                    
                    painter.drawRect( 0, 0, rendered_to_x, animated_scanbar_height )
                    
                
            
            if rendered_to_x != end_x:
                
                to_be_rendered_colour = ClientData.GetDifferentLighterDarkerColour( background_colour, 1 )
                
                painter.setBrush( QG.QBrush( to_be_rendered_colour ) )
                
                if end_x > rendered_to_x:
                    
                    painter.drawRect( rendered_to_x, 0, end_x - rendered_to_x, animated_scanbar_height )
                    
                else:
                    
                    painter.drawRect( rendered_to_x, 0, my_width - rendered_to_x, animated_scanbar_height )
                    
                    painter.drawRect( 0, 0, end_x, animated_scanbar_height )
                    
                
            
        
        painter.setBrush( QG.QBrush( QP.GetSystemColour( QG.QPalette.Shadow ) ) )
        
        animated_scanbar_nub_width = HG.client_controller.new_options.GetInteger( 'animated_scanbar_nub_width' )
        
        num_frames_are_useful = self._num_frames is not None and self._num_frames > 1
        
        nub_x = None
        
        if num_frames_are_useful and current_frame_index is not None:
            
            nub_x = self._GetXFromFrameIndex( current_frame_index, width_offset = animated_scanbar_nub_width )
            
        elif self._duration_ms is not None and current_timestamp_ms is not None:
            
            nub_x = self._GetXFromTimestamp( current_timestamp_ms, width_offset = animated_scanbar_nub_width )
            
        
        if nub_x is not None:
            
            painter.drawRect( nub_x, 0, animated_scanbar_nub_width, animated_scanbar_height )
            
        
        #
        
        painter.setPen( QG.QPen() )
        
        progress_strings = []
        
        if num_frames_are_useful:
            
            progress_strings.append( HydrusData.ConvertValueRangeToPrettyString( current_frame_index + 1, self._num_frames ) )
            
        
        if current_timestamp_ms is not None:
            
            progress_strings.append( HydrusData.ConvertValueRangeToScanbarTimestampsMS( current_timestamp_ms, self._duration_ms ) )
            
        
        s = ' - '.join( progress_strings )
        
        if len( s ) > 0:
            
            text_width = painter.fontMetrics().size( QC.Qt.TextSingleLine, s ).width()
            
            QP.DrawText( painter, my_width - text_width - 3, 3, s )
            
        
    
    def ClearMedia( self ):
        
        self._media_window = None
        
        HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
        
        self.update()
        
    
    def EventMouse( self, event ):
        
        if self._media_window is not None:
            
            if not self._media_window or not QP.isValid( self._media_window ):
                
                self.ClearMedia()
                
                return
                
            
            CC.CAN_HIDE_MOUSE = False
            
            if event.type() == QC.QEvent.MouseButtonPress:
                
                self._has_experienced_mouse_down = True
                
                self._it_was_playing = self._media_window.IsPlaying()
                
                if self._it_was_playing:
                    
                    self._media_window.Pause()
                    
                
            
            # sometimes, this can inherit mouse-down from previous filter or embed button reveal, resulting in undesired scan
            
            if not self._has_experienced_mouse_down:
                
                return
                
            
            my_width = self.size().width()
            
            if event.type() == QC.QEvent.MouseMove and event.buttons() != QC.Qt.NoButton:
                
                self._currently_in_a_drag = True
                
            
            a_button_is_down = event.buttons() != QC.Qt.NoButton
            
            if a_button_is_down:
                
                event_pos = event.pos()
                
                animated_scanbar_nub_width = HG.client_controller.new_options.GetInteger( 'animated_scanbar_nub_width' )
                
                compensated_x_position = event_pos.x() - ( animated_scanbar_nub_width / 2 )
                
                proportion = ( compensated_x_position ) / ( my_width - animated_scanbar_nub_width )
                
                if proportion < 0: proportion = 0
                if proportion > 1: proportion = 1
                
                self.update()
                
                if isinstance( self._media_window, Animation ):
                    
                    current_frame_index = int( proportion * ( self._num_frames - 1 ) + 0.5 )
                    
                    self._media_window.GotoFrame( current_frame_index )
                    
                elif isinstance( self._media_window, ClientGUIMPV.mpvWidget ):
                    
                    time_index_ms = int( proportion * self._duration_ms )
                    
                    self._media_window.Seek( time_index_ms )
                    
                
            elif event.type() == QC.QEvent.MouseButtonRelease:
                
                if self._it_was_playing:
                    
                    self._media_window.Play()
                    
                
                self._currently_in_a_drag = False
                
            
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        if self._media_window is None:
            
            self._DrawBlank( painter )
            
        else:
            
            self._Redraw( painter )
            
        
    
    def SetMediaAndWindow( self, media, media_window ):
        
        self._media_window = media_window
        self._duration_ms = max( media.GetDuration(), 1 )
        
        num_frames = media.GetNumFrames()
        
        if num_frames is None:
            
            self._num_frames = num_frames
            
        else:
            
            self._num_frames = max( num_frames, 1 )
            
        
        self._last_drawn_info = None
        
        self._has_experienced_mouse_down = False
        self._currently_in_a_drag = False
        self._it_was_playing = False
        
        HG.client_controller.gui.RegisterAnimationUpdateWindow( self )
        
        self.update()
        
    
    def TIMERAnimationUpdate( self ):
        
        if self.isVisible():
            
            if not self._media_window or not QP.isValid( self._media_window ):
                
                self.ClearMedia()
                
                return
                
            
            if self._last_drawn_info != self._GetAnimationBarStatus():
                
                self.update()
                
            
        
    
class MediaContainerDragClickReportingFilter( QC.QObject ):
    
    def __init__( self, parent ):
        
        QC.QObject.__init__( self, parent )
        
    
    def eventFilter( self, watched, event ):
        
        if event.type() == QC.QEvent.MouseButtonPress and event.button() == QC.Qt.LeftButton and event.modifiers() == QC.Qt.NoModifier:
            
            self.parent().BeginDrag()
            
        elif event.type() == QC.QEvent.MouseButtonRelease and event.button() == QC.Qt.LeftButton and event.modifiers() == QC.Qt.NoModifier:
            
            self.parent().EndDrag()
            
        
        return False
        

class MediaContainer( QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    
    def __init__( self, parent, canvas_type ):
        
        QW.QWidget.__init__( self, parent )
        
        self._canvas_type = canvas_type
        
        # If I do not set this, macOS goes 100% CPU endless repaint events!
        # My guess is it due to the borked layout
        # it means 'I guarantee to cover my whole viewport with pixels, no need for automatic background clear'
        self.setAttribute( QC.Qt.WA_OpaquePaintEvent, True )
        
        self.setSizePolicy( QW.QSizePolicy.Fixed, QW.QSizePolicy.Fixed )
        
        self._media = None
        self._show_action = CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE
        self._start_paused = False
        self._start_with_embed = False
        
        self._media_window = None
        
        self._embed_button = EmbedButton( self )
        self._embed_button_widget_event_filter = QP.WidgetEventFilter( self._embed_button )
        self._embed_button_widget_event_filter.EVT_LEFT_DOWN( self.EventEmbedButton )
        
        self.setMouseTracking( True )
        
        self._drag_click_reporting_filter = MediaContainerDragClickReportingFilter( self.parentWidget() )
        
        self._animation_window = Animation( self, self._canvas_type )
        self._animation_bar = AnimationBar( self )
        self._volume_control = ClientGUIMediaControls.VolumeControl( self, self._canvas_type, direction = 'up' )
        self._static_image_window = StaticImage( self, self._canvas_type )
        
        self._volume_control.adjustSize()
        self._volume_control.setCursor( QC.Qt.ArrowCursor )
        
        self._animation_window.hide()
        self._animation_bar.hide()
        self._volume_control.hide()
        self._static_image_window.hide()
        self._embed_button.hide()
        
        self.hide()
        
    
    def _DestroyOrHideThisMediaWindow( self, media_window ):
        
        if media_window is not None:
            
            if isinstance( media_window, ( Animation, StaticImage, ClientGUIMPV.mpvWidget ) ):
                
                media_window.ClearMedia()
                
                media_window.hide()
                
                if isinstance( media_window, ClientGUIMPV.mpvWidget ):
                    
                    HG.client_controller.gui.ReleaseMPVWidget( media_window )
                    
                
            else:
                
                media_window.deleteLater()
                
            
        
    
    def _HideAnimationBar( self ):
        
        self._animation_bar.ClearMedia()
        
        self._animation_bar.hide()
        
    
    def _MakeMediaWindow( self ):
        
        old_media_window = self._media_window
        destroy_old_media_window = True
        
        if self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV and not ClientGUIMPV.MPV_IS_AVAILABLE:
            
            self._show_action = CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON
            
            HydrusData.ShowText( 'MPV is not available!' )
            
        
        if self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV and self._media.GetMime() == HC.IMAGE_GIF and not self._media.HasDuration():
            
            self._show_action = CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE
            
        
        if self._show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            raise Exception( 'This media should not be shown in the media viewer!' )
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON:
            
            self._media_window = OpenExternallyPanel( self, self._media )
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE:
            
            if self._media.IsStaticImage():
                
                if isinstance( self._media_window, StaticImage ):
                    
                    destroy_old_media_window = False
                    
                    self._media_window.hide()
                    
                else:
                    
                    self._media_window = self._static_image_window
                    
                
                self._media_window.SetMedia( self._media )
                
            else:
                
                if isinstance( self._media_window, Animation ):
                    
                    destroy_old_media_window = False
                    
                    self._media_window.hide()
                    
                else:
                    
                    self._media_window = self._animation_window
                    
                
                self._media_window.SetMedia( self._media, start_paused = self._start_paused )
                
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV:
            
            self._media_window = HG.client_controller.gui.GetMPVWidget( self )
            
            self._media_window.SetCanvasType( self._canvas_type )
            
            self._media_window.SetMedia( self._media, start_paused = self._start_paused )
            
        
        if ShouldHaveAnimationBar( self._media, self._show_action ):
            
            self._animation_bar.SetMediaAndWindow( self._media, self._media_window )
            
            if isinstance( self._media_window, ClientGUIMPV.mpvWidget ) and self._media.HasAudio():
                
                self._volume_control.show()
                
            else:
                
                self._volume_control.hide()
                
            
            self._animation_bar.show()
            
        else:
            
            self._HideAnimationBar()
            
            self._volume_control.hide()
            
        
        # this has to go after setcanvastype on the mpv window so the filters are in the correct order
        if old_media_window != self._media_window:
            
            self._media_window.installEventFilter( self._drag_click_reporting_filter )
            
            launch_media_viewer_classes = ( Animation, ClientGUIMPV.mpvWidget, StaticImage )
            
            if isinstance( self._media_window, launch_media_viewer_classes ):
                
                self._media_window.launchMediaViewer.connect( self.launchMediaViewer )
                
            
            if old_media_window is not None:
                
                old_media_window.removeEventFilter( self._drag_click_reporting_filter )
                
                if isinstance( old_media_window, launch_media_viewer_classes ):
                    
                    try:
                        
                        old_media_window.launchMediaViewer.disconnect( self.launchMediaViewer )
                        
                    except RuntimeError:
                        
                        pass # lmao, weird 'Failed to disconnect signal launchMediaViewer()' error I couldn't figure out, I guess some out-of-order deleteLater gubbins
                        
                    
                
            
            self._media_window
            
        
        if old_media_window is not None and destroy_old_media_window:
            
            self._DestroyOrHideThisMediaWindow( old_media_window )
            
            # this forces a flush of the last valid background bmp, so we don't get a flicker of a file from five files ago when we last saw a static image
            self.repaint()
            
        
    
    def _SizeAndPositionChildren( self ):
        
        if self._media is not None:
            
            my_size = self.size()
            
            my_width = my_size.width()
            my_height = my_size.height()
            
            if self._media_window is None:
                
                self._embed_button.setFixedSize( QC.QSize( my_width, my_height ) )
                self._embed_button.move( QC.QPoint( 0, 0 ) )
                
            else:
                
                is_open_externally = isinstance( self._media_window, OpenExternallyPanel )
                
                ( media_width, media_height ) = ( my_width, my_height )
                
                if ShouldHaveAnimationBar( self._media, self._show_action ) and not is_open_externally:
                    
                    animated_scanbar_height = HG.client_controller.new_options.GetInteger( 'animated_scanbar_height' )
                    
                    media_height -= animated_scanbar_height
                    
                    if self._volume_control.isVisibleTo( self ):
                        
                        volume_width = self._volume_control.width()
                        
                    else:
                        
                        volume_width = 0
                        
                    
                    self._animation_bar.setFixedSize( QC.QSize( my_width - volume_width, animated_scanbar_height ) )
                    self._animation_bar.move( QC.QPoint( 0, my_height - animated_scanbar_height ) )
                    
                    if self._volume_control.isVisibleTo( self ):
                        
                        self._volume_control.setFixedSize( QC.QSize( volume_width, animated_scanbar_height ) )
                        self._volume_control.move( QC.QPoint( self._animation_bar.width(), my_height - animated_scanbar_height ) )
                        
                    
                
                self._media_window.setFixedSize( QC.QSize( media_width, media_height ) )
                self._media_window.move( QC.QPoint( 0, 0 ) )
                
            
        
    
    def BeginDrag( self ):
        
        self.parentWidget().BeginDrag()
        
    
    def ClearMedia( self ):
        
        self._media = None
        
        self._HideAnimationBar()
        
        self._volume_control.hide()
        
        self._DestroyOrHideThisMediaWindow( self._media_window )
        
        self._media_window = None
        
        self.hide()
        
    
    def EventEmbedButton( self, event ):
        
        self._embed_button.hide()
        
        self._MakeMediaWindow()
        
        self._SizeAndPositionChildren()
        
    
    def resizeEvent( self, event ):
        
        if self._media is not None:
            
            self._SizeAndPositionChildren()
            
        
    
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
                    
                elif isinstance( self._media_window, ClientGUIMPV.mpvWidget ):
                    
                    self._media_window.GotoPreviousOrNextFrame( direction )
                    
                
            
        
    
    def MouseIsNearAnimationBar( self ):
        
        if self._media is None:
            
            return False
            
        else:
            
            if ShouldHaveAnimationBar( self._media, self._show_action ):
                
                animation_bar_mouse_pos = self._animation_bar.mapFromGlobal( QG.QCursor.pos() )
                
                animation_bar_rect = self._animation_bar.rect()
                
                buffer = 100
                
                test_rect = animation_bar_rect.adjusted( -buffer, -buffer, buffer, buffer )
                
                return test_rect.contains( animation_bar_mouse_pos )
                
            
            return False
            
        
    
    def paintEvent( self, event ):
        
        painter = None
        
        # hackery dackery doo to deal with non-redrawing single-pixel border around the real widget
        # we'll fix this when we fix the larger layout/repaint issue
        if self._volume_control.isVisible():
            
            painter = QG.QPainter( self )
            
            background_colour = HG.client_controller.new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
            
            painter.setBrush( QG.QBrush( background_colour ) )
            painter.setPen( QC.Qt.NoPen )
            
            painter.drawRect( self._volume_control.geometry() )
            
        
        if self._media_window is not None and self._media_window.isVisible():
            
            return
            
        
        # this only happens when we are transitioning from one media to another. in the brief period when one media type is going to another, we'll get flicker of the last valid bmp
        # mpv embed fun aggravates this
        # so instead we do an explicit repaint after the hide and before the new show, to clear our window
        
        if painter is None:
            
            painter = QG.QPainter( self )
            
        
        background_colour = HG.client_controller.new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
        painter.setBrush( QG.QBrush( background_colour ) )
        
        painter.drawRect( painter.viewport() )
        
    
    def Pause( self ):
        
        if self._media is not None:
            
            if isinstance( self._media_window, ( Animation, ClientGUIMPV.mpvWidget ) ):
                
                self._media_window.Pause()
                
            
        
    
    def PausePlay( self ):
        
        if self._media is not None:
            
            if isinstance( self._media_window, ( Animation, ClientGUIMPV.mpvWidget ) ):
                
                self._media_window.PausePlay()
                
            
        
    
    def ReadyToSlideshow( self ):
        
        if self._media is None:
            
            return False
            
        else:
            
            if isinstance( self._media_window, ( Animation, ClientGUIMPV.mpvWidget ) ):
                
                if not self._media_window.HasPlayedOnceThrough():
                    
                    return False
                    
                
            
            if isinstance( self._media_window, StaticImage ):
                
                if not self._media_window.IsRendered():
                    
                    return False
                    
                
            
            return True
            
        
    
    def SetEmbedButton( self ):
        
        self._HideAnimationBar()
        
        self._volume_control.hide()
        
        self._DestroyOrHideThisMediaWindow( self._media_window )
        
        self._media_window = None
        
        self._embed_button.SetMedia( self._media )
        
        self._embed_button.show()
        
    
    def SetMedia( self, media: ClientMedia.MediaSingleton, initial_size, initial_position, show_action, start_paused, start_with_embed ):
        
        self._media = media
        
        self._show_action = show_action
        self._start_paused = start_paused
        self._start_with_embed = start_with_embed
        
        if self._start_with_embed:
            
            self.SetEmbedButton()
            
        else:
            
            self._embed_button.hide()
            
            self._MakeMediaWindow()
            
        
        self.setFixedSize( initial_size )
        self.move( initial_position )
        
        self._SizeAndPositionChildren()
        
        if self._media_window is not None:
            
            self._media_window.show()
            
        
        self.show()
        
    
    def StopForSlideshow( self, value ):
        
        if isinstance( self._media_window, ( Animation, ClientGUIMPV.mpvWidget ) ):
            
            self._media_window.StopForSlideshow( value )
            
        
    
class EmbedButton( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._media = None
        
        self._thumbnail_qt_pixmap = None
        
        self.setCursor( QG.QCursor( QC.Qt.PointingHandCursor ) )
        
        HG.client_controller.sub( self, 'update', 'notify_new_colourset' )
        
    
    def _Redraw( self, painter ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        center_x = my_width // 2
        center_y = my_height // 2
        radius = min( 50, center_x, center_y ) - 5
        
        new_options = HG.client_controller.new_options
        
        painter.setBackground( QG.QBrush( new_options.GetColour(CC.COLOUR_MEDIA_BACKGROUND) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._thumbnail_qt_pixmap is not None:
            
            scale = my_width / self._thumbnail_qt_pixmap.width()
            
            painter.setTransform( QG.QTransform().scale( scale, scale ) )
            
            painter.drawPixmap( 0, 0, self._thumbnail_qt_pixmap )
            
            painter.setTransform( QG.QTransform().scale( 1.0, 1.0 ) )
            
        
        painter.setBrush( QG.QBrush( QP.GetSystemColour( QG.QPalette.Button ) ) )
        
        painter.drawEllipse( QC.QPointF( center_x, center_y ), radius, radius )
        
        painter.setBrush( QG.QBrush( QP.GetSystemColour( QG.QPalette.Window ) ) )
        
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
        
        painter.setPen( QG.QPen( QP.GetSystemColour( QG.QPalette.Shadow ) ) )

        painter.setBrush( QG.QBrush( QG.QColor( QC.Qt.transparent ) ) )
        
        painter.drawRect( 0, 0, my_width, my_height )
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._Redraw( painter )
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        if self._media is None:
            
            needs_thumb = False
            
        else:
            
            needs_thumb = self._media.GetLocationsManager().IsLocal() and self._media.GetMime() in HC.MIMES_WITH_THUMBNAILS
            
        
        if needs_thumb:
            
            mime = self._media.GetMime()
            
            thumbnail_path = HG.client_controller.client_files_manager.GetThumbnailPath( self._media )
            
            self._thumbnail_qt_pixmap = ClientRendering.GenerateHydrusBitmap( thumbnail_path, mime ).GetQtPixmap()
            
            self.update()
            
        else:
            
            self._thumbnail_qt_pixmap = None
            
        
    
class OpenExternallyPanel( QW.QWidget ):
    
    def __init__( self, parent, media ):
        
        QW.QWidget.__init__( self, parent )
        
        self._new_options = HG.client_controller.new_options
        
        self._media = media
        
        vbox = QP.VBoxLayout()
        
        if self._media.GetLocationsManager().IsLocal() and self._media.GetMime() in HC.MIMES_WITH_THUMBNAILS:
            
            mime = self._media.GetMime()
            
            thumbnail_path = HG.client_controller.client_files_manager.GetThumbnailPath( self._media )
            
            qt_pixmap = ClientRendering.GenerateHydrusBitmap( thumbnail_path, mime ).GetQtPixmap()
            
            thumbnail_window = ClientGUICommon.BufferedWindowIcon( self, qt_pixmap )
            
            QP.AddToLayout( vbox, thumbnail_window, CC.FLAGS_CENTER )
            
        
        m_text = HC.mime_string_lookup[ media.GetMime() ]
        
        button = QW.QPushButton( 'open ' + m_text + ' externally', self )
        
        button.setFocusPolicy( QC.Qt.NoFocus )
        
        QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self.setCursor( QG.QCursor( QC.Qt.PointingHandCursor ) )
        
        button.clicked.connect( self.LaunchFile )
        
    
    def mousePressEvent( self, event ):
        
        if not ( event.modifiers() & ( QC.Qt.ShiftModifier | QC.Qt.ControlModifier | QC.Qt.AltModifier) ) and event.button() == QC.Qt.LeftButton:
            
            self.LaunchFile()
            
        else:
            
            event.ignore()
            
        
    
    def paintEvent( self, event ):
        
        # have to manually repaint background because of parent WA_OpaquePaintEvent
        
        painter = QG.QPainter( self )
        
        background_colour = self._new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
        painter.setBackground( QG.QBrush( background_colour ) )
        
        painter.eraseRect( painter.viewport() )
        
    
    def LaunchFile( self ):
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        launch_path = self._new_options.GetMimeLaunch( mime )
        
        HydrusPaths.LaunchFile( path, launch_path )
        
    
class StaticImage( QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    
    def __init__( self, parent, canvas_type ):
        
        QW.QWidget.__init__( self, parent )
        
        self._canvas_type = canvas_type
        
        self.setAttribute( QC.Qt.WA_OpaquePaintEvent, True )
        
        self.setMouseTracking( True )
        
        self._media = None
        
        self._first_background_drawn = False
        
        self._image_renderer = None
        
        self._is_rendered = False
        
        self._canvas_qt_pixmap = None
        
        if self._canvas_type == ClientGUICommon.CANVAS_MEDIA_VIEWER:
            
            shortcut_set = 'media_viewer_media_window'
            
        else:
            
            shortcut_set = 'preview_media_window'
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ shortcut_set ], catch_mouse = True )
        
    
    def _ClearCanvasBitmap( self ):
        
        self._canvas_qt_pixmap = None
        
        self._is_rendered = False
        
        self._first_background_drawn = False
        
    
    def _DrawBackground( self, painter ):
        
        new_options = HG.client_controller.new_options
        
        painter.setBackground( QG.QBrush( new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        self._first_background_drawn = True
        
    
    def _TryToDrawCanvasBitmap( self ):
        
        if self._image_renderer is not None and self._image_renderer.IsReady():
            
            my_size = self.size()
            
            width = my_size.width()
            height = my_size.height()
            
            self._canvas_qt_pixmap = HG.client_controller.bitmap_manager.GetQtPixmap( width, height )
            
            painter = QG.QPainter( self._canvas_qt_pixmap )
            
            self._DrawBackground( painter )
            
            qt_bitmap = self._image_renderer.GetQtImage( self.size() )
            
            painter.drawImage( 0, 0, qt_bitmap )
            
            self._is_rendered = True
            
        
    
    def ClearMedia( self ):
        
        self._media = None
        self._image_renderer = None
        
        self._ClearCanvasBitmap()
        
        self.update()
        
    
    def paintEvent( self, event ):           
        
        if self._canvas_qt_pixmap is None:
            
            self._TryToDrawCanvasBitmap()
            
        
        painter = QG.QPainter( self )
        
        if self._canvas_qt_pixmap is None:
            
            self._DrawBackground( painter )
            
        else:
            
            painter.drawPixmap( 0, 0, self._canvas_qt_pixmap )
            
        
    
    def resizeEvent( self, event ):
        
        self._ClearCanvasBitmap()
        
    
    def IsRendered( self ):
        
        return self._is_rendered
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'open_file_in_external_program':
                
                if self._media is not None:
                    
                    ClientGUIMedia.OpenExternally( self._media )
                    
                
            elif action == 'close_media_viewer' and self._canvas_type == ClientGUICommon.CANVAS_MEDIA_VIEWER:
                
                self.window().close()
                
            elif action == 'launch_media_viewer' and self._canvas_type == ClientGUICommon.CANVAS_PREVIEW:
                
                self.launchMediaViewer.emit()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        image_cache = HG.client_controller.GetCache( 'images' )
        
        self._image_renderer = image_cache.GetImageRenderer( self._media )
        
        self._ClearCanvasBitmap()
        
        if not self._image_renderer.IsReady():
            
            HG.client_controller.gui.RegisterAnimationUpdateWindow( self )
            
        
        self.update()
        
    
    def TIMERAnimationUpdate( self ):
        
        try:
            
            if self._image_renderer is None or self._image_renderer.IsReady():
                
                self.update()
                
                HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
                
            
        except:
            
            HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
            raise
            
        
    
