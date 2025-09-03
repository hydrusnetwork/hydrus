import locale
import os
import traceback
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusAnimationHandling

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.media import ClientGUIMediaControls
from hydrus.client.gui.media import ClientGUIMediaVolume
from hydrus.client.media import ClientMedia

MPV_IS_AVAILABLE = True
MPV_MODULE_NOT_FOUND = False
MPV_IMPORT_ERROR = 'MPV seems fine!'

try:
    
    import mpv
    
except Exception as e:
    
    MPV_IS_AVAILABLE = False
    MPV_MODULE_NOT_FOUND = isinstance( e, ModuleNotFoundError )
    MPV_IMPORT_ERROR = traceback.format_exc()
    

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

def EmergencyDumpOutGlobal( problem_widget: QW.QWidget, probably_crashy, too_many_events_queued, reason ):
    
    # this is Qt thread so we can talk to this guy no prob
    MPVHellBasket.instance().emergencyDumpOut.emit( problem_widget, probably_crashy, too_many_events_queued, reason )
    

def log_message_is_fine_bro( message ):
    
    return True in (
        'rescan-external-files' in message,
        'LZW decode failed' in message # borked gif headers
    )
    

def log_handler_factory( mpv_widget: QW.QWidget ):
    
    def log_handler( loglevel, component, message ):
        
        # ok important bug dude, if you have multiple mpv windows and hence log handlers, then somehow the mpv dll or python-mpv wrapper is delivering at least some log events to the wrong player's event loop
        # so my mapping here to preserve the mpv widget for a particular log message and then dump out the player in emergency is only going to work half the time
        
        if log_message_is_fine_bro( message ) and not HG.mpv_report_mode:
            
            return
            
        
        if loglevel == 'error':
            
            probably_crashy_tests = []
            too_many_events_queued_tests = []
            
            if 'ffmpeg' in component:
                
                probably_crashy_tests = [
                    'Invalid NAL unit size' in message,
                    'Error splitting the input' in message
                ]
                
            elif False:
                
                # this is the core of the 'too many events' error hook that gave us false positive problems
                # at the moment, this error will propagate to dumpout and be logged as a generic error, but maybe we'll want to silence it in the end as a 'fine bro' message
                # instead of catching the logspam, attack the original problem!
                
                too_many_events_queued_tests = [
                    'Too many events queued' in message
                ]
                
            
            probably_crashy = True in probably_crashy_tests
            too_many_events_queued = True in too_many_events_queued_tests
            
            CG.client_controller.CallBlockingToQt( CG.client_controller.gui, EmergencyDumpOutGlobal, mpv_widget, probably_crashy, too_many_events_queued, f'{component}: {message}' )
            
        
        HydrusData.DebugPrint( '[MPV {}] {}: {}'.format( loglevel, component, message ) )
        
    
    return log_handler
    

MPVShutdownEventType = QP.registerEventType()

class MPVShutdownEvent( QC.QEvent ):
    
    def __init__( self ):
        
        super().__init__( MPVShutdownEventType )
        
    

MPVFileLoadedEventType = QP.registerEventType()

class MPVFileLoadedEvent( QC.QEvent ):
    
    def __init__( self ):
        
        super().__init__( MPVFileLoadedEventType )
        
    

MPVLogEventType = QP.registerEventType()

class MPVLogEvent( QC.QEvent ):
    
    def __init__( self, player, event ):
        
        super().__init__( MPVLogEventType )
        
        self.player = player
        self.event = event
        
    

MPVFileSeekedEventType = QP.registerEventType()

class MPVFileSeekedEvent( QC.QEvent ):
    
    def __init__( self ):
        
        super().__init__( MPVFileSeekedEventType )
        
    

