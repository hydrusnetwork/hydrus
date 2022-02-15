from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

AUDIO_GLOBAL = 0
AUDIO_MEDIA_VIEWER = 1
AUDIO_PREVIEW = 2

volume_types_str_lookup = {}

volume_types_str_lookup[ AUDIO_GLOBAL ] = 'global'
volume_types_str_lookup[ AUDIO_MEDIA_VIEWER ] = 'media viewer'
volume_types_str_lookup[ AUDIO_PREVIEW ] = 'preview'

volume_types_to_option_names = {}

volume_types_to_option_names[ AUDIO_GLOBAL ] = ( 'global_audio_mute', 'global_audio_volume' )
volume_types_to_option_names[ AUDIO_MEDIA_VIEWER ] = ( 'media_viewer_audio_mute', 'media_viewer_audio_volume' )
volume_types_to_option_names[ AUDIO_PREVIEW ] = ( 'preview_audio_mute', 'preview_audio_volume' )

def ChangeVolume( volume_type, volume ):
    
    ( mute_option_name, volume_option_name ) = volume_types_to_option_names[ volume_type ]
    
    HG.client_controller.new_options.SetInteger( volume_option_name, volume )
    
    HG.client_controller.pub( 'new_audio_volume' )
    
def FlipMute( volume_type ):
    
    ( mute_option_name, volume_option_name ) = volume_types_to_option_names[ volume_type ]
    
    HG.client_controller.new_options.FlipBoolean( mute_option_name )
    
    HG.client_controller.pub( 'new_audio_mute' )
    
def SetMute( volume_type, mute ):
    
    ( mute_option_name, volume_option_name ) = volume_types_to_option_names[ volume_type ]
    
    HG.client_controller.new_options.SetBoolean( mute_option_name, mute )
    
    HG.client_controller.pub( 'new_audio_mute' )
    
class AudioMuteButton( ClientGUICommon.BetterBitmapButton ):
    
    def __init__( self, parent, volume_type ):
        
        self._volume_type = volume_type
        
        pixmap = self._GetCorrectPixmap()
        
        ClientGUICommon.BetterBitmapButton.__init__( self, parent, pixmap, FlipMute, self._volume_type )
        
        HG.client_controller.sub( self, 'UpdateMute', 'new_audio_mute' )
        
    
    def _GetCorrectPixmap( self ):
        
        ( mute_option_name, volume_option_name ) = volume_types_to_option_names[ self._volume_type ]
        
        if HG.client_controller.new_options.GetBoolean( mute_option_name ):
            
            pixmap = CC.global_pixmaps().mute
            
        else:
            
            pixmap = CC.global_pixmaps().sound
            
        
        return pixmap
        
    
    def UpdateMute( self ):
        
        pixmap = self._GetCorrectPixmap()
        
        ClientGUIFunctions.SetBitmapButtonBitmap( self, pixmap )
        
    
