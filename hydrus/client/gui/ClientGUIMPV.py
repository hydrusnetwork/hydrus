import locale
import os
import traceback

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusPaths

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIMedia
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP

mpv_failed_reason = 'MPV seems ok!'

try:
    
    import mpv
    
    MPV_IS_AVAILABLE = True
    
except Exception as e:
    
    mpv_failed_reason = traceback.format_exc()
    
    MPV_IS_AVAILABLE = False

def GetClientAPIVersionString():
    
    try:
        
        ( major, minor ) = mpv._mpv_client_api_version()
        
        return '{}.{}'.format( major, minor )
        
    except:
        
        return 'unknown'
        
    
# issue about mouse-to-osc interactions:
'''
    def mouseMoveEvent( self, event ):
        
        # same deal here as with mousereleaseevent--osc is non-interactable with commands, so let's not use it for now
        #self._player.command( 'mouse', event.x(), event.y() )
        
        event.ignore()
        
    
    def mouseReleaseEvent( self, event ):
        
        # left index = 0
        # right index = 2
        # the issue with using this guy is it sends a mouse press or mouse down event, and the OSC only responds to mouse up
        
        #self._player.command( 'mouse', event.x(), event.y(), index, 'single' )
        
        event.ignore()
        
    '''

def log_handler( loglevel, component, message ):
    
    HydrusData.DebugPrint( '[{}] {}: {}'.format( loglevel, component, message ) )
    
