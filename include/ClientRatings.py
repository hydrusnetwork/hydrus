import HydrusConstants as HC
import wx

ALL_ON = 0
ALL_OFF = 1
ALL_NULL = 2
MIXED = 3

def DrawLike( dc, x, y, pen_colour, brush_colour ):
    
    dc.SetPen( wx.Pen( pen_colour ) )
    dc.SetBrush( wx.Brush( brush_colour ) )
    
    dc.DrawCircle( x + 7, y + 7, 6 )
    
def GetLikeStateFromMedia( media, service_key ):
    
    on_exists = False
    off_exists = False
    null_exists = False
    
    for m in media:
        
        ( local_ratings, remote_ratings ) = m.GetRatings()
        
        rating = local_ratings.GetRating( service_key )
        
        if rating == 1: on_exists = True
        elif rating == 0: off_exists = True
        elif rating is None: null_exists = True
        
    
    if len( [ b for b in ( on_exists, off_exists, null_exists ) if b ] ) == 1:
        
        if on_exists: return ALL_ON
        elif off_exists: return ALL_OFF
        else: return ALL_NULL
        
    else: return MIXED
    
def GetLikeStateFromRating( rating ):
    
    if rating == 1: return ALL_ON
    elif rating == 0: return ALL_OFF
    else: return ALL_NULL
    
def GetPenAndBrushColours( service_key, rating_state ):
    
    if rating_state == ALL_ON:
        
        brush_colour = wx.Colour( 80, 200, 120 )
        
    elif rating_state == ALL_OFF:
        
        brush_colour = wx.Colour( 200, 80, 120 )
        
    elif rating_state == ALL_NULL:
        
        brush_colour = wx.WHITE
        
    else:
        
        brush_colour = wx.Colour( 127, 127, 127 )
        
    
    return ( wx.BLACK, brush_colour )
    
class CPRemoteRatingsServiceKeys( object ):
    
    def __init__( self, service_keys_to_cp ):
        
        self._service_keys_to_cp = service_keys_to_cp
        
    
    def GetCP( self, service_key ):
        
        if service_key in self._service_keys_to_cp: return self._service_keys_to_cp[ service_key ]
        else: return ( None, None )
        
    
    def GetRatingSlice( self, service_keys ):
        
        # this doesn't work yet. it should probably use self.GetScore( service_key ) like I think Sort by remote rating does
        
        return frozenset( { self._service_keys_to_cp[ service_key ] for service_key in service_keys if service_key in self._service_keys_to_cp } )
        
    
    def GetServiceKeysToRatingsCP( self ): return self._service_keys_to_cp
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if service_key in self._service_keys_to_cp: ( current, pending ) = self._service_keys_to_cp[ service_key ]
        else:
            
            ( current, pending ) = ( None, None )
            
            self._service_keys_to_cp[ service_key ] = ( current, pending )
            
        
        # this may well need work; need to figure out how to set the pending back to None after an upload. rescind seems ugly
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            rating = content_update.GetInfo()
            
            current = rating
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            current = None
            
        elif action == HC.CONTENT_UPDATE_RESCIND_PENDING:
            
            pending = None
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            rating = content_update.GetInfo()
            
            pending = rating
            
        
    
    def ResetService( self, service_key ):
        
        if service_key in self._service_keys_to_cp:
            
            ( current, pending ) = self._service_keys_to_cp[ service_key ]
            
            self._service_keys_to_cp[ service_key ] = ( None, None )

class LocalRatingsManager( object ):
    
    def __init__( self, service_keys_to_ratings ):
        
        self._service_keys_to_ratings = service_keys_to_ratings
        
    
    def GetRating( self, service_key ):
        
        if service_key in self._service_keys_to_ratings: return self._service_keys_to_ratings[ service_key ]
        else: return None
        
    
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
        
    