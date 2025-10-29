from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class SystemPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        sleep_panel = ClientGUICommon.StaticBox( self, 'system sleep' )
        
        self._do_sleep_check = QW.QCheckBox( sleep_panel )
        self._do_sleep_check.setToolTip( ClientGUIFunctions.WrapToolTip( 'Hydrus detects sleeps via a hacky method where it simply checks the clock every 15 seconds. If too long a time has passed since the last check, it assumes it has just woken up from sleep. This produces false positives in certain UI-hanging situations, so you may, for debugging purposes, wish to turn it off here. When functioning well, it is useful and you should leave it on!' ) )
        
        self._wake_delay_period = ClientGUICommon.BetterSpinBox( sleep_panel, min = 0, max = 60 )
        
        tt = 'It sometimes takes a few seconds for your network adapter to reconnect after a wake. This adds a grace period after a detected wake-from-sleep to allow your OS to sort that out before Hydrus starts making requests.'
        
        self._wake_delay_period.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._file_system_waits_on_wakeup = QW.QCheckBox( sleep_panel )
        self._file_system_waits_on_wakeup.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is useful if your hydrus is stored on a NAS that takes a few seconds to get going after your machine resumes from sleep.' ) )
        
        #
        
        self._do_sleep_check.setChecked( self._new_options.GetBoolean( 'do_sleep_check' ) )
        
        self._wake_delay_period.setValue( self._new_options.GetInteger( 'wake_delay_period' ) )
        
        self._file_system_waits_on_wakeup.setChecked( self._new_options.GetBoolean( 'file_system_waits_on_wakeup' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Allow wake-from-system-sleep detection:', self._do_sleep_check ) )
        rows.append( ( 'After a wake from system sleep, wait this many seconds before allowing new network access:', self._wake_delay_period ) )
        rows.append( ( 'Include the file system in this wait: ', self._file_system_waits_on_wakeup ) )
        
        gridbox = ClientGUICommon.WrapInGrid( sleep_panel, rows )
        
        sleep_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, sleep_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'do_sleep_check', self._do_sleep_check.isChecked() )
        self._new_options.SetInteger( 'wake_delay_period', self._wake_delay_period.value() )
        self._new_options.SetBoolean( 'file_system_waits_on_wakeup', self._file_system_waits_on_wakeup.isChecked() )
        
    