#Not sure how well this works with hardware acceleration. This just renders to a QWidget. In my tests it seems fine, even with vdpau video out, but I'm not 100% sure it actually uses hardware acceleration.
#Here is an example on how to render into a QOpenGLWidget instead: https://gist.github.com/cosven/b313de2acce1b7e15afda263779c0afc
class mpvWidget( QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._canvas_type = CC.CANVAS_PREVIEW
        
        self._stop_for_slideshow = False
        
        # This is necessary since PyQT stomps over the locale settings needed by libmpv.
        # This needs to happen after importing PyQT before creating the first mpv.MPV instance.
        locale.setlocale( locale.LC_NUMERIC, 'C' )
        
        self.setAttribute( QC.Qt.WA_DontCreateNativeAncestors )
        self.setAttribute( QC.Qt.WA_NativeWindow )
        
        loglevel = 'debug' if HG.mpv_report_mode else 'fatal'
        
        # loglevels: fatal, error, debug
        self._player = mpv.MPV( wid = str( int( self.winId() ) ), log_handler = log_handler, loglevel = loglevel )
        
        # hydev notes on OSC:
        # OSC is by default off, default input bindings are by default off
        # difficult to get this to intercept mouse/key events naturally, so you have to pipe them to the window with 'command', but this is not excellent
        # general recommendation when using libmpv is to just implement your own stuff anyway, so let's do that for prototype
        
        #self._player[ 'input-default-bindings' ] = True
        
        self.UpdateConf()
        
        self._player.loop = True
        
        # this makes black screen for audio (rather than transparent)
        self._player.force_window = True
        
        # this actually propagates up to the OS-level sound mixer lmao, otherwise defaults to ugly hydrus filename
        self._player.title = 'hydrus mpv player'
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
        self.setMouseTracking( True )
        #self.setFocusPolicy(QC.Qt.StrongFocus)#Needed to get key events
        self._player.input_cursor = False#Disable mpv mouse move/click event capture
        self._player.input_vo_keyboard = False#Disable mpv key event capture, might also need to set input_x11_keyboard
        
        self._media = None
        
        self._file_is_loaded = False
        self._disallow_seek_on_this_file = False
        
        self._times_to_play_gif = 0
        
        self._current_seek_to_start_count = 0
        
        self._InitialiseMPVCallbacks()
        
        self.destroyed.connect( self._player.terminate )
        
        HG.client_controller.sub( self, 'UpdateAudioMute', 'new_audio_mute' )
        HG.client_controller.sub( self, 'UpdateAudioVolume', 'new_audio_volume' )
        HG.client_controller.sub( self, 'UpdateConf', 'notify_new_options' )
        HG.client_controller.sub( self, 'SetLogLevel', 'set_mpv_log_level' )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [], catch_mouse = True )
        
    
    def _GetAudioOptionNames( self ):
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            if HG.client_controller.new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ):
                
                return ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_MEDIA_VIEWER ]
                
            
        elif self._canvas_type == CC.CANVAS_PREVIEW:
            
            if HG.client_controller.new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ):
                
                return ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_PREVIEW ]
                
            
        
        return ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_GLOBAL ]
        
    
    def _GetCorrectCurrentMute( self ):
        
        ( global_mute_option_name, global_volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_GLOBAL ]
        
        mute_option_name = global_mute_option_name
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_MEDIA_VIEWER ]
            
        elif self._canvas_type == CC.CANVAS_PREVIEW:
            
            ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_PREVIEW ]
            
        
        return HG.client_controller.new_options.GetBoolean( mute_option_name ) or HG.client_controller.new_options.GetBoolean( global_mute_option_name )
        
    
    def _GetCorrectCurrentVolume( self ):
        
        ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_GLOBAL ]
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            if HG.client_controller.new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ):
                
                ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_MEDIA_VIEWER ]
                
            
        elif self._canvas_type == CC.CANVAS_PREVIEW:
            
            if HG.client_controller.new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ):
                
                ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_PREVIEW ]
                
            
        
        return HG.client_controller.new_options.GetInteger( volume_option_name )
        
    
    def _InitialiseMPVCallbacks( self ):
        
        def qt_file_loaded_event():
            
            if not QP.isValid( self ):
                
                return
                
            
            self._file_is_loaded = True
            
        
        def qt_seek_event():
            
            if not QP.isValid( self ):
                
                return
                
            
            if not self._file_is_loaded:
                
                return
                
            
            current_timestamp_s = self._player.time_pos
            
            if self._media is not None and current_timestamp_s is not None and current_timestamp_s <= 1.0:
                
                self._current_seek_to_start_count += 1
                
                if self._stop_for_slideshow:
                    
                    self.Pause()
                    
                
                if self._times_to_play_gif != 0 and self._current_seek_to_start_count >= self._times_to_play_gif:
                    
                    self.Pause()
                    
                
            
            
        
        player = self._player
        
        @player.event_callback( mpv.MpvEventID.SEEK )
        def seek_event( event ):
            
            QP.CallAfter( qt_seek_event )
            
        
        @player.event_callback( mpv.MpvEventID.FILE_LOADED )
        def file_loaded_event( event ):
            
            QP.CallAfter( qt_file_loaded_event )
            
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def GetAnimationBarStatus( self ):
        
        buffer_indices = None
        
        if self._media is None or not self._file_is_loaded:
            
            current_frame_index = 0
            current_timestamp_ms = 0
            paused = True
            
        else:
            
            current_timestamp_s = self._player.time_pos
            
            if current_timestamp_s is None:
                
                current_frame_index = 0
                current_timestamp_ms = None
                
            else:
                
                current_timestamp_ms = current_timestamp_s * 1000
                
                num_frames = self._media.GetNumFrames()
                
                if num_frames is None or num_frames == 1:
                    
                    current_frame_index = 0
                    
                else:
                    
                    current_frame_index = int( round( ( current_timestamp_ms / self._media.GetDuration() ) * num_frames ) )
                    
                    current_frame_index = min( current_frame_index, num_frames - 1 )
                    
                
                current_timestamp_ms = min( current_timestamp_ms, self._media.GetDuration() )
                
            
            paused = self._player.pause
            
        
        return ( current_frame_index, current_timestamp_ms, paused, buffer_indices )
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        if not self._file_is_loaded:
            
            return
            
        
        command = 'frame-step'
        
        if direction == 1:
            
            command = 'frame-step'
            
        elif direction == -1:
            
            command = 'frame-back-step'
            
        
        self._player.command( command )
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._current_seek_to_start_count > 0
        

    def IsPlaying( self ):
        
        return not self._player.pause
        
    
    def Pause( self ):
        
        self._player.pause = True
        

    def PausePlay( self ):
        
        self._player.pause = not self._player.pause
        

    def Play( self ):
        
        self._player.pause = False
        
    
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
        
    
    def Seek( self, time_index_ms ):
        
        if not self._file_is_loaded:
            
            return
            
        
        if self._disallow_seek_on_this_file:
            
            return
            
        
        time_index_s = time_index_ms / 1000
        
        try:
            
            self._player.seek( time_index_s, reference = 'absolute' )
            
        except:
            
            self._disallow_seek_on_this_file = True
            
            # on some files, this seems to fail with a SystemError lmaoooo
            # with the same elegance, we will just pass all errors
            
        
    
    def SeekDelta( self, direction, duration_ms ):
        
        if not self._file_is_loaded:
            
            return
            
        
        current_timestamp_s = self._player.time_pos
        
        new_timestamp_ms = max( 0, ( current_timestamp_s * 1000 ) + ( direction * duration_ms ) )
        
        if new_timestamp_ms > self._media.GetDuration():
            
            new_timestamp_ms = 0
            
        
        self.Seek( new_timestamp_ms )
        
    
    def SetCanvasType( self, canvas_type ):
        
        self._canvas_type = canvas_type
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            shortcut_set = 'media_viewer_media_window'
            
        else:
            
            shortcut_set = 'preview_media_window'
            
        
        self._my_shortcut_handler.SetShortcuts( [ shortcut_set ] )
        
    
    def SetLogLevel( self, level: str ):
        
        self._player.set_loglevel( level )
        
    
    def SetMedia( self, media, start_paused = False ):
        
        if media == self._media:
            
            return
            
        
        self._file_is_loaded = False
        self._disallow_seek_on_this_file = False
        
        self._media = media
        
        self._times_to_play_gif = 0
        
        if self._media is not None and self._media.GetMime() == HC.IMAGE_GIF and not HG.client_controller.new_options.GetBoolean( 'always_loop_gifs' ):
            
            hash = self._media.GetHash()
            
            path = HG.client_controller.client_files_manager.GetFilePath( hash, HC.IMAGE_GIF )
            
            self._times_to_play_gif = HydrusImageHandling.GetTimesToPlayGIF( path )
            
        
        self._current_seek_to_start_count = 0
        
        if self._media is None:
            
            self._player.pause = True
            
            if len( self._player.playlist ) > 0:
                
                try:
                    
                    self._player.command( 'playlist-remove', 'current' )
                    
                except:
                    
                    pass # sometimes happens after an error--screw it
                    
                
            
        else:
            
            hash = self._media.GetHash()
            mime = self._media.GetMime()
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( hash, mime )
            
            self._player.visibility = 'always'
            
            self._stop_for_slideshow = False
            
            self._player.pause = True
            
            try:
                
                self._player.loadfile( path )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            self._player.volume = self._GetCorrectCurrentVolume()
            self._player.mute = self._GetCorrectCurrentMute()
            self._player.pause = start_paused
            
        
    
    def StopForSlideshow( self, value ):
        
        self._stop_for_slideshow = value
        
    
    def UpdateAudioMute( self ):
        
        self._player.mute = self._GetCorrectCurrentMute()
        

    def UpdateAudioVolume( self ):
        
        self._player.volume = self._GetCorrectCurrentVolume()
        
    
    def UpdateConf( self ):
        
        mpv_config_path = HG.client_controller.GetMPVConfPath()
        
        if not os.path.exists( mpv_config_path ):
            
            default_mpv_config_path = HG.client_controller.GetDefaultMPVConfPath()
            
            if not os.path.exists( default_mpv_config_path ):
                
                HydrusData.ShowText( 'There is no default mpv configuration file to load! Perhaps there is a problem with your install?' )
                
                return
                
            else:
                
                HydrusPaths.MirrorFile( default_mpv_config_path, mpv_config_path )
                
            
        
        #To load an existing config file (by default it doesn't load the user/global config like standalone mpv does):
        
        load_f = getattr( mpv, '_mpv_load_config_file', None )
        
        if load_f is not None and callable( load_f ):
            
            try:
                
                load_f( self._player.handle, mpv_config_path.encode( 'utf-8' ) ) # pylint: disable=E1102
                
            except Exception as e:
                
                HydrusData.ShowText( 'MPV could not load its configuration file! This was probably due to an invalid parameter value inside the conf. The error follows:' )
                
                HydrusData.ShowException( e )
                
            
        else:
            
            HydrusData.Print( 'Was unable to load mpv.conf--has the MPV API changed?' )
            
        
    
