from . import ClientGUIMenus
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP
import os

SystemTrayAvailable = QW.QSystemTrayIcon.isSystemTrayAvailable

class ClientSystemTrayIcon( QW.QSystemTrayIcon ):
    
    flip_show_ui = QC.Signal()
    flip_pause_network_jobs = QC.Signal()
    flip_pause_subscription_jobs = QC.Signal()
    highlight = QC.Signal()
    exit_client = QC.Signal()
    
    def __init__( self, parent: QW.QWidget ):
        
        QW.QSystemTrayIcon.__init__( self, parent )
        
        self._ui_is_currently_shown = True
        self._should_always_show = False
        self._network_traffic_paused = False
        self._subscriptions_paused = False
        
        png_path = os.path.join( HC.STATIC_DIR, 'hydrus_non-transparent.png' )
        
        self.setIcon( QG.QIcon( png_path ) )
        
        self.activated.connect( self._WasActivated )
        
        self._RegenerateMenu()
        
    
    def _RegenerateMenu( self ):
        
        # I'm not a qwidget, but a qobject, so use my parent for this
        parent_widget = self.parent()
        
        new_menu = QW.QMenu( parent_widget )
        
        label = 'hide' if self._ui_is_currently_shown else 'show'
        
        ClientGUIMenus.AppendMenuItem( new_menu, label, 'Hide or show the hydrus client', self.flip_show_ui.emit )
        
        ClientGUIMenus.AppendSeparator( new_menu )
        
        label = 'unpause network traffic' if self._network_traffic_paused else 'pause network traffic'
        
        ClientGUIMenus.AppendMenuItem( new_menu, label, 'Pause/resume network traffic', self.flip_pause_network_jobs.emit )
        
        label = 'unpause subscriptions' if self._subscriptions_paused else 'pause subscriptions'
        
        ClientGUIMenus.AppendMenuItem( new_menu, label, 'Pause/resume subscriptions', self.flip_pause_subscription_jobs.emit )
        
        ClientGUIMenus.AppendSeparator( new_menu )
        
        ClientGUIMenus.AppendMenuItem( new_menu, 'exit', 'Close the hydrus client', self.exit_client.emit )
        
        #
        
        old_menu = self.contextMenu()
        
        self.setContextMenu( new_menu )
        
        if old_menu is not None:
            
            ClientGUIMenus.DestroyMenu( parent_widget, old_menu )
            
        
    
    def _UpdateShowSelf( self ) -> bool:
        
        menu_regenerated = False
        
        should_show = self._should_always_show or not self._ui_is_currently_shown
        
        if should_show != self.isVisible():
            
            self.setVisible( should_show )
            
            if should_show:
                
                # apparently context menu needs to be regenerated on re-show
                
                self._RegenerateMenu()
                
                menu_regenerated = True
                
            
        
        return menu_regenerated
        
    
    def _WasActivated( self, activation_reason ):
        
        if activation_reason in ( QW.QSystemTrayIcon.Unknown, QW.QSystemTrayIcon.Trigger ):
            
            if self._ui_is_currently_shown:
                
                self.highlight.emit()
                
            else:
                
                self.flip_show_ui.emit()
                
            
        elif activation_reason in ( QW.QSystemTrayIcon.DoubleClick, QW.QSystemTrayIcon.MiddleClick ):
            
            self.flip_show_ui.emit()
            
        
    
    def SetNetworkTrafficPaused( self, network_traffic_paused: bool ):
        
        if network_traffic_paused != self._network_traffic_paused:
            
            self._network_traffic_paused = network_traffic_paused
            
            self._RegenerateMenu()
            
        
    
    def SetSubscriptionsPaused( self, subscriptions_paused: bool ):
        
        if subscriptions_paused != self._subscriptions_paused:
            
            self._subscriptions_paused = subscriptions_paused
            
            self._RegenerateMenu()
            
        
    
    def SetUIIsCurrentlyShown( self, ui_is_currently_shown: bool ):
        
        if ui_is_currently_shown != self._ui_is_currently_shown:
            
            self._ui_is_currently_shown = ui_is_currently_shown
            
            menu_regenerated = self._UpdateShowSelf()
            
            if not menu_regenerated:
                
                self._RegenerateMenu()
                
            
        
    
    def SetShouldAlwaysShow( self, should_always_show: bool ):
        
        if should_always_show != self._should_always_show:
            
            self._should_always_show = should_always_show
            
            self._UpdateShowSelf()
            
        
