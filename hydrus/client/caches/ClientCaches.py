import collections
import collections.abc
import json
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files.images import HydrusBlurhash
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientRendering
from hydrus.client import ClientSVGHandling
from hydrus.client import ClientThreading
from hydrus.client.caches import ClientCachesBase
from hydrus.client.files import ClientFilesMaintenance
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
        
    
class ThumbnailCache( object ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        cache_size = self._controller.new_options.GetInteger( 'thumbnail_cache_size' )
        cache_timeout = self._controller.new_options.GetInteger( 'thumbnail_cache_timeout' )
        
        self._data_cache = ClientCachesBase.DataCache( self._controller, 'thumbnail cache', cache_size, timeout = cache_timeout )
        
        self._magic_mime_thumbnail_ease_score_lookup = {}
        
        self._InitialiseMagicMimeScores()
        
        self._lock = threading.Lock()
        
        self._thumbnail_error_occurred = False
        
        self._waterfall_queue_quick = set()
        self._waterfall_queue = []
        
        self._waterfall_queue_empty_event = threading.Event()
        
        self._delayed_regeneration_queue_quick = set()
        self._delayed_regeneration_queue = []
        
        self._allow_blurhash_fallback = self._controller.new_options.GetBoolean( 'allow_blurhash_fallback' )
        
        self._waterfall_event = threading.Event()
        
        self._special_thumbs = {}
        
        self.Clear()
        
        self._controller.CallToThreadLongRunning( self.MainLoop )
        
        self._controller.sub( self, 'Clear', 'clear_thumbnail_cache' )
        self._controller.sub( self, 'ClearThumbnails', 'clear_thumbnails' )
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        
    
    def _GetBestRecoveryThumbnailHydrusBitmap( self, media_result: ClientMediaResult.MediaResult ):
        
        if self._allow_blurhash_fallback:
            
            blurhash = media_result.GetFileInfoManager().blurhash
            
            if blurhash is not None:
                
                try:
                    
                    ( media_width, media_height ) = media_result.GetResolution()
                    
                    bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
                    thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
                    thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
                    
                    ( expected_width, expected_height ) = HydrusImageHandling.GetThumbnailResolution( ( media_width, media_height ), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
                    
                    numpy_image = HydrusBlurhash.GetNumpyFromBlurhash( blurhash, expected_width, expected_height )
                    
                    hydrus_bitmap = ClientRendering.GenerateHydrusBitmapFromNumPyImage( numpy_image )
                    
                    return hydrus_bitmap
                    
                except:
                    
                    pass
                    
                
            
        
        return self._special_thumbs[ HC.APPLICATION_UNKNOWN ]
        
    
    def _GetThumbnailHydrusBitmap( self, media_result: ClientMediaResult.MediaResult ):
        
        if HG.blurhash_mode:
            
            return self._GetBestRecoveryThumbnailHydrusBitmap( media_result )
            
        
        hash = media_result.GetHash()
        
        locations_manager = media_result.GetLocationsManager()
        
        try:
            
            thumbnail_path = self._controller.client_files_manager.GetThumbnailPath( media_result )
            
        except HydrusExceptions.FileMissingException as e:
            
            if locations_manager.IsLocal():
                
                summary = 'Unable to get thumbnail for file {}.'.format( hash.hex() )
                
                self._HandleThumbnailException( hash, e, summary )
                
            
            return self._GetBestRecoveryThumbnailHydrusBitmap( media_result )
            
        
        thumbnail_mime = HC.IMAGE_JPEG
        
        try:
            
            thumbnail_mime = HydrusFileHandling.GetThumbnailMime( thumbnail_path )
            
            numpy_image = HydrusImageHandling.GenerateNumPyImage( thumbnail_path, thumbnail_mime )
            
        except Exception as e:
            
            try:
                
                # file is malformed, let's force a regen
                self._controller.files_maintenance_manager.RunJobImmediately( [ media_result ], ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL, pub_job_status = False )
                
            except Exception as e:
                
                summary = 'The thumbnail for file {} was not loadable. An attempt to regenerate it failed.'.format( hash.hex() )
                
                self._HandleThumbnailException( hash, e, summary )
                
                return self._GetBestRecoveryThumbnailHydrusBitmap( media_result )
                
            
            try:
                
                numpy_image = HydrusImageHandling.GenerateNumPyImage( thumbnail_path, thumbnail_mime )
                
            except Exception as e:
                
                summary = 'The thumbnail for file {} was not loadable. It was regenerated, but that file would not render either. Your image libraries or hard drive connection are unreliable. Please inform the hydrus developer what has happened.'.format( hash.hex() )
                
                self._HandleThumbnailException( hash, e, summary )
                
                return self._GetBestRecoveryThumbnailHydrusBitmap( media_result )
                
            
        
        ( current_width, current_height ) = HydrusImageHandling.GetResolutionNumPy( numpy_image )
        
        ( media_width, media_height ) = media_result.GetResolution()
        
        bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
        thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
        thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
        
        ( expected_width, expected_height ) = HydrusImageHandling.GetThumbnailResolution( ( media_width, media_height ), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
        
        exactly_as_expected = current_width == expected_width and current_height == expected_height
        
        rotation_exception = current_width == expected_height and current_height == expected_width
        
        correct_size = exactly_as_expected or rotation_exception
        
        if not correct_size:
            
            numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, ( expected_width, expected_height ) )
            
            if locations_manager.IsLocal():
                
                # we have the master file, so we should regen the thumb from source
                
                if HG.file_report_mode:
                    
                    HydrusData.ShowText( 'Thumbnail {} wrong size ({}x{} instead of {}x{}), scheduling regeneration from source.'.format( hash.hex(), current_width, current_height, expected_width, expected_height ) )
                    
                
                with self._lock:
                    
                    if media_result not in self._delayed_regeneration_queue_quick:
                        
                        self._delayed_regeneration_queue_quick.add( media_result )
                        
                        self._delayed_regeneration_queue.append( media_result )
                        
                    
                
            else:
                
                # we do not have the master file, so we have to scale up from what we have
                
                if HG.file_report_mode:
                    
                    HydrusData.ShowText( 'Thumbnail {} wrong size ({}x{} instead of {}x{}), only scaling due to no local source.'.format( hash.hex(), current_width, current_height, expected_width, expected_height ) )
                    
                
            
        
        hydrus_bitmap = ClientRendering.GenerateHydrusBitmapFromNumPyImage( numpy_image )
        
        return hydrus_bitmap
        
    
    def _HandleThumbnailException( self, hash, e, summary ):
        
        if self._thumbnail_error_occurred:
            
            HydrusData.Print( summary )
            
        else:
            
            self._thumbnail_error_occurred = True
            
            message = 'A thumbnail error has occurred. The problem thumbnail will appear with the default \'hydrus\' symbol. You may need to take hard drive recovery actions, and if the error is not obviously fixable, you can contact hydrus dev for additional help. Specific information for this first error follows. Subsequent thumbnail errors in this session will be silently printed to the log.'
            message += '\n' * 2
            message += str( e )
            message += '\n' * 2
            message += summary
            
            job_status = ClientThreading.JobStatus()
            
            job_status.SetStatusText( message )
            job_status.SetFiles( [ hash ], 'broken thumbnail' )
            
            CG.client_controller.pub( 'message', job_status )
            
        
    
    def _InitialiseMagicMimeScores( self ):
        
        # let's render our thumbs in order of ease of regeneration, so we rush what we can to screen as fast as possible and leave big vids until the end
        
        for mime in HC.ALLOWED_MIMES:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 5
            
        
        # default filetype thumbs are easiest
        
        self._magic_mime_thumbnail_ease_score_lookup[ None ] = 0
        self._magic_mime_thumbnail_ease_score_lookup[ HC.APPLICATION_UNKNOWN ] = 0
        
        for mime in HC.APPLICATIONS:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 0
            
        
        for mime in HC.AUDIO:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 0
            
        
        # images a little trickier
        
        for mime in HC.IMAGES:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 1
            
        
        for mime in HC.ANIMATIONS:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 2
            

        # could get more specific here because some applications will probably be even worse than videos
        for mime in HC.APPLICATIONS_WITH_THUMBNAILS:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 3
            
        
        # ffmpeg hellzone
        
        for mime in HC.VIDEO:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 3
            
        
    
    def _RecalcQueues( self ):
        
        # here we sort by the hash since this is both breddy random and more likely to access faster on a well defragged hard drive!
        # and now with the magic mime order
        
        def sort_waterfall( item ):
            
            ( page_key, media ) = item
            
            display_media = media.GetDisplayMedia()
            
            if display_media is None:
                
                magic_score = self._magic_mime_thumbnail_ease_score_lookup[ None ]
                hash = ''
                
            else:
                
                magic_score = self._magic_mime_thumbnail_ease_score_lookup[ display_media.GetMime() ]
                hash = display_media.GetHash()
                
            
            return ( magic_score, hash )
            
        
        self._waterfall_queue = list( self._waterfall_queue_quick )
        
        # we pop off the end, so reverse
        self._waterfall_queue.sort( key = sort_waterfall, reverse = True )
        
        if len( self._waterfall_queue ) == 0:
            
            self._waterfall_queue_empty_event.set()
            
        else:
            
            self._waterfall_queue_empty_event.clear()
            
        
        def sort_regen( item ):
            
            media_result = item
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            magic_score = self._magic_mime_thumbnail_ease_score_lookup[ mime ]
            
            return ( magic_score, hash )
            
        
        self._delayed_regeneration_queue = list( self._delayed_regeneration_queue_quick )
        
        # we pop off the end, so reverse
        self._delayed_regeneration_queue.sort( key = sort_regen, reverse = True )
        
    
    def _ShouldBeAbleToProvideThumb( self, media_result: ClientMediaResult.MediaResult ):
        
        locations_manager = media_result.GetLocationsManager()
        
        we_have_file = locations_manager.IsLocal()
        we_should_have_thumb = not locations_manager.GetCurrent().isdisjoint( CG.client_controller.services_manager.GetServiceKeys( ( HC.FILE_REPOSITORY, ) ) )
        we_have_blurhash = media_result.GetFileInfoManager().blurhash is not None
        
        return we_have_file or we_should_have_thumb or we_have_blurhash
        
    
    def CancelWaterfall( self, page_key: bytes, medias: list ):
        
        with self._lock:
            
            self._waterfall_queue_quick.difference_update( ( ( page_key, media ) for media in medias ) )
            
            cancelled_display_medias = { media.GetDisplayMedia() for media in medias }
            
            cancelled_display_medias.discard( None )
            
            cancelled_media_results = { media.GetMediaResult() for media in cancelled_display_medias }
            
            outstanding_delayed_hashes = { media_result.GetHash() for media_result in cancelled_media_results if media_result in self._delayed_regeneration_queue_quick }
            
            if len( outstanding_delayed_hashes ) > 0:
                
                self._controller.files_maintenance_manager.ScheduleJob( outstanding_delayed_hashes, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                
            
            self._delayed_regeneration_queue_quick.difference_update( cancelled_media_results )
            
            self._RecalcQueues()
            
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._data_cache.Clear()
            
            self._special_thumbs = {}
            
            bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
            thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
            thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
            
            image_svg_hydrus_bitmap = None
            
            try:
                
                svg_thumbnail_path = HydrusStaticDir.GetStaticPath( 'image.svg' )
                
                numpy_image_resolution = ClientSVGHandling.GetSVGResolution( svg_thumbnail_path )
                
                target_resolution = HydrusImageHandling.GetThumbnailResolution( numpy_image_resolution, bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
                
                numpy_image = ClientSVGHandling.GenerateThumbnailNumPyFromSVGPath( svg_thumbnail_path, target_resolution )
                
                image_svg_hydrus_bitmap = ClientRendering.GenerateHydrusBitmapFromNumPyImage( numpy_image )
                
            except Exception as e:
                
                pass
                
            
            for ( mime, thumbnail_path ) in HydrusFileHandling.mimes_to_default_thumbnail_paths.items():
                
                if mime in HC.IMAGES and image_svg_hydrus_bitmap is not None:
                    
                    self._special_thumbs[ mime ] = image_svg_hydrus_bitmap
                    
                    continue
                    
                
                numpy_image = HydrusImageHandling.GenerateNumPyImage( thumbnail_path, HC.IMAGE_PNG )
                
                numpy_image_resolution = HydrusImageHandling.GetResolutionNumPy( numpy_image )
                
                target_resolution = HydrusImageHandling.GetThumbnailResolution( numpy_image_resolution, bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
                
                numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, target_resolution )
                
                hydrus_bitmap = ClientRendering.GenerateHydrusBitmapFromNumPyImage( numpy_image )
                
                self._special_thumbs[ mime ] = hydrus_bitmap
                
            
            self._controller.pub( 'notify_complete_thumbnail_reset' )
            
            self._waterfall_queue_quick = set()
            self._delayed_regeneration_queue_quick = set()
            
            self._RecalcQueues()
            
        
    
    def ClearThumbnails( self, hashes ):
        
        with self._lock:
            
            for hash in hashes:
                
                self._data_cache.DeleteData( hash )
                
            
        
    
    def WaitUntilFree( self ):
        
        while True:
            
            if HG.started_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application shutting down!' )
                
            
            queue_is_empty = self._waterfall_queue_empty_event.wait( 1 )
            
            if queue_is_empty:
                
                return
                
            
        
    
    def GetHydrusPlaceholderThumbnail( self ) -> ClientRendering.HydrusBitmap:
        
        return self._special_thumbs[ HC.APPLICATION_UNKNOWN ]
        
    
    def GetThumbnail( self, media_result: ClientMediaResult.MediaResult ) -> ClientRendering.HydrusBitmap:
        
        if media_result is None:
            
            return self._special_thumbs[ HC.APPLICATION_UNKNOWN ]
            
        
        can_provide = self._ShouldBeAbleToProvideThumb( media_result )
        
        mime = media_result.GetMime()
        
        if mime in self._special_thumbs:
            
            default_thumb_hydrus_bitmap = self._special_thumbs[ mime ]
            
        else:
            
            default_thumb_hydrus_bitmap = self._special_thumbs[ HC.APPLICATION_UNKNOWN ]
            
        
        if can_provide:
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                hash = media_result.GetHash()
                
                result = self._data_cache.GetIfHasData( hash )
                
                if result is None:
                    
                    try:
                        
                        hydrus_bitmap = self._GetThumbnailHydrusBitmap( media_result )
                        
                    except:
                        
                        return default_thumb_hydrus_bitmap
                        
                    
                    self._data_cache.AddData( hash, hydrus_bitmap )
                    
                else:
                    
                    hydrus_bitmap = result
                    
                
                return hydrus_bitmap
                
            
        
        return default_thumb_hydrus_bitmap
        
    
    def HasThumbnailCached( self, media ):
        
        display_media = media.GetDisplayMedia()
        
        if display_media is None:
            
            return True
            
        
        media_result = display_media.GetMediaResult()
        
        mime = media_result.GetMime()
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            if self._ShouldBeAbleToProvideThumb( media_result ):
                
                hash = media_result.GetHash()
                
                return self._data_cache.HasData( hash )
                
            else:
                
                # yes because we provide the hydrus icon instantly
                return True
                
            
        else:
            
            return True
            
        
    
    def NotifyNewOptions( self ):
        
        cache_size = self._controller.new_options.GetInteger( 'thumbnail_cache_size' )
        cache_timeout = self._controller.new_options.GetInteger( 'thumbnail_cache_timeout' )
        
        self._data_cache.SetCacheSizeAndTimeout( cache_size, cache_timeout )
        
        allow_blurhash_fallback = self._controller.new_options.GetBoolean( 'allow_blurhash_fallback' )
        
        if allow_blurhash_fallback != self._allow_blurhash_fallback:
            
            self._allow_blurhash_fallback = allow_blurhash_fallback
            
            self.Clear()
            
        
    
    def Waterfall( self, page_key, medias ):
        
        with self._lock:
            
            self._waterfall_queue_quick.update( ( ( page_key, media ) for media in medias ) )
            
            self._RecalcQueues()
            
        
        self._waterfall_event.set()
        
    
    def MainLoop( self ):
        
        # TODO: Wangle this guy to a ManagerWithMainLoop
        
        while not HydrusThreading.IsThreadShuttingDown():
            
            time.sleep( 0.00001 )
            
            with self._lock:
                
                do_wait = len( self._waterfall_queue ) == 0 and len( self._delayed_regeneration_queue ) == 0
                
            
            if do_wait:
                
                self._waterfall_event.wait( 1 )
                
                self._waterfall_event.clear()
                
            
            start_time = HydrusTime.GetNowPrecise()
            stop_time = start_time + 0.005 # a bit of a typical frame
            
            page_keys_to_rendered_medias = collections.defaultdict( list )
            
            num_done = 0
            max_at_once = 16
            
            while not HydrusTime.TimeHasPassedPrecise( stop_time ) and num_done <= max_at_once:
                
                with self._lock:
                    
                    if len( self._waterfall_queue ) == 0:
                        
                        break
                        
                    
                    result = self._waterfall_queue.pop()
                    
                    if len( self._waterfall_queue ) == 0:
                        
                        self._waterfall_queue_empty_event.set()
                        
                    
                    self._waterfall_queue_quick.discard( result )
                    
                
                ( page_key, media ) = result
                
                if media.GetDisplayMedia() is not None:
                    
                    self.GetThumbnail( media.GetDisplayMedia().GetMediaResult() )
                    
                    page_keys_to_rendered_medias[ page_key ].append( media )
                    
                
                num_done += 1
                
            
            if len( page_keys_to_rendered_medias ) > 0:
                
                for ( page_key, rendered_medias ) in page_keys_to_rendered_medias.items():
                    
                    self._controller.pub( 'waterfall_thumbnails', page_key, rendered_medias )
                    
                
                time.sleep( 0.00001 )
                
            
            # now we will do regen if appropriate
            
            with self._lock:
                
                # got more important work or no work to do
                if len( self._waterfall_queue ) > 0 or len( self._delayed_regeneration_queue ) == 0 or CG.client_controller.CurrentlyPubSubbing():
                    
                    continue
                    
                
                media_result = self._delayed_regeneration_queue.pop()
                
                self._delayed_regeneration_queue_quick.discard( media_result )
                
            
            if HG.file_report_mode:
                
                hash = media_result.GetHash()
                
                HydrusData.ShowText( 'Thumbnail {} now regenerating from source.'.format( hash.hex() ) )
                
            
            try:
                
                self._controller.files_maintenance_manager.RunJobImmediately( [ media_result ], ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL, pub_job_status = False )
                
            except HydrusExceptions.FileMissingException:
                
                pass
                
            except Exception as e:
                
                hash = media_result.GetHash()
                
                summary = 'The thumbnail for file {} was incorrect, but a later attempt to regenerate it or load the new file back failed.'.format( hash.hex() )
                
                self._HandleThumbnailException( hash, e, summary )
                
            
        
    
