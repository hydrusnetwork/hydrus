import HydrusConstants as HC
import HydrusGlobals
import wx

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

STAR_COORDS.append( wx.Point( 6, 0 ) ) # top
STAR_COORDS.append( wx.Point( 9, 4 ) )
STAR_COORDS.append( wx.Point( 12, 4 ) ) # right
STAR_COORDS.append( wx.Point( 9, 8 ) )
STAR_COORDS.append( wx.Point( 10, 12 ) ) # bottom right
STAR_COORDS.append( wx.Point( 6, 10 ) )
STAR_COORDS.append( wx.Point( 2, 12 ) ) # bottom left
STAR_COORDS.append( wx.Point( 3, 8 ) )
STAR_COORDS.append( wx.Point( 0, 4 ) ) # left
STAR_COORDS.append( wx.Point( 3, 4 ) )

def DrawLike( dc, x, y, service_key, rating_state ):
    
    shape = GetShape( service_key )
    
    ( pen_colour, brush_colour ) = GetPenAndBrushColours( service_key, rating_state )
    
    dc.SetPen( wx.Pen( pen_colour ) )
    dc.SetBrush( wx.Brush( brush_colour ) )

    if shape == CIRCLE:
        
        dc.DrawCircle( x + 7, y + 7, 6 )
        
    elif shape == SQUARE:
        
        dc.DrawRectangle( x + 2, y + 2, 12, 12 )
        
    elif shape == STAR:
        
        dc.DrawPolygon( STAR_COORDS, x + 1, y + 1 )
        
    
def DrawNumerical( dc, x, y, service_key, rating_state, rating ):
    
    ( shape, stars ) = GetStars( service_key, rating_state, rating )
    
    x_delta = 0
    x_step = 12
    
    for ( num_stars, pen_colour, brush_colour ) in stars:
        
        dc.SetPen( wx.Pen( pen_colour ) )
        dc.SetBrush( wx.Brush( brush_colour ) )
        
        for i in range( num_stars ):
            
            if shape == CIRCLE:
                
                dc.DrawCircle( x + 7 + x_delta, y + 7, 6 )
                
            elif shape == SQUARE:
                
                dc.DrawRectangle( x + 2 + x_delta, y + 2, 12, 12 )
                
            elif shape == STAR:
                
                dc.DrawPolygon( STAR_COORDS, x + 1 + x_delta, y + 1 )
                
            
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
        
    else: return MIXED
    
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
    
    service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
    
    num_stars = service.GetNumStars()
    
    return 4 + 12 * num_stars
    
def GetPenAndBrushColours( service_key, rating_state ):
    
    service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
    
    colour = service.GetColour( rating_state )
    
    ( pen_rgb, brush_rgb ) = colour
    
    pen_colour = wx.Colour( *pen_rgb )
    brush_colour = wx.Colour( *brush_rgb )
    
    return ( pen_colour, brush_colour )
    
def GetShape( service_key ):
    
    service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
    
    shape = service.GetShape()
    
    return shape
    
def GetStars( service_key, rating_state, rating ):
    
    service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
    
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
        
    