class VolumeControl( QW.QWidget ):
    
    def __init__( self, parent, canvas_type, direction = 'down' ):
        
        QW.QWidget.__init__( self, parent )
        
        self._canvas_type = canvas_type
        
        self._global_mute = AudioMuteButton( self, AUDIO_GLOBAL )
        
        self._global_mute.setToolTip( 'Global mute/unmute' )
        self._global_mute.setFocusPolicy( QC.Qt.NoFocus )
        
        vbox = QP.VBoxLayout( margin = 0, spacing = 0 )
        
        QP.AddToLayout( vbox, self._global_mute, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._popup_window = self._PopupWindow( self, canvas_type, direction = direction )
        
    
    def enterEvent( self, event ):
        
        if not self.isVisible():
            
            return
            
        
        self._popup_window.DoShowHide()
        
        event.ignore()
        
    
    def leaveEvent( self, event ):
        
        if not self.isVisible():
            
            return
            
        
        self._popup_window.DoShowHide()
        
        event.ignore()
        
    
    def PopupIsVisible( self ):
        
        return self._popup_window.isVisible()
        
    
    class _PopupWindow( QW.QFrame ):
        
        def __init__( self, parent, canvas_type, direction = 'down' ):
            
            QW.QFrame.__init__( self, parent )
            
            self._canvas_type = canvas_type
            
            self._direction = direction
            
            self.setWindowFlags( QC.Qt.Tool | QC.Qt.FramelessWindowHint )
            
            self.setAttribute( QC.Qt.WA_ShowWithoutActivating )
            
            if self._canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
                
                option_to_use = 'media_viewer_uses_its_own_audio_volume'
                volume_type = AUDIO_MEDIA_VIEWER
                
            else:
                
                option_to_use = 'preview_uses_its_own_audio_volume'
                volume_type = AUDIO_PREVIEW
                
            
            self._specific_mute = AudioMuteButton( self, volume_type )
            
            self._specific_mute.setToolTip( 'Mute/unmute: {}'.format( CC.canvas_type_str_lookup[ self._canvas_type ] ) )
            
            if HG.client_controller.new_options.GetBoolean( option_to_use ):
                
                slider_volume_type = volume_type
                
            else:
                
                slider_volume_type = AUDIO_GLOBAL
                
            
            self._volume = VolumeSlider( self, slider_volume_type )
            
            vbox = QP.VBoxLayout()
            
            if self._direction == 'down':
                
                QP.AddToLayout( vbox, self._specific_mute, CC.FLAGS_CENTER )
                QP.AddToLayout( vbox, self._volume, CC.FLAGS_CENTER )
                
            else:
                
                QP.AddToLayout( vbox, self._volume, CC.FLAGS_CENTER )
                QP.AddToLayout( vbox, self._specific_mute, CC.FLAGS_CENTER )
                
            
            #vbox.setAlignment( self._volume, QC.Qt.AlignHCenter )
            #vbox.setAlignment( self._specific_mute, QC.Qt.AlignHCenter )
            
            self.setLayout( vbox )
            
            self.hide()
            
            self.adjustSize()
            
        
        def DoShowHide( self ):
            
            parent = self.parentWidget()
            
            horizontal_offset = ( self.width() - parent.width() ) // 2 
            
            if self._direction == 'down':
                
                pos = parent.mapToGlobal( parent.rect().bottomLeft() )
                
            else:
                
                pos = parent.mapToGlobal( parent.rect().topLeft() - self.rect().bottomLeft() )
                
            
            pos.setX( pos.x() - horizontal_offset )
            
            self.move( pos )
            
            over_parent = ClientGUIFunctions.MouseIsOverWidget( parent )
            over_me = ClientGUIFunctions.MouseIsOverWidget( self )
            
            should_show = over_parent or over_me
            
            if should_show:
                
                self.show()
                
            else:
                
                self.hide()
                
            
        
        def leaveEvent( self, event ):
            
            if not self.isVisible():
                
                return
                
            
            self.DoShowHide()
            
            event.ignore()
            
        
    
class VolumeSlider( QW.QSlider ):
    
    def __init__( self, parent, volume_type ):
        
        QW.QSlider.__init__( self, parent )
        
        self._volume_type = volume_type
        
        self.setOrientation( QC.Qt.Vertical )
        self.setTickInterval( 1 )
        self.setTickPosition( QW.QSlider.TicksBothSides )
        self.setRange( 0, 100 )
        
        volume = self._GetCorrectValue()
        
        self.setValue( volume )
        
        self.valueChanged.connect( self._VolumeSliderMoved )
        
    
    def _GetCorrectValue( self ):
        
        ( mute_option_name, volume_option_name ) = volume_types_to_option_names[ self._volume_type ]
        
        return HG.client_controller.new_options.GetInteger( volume_option_name )
        
    
    def _VolumeSliderMoved( self ):
        
        ChangeVolume( self._volume_type, self.value() )
        
    
    def UpdateMute( self ):
        
        volume = self._GetCorrectValue()
        
        self.setValue( volume )
        
    
