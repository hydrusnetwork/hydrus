import typing

from qtpy import QtCore as QC

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas

class CanvasFrame( ClientGUITopLevelWindows.FrameThatResizesWithHovers ):
    
    def __init__( self, parent ):            
        
        # Parent is set to None here so that this window shows up as a separate entry on the taskbar
        ClientGUITopLevelWindows.FrameThatResizesWithHovers.__init__( self, None, 'hydrus client media viewer', 'media_viewer' )
        
        self._canvas_window = None
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media_viewer' ] )
        
        HG.client_controller.gui.RegisterCanvasFrameReference( self )
        
        self.destroyed.connect( HG.client_controller.gui.MaintainCanvasFrameReferences )
        
        self._was_maximised_before_fullscreen = True
        
    
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
            
            if self._was_maximised_before_fullscreen:
                
                self.showMaximized()
                
            else:
                
                self.showNormal()
                
            
        else:
            
            if HC.PLATFORM_MACOS:
                
                return
                
            
            self._was_maximised_before_fullscreen = self.isMaximized()
            
            self.showFullScreen()
            
        
        self._canvas_window.ResetMediaWindowCenterPosition()
        
    
    def PauseMedia( self ):
        
        self._canvas_window.PauseMedia()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_EXIT_APPLICATION:
                
                HG.client_controller.gui.TryToExit()
                
            elif action == CAC.SIMPLE_EXIT_APPLICATION_FORCE_MAINTENANCE:
                
                HG.client_controller.gui.TryToExit( force_shutdown_maintenance = True )
                
            elif action == CAC.SIMPLE_RESTART_APPLICATION:
                
                HG.client_controller.gui.TryToExit( restart = True )
                
            elif action == CAC.SIMPLE_HIDE_TO_SYSTEM_TRAY:
                
                HG.client_controller.gui.HideToSystemTray()
                
            elif action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER:
                
                self.close()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW:
                
                self.FullscreenSwitch()
                
            elif action == CAC.SIMPLE_FLIP_DARKMODE:
                
                HG.client_controller.gui.FlipDarkmode()
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_MUTE:
                
                ClientGUIMediaControls.SetMute( ClientGUIMediaControls.AUDIO_GLOBAL, True )
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_UNMUTE:
                
                ClientGUIMediaControls.SetMute( ClientGUIMediaControls.AUDIO_GLOBAL, False )
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_MUTE_FLIP:
                
                ClientGUIMediaControls.FlipMute( ClientGUIMediaControls.AUDIO_GLOBAL )
                
            elif action == CAC.SIMPLE_GLOBAL_PROFILE_MODE_FLIP:
                
                HG.client_controller.FlipProfileMode()
                
            elif action == CAC.SIMPLE_GLOBAL_FORCE_ANIMATION_SCANBAR_SHOW:
                
                HG.client_controller.new_options.FlipBoolean( 'force_animation_scanbar_show' )
                
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
        
    
