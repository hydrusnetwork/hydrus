from . import ClientFiles
from . import ClientImageHandling
from . import ClientVideoHandling
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusImageHandling
from . import HydrusGlobals as HG
from . import HydrusThreading
from . import HydrusVideoHandling
import os
import threading
import time
import wx

LZ4_OK = False

try:
    
    import lz4
    import lz4.block
    
    LZ4_OK = True
    
except Exception as e: # ImportError wasn't enough here as Linux went up the shoot with a __version__ doesn't exist bs
    
    pass
    
def FrameIndexOutOfRange( index, range_start, range_end ):
    
    before_start = index < range_start
    after_end = range_end < index
    
    if range_start < range_end:
        
        if before_start or after_end:
            
            return True
            
        
    else:
        
        if after_end and before_start:
            
            return True
            
        
    
    return False
    
def GenerateHydrusBitmap( path, mime, compressed = True ):
    
    numpy_image = ClientImageHandling.GenerateNumPyImage( path, mime )
    
    return GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = compressed )
    
def GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = True ):
    
    ( y, x, depth ) = numpy_image.shape
    
    return HydrusBitmap( numpy_image.data, ( x, y ), depth, compressed = compressed )
    
def GenerateHydrusBitmapFromPILImage( pil_image, compressed = True ):
    
    pil_image = HydrusImageHandling.Dequantize( pil_image )
    
    if pil_image.mode == 'RGBA':
        
        depth = 4
        
    elif pil_image.mode == 'RGB':
        
        depth = 3
        
    
    return HydrusBitmap( pil_image.tobytes(), pil_image.size, depth, compressed = compressed )
    
class ImageRenderer( object ):
    
    def __init__( self, media ):
        
        self._media = media
        self._numpy_image = None
        
        self._hash = self._media.GetHash()
        self._mime = self._media.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        self._path = client_files_manager.GetFilePath( self._hash, self._mime )
        
        HG.client_controller.CallToThread( self._Initialise )
        
    
    def _Initialise( self ):
        
        self._numpy_image = ClientImageHandling.GenerateNumPyImage( self._path, self._mime )
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        if self._numpy_image is None:
            
            ( width, height ) = self.GetResolution()
            
            return width * height * 3
            
        else:
            
            ( height, width, depth ) = self._numpy_image.shape
            
            return height * width * depth
            
        
    
    def GetHash( self ): return self._media.GetHash()
    
    def GetNumFrames( self ): return self._media.GetNumFrames()
    
    def GetResolution( self ): return self._media.GetResolution()
    
    def GetWXBitmap( self, target_resolution = None ):
        
        # add region param to this to allow clipping before resize
        
        if target_resolution is None:
            
            wx_numpy_image = self._numpy_image
            
        else:
            
            wx_numpy_image = ClientImageHandling.ResizeNumPyImageForMediaViewer( self._media.GetMime(), self._numpy_image, target_resolution )
            
        
        ( wx_height, wx_width, wx_depth ) = wx_numpy_image.shape
        
        wx_data = wx_numpy_image.data
        
        if wx_depth == 3:
            
            return HG.client_controller.bitmap_manager.GetBitmapFromBuffer( wx_width, wx_height, 24, wx_data )
            
        else:
            
            return HG.client_controller.bitmap_manager.GetBitmapFromBuffer( wx_width, wx_height, 32, wx_data )
            
        
    
    def IsReady( self ):
        
        return self._numpy_image is not None
        
    
class RasterContainer( object ):
    
    def __init__( self, media, target_resolution = None ):
        
        if target_resolution is None: target_resolution = media.GetResolution()
        
        ( width, height ) = target_resolution
        
        if width == 0 or height == 0:
            
            target_resolution = ( 100, 100 )
            
        
        self._media = media
        
        ( media_width, media_height ) = self._media.GetResolution()
        ( target_width, target_height ) = target_resolution
        
        if target_width > media_width or target_height > media_height:
            
            target_resolution = self._media.GetResolution()
            
        
        self._target_resolution = target_resolution
        
        ( target_width, target_height ) = target_resolution
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        self._path = client_files_manager.GetFilePath( hash, mime )
        
        width_zoom = target_width / media_width
        height_zoom = target_height / media_height
        
        self._zoom = min( ( width_zoom, height_zoom ) )
        
        if self._zoom > 1.0:
            
            self._zoom = 1.0
            
        
    
