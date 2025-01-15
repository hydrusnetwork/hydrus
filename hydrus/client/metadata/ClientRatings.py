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

shape_to_str_lookup_dict = {
    CIRCLE : 'circle',
    SQUARE : 'square',
    FAT_STAR : 'fat star',
    PENTAGRAM_STAR : 'pentagram star'
}

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
    
