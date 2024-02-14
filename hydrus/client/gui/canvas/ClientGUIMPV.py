import locale
import os
import time
import traceback
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core.files import HydrusAnimationHandling

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIMedia
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUIMediaVolume
from hydrus.client.media import ClientMedia

mpv_failed_reason = 'MPV seems ok!'

try:
    
    import mpv
    
    MPV_IS_AVAILABLE = True
    
except Exception as e:
    
    mpv_failed_reason = traceback.format_exc()
    
    MPV_IS_AVAILABLE = False
    

damaged_file_hashes = set()

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

def EmergencyDumpOutGlobal( probably_crashy, reason ):
    
    # this is Qt thread so we can talk to this guy no prob
    MPVHellBasket.instance().emergencyDumpOut.emit( probably_crashy, reason )
    

def log_handler( loglevel, component, message ):
    
    # ok important bug dude, if you have multiple mpv windows and hence log handlers, then somehow the mpv dll or python-mpv wrapper is delivering at least some log events to the wrong player's event loop
    # so my mapping here to preserve the mpv widget for a particular log message and then dump out the player in emergency is only going to work half the time
    
    nah_it_is_fine_bro_tests = [
        'rescan-external-files' in message,
        'LZW decode failed' in message # borked gif headers
    ]
    
    if True in nah_it_is_fine_bro_tests and not HG.mpv_report_mode:
        
        return
        
    
    if loglevel == 'error' and 'ffmpeg' in component:
        
        probably_crashy_tests = [
            'Invalid NAL unit size' in message,
            'Error splitting the input' in message
        ]
        
        CG.client_controller.CallBlockingToQt( CG.client_controller.gui, EmergencyDumpOutGlobal, True in probably_crashy_tests, f'{component}: {message}' )
        
    
    HydrusData.DebugPrint( '[MPV {}] {}: {}'.format( loglevel, component, message ) )
    

MPVShutdownEventType = QP.registerEventType()

class MPVShutdownEvent( QC.QEvent ):
    
    def __init__( self ):
        
        QC.QEvent.__init__( self, MPVShutdownEventType )
        
    

MPVFileLoadedEventType = QP.registerEventType()

class MPVFileLoadedEvent( QC.QEvent ):
    
    def __init__( self ):
        
        QC.QEvent.__init__( self, MPVFileLoadedEventType )
        
    
'''
MPVLogEventType = QP.registerEventType()

class MPVLogEvent( QC.QEvent ):
    
    def __init__( self, player, event ):
        
        QC.QEvent.__init__( self, MPVLogEventType )
        
        self.player = player
        self.event = event
        
    
'''
MPVFileSeekedEventType = QP.registerEventType()

class MPVFileSeekedEvent( QC.QEvent ):
    
    def __init__( self ):
        
        QC.QEvent.__init__( self, MPVFileSeekedEventType )
        
    

class MPVHellBasket( QC.QObject ):
    
    emergencyDumpOut = QC.Signal( bool, str )
    my_instance = None
    
    def __init__( self ):
        
        QC.QObject.__init__( self )
        
        MPVHellBasket.my_instance = self
        
    
    @staticmethod
    def instance() -> 'MPVHellBasket':
        
        if MPVHellBasket.my_instance is None:
            
            MPVHellBasket.my_instance = MPVHellBasket()
            
        
        return MPVHellBasket.my_instance
        
    

LOCALE_IS_SET = False

