from psd_tools import PSDImage
from psd_tools.constants import ChannelID, Tag, ColorMode, Resource

from PIL import Image as PILImage

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusImageHandling


def MergedPILImageFromPSD(path: str) -> PILImage:
    
    psd = PSDImage.open(path)

    return psd.topil()


def GenerateThumbnailBytesFromPSDPath(path: str, target_resolution: tuple[int, int], clip_rect = None) -> bytes:
    
    psd = PSDImage.open(path)

    pil_image = psd.topil()

    no_alpha = psd._record.layer_and_mask_information.layer_info is not None and psd._record.layer_and_mask_information.layer_info.layer_count > 0

    if(HydrusImageHandling.PILImageHasTransparency(pil_image) and no_alpha):
        # merged image from psd-tools has transparency when it shouldn't
        # see https://github.com/psd-tools/psd-tools/issues/369

        # I think it's fine to convert to RGB in all cases since eventually
        # that has to happen for the thumbnail anyway.
        pil_image = pil_image.convert("RGB")


    if clip_rect is not None:
        
        pil_image = HydrusImageHandling.ClipPILImage( pil_image, clip_rect )
        
    
    thumbnail_pil_image = pil_image.resize( target_resolution, PILImage.ANTIALIAS )
    
    thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesPIL( thumbnail_pil_image )
    
    return thumbnail_bytes



def GetPSDResolution(path: str):

    psd = PSDImage.open(path)

    resolution = (psd.width, psd.height)

    return resolution