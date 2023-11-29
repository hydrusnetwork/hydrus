import PIL.Image
import cv2
import numpy

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime
from hydrus.core.images import HydrusImageHandling
from hydrus.core.images import HydrusImageNormalisation

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
    
    if fps is None or fps == 0:
        
        fps = 1
        
    
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
        self._cannot_seek_to_or_beyond_this_index = None
        self._frames_we_could_not_render = set()
        
        self._current_render_index = 0
        self._last_valid_numpy_frame = None
        
        self._Initialise()
        
    
    def _GetRecoveryFrame( self ) -> numpy.array:
        
        if self._last_valid_numpy_frame is None:
            
            numpy_image = numpy.zeros( ( self._target_resolution[1], self._target_resolution[0], 4 ), dtype = 'uint8' )
            numpy_image[:,:,3] = 255 # numpy is great!
            
        else:
            
            numpy_image = self._last_valid_numpy_frame
            
        
        return numpy_image
        
    
    def _Initialise( self ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading GIF with PIL' )
            
        
        # dequantize = False since we'll be doing that later for each frame in turn
        # if we do it now, it collapses down to a one frame object
        self._pil_image = HydrusImageHandling.GeneratePILImage( self._path, dequantize = False )
        
        self._pil_global_palette = self._pil_image.palette
        
        # years-old weirdo fix, taking it out 2023-11
        '''
        # believe it or not, doing this actually fixed a couple of gifs!
        try:
            
            self._pil_image.seek( 1 )
            self._pil_image.seek( 0 )
            
        except Exception as e:
            
            raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not initialise GIF!' ) from e 
            
        '''
        
    
    def _MoveRendererOnOneFrame( self ):
        
        self._current_render_index = ( self._current_render_index + 1 ) % self._num_frames
        
        we_are_in_the_dangerzone = self._cannot_seek_to_or_beyond_this_index is not None and self._current_render_index >= self._cannot_seek_to_or_beyond_this_index
        
        if self._current_render_index == 0 or we_are_in_the_dangerzone:
            
            self._RewindGIF( reinitialise = True )
            
        else:
            
            try:
                
                self._pil_image.seek( self._current_render_index )
                
                size = self._pil_image.size
                
                # this out of the blue: <PIL.GifImagePlugin.GifImageFile image mode=RGBA size=85171x53524 at 0x1BF0386C460>
                # 8GB memory 20 second fail render
                if size[0] > 16384 or size[1] > 16384:
                    
                    raise HydrusExceptions.DamagedOrUnusualFileException( 'Crazy GIF frame went bananas!' )
                    
                
            except:
                
                # this can raise OSError in some 'trancated file' circumstances
                # trying to render beyond with PIL is rife with trouble, so we won't try
                if self._cannot_seek_to_or_beyond_this_index is None:
                    
                    self._cannot_seek_to_or_beyond_this_index = self._current_render_index
                    
                else:
                    
                    self._cannot_seek_to_or_beyond_this_index = min( self._cannot_seek_to_or_beyond_this_index, self._current_render_index )
                    
                
                self._RewindGIF( reinitialise = True )
                
            
        
    
    def _RenderCurrentFrameAndResizeIt( self ) -> numpy.array:
        
        if self._cannot_seek_to_or_beyond_this_index is not None and self._current_render_index >= self._cannot_seek_to_or_beyond_this_index:
            
            numpy_image = self._GetRecoveryFrame()
            
        elif self._current_render_index in self._frames_we_could_not_render:
            
            numpy_image = self._GetRecoveryFrame()
            
        else:
            
            time_started = HydrusTime.GetNowFloat()
            
            try:
                
                current_frame = HydrusImageNormalisation.DequantizePILImage( self._pil_image )
                
                # don't have to worry about pasting alpha-having transparent frames over the previous frame--PIL seems to handle this these days!
                self._pil_canvas = current_frame
                
                numpy_image = HydrusImageHandling.GenerateNumPyImageFromPILImage( self._pil_canvas, strip_useless_alpha = False )
                
            except:
                
                # PIL can produce an IOError, which is an OSError(!!!), on a truncated file, lfg
                # so let's just bail out in that case mate
                
                self._frames_we_could_not_render.add( self._current_render_index )
                
                time_to_error = HydrusTime.GetNowFloat() - time_started
                
                if time_to_error > 2.0:
                    
                    # this is a crazy file that, with its broken frame, needs to re-render the whole thing or something
                    # don't push any further
                    
                    self._cannot_seek_to_or_beyond_this_index = min( self._frames_we_could_not_render )
                    
                
                numpy_image = self._GetRecoveryFrame()
                
            
        
        self._last_valid_numpy_frame = numpy_image
        
        numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, self._target_resolution )
        
        return numpy_image
        
    
    def _RewindGIF( self, reinitialise = False ):
        
        self._pil_image.seek( 0 )
        
        self._current_render_index = 0
        
        if reinitialise:
            
            self._Initialise()
            
        
    
    def read_frame( self ):
        
        numpy_image = self._RenderCurrentFrameAndResizeIt()
        
        self._MoveRendererOnOneFrame()
        
        return numpy_image
        
    
    def set_position( self, index ):
        
        if self._cannot_seek_to_or_beyond_this_index is not None and index >= self._cannot_seek_to_or_beyond_this_index:
            
            return
            
        
        if index == self._current_render_index:
            
            return
            
        elif index < self._current_render_index:
            
            self._RewindGIF()
            
        
        while self._current_render_index < index:
            
            self._MoveRendererOnOneFrame()
            
        
        #self._cv_video.set( CV_CAP_PROP_POS_FRAMES, index )
        
    
    def Stop( self ):
        
        pass
        
    

