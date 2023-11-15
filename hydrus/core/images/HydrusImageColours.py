import numpy

from PIL import Image as PILImage

def GetNumPyAlphaChannel( numpy_image: numpy.array ) -> numpy.array:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        raise Exception( 'Does not have an alpha channel!' )
        
    
    channel_number = GetNumPyAlphaChannelNumber( numpy_image )
    
    alpha_channel = numpy_image[:,:,channel_number].copy()
    
    return alpha_channel
    

def GetNumPyAlphaChannelNumber( numpy_image: numpy.array ):
    
    shape = numpy_image.shape
    
    if len( shape ) <= 2:
        
        raise Exception( 'Greyscale image, does not have an alpha channel!' )
        
    
    # 1 for LA, 3 for RGBA
    return shape[2] - 1
    

def NumPyImageHasAllCellsTheSame( numpy_image: numpy.array, value: int ):
    
    # I looked around for ways to do this iteratively at the c++ level but didn't have huge luck.
    # unless some magic is going on, the '==' actually creates the bool array
    # its ok for now!
    return numpy.all( numpy_image == value )
    
    # old way, which makes a third array:
    # alpha_channel == numpy.full( ( shape[0], shape[1] ), 255, dtype = 'uint8' ) ).all()
    

def NumPyImageHasUsefulAlphaChannel( numpy_image: numpy.array ) -> bool:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        return False
        
    
    # RGBA or LA image
    
    alpha_channel = GetNumPyAlphaChannel( numpy_image )
    
    if NumPyImageHasAllCellsTheSame( alpha_channel, 255 ): # all opaque
        
        return False
        
    
    if NumPyImageHasAllCellsTheSame( alpha_channel, 0 ): # all transparent
        
        underlying_image_is_black = NumPyImageHasAllCellsTheSame( numpy_image, 0 )
        
        return underlying_image_is_black
        
    
    return True
    

def NumPyImageHasUselessAlphaChannel( numpy_image: numpy.array ) -> bool:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        return False
        
    
    # RGBA or LA image
    
    alpha_channel = GetNumPyAlphaChannel( numpy_image )
    
    if NumPyImageHasAllCellsTheSame( alpha_channel, 255 ): # all opaque
        
        return True
        
    
    if NumPyImageHasAllCellsTheSame( alpha_channel, 0 ): # all transparent
        
        underlying_image_is_black = NumPyImageHasAllCellsTheSame( numpy_image, 0 )
        
        return not underlying_image_is_black
        
    
    return False
    

def NumPyImageHasOpaqueAlphaChannel( numpy_image: numpy.array ) -> bool:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        return False
        
    
    # RGBA or LA image
    # opaque means 255
    
    alpha_channel = GetNumPyAlphaChannel( numpy_image )
    
    return NumPyImageHasAllCellsTheSame( alpha_channel, 255 )
    

def NumPyImageHasAlphaChannel( numpy_image: numpy.array ) -> bool:
    
    # note this does not test how useful the channel is, just if it exists
    
    shape = numpy_image.shape
    
    if len( shape ) <= 2:
        
        return False
        
    
    # 2 for LA? think this works
    return shape[2] in ( 2, 4 )
    

def NumPyImageHasTransparentAlphaChannel( numpy_image: numpy.array ) -> bool:
    
    if not NumPyImageHasAlphaChannel( numpy_image ):
        
        return False
        
    
    # RGBA or LA image
    # transparent means 0
    
    alpha_channel = GetNumPyAlphaChannel( numpy_image )
    
    return NumPyImageHasAllCellsTheSame( alpha_channel, 0 )
    

def PILImageHasTransparency( pil_image: PILImage.Image ) -> bool:
    
    return pil_image.mode in ( 'LA', 'RGBA' ) or ( pil_image.mode == 'P' and 'transparency' in pil_image.info )
    
