import locale
import os
import threading
import traceback

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
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
    
except Exception as e_mpv:
    
    MPV_IS_AVAILABLE = False
    MPV_MODULE_NOT_FOUND = isinstance( e_mpv, ModuleNotFoundError )
    MPV_IMPORT_ERROR = traceback.format_exc()
    

damaged_file_hashes = set()

def GetClientAPIVersionString():
    
    try:
        
        ( major, minor ) = mpv._mpv_client_api_version()
        
        return '{}.{}'.format( major, minor )
        
    except Exception as e:
        
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
    MPVEmergencyDumpOutSignaller.instance().emergencyDumpOut.emit( probably_crashy, reason )
    

def log_message_is_fine_bro( component, message ):
    
    return True in (
        'rescan-external-files' in message,
        'LZW decode failed' in message, # borked gif headers
        'Too many events queued' in message # used to be a problem, now no longer a big deal with the async mediator
    )
    

def log_message_is_probably_crashy_bro( component, message ):
    
    probably_crashy_tests = []
    
    if 'ffmpeg' in component:
        
        probably_crashy_tests = [
            'Invalid NAL unit size' in message,
            'Error splitting the input' in message
        ]
        
    elif 'ao/' in component: # ao/wasapi, potentially others
        
        probably_crashy_tests = [
            'There are no playback devices available' in message
        ]
        
    
    return True in probably_crashy_tests
    

def log_handler( loglevel, component, message ):
    
    # IMPORTANT ISSUE! if you have multiple mpv windows and hence log handlers, then somehow the mpv dll or python-mpv wrapper seems to only use the first or something
    # so we need to push to all players when we have a big deal problem and we'll just deal with it
    
    if log_message_is_fine_bro( component, message ) and not HG.mpv_report_mode:
        
        return
        
    
    if loglevel in ( 'error', 'fatal' ):
        
        if loglevel == 'fatal':
            
            probably_crashy = True
            
        else:
            
            probably_crashy = log_message_is_probably_crashy_bro( component, message )
            
        
        try:
            
            CG.client_controller.CallBlockingToQtTLW( EmergencyDumpOutGlobal, probably_crashy, f'{component}: {message}' )
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        
    
    HydrusData.DebugPrint( '[MPV {}] {}: {}'.format( loglevel, component, message ) )
    

class MPVEmergencyDumpOutSignaller( QC.QObject ):
    
    emergencyDumpOut = QC.Signal( bool, str )
    my_instance = None
    
    def __init__( self ):
        
        super().__init__()
        
        MPVEmergencyDumpOutSignaller.my_instance = self
        
    
    @staticmethod
    def instance() -> 'MPVEmergencyDumpOutSignaller':
        
        if MPVEmergencyDumpOutSignaller.my_instance is None:
            
            MPVEmergencyDumpOutSignaller.my_instance = MPVEmergencyDumpOutSignaller()
            
        
        return MPVEmergencyDumpOutSignaller.my_instance
        
    

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
        
    

MPVPlaybackRestartedType = QP.registerEventType()

class MPVPlaybackRestarted( QC.QEvent ):
    
    def __init__( self ):
        
        super().__init__( MPVPlaybackRestartedType )
        
    

LOCALE_IS_SET = False

