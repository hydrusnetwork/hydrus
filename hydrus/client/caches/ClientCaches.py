import json
import threading
import typing

from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientRendering
from hydrus.client.caches import ClientCachesBase
from hydrus.client.parsing import ClientParsing
from hydrus.client.media import ClientMediaResult

class ParsingCache( object ):
    
    def __init__( self ):
        
        self._next_clean_cache_time = HydrusTime.GetNow()
        
        self._html_to_soups = {}
        self._json_to_jsons = {}
        
        self._lock = threading.Lock()
        
    
    def _CleanCache( self ):
        
        if HydrusTime.TimeHasPassed( self._next_clean_cache_time ):
            
            for cache in ( self._html_to_soups, self._json_to_jsons ):
                
                dead_datas = set()
                
                for ( data, ( last_accessed, parsed_object ) ) in cache.items():
                    
                    if HydrusTime.TimeHasPassed( last_accessed + 10 ):
                        
                        dead_datas.add( data )
                        
                    
                
                for dead_data in dead_datas:
                    
                    del cache[ dead_data ]
                    
                
            
            self._next_clean_cache_time = HydrusTime.GetNow() + 5
            
        
    
    def CleanCache( self ):
        
        with self._lock:
            
            self._CleanCache()
            
        
    
    def GetJSON( self, json_text ):
        
        with self._lock:
            
            now = HydrusTime.GetNow()
            
            if json_text not in self._json_to_jsons:
                
                json_object = json.loads( json_text )
                
                self._json_to_jsons[ json_text ] = ( now, json_object )
                
            
            ( last_accessed, json_object ) = self._json_to_jsons[ json_text ]
            
            if last_accessed != now:
                
                self._json_to_jsons[ json_text ] = ( now, json_object )
                
            
            if len( self._json_to_jsons ) > 10:
                
                self._CleanCache()
                
            
            return json_object
            
        
    
    def GetSoup( self, html ):
        
        with self._lock:
            
            now = HydrusTime.GetNow()
            
            if html not in self._html_to_soups:
                
                soup = ClientParsing.GetSoup( html )
                
                self._html_to_soups[ html ] = ( now, soup )
                
            
            ( last_accessed, soup ) = self._html_to_soups[ html ]
            
            if last_accessed != now:
                
                self._html_to_soups[ html ] = ( now, soup )
                
            
            if len( self._html_to_soups ) > 10:
                
                self._CleanCache()
                
            
            return soup
            
        
    

