import re

import qtpy
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIStyle
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class AlphaColourControl( QW.QWidget ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._colour_picker = ColourPickerButton( self )
        
        self._alpha_selector = ClientGUICommon.BetterSpinBox( self, min=0, max=255 )
        
        hbox = QP.HBoxLayout( spacing = 5 )
        
        QP.AddToLayout( hbox, self._colour_picker, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'alpha:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._alpha_selector, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
    
    def GetValue( self ):
        
        colour = self._colour_picker.GetColour()
        
        a = self._alpha_selector.value()
        
        colour.setAlpha( a )
        
        return colour
        
    
    def SetValue( self, colour: QG.QColor ):
        
        picker_colour = QG.QColor( colour.rgb() )
        
        self._colour_picker.SetColour( picker_colour )
        
        self._alpha_selector.setValue( colour.alpha() )
        
    

def EditColour( win: QW.QWidget, colour: QG.QColor ):
    
    return_value = colour
    
    old_stylesheet = ClientGUIStyle.CURRENT_STYLESHEET
    
    original_stylesheet_name = ClientGUIStyle.CURRENT_STYLESHEET_FILENAME
    
    try:
        
        qt_version_tuple = tuple( map( int, qtpy.QT_VERSION.split( '.' ) ) ) # 6.6.0 -> ( 6, 6, 0 )
        
        qt_version_is_dangerzone = qt_version_tuple[0] == 6 and qt_version_tuple[1] < 6
        
    except Exception as e:
        
        qt_version_is_dangerzone = False # who knows what is going on, but let's not spam stylesheets on this crazy Qt!?
        
    
    # OK, this is a legit bug in Qt6, all I know is <6.6.0 but it might have been fixed earlier
    # I think it is this one https://bugreports.qt.io/browse/QTBUG-115516
    # if QWidget::item:hover is set in the QSS, even as an empty block, the colour-picker gradient square thing will update on normal mouse moves, not just drags, lmao
    # so we do this laggy nonsense, but it fixes it
    
    yes_do_qss_switch = qt_version_is_dangerzone and ( 'QWidget::item:hover' in ClientGUIStyle.CURRENT_STYLESHEET or 'QWidget:item:hover' in ClientGUIStyle.CURRENT_STYLESHEET )
    
    if yes_do_qss_switch:
        
        new_stylesheet = old_stylesheet.replace( 'QWidget::item:hover', 'QWidget::fugg:fugg' ).replace( 'QWidget:item:hover', 'QWidget:fugg:fugg' )
        
        ClientGUIStyle.SetStyleSheet( new_stylesheet, 'temp art hack', prepend_hydrus = False )
        
    
    # note you can set alpha support here with a flag
    
    dialog = QW.QColorDialog( colour, win )
    
    if dialog.exec_() == QW.QDialog.DialogCode.Accepted:
        
        edited_colour = dialog.selectedColor()
        
        if edited_colour.isValid():
            
            return_value = edited_colour
            
        
    
    if yes_do_qss_switch:
        
        ClientGUIStyle.SetStyleSheet( old_stylesheet, original_stylesheet_name )
        
    
    return return_value
    

class ColourPickerButton( QW.QPushButton ):
    
    colourChanged = QC.Signal()
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self._colour = QG.QColor( 0, 0, 0, 0 )
        
        self.clicked.connect( self._ChooseColour )
        
        self._highlighted = False
        
    
    def SetColour( self, colour ):
        
        self._colour = colour
        
        self.colourChanged.emit()
        
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
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        import_string = raw_text
        
        if import_string.startswith( '#' ):
            
            import_string = import_string[1:]
            
        
        import_string = '#' + re.sub( '[^0-9a-fA-F]', '', import_string )
        
        if len( import_string ) != 7:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', f'"{raw_text}" did not appear to be a hex string!' )
            
            return
            
        
        try:
            
            colour = QG.QColor( import_string )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'A hex colour like #FF0050', e )
            
            return
            
        
        self.SetColour( colour )
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Reason.Keyboard:
            
            self.ShowMenu()
            
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.MouseButton.RightButton:
            
            return QW.QPushButton.mouseReleaseEvent( self, event )
            
        
        self.ShowMenu()
        
    
    def ShowMenu( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        hex_string = self.GetColour().name( QG.QColor.NameFormat.HexRgb )
        
        ClientGUIMenus.AppendMenuItem( menu, 'copy ' + hex_string + ' to the clipboard', 'Copy the current colour to the clipboard.', CG.client_controller.pub, 'clipboard', 'text', hex_string )
        ClientGUIMenus.AppendMenuItem( menu, 'import a hex colour from the clipboard', 'Look at the clipboard for a colour in the format #FF0000, and set the colour.', self._ImportHexFromClipboard )
        
        CGC.core().PopupMenu( self, menu )
        
    
