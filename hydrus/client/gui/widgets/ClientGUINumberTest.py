from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.search import ClientNumberTest

class NumberTestWidget( QW.QWidget ):
    
    def __init__( self, parent, allowed_operators = None, max = 200000, unit_string = None, appropriate_absolute_plus_or_minus_default = 1, appropriate_percentage_plus_or_minus_default = 15 ):
        
        super().__init__( parent )
        
        choice_tuples = []
        
        for possible_operator in [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
        ]:
            
            if possible_operator in allowed_operators:
                
                text = ClientNumberTest.number_test_operator_to_str_lookup[ possible_operator ]
                
                if possible_operator == ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
                    
                    text += '%'
                    
                
                choice_tuples.append( ( text, possible_operator ) )
                
            
        
        self._operator = ClientGUICommon.BetterRadioBox( self, choice_tuples )
        
        self._value = self._GenerateValueWidget( max )
        
        #
        
        self._absolute_plus_or_minus_panel = QW.QWidget( self )
        
        self._absolute_plus_or_minus = self._GenerateAbsoluteValueWidget( max )
        
        self._SetAbsoluteValue( appropriate_absolute_plus_or_minus_default )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._absolute_plus_or_minus_panel, label = HC.UNICODE_PLUS_OR_MINUS ), CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( hbox, self._absolute_plus_or_minus, CC.FLAGS_CENTER_PERPENDICULAR )
        
        if unit_string is not None:
            
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._absolute_plus_or_minus_panel, label = unit_string ), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        self._absolute_plus_or_minus_panel.setLayout( hbox )
        
        #
        
        self._percent_plus_or_minus_panel = QW.QWidget( self )
        
        self._percent_plus_or_minus = ClientGUICommon.BetterSpinBox( self._percent_plus_or_minus_panel, min = 0, max = 10000, width = 60 )
        
        self._percent_plus_or_minus.setValue( appropriate_percentage_plus_or_minus_default )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._percent_plus_or_minus_panel, label = HC.UNICODE_PLUS_OR_MINUS ), CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( hbox, self._percent_plus_or_minus, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._percent_plus_or_minus_panel, label = '%' ), CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._percent_plus_or_minus_panel.setLayout( hbox )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._value, CC.FLAGS_CENTER_PERPENDICULAR )
        
        if unit_string is not None:
            
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, label = unit_string ), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        QP.AddToLayout( hbox, self._absolute_plus_or_minus_panel, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._percent_plus_or_minus_panel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self._operator.radioBoxChanged.connect( self._UpdateVisibility )
        
        self._UpdateVisibility()
        
        
    
    def _GenerateAbsoluteValueWidget( self, max: int ):
        
        return ClientGUICommon.BetterSpinBox( self._absolute_plus_or_minus_panel, min = 0, max = int( max / 2 ), width = 60 )
        
    
    def _GenerateValueWidget( self, max: int ):
        
        return ClientGUICommon.BetterSpinBox( self, max = max, width = 60 )
        
    
    def _GetSubValue( self ):
        
        return self._value.value()
        
    
    def _SetSubValue( self, value ):
        
        return self._value.setValue( value )
        
    
    def _GetAbsoluteValue( self ):
        
        return self._absolute_plus_or_minus.value()
        
    
    def _SetAbsoluteValue( self, value ):
        
        return self._absolute_plus_or_minus.setValue( value )
        
    
    def _UpdateVisibility( self ):
        
        operator = self._operator.GetValue()
        
        self._absolute_plus_or_minus_panel.setVisible( operator == ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE )
        self._percent_plus_or_minus_panel.setVisible( operator == ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT )
        
    
    def GetValue( self ) -> ClientNumberTest.NumberTest:
        
        operator = self._operator.GetValue()
        value = self._GetSubValue()
        
        if operator == ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE:
            
            extra_value = self._GetAbsoluteValue()
            
        elif operator == ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
            
            extra_value = self._percent_plus_or_minus.value() / 100
            
        else:
            
            extra_value = None
            
        
        return ClientNumberTest.NumberTest( operator = operator, value = value, extra_value = extra_value )
        
    
    def SetValue( self, number_test: ClientNumberTest.NumberTest ):
        
        self._operator.SetValue( number_test.operator )
        self._SetSubValue( number_test.value )
        
        if number_test.operator == ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE:
            
            self._SetAbsoluteValue( number_test.extra_value )
            
        elif number_test.operator == ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
            
            self._percent_plus_or_minus.setValue( int( number_test.extra_value * 100 ) )
            
        
        self._UpdateVisibility()
        
    
