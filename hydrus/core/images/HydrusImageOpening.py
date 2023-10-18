import typing
from PIL import Image as PILImage

from hydrus.core import HydrusExceptions

def RawOpenPILImage( path: typing.Union[ str, typing.BinaryIO ] ) -> PILImage.Image:
    
    try:
        
        pil_image = PILImage.open( path )
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not load the image--it was likely malformed!' )
        
    
    return pil_image
    
