from qtpy import QtCore as QC
from qtpy import QtGui as QG

from hydrus.client.metadata import ClientRatings

# polygons

SIZE = QC.QSize( 12, 12 )

PENTAGRAM_STAR_COORDS = [
    QC.QPointF( 6, 0 ), # top
    QC.QPointF( 7.5, 4.5 ),
    QC.QPointF( 12, 4.5 ), # right
    QC.QPointF( 8.3, 7.2 ),
    QC.QPointF( 9.8, 12 ), # bottom right
    QC.QPointF( 6, 9 ),
    QC.QPointF( 2.2, 12 ), # bottom left
    QC.QPointF( 3.7, 7.2 ),
    QC.QPointF( 0, 4.5 ), # left
    QC.QPointF( 4.5, 4.5 )
]

FAT_STAR_COORDS = [
    QC.QPointF( 6, 0 ), # top
    QC.QPointF( 7.8, 4.1 ),
    QC.QPointF( 12, 4.6 ), # right
    QC.QPointF( 8.9, 7.6 ),
    QC.QPointF( 9.8, 12 ), # bottom right
    QC.QPointF( 6, 9.8 ),
    QC.QPointF( 2.2, 12 ), # bottom left
    QC.QPointF( 3.1, 7.6 ),
    QC.QPointF( 0, 4.5 ), # left
    QC.QPointF( 4.2, 4.1 )
]

TRIANGLE_UP_COORDS = [
    QC.QPointF(6, 0),
    QC.QPointF(12, 12),
    QC.QPointF(0, 12)
]

TRIANGLE_DOWN_COORDS = [
    QC.QPointF(0, 0),
    QC.QPointF(12, 0),
    QC.QPointF(6, 12)
]

TRIANGLE_RIGHT_COORDS = [ #triangle pointing right
    QC.QPointF(0, 0),
    QC.QPointF(12, 6),
    QC.QPointF(0, 12)
]

TRIANGLE_LEFT_COORDS = [ #triangle pointing right
    QC.QPointF(12, 0),
    QC.QPointF(0, 6),
    QC.QPointF(12, 12)
]

HEXAGON_COORDS = [
    QC.QPointF(6.0, 0.0),
    QC.QPointF(10.3, 2.6),
    QC.QPointF(10.3, 7.8),
    QC.QPointF(6.0, 10.4),
    QC.QPointF(1.7, 7.8),
    QC.QPointF(1.7, 2.6)
]

SMALL_HEXAGON_COORDS = [
    QC.QPointF(6.0, 2.8),
    QC.QPointF(8.7, 4.9),
    QC.QPointF(8.7, 7.3),
    QC.QPointF(6.0, 9.4),
    QC.QPointF(3.3, 7.3),
    QC.QPointF(3.3, 4.9)
]

SIX_POINT_STAR_COORDS = [
    QC.QPointF(6.0, 0.0),     # Top
    QC.QPointF(8.0, 3.0),
    QC.QPointF(11.0, 3.0),    # Upper right
    QC.QPointF(9.0, 6.0),     # Right inner
    QC.QPointF(11.0, 9.0),    # Lower right
    QC.QPointF(8.0, 9.0),
    QC.QPointF(6.0, 12.0),    # Bottom
    QC.QPointF(4.0, 9.0),
    QC.QPointF(1.0, 9.0),     # Lower left
    QC.QPointF(3.0, 6.0),     # Left inner
    QC.QPointF(1.0, 3.0),     # Upper left
    QC.QPointF(4.0, 3.0)
]

EIGHT_POINT_STAR_COORDS = [
    QC.QPointF(6.0, 0.5),     # Top
    QC.QPointF(6.9, 3.9),
    QC.QPointF(10.0, 2.0),    # Top right
    QC.QPointF(8.0, 5.1),
    QC.QPointF(11.5, 6.0),    # Right
    QC.QPointF(8.0, 6.9),
    QC.QPointF(10.0, 10.0),   # Bottom right
    QC.QPointF(7.0, 8.1),
    QC.QPointF(6.0, 11.5),    # Bottom
    QC.QPointF(5.0, 8.1),
    QC.QPointF(2.0, 10.0),    # Bottom left
    QC.QPointF(4.0, 6.9),
    QC.QPointF(0.5, 6.0),     # Left
    QC.QPointF(4.0, 5.1),
    QC.QPointF(2.0, 2.0),     # Top left
    QC.QPointF(5.0, 3.9)
]

DIAMOND_COORDS = [
    QC.QPointF(6, 0),    # Top
    QC.QPointF(12, 6),   # Right
    QC.QPointF(6, 12),   # Bottom
    QC.QPointF(0, 6)     # Left
]

RHOMBUS_L_COORDS = [
    QC.QPointF(0, 0),
    QC.QPointF(12,5),
    QC.QPointF(12, 12),
    QC.QPointF(0, 7)
]

RHOMBUS_R_COORDS = [
    QC.QPointF(12, 0),
    QC.QPointF(1, 4),
    QC.QPointF(0, 12),
    QC.QPointF(11, 8)
]

PENTAGON_COORDS = [
    QC.QPointF(6, 0),     # Top center
    QC.QPointF(12, 5.5),    # Upper right
    QC.QPointF(9, 12),  # Lower right
    QC.QPointF(3, 12),  # Lower left
    QC.QPointF(0, 5.5)      # Upper left
]

HOURGLASS_COORDS = [
    QC.QPointF(2,0),
    QC.QPointF(10,0),
    QC.QPointF(2,12),
    QC.QPointF(10,12)
]

