import ClientFiles
import ClientImageHandling
import ClientVideoHandling
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusImageHandling
import HydrusGlobals
import HydrusThreading
import HydrusVideoHandling
import lz4
import os
import threading
import time
import wx

def GenerateHydrusBitmap( path, compressed = True ):
    
    numpy_image = ClientImageHandling.GenerateNumpyImage( path )
    
    return GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = compressed )
    
def GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = True ):
    
    ( y, x, depth ) = numpy_image.shape
    
    if depth == 4:
        
        buffer_format = wx.BitmapBufferFormat_RGBA
        
    else:
        
        buffer_format = wx.BitmapBufferFormat_RGB
        
    
    return HydrusBitmap( numpy_image.data, buffer_format, ( x, y ), compressed = compressed )
    
def GenerateHydrusBitmapFromPILImage( pil_image, compressed = True ):
    
    pil_image = HydrusImageHandling.Dequantize( pil_image )
    
    if pil_image.mode == 'RGBA':
        
        buffer_format = wx.BitmapBufferFormat_RGBA
        
    elif pil_image.mode == 'RGB':
        
        buffer_format = wx.BitmapBufferFormat_RGB
        
    
    return HydrusBitmap( pil_image.tobytes(), buffer_format, pil_image.size, compressed = compressed )
    
class ImageRenderer( object ):
    
    def __init__( self, media ):
        
        self._media = media
        self._numpy_image = None
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        self._path = client_files_manager.GetFilePath( hash, mime )
        
        HydrusGlobals.client_controller.CallToThread( self._Initialise )
        
    
    def _Initialise( self ):
        
        time.sleep( 0.00001 )
        
        self._numpy_image = ClientImageHandling.GenerateNumpyImage( self._path )
        
    
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
            
            wx_numpy_image = ClientImageHandling.ResizeNumpyImage( self._media.GetMime(), self._numpy_image, target_resolution )
            
        
        ( wx_height, wx_width, wx_depth ) = wx_numpy_image.shape
        
        wx_data = wx_numpy_image.data
        
        if wx_depth == 3:
            
            return wx.BitmapFromBuffer( wx_width, wx_height, wx_data )
            
        else:
            
            return wx.BitmapFromBufferRGBA( wx_width, wx_height, wx_data )
            
        
    
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
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        self._path = client_files_manager.GetFilePath( hash, mime )
        
        width_zoom = target_width / float( media_width )
        height_zoom = target_height / float( media_height )
        
        self._zoom = min( ( width_zoom, height_zoom ) )
        
        if self._zoom > 1.0: self._zoom = 1.0
        
    
