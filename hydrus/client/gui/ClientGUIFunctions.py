import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

from hydrus.client.gui import QtPorting as QP

def ClientToScreen( win: QW.QWidget, pos: QC.QPoint ) -> QC.QPoint:
    
    tlw = win.window()
    
    if ( win.isVisible() and tlw.isVisible() ):
        
        return win.mapToGlobal( pos )
        
    else:
        
        return QC.QPoint( 50, 50 )
        
    
def ColourIsBright( colour: QG.QColor ):
    
    it_is_bright = colour.valueF() > 0.75
    
    return it_is_bright
    
def ColourIsGreyish( colour: QG.QColor ):
    
    it_is_greyish = colour.hsvSaturationF() < 0.12
    
    return it_is_greyish
    
# OK, so we now have a fixed block for width, which we sometimes want to calculate in both directions.
# by normalising our 'one character' width, the inverse calculation uses the same coefficient and we aren't losing so much in rounding
NUM_CHARS_FOR_WIDTH_CALCULATIONS = 32
MAGIC_TEXT_PADDING = 1.1

def GetOneCharacterPixelHeight( window ) -> float:
    
    return window.fontMetrics().height() * MAGIC_TEXT_PADDING
    
def GetOneCharacterPixelWidth( window ) -> float:
    
    char_block_width = window.fontMetrics().boundingRect( NUM_CHARS_FOR_WIDTH_CALCULATIONS * 'x' ).width() * MAGIC_TEXT_PADDING
    
    one_char_width = char_block_width / NUM_CHARS_FOR_WIDTH_CALCULATIONS
    
    return one_char_width
    
