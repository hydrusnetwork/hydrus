import fractions
import itertools
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientRendering
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMedia
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIMPV
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.media import ClientMedia

def ShouldHaveAnimationBar( media, show_action ):
    
    if media is None:
        
        return False
        
    
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
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
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
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
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
        
    
    def GotoFrame( self, frame_index, pause_afterwards = True ):
        
        if self._video_container is not None and self._video_container.IsInitialised():
            
            if frame_index != self._current_frame_index:
                
                self._current_frame_index = frame_index
                self._current_timestamp_ms = None
                
                self._next_frame_due_at = HydrusData.GetNowPrecise()
                
                self._video_container.GetReadyForFrame( self._current_frame_index )
                
                self._current_frame_drawn = False
                
            
            if pause_afterwards:
                
                self._paused = True
                
            
        
    
    def GotoTimestamp( self, timestamp_ms, round_direction, pause_afterwards = True ):
        
        if self._video_container is not None and self._video_container.IsInitialised():
            
            frame_index = self._video_container.GetFrameIndex( timestamp_ms )
            
            if frame_index == self._current_frame_index:
                
                frame_index += round_direction
                
            
            if frame_index > self._media.GetNumFrames() - 1:
                
                frame_index = 0
                
            
            self.GotoFrame( frame_index, pause_afterwards = pause_afterwards )
            
        
    
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
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM:
                
                if self._media is not None:
                    
                    self.Pause()
                    
                    ClientGUIMedia.OpenExternally( self._media )
                    
                
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
                                
                            
                        
                    
                
            
        
    
    def SeekDelta( self, direction, duration_ms ):
        
        if self._video_container is not None and self._video_container.IsInitialised():
            
            new_ts = self._current_timestamp_ms + ( direction * duration_ms )
            
            self.GotoTimestamp( new_ts, direction, pause_afterwards = False )
            
        
    
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
        
        self._colours = {
            'hab_border' : QG.QColor( 0, 0, 0 ),
            'hab_background' : QG.QColor( 240, 240, 240 ),
            'hab_nub' : QG.QColor( 96, 96, 96 )
        }
        
        self.setObjectName( 'HydrusAnimationBar' )
        
        self.setCursor( QG.QCursor( QC.Qt.ArrowCursor ) )
        
        self.setSizePolicy( QW.QSizePolicy.Fixed, QW.QSizePolicy.Fixed )
        
        self._media_window = None
        self._duration_ms = 1000
        self._num_frames = 1
        self._last_drawn_info = None
        
        self._currently_in_a_drag = False
        self._it_was_playing_before_drag = False
        
    
    def _DrawBlank( self, painter ):
        
        self.setProperty( 'playing', False )
        
        new_options = HG.client_controller.new_options
        
        background_colour = self._colours[ 'hab_background' ]
        
        painter.setBackground( background_colour )
        
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
        
    
    def _CurrentMediaWindowIsBad( self ):
        
        if self._media_window is None:
            
            return True
            
        
        if not QP.isValid( self._media_window ):
            
            self.ClearMedia()
            
            return True
            
        
        return False
        
    
    def _Redraw( self, painter ):
        
        self._last_drawn_info = self._GetAnimationBarStatus()
        
        ( current_frame_index, current_timestamp_ms, paused, buffer_indices )  = self._last_drawn_info
        
        self.setProperty( 'playing', not paused )
        
        my_width = self.size().width()
        my_height = self.size().height()
        
        painter.setPen( QC.Qt.NoPen )
        
        background_colour = self._colours[ 'hab_background' ]
        
        if paused:
            
            background_colour = ClientGUIFunctions.GetLighterDarkerColour( background_colour )
            
        
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
                
                rendered_colour = ClientGUIFunctions.GetDifferentLighterDarkerColour( background_colour )
                
                painter.setBrush( QG.QBrush( rendered_colour ) )
                
                if rendered_to_x > start_x:
                    
                    painter.drawRect( start_x, 0, rendered_to_x - start_x, animated_scanbar_height )
                    
                else:
                    
                    painter.drawRect( start_x, 0, my_width - start_x, animated_scanbar_height )
                    
                    painter.drawRect( 0, 0, rendered_to_x, animated_scanbar_height )
                    
                
            
            if rendered_to_x != end_x:
                
                to_be_rendered_colour = ClientGUIFunctions.GetDifferentLighterDarkerColour( background_colour, 1 )
                
                painter.setBrush( QG.QBrush( to_be_rendered_colour ) )
                
                if end_x > rendered_to_x:
                    
                    painter.drawRect( rendered_to_x, 0, end_x - rendered_to_x, animated_scanbar_height )
                    
                else:
                    
                    painter.drawRect( rendered_to_x, 0, my_width - rendered_to_x, animated_scanbar_height )
                    
                    painter.drawRect( 0, 0, end_x, animated_scanbar_height )
                    
                
            
        
        painter.setBrush( QG.QBrush( self._colours[ 'hab_nub' ] ) )
        
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
            
            ( text_size, s ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, s )
            
            x = my_width - text_size.width() - 3
            y = ( my_height - text_size.height() ) / 2
            
            ClientGUIFunctions.DrawText( painter, x, y, s )
            
        
        #
        
        painter.setBrush( QC.Qt.NoBrush )
        
        painter.setPen( QG.QPen( self._colours[ 'hab_border' ] ) )
        
        painter.drawRect( 0, 0, my_width - 1, my_height - 1 )
        
    
    def _ScanToCurrentMousePos( self ):
        
        my_width = self.size().width()
        
        mouse_pos = self.mapFromGlobal( QG.QCursor.pos() )
        
        animated_scanbar_nub_width = HG.client_controller.new_options.GetInteger( 'animated_scanbar_nub_width' )
        
        compensated_x_position = mouse_pos.x() - ( animated_scanbar_nub_width / 2 )
        
        proportion = ( compensated_x_position ) / ( my_width - animated_scanbar_nub_width )
        
        proportion = max( proportion, 0.0 )
        proportion = min( 1.0, proportion )
        
        self.update()
        
        if isinstance( self._media_window, Animation ):
            
            current_frame_index = int( proportion * ( self._num_frames - 1 ) + 0.5 )
            
            self._media_window.GotoFrame( current_frame_index )
            
        elif isinstance( self._media_window, ClientGUIMPV.mpvWidget ):
            
            time_index_ms = int( proportion * self._duration_ms )
            
            self._media_window.Seek( time_index_ms )
            
        
    
    def ClearMedia( self ):
        
        self._media_window = None
        
        HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
        
        self.update()
        
    
    def DoingADrag( self ):
        
        return self._currently_in_a_drag
        
    
    def mouseMoveEvent( self, event ):
        
        if self._CurrentMediaWindowIsBad():
            
            return
            
        
        CC.CAN_HIDE_MOUSE = False
        
        if self._currently_in_a_drag:
            
            if event.buttons() == QC.Qt.NoButton:
                
                self._currently_in_a_drag = False
                
                return
                
            
            self._ScanToCurrentMousePos()
            
        
    
    def mousePressEvent( self, event ):
        
        if self._CurrentMediaWindowIsBad():
            
            return
            
        
        CC.CAN_HIDE_MOUSE = False
        
        self._it_was_playing_before_drag = self._media_window.IsPlaying()
        
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
        
        if self._CurrentMediaWindowIsBad():
            
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
        
        self._currently_in_a_drag = False
        self._it_was_playing_before_drag = False
        
        HG.client_controller.gui.RegisterAnimationUpdateWindow( self )
        
        self.update()
        
    
    def TIMERAnimationUpdate( self ):
        
        if self._CurrentMediaWindowIsBad():
            
            self.ClearMedia()
            
            return
            
        
        if not self.isVisible():
            
            return
            
        
        if self._last_drawn_info != self._GetAnimationBarStatus():
            
            self.update()
            
        
    
    def get_hab_background( self ):
        
        return self._colours[ 'hab_background' ]
        
    
    def get_hab_border( self ):
        
        return self._colours[ 'hab_border' ]
        
    
    def get_hab_nub( self ):
        
        return self._colours[ 'hab_nub' ]
        
    
    def set_hab_background( self, colour ):
        
        self._colours[ 'hab_background' ] = colour
        
    
    def set_hab_border( self, colour ):
        
        self._colours[ 'hab_border' ] = colour
        
    
    def set_hab_nub( self, colour ):
        
        self._colours[ 'hab_nub' ] = colour
        
    
    hab_border = QC.Property( QG.QColor, get_hab_border, set_hab_border )
    hab_background = QC.Property( QG.QColor, get_hab_background, set_hab_background )
    hab_nub = QC.Property( QG.QColor, get_hab_nub, set_hab_nub )
    