class RasterContainerVideo( RasterContainer ):
    
    def __init__( self, media, target_resolution = None, init_position = 0 ):
        
        RasterContainer.__init__( self, media, target_resolution )
        
        self._init_position = init_position
        
        self._initialised = False
        
        self._frames = {}
        self._buffer_start_index = -1
        self._buffer_end_index = -1
        
        self._stop = False
        
        self._render_event = threading.Event()
        
        ( x, y ) = self._target_resolution
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        video_buffer_size_mb = new_options.GetInteger( 'video_buffer_size_mb' )
        
        duration = self._media.GetDuration()
        num_frames = self._media.GetNumFrames()
        
        if num_frames is None or num_frames == 0:
            
            message = 'The file with hash ' + media.GetHash().encode( 'hex' ) + ', had an invalid number of frames.'
            message += os.linesep * 2
            message += 'You may wish to try exporting, deleting, and the reimporting it.'
            
            HydrusData.ShowText( message )
            
            num_frames = 1
            
        
        self._average_frame_duration = float( duration ) / num_frames
        
        frame_buffer_length = ( video_buffer_size_mb * 1024 * 1024 ) / ( x * y * 3 )
        
        # if we can't buffer the whole vid, then don't have a clunky massive buffer
        
        max_streaming_buffer_size = max( 48, int( num_frames / ( duration / 3.0 ) ) ) # 48 or 3 seconds
        
        if max_streaming_buffer_size < frame_buffer_length and frame_buffer_length < num_frames:
            
            frame_buffer_length = max_streaming_buffer_size
            
        
        self._num_frames_backwards = frame_buffer_length * 2 / 3
        self._num_frames_forwards = frame_buffer_length / 3
        
        self._render_lock = threading.Lock()
        self._buffer_lock = threading.Lock()
        
        self._last_index_rendered = -1
        self._next_render_index = -1
        self._render_to_index = -1
        self._rendered_first_frame = False
        self._rush_to_index = None
        
        HydrusGlobals.client_controller.CallToThread( self.THREADRender )
        
    
    def _IndexOutOfRange( self, index, range_start, range_end ):
        
        before_start = index < range_start
        after_end = range_end < index
        
        if range_start < range_end:
            
            if before_start or after_end:
                
                return True
                
            
        else:
            
            if after_end and before_start:
                
                return True
                
            
        
        return False
        
    
    def _MaintainBuffer( self ):
        
        with self._buffer_lock:
            
            deletees = [ index for index in self._frames.keys() if self._IndexOutOfRange( index, self._buffer_start_index, self._buffer_end_index ) ]
            
            for i in deletees:
                
                del self._frames[ i ]
                
            
        
    
    def THREADMoveRenderTo( self, render_to_index ):
        
        with self._render_lock:
            
            if self._render_to_index != render_to_index:
                
                self._render_to_index = render_to_index
                
                self._render_event.set()
                
                self._initialised = True
                
            
        
    
    def THREADMoveRenderer( self, start_index, rush_to_index, render_to_index ):
        
        with self._render_lock:
            
            if self._next_render_index != start_index:
                
                self._renderer.set_position( start_index )
                
                self._last_index_rendered = -1
                
                self._next_render_index = start_index
                
                self._rush_to_index = rush_to_index
                
                self._render_to_index = render_to_index
                
                self._render_event.set()
                
                self._initialised = True
                
            
        
    
    def THREADRushTo( self, rush_to_index ):
        
        with self._render_lock:
            
            self._rush_to_index = rush_to_index
            
            self._render_event.set()
            
            self._initialised = True
            
        
    
    def THREADRender( self ):
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        duration = self._media.GetDuration()
        num_frames = self._media.GetNumFrames()
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            self._durations = HydrusImageHandling.GetGIFFrameDurations( self._path )
            
            self._renderer = ClientVideoHandling.GIFRenderer( self._path, num_frames, self._target_resolution )
            
        else:
            
            self._renderer = HydrusVideoHandling.VideoRendererFFMPEG( self._path, mime, duration, num_frames, self._target_resolution )
            
        
        self.GetReadyForFrame( self._init_position )
        
        while True:
            
            if self._stop or HydrusGlobals.view_shutdown:
                
                return
                
            
            ready_to_render = self._initialised
            frames_needed = not self._rendered_first_frame or self._next_render_index != ( self._render_to_index + 1 ) % num_frames
            
            if ready_to_render and frames_needed:
                
                with self._render_lock:
                    
                    self._rendered_first_frame = True
                    
                    frame_index = self._next_render_index # keep this before the get call, as it increments in a clock arithmetic way afterwards
                    
                    try:
                        
                        numpy_image = self._renderer.read_frame()
                        
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                        return
                        
                    finally:
                        
                        self._last_index_rendered = frame_index
                        
                        self._next_render_index = ( self._next_render_index + 1 ) % num_frames
                        
                    
                
                with self._buffer_lock:
                    
                    frame_needed = frame_index not in self._frames
                    
                    if self._rush_to_index is not None:
                        
                        reached_it = self._rush_to_index == frame_index
                        already_got_it = self._rush_to_index in self._frames
                        can_no_longer_reach_it = self._IndexOutOfRange( self._rush_to_index, self._next_render_index, self._render_to_index )
                        
                        if reached_it or already_got_it or can_no_longer_reach_it:
                            
                            self._rush_to_index = None
                            
                        
                    
                
                if frame_needed:
                    
                    frame = GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = False )
                    
                    with self._buffer_lock:
                        
                        self._frames[ frame_index ] = frame
                        
                    
                
                if self._rush_to_index is not None:
                    
                    time.sleep( 0.00001 )
                    
                else:
                    
                    half_a_frame = ( self._average_frame_duration / 1000.0 ) * 0.5
                    
                    time.sleep( half_a_frame ) # just so we don't spam cpu
                    
                
            else:
                
                self._render_event.wait( 1 )
                
                self._render_event.clear()
                
            
        
    
    def GetBufferIndices( self ):
        
        if self._last_index_rendered == -1:
            
            return None
            
        else:
            
            return ( self._buffer_start_index, self._last_index_rendered, self._buffer_end_index )
            
        
    
    def GetDuration( self, index ):
        
        if self._media.GetMime() == HC.IMAGE_GIF: return self._durations[ index ]
        else: return self._average_frame_duration
        
    
    def GetFrame( self, index ):
        
        with self._buffer_lock:
            
            frame = self._frames[ index ]
            
        
        self.GetReadyForFrame( index + 1 )
        
        return frame
        
    
    def GetHash( self ): return self._media.GetHash()
    
    def GetKey( self ): return ( self._media.GetHash(), self._target_resolution )
    
    def GetNumFrames( self ): return self._media.GetNumFrames()
    
    def GetReadyForFrame( self, next_index_to_expect ):
        
        num_frames = self.GetNumFrames()
        
        if num_frames > self._num_frames_backwards + 1 + self._num_frames_forwards:
            
            index_out_of_buffer = self._IndexOutOfRange( next_index_to_expect, self._buffer_start_index, self._buffer_end_index )
            
            ideal_buffer_start_index = max( 0, next_index_to_expect - self._num_frames_backwards )
            
            ideal_buffer_end_index = ( next_index_to_expect + self._num_frames_forwards ) % num_frames
            
            if not self._rendered_first_frame or index_out_of_buffer:
                
                self._buffer_start_index = ideal_buffer_start_index
                
                self._buffer_end_index = ideal_buffer_end_index
                
                HydrusGlobals.client_controller.CallToThread( self.THREADMoveRenderer, self._buffer_start_index, next_index_to_expect, self._buffer_end_index )
                
            else:
                
                # rendering can't go backwards, so dragging caret back shouldn't rewind either of these!
                
                if self.HasFrame( ideal_buffer_start_index ):
                    
                    self._buffer_start_index = ideal_buffer_start_index
                    
                
                if not self._IndexOutOfRange( self._next_render_index + 1, self._buffer_start_index, ideal_buffer_end_index ):
                    
                    self._buffer_end_index = ideal_buffer_end_index
                    
                
                HydrusGlobals.client_controller.CallToThread( self.THREADMoveRenderTo, self._buffer_end_index )
                
            
        else:
            
            if self._buffer_end_index == -1:
                
                self._buffer_start_index = 0
                
                self._buffer_end_index = num_frames - 1
                
                HydrusGlobals.client_controller.CallToThread( self.THREADMoveRenderer, self._buffer_start_index, next_index_to_expect, self._buffer_end_index )
                
            else:
                
                if not self.HasFrame( next_index_to_expect ):
                    
                    HydrusGlobals.client_controller.CallToThread( self.THREADRushTo, next_index_to_expect )
                    
                
            
        
        self._MaintainBuffer()
        
    
    def GetResolution( self ): return self._media.GetResolution()
    
    def GetSize( self ): return self._target_resolution
    
    def GetTotalDuration( self ):
        
        if self._media.GetMime() == HC.IMAGE_GIF: return sum( self._durations )
        else: return self._average_frame_duration * self.GetNumFrames()
        
    
    def HasFrame( self, index ):
        
        with self._buffer_lock:
            
            return index in self._frames
            
        
    
    def IsInitialised( self ):
        
        return self._initialised
        
    
    def IsScaled( self ): return self._zoom != 1.0
    
    def Stop( self ):
        
        self._stop = True
        
    