class MPVMediator( object ):
    
    def __init__( self, mpv_player: "mpv.MPV" ):
        
        self._mpv_player = mpv_player
        
    
    def BlockingTerminate( self ):
        
        self._mpv_player.terminate()
        
    
    def ForceStop( self ):
        
        self._mpv_player.stop()
        
    
    def GetPlaybackTime( self ):
        
        raise NotImplementedError()
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        raise NotImplementedError()
        
    
    def IsPaused( self ):
        
        raise NotImplementedError()
        
    
    def LoadFile( self, path ):
        
        raise NotImplementedError()
        
    
    def LooksLikeALoadError( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def NotifySeekComplete( self ):
        
        pass
        
    
    def ResetForNewMedia( self, paused: bool ):
        
        raise NotImplementedError()
        
    
    def Seek( self, time_pos, precise = True ):
        
        raise NotImplementedError()
        
    
    def SetLogLevel( self, value ):
        
        # this appears to be adjunct to the normal gubbins, no idea how to do this 'polite'
        self._mpv_player.set_loglevel( value )
        
    
    def SetPaused( self, value: bool ):
        
        raise NotImplementedError()
        
    

# this is the old sledgehammer interrogation, which some APIs may still need to use
class MPVMediatorRude( MPVMediator ):
    
    def __init__( self, mpv_player: "mpv.MPV" ):
        
        super().__init__( mpv_player )
        
        self.ResetForNewMedia( True )
        
        # this makes black screen for audio (rather than transparent)
        self._mpv_player.force_window = True
        
        # this actually propagates up to the OS-level sound mixer lmao, otherwise defaults to ugly hydrus filename
        self._mpv_player.title = 'hydrus mpv player'
        
        # Disable mpv mouse move/click event capture
        self._mpv_player.input_cursor = False
        
        # Disable mpv key event capture, might also need to set input_x11_keyboard
        self._mpv_player.input_vo_keyboard = False
        
    
    def LoadFile( self, path ):
        
        self._mpv_player.loadfile( path )
        
    
    def LooksLikeALoadError( self ) -> bool:
        
        # as an additional note for the error we are handling here, this isn't catching something like 'error: truncated gubbins', but instead the 'verbose' debug level message of 'ffmpeg can't handle this apng's format, update ffmpeg'
        # what happens in this state is the media is unloaded and the self._player.path goes from a valid path to None
        # the extra fun is that self._player.path starts as None even after self._player.loadfile and may not be the valid path get as of the LoadedEvent. that event is sent when headers are read, not data
        # so we need to detect when the data is actually loaded, after the .path was (briefly) something valid, and then switches back to None
        # thankfully, it seems on the dump-out unload, the playlist is unset, and this appears to be the most reliable indicator of a problem and an mpv with nothing currently loaded!
        
        try:
            
            if self._mpv_player.path is None:
                
                playlist = self._mpv_player.playlist
                
                if len( playlist ) == 0:
                    
                    return True
                    
                
                for item in playlist:
                    
                    if 'current' in item:
                        
                        return False
                        
                    
                
                return True
                
            
            return False
            
        except mpv.ShutdownError:
            
            return True
            
        
    
    def GetPlaybackTime( self ):
        
        return self._mpv_player.time_pos
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        command = 'frame-step'
        
        if direction == 1:
            
            command = 'frame-step'
            
        elif direction == -1:
            
            command = 'frame-back-step'
            
        
        self._mpv_player.command( command )
        
    
    def IsPaused( self ):
        
        return self._mpv_player.pause
        
    
    def ResetForNewMedia( self, paused: bool ):
        
        pass
        
    
    def Seek( self, time_pos, precise = True ):
        
        # this is a nice idea but it feels awful in practise
        # precision = 'exact' if precise else 'keyframes'
        
        precision = 'exact'
        
        self._mpv_player.seek( time_pos, reference = 'absolute', precision = precision )
        
    
    def SetPaused( self, value: bool ):
        
        self._mpv_player.pause = value
        
    

# ok so we are doing this because interrogating mpv from the Qt thread seems to raise serious exceptions inside the mpv dll that our faulthandler catches as a program halt
# we don't want to hit player.pause and friends _in general_
# we want to be nice, so we'll ask mpv to tell us about changes from its thread, when it is ready
class MPVMediatorPolite( MPVMediator ):
    
    def __init__( self, mpv_player: "mpv.MPV" ):
        
        super().__init__( mpv_player )
        
        self._lock = threading.Lock()
        self._properties = {}
        
        self._waiting_on_a_seek = False
        self._seek_time_and_precise_to_do_after_current_seek_done = None
        
        self.ResetForNewMedia( True )
        
        # this makes black screen for audio (rather than transparent)
        self._mpv_player.command_async( 'set', 'force-window', True )
        
        # this actually propagates up to the OS-level sound mixer lmao, otherwise defaults to ugly hydrus filename
        self._mpv_player.command_async( 'set', 'title', 'hydrus mpv player' )
        
        # Disable mpv mouse move/click event capture
        self._mpv_player.command_async( 'set', 'input-cursor', False )
        
        # Disable mpv key event capture, might also need to set input_x11_keyboard
        self._mpv_player.command_async( 'set', 'input-vo-keyboard', False )
        
        self._mpv_player.observe_property( 'pause', self._Catcher )
        self._mpv_player.observe_property( 'playback-time', self._Catcher )
        self._mpv_player.observe_property( 'path', self._Catcher )
        self._mpv_player.observe_property( 'playlist', self._Catcher )
        # self._mpv_player.observe_property( 'vo-configured', self._Catcher ) kind of useful, it seems to show when the video connection with Qt is initialised
        
    
    def _Catcher( self, name, value ):
        
        # this occurs in mpv thread
        
        with self._lock:
            
            self._properties[ name ] = value
            
        
    
    def GetPlaybackTime( self ):
        
        with self._lock:
            
            return self._properties[ 'playback-time' ]
            
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        command = 'frame-step'
        
        if direction == 1:
            
            command = 'frame-step'
            
        elif direction == -1:
            
            command = 'frame-back-step'
            
        
        self._mpv_player.command_async( command )
        
    
    def IsPaused( self ):
        
        with self._lock:
            
            return self._properties[ 'pause' ]
            
        
    
    def LoadFile( self, path ):
        
        mode = 'replace'
        options = ''
        
        fs_enc = mpv.fs_enc
        
        if self._mpv_player.mpv_version_tuple >= (0, 38, 0):
            
            index = -1
            
            self._mpv_player.command_async( 'loadfile', path.encode( fs_enc ), mode, index, options )
            
        else:
            
            self._mpv_player.command_async( 'loadfile', path.encode( fs_enc ), mode, options )
            
        
    
    def LooksLikeALoadError( self ) -> bool:
        
        # as an additional note for the error we are handling here, this isn't catching something like 'error: truncated gubbins', but instead the 'verbose' debug level message of 'ffmpeg can't handle this apng's format, update ffmpeg'
        # what happens in this state is the media is unloaded and the self._player.path goes from a valid path to None
        # the extra fun is that self._player.path starts as None even after self._player.loadfile and may not be the valid path get as of the LoadedEvent. that event is sent when headers are read, not data
        # so we need to detect when the data is actually loaded, after the .path was (briefly) something valid, and then switches back to None
        # thankfully, it seems on the dump-out unload, the playlist is unset, and this appears to be the most reliable indicator of a problem and an mpv with nothing currently loaded!
        
        with self._lock:
            
            if self._properties[ 'path' ] is None:
                
                playlist = self._properties[ 'playlist' ]
                
                if len( playlist ) == 0:
                    
                    return True
                    
                
                for item in playlist:
                    
                    if 'current' in item:
                        
                        return False
                        
                    
                
                return True
                
            
            return False
            
        
    
    def NotifySeekComplete( self ):
        
        with self._lock:
            
            self._waiting_on_a_seek = False
            
            if self._seek_time_and_precise_to_do_after_current_seek_done is not None:
                
                ( seek_time, precise ) = self._seek_time_and_precise_to_do_after_current_seek_done
                
                self._seek_time_and_precise_to_do_after_current_seek_done = None
                
            else:
                
                ( seek_time, precise ) = ( None, None )
                
            
        
        if seek_time is not None:
            
            self.Seek( seek_time, precise = precise )
            
        
    
    def ResetForNewMedia( self, paused: bool ):
        
        self._properties = {
            'pause' : paused,
            'playback-time' : 0,
            'path' : 'assumed_ok_and_not_none_to_start',
            'playlist' : []
        }
        
        self._waiting_on_a_seek = False
        self._seek_time_and_precise_to_do_after_current_seek_done = None
        
    
    def Seek( self, time_pos, precise = True ):
        
        # TODO: Update this guy to be Fast-Seek and End-Seek (sent on mouse-up), and make Fast-Seek do 'keyframes' instead of 'exact'
        
        with self._lock:
            
            if self._waiting_on_a_seek:
                
                self._seek_time_and_precise_to_do_after_current_seek_done = ( time_pos, precise )
                
                return
                
            
        
        # I tried using the callback here to catch when the seek was 'done', but catching/notifying on the 'playback restarted' event is what we actually wanted
        
        # this is a nice idea but it feels awful in practise
        # precision = 'exact' if precise else 'keyframes'
        
        precision = 'exact'
        
        self._mpv_player.command_async( 'seek', time_pos, 'absolute', precision )
        
        self._waiting_on_a_seek = True
        
    
    def SetPaused( self, value: bool ):
        
        # mpv_value = 'yes' if value else 'no'
        
        self._mpv_player.command_async( 'set', 'pause', value )
        
    

MPV_WIDGET_STATE_INITIALISING = 0
MPV_WIDGET_STATE_WORKING = 1
MPV_WIDGET_STATE_CLEANING_UP = 2
MPV_WIDGET_STATE_READY_TO_DESTROY = 3

#Not sure how well this works with hardware acceleration. This just renders to a QWidget. In my tests it seems fine, even with vdpau video out, but I'm not 100% sure it actually uses hardware acceleration.
#Here is an example on how to render into a QOpenGLWidget instead: https://gist.github.com/cosven/b313de2acce1b7e15afda263779c0afc
class MPVWidget( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    amInitialised = QC.Signal()
    launchMediaViewer = QC.Signal()
    readyForDestruction = QC.Signal()
    
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
        
        self._current_mpv_player_state = MPV_WIDGET_STATE_INITIALISING
        self._initialisation_start_time = HydrusTime.GetNow()
        self._cleanup_start_time = 0
        
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
        
        self._player = mpv.MPV(
            wid = str( int( self.winId() ) ),
            log_handler = log_handler,
            loglevel = loglevel
        )
        
        if CG.client_controller.new_options.GetBoolean( 'use_legacy_mpv_mediator' ):
            
            self._mpv_mediator = MPVMediatorRude( self._player )
            
        else:
            
            self._mpv_mediator = MPVMediatorPolite( self._player )
            
        
        # hydev notes on OSC:
        # OSC is by default off, default input bindings are by default off
        # difficult to get this to intercept mouse/key events naturally, so you have to pipe them to the window with 'command', but this is not excellent
        # general recommendation when using libmpv is to just implement your own stuff anyway, so let's do that for prototype
        
        # self._player[ 'osd-level' ] = 1
        # self._player[ 'input-default-bindings' ] = True
        
        self._previous_conf_content_bytes = b''
        
        self.UpdateConfAndCoreOptions()
        
        # pass up un-button-pressed mouse moves to parent, which wants to do cursor show/hide
        self.setMouseTracking( True )
        #self.setFocusPolicy(QC.Qt.FocusPolicy.StrongFocus)#Needed to get key events
        
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
            
        except Exception as e:
            
            self.we_are_newer_api = False
            
        
        MPVEmergencyDumpOutSignaller.instance().emergencyDumpOut.connect( self.EmergencyDumpOut )
        
        try:
            
            self._mpv_mediator.LoadFile( self._black_png_path )
            
        except mpv.ShutdownError:
            
            self._NotifyInitialisationIsDone()
            
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
            
            self._mpv_mediator.LoadFile( self._hydrus_png_path )
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            HydrusData.ShowText( 'While trying to handle another error, the mpv window could not show the error fallback png! Program may be unstable, restart ASAP recommended.' )
            
        
        if self._media is not None:
            
            HydrusData.ShowText( f'The file with hash "{self._media.GetHash().hex()}" seems to have failed to load in mpv. In order to preserve program stability, I have unloaded it immediately!' )
            
        
    
    def _InitialiseMPVCallbacks( self ):
        
        def qt_code( event_type ):
            
            if event_type == mpv.MpvEventID.SEEK:
                
                QW.QApplication.postEvent( self, MPVFileSeekedEvent() )
                
            elif event_type == mpv.MpvEventID.PLAYBACK_RESTART:
                
                QW.QApplication.postEvent( self, MPVPlaybackRestarted() )
                
            elif event_type == mpv.MpvEventID.FILE_LOADED:
                
                QW.QApplication.postEvent( self, MPVFileLoadedEvent() )
                
            elif event_type == mpv.MpvEventID.SHUTDOWN:
                
                QW.QApplication.postEvent( self, MPVShutdownEvent() )
                
            
        
        # note that these happen on the mpv mainloop, not UI code, so we need to post events to stay stable
        # lol when I started destroying mpv windows, this started failing because 'self' was already deleted C++ side. I just dump to Qt now w/e
        
        def event_handler( event: mpv.MpvEvent ):
            
            event_type = event.event_id.value
            
            CG.client_controller.CallAfterQtSafe( self, qt_code, event_type )
            
        
        self._player.register_event_callback( event_handler )
        
    
    def _NotifyInitialisationIsDone( self ):
        
        if self._current_mpv_player_state == MPV_WIDGET_STATE_INITIALISING:
            
            self._current_mpv_player_state = MPV_WIDGET_STATE_WORKING
            
            self.amInitialised.emit()
            
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == MPVFileLoadedEventType:
                
                self._NotifyInitialisationIsDone()
                
                if self._mpv_mediator.LooksLikeALoadError():
                    
                    self._HandleLoadError()
                    
                
                if not self._currently_in_media_load_error_state:
                    
                    self._file_header_is_loaded = True
                    
                
                return True
                
            elif event.type() == MPVFileSeekedEventType:
                
                # a seek has been started, not finished
                
                if not self._file_header_is_loaded:
                    
                    return True
                    
                
                current_timestamp_s = self._mpv_mediator.GetPlaybackTime()
                
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
                        
                        self.EmergencyDumpOut( True,'This file was caught in a rewind loop, it is probably damaged.' )
                        
                        return True
                        
                    
                    if self._stop_for_slideshow:
                        
                        self.Pause()
                        
                    
                    if self._times_to_play_animation != 0 and self._current_seek_to_start_count >= self._times_to_play_animation:
                        
                        self.Pause()
                        
                    
                
                return True
                
            elif event.type() == MPVPlaybackRestartedType:
                
                self._NotifyInitialisationIsDone()
                
                # a seek is now complete and mpv has loaded up the frame
                
                self._mpv_mediator.NotifySeekComplete()
                
                
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
        # it now broadcasts to all mpv widgets, so we could unload all on very serious errors, but for now I've hacked in the problem widget handle so we'll only do it for us right now
        
        self._NotifyInitialisationIsDone()
        
        original_media = self._media
        
        if original_media is None:
            
            return
            
        
        media_line = '\n\nIf you have multiple mpv windows playing media, you may see multiple versions of this message. Only one is correct. For this player, the hash is: {}'.format( original_media.GetHash().hex() )
        
        if probably_crashy:
            
            if HG.mpv_allow_crashy_files or HG.mpv_allow_crashy_files_silently:
                
                if not HG.mpv_allow_crashy_files_silently:
                    
                    hash = original_media.GetHash()
                    
                    HydrusData.ShowText( f'This file ({hash.hex()}) would have triggered the crash handling now.' )
                    
                
                return
                
            
            self._mpv_mediator.ForceStop()
            
            self.ClearMedia()
            
            global damaged_file_hashes
            
            hash = original_media.GetHash()
            
            if hash in damaged_file_hashes:
                
                return
                
            
            damaged_file_hashes.add( hash )
            
        
        if not self._have_shown_human_error_on_this_file:
            
            self._have_shown_human_error_on_this_file = True
            
            if probably_crashy:
                
                message = f'Sorry, this media appears to have a serious problem in mpv! To avoid crashes, I have unloaded it and will not allow it again this program boot. The file is possibly truncated or otherwise corrupted, but if you think it is good, please send it to hydev for more testing. The specific errors should be written to the log.{media_line}'
                
                HydrusData.DebugPrint( message )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', f'{message}\n\nThe first error was:\n\n{reason}' )
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetFiles( [ original_media.GetHash() ], 'MPV-crasher' )
                
                CG.client_controller.pub( 'message', job_status )
                
            else:
                
                message = f'A media loaded in MPV appears to have had an error. This may not be a big deal, or it may herald a crash. The specific errors should be written after this message. They are not positively known as crashy, but if you are getting crashes, please send the file and these errors to hydev so he can test his end.{media_line}'
                
                HydrusData.DebugPrint( message )
                
            
        
    
    def GetAnimationBarStatus( self ):
        
        if self._file_header_is_loaded and self._mpv_mediator.LooksLikeALoadError():
            
            self._HandleLoadError()
            
        
        try:
            
            if self._media is None or not self._file_header_is_loaded or self._currently_in_media_load_error_state:
                
                return None
                
            else:
                
                current_timestamp_s = self._mpv_mediator.GetPlaybackTime()
                
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
                    
                
                paused = self.IsPaused()
                
            
        except mpv.ShutdownError:
            
            return None
            
        
        buffer_indices = None
        
        return ( current_frame_index, current_timestamp_ms, paused, buffer_indices )
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        if not self._file_header_is_loaded:
            
            return
            
        
        try:
            
            self._mpv_mediator.GotoPreviousOrNextFrame( direction )
            
        except mpv.ShutdownError:
            
            pass
            
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._current_seek_to_start_count > 0
        
    
    def IsInitialised( self ):
        
        INITIALISE_TOOK_TOO_LONG_PERIOD = 180
        
        return self._current_mpv_player_state != MPV_WIDGET_STATE_INITIALISING or HydrusTime.TimeHasPassed( self._initialisation_start_time + INITIALISE_TOOK_TOO_LONG_PERIOD )
        
    
    def IsPaused( self ):
        
        if self._currently_in_media_load_error_state:
            
            return True
            
        
        return self._mpv_mediator.IsPaused()
        
    
    def paintEvent(self, event):
        
        return
        
    
    def Pause( self ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        try:
            
            self._mpv_mediator.SetPaused( True )
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        

    def PausePlay( self ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        try:
            
            self._mpv_mediator.SetPaused( not self._mpv_mediator.IsPaused() )
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        

    def Play( self ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        try:
            
            self._mpv_mediator.SetPaused( False )
            
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
        
    
    def ReadyForDestruction( self ):
        
        TERMINATE_TOOK_TOO_LONG_PERIOD = 180
        
        return self._current_mpv_player_state == MPV_WIDGET_STATE_READY_TO_DESTROY or HydrusTime.TimeHasPassed( self._cleanup_start_time + TERMINATE_TOOK_TOO_LONG_PERIOD )
        
    
    def Seek( self, time_index_ms, precise = True ):
        
        if self._currently_in_media_load_error_state:
            
            return
            
        
        if not self._file_header_is_loaded:
            
            return
            
        
        if self._disallow_seek_on_this_file:
            
            return
            
        
        time_index_s = HydrusTime.SecondiseMSFloat( time_index_ms )
        
        # TODO: could also say like 'if it is between current time +/-5ms to catch odd frame float rounding stuff, but this would need careful testing with previous/next frame navigation etc..
        # mostly this guy just catches the 0.0 start point
        if time_index_s == self._mpv_mediator.GetPlaybackTime():
            
            return
            
        
        self._number_of_restarts_this_second = 0 # patching an error hook elsewhere
        
        try:
            
            self._mpv_mediator.Seek( time_index_s, precise = precise )
            
        except Exception as e:
            
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
            
            current_timestamp_s = self._mpv_mediator.GetPlaybackTime()
            
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
            
            self._mpv_mediator.SetLogLevel( level )
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        
    
    def SetMedia( self, media: ClientMedia.MediaSingleton | None, start_paused = False ):
        
        if media == self._media:
            
            return
            
        
        global damaged_file_hashes
        
        if media is not None and media.GetHash() in damaged_file_hashes and not HG.mpv_allow_crashy_files and not HG.mpv_allow_crashy_files_silently:
            
            self.ClearMedia()
            
            return
            
        
        self._mpv_mediator.ResetForNewMedia( start_paused )
        
        self._currently_in_media_load_error_state = False
        self._file_header_is_loaded = False
        self._disallow_seek_on_this_file = False
        self._times_to_play_animation = 0
        self._current_seek_to_start_count = 0
        
        self._media = media
        
        try:
            
            self._mpv_mediator.SetPaused( True )
            
            if self._media is None:
                
                self._mpv_mediator.LoadFile( self._black_png_path )
                
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
                        
                        self._mpv_mediator.LoadFile( path )
                        
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                    
                    self._player.volume = ClientGUIMediaVolume.GetCorrectCurrentVolume( self._canvas_type )
                    self._player.mute = mute_override or ClientGUIMediaVolume.GetCorrectCurrentMute( self._canvas_type )
                    self._mpv_mediator.SetPaused( start_paused )
                    
                    self.update()
                    
                
                def errback_callable( etype, value, tb ):
                    
                    if etype == HydrusExceptions.FileMissingException:
                        
                        hash = media.GetHash()
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Missing File!', f'This file, "{hash.hex()}", is missing!' )
                        
                    else:
                        
                        HydrusData.ShowText( 'Unknown MPV File Load Error:' )
                        HydrusData.ShowExceptionTuple( etype, value, tb, do_wait = False )
                        
                    
                    self.SetMedia( None )
                    
                
                job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable )
                
                job.start()
                
            
        except mpv.ShutdownError:
            
            # libmpv core probably shut down
            pass
            
        
    
    def StartCleanBeforeDestroy( self ):
        
        self._current_mpv_player_state = MPV_WIDGET_STATE_CLEANING_UP
        self._cleanup_start_time = HydrusTime.GetNow()
        
        mpv_mediator = self._mpv_mediator
        
        def work_callable():
            
            mpv_mediator.BlockingTerminate()
            
            return 1
            
        
        def publish_callable( _ ):
            
            self._current_mpv_player_state = MPV_WIDGET_STATE_READY_TO_DESTROY
            
            self.readyForDestruction.emit()
            
        
        def errback_callable( etype, value, tb ):
            
            HydrusData.ShowText( 'Unable to terminate mpv instance:' )
            HydrusData.ShowExceptionTuple( etype, value, tb, do_wait = False )
            
            self._current_mpv_player_state = MPV_WIDGET_STATE_READY_TO_DESTROY
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable )
        
        job.start()
        
    
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
        
        if self._player.handle is None or self._current_mpv_player_state in ( MPV_WIDGET_STATE_CLEANING_UP, MPV_WIDGET_STATE_READY_TO_DESTROY ):
            
            return
            
        
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
            
        
    