class ImageRendererCache( object ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        cache_size = self._controller.new_options.GetInteger( 'image_cache_size' )
        cache_timeout = self._controller.new_options.GetInteger( 'image_cache_timeout' )
        
        # there was a good user submission about 'pinned', which may be something to explore again in future
        # I looked into adding pin tech to the datacache itself. not a bad idea, but I'm not sure how to handle various overflow events, so that needs careful thought
        # the problem is not so much the caching atm, but the overflows
        
        self._data_cache = ClientCachesBase.DataCache( self._controller, 'image cache', cache_size, timeout = cache_timeout )
        
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        self._controller.sub( self, 'Clear', 'clear_image_cache' )
        self._controller.sub( self, 'ClearSpecificFiles', 'notify_files_need_cache_clear' )
        
    
    def Clear( self ):
        
        self._data_cache.Clear()
        
    
    def ClearSpecificFiles( self, hashes ):
        
        for hash in hashes:
            
            self._data_cache.DeleteData( hash )
            
        
    
    def GetImageRenderer( self, media_result: ClientMediaResult.MediaResult, this_is_for_metadata_alone = False ) -> ClientRendering.ImageRenderer:
        
        hash = media_result.GetHash()
        
        key = hash
        
        result = self._data_cache.GetIfHasData( key )
        
        if result is None:
            
            image_renderer = ClientRendering.ImageRenderer( media_result, this_is_for_metadata_alone = this_is_for_metadata_alone )
            
            # we are no longer going to let big lads flush the whole cache. they can render on demand
            
            image_cache_storage_limit_percentage = self._controller.new_options.GetInteger( 'image_cache_storage_limit_percentage' )
            acceptable_size = image_renderer.GetEstimatedMemoryFootprint() < self._data_cache.GetSizeLimit() * ( image_cache_storage_limit_percentage / 100 )
            
            if acceptable_size:
                
                self._data_cache.AddData( key, image_renderer )
                
            
        else:
            
            image_renderer = result
            
        
        return image_renderer
        
    
    def HasImageRenderer( self, hash ) -> bool:
        
        key = hash
        
        return self._data_cache.HasData( key )
        
    
    def NotifyNewOptions( self ):
        
        cache_size = self._controller.new_options.GetInteger( 'image_cache_size' )
        cache_timeout = self._controller.new_options.GetInteger( 'image_cache_timeout' )
        
        self._data_cache.SetCacheSizeAndTimeout( cache_size, cache_timeout )
        
    
    def PrefetchImageRenderers( self, media_results: list[ ClientMediaResult.MediaResult ] ):
        
        image_cache_storage_limit_percentage = self._controller.new_options.GetInteger( 'image_cache_storage_limit_percentage' )
        image_cache_prefetch_limit_percentage = self._controller.new_options.GetInteger( 'image_cache_prefetch_limit_percentage' )
        
        cache_size = self._data_cache.GetSizeLimit()
        
        single_file_size_we_are_ok_with = cache_size * ( image_cache_storage_limit_percentage / 100 )
        total_size_we_are_ok_with = cache_size * ( image_cache_prefetch_limit_percentage / 100 )
        total_size_we_have_prefetched_here = 0
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            key = hash
            
            result = self._data_cache.GetIfHasData( key )
            
            if result is not None:
                
                image_renderer = typing.cast( ClientRendering.ImageRenderer, result )
                
                if image_renderer.IsReady():
                    
                    total_size_we_have_prefetched_here += image_renderer.GetEstimatedMemoryFootprint()
                    
                else:
                    
                    return # we are still rendering a guy, no desire to add more work right now
                    
                
            else:
                
                # ok, here's a guy to do
                
                ( width, height ) = media_result.GetResolution()
                
                if width is None or height is None:
                    
                    return
                    
                
                expected_size = width * height * 3
                
                if total_size_we_have_prefetched_here + expected_size > total_size_we_are_ok_with:
                    
                    return # ok, this prefetch is pretty bulky
                    
                
                if expected_size > single_file_size_we_are_ok_with:
                    
                    return # ok this guy is too bulky to save
                    
                
                successful = self._data_cache.TryToFlushEasySpaceForPrefetch( expected_size )
                
                if successful:
                    
                    self.GetImageRenderer( media_result )
                    
                
                return
                
            
        
    

class ImageTileCache( object ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        cache_size = self._controller.new_options.GetInteger( 'image_tile_cache_size' )
        cache_timeout = self._controller.new_options.GetInteger( 'image_tile_cache_timeout' )
        
        self._data_cache = ClientCachesBase.DataCache( self._controller, 'image tile cache', cache_size, timeout = cache_timeout )
        
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        self._controller.sub( self, 'Clear', 'clear_image_tile_cache' )
        self._controller.sub( self, 'ClearSpecificFiles', 'notify_files_need_cache_clear' )
        
    
    def Clear( self ):
        
        self._data_cache.Clear()
        
    
    def ClearSpecificFiles( self, hashes ):
        
        for hash in hashes:
            
            keys = self._data_cache.GetAllKeys()
            
            for key in keys:
                
                key = typing.cast( tuple, key )
                
                if key[0] == hash:
                    
                    self._data_cache.DeleteData( key )
                    
                
            
        
    
    def GetTile( self, image_renderer: ClientRendering.ImageRenderer, media_result: ClientMediaResult.MediaResult, clip_rect, target_resolution ) -> ClientRendering.ImageTile:
        
        hash = media_result.GetHash()
        
        key = (
            hash,
            clip_rect.left(),
            clip_rect.top(),
            clip_rect.right(),
            clip_rect.bottom(),
            target_resolution.width(),
            target_resolution.height()
        )
        
        result = self._data_cache.GetIfHasData( key )
        
        if result is None:
            
            qt_pixmap = image_renderer.GetQtPixmap( clip_rect = clip_rect, target_resolution = target_resolution )
            
            tile = ClientRendering.ImageTile( hash, clip_rect, qt_pixmap )
            
            self._data_cache.AddData( key, tile )
            
        else:
            
            tile = result
            
        
        return tile
        
    
    def NotifyNewOptions( self ):
        
        cache_size = self._controller.new_options.GetInteger( 'image_tile_cache_size' )
        cache_timeout = self._controller.new_options.GetInteger( 'image_tile_cache_timeout' )
        
        self._data_cache.SetCacheSizeAndTimeout( cache_size, cache_timeout )
        
    
