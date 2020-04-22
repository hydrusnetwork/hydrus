from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from qtpy import QtCore as QC
from qtpy import QtGui as QG

LIKE = 0
DISLIKE = 1
NULL = 2
SET = 3
MIXED = 4

CIRCLE = 0
SQUARE = 1
STAR = 2

default_like_colours = {}

default_like_colours[ LIKE ] = ( ( 0, 0, 0 ), ( 80, 200, 120 ) )
default_like_colours[ DISLIKE ] = ( ( 0, 0, 0 ), ( 200, 80, 120 ) )
default_like_colours[ NULL ] = ( ( 0, 0, 0 ), ( 191, 191, 191 ) )
default_like_colours[ MIXED ] = ( ( 0, 0, 0 ), ( 95, 95, 95 ) )

default_numerical_colours = {}

default_numerical_colours[ LIKE ] = ( ( 0, 0, 0 ), ( 80, 200, 120 ) )
default_numerical_colours[ DISLIKE ] = ( ( 0, 0, 0 ), ( 255, 255, 255 ) )
default_numerical_colours[ NULL ] = ( ( 0, 0, 0 ), ( 191, 191, 191 ) )
default_numerical_colours[ MIXED ] = ( ( 0, 0, 0 ), ( 95, 95, 95 ) )

STAR_COORDS = []

STAR_COORDS.append( QC.QPoint( 6, 0 ) ) # top
STAR_COORDS.append( QC.QPoint( 9, 4 ) )
STAR_COORDS.append( QC.QPoint( 12, 4 ) ) # right
STAR_COORDS.append( QC.QPoint( 9, 8 ) )
STAR_COORDS.append( QC.QPoint( 10, 12 ) ) # bottom right
STAR_COORDS.append( QC.QPoint( 6, 10 ) )
STAR_COORDS.append( QC.QPoint( 2, 12 ) ) # bottom left
STAR_COORDS.append( QC.QPoint( 3, 8 ) )
STAR_COORDS.append( QC.QPoint( 0, 4 ) ) # left
STAR_COORDS.append( QC.QPoint( 3, 4 ) )

def DrawLike( painter, x, y, service_key, rating_state ):
    
    shape = GetShape( service_key )
    
    ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, rating_state )
    
    painter.setPen( QG.QPen( pen_colour ) )
    painter.setBrush( QG.QBrush( brush_colour ) )

    if shape == CIRCLE:
        
        painter.drawEllipse( QC.QPointF( x+7, y+7 ), 6, 6 )
        
    elif shape == SQUARE:
        
        painter.drawRect( x+2, y+2, 12, 12 )
        
    elif shape == STAR:

        offset = QC.QPoint( x + 1, y + 1 )
        
        painter.translate( offset )
        
        painter.drawPolygon( QG.QPolygonF( STAR_COORDS ) )
        
        painter.translate( -offset )
        
    
def DrawNumerical( painter, x, y, service_key, rating_state, rating ):
    
    ( shape, stars ) = GetStars( service_key, rating_state, rating )
    
    x_delta = 0
    x_step = 12
    
    for ( num_stars, pen_colour, brush_colour ) in stars:
        
        painter.setPen( QG.QPen( pen_colour ) )
        painter.setBrush( QG.QBrush( brush_colour ) )
        
        for i in range( num_stars ):
            
            if shape == CIRCLE:
                
                painter.drawEllipse( QC.QPointF( x + 7 + x_delta, y + 7 ), 6, 6 )
                
            elif shape == SQUARE:
                
                painter.drawRect( x + 2 + x_delta, y + 2, 12, 12 )
                
            elif shape == STAR:
                
                offset = QC.QPoint( x + 1 + x_delta, y + 1 )
                
                painter.translate( offset )
                
                painter.drawPolygon( QG.QPolygonF( STAR_COORDS ) )
                
                painter.translate( -offset )
                
            
            x_delta += x_step
            
        
    
def GetLikeStateFromMedia( media, service_key ):
    
    on_exists = False
    off_exists = False
    null_exists = False
    
    for m in media:
        
        ratings_manager = m.GetRatingsManager()
        
        rating = ratings_manager.GetRating( service_key )
        
        if rating == 1:
            
            on_exists = True
            
        elif rating == 0:
            
            off_exists = True
            
        elif rating is None:
            
            null_exists = True
            
        
    
    if len( [ b for b in ( on_exists, off_exists, null_exists ) if b ] ) == 1:
        
        if on_exists: return LIKE
        elif off_exists: return DISLIKE
        else: return NULL
        
    else:
        
        return MIXED
        
    
