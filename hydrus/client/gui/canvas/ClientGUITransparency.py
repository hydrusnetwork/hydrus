from qtpy import QtCore as QC
from qtpy import QtGui as QG

def MakeCheckerboardBrush( tile_size: int ):
    
    light_grey = QG.QColor( 237, 237, 237 )
    dark_grey = QG.QColor( 222, 222, 222 )
    
    pixmap = QG.QPixmap( tile_size * 2, tile_size * 2 )
    
    pixmap.fill( light_grey )

    painter = QG.QPainter( pixmap )
    
    painter.fillRect( QC.QRect( tile_size, 0, tile_size, tile_size ), dark_grey )
    painter.fillRect( QC.QRect( 0, tile_size, tile_size, tile_size ), dark_grey )
    
    painter.end()

    return QG.QBrush( pixmap )
    

def MakeGreenscreenBrush():
    
    neon_greenscreen = QG.QColor( 34, 255, 0 )
    
    return QG.QBrush( neon_greenscreen )
    
