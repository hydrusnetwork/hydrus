from qtpy import QtCore as QC
from qtpy import QtGui as QG

from hydrus.client import ClientConstants as CC
from hydrus.client.metadata import ClientRatings

_W = 12
_H = 12

_MIN_OUTLINE_PX = 1
_MAX_OUTLINE_PX = 4
_TARGET_OUTLINE_THICKNESS = 12 # 1:12 ratio of pixel width to shape outline

_FEATHER_IN = 0.25  #replace outer this% of outline pixels with 50% transparency (for SVG/QIcon)
_MAX_FEATHER_PX = 2

#

PAD_PX = 4

#do not use any padding inside paintershapes itself; it should only be used by parent widgets
PAD = QC.QSize( int( PAD_PX ), int( PAD_PX ) )

SIZE = QC.QSize( int( _W ), int( _H ) ) #width of this SIZE is used as default px value in options
STAR_W = PAD.width() + _W
STAR_H = PAD.height() + _H

INCDEC_BACKGROUND_SIZE = QC.QSize( int( STAR_W * 2 ), int( STAR_H ) )

# polygons
_ORIGINAL_PX_SCALE = 12.0

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
HEART_PATH.moveTo(6, 11)
HEART_PATH.lineTo(1.5, 5)
HEART_PATH.cubicTo(0, 3, 3.5, -1, 6, 3)
HEART_PATH.cubicTo(8.5, -1, 12, 3, 10.5, 5)
HEART_PATH.lineTo(6, 11)

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
    ClientRatings.FAT_STAR : FAT_STAR_COORDS,
    ClientRatings.PENTAGRAM_STAR : PENTAGRAM_STAR_COORDS,
    ClientRatings.TRIANGLE_UP : TRIANGLE_UP_COORDS,
    ClientRatings.TRIANGLE_DOWN : TRIANGLE_DOWN_COORDS,
    ClientRatings.TRIANGLE_RIGHT : TRIANGLE_RIGHT_COORDS,
    ClientRatings.TRIANGLE_LEFT : TRIANGLE_LEFT_COORDS,
    ClientRatings.HEXAGON : HEXAGON_COORDS,
    ClientRatings.SMALL_HEXAGON : SMALL_HEXAGON_COORDS,
    ClientRatings.SIX_POINT_STAR : SIX_POINT_STAR_COORDS,
    ClientRatings.EIGHT_POINT_STAR : EIGHT_POINT_STAR_COORDS,
    ClientRatings.DIAMOND : DIAMOND_COORDS,
    ClientRatings.RHOMBUS_L : RHOMBUS_L_COORDS,
    ClientRatings.RHOMBUS_R : RHOMBUS_R_COORDS,
    ClientRatings.PENTAGON : PENTAGON_COORDS,
    ClientRatings.HOURGLASS : HOURGLASS_COORDS,
    ClientRatings.X_SHAPE : X_SHAPE_COORDS,
    ClientRatings.CROSS : CROSS_COORDS,
}

SHAPE_DRAW_FN_LOOKUP = {
    ClientRatings.CIRCLE : lambda painter, x, y, width = _W, height = _H : painter.drawEllipse( QC.QPointF( x + width / 2, y + height / 2 ), width / 2, height / 2 ),
    ClientRatings.SQUARE : lambda painter, x, y, width = _W, height = _H : painter.drawRect( QC.QRectF( x, y, width, height ) ),
    ClientRatings.HEART : lambda painter, x, y, width = _W, height = _H : _draw_path( painter, HEART_PATH, x, y, width, height ),
    ClientRatings.TEARDROP : lambda painter, x, y, width = _W, height = _H : _draw_path( painter, TEARDROP_PATH, x, y, width, height ),
    ClientRatings.MOON_CRESCENT : lambda painter, x, y, width = _W, height = _H : _draw_path( painter, MOON_CRESCENT_PATH, x, y, width, height )
}

