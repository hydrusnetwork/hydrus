from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class SystemTrayPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        self._always_show_system_tray_icon = QW.QCheckBox( self )
        self._minimise_client_to_system_tray = QW.QCheckBox( self )
        self._close_client_to_system_tray = QW.QCheckBox( self )
        self._start_client_in_system_tray = QW.QCheckBox( self )
        
        #
        
        self._always_show_system_tray_icon.setChecked( self._new_options.GetBoolean( 'always_show_system_tray_icon' ) )
        self._minimise_client_to_system_tray.setChecked( self._new_options.GetBoolean( 'minimise_client_to_system_tray' ) )
        self._close_client_to_system_tray.setChecked( self._new_options.GetBoolean( 'close_client_to_system_tray' ) )
        self._start_client_in_system_tray.setChecked( self._new_options.GetBoolean( 'start_client_in_system_tray' ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'Always show the hydrus system tray icon: ', self._always_show_system_tray_icon ) )
        rows.append( ( 'Minimise the main window to system tray: ', self._minimise_client_to_system_tray ) )
        rows.append( ( 'Close the main window to system tray: ', self._close_client_to_system_tray ) )
        rows.append( ( 'Start the client minimised to system tray: ', self._start_client_in_system_tray ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        from hydrus.client.gui import ClientGUISystemTray
        
        if not ClientGUISystemTray.SystemTrayAvailable():
            
            QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, 'Unfortunately, your system does not seem to have a supported system tray.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._always_show_system_tray_icon.setEnabled( False )
            self._minimise_client_to_system_tray.setEnabled( False )
            self._close_client_to_system_tray.setEnabled( False )
            self._start_client_in_system_tray.setEnabled( False )
            
            self._always_show_system_tray_icon.setChecked( False )
            self._minimise_client_to_system_tray.setChecked( False )
            self._close_client_to_system_tray.setChecked( False )
            self._start_client_in_system_tray.setChecked( False )
            
        elif not HC.PLATFORM_WINDOWS:
            
            if not CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                label = 'This is turned off for non-advanced non-Windows users for now.'
                
                self._always_show_system_tray_icon.setEnabled( False )
                self._minimise_client_to_system_tray.setEnabled( False )
                self._close_client_to_system_tray.setEnabled( False )
                self._start_client_in_system_tray.setEnabled( False )
                
            else:
                
                label = 'This can be buggy/crashy on non-Windows, hydev will keep working on this.'
                
            
            QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, label ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'always_show_system_tray_icon', self._always_show_system_tray_icon.isChecked() )
        self._new_options.SetBoolean( 'minimise_client_to_system_tray', self._minimise_client_to_system_tray.isChecked() )
        self._new_options.SetBoolean( 'close_client_to_system_tray', self._close_client_to_system_tray.isChecked() )
        self._new_options.SetBoolean( 'start_client_in_system_tray', self._start_client_in_system_tray.isChecked() )
        
    
