from hydrus.core import HydrusTime

def PullNFromIterator( iterator, n ):
    
    chunk = []
    
    for item in iterator:
        
        chunk.append( item )
        
        if len( chunk ) == n:
            
            return chunk
            
        
    
    return chunk
    

def SplitIteratorIntoAutothrottledChunks( iterator, starting_n, precise_time_to_stop ):
    
    n = starting_n
    
    chunk = PullNFromIterator( iterator, n )
    
    while len( chunk ) > 0:
        
        time_work_started = HydrusTime.GetNowPrecise()
        
        yield chunk
        
        work_time = HydrusTime.GetNowPrecise() - time_work_started
        
        items_per_second = n / work_time
        
        time_remaining = precise_time_to_stop - HydrusTime.GetNowPrecise()
        
        if HydrusTime.TimeHasPassedPrecise( precise_time_to_stop ):
            
            n = 1
            
        else:
            
            expected_items_in_remaining_time = max( 1, int( time_remaining * items_per_second ) )
            
            quad_speed = n * 4
            
            n = min( quad_speed, expected_items_in_remaining_time )
            
        
        chunk = PullNFromIterator( iterator, n )
        
    

def SplitListIntoChunks( xs, n ):
    
    if isinstance( xs, set ):
        
        xs = list( xs )
        
    
    for i in range( 0, len( xs ), n ):
        
        yield xs[ i : i + n ]
        
    

def SplitMappingIteratorIntoAutothrottledChunks( iterator, starting_n, precise_time_to_stop ):
    
    n = starting_n
    
    chunk_weight = 0
    chunk = []
    
    for ( tag_item, hash_items ) in iterator:
        
        chunk.append( ( tag_item, hash_items ) )
        
        chunk_weight += len( hash_items )
        
        if chunk_weight >= n:
            
            time_work_started = HydrusTime.GetNowPrecise()
            
            yield chunk
            
            work_time = HydrusTime.GetNowPrecise() - time_work_started
            
            chunk_weight = 0
            chunk = []
            
            items_per_second = n / work_time
            
            time_remaining = precise_time_to_stop - HydrusTime.GetNowPrecise()
            
            if HydrusTime.TimeHasPassedPrecise( precise_time_to_stop ):
                
                n = 1
                
            else:
                
                expected_items_in_remaining_time = max( 1, int( time_remaining * items_per_second ) )
                
                quad_speed = n * 4
                
                n = min( quad_speed, expected_items_in_remaining_time )
                
            
        
    
    if len( chunk ) > 0:
        
        yield chunk
        
    
