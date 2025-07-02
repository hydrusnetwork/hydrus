from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class EditTextPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, message: str, default = '', placeholder = None, allow_blank = False, suggestions = None, max_chars = None, password_entry = False, min_char_width = 72 ):
        
        if suggestions is None:
            
            suggestions = []
            
        
        super().__init__( parent )
        
        self._chosen_suggestion = None
        self._allow_blank = allow_blank
        self._max_chars = max_chars
        
        button_choices =  []
        
        for text in suggestions:
            
            button_choices.append( ClientGUICommon.BetterButton( self, text, self.ButtonChoice, text ) )
            
        
        self._text = QW.QLineEdit( self )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._text, min_char_width )
        
        self._text.setMinimumWidth( width )
        
        if password_entry:
            
            self._text.setEchoMode( QW.QLineEdit.EchoMode.Password )
            
        
        if self._max_chars is not None:
            
            self._text.setMaxLength( self._max_chars )
            
        
        #
        
        self._text.setText( default )
        
        if placeholder is not None:
            
            self._text.setPlaceholderText( placeholder )
            
        
        if len( default ) > 0:
            
            self._text.setSelection( 0, len( default ) )
            
        
        #
        
        st_message = ClientGUICommon.BetterStaticText( self, message )
        st_message.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st_message, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for button in button_choices:
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._text, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._text.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    
    def ButtonChoice( self, text ):
        
        self._chosen_suggestion =  text
        
        self._OKParent()
        
    
    def GetValue( self ):
        
        if self._chosen_suggestion is None:
            
            text = self._text.text()
            
        else:
            
            text = self._chosen_suggestion
            
        
        if not self._allow_blank and text == '':
            
            raise HydrusExceptions.CancelledException( 'Cannot enter blank text here!' )
            
        
        return text
        
    
