from PIL import Image as PILImage

from psd_tools import PSDImage
from psd_tools.constants import Resource, ColorMode
from psd_tools.api.numpy_io import has_transparency, get_transparency_index
from psd_tools.api.pil_io import get_pil_mode, get_pil_channels, _create_image

from hydrus.core import HydrusExceptions
from hydrus.core.files.images import HydrusImageNormalisation

def PSDHasICCProfile( path: str ):
    
    psd = PSDImage.open( path )
    
    return Resource.ICC_PROFILE in psd.image_resources
    

def MergedPILImageFromPSD( path: str ) -> PILImage:
    
    psd = PSDImage.open( path )
    
    #pil_image = psd.topil( apply_icc = False )

    if not psd.has_preview():
        
        raise HydrusExceptions.DamagedOrUnusualFileException('PSD file has no embedded preview!')
        
    
    pil_image = convert_image_data_to_pil( psd )
    
    return pil_image
    

def GetPSDResolution( path: str ):
    
    psd = PSDImage.open( path )
    
    return ( psd.width, psd.height )
    

# modified from psd-tools source:
# https://github.com/psd-tools/psd-tools/blob/main/src/psd_tools/api/pil_io.py

def convert_image_data_to_pil( psd: PSDImage ):
    
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
        

    pil_image = post_process(image, alpha)
    
    if Resource.ICC_PROFILE in psd.image_resources:
        
        icc = psd.image_resources.get_data( Resource.ICC_PROFILE )
        
        pil_image.info[ 'icc_profile' ] = icc
        
    
    pil_image = HydrusImageNormalisation.DequantizePILImage( pil_image )
    
    return pil_image
    

def post_process(image, alpha):
    
    # Fix inverted CMYK.
    if image.mode == 'CMYK':
        
        from PIL import ImageChops
        image = ImageChops.invert(image)
        

    # In Pillow, alpha channel is only available in RGB or L.
    if alpha and image.mode in ('RGB', 'L'):
        
        image.putalpha(alpha)
        
    
    return image
    
