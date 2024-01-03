import io

import numpy

import cv2

from PIL import Image as PILImage
from PIL import ImageCms as PILImageCms

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core.files.images import HydrusImageColours
from hydrus.core.files.images import HydrusImageMetadata

try:
    
    PIL_SRGB_PROFILE = PILImageCms.get_display_profile()
    
except:
    
    PIL_SRGB_PROFILE = PILImageCms.createProfile( 'sRGB' )
    

def NormaliseNumPyImageToUInt8( numpy_image: numpy.array ):
    
    if numpy_image.dtype == numpy.uint16:
        
        numpy_image = numpy.array( numpy_image // 256, dtype = numpy.uint8 )
        
    elif numpy_image.dtype == numpy.int16:
        
        numpy_image = numpy.array( ( numpy_image + 32768 ) // 256, dtype = numpy.uint8 )
        
    elif numpy_image.dtype != numpy.uint8:
        
        # this is hacky and is applying some crazy old-school flickr HDR to minmax our range, but it basically works
        # this MINMAX is a decent fallback since it seems that some satellite TIFF files have a range of -9999,9999, which is probably in the advanced metadata somewhere but we can't read it mate
        
        #numpy_image = cv2.normalize( numpy_image, None, 0, 255, cv2.NORM_MINMAX, dtype = cv2.CV_8U )
        
        # this is hacky and is applying some crazy old-school flickr HDR to minmax our range, but it basically works
        min_value = numpy.min( numpy_image )
        max_value = numpy.max( numpy_image )
        
        if min_value > 0:
            
            numpy_image = numpy_image - min_value
            
        
        range_value = ( max_value - min_value ) + 1
        
        if range_value > 0:
            
            magic_multiple = 256 / range_value
            
            numpy_image = ( numpy_image * magic_multiple ).clip( 0, 255 ).astype( numpy.uint8 )
            
        else:
            
            numpy_image = numpy_image.astype( numpy.uint8 )
            
        
    
    return numpy_image
    

def DequantizeFreshlyLoadedNumPyImage( numpy_image: numpy.array ) -> numpy.array:
    
    # OpenCV loads images in BGR, and we want to normalise to RGB in general
    
    numpy_image = NormaliseNumPyImageToUInt8( numpy_image )
    
    shape = numpy_image.shape
    
    if len( shape ) == 2:
        
        # L to RGB
        
        l = numpy_image
        
        # axis -1 makes them stack on the last dimension
        numpy_image = numpy.stack( ( l, l, l ), axis = -1 )
        
    else:
        
        ( im_y, im_x, depth ) = shape
        
        if depth == 4:
            
            # BGRA to RGBA
            
            b = numpy_image[ :, :, 0 ]
            g = numpy_image[ :, :, 1 ]
            r = numpy_image[ :, :, 2 ]
            a = numpy_image[ :, :, 3 ]
            
            # axis -1 makes them stack on the last dimension
            numpy_image = numpy.stack( ( r, g, b, a ), axis = -1 )
            
        else:
            
            # BGR to RGB, channel swap
            
            numpy_image = numpy_image[ :, :, ::-1 ]
            
        
    
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
        
        if pil_image.mode in ( 'I', 'F', 'L', 'LA', 'P' ):
            
            # had a bunch of LA pngs that turned pure white on RGBA ICC conversion
            # but seem to work fine if keep colourspace the same for now
            # it is a mystery, I guess a PIL bug, but presumably L and LA are technically sRGB so it is still ok to this
            
            # note that 'I' and 'F' ICC Profile images tend to just fail here with 'cannot build transform', and generally have poor PIL support, so I convert to RGB beforehand with hacky tech
            
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
        
        channel_number = HydrusImageColours.GetNumPyAlphaChannelNumber( numpy_image )
        
        numpy_image = numpy_image[:,:,:channel_number].copy()
        
        # old way, which doesn't actually remove the channel lmao lmao lmao
        '''
        convert = cv2.COLOR_RGBA2RGB
        
        numpy_image = cv2.cvtColor( numpy_image, convert )
        '''
    
    return numpy_image
    
