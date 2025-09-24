import collections
import collections.abc
import itertools
import numpy
import random

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime

def DedupeList( xs: collections.abc.Iterable ):
    
    if isinstance( xs, set ):
        
        return list( xs )
        
    
    xs_seen = set()
    
    xs_return = []
    
    for x in xs:
        
        if x in xs_seen:
            
            continue
            
        
        xs_return.append( x )
        
        xs_seen.add( x )
        
    
    return xs_return
    

class FastIndexUniqueList( collections.abc.MutableSequence ):
    
    def __init__( self, initial_items = None ):
        
        if initial_items is None:
            
            initial_items = []
            
        
        self._sort_key = None
        self._sort_reverse = False
        
        self._list = list( initial_items )
        
        self._items_to_indices = {}
        self._indices_dirty = True
        
    
    def __contains__( self, item ):
        
        if self._indices_dirty:
            
            self._RecalcIndices()
            
        
        return self._items_to_indices.__contains__( item )
        
    
    def __delitem__( self, index ):
        
        # only clean state is when we take what is the last item _at this point in time_
        # previously this test was after the delete and it messed everything up hey
        removing_last_item_in_list = index in ( -1, len( self._list ) - 1 )
        
        if removing_last_item_in_list:
            
            item = self._list[ index ]
            del self._list[ index ]
            
            if item in self._items_to_indices:
                
                del self._items_to_indices[ item ]
                
            
        else:
            
            del self._list[ index ]
            
            self._DirtyIndices()
            
        
    
    def __eq__( self, other ):
        
        if isinstance( other, list ):
            
            return self._list == other
            
        
        return False
        
    
    def __getitem__( self, value ):
        
        return self._list.__getitem__( value )
        
    
    def __iadd__( self, other ):
        
        self.extend( other )
        
    
    def __iter__( self ):
        
        return iter( self._list )
        
    
    def __len__( self ):
        
        return len( self._list )
        
    
    def __repr__( self ):
        
        return f'FastIndexUniqueList: {repr( self._list )}'
        
    
    def __setitem__( self, index, value ):
        
        old_item = self._list[ index ]
        
        if old_item in self._items_to_indices:
            
            del self._items_to_indices[ old_item ]
            
        
        self._list[ index ] = value
        self._items_to_indices[ value ] = index
        
    
    def _DirtyIndices( self ):
        
        self._indices_dirty = True
        
        self._items_to_indices = {}
        
    
    def _RecalcIndices( self ):
        
        self._items_to_indices = { item : index for ( index, item ) in enumerate( self._list ) }
        
        self._indices_dirty = False
        
    
    def append( self, item ):
        
        self.extend( ( item, ) )
        
    
    def clear( self ):
        
        self._list.clear()
        
        self._DirtyIndices()
        
    
    def extend( self, items ):
        
        if self._indices_dirty is None:
            
            self._RecalcIndices()
            
        
        for ( i, item ) in enumerate( items, start = len( self._list ) ):
            
            self._items_to_indices[ item ] = i
            
        
        self._list.extend( items )
        
    
    def index( self, item, **kwargs ):
        """
        This is fast!
        """
        
        if self._indices_dirty:
            
            self._RecalcIndices()
            
        
        try:
            
            result = self._items_to_indices[ item ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing()
            
        
        return result
        
    
    def insert( self, index, item ):
        
        self.insert_items( ( item, ), insertion_index = index )
        
    
    def insert_items( self, items, insertion_index = None ):
        
        if insertion_index is None:
            
            self.extend( items )
            
            self.sort()
            
        else:
            
            # don't forget we can insert elements in the final slot for an append, where index >= len( muh_list ) 
            
            for ( i, item ) in enumerate( items ):
                
                self._list.insert( insertion_index + i, item )
                
            
            self._DirtyIndices()
            
        
    
    def move_items( self, new_items: list, insertion_index: int ):
        
        items_to_move = []
        items_before_insertion_index = 0
        
        if insertion_index < 0:
            
            insertion_index = max( 0, len( self._list ) + ( insertion_index + 1 ) )
            
        
        for new_item in new_items:
            
            try:
                
                index = self.index( new_item )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            items_to_move.append( new_item )
            
            if index < insertion_index:
                
                items_before_insertion_index += 1
                
            
        
        if items_before_insertion_index > 0: # i.e. we are moving to the right
            
            items_before_insertion_index -= 1
            
        
        adjusted_insertion_index = insertion_index# - items_before_insertion_index
        
        if len( items_to_move ) == 0:
            
            return
            
        
        self.remove_items( items_to_move )
        
        self.insert_items( items_to_move, insertion_index = adjusted_insertion_index )
        
    
    def pop( self, index = -1 ):
        
        item = self._list.pop( index )
        
        del self[ index ]
        
        return item
        
    
    def random_sort( self ):
        
        def sort_key( x ):
            
            return random.random()
            
        
        self._sort_key = sort_key
        
        random.shuffle( self._list )
        
        self._DirtyIndices()
        
    
    def remove( self, item ):
        
        self.remove_items( ( item, ) )
        
    
    def remove_items( self, items ):
        
        deletee_indices = [ self.index( item ) for item in items ]
        
        deletee_indices.sort( reverse = True )
        
        for index in deletee_indices:
            
            del self[ index ]
            
        
    
    def reverse( self ):
        
        self._list.reverse()
        
        self._DirtyIndices()
        
    
    def sort( self, key = None, reverse = False ):
        
        if key is None:
            
            key = self._sort_key
            reverse = self._sort_reverse
            
        else:
            
            self._sort_key = key
            self._sort_reverse = reverse
            
        
        self._list.sort( key = key, reverse = reverse )
        
        self._DirtyIndices()
        
    

def ConvertTupleOfDatasToCasefolded( l: collections.abc.Sequence ) -> tuple:
    
    # TODO: We could convert/augment this guy to do HumanTextSort too so we have 3 < 22
    
    def casefold_obj( o ):
        
        if isinstance( o, str ):
            
            return o.casefold()
            
        elif isinstance( o, collections.abc.Sequence ):
            
            return ConvertTupleOfDatasToCasefolded( o )
            
        else:
            
            return o
            
        
    
    return tuple( ( casefold_obj( obj ) for obj in l ) )
    

def IntelligentMassIntersect( sets_to_reduce: collections.abc.Collection[ set ] ):
    
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
        
    

def IterateListRandomlyAndFast( xs: list ):
    
    # do this instead of a pre-for-loop shuffle on big lists
    
    for i in numpy.random.permutation( len( xs ) ):
        
        yield xs[ i ]
        
    

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
    

def PartitionIterator( pred: collections.abc.Callable[ [ object ], bool ], stream: collections.abc.Iterable[ object ] ):
    
    ( t1, t2 ) = itertools.tee( stream )
    
    return ( itertools.filterfalse( pred, t1 ), filter( pred, t2 ) )
    

def PartitionIteratorIntoLists( pred: collections.abc.Callable[ [ object ], bool ], stream: collections.abc.Iterable[ object ] ):
    
    ( a, b ) = PartitionIterator( pred, stream )
    
    return ( list( a ), list( b ) )
    

def PullNFromIterator( iterator, n ):
    
    chunk = []
    
    for item in iterator:
        
        chunk.append( item )
        
        if len( chunk ) == n:
            
            return chunk
            
        
    
    return chunk
    

def RandomiseListByChunks( xs, n ):
    
    blocks = list( SplitListIntoChunks( xs, n ) )
    
    random.shuffle( blocks )
    
    return [ item for block in blocks for item in block ] # 2025-06-03 - hydev's first nested list comprehension
    

def RandomPop( population ):
    
    random_index = random.randint( 0, len( population ) - 1 )
    
    row = population.pop( random_index )
    
    return row
    

def SampleSetByGettingFirst( s: set, n ):
    
    # sampling from a big set can be slow, so if we don't care about super random, let's just rip off the front and let __hash__ be our random
    
    n = min( len( s ), n )
    
    sample = set()
    
    if n == 0:
        
        return sample
        
    
    for ( i, obj ) in enumerate( s ):
        
        sample.add( obj )
        
        if i >= n - 1:
            
            break
            
        
    
    return sample
    

def SetsIntersect( a, b ):
    
    if not isinstance( a, set ):
        
        a = set( a )
        
    
    return not a.isdisjoint( b )
    

def SmoothOutMappingIterator( xs, n ):
    
    # de-spikifies mappings, so if there is ( tag, 20k files ), it breaks that up into manageable chunks
    
    chunk_weight = 0
    chunk = []
    
    for ( tag_item, hash_items ) in xs:
        
        for chunk_of_hash_items in SplitIteratorIntoChunks( hash_items, n ):
            
            yield ( tag_item, chunk_of_hash_items )
            
        
    

def SplayListForDB( xs ):
    
    return '(' + ','.join( ( str( x ) for x in xs ) ) + ')'
    

def SplitIteratorIntoAutothrottledChunks( iterator, starting_n, precise_time_to_stop ):
    
    n = starting_n
    
    chunk = PullNFromIterator( iterator, n )
    
    while len( chunk ) > 0:
        
        time_work_started = HydrusTime.GetNowPrecise()
        
        yield chunk
        
        actual_work_period = HydrusTime.GetNowPrecise() - time_work_started
        
        items_per_second = n / actual_work_period
        
        time_remaining = precise_time_to_stop - HydrusTime.GetNowPrecise()
        
        if HydrusTime.TimeHasPassedPrecise( precise_time_to_stop ):
            
            n = 1
            
        else:
            
            expected_items_in_remaining_time = max( 1, int( time_remaining * items_per_second ) )
            
            quad_speed = n * 4
            
            n = min( quad_speed, expected_items_in_remaining_time )
            
        
        chunk = PullNFromIterator( iterator, n )
        
    

def SplitIteratorIntoChunks( iterator, n ):
    
    chunk = []
    
    for item in iterator:
        
        chunk.append( item )
        
        if len( chunk ) == n:
            
            yield chunk
            
            chunk = []
            
        
    
    if len( chunk ) > 0:
        
        yield chunk
        
    

def SplitListIntoChunks( xs, n ):
    
    if isinstance( xs, set ):
        
        xs = list( xs )
        
    
    for i in range( 0, len( xs ), n ):
        
        yield xs[ i : i + n ]
        
    

def SplitListIntoChunksRich( xs, n ):
    
    if isinstance( xs, set ):
        
        xs = list( xs )
        
    
    num_to_do = len( xs )
    
    for i in range( 0, len( xs ), n ):
        
        yield ( i, num_to_do, xs[ i : i + n ] )
        
    

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
            
            actual_work_period = HydrusTime.GetNowPrecise() - time_work_started
            
            chunk_weight = 0
            chunk = []
            
            items_per_second = n / actual_work_period
            
            time_remaining = precise_time_to_stop - HydrusTime.GetNowPrecise()
            
            if HydrusTime.TimeHasPassedPrecise( precise_time_to_stop ):
                
                n = 1
                
            else:
                
                expected_items_in_remaining_time = max( 1, int( time_remaining * items_per_second ) )
                
                quad_speed = n * 4
                
                n = min( quad_speed, expected_items_in_remaining_time )
                
            
        
    
    if len( chunk ) > 0:
        
        yield chunk
        
    
