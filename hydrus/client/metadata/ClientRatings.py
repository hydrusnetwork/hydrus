from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

LIKE = 0
DISLIKE = 1
NULL = 2
SET = 3
MIXED = 4

CIRCLE = 0
SQUARE = 1
FAT_STAR = 2
PENTAGRAM_STAR = 3

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
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        shape = service.GetShape()
        
    except HydrusExceptions.DataMissing:
        
        shape = FAT_STAR
        
    
    return shape
    
