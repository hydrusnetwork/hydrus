import numpy.core.multiarray # important this comes before cv!
import cv2
from . import ClientImageHandling
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusImageHandling

if cv2.__version__.startswith( '2' ):
    
    CAP_PROP_FRAME_COUNT = cv2.cv.CV_CAP_PROP_FRAME_COUNT
    CAP_PROP_FPS = cv2.cv.CV_CAP_PROP_FPS
    CAP_PROP_FRAME_WIDTH = cv2.cv.CV_CAP_PROP_FRAME_WIDTH
    CAP_PROP_FRAME_HEIGHT = cv2.cv.CV_CAP_PROP_FRAME_HEIGHT
    CAP_PROP_CONVERT_RGB = cv2.cv.CV_CAP_PROP_CONVERT_RGB
    CAP_PROP_POS_FRAMES = cv2.cv.CV_CAP_PROP_POS_FRAMES
    
else:
    
    CAP_PROP_FRAME_COUNT = cv2.CAP_PROP_FRAME_COUNT
    CAP_PROP_FPS = cv2.CAP_PROP_FPS
    CAP_PROP_FRAME_WIDTH = cv2.CAP_PROP_FRAME_WIDTH
    CAP_PROP_FRAME_HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT
    CAP_PROP_CONVERT_RGB = cv2.CAP_PROP_CONVERT_RGB
    CAP_PROP_POS_FRAMES = cv2.CAP_PROP_POS_FRAMES
    
def GetCVVideoProperties( path ):
    
    capture = cv2.VideoCapture( path )
    
    num_frames = int( capture.get( CAP_PROP_FRAME_COUNT ) )
    
    fps = capture.get( CAP_PROP_FPS )
    
    length_in_seconds = num_frames / fps
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    duration = length_in_ms
    
    width = int( capture.get( CAP_PROP_FRAME_WIDTH ) )
    
    height = int( capture.get( CAP_PROP_FRAME_HEIGHT ) )
    
    return ( ( width, height ), duration, num_frames )
    
# the cv code was initially written by @fluffy_cub
class GIFRenderer( object ):
    
    def __init__( self, path, num_frames, target_resolution ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading GIF: ' + path )
            
        
        self._path = path
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        
        new_options = HG.client_controller.new_options
        
        if new_options.GetBoolean( 'disable_cv_for_gifs' ) or cv2.__version__.startswith( '2' ):
            
            self._InitialisePIL()
            
        else:
            
            self._InitialiseCV()
            
        
    
    def _GetCurrentFrame( self ):
        
        if self._cv_mode:
            
            ( retval, numpy_image ) = self._cv_video.read()
            
            if not retval:
                
                self._next_render_index = ( self._next_render_index + 1 ) % self._num_frames
                
                raise HydrusExceptions.CantRenderWithCVException( 'CV could not render frame ' + str( self._next_render_index - 1 ) + '.' )
                
            
        else:
            
            current_frame = HydrusImageHandling.Dequantize( self._pil_image )
            
            if current_frame.mode == 'RGBA':
                
                if self._pil_canvas is None:
                    
                    self._pil_canvas = current_frame
                    
                else:
                    
                    self._pil_canvas.paste( current_frame, None, current_frame ) # use the rgba image as its own mask
                    
                
            elif current_frame.mode == 'RGB':
                
                self._pil_canvas = current_frame
                
            
            numpy_image = HydrusImageHandling.GenerateNumPyImageFromPILImage( self._pil_canvas )
            
        
        self._next_render_index = ( self._next_render_index + 1 ) % self._num_frames
        
        if self._next_render_index == 0:
            
            self._RewindGIF()
            
        else:
            
            if not self._cv_mode:
                
                self._pil_image.seek( self._next_render_index )
                
                if self._pil_global_palette is not None and self._pil_image.palette == self._pil_global_palette: # for some reason, when pil falls back from local palette to global palette, a bunch of important variables reset!
                    
                    self._pil_image.palette.dirty = self._pil_dirty
                    self._pil_image.palette.mode = self._pil_mode
                    self._pil_image.palette.rawmode = self._pil_rawmode
                    
                
            
        
        return numpy_image
        
    
    def _InitialiseCV( self ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading GIF with OpenCV' )
            
        
        self._cv_mode = True
        
        self._cv_video = cv2.VideoCapture( self._path )
        
        self._cv_video.set( CAP_PROP_CONVERT_RGB, True )
        
        self._next_render_index = 0
        self._last_frame = None
        
    
    def _InitialisePIL( self ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading GIF with PIL' )
            
        
        self._cv_mode = False
        
        self._pil_image = HydrusImageHandling.GeneratePILImage( self._path )
        
        self._pil_canvas = None
        
        self._pil_global_palette = self._pil_image.palette
        
        if self._pil_global_palette is not None and False:
            
            self._pil_dirty = self._pil_image.palette.dirty
            self._pil_mode = self._pil_image.palette.mode
            self._pil_rawmode = self._pil_image.palette.rawmode
            
        
        self._next_render_index = 0
        self._last_frame = None
        
        # believe it or not, doing this actually fixed a couple of gifs!
        self._pil_image.seek( 1 )
        self._pil_image.seek( 0 )
        
    
    def _RenderCurrentFrame( self ):
        
        if self._cv_mode:
            
            try:
                
                numpy_image = self._GetCurrentFrame()
                
                numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, self._target_resolution )
                
                numpy_image = cv2.cvtColor( numpy_image, cv2.COLOR_BGR2RGB )
                
            except HydrusExceptions.CantRenderWithCVException:
                
                if self._last_frame is None:
                    
                    if HG.media_load_report_mode:
                        
                        HydrusData.ShowText( 'OpenCV Failed to render a frame' )
                        
                    
                    self._InitialisePIL()
                    
                    numpy_image = self._RenderCurrentFrame()
                    
                else:
                    
                    numpy_image = self._last_frame
                    
                
            
        else:
            
            numpy_image = self._GetCurrentFrame()
            
            numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, self._target_resolution )
            
        
        self._last_frame = numpy_image
        
        return numpy_image
        
    
    def _RewindGIF( self ):
        
        if self._cv_mode:
            
            self._cv_video.release()
            self._cv_video.open( self._path )
            
            #self._cv_video.set( CAP_PROP_POS_FRAMES, 0.0 )
            
        else:
            
            self._pil_image.seek( 0 )
            
        
        self._next_render_index = 0
        
    
    def read_frame( self ):
        
        return self._RenderCurrentFrame()
        
    
    def set_position( self, index ):
        
        if index == self._next_render_index: return
        elif index < self._next_render_index: self._RewindGIF()
        
        while self._next_render_index < index: self._GetCurrentFrame()
        
        #self._cv_video.set( CV_CAP_PROP_POS_FRAMES, index )
        
    
    def Stop( self ):
        
        pass
        
    
