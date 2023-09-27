import struct
import typing

from PIL import Image as PILImage

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusImageHandling

try:
    
    from hydrus.core import HydrusPSDTools

    PSD_TOOLS_OK = True
    
except:
    
    PSD_TOOLS_OK = False
    

def PSDHasICCProfile( path: str ):
    
    if not PSD_TOOLS_OK:
        
        raise HydrusExceptions.UnsupportedFileException( 'psd_tools unavailable' )
        
    
    return HydrusPSDTools.PSDHasICCProfile( path )
    

def MergedPILImageFromPSD( path: str ) -> PILImage:
    
    if not PSD_TOOLS_OK:
        
        raise HydrusExceptions.UnsupportedFileException( 'psd_tools unavailable' )
        
    
    return HydrusPSDTools.MergedPILImageFromPSD( path )
    

def GenerateThumbnailNumPyFromPSDPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
    
    pil_image = MergedPILImageFromPSD( path )
    
    if clip_rect is not None:
        
        pil_image = HydrusImageHandling.ClipPILImage( pil_image, clip_rect )
        
    
    thumbnail_pil_image = pil_image.resize( target_resolution, PILImage.LANCZOS )
    
    numpy_image = HydrusImageHandling.GenerateNumPyImageFromPILImage(thumbnail_pil_image)
    
    numpy_image = HydrusImageHandling.DequantizeNumPyImage( numpy_image )
    
    return numpy_image
    

def GetPSDResolution( path: str ):
    
    if not PSD_TOOLS_OK:
        
        raise HydrusExceptions.UnsupportedFileException( 'psd_tools unavailable' )
        
    
    return HydrusPSDTools.GetPSDResolution( path )
    

def GetPSDResolutionFallback( path: str ):
    
    with open( path, 'rb' ) as f:
        
        f.seek( 14 )
        
        height_bytes = f.read( 4 )
        width_bytes = f.read( 4 )
        
    
    height: int = struct.unpack( '>L', height_bytes )[0]
    width: int = struct.unpack( '>L', width_bytes )[0]
    
    return ( width, height )
    