X_SHAPE_COORDS = [
    QC.QPointF(2, 0),
    QC.QPointF(6, 4),
    QC.QPointF(10, 0),
    QC.QPointF(12, 2),
    QC.QPointF(8, 6),
    QC.QPointF(12, 10),
    QC.QPointF(10, 12),
    QC.QPointF(6, 8),
    QC.QPointF(2, 12),
    QC.QPointF(0, 10),
    QC.QPointF(4, 6),
    QC.QPointF(0, 2)
]

CROSS_COORDS = [
    QC.QPointF(4.5, 0),
    QC.QPointF(7.5, 0),
    QC.QPointF(7.5, 4.5),
    QC.QPointF(12, 4.5),
    QC.QPointF(12, 7.5),
    QC.QPointF(7.5, 7.5),
    QC.QPointF(7.5, 12),
    QC.QPointF(4.5, 12),
    QC.QPointF(4.5, 7.5),
    QC.QPointF(0, 7.5),
    QC.QPointF(0, 4.5),
    QC.QPointF(4.5, 4.5)
]


# paths

HEART_PATH = QG.QPainterPath()
HEART_PATH.moveTo(6, 12)
HEART_PATH.lineTo(1.5,6)
HEART_PATH.cubicTo(0,4, 3.5,0, 6, 4)
HEART_PATH.cubicTo(8.5,0, 12,4, 10.5,6)
HEART_PATH.lineTo(6, 12)
#altn. heart that doesn't look good at 12x12
# HEART_PATH.moveTo(6, 11.5)
# HEART_PATH.cubicTo(0.5, 7, 0.5, 0.25, 6, 5.25)
# HEART_PATH.cubicTo(11.5, 0.25, 11.5, 7, 6, 11.5)


TEARDROP_PATH = QG.QPainterPath()
TEARDROP_PATH.moveTo(6, 0)
TEARDROP_PATH.cubicTo(6.8, 5.2, 7.5, 5.5, 9, 7.3)
TEARDROP_PATH.cubicTo(11,10, 9,12 , 6,12)
TEARDROP_PATH.cubicTo(3,12, 1,10, 3,7.3)
TEARDROP_PATH.cubicTo(4.5, 5.5, 5.2, 5.2, 6, 0)

MOON_CRESCENT_PATH = QG.QPainterPath()
MOON_CRESCENT_PATH.moveTo(8, 1.1)
MOON_CRESCENT_PATH.cubicTo(0.25, 2, 0.25, 11, 8, 11.5)               
MOON_CRESCENT_PATH.cubicTo(10.25, 11.5, 11.75, 10.8, 11.75, 10.5)    
MOON_CRESCENT_PATH.cubicTo(6, 9, 6, 3, 11.75, 3)                     
MOON_CRESCENT_PATH.cubicTo(11.75, 1.8, 10.25, 1.2, 8, 1.1)           

# lookup dictionaries

SHAPE_COORDS_LOOKUP = {
    'fat star'        : FAT_STAR_COORDS,
    'pentagram star'  : PENTAGRAM_STAR_COORDS,
    'triangle up'     : TRIANGLE_UP_COORDS,
    'triangle down'   : TRIANGLE_DOWN_COORDS,
    'triangle right'  : TRIANGLE_RIGHT_COORDS,
    'triangle left'   : TRIANGLE_LEFT_COORDS,
    'hexagon'         : HEXAGON_COORDS,
    'small hexagon'   : SMALL_HEXAGON_COORDS,
    'six point star'  : SIX_POINT_STAR_COORDS,
    'eight point star': EIGHT_POINT_STAR_COORDS,
    'diamond'         : DIAMOND_COORDS,
    'rhombus left'    : RHOMBUS_L_COORDS,
    'rhombus right'   : RHOMBUS_R_COORDS,
    'pentagon'        : PENTAGON_COORDS,
    'hourglass'       : HOURGLASS_COORDS,
    'x shape'         : X_SHAPE_COORDS,
    'square cross'    : CROSS_COORDS,
}

SHAPE_DRAW_FN_LOOKUP = {
    'circle' : lambda painter, x, y : painter.drawEllipse( QC.QPointF( x + 6, y + 6 ), 6, 6 ),
    'square' : lambda painter, x, y : painter.drawRect( QC.QRectF( x, y, 12, 12 ) ),
    'heart'         : lambda painter, x, y : _draw_path( painter, HEART_PATH, x, y ),
    'teardrop'      : lambda painter, x, y : _draw_path( painter, TEARDROP_PATH, x, y ),
    'crescent moon' : lambda painter, x, y : _draw_path( painter, MOON_CRESCENT_PATH, x, y )
}

# 

def _draw_path( painter, path: QG.QPainterPath, x: float, y: float ):
    
    painter.save()
    painter.translate( x, y )
    painter.drawPath( path )
    painter.restore()

def DrawShape( painter, shape, x: float, y: float, text: str = None, text_colour: QG.QColor = None ):

    shape = ClientRatings.shape_to_str_lookup_dict.get( shape, None )

    if shape in SHAPE_DRAW_FN_LOOKUP:
        
        SHAPE_DRAW_FN_LOOKUP[ shape ]( painter, x, y )
        
        
    elif shape in SHAPE_COORDS_LOOKUP:
        
        painter.save()
        painter.translate( QC.QPointF( x, y ) )
        painter.drawPolygon( QG.QPolygonF( SHAPE_COORDS_LOOKUP[ shape ] ) )
        painter.restore()
    
    if text: 
        painter.save()

        if text_colour is not None:
            
            painter.setPen( QG.QPen( text_colour ) )

        font = painter.font()
        font.setBold( True )
        font.setPixelSize( 10 )
        painter.setFont( font )

        text_rect = QC.QRectF( x, y, 12, 12 )
        painter.drawText( text_rect, QC.Qt.AlignmentFlag.AlignCenter, text )

        painter.restore()