from qtpy import QtCore as QC

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.media import ClientGUIMediaControls

class CanvasFrame( CAC.ApplicationCommandProcessorMixin, ClientGUITopLevelWindows.FrameThatResizesWithHovers ):
    
    def __init__( self, parent, set_parent = False ):            
        
        if set_parent:
            
            # child of auto-resolution dialog, modal gubbins requires ancestry
            parent_to_set = parent
            
        else:
            
            # Parent is set to None here so that this window shows up as a separate entry on the taskbar
            parent_to_set = None
            
        
        super().__init__( parent_to_set, 'hydrus client media viewer', 'media_viewer' )
        
        self._canvas_window: ClientGUICanvas.CanvasWithHovers | None = None
        self._we_are_hidden_and_cleaning_up_before_destroy = False
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'media_viewer' ] )
        
        CG.client_controller.gui.RegisterCanvasFrameReference( self )
        
        self.destroyed.connect( CG.client_controller.gui.MaintainCanvasFrameReferences )
        
        self._was_maximised_before_fullscreen = True
        
    
    def _NotifyCanvasHasDestroyedAllMediaWindows( self ):
        
        if self._we_are_hidden_and_cleaning_up_before_destroy:
            
            if self.ReadyToDestroy():
                
                self.close()
                
            
        
    
    def moveEvent( self, event ):
        
        # manually calling SaveTLW on moveEvent fixes a bug that does not save the position of the window when it is moved, but not resized, by Windows Snap™
        # but it's probably useful on all platforms with window movement keys so removing #if HC.PLATFORM_WINDOWS
        ClientGUITopLevelWindows.SaveTLWSizeAndPosition( self, self._frame_key )
        
        super().moveEvent( event )
        
    
    def ReadyToDestroy( self ):
        
        if self._canvas_window is not None:
            
            return self._canvas_window.ReadyToDestroy()
            
        
        return True
        
    
    def closeEvent( self, event ):
        
        if self._we_are_hidden_and_cleaning_up_before_destroy:
            
            if self.ReadyToDestroy():
                
                event.accept()
                
            else:
                
                event.ignore()
                
                CG.client_controller.CallLaterQtSafe( self, 5.0, 'closing old media viewer safety check', self.close )
                
            
            return
            
        
        if self._canvas_window is not None:
            
            if not self._canvas_window.CanConsiderAClose():
                
                event.ignore()
                
                return
                
            
            if not self._canvas_window.UserOKToClose():
                
                event.ignore()
                
                return
                
            
            self._canvas_window.NotifyWeAreClosing()
            
            # WE ARE CLOSING
            
            # only affect media viewer TLWs
            if CG.client_controller.new_options.GetBoolean( 'save_window_size_and_position_on_close' ):
                
                ClientGUITopLevelWindows.SaveTLWSizeAndPosition( self, self._frame_key )
                
            
            self._canvas_window.CleanBeforeDestroy()
            
            super().closeEvent( event )
            
            if self.ReadyToDestroy():
                
                event.accept()
                
            else:
                
                self.hide()
                
                self._we_are_hidden_and_cleaning_up_before_destroy = True
                
                event.ignore()
                
                # just in case somehow the signal doesn't fire
                CG.client_controller.CallLaterQtSafe( self, 5.0, 'closing old media viewer safety check', self.close )
                
            
        else:
            
            super().closeEvent( event )
            
        
    
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
        
    
    def GetCanvas( self ) -> ClientGUICanvas.CanvasWithHovers | None:
        
        return self._canvas_window
        
    
    def PauseMedia( self ):
        
        self._canvas_window.PauseMedia()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_EXIT_APPLICATION:
                
                CG.client_controller.gui.TryToExit()
                
            elif action == CAC.SIMPLE_EXIT_APPLICATION_FORCE_MAINTENANCE:
                
                CG.client_controller.gui.TryToExit( force_shutdown_maintenance = True )
                
            elif action == CAC.SIMPLE_RESTART_APPLICATION:
                
                CG.client_controller.gui.TryToExit( restart = True )
                
            elif action == CAC.SIMPLE_HIDE_TO_SYSTEM_TRAY:
                
                CG.client_controller.gui.HideToSystemTray()
                
            elif action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER:
                
                self.close()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW:
                
                self.FullscreenSwitch()
                
            elif action == CAC.SIMPLE_FLIP_DARKMODE:
                
                CG.client_controller.gui.FlipDarkmode()
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_MUTE:
                
                ClientGUIMediaControls.SetMute( ClientGUIMediaControls.AUDIO_GLOBAL, True )
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_UNMUTE:
                
                ClientGUIMediaControls.SetMute( ClientGUIMediaControls.AUDIO_GLOBAL, False )
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_MUTE_FLIP:
                
                ClientGUIMediaControls.FlipMute( ClientGUIMediaControls.AUDIO_GLOBAL )
                
            elif action == CAC.SIMPLE_GLOBAL_PROFILE_MODE_FLIP:
                
                CG.client_controller.gui.FlipProfileMode( 'db' )
                
            elif action == CAC.SIMPLE_GLOBAL_FORCE_ANIMATION_SCANBAR_SHOW:
                
                CG.client_controller.new_options.FlipBoolean( 'force_animation_scanbar_show' )
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def minimumSizeHint( self ):
        
        return QC.QSize( 240, 180 )
        
    
    def sizeHint( self ):
        
        # TODO: you should be able to delete or alter this in some nice way when you move to a proper layout for this guy
        return QC.QSize( 1280, 720 )
        
    
    def SetCanvas( self, canvas_window: ClientGUICanvas.CanvasWithHovers ):
        
        self._canvas_window = canvas_window
        
        self._canvas_window.haveDestroyedAllMediaWindows.connect( self._NotifyCanvasHasDestroyedAllMediaWindows )
        
        self.setFocusProxy( self._canvas_window )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._canvas_window, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        ClientGUITopLevelWindows.SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self.show()
        
        # just to reinforce, as Qt sometimes sets none focus for this window until it goes off and back on
        self._canvas_window.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    
    def TakeFocusForUser( self ):
        
        self.activateWindow()
        
        self._canvas_window.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    
