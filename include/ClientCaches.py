import ClientFiles
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import os
import random
import Queue
import threading
import time
import wx

class DataCache( object ):
    
    def __init__( self, cache_size_key, decay_duration = 1200 ):
        
        self._cache_size_key = cache_size_key
        
        self._decay_duration = decay_duration
        
        self._keys_to_data = {}
        self._keys_fifo = []
        
        self._total_estimated_memory_footprint = 0
        
        self._lock = threading.Lock()
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._keys_to_data = {}
            self._keys_fifo = []
            
            self._total_estimated_memory_footprint = 0
            
        
    
    def AddData( self, key, data ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                while self._total_estimated_memory_footprint > HC.options[ self._cache_size_key ]:
                    
                    ( deletee_key, last_access_time ) = self._keys_fifo.pop( 0 )
                    
                    deletee_data = self._keys_to_data[ deletee_key ]
                    
                    self._total_estimated_memory_footprint -= deletee_data.GetEstimatedMemoryFootprint()
                    
                    del self._keys_to_data[ deletee_key ]
                    
                
                self._keys_to_data[ key ] = data
                
                self._keys_fifo.append( ( key, HC.GetNow() ) )
                
                self._total_estimated_memory_footprint += data.GetEstimatedMemoryFootprint()
                
            
        
    
    def GetData( self, key ):
        
        with self._lock:
            
            if key not in self._keys_to_data: raise Exception( 'Cache error! Looking for ' + HC.u( key ) + ', but it was missing.' )
            
            i = 0
            
            for ( fifo_key, last_access_time ) in self._keys_fifo:
                
                if fifo_key == key:
                    
                    del self._keys_fifo[ i ]
                    
                    break
                    
                else: i += 1
                
            
            self._keys_fifo.append( ( key, HC.GetNow() ) )
            
            return self._keys_to_data[ key ]
            
        
    
    def HasData( self, key ):
        
        with self._lock: return key in self._keys_to_data
        
    
    def MaintainCache( self ):
        
        now = HC.GetNow()
        
        with self._lock:
            
            while True:
                
                if len( self._keys_fifo ) == 0: break
                else:
                    
                    ( key, last_access_time ) = self._keys_fifo[ 0 ]
                    
                    if now - last_access_time > self._decay_duration:
                        
                        del self._keys_fifo[ 0 ]
                        
                        data = self._keys_to_data[ key ]
                        
                        self._total_estimated_memory_footprint -= data.GetEstimatedMemoryFootprint()
                        
                        del self._keys_to_data[ key ]
                        
                    else: break
                    
                
            
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
class LocalBooruCache( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self._RefreshShares()
        
        HC.pubsub.sub( self, 'RefreshShares', 'refresh_local_booru_shares' )
        HC.pubsub.sub( self, 'RefreshShares', 'restart_booru' )
        
    
    def _CheckDataUsage( self ):
        
        info = self._local_booru_service.GetInfo()
        
        max_monthly_data = info[ 'max_monthly_data' ]
        used_monthly_data = info[ 'used_monthly_data' ]
        
        if max_monthly_data is not None and used_monthly_data > max_monthly_data: raise HydrusExceptions.ForbiddenException( 'This booru has used all its monthly data. Please try again next month.' )
        
    
    def _CheckFileAuthorised( self, share_key, hash ):
        
        self._CheckShareAuthorised( share_key )
        
        info = self._GetInfo( share_key )
        
        if hash not in info[ 'hashes_set' ]: raise HydrusExceptions.NotFoundException( 'That file was not found in that share.' )
        
    
    def _CheckShareAuthorised( self, share_key ):
        
        self._CheckDataUsage()
        
        info = self._GetInfo( share_key )
        
        timeout = info[ 'timeout' ]
        
        if timeout is not None and HC.GetNow() > timeout: raise HydrusExceptions.ForbiddenException( 'This share has expired.' )
        
    
    def _GetInfo( self, share_key ):
        
        try: info = self._keys_to_infos[ share_key ]
        except: raise HydrusExceptions.NotFoundException( 'Did not find that share on this booru.' )
        
        if info is None:
            
            info = HC.app.Read( 'local_booru_share', share_key )
            
            hashes = info[ 'hashes' ]
            
            info[ 'hashes_set' ] = set( hashes )
            
            media_results = HC.app.ReadDaemon( 'media_results', HC.LOCAL_FILE_SERVICE_KEY, hashes )
            
            info[ 'media_results' ] = media_results
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            info[ 'hashes_to_media_results' ] = hashes_to_media_results
            
            self._keys_to_infos[ share_key ] = info
            
        
        return info
        
    
    def _RefreshShares( self ):
        
        self._local_booru_service = HC.app.GetManager( 'services' ).GetService( HC.LOCAL_BOORU_SERVICE_KEY )
        
        self._keys_to_infos = {}
        
        share_keys = HC.app.Read( 'local_booru_share_keys' )
        
        for share_key in share_keys: self._keys_to_infos[ share_key ] = None
        
    
    def CheckShareAuthorised( self, share_key ):
        
        with self._lock: self._CheckShareAuthorised( share_key )
        
    
    def CheckFileAuthorised( self, share_key, hash ):
        
        with self._lock: self._CheckFileAuthorised( share_key, hash )
        
    
    def GetGalleryInfo( self, share_key ):
        
        with self._lock:
            
            self._CheckShareAuthorised( share_key )
            
            info = self._GetInfo( share_key )
            
            name = info[ 'name' ]
            text = info[ 'text' ]
            timeout = info[ 'timeout' ]
            media_results = info[ 'media_results' ]
            
            return ( name, text, timeout, media_results )
            
        
    
    def GetMediaResult( self, share_key, hash ):
        
        with self._lock:
            
            info = self._GetInfo( share_key )
            
            media_result = info[ 'hashes_to_media_results' ][ hash ]
            
            return media_result
            
        
    
    def GetPageInfo( self, share_key, hash ):
        
        with self._lock:
            
            self._CheckFileAuthorised( share_key, hash )
            
            info = self._GetInfo( share_key )
            
            name = info[ 'name' ]
            text = info[ 'text' ]
            timeout = info[ 'timeout' ]
            media_result = info[ 'hashes_to_media_results' ][ hash ]
            
            return ( name, text, timeout, media_result )
            
        
    
    def RefreshShares( self ):
        
        with self._lock:
            
            self._RefreshShares()
            
        
    
class MenuEventIdToActionCache( object ):
    
    def __init__( self ):
        
        self._ids_to_actions = {}
        self._actions_to_ids = {}
        
    
    def GetAction( self, event_id ):
        
        if event_id in self._ids_to_actions: return self._ids_to_actions[ event_id ]
        else: return None
        
    
    def GetId( self, command, data = None ):
        
        action = ( command, data )
        
        if action not in self._actions_to_ids:
            
            event_id = wx.NewId()
            
            self._ids_to_actions[ event_id ] = action
            self._actions_to_ids[ action ] = event_id
            
        
        return self._actions_to_ids[ action ]
        
    
MENU_EVENT_ID_TO_ACTION_CACHE = MenuEventIdToActionCache()

class RenderedImageCache( object ):
    
    def __init__( self, cache_type ):
        
        self._type = cache_type
        
        if self._type == 'fullscreen': self._data_cache = DataCache( 'fullscreen_cache_size' )
        elif self._type == 'preview': self._data_cache = DataCache( 'preview_cache_size' )
        
        self._total_estimated_memory_footprint = 0
        
        self._keys_being_rendered = {}
        
        HC.pubsub.sub( self, 'FinishedRendering', 'finished_rendering' )
        
    
    def Clear( self ): self._data_cache.Clear()
    
    def GetImage( self, media, target_resolution = None ):
        
        hash = media.GetHash()
        
        if target_resolution is None: target_resolution = media.GetResolution()
        
        key = ( hash, target_resolution )
        
        if self._data_cache.HasData( key ): return self._data_cache.GetData( key )
        elif key in self._keys_being_rendered: return self._keys_being_rendered[ key ]
        else:
            
            image_container = HydrusImageHandling.ImageContainer( media, target_resolution )
            
            self._keys_being_rendered[ key ] = image_container
            
            return image_container
            
        
    
    def HasImage( self, hash, target_resolution ):
        
        key = ( hash, target_resolution )
        
        return self._data_cache.HasData( key ) or key in self._keys_being_rendered
        
    
    def FinishedRendering( self, key ):
        
        if key in self._keys_being_rendered:
            
            image_container = self._keys_being_rendered[ key ]
            
            del self._keys_being_rendered[ key ]
            
            self._data_cache.AddData( key, image_container )
            
        
    
class ThumbnailCache( object ):
    
    def __init__( self ):
        
        self._data_cache = DataCache( 'thumbnail_cache_size' )
        
        self._queue = Queue.Queue()
        
        self._special_thumbs = {}
        
        self.Clear()
        
        threading.Thread( target = self.DAEMONWaterfall, name = 'Waterfall Daemon' ).start()
        
        HC.pubsub.sub( self, 'Clear', 'thumbnail_resize' )
        
    
    def Clear( self ):
        
        self._data_cache.Clear()
        
        self._special_thumbs = {}
        
        names = [ 'hydrus', 'flash', 'pdf', 'audio', 'video' ]
        
        for name in names:
            
            path = HC.STATIC_DIR + os.path.sep + name + '.png'
            
            thumbnail = HydrusFileHandling.GenerateThumbnail( path, HC.options[ 'thumbnail_dimensions' ] )
            
            resized_path = HC.STATIC_DIR + os.path.sep + name + '_resized.png'
            
            with open( resized_path, 'wb' ) as f: f.write( thumbnail )
            
            hydrus_bitmap = HydrusImageHandling.GenerateHydrusBitmap( resized_path )
            
            self._special_thumbs[ name ] = hydrus_bitmap
            
        
    
    def GetThumbnail( self, media ):
        
        mime = media.GetDisplayMedia().GetMime()
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            hash = media.GetDisplayMedia().GetHash()
            
            if not self._data_cache.HasData( hash ):
                
                path = None
                
                try:
                    
                    path = ClientFiles.GetThumbnailPath( hash, False )
                    
                    hydrus_bitmap = HydrusImageHandling.GenerateHydrusBitmap( path )
                    
                except HydrusExceptions.NotFoundException:
                    
                    print( 'Could not find the thumbnail for ' + hash.encode( 'hex' ) + '!' )
                    
                    return self._special_thumbs[ 'hydrus' ]
                    
                
                self._data_cache.AddData( hash, hydrus_bitmap )
                
            
            return self._data_cache.GetData( hash )
            
        elif mime in HC.AUDIO: return self._special_thumbs[ 'audio' ]
        elif mime in HC.VIDEO: return self._special_thumbs[ 'video' ]
        elif mime == HC.APPLICATION_FLASH: return self._special_thumbs[ 'flash' ]
        elif mime == HC.APPLICATION_PDF: return self._special_thumbs[ 'pdf' ]
        else: return self._special_thumbs[ 'hydrus' ]
        
    
    def Waterfall( self, page_key, medias ): self._queue.put( ( page_key, medias ) )
    
    def DAEMONWaterfall( self ):
        
        last_paused = HC.GetNowPrecise()
        
        while not HC.shutdown:
            
            try: ( page_key, medias ) = self._queue.get( timeout = 1 )
            except Queue.Empty: continue
            
            try:
                
                random.shuffle( medias )
                
                for media in medias:
                    
                    thumbnail = self.GetThumbnail( media )
                    
                    HC.pubsub.pub( 'waterfall_thumbnail', page_key, media, thumbnail )
                    
                    if HC.GetNowPrecise() - last_paused > 0.005:
                        
                        time.sleep( 0.00001 )
                        
                        last_paused = HC.GetNowPrecise()
                        
                    
                
            except Exception as e:
                
                HC.ShowException( e )
                
            
        
    