class RasterContainerVideo( RasterContainer ):
    
    def __init__( self, media, target_resolution = None, init_position = 0 ):
        
        RasterContainer.__init__( self, media, target_resolution )
        
        self._init_position = init_position
        
        self._initialised = False
        
        self._renderer = None
        
        self._frames = {}
        
        self._buffer_start_index = -1
        self._buffer_end_index = -1
        
        self._stop = False
        
        self._render_event = threading.Event()
        
        ( x, y ) = self._target_resolution
        
        new_options = HG.client_controller.new_options
        
        video_buffer_size_mb = new_options.GetInteger( 'video_buffer_size_mb' )
        
        duration = self._media.GetDuration()
        num_frames_in_video = self._media.GetNumFrames()
        
        if duration is None or duration == 0:
            
            message = 'The file with hash ' + media.GetHash().hex() + ', had an invalid duration.'
            message += os.linesep * 2
            message += 'You may wish to try regenerating its metadata through the advanced mode right-click menu.'
            
            HydrusData.ShowText( message )
            
            duration = 1.0
            
        
        if num_frames_in_video is None or num_frames_in_video == 0:
            
            message = 'The file with hash ' + media.GetHash().hex() + ', had an invalid number of frames.'
            message += os.linesep * 2
            message += 'You may wish to try regenerating its metadata through the advanced mode right-click menu.'
            
            HydrusData.ShowText( message )
            
            num_frames_in_video = 1
            
        
        self._average_frame_duration = duration / num_frames_in_video
        
        frame_buffer_length = ( video_buffer_size_mb * 1024 * 1024 ) // ( x * y * 3 )
        
        # if we can't buffer the whole vid, then don't have a clunky massive buffer
        
        max_streaming_buffer_size = max( 48, int( num_frames_in_video / ( duration / 3.0 ) ) ) # 48 or 3 seconds
        
        if max_streaming_buffer_size < frame_buffer_length and frame_buffer_length < num_frames_in_video:
            
            frame_buffer_length = max_streaming_buffer_size
            
        
        self._num_frames_backwards = frame_buffer_length * 2 // 3
        self._num_frames_forwards = frame_buffer_length // 3
        
        self._lock = threading.Lock()
        
        self._last_index_rendered = -1
        self._next_render_index = -1
        self._rendered_first_frame = False
        self._ideal_next_frame = 0
        
        HG.client_controller.CallToThread( self.THREADRender )
        
    
    def _HasFrame( self, index ):
        
        return index in self._frames
        
    
    def _IndexInRange( self, index, range_start, range_end ):
        
        return not FrameIndexOutOfRange( index, range_start, range_end )
        
    
    def _MaintainBuffer( self ):
        
        deletees = [ index for index in list(self._frames.keys()) if FrameIndexOutOfRange( index, self._buffer_start_index, self._buffer_end_index ) ]
        
        for i in deletees:
            
            del self._frames[ i ]
            
        
    
    def THREADRender( self ):
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        duration = self._media.GetDuration()
        num_frames_in_video = self._media.GetNumFrames()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        time.sleep( 0.00001 )
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            self._durations = HydrusImageHandling.GetGIFFrameDurations( self._path )
            
            self._renderer = ClientVideoHandling.GIFRenderer( self._path, num_frames_in_video, self._target_resolution )
            
        else:
            
            self._renderer = HydrusVideoHandling.VideoRendererFFMPEG( self._path, mime, duration, num_frames_in_video, self._target_resolution )
            
        
        # give ui a chance to draw a blank frame rather than hard-charge right into CPUland
        time.sleep( 0.00001 )
        
        self.GetReadyForFrame( self._init_position )
        
        with self._lock:
            
            self._initialised = True
            
        
        while True:
            
            if self._stop or HG.view_shutdown:
                
                self._renderer.Stop()
                
                self._renderer = None
                
                with self._lock:
                    
                    self._frames = {}
                    
                
                return
                
            
            #
            
            with self._lock:
                
                # lets see if we should move the renderer to a new position
                
                next_render_is_out_of_buffer = FrameIndexOutOfRange( self._next_render_index, self._buffer_start_index, self._buffer_end_index )
                buffer_not_fully_rendered = self._last_index_rendered != self._buffer_end_index
                
                currently_rendering_out_of_buffer = next_render_is_out_of_buffer and buffer_not_fully_rendered
                
                will_render_ideal_frame_soon = self._IndexInRange( self._next_render_index, self._buffer_start_index, self._ideal_next_frame )
                
                need_ideal_next_frame = not self._HasFrame( self._ideal_next_frame )
                
                will_not_get_to_ideal_frame = need_ideal_next_frame and not will_render_ideal_frame_soon
                
                if currently_rendering_out_of_buffer or will_not_get_to_ideal_frame:
                    
                    # we cannot get to the ideal next frame, so we need to rewind/reposition
                    
                    self._renderer.set_position( self._buffer_start_index )
                    
                    self._last_index_rendered = -1
                    
                    self._next_render_index = self._buffer_start_index
                    
                
                #
                
                need_to_render = self._last_index_rendered != self._buffer_end_index
                
            
            if need_to_render:
                
                with self._lock:
                    
                    self._rendered_first_frame = True
                    
                    frame_index = self._next_render_index # keep this before the get call, as it increments in a clock arithmetic way afterwards
                    
                    try:
                        
                        numpy_image = self._renderer.read_frame()
                        
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                        return
                        
                    finally:
                        
                        self._last_index_rendered = frame_index
                        
                        self._next_render_index = ( self._next_render_index + 1 ) % num_frames_in_video
                        
                    
                
                with self._lock:
                    
                    if self._next_render_index == 0 and self._buffer_end_index != num_frames_in_video - 1:
                        
                        # we need to rewind renderer
                        
                        self._renderer.set_position( 0 )
                        
                        self._last_index_rendered = -1
                        
                    
                    should_save_frame = not self._HasFrame( frame_index )
                    
                
                if should_save_frame:
                    
                    frame = GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = False )
                    
                    with self._lock:
                        
                        self._frames[ frame_index ] = frame
                        
                        self._MaintainBuffer()
                        
                    
                
                with self._lock:
                    
                    work_still_to_do = self._last_index_rendered != self._buffer_end_index
                    
                
                if work_still_to_do:
                    
                    time.sleep( 0.0001 )
                    
                else:
                    
                    half_a_frame = ( self._average_frame_duration / 1000.0 ) * 0.5
                    
                    sleep_duration = min( 0.1, half_a_frame ) # for 10s-long 3-frame gifs, wew
                    
                    time.sleep( sleep_duration ) # just so we don't spam cpu
                    
                
            else:
                
                self._render_event.wait( 1 )
                
                self._render_event.clear()
                
            
        
    
    def GetBufferIndices( self ):
        
        if self._last_index_rendered == -1:
            
            return None
            
        else:
            
            return ( self._buffer_start_index, self._last_index_rendered, self._buffer_end_index )
            
        
    
    def GetDuration( self, index ):
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            return self._durations[ index ]
            
        else:
            
            return self._average_frame_duration
            
        
    
    def GetFrame( self, index ):
        
        with self._lock:
            
            frame = self._frames[ index ]
            
        
        num_frames_in_video = self.GetNumFrames()
        
        if index == num_frames_in_video - 1:
            
            next_index = 0
            
        else:
            
            next_index = index + 1
            
        
        self.GetReadyForFrame( next_index )
        
        return frame
        
    
    def GetHash( self ):
        
        return self._media.GetHash()
        
    
    def GetKey( self ):
        
        return ( self._media.GetHash(), self._target_resolution )
        
    
    def GetNumFrames( self ):
        
        return self._media.GetNumFrames()
        
    
    def GetReadyForFrame( self, next_index_to_expect ):
        
        num_frames_in_video = self.GetNumFrames()
        
        frame_request_is_impossible = FrameIndexOutOfRange( next_index_to_expect, 0, num_frames_in_video - 1 )
        
        if frame_request_is_impossible:
            
            return
            
        
        with self._lock:
            
            self._ideal_next_frame = next_index_to_expect
            
            video_is_bigger_than_buffer = num_frames_in_video > self._num_frames_backwards + 1 + self._num_frames_forwards
            
            if video_is_bigger_than_buffer:
                
                current_ideal_is_out_of_buffer = self._buffer_start_index == -1 or FrameIndexOutOfRange( self._ideal_next_frame, self._buffer_start_index, self._buffer_end_index )
                
                ideal_buffer_start_index = max( 0, self._ideal_next_frame - self._num_frames_backwards )
                
                ideal_buffer_end_index = ( self._ideal_next_frame + self._num_frames_forwards ) % num_frames_in_video
                
                if current_ideal_is_out_of_buffer:
                    
                    # the current buffer won't get to where we want, so remake it
                    
                    self._buffer_start_index = ideal_buffer_start_index
                    self._buffer_end_index = ideal_buffer_end_index
                    
                else:
                    
                    # we can get to our desired position, but should we move the start and beginning on a bit?
                    
                    # we do not ever want to shunt left (rewind)
                    # we do not want to shunt right if we don't have the earliest frames yet--be patient
                    
                    # i.e. it is between the current start and the ideal
                    next_ideal_start_would_shunt_right = self._IndexInRange( ideal_buffer_start_index, self._buffer_start_index, self._ideal_next_frame )
                    have_next_ideal_start = self._HasFrame( ideal_buffer_start_index )
                    
                    if next_ideal_start_would_shunt_right and have_next_ideal_start:
                        
                        self._buffer_start_index = ideal_buffer_start_index
                        
                    
                    next_ideal_end_would_shunt_right = self._IndexInRange( ideal_buffer_end_index, self._buffer_end_index, self._buffer_start_index )
                    
                    if next_ideal_end_would_shunt_right:
                    
                        self._buffer_end_index = ideal_buffer_end_index
                        
                
            else:
                
                self._buffer_start_index = 0
                
                self._buffer_end_index = num_frames_in_video - 1
                
            
        
        self._render_event.set()
        
    
    def GetResolution( self ):
        
        return self._media.GetResolution()
        
    
    def GetSize( self ):
        
        return self._target_resolution
        
    
    def GetTimestampMS( self, frame_index ):
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            return sum( self._durations[ : frame_index ] )
            
        else:
            
            return self._average_frame_duration * frame_index
            
        
    
    def GetTotalDuration( self ):
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            return sum( self._durations )
            
        else:
            
            return self._average_frame_duration * self.GetNumFrames()
            
        
    
    def HasFrame( self, index ):
        
        with self._lock:
            
            return self._HasFrame( index )
            
        
    
    def CanHaveVariableFramerate( self ):
        
        with self._lock:
            
            return self._media.GetMime() == HC.IMAGE_GIF
            
        
    
    def IsInitialised( self ):
        
        with self._lock:
            
            return self._initialised
            
        
    
    def IsScaled( self ):
        
        return self._zoom != 1.0
        
    
    def Stop( self ):
        
        self._stop = True
        
    
