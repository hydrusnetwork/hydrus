import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUICanvas
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import QtPorting as QP

class CanvasFrame( ClientGUITopLevelWindows.FrameThatResizesWithHovers ):
    
    def __init__( self, parent ):            
        
        # Parent is set to None here so that this window shows up as a separate entry on the taskbar
        ClientGUITopLevelWindows.FrameThatResizesWithHovers.__init__( self, None, 'hydrus client media viewer', 'media_viewer' )
        
        self._canvas_window = None
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media_viewer' ] )
        
        HG.client_controller.gui.RegisterCanvasFrameReference( self )
        
        self.destroyed.connect( HG.client_controller.gui.MaintainCanvasFrameReferences )
        
    
    def closeEvent( self, event ):
        
        if self._canvas_window is not None:
            
            can_close = self._canvas_window.TryToDoPreClose()
            
            if can_close:
                
                self._canvas_window.CleanBeforeDestroy()
                
                ClientGUITopLevelWindows.FrameThatResizes.closeEvent( self, event )
                
            else:
                
                event.ignore()
                
            
        else:
            
            ClientGUITopLevelWindows.FrameThatResizes.closeEvent( self, event )
            
        
    
    def FullscreenSwitch( self ):
        
        if self.isFullScreen():
            
            self.showNormal()
            
        else:
            
            if HC.PLATFORM_MACOS:
                
                return
                
            
            self.showFullScreen()
            
        
        self._canvas_window.ResetMediaWindowCenterPosition()
        
    
    def PauseMedia( self ):
        
        self._canvas_window.PauseMedia()
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'exit_application':
                
                HG.client_controller.gui.TryToSaveAndClose()
                
            elif action == 'exit_application_force_maintenance':
                
                HG.client_controller.gui.TryToSaveAndClose( force_shutdown_maintenance = True )
                
            elif action == 'restart_application':
                
                HG.client_controller.gui.TryToSaveAndClose( restart = True )
                
            elif action == 'hide_to_system_tray':
                
                HG.client_controller.gui.HideToSystemTray()
                
            elif action == 'close_media_viewer':
                
                self.close()
                
            elif action == 'switch_between_fullscreen_borderless_and_regular_framed_window':
                
                self.FullscreenSwitch()
                
            elif action == 'flip_darkmode':
                
                HG.client_controller.gui.FlipDarkmode()
                
            elif action == 'global_audio_mute':
                
                ClientGUIMediaControls.SetMute( ClientGUIMediaControls.AUDIO_GLOBAL, True )
                
            elif action == 'global_audio_unmute':
                
                ClientGUIMediaControls.SetMute( ClientGUIMediaControls.AUDIO_GLOBAL, False )
                
            elif action == 'global_audio_mute_flip':
                
                ClientGUIMediaControls.FlipMute( ClientGUIMediaControls.AUDIO_GLOBAL )
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def minimumSizeHint( self ):
        
        return QC.QSize( 240, 180 )
        
    
    def SetCanvas( self, canvas_window: ClientGUICanvas.CanvasWithDetails ):
        
        self._canvas_window = canvas_window
        
        self.setFocusProxy( self._canvas_window )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._canvas_window )
        
        self.setLayout( vbox )
        
        ClientGUITopLevelWindows.SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self.show()
        
        # just to reinforce, as Qt sometimes sets none focus for this window until it goes off and back on
        self._canvas_window.setFocus( QC.Qt.OtherFocusReason )
        
    
    def TakeFocusForUser( self ):
        
        self.activateWindow()
        
        self._canvas_window.setFocus( QC.Qt.OtherFocusReason )
        
    
