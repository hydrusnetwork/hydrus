from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusPaths
import os
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
import locale

try:
    
    import mpv
    
    MPV_IS_AVAILABLE = True
    
except:
    
    MPV_IS_AVAILABLE = False

def GetClientAPIVersionString():
    
    try:
        
        ( major, minor ) = mpv._mpv_client_api_version()
        
        return '{}.{}'.format( major, minor )
        
    except:
        
        return 'unknown'
        
    
#Not sure how well this works with hardware acceleration. This just renders to a QWidget. In my tests it seems fine, even with vdpau video out, but I'm not 100% sure it actually uses hardware acceleration.
#Here is an example on how to render into a QOpenGLWidget instead: https://gist.github.com/cosven/b313de2acce1b7e15afda263779c0afc
class mpvWidget( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        # This is necessary since PyQT stomps over the locale settings needed by libmpv.
        # This needs to happen after importing PyQT before creating the first mpv.MPV instance.
        locale.setlocale( locale.LC_NUMERIC, 'C' )
        
        self.setAttribute( QC.Qt.WA_DontCreateNativeAncestors )
        self.setAttribute( QC.Qt.WA_NativeWindow )
        
        self._player = mpv.MPV( wid = str( int( self.winId() ) ), log_handler = print, loglevel = 'fatal' )
        
        # hydev notes on OSC:
        # OSC is by default off, default input bindings are by default off
        # difficult to get this to intercept mouse/key events naturally, so you have to pipe them to the window with 'command', but this is not excellent
        # general recommendation when using libmpv is to just implement your own stuff anyway, so let's do that for prototype
        
        #self._player[ 'input-default-bindings' ] = True
        
        mpv_config_path = os.path.join( HC.STATIC_DIR, 'mpv-conf', 'mpv.conf' )
        
        #To load an existing config file (by default it doesn't load the user/global config like standalone mpv does):
        if hasattr( mpv, '_mpv_load_config_file' ):
            
            mpv._mpv_load_config_file( self._player.handle, mpv_config_path.encode( 'utf-8' ) )
            
        else:
            
            HydrusData.Print( 'Failed to load mpv.conf--has the API changed?' )
            
        
        #self._player.osc = True #Set to enable the mpv UI. Requires that mpv captures mouse/key events, otherwise it won't work.
        
        self._player.loop = True
        
        # this makes black screen for audio (rather than transparent)
        self._player.force_window = True
        
        self.setMouseTracking( True )#Needed to get mouse move events
        #self.setFocusPolicy(QC.Qt.StrongFocus)#Needed to get key events
        self._player.input_cursor = False#Disable mpv mouse move/click event capture
        self._player.input_vo_keyboard = False#Disable mpv key event capture, might also need to set input_x11_keyboard
        
        self._media = None
        
        self._has_played_once_through = False
        
        self.destroyed.connect( self._player.terminate )
        
        HG.client_controller.sub( self, 'UpdateGlobalAudioMute', 'new_global_audio_mute' )
        HG.client_controller.sub( self, 'UpdateGlobalAudioVolume', 'new_global_audio_volume' )
        

    def GetAnimationBarStatus( self ):
        
        buffer_indices = None
        
        if self._media is None:
            
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
                
                if num_frames is None:
                    
                    current_frame_index = 0
                    
                else:
                    
                    current_frame_index = int( round( ( current_timestamp_ms / self._media.GetDuration() ) * num_frames ) )
                    
                
            
            paused = self._player.pause
            
        
        return ( current_frame_index, current_timestamp_ms, paused, buffer_indices )
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        command = 'frame-step'
        
        if direction == 1:
            
            command = 'frame-step'
            
        elif direction == -1:
            
            command = 'frame-back-step'
            
        
        self._player.command( command )
        
    
    def Seek( self, time_index_ms ):
        
        time_index_s = time_index_ms / 1000
        
        self._player.seek( time_index_s, reference = 'absolute' )
        
    
    def HasPlayedOnceThrough( self ):
        
        return self._has_played_once_through
        

    def IsPlaying( self ):
        
        return not self._player.pause
        
    
    def mouseDoubleClickEvent( self, event ):
        
        if not ( event.modifiers() & ( QC.Qt.ShiftModifier | QC.Qt.ControlModifier | QC.Qt.AltModifier) ):
            
            if event.button() == QC.Qt.LeftButton:
                
                self.Pause()
                
                hash = self._media.GetHash()
                mime = self._media.GetMime()
                
                client_files_manager = HG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                new_options = HG.client_controller.new_options
                
                launch_path = new_options.GetMimeLaunch( mime )
                
                HydrusPaths.LaunchFile( path, launch_path )
                
                event.accept()
                
                return
                
            
        
        event.ignore()
        

    def mouseMoveEvent( self, event ):
        
        # same deal here as with mousereleaseevent--osc is non-interactable with commands, so let's not use it for now
        #self._player.command( 'mouse', event.x(), event.y() )
        
        event.ignore()
        
    
    def mousePressEvent( self, event ):
        
        if not ( event.modifiers() & ( QC.Qt.ShiftModifier | QC.Qt.ControlModifier | QC.Qt.AltModifier) ):
            
            if event.button() == QC.Qt.LeftButton:
                
                self.PausePlay()
                
                self.parentWidget().BeginDrag()
                
                return
                
            
        
        event.ignore()
        
    
    def mouseReleaseEvent( self, event ):
        
        # left index = 0
        # right index = 2
        # the issue with using this guy is it sends a mouse press or mouse down event, and the OSC only responds to mouse up
        
        #self._player.command( 'mouse', event.x(), event.y(), index, 'single' )
        
        event.ignore()
        

    def Pause( self ):
        
        self._player.pause = True
        

    def PausePlay( self ):
        
        self._player.pause = not self._player.pause
        

    def Play( self ):
        
        self._player.pause = False
        

    def SetMedia( self, media, start_paused = False ):
        
        self._media = media
        
        if self._media is None:
            
            self._player.pause = True
            
            if len( self._player.playlist ) > 0:
                
                self._player.command( 'playlist-remove', 'current' )
                
            
        else:
            
            hash = self._media.GetHash()
            mime = self._media.GetMime()
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( hash, mime )
            
            self._has_played_once_through = False
            
            self._player.visibility = 'always'
            
            self._player.pause = True
            
            try:
                
                self._player.loadfile( path )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            self._player.volume = HG.client_controller.new_options.GetInteger( 'global_audio_volume' )
            self._player.mute = HG.client_controller.new_options.GetBoolean( 'global_audio_mute' )
            self._player.pause = start_paused
            
        
    
    def SetNoneMedia( self ):
        
        self.SetMedia( None )
        
    
    def UpdateGlobalAudioMute( self ):
        
        self._player.mute = HG.client_controller.new_options.GetBoolean( 'global_audio_mute' )
        

    def UpdateGlobalAudioVolume( self ):
        
        self._player.volume = HG.client_controller.new_options.GetInteger( 'global_audio_volume' )
        
