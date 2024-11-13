from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class TextAndPasteCtrl( QW.QWidget ):
    
    def __init__( self, parent, add_callable, allow_empty_input = False ):
        
        self._add_callable = add_callable
        self._allow_empty_input = allow_empty_input
        
        super().__init__( parent )
        
        self._text_input = QW.QLineEdit( self )
        self._text_input.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._text_input, self.EnterText ) )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste multiple inputs from the clipboard. Assumes the texts are newline-separated.' ) )
        
        self.setFocusProxy( self._text_input )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._text_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            texts = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            if not self._allow_empty_input:
                
                texts = [ text for text in texts if text != '' ]
                
            
            if len( texts ) > 0:
                
                self._add_callable( texts )
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of text', e )
            
        
    
    def EnterText( self ):
        
        text = self._text_input.text()
        
        text = HydrusText.StripIOInputLine( text )
        
        if text == '' and not self._allow_empty_input:
            
            return
            
        
        self._add_callable( ( text, ) )
        
        self._text_input.clear()
        
    
    def GetValue( self ):
        
        return self._text_input.text()
        
    
    def setPlaceholderText( self, text ):
        
        self._text_input.setPlaceholderText( text )
        
    
    def SetValue( self, text ):
        
        self._text_input.setText( text )
        
    
