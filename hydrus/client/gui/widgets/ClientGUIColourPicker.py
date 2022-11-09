import re

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIStyle
from hydrus.client.gui import QtInit

def EditColour( win: QW.QWidget, colour: QG.QColor ):
    
    return_value = colour
    
    old_stylesheet = ClientGUIStyle.CURRENT_STYLESHEET
    
    # OK, this is a legit bug in Qt6. if QWidget::item:hover is set in the QSS, even as an empty block, the colour-picker gradient square thing will update on normal mouse moves, not just drags, lmao
    # so we do this laggy nonsense, but it fixes it
    
    if QtInit.WE_ARE_QT6 and ( 'QWidget::item:hover' in ClientGUIStyle.CURRENT_STYLESHEET or 'QWidget:item:hover' in ClientGUIStyle.CURRENT_STYLESHEET ):
        
        new_stylesheet = old_stylesheet.replace( 'QWidget::item:hover', 'QWidget::fugg:fugg' ).replace( 'QWidget:item:hover', 'QWidget:fugg:fugg' )
        
        ClientGUIStyle.SetStyleSheet( new_stylesheet, prepend_hydrus = False )
        
    
    # note you can set alpha support here with a flag
    
    dialog = QW.QColorDialog( colour, win )
    
    if dialog.exec_() == QW.QDialog.Accepted:
        
        edited_colour = dialog.selectedColor()
        
        if edited_colour.isValid():
            
            return_value = edited_colour
            
        
    
    ClientGUIStyle.SetStyleSheet( old_stylesheet, prepend_hydrus = False )
    
    return return_value
    

class ColourPickerButton( QW.QPushButton ):
    
    def __init__( self, parent = None ):
        
        QW.QPushButton.__init__( self, parent )
        
        self._colour = QG.QColor( 0, 0, 0, 0 )
        
        self.clicked.connect( self._ChooseColour )
        
        self._highlighted = False
        
    
    def SetColour( self, colour ):
        
        self._colour = colour

        self._UpdatePixmap()
        

    def _UpdatePixmap( self ):
        
        px = QG.QPixmap( self.contentsRect().height(), self.contentsRect().height() )
        
        painter = QG.QPainter( px )
        
        colour = self._colour
        
        if self._highlighted:
            
            colour = self._colour.lighter( 125 ) # 25% lighter
            
        
        painter.fillRect( px.rect(), QG.QBrush( colour ) )
        
        painter.end()
        
        self.setIcon( QG.QIcon( px ) )
        
        self.setIconSize( px.size() )
        
        self.setFlat( True )
        
        self.setFixedSize( px.size() )
        
    
    def enterEvent( self, event ):
        
        self._highlighted = True
        
        self._UpdatePixmap()
        
    
    def leaveEvent( self, event ):
        
        self._highlighted = False
        
        self._UpdatePixmap()
        
    
    def GetColour( self ):
        
        return self._colour
        
    
    def _ChooseColour( self ):
        
        new_colour = EditColour( self, self._colour )
        
        self.SetColour( new_colour )
        
    
    def _ImportHexFromClipboard( self ):
        
        try:
            
            import_string = HG.client_controller.GetClipboardText()
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        if import_string.startswith( '#' ):
            
            import_string = import_string[1:]
            
        
        import_string = '#' + re.sub( '[^0-9a-fA-F]', '', import_string )
        
        if len( import_string ) != 7:
            
            QW.QMessageBox.critical( self, 'Error', 'That did not appear to be a hex string!' )
            
            return
            
        
        try:
            
            colour = QG.QColor( import_string )
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            HydrusData.ShowException( e )
            
            return
            
        
        self.SetColour( colour )
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Keyboard:
            
            self.ShowMenu()
            
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.RightButton:
            
            return QW.QPushButton.mouseReleaseEvent( self, event )
            
        
        self.ShowMenu()
        
    
    def ShowMenu( self ):
        
        menu = QW.QMenu()
        
        hex_string = self.GetColour().name( QG.QColor.HexRgb )
        
        ClientGUIMenus.AppendMenuItem( menu, 'copy ' + hex_string + ' to the clipboard', 'Copy the current colour to the clipboard.', HG.client_controller.pub, 'clipboard', 'text', hex_string )
        ClientGUIMenus.AppendMenuItem( menu, 'import a hex colour from the clipboard', 'Look at the clipboard for a colour in the format #FF0000, and set the colour.', self._ImportHexFromClipboard )
        
        CGC.core().PopupMenu( self, menu )
        
    
