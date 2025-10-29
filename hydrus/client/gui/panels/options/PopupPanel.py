from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class PopupPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        self._popup_panel = ClientGUICommon.StaticBox( self, 'popup window toaster' )
        
        self._popup_message_character_width = ClientGUICommon.BetterSpinBox( self._popup_panel, min = 16, max = 256 )
        
        self._popup_message_force_min_width = QW.QCheckBox( self._popup_panel )
        
        self._freeze_message_manager_when_mouse_on_other_monitor = QW.QCheckBox( self._popup_panel )
        self._freeze_message_manager_when_mouse_on_other_monitor.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is useful if you have a virtual desktop and find the popup manager restores strangely when you hop back to the hydrus display.' ) )
        
        self._freeze_message_manager_when_main_gui_minimised = QW.QCheckBox( self._popup_panel )
        self._freeze_message_manager_when_main_gui_minimised.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is useful if the popup toaster restores strangely after minimised changes.' ) )
        
        self._notify_client_api_cookies = QW.QCheckBox( self._popup_panel )
        self._notify_client_api_cookies.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will make a short-lived popup message every time you get new cookie or http header information over the Client API.' ) )
        
        #
        
        self._popup_message_character_width.setValue( self._new_options.GetInteger( 'popup_message_character_width' ) )
        
        self._popup_message_force_min_width.setChecked( self._new_options.GetBoolean( 'popup_message_force_min_width' ) )
        
        self._freeze_message_manager_when_mouse_on_other_monitor.setChecked( self._new_options.GetBoolean( 'freeze_message_manager_when_mouse_on_other_monitor' ) )
        self._freeze_message_manager_when_main_gui_minimised.setChecked( self._new_options.GetBoolean( 'freeze_message_manager_when_main_gui_minimised' ) )
        
        self._notify_client_api_cookies.setChecked( self._new_options.GetBoolean( 'notify_client_api_cookies' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Approximate max width of popup messages (in characters): ', self._popup_message_character_width ) )
        rows.append( ( 'BUGFIX: Force this width as the fixed width for all popup messages: ', self._popup_message_force_min_width ) )
        rows.append( ( 'Freeze the popup toaster when mouse is on another display: ', self._freeze_message_manager_when_mouse_on_other_monitor ) )
        rows.append( ( 'Freeze the popup toaster when the main gui is minimised: ', self._freeze_message_manager_when_main_gui_minimised ) )
        rows.append( ( 'Make a short-lived popup on cookie/header updates through the Client API: ', self._notify_client_api_cookies ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._popup_panel, rows )
        
        self._popup_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._popup_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetInteger( 'popup_message_character_width', self._popup_message_character_width.value() )
        
        self._new_options.SetBoolean( 'popup_message_force_min_width', self._popup_message_force_min_width.isChecked() )
        
        self._new_options.SetBoolean( 'freeze_message_manager_when_mouse_on_other_monitor', self._freeze_message_manager_when_mouse_on_other_monitor.isChecked() )
        self._new_options.SetBoolean( 'freeze_message_manager_when_main_gui_minimised', self._freeze_message_manager_when_main_gui_minimised.isChecked() )
        
        self._new_options.SetBoolean( 'notify_client_api_cookies', self._notify_client_api_cookies.isChecked() )
        
    
