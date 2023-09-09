import struct
import typing

from PIL import Image as PILImage

from hydrus.core import HydrusExceptions, HydrusImageHandling

try:
    
    from psd_tools import PSDImage
    from psd_tools.constants import Resource, ColorMode, Resource
    from psd_tools.api.numpy_io import has_transparency, get_transparency_index
    from psd_tools.api.pil_io import get_pil_mode, get_pil_channels, _create_image
    
    PSD_TOOLS_OK = True
    
except:
    
    PSD_TOOLS_OK = False
    

def PSDHasICCProfile( path: str ):
    
    if not PSD_TOOLS_OK:
        
        raise HydrusExceptions.UnsupportedFileException( 'psd_tools unavailable' )
        
    
    psd = PSDImage.open( path )
    
    return Resource.ICC_PROFILE in psd.image_resources
    

def MergedPILImageFromPSD( path: str ) -> PILImage:
    
    if not PSD_TOOLS_OK:
        
        raise HydrusExceptions.UnsupportedFileException( 'psd_tools unavailable' )
        
    
    psd = PSDImage.open( path )
    
    #pil_image = psd.topil( apply_icc = False )

    if psd.has_preview():

        pil_image = convert_image_data_to_pil(psd)

    else:

        raise HydrusExceptions.UnsupportedFileException('PSD file has no embedded preview!')
        
    
    if Resource.ICC_PROFILE in psd.image_resources:
        
        icc = psd.image_resources.get_data( Resource.ICC_PROFILE )
        
        pil_image.info[ 'icc_profile' ] = icc
        
    
    return pil_image
    

def GenerateThumbnailBytesFromPSDPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
    
    pil_image = MergedPILImageFromPSD( path )
    
    if clip_rect is not None:
        
        pil_image = HydrusImageHandling.ClipPILImage( pil_image, clip_rect )
        
    
    thumbnail_pil_image = pil_image.resize( target_resolution, PILImage.LANCZOS )
    
    thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesPIL( thumbnail_pil_image )
    
    return thumbnail_bytes
    

def GetPSDResolution( path: str ):
    
    if not PSD_TOOLS_OK:

        raise HydrusExceptions.UnsupportedFileException( 'psd_tools unavailable' )
    
    psd = PSDImage.open( path )
            
    return ( psd.width, psd.height )
    

def GetPSDResolutionFallback( path: str ):
    
    with open( path, 'rb' ) as f:
        
        f.seek( 14 )
        
        height_bytes = f.read( 4 )
        width_bytes = f.read( 4 )
        
    
    height: int = struct.unpack( '>L', height_bytes )[0]
    width: int = struct.unpack( '>L', width_bytes )[0]
    
    return ( width, height )
    

# modified from psd-tools source:
# https://github.com/psd-tools/psd-tools/blob/main/src/psd_tools/api/pil_io.py

def convert_image_data_to_pil(psd: PSDImage):
    alpha = None

    channel_data = psd._record.image_data.get_data(psd._record.header)
    size = (psd.width, psd.height)
    
    channels = [_create_image(size, c, psd.depth) for c in channel_data]

    # has_transparency not quite correct
    # see https://github.com/psd-tools/psd-tools/issues/369
    # and https://github.com/psd-tools/psd-tools/pull/370
    no_alpha = psd._record.layer_and_mask_information.layer_info is not None and psd._record.layer_and_mask_information.layer_info.layer_count > 0

    if has_transparency(psd) and not no_alpha:
        alpha = channels[get_transparency_index(psd)]

    if psd.color_mode == ColorMode.INDEXED:
        image = channels[0]
        image.putpalette(psd._record.color_mode_data.interleave())
    elif psd.color_mode == ColorMode.MULTICHANNEL:
        image = channels[0]  # Multi-channel mode is a collection of alpha.
    else:
        mode = get_pil_mode(psd.color_mode)
        image = PILImage.merge(mode, channels[:get_pil_channels(mode)])

    if not image:
        return None

    return post_process(image, alpha)


def post_process(image, alpha):
    # Fix inverted CMYK.
    if image.mode == 'CMYK':
        from PIL import ImageChops
        image = ImageChops.invert(image)

    # In Pillow, alpha channel is only available in RGB or L.
    if alpha and image.mode in ('RGB', 'L'):
        image.putalpha(alpha)
    return image
