from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class AudioPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #self._media_viewer_uses_its_own_audio_volume = QW.QCheckBox( self )
        self._preview_uses_its_own_audio_volume = QW.QCheckBox( self )
        
        self._has_audio_label = QW.QLineEdit( self )
        
        #
        
        tt = 'If unchecked, this media canvas will use the \'global\' audio volume slider. If checked, this media canvas will have its own separate one.'
        tt += '\n' * 2
        tt += 'Keep this on if you would like the preview viewer to be quieter than the main media viewer.'
        
        #self._media_viewer_uses_its_own_audio_volume.setChecked( self._new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ) )
        self._preview_uses_its_own_audio_volume.setChecked( self._new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ) )
        
        #self._media_viewer_uses_its_own_audio_volume.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        self._preview_uses_its_own_audio_volume.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._has_audio_label.setText( self._new_options.GetString( 'has_audio_label' ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'The preview window has its own volume: ', self._preview_uses_its_own_audio_volume ) )
        #rows.append( ( 'The media viewer has its own volume: ', self._media_viewer_uses_its_own_audio_volume ) )
        rows.append( ( 'Label for files with audio: ', self._has_audio_label ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        #self._new_options.SetBoolean( 'media_viewer_uses_its_own_audio_volume', self._media_viewer_uses_its_own_audio_volume.isChecked() )
        self._new_options.SetBoolean( 'preview_uses_its_own_audio_volume', self._preview_uses_its_own_audio_volume.isChecked() )
        
        self._new_options.SetString( 'has_audio_label', self._has_audio_label.text() )
        
    