def GetLikeStateFromRating( rating ):
    
    if rating == 1: return LIKE
    elif rating == 0: return DISLIKE
    else: return NULL
    
def GetNumericalStateFromMedia( media, service_key ):
    
    existing_rating = None
    null_exists = False
    
    for m in media:
        
        ratings_manager = m.GetRatingsManager()
        
        rating = ratings_manager.GetRating( service_key )
        
        if rating is None:
            
            if existing_rating is not None:
                
                return ( MIXED, None )
                
            else:
                
                null_exists = True
                
            
        else:
            
            if null_exists:
                
                return ( MIXED, None )
                
            else:
                
                if existing_rating is None:
                    
                    existing_rating = rating
                    
                else:
                    
                    if existing_rating != rating:
                        
                        return ( MIXED, None )
                        
                    
                
            
        
    
    if null_exists:
        
        return ( NULL, None )
        
    else:
        
        return ( SET, existing_rating )
        
    
def GetNumericalWidth( service_key ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        num_stars = service.GetNumStars()
        
    except HydrusExceptions.DataMissing:
        
        num_stars = 1
        
    
    return 4 + 12 * num_stars
    
def GetPenAndBrushColours( service_key, rating_state ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        colour = service.GetColour( rating_state )
        
    except HydrusExceptions.DataMissing:
        
        colour = ( ( 0, 0, 0 ), ( 0, 0, 0 ) )
        
    
    ( pen_rgb, brush_rgb ) = colour
    
    pen_colour = QG.QColor( *pen_rgb )
    brush_colour = QG.QColor( *brush_rgb )
    
    return ( pen_colour, brush_colour )
    
def GetShape( service_key ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        shape = service.GetShape()
        
    except HydrusExceptions.DataMissing:
        
        shape = STAR
        
    
    return shape
    
def GetStars( service_key, rating_state, rating ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
    except HydrusExceptions.DataMissing:
        
        return ( STAR, 0 )
        
    
    allow_zero = service.AllowZero()
    
    shape = service.GetShape()
    
    num_stars = service.GetNumStars()
    
    stars = []
    
    if rating_state in ( NULL, MIXED ):
        
        ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, rating_state )
        
        stars.append( ( num_stars, pen_colour, brush_colour ) )
        
    else:
        
        if allow_zero:
            
            num_stars_on = int( round( rating * num_stars ) )
            
        else:
            
            num_stars_on = int( round( rating * ( num_stars - 1 ) ) ) + 1
            
        
        num_stars_off = num_stars - num_stars_on
        
        ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, LIKE )
        
        stars.append( ( num_stars_on, pen_colour, brush_colour ) )
        
        ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, DISLIKE )
        
        stars.append( ( num_stars_off, pen_colour, brush_colour ) )
        
    
    return ( shape, stars )
    
class RatingsManager( object ):
    
    def __init__( self, service_keys_to_ratings ):
        
        self._service_keys_to_ratings = service_keys_to_ratings
        
    
    def Duplicate( self ):
        
        return RatingsManager( dict( self._service_keys_to_ratings ) )
        
    
    def GetRating( self, service_key ):
        
        if service_key in self._service_keys_to_ratings:
            
            return self._service_keys_to_ratings[ service_key ]
            
        else:
            
            return None
            
        
    
    def GetRatingSlice( self, service_keys ): return frozenset( { self._service_keys_to_ratings[ service_key ] for service_key in service_keys if service_key in self._service_keys_to_ratings } )
    
    def GetServiceKeysToRatings( self ): return self._service_keys_to_ratings
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            ( rating, hashes ) = row
            
            if rating is None and service_key in self._service_keys_to_ratings: del self._service_keys_to_ratings[ service_key ]
            else: self._service_keys_to_ratings[ service_key ] = rating
            
        
    
    def ResetService( self, service_key ):
        
        if service_key in self._service_keys_to_ratings: del self._service_keys_to_ratings[ service_key ]
        
    
