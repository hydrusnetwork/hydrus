import numpy

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.files.images import HydrusImageNormalisation

class AnimationRendererPIL( object ):
    
    def __init__( self, path, num_frames, target_resolution ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading animation: ' + path )
            
        
        self._path = path
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        self._cannot_seek_to_or_beyond_this_index = None
        self._frames_we_could_not_render = set()
        
        self._current_render_index = 0
        self._last_valid_numpy_frame = None
        
        self._Initialise()
        
    
    def _GetRecoveryFrame( self ) -> numpy.ndarray:
        
        if self._last_valid_numpy_frame is None:
            
            numpy_image = numpy.zeros( ( self._target_resolution[1], self._target_resolution[0], 4 ), dtype = 'uint8' )
            numpy_image[:,:,3] = 255 # numpy is great!
            
        else:
            
            numpy_image = self._last_valid_numpy_frame
            
        
        return numpy_image
        
    
    def _Initialise( self ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading animation with PIL' )
            
        
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
            
            raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not initialise animation!' ) from e 
            
        '''
        
    
    def _MoveRendererOnOneFrame( self ):
        
        self._current_render_index = ( self._current_render_index + 1 ) % self._num_frames
        
        we_are_in_the_dangerzone = self._cannot_seek_to_or_beyond_this_index is not None and self._current_render_index >= self._cannot_seek_to_or_beyond_this_index
        
        if self._current_render_index == 0 or we_are_in_the_dangerzone:
            
            self._RewindAnimation( reinitialise = True )
            
        else:
            
            try:
                
                self._pil_image.seek( self._current_render_index )
                
                size = self._pil_image.size
                
                # this out of the blue: <PIL.GifImagePlugin.GifImageFile image mode=RGBA size=85171x53524 at 0x1BF0386C460>
                # 8GB memory 20 second fail render
                if size[0] > 16384 or size[1] > 16384:
                    
                    raise HydrusExceptions.DamagedOrUnusualFileException( 'Crazy animation frame went bananas!' )
                    
                
            except Exception as e:
                
                # this can raise OSError in some 'trancated file' circumstances
                # trying to render beyond with PIL is rife with trouble, so we won't try
                if self._cannot_seek_to_or_beyond_this_index is None:
                    
                    self._cannot_seek_to_or_beyond_this_index = self._current_render_index
                    
                else:
                    
                    self._cannot_seek_to_or_beyond_this_index = min( self._cannot_seek_to_or_beyond_this_index, self._current_render_index )
                    
                
                self._RewindAnimation( reinitialise = True )
                
            
        
    
    def _RenderCurrentFrameAndResizeIt( self ) -> numpy.ndarray:
        
        we_are_in_the_dangerzone = self._cannot_seek_to_or_beyond_this_index is not None and self._current_render_index >= self._cannot_seek_to_or_beyond_this_index
        
        if we_are_in_the_dangerzone:
            
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
                
            except Exception as e:
                
                # PIL can produce an IOError, which is an OSError(!!!), on a truncated file, lfg
                # so let's just bail out in that case mate
                
                self._frames_we_could_not_render.add( self._current_render_index )
                
                time_to_error = HydrusTime.GetNowFloat() - time_started
                
                if time_to_error > 2.0:
                    
                    # this is a crazy file that, with its broken frame, needs to re-render the whole thing or something
                    # don't push any further
                    
                    self._cannot_seek_to_or_beyond_this_index = min( self._frames_we_could_not_render )
                    
                
                numpy_image = self._GetRecoveryFrame()
                
            
        
        try:
            
            resized_numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, self._target_resolution )
            
        except Exception as e:
            
            self._frames_we_could_not_render.add( self._current_render_index )
            self._cannot_seek_to_or_beyond_this_index = min( self._frames_we_could_not_render )
            
            numpy_image = self._GetRecoveryFrame()
            
            resized_numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, self._target_resolution )
            
        
        self._last_valid_numpy_frame = numpy_image
        
        return resized_numpy_image
        
    
    def _RewindAnimation( self, reinitialise = False ):
        
        self._pil_image.seek( 0 )
        
        self._current_render_index = 0
        
        if reinitialise:
            
            self._Initialise()
            
        
    
    def close( self ):
        
        pass
        
    
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
            
            self._RewindAnimation()
            
        
        while self._current_render_index < index:
            
            self._MoveRendererOnOneFrame()
            
        
    
    def Stop( self ):
        
        pass
        
    
