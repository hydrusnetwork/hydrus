from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class BytesControl( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, initial_value = 65536 ):
        
        super().__init__( parent )
        
        self._spin = ClientGUICommon.BetterSpinBox( self, min=0, max=1048576 )
        
        self._unit = ClientGUICommon.BetterChoice( self )
        
        self._unit.addItem( 'B', 1 )
        self._unit.addItem( 'KB', 1024 )
        self._unit.addItem( 'MB', 1024 ** 2 )
        self._unit.addItem( 'GB', 1024 ** 3 )
        self._unit.addItem( 'TB', 1024 ** 4 )
        
        #
        
        self.SetValue( initial_value )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._spin, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._unit, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )

        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._unit, 8 )
        
        self._unit.setMinimumWidth( min_width )
        
        self._spin.valueChanged.connect( self._HandleValueChanged )
        self._unit.currentIndexChanged.connect( self._HandleValueChanged )
        
    
    def _HandleValueChanged( self, val ):
        
        self.valueChanged.emit()
        
    
    def GetSeparatedValue( self ):
        
        return ( self._spin.value(), self._unit.GetValue() )
        
    
    def GetValue( self ):
        
        return self._spin.value() * self._unit.GetValue()
        
    
    def SetSeparatedValue( self, value, unit ):
        
        return ( self._spin.setValue( value ), self._unit.SetValue( unit ) )
        
    
    def SetValue( self, value: int ):
        
        max_unit = 1024 ** 4
        
        unit = 1
        
        while value % 1024 == 0 and unit < max_unit:
            
            value //= 1024
            
            unit *= 1024
            
        
        self._spin.setValue( value )
        self._unit.SetValue( unit )
        
    

class NoneableBytesControl( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, default_bytes: int, none_label = 'no limit' ):
        
        super().__init__( parent )
        
        self._bytes = BytesControl( self )
        self._bytes.SetValue( default_bytes )
        
        self._none_checkbox = QW.QCheckBox( none_label, self )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._bytes, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._none_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        self._none_checkbox.clicked.connect( self._UpdateEnabled )
        
        self._bytes.valueChanged.connect( self._HandleValueChanged )
        self._none_checkbox.clicked.connect( self._HandleValueChanged )
        
    
    def _UpdateEnabled( self ):
        
        if self._none_checkbox.isChecked():
            
            self._bytes.setEnabled( False )
            
        else:
            
            self._bytes.setEnabled( True )
            
        
    
    def _HandleValueChanged( self ):
        
        self.valueChanged.emit()
        
    
    def GetValue( self ):
        
        if self._none_checkbox.isChecked():
            
            return None
            
        else:
            
            return self._bytes.GetValue()
            
        
    
    def setToolTip( self, text ):
        
        QW.QWidget.setToolTip( self, text )
        
        for c in self.children():
            
            if isinstance( c, QW.QWidget ):
                
                c.setToolTip( text )
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._none_checkbox.setChecked( True )
            
        else:
            
            self._none_checkbox.setChecked( False )
            
            self._bytes.SetValue( value )
            
        
        self._UpdateEnabled()
        
    
