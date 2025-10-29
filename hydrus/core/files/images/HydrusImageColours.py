import numpy

from PIL import Image as PILImage

from hydrus.core import HydrusGlobals as HG

def GetNumPyAlphaChannel( numpy_image: numpy.ndarray ) -> numpy.ndarray:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        raise Exception( 'Does not have an alpha channel!' )
        
    
    channel_number = GetNumPyAlphaChannelNumber( numpy_image )
    
    alpha_channel = numpy_image[:,:,channel_number].copy()
    
    return alpha_channel
    

def GetNumPyAlphaChannelNumber( numpy_image: numpy.ndarray ):
    
    shape = numpy_image.shape
    
    if len( shape ) <= 2:
        
        raise Exception( 'Greyscale image, does not have an alpha channel!' )
        
    
    # 1 for LA, 3 for RGBA
    return shape[2] - 1
    

def NumPyImageHasAllCellsTheSame( numpy_image: numpy.ndarray, value: int ):
    
    # I looked around for ways to do this iteratively at the c++ level but didn't have huge luck.
    # unless some magic is going on, the '==' actually creates the bool array
    # its ok for now!
    return numpy.all( numpy_image == value )
    
    # old way, which makes a third array:
    # alpha_channel == numpy.full( ( shape[0], shape[1] ), 255, dtype = 'uint8' ) ).all()
    

def NumPyImageHasAlphaChannel( numpy_image: numpy.ndarray ) -> bool:
    
    # note this does not test how useful the channel is, just if it exists
    
    shape = numpy_image.shape
    
    if len( shape ) <= 2:
        
        return False
        
    
    # 2 for LA? think this works
    return shape[2] in ( 2, 4 )
    

def NumPyImageHasNonFullyBlackOrWhiteAlphaChannel( numpy_image: numpy.ndarray ) -> bool:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        return False
        
    
    alpha_channel = GetNumPyAlphaChannel( numpy_image )
    
    if NumPyImageHasAllCellsTheSame( alpha_channel, 0 ): # totally transparent
        
        return False
        
    
    if NumPyImageHasAllCellsTheSame( alpha_channel, 255 ): # totally opaque
        
        return False
        
    
    return True
    

def NumPyImageHasHumanPerceptibleAlphaChannel( numpy_image: numpy.ndarray ) -> bool:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        return False
        
    
    # RGBA or LA image
    
    alpha_channel = GetNumPyAlphaChannel( numpy_image )
    
    # ok I used to say "If all are 255 or 0, then it is useless"
    # this is ok, but there are _many_ images that are like "560k pixels opaque, 442k at 254, 20k at 253, 243 at 252, and 22 at 251"
    # apparently an anti-aliasing algorithm can do this. I suspect dodgy brushes may also do it
    # so, we are reworking this test so that something like a circumference of interesting alpha is the minimum acceptable state. anything less than that is discarded
    
    width = numpy_image.shape[1]
    height = numpy_image.shape[0]
    
    circumference = 2 * ( width + height )
    weight = max( int( ( width * height ) / 200 ), 1 )
    
    num_interesting_alpha_pixels_needed = min( circumference, weight )
    
    # do not combine these tests, they mean something different when separate!
    if numpy.count_nonzero( alpha_channel < 251 ) < num_interesting_alpha_pixels_needed:
        
        # everything is clustered in opaque-land, this alpha is useless
        return False
        
    
    if numpy.count_nonzero( alpha_channel > 4 ) < num_interesting_alpha_pixels_needed:
        
        # everything is clustered in transparency-land, this alpha is useless
        return False
        
    
    # ok this alpha has something interesting going on
    return True
    

HAS_TRANSPARENCY_STRICTNESS_CHANNEL_PRESENCE = 0
HAS_TRANSPARENCY_STRICTNESS_NOT_BLACK_OR_WHITE = 1
HAS_TRANSPARENCY_STRICTNESS_HUMAN = 2

has_transparency_strictness_string_lookup = {
    HAS_TRANSPARENCY_STRICTNESS_CHANNEL_PRESENCE : 'it has a transparency channel',
    HAS_TRANSPARENCY_STRICTNESS_NOT_BLACK_OR_WHITE : 'it has a transparency channel that is not completely transparent or opaque',
    HAS_TRANSPARENCY_STRICTNESS_HUMAN : 'it has a transparency channel that a human might recognise'
}

CURRENT_HAS_TRANSPARENCY_STRICTNESS_LEVEL = HAS_TRANSPARENCY_STRICTNESS_HUMAN

def NumPyImageHasUsefulAlphaChannel( numpy_image: numpy.ndarray ) -> bool:
    
    global CURRENT_HAS_TRANSPARENCY_STRICTNESS_LEVEL
    
    if CURRENT_HAS_TRANSPARENCY_STRICTNESS_LEVEL == HAS_TRANSPARENCY_STRICTNESS_HUMAN:
        
        return NumPyImageHasHumanPerceptibleAlphaChannel( numpy_image )
        
    elif CURRENT_HAS_TRANSPARENCY_STRICTNESS_LEVEL == HAS_TRANSPARENCY_STRICTNESS_NOT_BLACK_OR_WHITE:
        
        return NumPyImageHasNonFullyBlackOrWhiteAlphaChannel( numpy_image )
        
    elif CURRENT_HAS_TRANSPARENCY_STRICTNESS_LEVEL == HAS_TRANSPARENCY_STRICTNESS_CHANNEL_PRESENCE:
        
        return NumPyImageHasAlphaChannel( numpy_image )
        
    else:
        
        raise NotImplementedError( 'Unknown transparency strictness!' )
        
    

# note that this is not the same as 'not useful()'. we need to test for the alpha explictly, otherwise an RGB image passing through here returns false
def NumPyImageHasUselessAlphaChannel( numpy_image: numpy.ndarray ) -> bool:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        return False
        
    
    return not NumPyImageHasUsefulAlphaChannel( numpy_image )
    

def PILImageHasTransparency( pil_image: PILImage.Image ) -> bool:
    
    return pil_image.mode in ( 'LA', 'RGBA' ) or ( pil_image.mode == 'P' and 'transparency' in pil_image.info )
    

def SetHasTransparencyStrictnessLevel( value: bool ):
    
    global CURRENT_HAS_TRANSPARENCY_STRICTNESS_LEVEL
    
    if value != CURRENT_HAS_TRANSPARENCY_STRICTNESS_LEVEL:
        
        CURRENT_HAS_TRANSPARENCY_STRICTNESS_LEVEL = value
        
        HG.controller.pub( 'clear_image_cache' )
        HG.controller.pub( 'clear_image_tile_cache' )
        
    