class HydrusBitmap( object ):
    
    def __init__( self, data, format, size, compressed = True ):
        
        self._compressed = compressed
        
        if self._compressed:
            
            self._data = lz4.dumps( data )
            
        else:
            
            self._data = data
            
        
        self._format = format
        self._size = size
        
    
    def _GetData( self ):
        
        if self._compressed:
            
            return lz4.loads( self._data )
            
        else:
            
            return self._data
            
        
    
    def CopyToWxBitmap( self, wx_bmp ):
        
        wx_bmp.CopyFromBuffer( self._GetData(), self._format )
        
    
    def GetDepth( self ):
        
        if self._format == wx.BitmapBufferFormat_RGB:
            
            return 3
            
        elif self._format == wx.BitmapBufferFormat_RGBA:
            
            return 4
            
        
    
    def GetWxBitmap( self ):
        
        ( width, height ) = self._size
        
        if self._format == wx.BitmapBufferFormat_RGB: return wx.BitmapFromBuffer( width, height, self._GetData() )
        else: return wx.BitmapFromBufferRGBA( width, height, self._GetData() )
        
    
    def GetWxImage( self ):
        
        ( width, height ) = self._size
        
        if self._format == wx.BitmapBufferFormat_RGB:
            
            return wx.ImageFromBuffer( width, height, self._GetData() )
            
        else:
            
            bitmap = wx.BitmapFromBufferRGBA( width, height, self._GetData() )
            
            image = wx.ImageFromBitmap( bitmap )
            
            bitmap.Destroy()
            
            return image
            
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        return len( self._data )
        
    
    def GetSize( self ): return self._size
    
