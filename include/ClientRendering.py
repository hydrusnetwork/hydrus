import ClientFiles
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusImageHandling
import HydrusGlobals
import HydrusThreading
import HydrusVideoHandling
import lz4
import numpy
import subprocess
import threading
import time
import wx

def GenerateHydrusBitmap( path, compressed = True ):
    
    try:
        
        numpy_image = HydrusImageHandling.GenerateNumpyImage( path )
        
        return GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = compressed )
        
    except:
        
        pil_image = HydrusImageHandling.GeneratePILImage( path )
        
        return GenerateHydrusBitmapFromPILImage( pil_image, compressed = compressed )
        
    
def GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = True ):
    
    ( y, x, depth ) = numpy_image.shape
    
    if depth == 4: buffer_format = wx.BitmapBufferFormat_RGBA
    else: buffer_format = wx.BitmapBufferFormat_RGB
    
    return HydrusBitmap( numpy_image.data, buffer_format, ( x, y ), compressed = compressed )
    
def GenerateHydrusBitmapFromPILImage( pil_image, compressed = True ):
    
    if pil_image.mode == 'RGBA' or ( pil_image.mode == 'P' and pil_image.info.has_key( 'transparency' ) ):
        
        if pil_image.mode == 'P': pil_image = pil_image.convert( 'RGBA' )
        
        format = wx.BitmapBufferFormat_RGBA
        
    else:
        
        if pil_image.mode != 'RGB': pil_image = pil_image.convert( 'RGB' )
        
        format = wx.BitmapBufferFormat_RGB
        
    
    return HydrusBitmap( pil_image.tobytes(), format, pil_image.size, compressed = compressed )
    
class RasterContainer( object ):
    
    def __init__( self, media, target_resolution = None ):
        
        if target_resolution is None: target_resolution = media.GetResolution()
        
        ( width, height ) = target_resolution
        
        if width == 0 or height == 0: target_resolution = ( 100, 100 )
        
        self._media = media
        self._target_resolution = target_resolution
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        self._path = ClientFiles.GetFilePath( hash, mime )
        
        ( original_width, original_height ) = self._media.GetResolution()
        
        ( my_width, my_height ) = target_resolution
        
        width_zoom = my_width / float( original_width )
        height_zoom = my_height / float( original_height )
        
        self._zoom = min( ( width_zoom, height_zoom ) )
        
        if self._zoom > 1.0: self._zoom = 1.0
        
    
class RasterContainerImage( RasterContainer ):
    
    def __init__( self, media, target_resolution = None ):
        
        RasterContainer.__init__( self, media, target_resolution )
        
        self._hydrus_bitmap = None
        
        HydrusGlobals.client_controller.CallToThread( self._InitialiseHydrusBitmap )
        
    
    def _InitialiseHydrusBitmap( self ):
        
        time.sleep( 0.00001 )
        
        try:
            
            numpy_image = HydrusImageHandling.GenerateNumpyImage( self._path )
            
            resized_numpy_image = HydrusImageHandling.EfficientlyResizeNumpyImage( numpy_image, self._target_resolution )
            
            hydrus_bitmap = GenerateHydrusBitmapFromNumPyImage( resized_numpy_image )
            
        except:
            
            pil_image = HydrusImageHandling.GeneratePILImage( self._path )
            
            resized_pil_image = HydrusImageHandling.EfficientlyResizePILImage( pil_image, self._target_resolution )
            
            hydrus_bitmap = GenerateHydrusBitmapFromPILImage( resized_pil_image )
            
        
        self._hydrus_bitmap = hydrus_bitmap
        
        HydrusGlobals.client_controller.pub( 'finished_rendering', self.GetKey() )
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        if self._hydrus_bitmap is None:
            
            ( width, height ) = self._target_resolution
            
            return width * height * 3
            
        else: return self._hydrus_bitmap.GetEstimatedMemoryFootprint()
        
    
    def GetHash( self ): return self._media.GetHash()
    
    def GetHydrusBitmap( self ): return self._hydrus_bitmap
    
    def GetKey( self ): return ( self._media.GetHash(), self._target_resolution )
    
    def GetNumFrames( self ): return self._media.GetNumFrames()
    
    def GetResolution( self ): return self._media.GetResolution()
    
    def GetSize( self ): return self._target_resolution
    
    def GetZoom( self ): return self._zoom
    
    def IsRendered( self ): return self._hydrus_bitmap is not None
    
    def IsScaled( self ): return self._zoom != 1.0
    
