from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class AdvancedPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        # https://github.com/hydrusnetwork/hydrus/issues/1558
        
        self._advanced_mode = QW.QCheckBox( self )
        self._advanced_mode.setToolTip( ClientGUIFunctions.WrapToolTip( 'This controls a variety of different features across the program, too many to list neatly. The plan is to blow this single option out into many granular options on this page.\n\nThis plan is failing!' ) )
        
        self._advanced_mode.setChecked( self._new_options.GetBoolean( 'advanced_mode' ) )
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'Advanced mode: ', self._advanced_mode ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        #
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'advanced_mode', self._advanced_mode.isChecked() )
        
    
