from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class GUISessionsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        self._sessions_panel = ClientGUICommon.StaticBox( self, 'sessions' )
        
        self._default_gui_session = ClientGUICommon.BetterChoice( self._sessions_panel )
        
        self._last_session_save_period_minutes = ClientGUICommon.BetterSpinBox( self._sessions_panel, min = 1, max = 1440 )
        
        self._only_save_last_session_during_idle = QW.QCheckBox( self._sessions_panel )
        
        self._only_save_last_session_during_idle.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is useful if you usually have a very large session (200,000+ files/import items open) and a client that is always on.' ) )
        
        self._number_of_gui_session_backups = ClientGUICommon.BetterSpinBox( self._sessions_panel, min = 1, max = 32 )
        
        self._number_of_gui_session_backups.setToolTip( ClientGUIFunctions.WrapToolTip( 'The client keeps multiple rolling backups of your gui sessions. If you have very large sessions, you might like to reduce this number.' ) )
        
        self._show_session_size_warnings = QW.QCheckBox( self._sessions_panel )
        
        self._show_session_size_warnings.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will give you a once-per-boot warning popup if your active session contains more than 10M weight.' ) )
        
        #
        
        gui_session_names = CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
        
        if CC.LAST_SESSION_SESSION_NAME not in gui_session_names:
            
            gui_session_names.insert( 0, CC.LAST_SESSION_SESSION_NAME )
            
        
        self._default_gui_session.addItem( 'just a blank page', None )
        
        for name in gui_session_names:
            
            self._default_gui_session.addItem( name, name )
            
        
        self._default_gui_session.SetValue( HC.options['default_gui_session'] )
        
        self._last_session_save_period_minutes.setValue( self._new_options.GetInteger( 'last_session_save_period_minutes' ) )
        
        self._only_save_last_session_during_idle.setChecked( self._new_options.GetBoolean( 'only_save_last_session_during_idle' ) )
        
        self._number_of_gui_session_backups.setValue( self._new_options.GetInteger( 'number_of_gui_session_backups' ) )
        
        self._show_session_size_warnings.setChecked( self._new_options.GetBoolean( 'show_session_size_warnings' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Default session on startup: ', self._default_gui_session ) )
        rows.append( ( 'If \'last session\' above, autosave it how often (minutes)?', self._last_session_save_period_minutes ) )
        rows.append( ( 'If \'last session\' above, only autosave during idle time?', self._only_save_last_session_during_idle ) )
        rows.append( ( 'Number of session backups to keep: ', self._number_of_gui_session_backups ) )
        rows.append( ( 'Show warning popup if session size exceeds 10,000,000: ', self._show_session_size_warnings ) )
        
        sessions_gridbox = ClientGUICommon.WrapInGrid( self._sessions_panel, rows )
        
        self._sessions_panel.Add( sessions_gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._sessions_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        HC.options[ 'default_gui_session' ] = self._default_gui_session.GetValue()
        
        self._new_options.SetInteger( 'last_session_save_period_minutes', self._last_session_save_period_minutes.value() )
        
        self._new_options.SetInteger( 'number_of_gui_session_backups', self._number_of_gui_session_backups.value() )
        
        self._new_options.SetBoolean( 'show_session_size_warnings', self._show_session_size_warnings.isChecked() )
        
        self._new_options.SetBoolean( 'only_save_last_session_during_idle', self._only_save_last_session_during_idle.isChecked() )
        
    
