import collections
import threading
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

class CacheableObject( object ):
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        raise NotImplementedError()
        
    

class DataCache( object ):
    
    def __init__( self, controller, name, cache_size, timeout = 1200 ):
        
        self._controller = controller
        self._name = name
        self._cache_size = cache_size
        self._timeout = timeout
        
        self._keys_to_data = {}
        self._keys_fifo = collections.OrderedDict()
        
        self._total_estimated_memory_footprint = 0
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'MaintainCache', 'memory_maintenance_pulse' )
        
    
    def _Delete( self, key ):
        
        if key not in self._keys_to_data:
            
            return
            

        ( data, size_estimate ) = self._keys_to_data[ key ]
        
        del self._keys_to_data[ key ]
        
        self._total_estimated_memory_footprint -= size_estimate
        
        if HG.cache_report_mode:
            
            HydrusData.ShowText( 'Cache "{}" removing "{}", size "{}". Current size {}.'.format( self._name, key, HydrusData.ToHumanBytes( size_estimate ), HydrusData.ConvertValueRangeToBytes( self._total_estimated_memory_footprint, self._cache_size ) ) )
            
        
    
    def _DeleteItem( self ):
        
        ( deletee_key, last_access_time ) = self._keys_fifo.popitem( last = False )
        
        self._Delete( deletee_key )
        
    
    def _GetData( self, key ) -> CacheableObject:
        
        if key not in self._keys_to_data:
            
            raise Exception( 'Cache error! Looking for {}, but it was missing.'.format( key ) )
            
        
        self._TouchKey( key )

        ( data, size_estimate ) = self._keys_to_data[ key ]
        
        new_estimate = data.GetEstimatedMemoryFootprint()
        
        if new_estimate != size_estimate:
            
            self._total_estimated_memory_footprint += new_estimate - size_estimate
            
            self._keys_to_data[ key ] = ( data, new_estimate )
            
        
        return data
        
    
    def _TouchKey( self, key ):
        
        # have to delete first, rather than overwriting, so the ordereddict updates its internal order
        if key in self._keys_fifo:
            
            del self._keys_fifo[ key ]
            
        
        self._keys_fifo[ key ] = HydrusTime.GetNow()
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._keys_to_data = {}
            self._keys_fifo = collections.OrderedDict()
            
            self._total_estimated_memory_footprint = 0
            
        
    
    def AddData( self, key, data: CacheableObject ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                while self._total_estimated_memory_footprint > self._cache_size:
                    
                    self._DeleteItem()
                    
                
                size_estimate = data.GetEstimatedMemoryFootprint()
                
                self._keys_to_data[ key ] = ( data, size_estimate )
                
                self._total_estimated_memory_footprint += size_estimate
                
                self._TouchKey( key )
                
                if HG.cache_report_mode:
                    
                    HydrusData.ShowText(
                        'Cache "{}" adding "{}" ({}). Current size {}.'.format(
                            self._name,
                            key,
                            HydrusData.ToHumanBytes( size_estimate ),
                            HydrusData.ConvertValueRangeToBytes( self._total_estimated_memory_footprint, self._cache_size )
                        )
                    )
                    
                
            
        
    
    def DeleteData( self, key ):
        
        with self._lock:
            
            self._Delete( key )
            
        
    
    def GetData( self, key ) -> CacheableObject:
        
        with self._lock:
            
            return self._GetData( key )
            
        
    
    def GetIfHasData( self, key ) -> typing.Optional[ CacheableObject ]:
        
        with self._lock:
            
            if key in self._keys_to_data:
                
                return self._GetData( key )
                
            else:
                
                return None
                
            
        
    
    def GetSizeLimit( self ) -> int:
        
        with self._lock:
            
            return self._cache_size
            
        
    
    def HasData( self, key ) -> bool:
        
        with self._lock:
            
            return key in self._keys_to_data
            
        
    
    def MaintainCache( self ) -> None:
        
        with self._lock:
            
            while self._total_estimated_memory_footprint > self._cache_size:
                
                self._DeleteItem()
                
            
            while True:
                
                if len( self._keys_fifo ) == 0:
                    
                    break
                    
                else:
                    
                    ( key, last_access_time ) = next( iter( self._keys_fifo.items() ) )
                    
                    if HydrusTime.TimeHasPassed( last_access_time + self._timeout ):
                        
                        self._DeleteItem()
                        
                    else:
                        
                        break
                        
                    
                
            
        
    
    def SetCacheSizeAndTimeout( self, cache_size, timeout ) -> None:
        
        with self._lock:
            
            self._cache_size = cache_size
            self._timeout = timeout
            
        
        self.MaintainCache()
        
    
    def TouchKey( self, key ):
        
        with self._lock:
            
            self._TouchKey( key )
            
        
    