class MediaContainer( QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    readyForNeighbourPrefetch = QC.Signal()
    
    def __init__( self, parent, canvas_type, additional_event_filter: QC.QObject ):
        
        QW.QWidget.__init__( self, parent )
        
        self._canvas_type = canvas_type
        
        if HC.PLATFORM_MACOS and not HG.macos_antiflicker_test:
            
            # does modern macOS still go 100% CPU when this is off?
            # yes :^(
            # try again with more layout tech on the full canvas
            
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
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
        self.setMouseTracking( True )
        
        self._additional_event_filter = additional_event_filter
        
        self._animation_window = Animation( self, self._canvas_type )
        
        self._static_image_window = StaticImage( self, self._canvas_type )
        
        self._static_image_window.readyForNeighbourPrefetch.connect( self.readyForNeighbourPrefetch )
        
        self._controls_bar = QW.QWidget( self )
        
        QP.SetBackgroundColour( self._controls_bar, QP.GetSystemColour( QG.QPalette.Shadow ) )
        
        self._animation_bar = AnimationBar( self._controls_bar )
        self._volume_control = ClientGUIMediaControls.VolumeControl( self._controls_bar, self._canvas_type, direction = 'up' )
        
        self._volume_control.setCursor( QC.Qt.ArrowCursor )
        
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
        
        HG.client_controller.sub( self, 'Pause', 'pause_all_media' )
        
    
    def _DestroyOrHideThisMediaWindow( self, media_window ):
        
        if media_window is not None:
            
            launch_media_viewer_classes = ( Animation, ClientGUIMPV.mpvWidget, StaticImage )
            
            media_window.removeEventFilter( self._additional_event_filter )
            
            if isinstance( media_window, launch_media_viewer_classes ):
                
                try:
                    
                    media_window.launchMediaViewer.disconnect( self.launchMediaViewer )
                    
                except RuntimeError:
                    
                    pass # lmao, weird 'Failed to disconnect signal launchMediaViewer()' error I couldn't figure out, I guess some out-of-order deleteLater gubbins
                    
                
            
            if isinstance( media_window, launch_media_viewer_classes ):
                
                media_window.ClearMedia()
                
                if isinstance( media_window, StaticImage ):
                    
                    media_window.repaint()
                    
                
                media_window.hide()
                
                if isinstance( media_window, ClientGUIMPV.mpvWidget ):
                    
                    HG.client_controller.gui.ReleaseMPVWidget( media_window )
                    
                
            else:
                
                media_window.deleteLater()
                
            
        
    
    def _MakeMediaWindow( self ):
        
        old_media_window = self._media_window
        destroy_old_media_window = True
        
        do_neighbour_prefetch_emit = True
        
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
                
                do_neighbour_prefetch_emit = False
                
            else:
                
                if isinstance( self._media_window, Animation ):
                    
                    destroy_old_media_window = False
                    
                    self._media_window.hide()
                    
                else:
                    
                    self._media_window = self._animation_window
                    
                
                self._media_window.SetMedia( self._media, start_paused = self._start_paused )
                
                self._media_window.lower()
                
            
        elif self._show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV:
            
            self._media_window = HG.client_controller.gui.GetMPVWidget( self )
            
            self._media_window.SetCanvasType( self._canvas_type )
            
            self._media_window.SetMedia( self._media, start_paused = self._start_paused )
            
            self._media_window.lower()
            
        
        if ShouldHaveAnimationBar( self._media, self._show_action ):
            
            self._animation_bar.SetMediaAndWindow( self._media, self._media_window )
            
        else:
            
            self._animation_bar.ClearMedia()
            
        
        media_window_changed = old_media_window != self._media_window
        
        # this has to go after setcanvastype on the mpv window so the filters are in the correct order
        if media_window_changed:
            
            self._media_window.installEventFilter( self._additional_event_filter )
            
            launch_media_viewer_classes = ( Animation, ClientGUIMPV.mpvWidget, StaticImage )
            
            if isinstance( self._media_window, launch_media_viewer_classes ):
                
                self._media_window.launchMediaViewer.connect( self.launchMediaViewer )
                
            
            self._DestroyOrHideThisMediaWindow( old_media_window )
            
            # this forces a flush of the last valid background bmp, so we don't get a flicker of a file from five files ago when we last saw a static image
            self.repaint()
            
        
        if do_neighbour_prefetch_emit:
            
            self.readyForNeighbourPrefetch.emit()
            
        
    
    def _SizeAndPositionChildren( self ):
        
        if self._media is not None:
            
            self._embed_button.setFixedSize( self.size() )
            self._embed_button.move( QC.QPoint( 0, 0 ) )
            
            if self._media_window is not None:
                
                self._media_window.setFixedSize( self.size() )
                self._media_window.move( QC.QPoint( 0, 0 ) )
                
            
            controls_bar_rect = self.GetIdealControlsBarRect()
            
            self._controls_bar.setFixedSize( controls_bar_rect.size() )
            self._controls_bar.move( controls_bar_rect.topLeft() )
            
        
    
    def BeginDrag( self ):
        
        self.parentWidget().BeginDrag()
        
    
    def ClearMedia( self ):
        
        self._media = None
        
        self._animation_bar.ClearMedia()
        
        self._controls_bar.hide()
        
        self._DestroyOrHideThisMediaWindow( self._media_window )
        
        self._media_window = None
        
        HG.client_controller.gui.UnregisterUIUpdateWindow( self )
        
        self.hide()
        
    
    def EventEmbedButton( self, event ):
        
        self._embed_button.hide()
        
        self._MakeMediaWindow()
        
        self._SizeAndPositionChildren()
        
        if self._media_window is not None:
            
            self._media_window.show()
            
        
    
    def resizeEvent( self, event ):
        
        if self._media is not None:
            
            self._SizeAndPositionChildren()
            
        
    
    def GetIdealControlsBarRect( self ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        animated_scanbar_height = HG.client_controller.new_options.GetInteger( 'animated_scanbar_height' )
        
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
                    
                elif isinstance( self._media_window, ClientGUIMPV.mpvWidget ):
                    
                    self._media_window.GotoPreviousOrNextFrame( direction )
                    
                
            
        
    
    def MouseIsNearAnimationBar( self ):
        
        if self._media is None:
            
            return False
            
        else:
            
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
            
        
    
    def SeekDelta( self, direction, duration_ms ):
        
        if self._media is not None:
            
            if isinstance( self._media_window, ( Animation, ClientGUIMPV.mpvWidget ) ):
                
                self._media_window.SeekDelta( direction, duration_ms )
                
            
        
    
    def SetMedia( self, media: ClientMedia.MediaSingleton, initial_size, initial_position, show_action, start_paused, start_with_embed ):
        
        self._media = media
        
        self._show_action = show_action
        self._start_paused = start_paused
        self._start_with_embed = start_with_embed
        
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
            
        
        self.setFixedSize( initial_size )
        self.move( initial_position )
        
        self._SizeAndPositionChildren()
        
        if self._media_window is not None:
            
            self._media_window.show()
            
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
        self.show()
        
    
    def ShouldHaveVolumeControl( self ):
        
        if self._media is None:
            
            return False
            
        
        return isinstance( self._media_window, ClientGUIMPV.mpvWidget ) and self._media.HasAudio()
        
    
    def StopForSlideshow( self, value ):
        
        if isinstance( self._media_window, ( Animation, ClientGUIMPV.mpvWidget ) ):
            
            self._media_window.StopForSlideshow( value )
            
        
    
    def TIMERUIUpdate( self ):
        
        if not ShouldHaveAnimationBar( self._media, self._show_action ):
            
            should_show_controls = False
            
        else:
            
            my_window = self.window()
            
            should_show_controls = self.MouseIsNearAnimationBar() or self._volume_control.PopupIsVisible() or self._animation_bar.DoingADrag() or HG.client_controller.new_options.GetBoolean( 'force_animation_scanbar_show' )
            
        
        if should_show_controls:
            
            if not self._controls_bar.isVisible():
                
                self._animation_bar.SetMediaAndWindow( self._media, self._media_window )
                
                self._controls_bar.show()
                self._controls_bar.raise_()
                
            
            should_show_volume = self.ShouldHaveVolumeControl()
            
            if self._volume_control.isVisible() != should_show_volume:
                
                self._volume_control.setVisible( should_show_volume )
                
                self._controls_bar.layout()
                
            
        else:
            
            if self._controls_bar.isVisible():
                
                # ok, repaint here forces a clear paint event NOW, before we hide.
                # this ensures that when we show again, we won't have the nub in the wrong place for a frame before it repaints
                # we'll have no nub, but this is less noticeable
                
                self._animation_bar.ClearMedia()
                
                self._animation_bar.repaint()
                
                self._controls_bar.hide()
                
                self._controls_bar.layout()
                
            
        
    
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

        painter.setBrush( QC.Qt.NoBrush )
        
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
        
        if not ( event.modifiers() & ( QC.Qt.ShiftModifier | QC.Qt.ControlModifier | QC.Qt.AltModifier ) ) and event.button() == QC.Qt.LeftButton:
            
            self.LaunchFile()
            
        else:
            
            event.ignore()
            
        
    
    def LaunchFile( self ):
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        launch_path = self._new_options.GetMimeLaunch( mime )
        
        HydrusPaths.LaunchFile( path, launch_path )
        
    
class StaticImage( QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    readyForNeighbourPrefetch = QC.Signal()
    
    def __init__( self, parent, canvas_type ):
        
        QW.QWidget.__init__( self, parent )
        
        self._canvas_type = canvas_type
        
        if HC.PLATFORM_MACOS and not HG.macos_antiflicker_test:
            
            self.setAttribute( QC.Qt.WA_OpaquePaintEvent, True )
            
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
        self.setMouseTracking( True )
        
        self._media = None
        
        self._image_renderer = None
        
        self._tile_cache = HG.client_controller.GetCache( 'image_tiles' )
        
        self._canvas_tiles = {}
        
        self._is_rendered = False
        
        self._canvas_tile_size = QC.QSize( 768, 768 )
        
        self._zoom = 1.0
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            shortcut_set = 'media_viewer_media_window'
            
        else:
            
            shortcut_set = 'preview_media_window'
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ shortcut_set ], catch_mouse = True )
        
    
    def _ClearCanvasTileCache( self ):
        
        if self._media is None or self.width() == 0 or self.height() == 0:
            
            self._zoom = 1.0
            tile_dimension = 0
            
        else:
            
            ( media_width, media_height ) = self._media.GetResolution()
            
            self._zoom = self.width() / media_width
            
            # it is most convenient to have tiles that line up with the current zoom ratio
            # 768 is a convenient size for meaty GPU blitting, but as a number it doesn't make for nice multiplication
            
            # a 'nice' size is one that divides nicely by our zoom, so that integer translations between canvas and native res aren't losing too much in the float remainder
            
            # the trick of going ( 123456 // 16 ) * 16 to give you a nice multiple of 16 does not work with floats like 1.4 lmao.
            # what we can do instead is phrase 1.4 as 7/5 and use 7 as our int. any number cleanly divisible by 7 is cleanly divisible by 1.4
            
            ideal_tile_dimension = HG.client_controller.new_options.GetInteger( 'ideal_tile_dimension' )
            
            nice_number = HydrusData.GetNicelyDivisibleNumberForZoom( self._zoom, ideal_tile_dimension )
            
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
                
            
        
        self._canvas_tile_size = QC.QSize( tile_dimension, tile_dimension )
        
        self._canvas_tiles = {}
        
        self._is_rendered = False
        
    
    def _DrawBackground( self, painter ):
        
        new_options = HG.client_controller.new_options
        
        painter.setBackground( QG.QBrush( new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND ) ) )
        
        painter.eraseRect( painter.viewport() )
        
    
    def _DrawTile( self, tile_coordinate ):
        
        ( native_clip_rect, canvas_clip_rect ) = self._GetClipRectsFromTileCoordinates( tile_coordinate )
        
        width = canvas_clip_rect.width()
        height = canvas_clip_rect.height()
        
        tile_pixmap = HG.client_controller.bitmap_manager.GetQtPixmap( width, height )
        
        painter = QG.QPainter( tile_pixmap )
        
        self._DrawBackground( painter )
        
        tile = self._tile_cache.GetTile( self._image_renderer, self._media, native_clip_rect, canvas_clip_rect.size() )
        
        painter.drawPixmap( 0, 0, tile.qt_pixmap )
        
        if HG.canvas_tile_outline_mode:
            
            painter.setPen( QG.QPen( QG.QColor( 0, 127, 255 ) ) )
            painter.setBrush( QC.Qt.NoBrush )
            
            painter.drawRect( tile_pixmap.rect() )
            
        
        self._canvas_tiles[ tile_coordinate ] = ( tile_pixmap, canvas_clip_rect.topLeft() )
        
    
    def _GetClipRectsFromTileCoordinates( self, tile_coordinate ) -> typing.Tuple[ QC.QRect, QC.QRect ]:
        
        ( tile_x, tile_y ) = tile_coordinate
        
        ( my_width, my_height ) = ( self.width(), self.height() )
        
        ( normal_canvas_width, normal_canvas_height ) = ( self._canvas_tile_size.width(), self._canvas_tile_size.height() )
        
        ( media_width, media_height ) = self._media.GetResolution()
        
        canvas_x = tile_x * self._canvas_tile_size.width()
        canvas_y = tile_y * self._canvas_tile_size.height()
        
        canvas_topLeft = QC.QPoint( canvas_x, canvas_y )
        
        canvas_width = normal_canvas_width
        
        if canvas_x + normal_canvas_width > my_width:
            
            # this is the rightmost tile and should be shrunk
            
            canvas_width = my_width % normal_canvas_width
            
        
        canvas_height = normal_canvas_height
        
        if canvas_y + normal_canvas_height > my_height:
            
            # this is the bottommost tile and should be shrunk
            
            canvas_height = my_height % normal_canvas_height
            
        
        canvas_width = max( 1, canvas_width )
        canvas_height = max( 1, canvas_height )
        
        # if we are the last row/column our size is not this!
        
        canvas_size = QC.QSize( canvas_width, canvas_height )
        
        canvas_clip_rect = QC.QRect( canvas_topLeft, canvas_size )
        
        native_clip_rect = QC.QRect( canvas_topLeft / self._zoom, canvas_size / self._zoom )
        
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
            
        
        return ( native_clip_rect, canvas_clip_rect )
        
    
    def _GetTileCoordinateFromPoint( self, pos: QC.QPoint ):
        
        tile_x = pos.x() // self._canvas_tile_size.width()
        tile_y = pos.y() // self._canvas_tile_size.height()
        
        return ( tile_x, tile_y )
        
    
    def _GetTileCoordinatesInView( self, rect: QC.QRect ):
        
        if self.width() == 0 or self.height() == 0 or self._canvas_tile_size.width() == 0 or self._canvas_tile_size.height() == 0:
            
            return []
            
        
        topLeft_tile_coordinate = self._GetTileCoordinateFromPoint( rect.topLeft() )
        bottomRight_tile_coordinate = self._GetTileCoordinateFromPoint( rect.bottomRight() )
        
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
        
        painter = QG.QPainter( self )
        
        if self._image_renderer is None or not self._image_renderer.IsReady():
            
            self._DrawBackground( painter )
            
            return
            
        
        try:
            
            dirty_tile_coordinates = self._GetTileCoordinatesInView( event.rect() )
            
            for dirty_tile_coordinate in dirty_tile_coordinates:
                
                if dirty_tile_coordinate not in self._canvas_tiles:
                    
                    self._DrawTile( dirty_tile_coordinate )
                    
                
            
            for dirty_tile_coordinate in dirty_tile_coordinates:
                
                ( tile, pos ) = self._canvas_tiles[ dirty_tile_coordinate ]
                
                painter.drawPixmap( pos, tile )
                
            
            all_visible_tile_coordinates = self._GetTileCoordinatesInView( self.visibleRegion().boundingRect() )
            
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
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM:
                
                if self._media is not None:
                    
                    ClientGUIMedia.OpenExternally( self._media )
                    
                
            elif action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER and self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
                
                self.window().close()
                
            elif action == CAC.SIMPLE_LAUNCH_MEDIA_VIEWER and self._canvas_type == CC.CANVAS_PREVIEW:
                
                self.launchMediaViewer.emit()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def SetMedia( self, media ):
        
        if media == self._media:
            
            return
            
        
        self._ClearCanvasTileCache()
        
        self._media = media
        
        image_cache = HG.client_controller.GetCache( 'images' )
        
        self._image_renderer = image_cache.GetImageRenderer( self._media )
        
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
            
        
    