# the cv code was initially written by @fluffy_cub
# hydev is splitting this off into its own clean thing now, just for posterity
# PIL gif rendering has improved by leaps and bounds in recent years, and we have good alpha rendering now. CV is now the sub-par
class GIFRendererCV( object ):
    
    def __init__( self, path, num_frames, target_resolution ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading GIF: ' + path )
            
        
        self._path = path
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        
        self._InitialiseCV()
        
    
    def _GetCurrentFrameAndMoveOn( self ):
        
        ( retval, numpy_image ) = self._cv_video.read()
        
        if not retval:
            
            self._next_render_index = ( self._next_render_index + 1 ) % self._num_frames
            
            raise HydrusExceptions.CantRenderWithCVException( 'CV could not render frame ' + str( self._next_render_index - 1 ) + '.' )
            
        
        self._next_render_index = ( self._next_render_index + 1 ) % self._num_frames
        
        if self._next_render_index == 0:
            
            self._RewindGIF()
            
        
        return numpy_image
        
    
    def _InitialiseCV( self ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading GIF with OpenCV' )
            
        
        self._cv_video = cv2.VideoCapture( self._path )
        
        self._cv_video.set( CAP_PROP_CONVERT_RGB, 1.0 ) # True cast to double
        
        self._next_render_index = 0
        
    
    def _RenderCurrentFrameAndResizeIt( self ):
        
        numpy_image = self._GetCurrentFrameAndMoveOn()
        
        numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, self._target_resolution )
        
        numpy_image = cv2.cvtColor( numpy_image, cv2.COLOR_BGR2RGB )
        
        return numpy_image
        
    
    def _RewindGIF( self ):
        
        self._cv_video.release()
        self._cv_video.open( self._path )
        
        #self._cv_video.set( CAP_PROP_POS_FRAMES, 0.0 )
        
        self._next_render_index = 0
        
    
    def read_frame( self ):
        
        return self._RenderCurrentFrameAndResizeIt()
        
    
    def set_position( self, index ):
        
        if index == self._next_render_index: return
        elif index < self._next_render_index: self._RewindGIF()
        
        while self._next_render_index < index: self._GetCurrentFrameAndMoveOn()
        
        #self._cv_video.set( CV_CAP_PROP_POS_FRAMES, index )
        
    
    def Stop( self ):
        
        pass
        
    