def ConvertPixelsToTextWidth( window, pixels, round_down = False ) -> int:
    
    one_char_width = GetOneCharacterPixelWidth( window )
    
    if round_down:
        
        return int( pixels // one_char_width )
        
    else:
        
        return round( pixels / one_char_width )
        
    
def ConvertTextToPixels( window, char_dimensions ) -> typing.Tuple[ int, int ]:
    
    ( char_cols, char_rows ) = char_dimensions
    
    one_char_width = GetOneCharacterPixelWidth( window )
    one_char_height = GetOneCharacterPixelHeight( window )
    
    return ( round( char_cols * one_char_width ), round( char_rows * one_char_height ) )
    
def ConvertTextToPixelWidth( window, char_cols ) -> int:
    
    one_char_width = GetOneCharacterPixelWidth( window )
    
    return round( char_cols * one_char_width )
    
def DialogIsOpen():
    
    tlws = QW.QApplication.topLevelWidgets()
    
    for tlw in tlws:
        
        if isinstance( tlw, QP.Dialog ) and tlw.isModal():
            
            return True
            
        
    
    return False
    
def DrawText( painter, x, y, text ):
    
    ( boundingRect, text ) = GetTextSizeFromPainter( painter, text )
    
    painter.drawText( QC.QRectF( x, y, boundingRect.width(), boundingRect.height() ), text )

def EscapeMnemonics( s: str ):
    
    return s.replace( "&", "&&" )
    
def GetDifferentLighterDarkerColour( colour, intensity = 3 ):
    
    new_hue = colour.hsvHueF()
    
    if new_hue == -1: # completely achromatic
        
        new_hue = 0.5
        
    else:
        
        new_hue = ( new_hue + 0.33 ) % 1.0
        
    
    new_saturation = colour.hsvSaturationF()
    
    if ColourIsGreyish( colour ):
        
        new_saturation = 0.2
        
    
    new_colour = QG.QColor.fromHsvF( new_hue, new_saturation, colour.valueF(), colour.alphaF() )
    
    return GetLighterDarkerColour( new_colour, intensity )
    
def GetDisplayPosition( window ):
    
    return QW.QApplication.desktop().availableGeometry( window ).topLeft()
    
def GetDisplaySize( window ):
    
    return QW.QApplication.desktop().availableGeometry( window ).size()
    
def GetLighterDarkerColour( colour, intensity = 3 ):
    
    if intensity is None or intensity == 0:
        
        return colour
        
    
    # darker/lighter works by multiplying value, so when it is closer to 0, lmao
    breddy_darg_made = 0.25
    
    if colour.value() < breddy_darg_made:
        
        colour = QG.QColor.fromHslF( colour.hsvHueF(), colour.hsvSaturationF(), breddy_darg_made, colour.alphaF() )
        
    
    qt_intensity = 100 + ( 20 * intensity )
    
    if ColourIsBright( colour ):
        
        return colour.darker( qt_intensity )
        
    else:
        
        return colour.lighter( qt_intensity )
        
    
def GetMouseScreen():
    
    return QW.QApplication.screenAt( QG.QCursor.pos() )
    
def GetTextSizeFromPainter( painter: QG.QPainter, text: str ):
    
    try:
        
        text_size = painter.fontMetrics().size( QC.Qt.TextSingleLine, text )
        
    except ValueError:
        
        from hydrus.client.metadata import ClientTags
        
        if not ClientTags.have_shown_invalid_tag_warning:
            
            from hydrus.core import HydrusData
            
            HydrusData.ShowText( 'Hey, I think hydrus stumbled across an invalid tag! Please run _database->check and repair->fix invalid tags_ immediately, or you may get errors!' )
            
            bad_text = repr( text )
            bad_text = HydrusText.ElideText( bad_text, 24 )
            
            HydrusData.ShowText( 'The bad text was: {}'.format( bad_text ) )
            
            ClientTags.have_shown_invalid_tag_warning = True
            
        
        text = '*****INVALID, UNDISPLAYABLE TAG, RUN DATABASE REPAIR NOW*****'
        
        text_size = painter.fontMetrics().size( QC.Qt.TextSingleLine, text )
        
    
    return ( text_size, text )
    
def GetTLWParents( widget ):
    
    widget_tlw = widget.window()        
    
    parent_tlws = []
    
    parent = widget_tlw.parentWidget()
    
    while parent is not None:
        
        parent_tlw = parent.window()
        
        parent_tlws.append( parent_tlw )
        
        parent = parent_tlw.parentWidget()
        
    
    return parent_tlws
    
def IsQtAncestor( child, ancestor, through_tlws = False ):
    
    if child == ancestor:
        
        return True
        
    
    parent = child
    
    if through_tlws:
        
        while not parent is None:
            
            if parent == ancestor:
                
                return True
                
            
            parent = parent.parentWidget()
            
        
    else:
        
        # only works within window
        return ancestor.isAncestorOf( child )
        
    
    return False
    
def MouseIsOnMyDisplay( window ):
    
    window_handle = window.window().windowHandle()
    
    if window_handle is None:
        
        return False
        
    
    window_screen = window_handle.screen()
    
    mouse_screen = GetMouseScreen()
    
    return mouse_screen is window_screen
    
def MouseIsOverWidget( win: QW.QWidget ):
    
    # note this is different from win.underMouse(), which in different situations seems to be more complicated than just a rect test
    
    # I also had QWidget.underMouse() do flicker on the border edge between two lads next to each other. I guess there might be a frameGeometry vs geometry issue, but dunno. not like I test that here
    
    global_mouse_pos = QG.QCursor.pos()
    
    local_mouse_pos = win.mapFromGlobal( global_mouse_pos )
    
    return win.rect().contains( local_mouse_pos )
    
def NotebookScreenToHitTest( notebook, screen_position ):
    
    tab_pos = notebook.tabBar().mapFromGlobal( screen_position )    
    
    return notebook.tabBar().tabAt( tab_pos )
    
def SetBitmapButtonBitmap( button, bitmap ):
    
    # old wx stuff, but still basically relevant
    # the button's bitmap, retrieved via GetBitmap, is not the same as the one we gave it!
    # hence testing bitmap vs that won't work to save time on an update loop, so we'll just save it here custom
    # this isn't a big memory deal for our purposes since they are small and mostly if not all from the GlobalPixmaps library so shared anyway
    
    if hasattr( button, 'last_bitmap' ):
        
        if button.last_bitmap == bitmap:
            
            return
            
        
    
    button.setIcon( QG.QIcon( bitmap ) )
    button.setIconSize( bitmap.size() )
    
    button.last_bitmap = bitmap
    
def SetFocusLater( win: QW.QWidget ):
    
    HG.client_controller.CallAfterQtSafe( win, 'set focus to a window', win.setFocus, QC.Qt.OtherFocusReason )
    
def TLWIsActive( window ):
    
    return window.window() == QW.QApplication.activeWindow()
    
def TLWOrChildIsActive( win ):
    
    current_focus_tlw = QW.QApplication.activeWindow()
    
    if current_focus_tlw is None:
        
        return False
        
    
    if current_focus_tlw == win:
        
        return True
        
    
    if win in GetTLWParents( current_focus_tlw ):
        
        return True
        
    
    return False
    
def UpdateAppDisplayName():
    
    app_display_name = HG.client_controller.new_options.GetString( 'app_display_name' )
    
    QW.QApplication.instance().setApplicationDisplayName( '{} {}'.format( app_display_name, HC.SOFTWARE_VERSION ) )
    
    for tlw in QW.QApplication.topLevelWidgets():
        
        window_title = tlw.windowTitle()
        
        if window_title != '':
            
            tlw.setWindowTitle( '' )
            
            tlw.setWindowTitle( window_title )
            
        
    
def WidgetOrAnyTLWChildHasFocus( window ):
    
    active_window = QW.QApplication.activeWindow()
    
    if window == active_window:
        
        return True
        
    
    widget = QW.QApplication.focusWidget()
    
    if widget is None:
        
        # take active window in lieu of focus, if it is unavailable
        widget = active_window
        
    
    while widget is not None:
        
        if widget == window:
            
            return True
            
        
        widget = widget.parentWidget()
        
    
    return False
    
