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

from hydrus.client import ClientConstants as CC

def EncodeShapeNameToID(name: str) -> int:
    
    prefix = 900000000
    base36 = "0123456789abcdefghijklmnopqrstuvwxyz"
    value = 0
    
    for c in name.lower():
        
        if c not in base36:
            
            continue
        
        value *= 36
        
        value += base36.index(c)
    
    return prefix + value

for name in CC.global_icons().user_icons.keys():
    
    if len( name ) > 6:
        # limit to 6 character filenames to avoid running out of integer space
        # perhaps we should warn the user if they have any unaccepted svgs here, but assuming we document this feature it'll be fine
        continue
    
    shape_id = EncodeShapeNameToID( name )
    
    while shape_id in shape_to_str_lookup_dict:
        # rare but safe fallback
        shape_id += 1  
    
    shape_to_str_lookup_dict[ shape_id ] = f'svg:{name}'
    
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
        
    
def GetShape( service_key ):
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
        shape = service.GetShape()
        
    except HydrusExceptions.DataMissing:
        
        shape = FAT_STAR
        
    
    return shape
    
