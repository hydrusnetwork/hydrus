import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

try:
    
    from qtpy import QtMultimediaWidgets as QMW
    from qtpy import QtMultimedia as QM
    
except Exception as e:
    
    pass
    

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.media import ClientGUIMediaVolume
from hydrus.client.media import ClientMedia

# TODO: Consider whether to abstract out the 'video output' parts to their own classes and merge these guys--or just delete the videowidget version if and when we know the graphicsview is noice

class QtMediaPlayerVideoWidget( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
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
            
            #CG.client_controller.CallAfterQtSafe( self, self._media_player.deleteLater )
            
            #self._media_player = QM.QMediaPlayer( self )
            
            #self._media_player.mediaStatusChanged.connect( self._MediaStatusChanged )
            
        
    
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
        
    
    def Seek( self, position_ms, precise = True ):
        
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
            
        
        self._my_audio_output.setVolume( ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type ) / 100 )
        self._my_audio_output.setMuted( ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type ) )
        
    
    def StopForSlideshow( self, value ):
        
        self._stop_for_slideshow = value
        
    
    def TryToUnload( self ):
        
        # this call is crashtastic, so don't inject it while the player is buffering or whatever
        if self._media_player.mediaStatus() in ( QM.QMediaPlayer.MediaStatus.LoadedMedia, QM.QMediaPlayer.MediaStatus.EndOfMedia, QM.QMediaPlayer.MediaStatus.InvalidMedia ):
            
            self._media_player.setSource( QC.QUrl() )
            
        
    
    def UpdateAudioMute( self ):
        
        self._my_audio_output.setMuted( ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type ) )
        

    def UpdateAudioVolume( self ):
        
        self._my_audio_output.setVolume( ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type ) / 100 )
        
    

if typing.TYPE_CHECKING:
    
    from hydrus.client.gui.canvas import ClientGUICanvas
    

class GraphicsViewViewportMouseMoveCatcher( QC.QObject ):
    
    def __init__( self, parent: "ClientGUICanvas.Canvas" ):
        
        super().__init__( parent )
        
        self._parent = parent
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.MouseMove:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                left_down = bool( event.buttons() & QC.Qt.MouseButton.LeftButton )
                
                self._parent.HandleMouseMoveWithoutEvent( left_down )
                
                return False
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    

class MyQGraphicsView( QW.QGraphicsView ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        if CG.client_controller.new_options.GetBoolean( 'qt_media_player_opengl_test' ):
            
            self.setViewport( QW.QOpenGLWidget( self ) )
            
        
        self.setDragMode( QW.QGraphicsView.DragMode.NoDrag )
        self.setScene( QW.QGraphicsScene( self ) )
        self.setVerticalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff )
        self.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff )
        
        self.setFrameShape( QW.QFrame.Shape.NoFrame )
        
        self.setBackgroundBrush( QC.Qt.GlobalColor.black )
        
    
    # TODO: Revisit mouseMove handling here. seems like if I set setMouseTracking( True ) here, I can catch mouseMoveEvent natively. play with that as a nicer alternative to the MouseMoveCatcher hackery dackery doo
    
    def wheelEvent( self, event ):
        
        # weird Viewport gubbins means media will sometimes scroll inside the viewport, I guess because it is 1px taller/wider than the viewport or whatever
        event.ignore()
        
    

