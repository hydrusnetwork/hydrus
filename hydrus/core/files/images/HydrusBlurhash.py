import numpy
import cv2

from hydrus.external import blurhash as external_blurhash

from hydrus.core.files.images import HydrusImageHandling

def GetBlurhashFromNumPy( numpy_image: numpy.array ) -> str:
    
    media_height = numpy_image.shape[0]
    media_width = numpy_image.shape[1]
    
    if media_width == 0 or media_height == 0:
        
        return ''
        
    
    ratio = media_width / media_height
    
    if ratio > 4 / 3:
        
        components_x = 5
        components_y = 3
        
    elif ratio < 3 / 4:
        
        components_x = 3
        components_y = 5
        
    else:
        
        components_x = 4
        components_y = 4
        
    
    CUTOFF_DIMENSION = 100
    
    if numpy_image.shape[0] > CUTOFF_DIMENSION or numpy_image.shape[1] > CUTOFF_DIMENSION:
        
        numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, (CUTOFF_DIMENSION, CUTOFF_DIMENSION), forced_interpolation = cv2.INTER_LINEAR )
        
    
    return external_blurhash.blurhash_encode( numpy_image, components_x, components_y )
    

def GetNumpyFromBlurhash( blurhash, width, height ) -> numpy.array:
    
    # this thing is super slow, they recommend even in the documentation to render small and scale up
    if width > 32 or height > 32:
        
        numpy_image = numpy.array( external_blurhash.blurhash_decode( blurhash, 32, 32 ), dtype = 'uint8' )
        
        numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, ( width, height ) )
        
    else:
        
        numpy_image = numpy.array( external_blurhash.blurhash_decode( blurhash, width, height ), dtype = 'uint8' )
        
    
    return numpy_image
    