class HydrusBitmap( object ):
    
    def __init__( self, data, size, depth, compressed = True ):
        
        if not LZ4_OK:
            
            compressed = False
            
        
        self._compressed = compressed
        
        if self._compressed:
            
            self._data = lz4.block.compress( data )
            
        else:
            
            self._data = data
            
        
        self._size = size
        self._depth = depth
        
    
    def _GetData( self ):
        
        if self._compressed:
            
            return lz4.block.decompress( self._data )
            
        else:
            
            return self._data
            
        
    
    def _GetWXBitmapFormat( self ):
        
        if self._depth == 3:
            
            return wx.BitmapBufferFormat_RGB
            
        elif self._depth == 4:
            
            return wx.BitmapBufferFormat_RGBA
            
        
    
    def CopyToWxBitmap( self, wx_bmp ):
        
        fmt = self._GetWXBitmapFormat()
        
        wx_bmp.CopyFromBuffer( self._GetData(), fmt )
        
    
    def GetDepth( self ):
        
        return self._depth
        
    
    def GetWxBitmap( self ):
        
        ( width, height ) = self._size
        
        return HG.client_controller.bitmap_manager.GetBitmapFromBuffer( width, height, self._depth * 8, self._GetData() )
        
    
    def GetWxImage( self ):
        
        ( width, height ) = self._size
        
        if self._depth == 3:
            
            return wx.ImageFromBuffer( width, height, self._GetData() )
            
        elif self._depth == 4:
            
            bitmap = HG.client_controller.bitmap_manager.GetBitmapFromBuffer( width, height, 32, self._GetData() )
            
            image = bitmap.ConvertToImage()
            
            HG.client_controller.bitmap_manager.ReleaseBitmap( bitmap )
            
            return image
            
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        return len( self._data )
        
    
    def GetSize( self ):
        
        return self._size
        
    