class MPVHellBasket( QC.QObject ):
    
    emergencyDumpOut = QC.Signal( QW.QWidget, bool, bool, str )
    my_instance = None
    
    def __init__( self ):
        
        super().__init__()
        
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
        
        super().__init__( parent )
        
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
        self._black_png_path = HydrusStaticDir.GetStaticPath( 'blacksquare.png' )
        self._hydrus_png_path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        self._currently_in_media_load_error_state = False
        
        global LOCALE_IS_SET
        
        if not LOCALE_IS_SET:
            
            # This is necessary since PyQT stomps over the locale settings needed by libmpv.
            # This needs to happen after importing PyQT before creating the first mpv.MPV instance.
            locale.setlocale( locale.LC_NUMERIC, 'C' )
            
            LOCALE_IS_SET = True
            
        
        self.setAttribute( QC.Qt.WidgetAttribute.WA_DontCreateNativeAncestors )
        self.setAttribute( QC.Qt.WidgetAttribute.WA_NativeWindow )
        
        self._time_media_load_started = 0.0
        
        # loglevels: fatal, error, debug
        loglevel = 'debug' if HG.mpv_report_mode else 'error'
        
        log_handler = log_handler_factory( self )
        
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
        
        self.UpdateConfAndCoreOptions()
        
        # this makes black screen for audio (rather than transparent)
        self._player.force_window = True
        
        # this actually propagates up to the OS-level sound mixer lmao, otherwise defaults to ugly hydrus filename
        self._player.title = 'hydrus mpv player'
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
        self.setMouseTracking( True )
        #self.setFocusPolicy(QC.Qt.FocusPolicy.StrongFocus)#Needed to get key events
        self._player.input_cursor = False#Disable mpv mouse move/click event capture
        self._player.input_vo_keyboard = False#Disable mpv key event capture, might also need to set input_x11_keyboard
        
        self._media = None
        
        self._file_header_is_loaded = False
        self._disallow_seek_on_this_file = False
        self._have_shown_human_error_on_this_file = False
        
        self._times_to_play_animation = 0
        
        self._current_second_of_seek_restarts = 0.0
        self._number_of_restarts_this_second = 0
        self._current_seek_to_start_count = 0
        
        self._InitialiseMPVCallbacks()
        
        self.destroyed.connect( self._player.terminate )
        
        CG.client_controller.sub( self, 'UpdateAudioMute', 'new_audio_mute' )
        CG.client_controller.sub( self, 'UpdateAudioVolume', 'new_audio_volume' )
        CG.client_controller.sub( self, 'UpdateConfAndCoreOptions', 'notify_new_options' )
        CG.client_controller.sub( self, 'SetLogLevel', 'set_mpv_log_level' )
        
        self.installEventFilter( self )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [], catch_mouse = True )
        
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
        
        def event_handler( event: mpv.MpvEvent ):
            
            event_type = event.event_id.value
            
            if event_type == mpv.MpvEventID.SEEK:
                
                QW.QApplication.postEvent( self, MPVFileSeekedEvent() )
                
            elif event_type == mpv.MpvEventID.FILE_LOADED:
                
                QW.QApplication.postEvent( self, MPVFileLoadedEvent() )
                
            elif event_type == mpv.MpvEventID.SHUTDOWN:
                
                if QP.isValid( self ):
                    
                    QW.QApplication.postEvent( self, MPVShutdownEvent() )
                    
                
            
        
        self._player.register_event_callback( event_handler )
        
    
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
                
                if self._media is not None and current_timestamp_s is not None and current_timestamp_s < 0.1:
                    
                    current_second = HydrusTime.GetNow()
                    
                    if current_second != self._current_second_of_seek_restarts:
                        
                        self._current_second_of_seek_restarts = current_second
                        self._number_of_restarts_this_second = 0
                        
                    
                    self._current_seek_to_start_count += 1
                    
                    self._number_of_restarts_this_second += 1
                    
                    if self._media.HasDuration():
                        
                        # if we say no more than 20 restarts allowed, what about the 33ms two-frame animation!
                        number_of_restarts_allowed = max( 20, ( 1000 / self._media.GetDurationMS() ) * 5 )
                        
                    else:
                        
                        number_of_restarts_allowed = 20
                        
                    
                    if self._number_of_restarts_this_second > number_of_restarts_allowed:
                        
                        self.EmergencyDumpOut( self, True, False, 'This file was caught in a rewind loop, it is probably damaged.' )
                        
                        return True
                        
                    
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
        
    
    def EmergencyDumpOut( self, problem_widget: QW.QWidget, probably_crashy, too_many_events_queued, reason ):
        
        # we had to rewrite this thing due to some threading/loop/event issues at the lower mpv level
        # it now broadcasts to all mpv widgets, so we could unload all on very serious errors, but for now I've hacked in the problem widget handle so we'll only do it for us right now
        
        if self != problem_widget:
            
            return
            
        
        original_media = self._media
        
        if original_media is None:
            
            return
            
        
        if too_many_events_queued:
            # I replaced this with the _number_of_restarts_this_second stuff in the eventFilter on seek spam
            # TODO: If we have no further use for this, you can delete it from the whole dump-out chain mate
            
            return
            
        
        media_line = '\n\nIts hash is: {}'.format( original_media.GetHash().hex() )
        
        if probably_crashy or too_many_events_queued:
            
            self.ClearMedia()
            
        
        if probably_crashy:
            
            global damaged_file_hashes
            
            hash = original_media.GetHash()
            
            if hash in damaged_file_hashes:
                
                return
                
            
            damaged_file_hashes.add( hash )
            
        
        if not self._have_shown_human_error_on_this_file:
            
            self._have_shown_human_error_on_this_file = True
            
            if probably_crashy:
                
                message = f'Sorry, this media appears to have a serious problem! To avoid crashes, I have unloaded it and will not allow it again this boot. The file is possibly truncated or otherwise corrupted, but if you think it is good, please send it to hydev for more testing. The specific errors should be written to the log.{media_line}'
                
                HydrusData.DebugPrint( message )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', f'{message}\n\nThe first error was:\n\n{reason}' )
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetFiles( [ original_media.GetHash() ], 'MPV-crasher' )
                
                CG.client_controller.pub( 'message', job_status )
                
            elif too_many_events_queued:
                
                message = f'Sorry, this media appears to have choked MPV! To avoid instability, I have unloaded it! You can try to load it again, but if it fails over and over, please send it to hydev for more testing. If this error happens when the file loops, you might like to try the Playlist-Loop DEBUG checkbox in "options->media playback". The specific errors should be written to the log.{media_line}'
                
                HydrusData.DebugPrint( message )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', f'{message}\n\nThe first error was:\n\n{reason}' )
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetFiles( [ original_media.GetHash() ], 'MPV-choker' )
                
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
            
        
        time_index_s = HydrusTime.SecondiseMSFloat( time_index_ms )
        
        # TODO: could also say like 'if it is between current time +/-5ms to catch odd frame float rounding stuff, but this would need careful testing with previous/next frame navigation etc..
        # mostly this guy just catches the 0.0 start point
        if time_index_s == self._player.time_pos:
            
            return
            
        
        self._number_of_restarts_this_second = 0 # patching an error hook elsewhere
        
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
            
            self._player.pause = True
            
            if self._media is None:
                
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
                
                media = self._media
                
                def work_callable():
                    
                    hash = media.GetHash()
                    mime = media.GetMime()
                    
                    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
                    
                    return ( media, path )
                    
                
                def publish_callable( media_and_path ):
                    
                    ( media, path ) = media_and_path
                    
                    if media != self._media:
                        
                        return
                        
                    
                    self._have_shown_human_error_on_this_file = False
                    
                    # some videos have an audio channel that is silent. hydrus thinks these dudes are 'no audio', but when we throw them at mpv, it may play audio for them
                    # would be fine, you think, except in one reported case this causes scratches and pops and hell whitenoise
                    # so let's see what happens here
                    mute_override = not self._media.HasAudio()
                    
                    self._player.visibility = 'always'
                    
                    self._stop_for_slideshow = False
                    
                    mime = self._media.GetMime()
                    
                    if mime in HC.VIEWABLE_ANIMATIONS and not CG.client_controller.new_options.GetBoolean( 'always_loop_gifs' ):
                        
                        if mime == HC.ANIMATION_APNG:
                            
                            self._times_to_play_animation = HydrusAnimationHandling.GetTimesToPlayAPNG( path )
                            
                        else:
                            
                            self._times_to_play_animation = HydrusAnimationHandling.GetTimesToPlayPILAnimation( path )
                            
                        
                    
                    self._time_media_load_started = HydrusTime.GetNowFloat()
                    
                    try:
                        
                        self._player.loadfile( path )
                        
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                    
                    self._player.volume = ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type )
                    self._player.mute = mute_override or ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type )
                    self._player.pause = start_paused
                    
                    self.update()
                    
                
                def errback_ui_cleanup_callable():
                    
                    self.SetMedia( None )
                    
                
                job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
                
                job.start()
                
            
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
            
        
    
    def UpdateConfAndCoreOptions( self ):
        
        # this fixes at least one instance of the 100% CPU 'too many events queued' bug, which was down to bad APNG EOF rewind navigation
        loop_playlist = CG.client_controller.new_options.GetBoolean( 'mpv_loop_playlist_instead_of_file' )
        
        self._player[ 'loop' ] = not loop_playlist
        self._player[ 'loop-playlist' ] = loop_playlist
        
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
            
        
    