#Not sure how well this works with hardware acceleration. This just renders to a QWidget. In my tests it seems fine, even with vdpau video out, but I'm not 100% sure it actually uses hardware acceleration.
#Here is an example on how to render into a QOpenGLWidget instead: https://gist.github.com/cosven/b313de2acce1b7e15afda263779c0afc
class MPVWidget( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    launchMediaViewer = QC.Signal()
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        CAC.ApplicationCommandProcessorMixin.__init__( self )
        
        self._canvas_type = CC.CANVAS_PREVIEW
        
        self._stop_for_slideshow = False
        
        # ok, if you talk to this object during an eventPaint while it is in various states of 'null', you'll get this instability problem:
        # QBackingStore::endPaint() called with active painter; did you forget to destroy it or call QPainter::end() on it?
        # simply calling a do-nothing GetAnimationBarStatus stub that returns immediately will cause this, so it must be some C++ wrapper magic triggering some during-paint reset/event-cycle/whatever
        #
        # #####
        # THUS, DO NOT EVER TALK TO THIS GUY DURING A paintEvent. fetch your data and call update() if it changed. Also, we now make sure _something_ is loaded as much as possible, even if it is a black square png
        # #####
        #
        self._black_png_path = os.path.join( HC.STATIC_DIR, 'blacksquare.png' )
        self._hydrus_png_path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        self._currently_in_media_load_error_state = False
        
        global LOCALE_IS_SET
        
        if not LOCALE_IS_SET:
            
            # This is necessary since PyQT stomps over the locale settings needed by libmpv.
            # This needs to happen after importing PyQT before creating the first mpv.MPV instance.
            locale.setlocale( locale.LC_NUMERIC, 'C' )
            
            LOCALE_IS_SET = True
            
        
        self.setAttribute( QC.Qt.WA_DontCreateNativeAncestors )
        self.setAttribute( QC.Qt.WA_NativeWindow )
        
        # loglevels: fatal, error, debug
        loglevel = 'debug' if HG.mpv_report_mode else 'error'
        
        self._player = mpv.MPV(
            wid = str( int( self.winId() ) ),
            log_handler = log_handler,
            loglevel = loglevel
        )
        
        # hydev notes on OSC:
        # OSC is by default off, default input bindings are by default off
        # difficult to get this to intercept mouse/key events naturally, so you have to pipe them to the window with 'command', but this is not excellent
        # general recommendation when using libmpv is to just implement your own stuff anyway, so let's do that for prototype
        
        # self._player[ 'osd-level' ] = 1
        # self._player[ 'input-default-bindings' ] = True
        
        self._previous_conf_content_bytes = b''
        
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
        
        self._file_header_is_loaded = False
        self._disallow_seek_on_this_file = False
        self._have_shown_human_error_on_this_file = False
        
        self._times_to_play_animation = 0
        
        self._current_seek_to_start_count = 0
        
        self._InitialiseMPVCallbacks()
        
        self.destroyed.connect( self._player.terminate )
        
        CG.client_controller.sub( self, 'UpdateAudioMute', 'new_audio_mute' )
        CG.client_controller.sub( self, 'UpdateAudioVolume', 'new_audio_volume' )
        CG.client_controller.sub( self, 'UpdateConf', 'notify_new_options' )
        CG.client_controller.sub( self, 'SetLogLevel', 'set_mpv_log_level' )
        
        self.installEventFilter( self )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [], catch_mouse = True )
        
        try:
            
            self.we_are_newer_api = float( GetClientAPIVersionString() ) >= 2.0
            
        except:
            
            self.we_are_newer_api = False
            
        
        MPVHellBasket.instance().emergencyDumpOut.connect( self.EmergencyDumpOut )
        
        try:
            
            self._player.loadfile( self._black_png_path )
            
        except mpv.ShutdownError:
            
            # fugg, libmpv core probably shut down already. not much we can do but panic
            self._currently_in_media_load_error_state = True
            
        
    
    def _GetAudioOptionNames( self ):
        
        if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            if CG.client_controller.new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ):
                
                return ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_MEDIA_VIEWER ]
                
            
        elif self._canvas_type == CC.CANVAS_PREVIEW:
            
            if CG.client_controller.new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ):
                
                return ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_PREVIEW ]
                
            
        
        return ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_GLOBAL ]
        
    
    def _HandleLoadError( self ):
        
        # file failed to load, and we are going to start getting what seem to be C++ level paintEvent exceptions after the GUI object is touched by code and then asked for repaints
        
        self._file_header_is_loaded = False
        self._currently_in_media_load_error_state = True
        
        try:
            
            self._player.loadfile( self._hydrus_png_path )
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            HydrusData.ShowText( 'While trying to handle another error, the mpv window could not show the error fallback png! Program may be unstable, restart ASAP recommended.' )
            
        
        if self._media is not None:
            
            HydrusData.ShowText( f'The file with hash "{self._media.GetHash().hex()}" seems to have failed to load in mpv. In order to preserve program stability, I have unloaded it immediately!' )
            
        
    
    def _InitialiseMPVCallbacks( self ):
        
        player = self._player
        
        # note that these happen on the mpv mainloop, not UI code, so we need to post events to stay stable
        
        @player.event_callback( mpv.MpvEventID.SEEK )
        def seek_event( event ):
            
            QW.QApplication.instance().postEvent( self, MPVFileSeekedEvent() )
            
        
        @player.event_callback( mpv.MpvEventID.FILE_LOADED )
        def file_loaded_event( event ):
            
            QW.QApplication.instance().postEvent( self, MPVFileLoadedEvent() )
            
        
        @player.event_callback( mpv.MpvEventID.SHUTDOWN )
        def file_started_event( event ):
            
            app = QW.QApplication.instance()
            
            if app is not None and QP.isValid( self ):
                
                app.postEvent( self, MPVShutdownEvent() )
                
            
        
        '''
        @player.event_callback( mpv.MpvEventID.LOG_MESSAGE )
        def log_event( event ):
            
            QW.QApplication.instance().postEvent( self, MPVLogEvent( player, event ) )
            
        '''
    
    def _LooksLikeALoadError( self ):
        
        # as an additional note for the error we are handling here, this isn't catching something like 'error: truncated gubbins', but instead the 'verbose' debug level message of 'ffmpeg can't handle this apng's format, update ffmpeg'
        # what happens in this state is the media is unloaded and the self._player.path goes from a valid path to None
        # the extra fun is that self._player.path starts as None even after self._player.loadfile and may not be the valid path get as of the LoadedEvent. that event is sent when headers are read, not data
        # so we need to detect when the data is actually loaded, after the .path was (briefly) something valid, and then switches back to None
        # thankfully, it seems on the dump-out unload, the playlist is unset, and this appears to be the most reliable indicator of a problem and an mpv with nothing currently loaded!
        
        try:
            
            if self._player.path is None:
                
                playlist = self._player.playlist
                
                if len( playlist ) == 0:
                    
                    return True
                    
                
                for item in playlist:
                    
                    if 'current' in item:
                        
                        return False
                        
                    
                
                return True
                
            
            return False
            
        except mpv.ShutdownError:
            
            return True
            
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == MPVFileLoadedEventType:
                
                if self._player.path is None:
                    
                    if self._LooksLikeALoadError():
                        
                        self._HandleLoadError()
                        
                    
                
                if not self._currently_in_media_load_error_state:
                    
                    self._file_header_is_loaded = True
                    
                
                return True
                
            elif event.type() == MPVFileSeekedEventType:
                
                if not self._file_header_is_loaded:
                    
                    return True
                    
                
                current_timestamp_s = self._player.time_pos
                
                if self._media is not None and current_timestamp_s is not None and current_timestamp_s <= 1.0:
                    
                    self._current_seek_to_start_count += 1
                    
                    if self._stop_for_slideshow:
                        
                        self.Pause()
                        
                    
                    if self._times_to_play_animation != 0 and self._current_seek_to_start_count >= self._times_to_play_animation:
                        
                        self.Pause()
                        
                    
                
                return True
                
            elif event.type() == MPVShutdownEventType:
                
                self.setVisible( False )
                
            
        except mpv.ShutdownError:
            
            return True
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def EmergencyDumpOut( self, probably_crashy, reason ):
        
        # we had to rewrite this thing due to some threading/loop/event issues at the lower mpv level
        # when we have an emergency, we now broadcast to all mpv players at once, they all crash out, to be safe
        
        original_media = self._media
        
        if original_media is None:
            
            # this MPV window is probably not the one that had a problem
            return
            
        
        media_line = '\n\nIts hash is: {}'.format( original_media.GetHash().hex() )
        
        if probably_crashy:
            
            self.ClearMedia()
            
            global damaged_file_hashes
            
            hash = original_media.GetHash()
            
            if hash in damaged_file_hashes:
                
                return
                
            
            damaged_file_hashes.add( hash )
            
        
        if not self._have_shown_human_error_on_this_file:
            
            self._have_shown_human_error_on_this_file = True
            
            if probably_crashy:
                
                message = f'Sorry, this media appears to have a serious problem! To avoid crashes, MPV will not attempt to play it! The file is possibly truncated or otherwise corrupted, but if you think it is good, please send it to hydev for more testing. The specific errors should be written to the log.{media_line}'
                
                HydrusData.DebugPrint( message )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', f'{message}\n\nThe first error was:\n\n{reason}' )
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetFiles( [ original_media.GetHash() ], 'MPV-crasher' )
                
                CG.client_controller.pub( 'message', job_status )
                
            else:
                
                message = f'A media loaded in MPV appears to have had an error. This may be not a big deal, or it may be a crash. The specific errors should be written after this message. They are not positively known as crashy, but if you are getting crashes, please send the file and these errors to hydev so he can test his end.{media_line}'
                
                HydrusData.DebugPrint( message )
                
            
    
    def GetAnimationBarStatus( self ):
        
        if self._file_header_is_loaded and self._LooksLikeALoadError():
            
            self._HandleLoadError()
            
        
        try:
            
            if self._media is None or not self._file_header_is_loaded or self._currently_in_media_load_error_state:
                
                return None
                
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
                        
                        current_frame_index = int( round( ( current_timestamp_ms / self._media.GetDurationMS() ) * num_frames ) )
                        
                        current_frame_index = min( current_frame_index, num_frames - 1 )
                        
                    
                    current_timestamp_ms = min( current_timestamp_ms, self._media.GetDurationMS() )
                    
                
                paused = self._player.pause
                
            
        except mpv.ShutdownError:
            
            return None
            
        
        buffer_indices = None
        
        return ( current_frame_index, current_timestamp_ms, paused, buffer_indices )
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        if not self._file_header_is_loaded:
            
            return
            
        
        command = 'frame-step'
        
        if direction == 1:
            
            command = 'frame-step'
            
        elif direction == -1:
            
            command = 'frame-back-step'
            
        
        try:
            
            self._player.command( command )
            
        except mpv.ShutdownError:
            
            pass
            
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._current_seek_to_start_count > 0
        
    
    def IsPaused( self ):
        
        if self._currently_in_media_load_error_state:
            
            return True
            
        
        try:
            
            return self._player.pause
            
        except:
            
            # libmpv core probably shut down
            return True
            
        
    
    def paintEvent(self, event):
        
        return
        
    
    def Pause( self ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        try:
            
            self._player.pause = True
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        

    def PausePlay( self ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        try:
            
            self._player.pause = not self._player.pause
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        

    def Play( self ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        try:
            
            self._player.pause = False
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        
    
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
                    
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_FILE_EXPLORER:
                
                if self._media is not None:
                    
                    self.Pause()
                    
                    ClientGUIMedia.OpenFileLocation( self._media )
                    
                
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
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        if not self._file_header_is_loaded:
            
            return
            
        
        if self._disallow_seek_on_this_file:
            
            return
            
        
        time_index_s = time_index_ms / 1000
        
        try:
            
            self._player.seek( time_index_s, reference = 'absolute', precision = 'exact' )
            
        except:
            
            self._disallow_seek_on_this_file = True
            
            # on some files, this seems to fail with a SystemError lmaoooo
            # with the same elegance, we will just pass all errors
            
        
    
    def SeekDelta( self, direction, duration_ms ):
        
        if self._media is None:
            
            return
            
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        if not self._file_header_is_loaded:
            
            return
            
        
        try:
            
            current_timestamp_s = self._player.time_pos
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            return
            
        
        
        if current_timestamp_s is None:
            
            return
            
        
        new_timestamp_ms = max( 0, ( current_timestamp_s * 1000 ) + ( direction * duration_ms ) )
        
        if new_timestamp_ms > self._media.GetDurationMS():
            
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
        
        try:
            
            self._player.set_loglevel( level )
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        
    
    def SetMedia( self, media: typing.Optional[ ClientMedia.MediaSingleton ], start_paused = False ):
        
        if media == self._media:
            
            return
            
        
        global damaged_file_hashes
        
        if media is not None and media.GetHash() in damaged_file_hashes:
            
            self.ClearMedia()
            
            return
            
        
        self._currently_in_media_load_error_state = False
        self._file_header_is_loaded = False
        self._disallow_seek_on_this_file = False
        self._times_to_play_animation = 0
        self._current_seek_to_start_count = 0
        
        self._media = media
        
        try:
            
            if self._media is None:
                
                self._player.pause = True
                
                self._player.loadfile( self._black_png_path )
                
                # old method. this does 'work', but null seems to be subtly dangerous in these accursed lands 
                '''
                if len( self._player.playlist ) > 0:
                    
                    try:
                        
                        self._player.command( 'stop' )
                        
                        # used to have this, it could raise errors if the load failed
                        # self._player.command( 'playlist-remove', 'current' )
                        
                    except Exception as e:
                        
                        HydrusData.PrintException( e )
                        
                        pass
                        
                    
                '''
                
            else:
                
                self._have_shown_human_error_on_this_file = False
                
                hash = self._media.GetHash()
                mime = self._media.GetMime()
                
                # some videos have an audio channel that is silent. hydrus thinks these dudes are 'no audio', but when we throw them at mpv, it may play audio for them
                # would be fine, you think, except in one reported case this causes scratches and pops and hell whitenoise
                # so let's see what happens here
                mute_override = not self._media.HasAudio()
                
                client_files_manager = CG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                self._player.visibility = 'always'
                
                self._stop_for_slideshow = False
                
                self._player.pause = True
                
                if mime in HC.VIEWABLE_ANIMATIONS and not CG.client_controller.new_options.GetBoolean( 'always_loop_gifs' ):
                    
                    if mime == HC.ANIMATION_GIF:
                        
                        self._times_to_play_animation = HydrusAnimationHandling.GetTimesToPlayPILAnimation( path )
                        
                    elif mime == HC.ANIMATION_APNG:
                        
                        self._times_to_play_animation = HydrusAnimationHandling.GetTimesToPlayAPNG( path )
                        
                    
                
                try:
                    
                    self._player.loadfile( path )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
                self._player.volume = ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type )
                self._player.mute = mute_override or ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type )
                self._player.pause = start_paused
                
            
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        
    
    def StopForSlideshow( self, value ):
        
        self._stop_for_slideshow = value
        
    
    def UpdateAudioMute( self ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        try:
            
            self._player.mute = ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type )
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        
        

    def UpdateAudioVolume( self ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        try:
            
            self._player.volume = ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type )
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        
    
    def UpdateConf( self ):
        
        mpv_config_path = CG.client_controller.GetMPVConfPath()
        
        if not os.path.exists( mpv_config_path ):
            
            default_mpv_config_path = CG.client_controller.GetDefaultMPVConfPath()
            
            if not os.path.exists( default_mpv_config_path ):
                
                HydrusData.ShowText( 'There is no default mpv configuration file to load! Perhaps there is a problem with your install?' )
                
                return
                
            else:
                
                HydrusPaths.MirrorFile( default_mpv_config_path, mpv_config_path )
                
            
        
        # let's touch mpv core functions as little ans possible
        
        with open( mpv_config_path, 'rb' ) as f:
            
            conf_content_bytes = f.read()
            
        
        if self._previous_conf_content_bytes == conf_content_bytes:
            
            return
            
        else:
            
            self._previous_conf_content_bytes = conf_content_bytes
            
        
        # To load an existing config file (by default it doesn't load the user/global config like standalone mpv does):
        
        load_f = getattr( mpv, '_mpv_load_config_file', None )
        
        if load_f is not None and callable( load_f ):
            
            try:
                
                load_f( self._player.handle, mpv_config_path.encode( 'utf-8' ) ) # pylint: disable=E1102
                
            except mpv.ShutdownError:
                
                pass
                
            except Exception as e:
                
                HydrusData.ShowText( 'MPV could not load its configuration file! This was probably due to an invalid parameter value inside the conf. The error follows:' )
                
                HydrusData.ShowException( e )
                
            
        else:
            
            HydrusData.Print( 'Was unable to load mpv.conf--has the MPV API changed?' )
            
        
    