class RasterContainerVideo( RasterContainer ):
    
    BUFFER_SIZE = 1024 * 1024 * 96
    
    def __init__( self, media, target_resolution = None, init_position = 0 ):
        
        RasterContainer.__init__( self, media, target_resolution )
        
        self._frames = {}
        self._last_index_asked_for = -1
        self._buffer_start_index = -1
        self._buffer_end_index = -1
        
        ( x, y ) = self._target_resolution
        
        frame_buffer_length = self.BUFFER_SIZE / ( x * y * 3 )
        
        self._num_frames_backwards = frame_buffer_length * 2 / 3
        self._num_frames_forwards = frame_buffer_length / 3
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        path = ClientFiles.GetFilePath( hash, mime )
        
        duration = self._media.GetDuration()
        num_frames = self._media.GetNumFrames()
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            self._durations = HydrusImageHandling.GetGIFFrameDurations( self._path )
            
            self._renderer = HydrusVideoHandling.GIFRenderer( path, num_frames, target_resolution )
            
        else:
            
            try:
                
                self._frame_duration = HydrusVideoHandling.GetVideoFrameDuration( self._path )
                
            except HydrusExceptions.CantRenderWithCVException:
                
                self._frame_duration = float( duration ) / num_frames
                
            
            self._renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration, num_frames, target_resolution )
            
        
        self._render_lock = threading.Lock()
        
        self._next_render_index = 0
        self._render_to_index = -1
        self._rendered_first_frame = False
        
        self.SetFramePosition( init_position )
        
    
    def _MaintainBuffer( self ):
        
        deletees = []
        
        for index in self._frames.keys():
            
            if self._buffer_start_index < self._buffer_end_index:
                
                if index < self._buffer_start_index or self._buffer_end_index < index: deletees.append( index )
                
            else:
                
                if self._buffer_end_index < index and index < self._buffer_start_index: deletees.append( index )
                
            
        
        for i in deletees: del self._frames[ i ]
        
    
    def _RENDERERSetRenderToPosition( self, index ):
        
        with self._render_lock:
            
            if self._render_to_index != index:
                
                self._render_to_index = index
                
                HydrusGlobals.client_controller.CallToThread( self.THREADRender )
                
            
        
    
    def _RENDERERSetFramePosition( self, index ):
        
        with self._render_lock:
            
            if index == self._next_render_index: return
            else:
                
                self._renderer.set_position( index )
                
                self._next_render_index = index
                self._render_to_index = index
                
            
        
    
    def THREADRender( self ):
        
        num_frames = self._media.GetNumFrames()
        
        while True:
            
            time.sleep( 0.00001 ) # thread yield
            
            with self._render_lock:
                
                if not self._rendered_first_frame or self._next_render_index != ( self._render_to_index + 1 ) % num_frames:
                    
                    self._rendered_first_frame = True
                    
                    frame_index = self._next_render_index # keep this before the get call, as it increments in a clock arithmetic way afterwards
                    
                    try: numpy_image = self._renderer.read_frame()
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                        break
                        
                    finally: self._next_render_index = ( self._next_render_index + 1 ) % num_frames
                    
                    frame = GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = False )
                    
                    wx.wx.CallAfter( self.AddFrame, frame_index, frame )
                    
                else: break
                
            
        
    
    def AddFrame( self, index, frame ): self._frames[ index ] = frame
    
    def GetDuration( self, index ):
        
        if self._media.GetMime() == HC.IMAGE_GIF: return self._durations[ index ]
        else: return self._frame_duration
        
    
    def GetFrame( self, index ):
        
        frame = self._frames[ index ]
        
        self._last_index_asked_for = index
        
        self._MaintainBuffer()
        
        return frame
        
    
    def GetHash( self ): return self._media.GetHash()
    
    def GetKey( self ): return ( self._media.GetHash(), self._target_resolution )
    
    def GetNumFrames( self ): return self._media.GetNumFrames()
    
    def GetResolution( self ): return self._media.GetResolution()
    
    def GetSize( self ): return self._target_resolution
    
    def GetTotalDuration( self ):
        
        if self._media.GetMime() == HC.IMAGE_GIF: return sum( self._durations )
        else: return self._frame_duration * self.GetNumFrames()
        
    
    def GetZoom( self ): return self._zoom
    
    def HasFrame( self, index ): return index in self._frames
    
    def IsScaled( self ): return self._zoom != 1.0
    
    def SetFramePosition( self, index ):
        
        num_frames = self.GetNumFrames()
        
        if num_frames > self._num_frames_backwards + 1 + self._num_frames_forwards:
            
            new_buffer_start_index = max( 0, index - self._num_frames_backwards ) % num_frames
            
            new_buffer_end_index = ( index + self._num_frames_forwards ) % num_frames
            
            if index == self._last_index_asked_for: return
            elif index < self._last_index_asked_for:
                
                if index < self._buffer_start_index:
                    
                    self._buffer_start_index = new_buffer_start_index
                    
                    self._RENDERERSetFramePosition( self._buffer_start_index )
                    
                    self._buffer_end_index = new_buffer_end_index
                    
                    self._RENDERERSetRenderToPosition( self._buffer_end_index )
                    
                
            else: # index > self._last_index_asked_for
                
                currently_no_wraparound = self._buffer_start_index < self._buffer_end_index
                
                self._buffer_start_index = new_buffer_start_index
                
                if currently_no_wraparound:
                    
                    if index > self._buffer_end_index:
                        
                        self._RENDERERSetFramePosition( self._buffer_start_index )
                        
                    
                
                self._buffer_end_index = new_buffer_end_index
                
                self._RENDERERSetRenderToPosition( self._buffer_end_index )
                
            
        else:
            
            if self._buffer_end_index == -1:
                
                self._buffer_start_index = 0
                
                self._RENDERERSetFramePosition( 0 )
                
                self._buffer_end_index = num_frames - 1
                
                self._RENDERERSetRenderToPosition( self._buffer_end_index )
                
            
        
        self._MaintainBuffer()
        
    
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
            
        
    
    def GetWxBitmap( self ):
        
        ( width, height ) = self._size
        
        if self._format == wx.BitmapBufferFormat_RGB: return wx.BitmapFromBuffer( width, height, self._GetData() )
        else: return wx.BitmapFromBufferRGBA( width, height, self._GetData() )
        
    
    def GetWxImage( self ):
        
        ( width, height ) = self._size
        
        if self._format == wx.BitmapBufferFormat_RGB: return wx.ImageFromBuffer( width, height, self._GetData() )
        else:
            
            bitmap = wx.BitmapFromBufferRGBA( width, height, self._GetData() )
            
            image = wx.ImageFromBitmap( bitmap )
            
            wx.CallAfter( bitmap.Destroy )
            
            return image
            
        
    
    def GetEstimatedMemoryFootprint( self ): return len( self._data )
    
    def GetSize( self ): return self._size
    