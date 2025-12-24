from hydrus.core import HydrusExceptions

from hydrus.client import ClientGlobals as CG

LIKE = 0
DISLIKE = 1
NULL = 2
SET = 3
MIXED = 4

CIRCLE = 0
SQUARE = 1
FAT_STAR = 2
PENTAGRAM_STAR = 3
SIX_POINT_STAR = 4
EIGHT_POINT_STAR = 5
X_SHAPE = 6
CROSS = 7
TRIANGLE_UP = 30
TRIANGLE_DOWN = 31
TRIANGLE_RIGHT = 32
TRIANGLE_LEFT = 33
DIAMOND = 40
RHOMBUS_R = 42
RHOMBUS_L = 43
HOURGLASS = 44
PENTAGON = 50
HEXAGON = 60
SMALL_HEXAGON = 61
HEART = 101
TEARDROP = 102
MOON_CRESCENT = 103

DRAW_NO = 0
DRAW_ON_LEFT = 1
DRAW_ON_RIGHT = 2

# TODO: Ultimately, assuming svg works out and fill/border colours are all good, let's port all this to the default svg directory

shape_to_str_lookup_dict = {
    CIRCLE : 'circle',
    SQUARE : 'square',
    FAT_STAR : 'fat star',
    PENTAGRAM_STAR : 'pentagram star',
    SIX_POINT_STAR : 'six point star',
    EIGHT_POINT_STAR : 'eight point star',
    X_SHAPE : 'x shape',
    CROSS : 'square cross',
    TRIANGLE_UP : 'triangle up',
    TRIANGLE_DOWN : 'triangle down',
    TRIANGLE_RIGHT : 'triangle right',
    TRIANGLE_LEFT : 'triangle left',
    DIAMOND : 'diamond',
    RHOMBUS_R : 'rhombus right',
    RHOMBUS_L : 'rhombus left',
    HOURGLASS : 'hourglass',
    PENTAGON : 'pentagon',
    HEXAGON : 'hexagon',
    SMALL_HEXAGON : 'small hexagon',
    HEART : 'heart',
    TEARDROP : 'teardrop',
    MOON_CRESCENT : 'crescent moon'
}

#

def ConvertRatingToStars( num_stars: int, allow_zero: bool, rating: float ) -> int:
    
    if allow_zero:
        
        stars = int( round( rating * num_stars ) )
        
    else:
        
        stars = int( round( rating * ( num_stars - 1 ) ) ) + 1
        
    
    return stars
    

def ConvertStarsToRating( num_stars: int, allow_zero: bool, stars: int ) -> float:
    
    if stars > num_stars:
        
        stars = num_stars
        
    
    if allow_zero:
        
        if stars < 0:
            
            stars = 0
            
        
        rating = stars / num_stars
        
    else:
        
        if stars < 1:
            
            stars = 1
            
        
        rating = ( stars - 1 ) / ( num_stars - 1 )
        
    
    return rating
    

def GetIncDecStateFromMedia( media, service_key ):
    
    values_seen = { m.GetRatingsManager().GetRating( service_key ) for m in media }
    
    if len( values_seen ) == 0:
        
        return ( SET, 0 )
        
    elif len( values_seen ) == 1:
        
        ( value, ) = values_seen
        
        return ( SET, value )
        
    else:
        
        average_int = int( sum( ( m.GetRatingsManager().GetRating( service_key ) for m in media ) ) // len( media ) )
        
        return ( MIXED, average_int )
        
    

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
        
    

class StarType( object ):
    
    def __init__( self, shape: int | None, rating_svg: str | None ):
        
        if shape is None and rating_svg is None:
            
            shape = FAT_STAR
            
        
        self._shape = shape
        self._rating_svg = rating_svg
        
    
    def GetShape( self ):
        
        return self._shape
        
    
    def HasShape( self ):
        
        return self._shape is not None
        
    
    def GetRatingSVG( self ):
        
        return self._rating_svg
        
    
    def HasRatingSVG( self ):
        
        return self._rating_svg is not None
        
    

def GetStarType( service_key ) -> StarType:
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
        star_type = service.GetStarType()
        
    except HydrusExceptions.DataMissing:
        
        star_type = StarType( FAT_STAR, None )
        
    
    return star_type
    
