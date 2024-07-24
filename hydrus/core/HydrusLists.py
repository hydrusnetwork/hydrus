import itertools
import typing

from hydrus.core import HydrusTime

def IntelligentMassIntersect( sets_to_reduce: typing.Collection[ set ] ):
    
    answer = None
    
    for set_to_reduce in sets_to_reduce:
        
        if len( set_to_reduce ) == 0:
            
            return set()
            
        
        if answer is None:
            
            answer = set( set_to_reduce )
            
        else:
            
            if len( answer ) == 0:
                
                return set()
                
            else:
                
                answer.intersection_update( set_to_reduce )
                
            
        
    
    if answer is None:
        
        return set()
        
    else:
        
        return answer
        
    

def IsAListLikeCollection( obj ):
    
    # protip: don't do isinstance( possible_list, collections.abc.Collection ) for a 'list' detection--strings pass it (and sometimes with infinite recursion) lol!
    return isinstance( obj, ( tuple, list, set, frozenset ) )
    

def MassExtend( iterables ):
    
    return [ item for item in itertools.chain.from_iterable( iterables ) ]
    

def MassUnion( iterables ):
    
    return { item for item in itertools.chain.from_iterable( iterables ) }
    

def MedianPop( population ):
    
    # assume it has at least one and comes sorted
    
    median_index = len( population ) // 2
    
    row = population.pop( median_index )
    
    return row
    

def PullNFromIterator( iterator, n ):
    
    chunk = []
    
    for item in iterator:
        
        chunk.append( item )
        
        if len( chunk ) == n:
            
            return chunk
            
        
    
    return chunk
    

def SetsIntersect( a, b ):
    
    if not isinstance( a, set ):
        
        a = set( a )
        
    
    return not a.isdisjoint( b )
    

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
        
    
