import HydrusConstants as HC

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
        
    
            
        
    