SVG_PIXMAP_CACHE = {}  # (shape_name, QColor.name()) -> QPixmap

# 

def _draw_path( painter, path: QG.QPainterPath, x, y, width = _W, height = _H ):
    
    scale_x = width / 12.0
    scale_y = height / 12.0
    
    transform = QG.QTransform()
    transform.scale( scale_x, scale_y )
    
    scaled_path = transform.map(path)
    
    painter.save()
    painter.translate( x, y )
    pen = painter.pen()
    pen.setWidthF( GetOutlinePx( width ) )
    painter.setPen( pen )
    painter.drawPath( scaled_path )
    painter.restore()
    

def _draw_svg_qicon( painter, shape_name: str, x, y, width = _W, height = _H ):

    icon = CC.global_icons().user_icons.get( shape_name )
    
    if icon is not None:
        
        rect = QC.QRectF( x, y, width, height )
        icon.paint( painter, rect.toRect() )
        
    

def _draw_icon_coloured( painter, shape_name: str, x, y, width = _W, height = _H ):
    
    icon = CC.global_icons().user_icons.get( shape_name )
    
    if icon is None:
        
        return
        
    
    color = painter.brush().color()
    cache_key = ( shape_name, color.name() )
    
    if cache_key in SVG_PIXMAP_CACHE:
        
        pixmap = SVG_PIXMAP_CACHE[ cache_key ]
        
    else:
        
        # TODO: there must be a nice way to draw a little border around this
        
        base_pixmap = icon.pixmap( width, height )
        
        # Create a tinted version
        tinted = QG.QPixmap( base_pixmap.size() )
        tinted.fill( QC.Qt.GlobalColor.transparent )
        
        p = QG.QPainter( tinted )
        p.setCompositionMode(QG.QPainter.CompositionMode.CompositionMode_Source)
        p.drawPixmap(0, 0, base_pixmap)
        
        p.setCompositionMode(QG.QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect( tinted.rect(), color )
        p.end()
        
        SVG_PIXMAP_CACHE[cache_key] = tinted
        pixmap = tinted
        
    
    painter.drawPixmap( QC.QPointF( x, y ), pixmap )
    

def _draw_icon_coloured_outlined( painter, rating_svg: str, x, y, width = _W, height = _H ):
    
    icon = CC.global_icons().user_icons.get( rating_svg )
    
    if icon is None:
        
        return
        
    
    fill_colour = painter.brush().color()
    stroke_colour = painter.pen().color()
    cache_key = ( rating_svg, fill_colour.name(), stroke_colour.name(), width, height )
    
    if cache_key in SVG_PIXMAP_CACHE:
        
        pixmap = SVG_PIXMAP_CACHE[ cache_key ]
        
    else:
        
        size = QC.QSize( int( width ), int( height ) )
        base = icon.pixmap( size )
        
        tinted = QG.QPixmap( size )
        tinted.fill( QC.Qt.GlobalColor.transparent )
        
        outline = QG.QPixmap( size )
        outline.fill( QC.Qt.GlobalColor.transparent )
        
        feathered = QG.QPixmap( size )
        feathered.fill( QC.Qt.GlobalColor.transparent )
        
        #make colour version
        p = QG.QPainter( tinted )        
        p.setRenderHint( QG.QPainter.RenderHint.Antialiasing, True )
        _painter_mask_opaque_pixels( p, base, fill_colour )
        p.end()
        
        po = QG.QPainter( outline )
        po.setRenderHint( QG.QPainter.RenderHint.Antialiasing, True )
        _painter_mask_opaque_pixels( po, base, stroke_colour )
        po.end()
        
        pf = QG.QPainter( feathered )
        
        hard_radius = max( int( GetOutlinePx( width ) * ( 1 - _FEATHER_IN ) ), 1 )
        feather = min( int( GetOutlinePx( width ) ), _MAX_FEATHER_PX )
        
        _painter_stamp_all_around( pf, hard_radius, outline )
        #pf.setOpacity( 0.5 )
        _painter_stamp_all_around( pf, feather, outline )
        pf.drawPixmap( 0, 0, tinted )
        
        SVG_PIXMAP_CACHE[ cache_key ] = feathered
        pixmap = feathered
        
    
    painter.drawPixmap( QC.QPointF( x, y ), pixmap )
    

def _painter_mask_opaque_pixels( painter, input_pixels, colour ):
    
    painter.setCompositionMode( QG.QPainter.CompositionMode.CompositionMode_Source )
    
    painter.drawPixmap( 0, 0, input_pixels )
    
    painter.setCompositionMode( QG.QPainter.CompositionMode.CompositionMode_SourceIn )
    
    painter.fillRect( input_pixels.rect(), colour )
    

def _painter_stamp_all_around( painter, radius, pixels ):
    
    for px_x in range ( -radius, radius ):
            
            for px_y in range ( -radius, radius ):
                
                painter.drawPixmap( QC.QPointF( px_x , px_y ), pixels )
                
            
        
    

#used for dynamic sizing e.g. from set size in options
#diameter = size (width or height) in px
def GetOutlinePx( diameter, ratio = _TARGET_OUTLINE_THICKNESS, min_thickness = _MIN_OUTLINE_PX, max_thickness = _MAX_OUTLINE_PX ):
    
    return max( min( diameter / ratio, max_thickness ), min_thickness )
    

def DrawShape( painter, star_type: ClientRatings.StarType, x, y, width = _W, height = _H, text: str | None = None, text_colour: QG.QColor | None = None ):
    
    if star_type.HasShape():
        
        shape = star_type.GetShape()
        
        if shape not in SHAPE_DRAW_FN_LOOKUP and shape not in SHAPE_COORDS_LOOKUP:
            
            shape = ClientRatings.FAT_STAR
            
        
        if shape in SHAPE_DRAW_FN_LOOKUP:
            
            pen = painter.pen()
            pen.setWidthF( GetOutlinePx( width ) )
            painter.setPen( pen )
            
            SHAPE_DRAW_FN_LOOKUP[ shape ]( painter, x, y, width, height )
            
        elif shape in SHAPE_COORDS_LOOKUP:
            
            scale_x = width / _ORIGINAL_PX_SCALE
            scale_y = height / _ORIGINAL_PX_SCALE
            
            scaled_points = [
                
                QC.QPointF( point.x() * scale_x, point.y() * scale_y )
                for point in SHAPE_COORDS_LOOKUP[ shape ]
                
            ]
            
            painter.save()
            pen = painter.pen()
            pen.setWidthF( GetOutlinePx( width ) )
            painter.setPen( pen )
            painter.translate( QC.QPointF( x, y ) )
            painter.drawPolygon( QG.QPolygonF( scaled_points ) )
            painter.restore()
            
        
    elif star_type.HasRatingSVG():
        
        rating_svg = star_type.GetRatingSVG()
        
        if rating_svg not in CC.global_icons().user_icons:
            
            default_star_type = ClientRatings.StarType( ClientRatings.FAT_STAR, None )
            
            DrawShape( painter, default_star_type, x, y, width = width, height = height, text = text, text_colour = text_colour )
            
            return
            
        
        _draw_icon_coloured_outlined( painter, rating_svg, x, y, width, height )
        
    
    if text:
        
        painter.save()
        
        if text_colour is not None:
            
            painter.setPen( QG.QPen( text_colour ) )
            
        
        font = painter.font()
        font.setBold( True )
        font.setPixelSize( int( height - 2 ) )
        painter.setFont( font )
        
        text_rect = QC.QRectF( x, y, width, height )
        painter.drawText( text_rect, QC.Qt.AlignmentFlag.AlignCenter, text )
        
        painter.restore()
        
    