class QtMediaPlayerGraphicsView( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, canvas_type, canvas, background_colour_generator ):
        
        super().__init__( parent )
        
        self._canvas_type = canvas_type
        self._canvas = canvas
        self._background_colour_generator = background_colour_generator
        
        self._my_audio_output = QM.QAudioOutput( self )
        self._my_audio_placeholder = QW.QWidget( self )
        
        # 2026-01: this is the first time hydev has done GraphicsView stuff, and thus all this was divined via haruspex
        
        self._my_graphics_view = MyQGraphicsView( self )
        
        self._my_video_output = QMW.QGraphicsVideoItem()
        self._my_video_output.setZValue( 0 )
        
        self._my_graphics_view.scene().addItem( self._my_video_output )
        
        self._my_video_output.setPos( 0, 0 )
        
        self._my_video_output.nativeSizeChanged.connect( self._RefitVideo )
        
        QP.SetBackgroundColour( self._my_audio_placeholder, QG.QColor( 0, 0, 0 ) )
        
        self._media_player = QM.QMediaPlayer( self )
        
        self._media_player.setLoops( QM.QMediaPlayer.Loops.Infinite )
        
        self._we_are_initialised = True
        
        self._stop_for_slideshow = False
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._my_graphics_view, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( vbox, self._my_audio_placeholder, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._media = None
        
        self._near_endpoint = False
        self._playthrough_count = 0
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            shortcut_set = 'media_viewer_media_window'
            
        else:
            
            shortcut_set = 'preview_media_window'
            
        
        self._my_audio_placeholder.setMouseTracking( True )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ shortcut_set ], catch_mouse = True )
        
        CG.client_controller.sub( self, 'UpdateAudioMute', 'new_audio_mute' )
        CG.client_controller.sub( self, 'UpdateAudioVolume', 'new_audio_volume' )
        
    
    def _RefitVideo( self ):
        
        # ok this is megaslop but it works
        # had to edit a bit for KISS since it was going bananas
        # doing fitInView( my_video.sceneBoundingRect ) gives some margin for some reason I don't know (viewport QSS?)
        
        self._my_graphics_view.scene().setSceneRect( self._my_video_output.mapRectToScene( self._my_video_output.boundingRect() ) )
        
        self._my_graphics_view.centerOn( self._my_video_output )
        
        rect = self._my_video_output.sceneBoundingRect()
        
        vp = self._my_graphics_view.viewport().rect()
        
        Vw, Vh = vp.width(), vp.height()
        Rw, Rh = rect.width(), rect.height()
        
        if Vw <= 0 or Vh <= 0 or Rw <= 0 or Rh <= 0:
            
            return
            
        
        s = min( Vw / Rw, Vh / Rh )
        
        Dw, Dh = Rw * s, Rh * s
        
        tx = (Vw - Dw) / 2.0 - rect.left() * s
        ty = (Vh - Dh) / 2.0 - rect.top()  * s
        
        self._my_graphics_view.setTransform( QG.QTransform( s, 0, 0, s, tx, ty ), False)
        
        '''
        rect = self._my_video_output.sceneBoundingRect()
        
        if rect.isValid() and rect.width() > 0 and rect.height() > 0:
            
            self._my_graphics_view.fitInView( rect, QC.Qt.AspectRatioMode.KeepAspectRatio )
            
        '''
    
    def ClearMedia( self ):
        
        if self._media is not None:
            
            self._media = None
            
            # it used to be really buggy to go media_player.setSource after a first load, but in Qt >=6.9 things seem fine
            
            self._media_player.stop()
            
        
    
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
                
                position_float = current_timestamp_ms / self._media.GetDurationMS()
                
                if not self._near_endpoint and position_float > 0.8: # bit of padding
                    
                    self._near_endpoint = True
                    
                elif self._near_endpoint and position_float < 0.2:
                    
                    self._near_endpoint = False
                    self._playthrough_count += 1
                    
                
                current_frame_index = int( round( position_float * num_frames ) )
                
                current_frame_index = min( current_frame_index, num_frames - 1 )
                
            
            current_timestamp_ms = min( current_timestamp_ms, self._media.GetDurationMS() )
            
            paused = self.IsPaused()
            
        
        return ( current_frame_index, current_timestamp_ms, paused, buffer_indices )
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._playthrough_count > 0
        
    
    def InstallMouseMoveCatcher( self, event_filter: QC.QObject ):
        
        self._my_graphics_view.viewport().setMouseTracking( True )
        self._my_graphics_view.viewport().installEventFilter( event_filter )
        
    
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
        
    
    def resizeEvent( self, event ):
        
        super().resizeEvent( event )
        
        self._RefitVideo()
        
    
    def Seek( self, position_ms, precise = True ):
        
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
            
        
        self._my_graphics_view.setVisible( not is_audio )
        self._my_audio_placeholder.setVisible( is_audio )
        
        path = CG.client_controller.client_files_manager.GetFilePath( self._media.GetHash(), self._media.GetMime() )
        
        self._media_player.setSource( QC.QUrl.fromLocalFile( path ) )
        
        if not start_paused:
            
            self._media_player.play()
            
        
        self._my_audio_output.setVolume( ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type ) / 100 )
        self._my_audio_output.setMuted( ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type ) )
        
    
    def showEvent( self, event ):
        
        super().showEvent( event )
        
        self._RefitVideo()
        
    
    def StopForSlideshow( self, value ):
        
        self._stop_for_slideshow = value
        
    
    def TryToUnload( self ):
        
        # this call is crashtastic, so don't inject it while the player is buffering or whatever
        if self._media_player.mediaStatus() in ( QM.QMediaPlayer.MediaStatus.LoadedMedia, QM.QMediaPlayer.MediaStatus.EndOfMedia, QM.QMediaPlayer.MediaStatus.InvalidMedia ):
            
            self._media_player.setSource( QC.QUrl() )
            
        
    
    def UpdateAudioMute( self ):
        
        self._my_audio_output.setMuted( ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type ) )
        

    def UpdateAudioVolume( self ):
        
        self._my_audio_output.setVolume( ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type ) / 100 )
        
    
