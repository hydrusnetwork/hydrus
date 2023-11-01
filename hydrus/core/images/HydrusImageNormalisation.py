import io

import numpy

import cv2

from PIL import Image as PILImage
from PIL import ImageCms as PILImageCms

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core.images import HydrusImageColours
from hydrus.core.images import HydrusImageMetadata

PIL_SRGB_PROFILE = PILImageCms.createProfile( 'sRGB' )

def DequantizeFreshlyLoadedNumPyImage( numpy_image: numpy.array ) -> numpy.array:
    
    # OpenCV loads images in BGR, and we want to normalise to RGB in general
    
    if numpy_image.dtype == 'uint16':
        
        numpy_image = numpy.array( numpy_image // 256, dtype = 'uint8' )
        
    
    shape = numpy_image.shape
    
    if len( shape ) == 2:
        
        # monochrome image
        
        convert = cv2.COLOR_GRAY2RGB
        
    else:
        
        ( im_y, im_x, depth ) = shape
        
        if depth == 4:
            
            convert = cv2.COLOR_BGRA2RGBA
            
        else:
            
            convert = cv2.COLOR_BGR2RGB
            
        
    
    numpy_image = cv2.cvtColor( numpy_image, convert )
    
    return numpy_image
    

def DequantizePILImage( pil_image: PILImage.Image ) -> PILImage.Image:
    
    if HydrusImageMetadata.HasICCProfile( pil_image ):
        
        try:
            
            pil_image = NormaliseICCProfilePILImageToSRGB( pil_image )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            HydrusData.ShowText( 'Failed to normalise image ICC profile.' )
            
        
    
    pil_image = NormalisePILImageToRGB( pil_image )
    
    return pil_image
    

def NormaliseICCProfilePILImageToSRGB( pil_image: PILImage.Image ) -> PILImage.Image:
    
    try:
        
        icc_profile_bytes = HydrusImageMetadata.GetICCProfileBytes( pil_image )
        
    except HydrusExceptions.DataMissing:
        
        return pil_image
        
    
    try:
        
        f = io.BytesIO( icc_profile_bytes )
        
        src_profile = PILImageCms.ImageCmsProfile( f )
        
        if pil_image.mode in ( 'L', 'LA', 'P' ):
            
            # had a bunch of LA pngs that turned pure white on RGBA ICC conversion
            # but seem to work fine if keep colourspace the same for now
            # it is a mystery, I guess a PIL bug, but presumably L and LA are technically sRGB so it is still ok to this
            
            outputMode = pil_image.mode
            
        else:
            
            if HydrusImageColours.PILImageHasTransparency( pil_image ):
                
                outputMode = 'RGBA'
                
            else:
                
                outputMode = 'RGB'
                
            
        
        pil_image = PILImageCms.profileToProfile( pil_image, src_profile, PIL_SRGB_PROFILE, outputMode = outputMode )
        
    except ( PILImageCms.PyCMSError, OSError ):
        
        # 'cannot build transform' and presumably some other fun errors
        # way more advanced than we can deal with, so we'll just no-op
        
        # OSError is due to a "OSError: cannot open profile from string" a user got
        # no idea, but that seems to be an ImageCms issue doing byte handling and ending up with an odd OSError?
        # or maybe somehow my PIL reader or bytesIO sending string for some reason?
        # in any case, nuke it for now
        
        pass
        
    
    return pil_image
    

def NormalisePILImageToRGB( pil_image: PILImage.Image ) -> PILImage.Image:
    
    if HydrusImageColours.PILImageHasTransparency( pil_image ):
        
        desired_mode = 'RGBA'
        
    else:
        
        desired_mode = 'RGB'
        
    
    if pil_image.mode != desired_mode:
        
        if pil_image.mode == 'LAB':
            
            pil_image = PILImageCms.profileToProfile( pil_image, PILImageCms.createProfile( 'LAB' ), PIL_SRGB_PROFILE, outputMode = 'RGB' )
            
        else:
            
            pil_image = pil_image.convert( desired_mode )
            
        
    
    return pil_image
    

def RotateEXIFPILImage( pil_image: PILImage.Image )-> PILImage.Image:
    
    exif_dict = HydrusImageMetadata.GetEXIFDict( pil_image )
    
    if exif_dict is not None:
        
        EXIF_ORIENTATION = 274
        
        if EXIF_ORIENTATION in exif_dict:
            
            orientation = exif_dict[ EXIF_ORIENTATION ]
            
            if orientation == 1:
                
                pass # normal
                
            elif orientation == 2:
                
                # mirrored horizontal
                
                pil_image = pil_image.transpose( PILImage.FLIP_LEFT_RIGHT )
                
            elif orientation == 3:
                
                # 180
                
                pil_image = pil_image.transpose( PILImage.ROTATE_180 )
                
            elif orientation == 4:
                
                # mirrored vertical
                
                pil_image = pil_image.transpose( PILImage.FLIP_TOP_BOTTOM )
                
            elif orientation == 5:
                
                # seems like these 90 degree rotations are wrong, but fliping them works for my posh example images, so I guess the PIL constants are odd
                
                # mirrored horizontal, then 90 CCW
                
                pil_image = pil_image.transpose( PILImage.FLIP_LEFT_RIGHT ).transpose( PILImage.ROTATE_90 )
                
            elif orientation == 6:
                
                # 90 CW
                
                pil_image = pil_image.transpose( PILImage.ROTATE_270 )
                
            elif orientation == 7:
                
                # mirrored horizontal, then 90 CCW
                
                pil_image = pil_image.transpose( PILImage.FLIP_LEFT_RIGHT ).transpose( PILImage.ROTATE_270 )
                
            elif orientation == 8:
                
                # 90 CCW
                
                pil_image = pil_image.transpose( PILImage.ROTATE_90 )
                
            
        
    
    return pil_image
    

def StripOutAnyUselessAlphaChannel( numpy_image: numpy.array ) -> numpy.array:
    
    if HydrusImageColours.NumPyImageHasUselessAlphaChannel( numpy_image ):
        
        numpy_image = numpy_image[:,:,:3].copy()
        
        # old way, which doesn't actually remove the channel lmao lmao lmao
        '''
        convert = cv2.COLOR_RGBA2RGB
        
        numpy_image = cv2.cvtColor( numpy_image, convert )
        '''
    
    return numpy_image
    
