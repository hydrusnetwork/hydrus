import typing
from PIL import Image as PILImage

from hydrus.core import HydrusExceptions

def RawOpenPILImage( path: str | typing.BinaryIO, human_file_description = None ) -> PILImage.Image:
    
    try:
        
        pil_image = PILImage.open( path )
        
        if pil_image is None:
            
            raise Exception( 'PIL returned None.' )
            
        
    except Exception as e:
        
        
        if human_file_description is not None:
            
            message = f'Could not load the image at "{human_file_description}"--it was likely malformed!'
            
        elif isinstance( path, str ):
            
            message = f'Could not load the image at "{path}"--it was likely malformed!'
            
        else:
            
            message = f'Could not load the image, which had no path (so was probably from inside another file?)--it was likely malformed!'
            
        
        raise HydrusExceptions.DamagedOrUnusualFileException( message ) from e
        
    
    return pil_image
    
