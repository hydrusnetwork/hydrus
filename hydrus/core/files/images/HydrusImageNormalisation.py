import io

import numpy

from PIL import Image as PILImage
from PIL import ImageCms as PILImageCms

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core.files.images import HydrusImageColours
from hydrus.core.files.images import HydrusImageICCProfiles
from hydrus.core.files.images import HydrusImageMathSlop as MathSlop
from hydrus.core.files.images import HydrusImageMetadata

PIL_SRGB_PROFILE = PILImageCms.createProfile( 'sRGB' )

DO_ICC_PROFILE_NORMALISATION = True

def ConvertGammaChromaticityPNGToSRGB( pil_image ):
    
    # this is no longer used. it is ten times slower than the ICC Profile solution and may be unstable for very large images
    
    if not PILImageIsPNGWithGammaAndChromaticity( pil_image ):
        
        return pil_image
        
    
    linear_gamma = pil_image.info[ 'gamma' ] # 0.45455
    display_gamma = 1 / linear_gamma # 2.2
    
    chroma = pil_image.info[ 'chromaticity' ]
    
    # Extract chromaticities
    white_xy = ( chroma[0], chroma[1] )
    red_xy = ( chroma[2], chroma[3] )
    green_xy = ( chroma[4], chroma[5] )
    blue_xy = ( chroma[6], chroma[7] )
    
    # Compute RGB→XYZ matrix for source
    M_src_rgb_to_xyz = MathSlop.chromaticities_to_rgb_to_xyz( white_xy, red_xy, green_xy, blue_xy )
    
    '''
    # as far as I can tell, this makes no change to the end pixel hash in my main test file
    XYZ_src_white = xy_to_xyz( white_xy[0], white_xy[1] )
    XYZ_dst_white = xy_to_xyz(0.3127, 0.3290)  # D65
    
    adapt = adapt_white_point( XYZ_src_white, XYZ_dst_white )
    
    M_src_rgb_to_xyz = adapt @ M_src_rgb_to_xyz
    '''
    
    # Standard sRGB XYZ conversion matrix
    M_xyz_to_srgb = numpy.array( [
        [ 3.2404542, -1.5371385, -0.4985314 ],
        [ -0.9692660,  1.8760108,  0.0415560 ],
        [ 0.0556434, -0.2040259,  1.0572252 ]
    ] )
    
    # Combine: src RGB → XYZ → sRGB
    M_total = M_xyz_to_srgb @ M_src_rgb_to_xyz
    
    primary_work_canvas_uint8 = numpy.asarray( pil_image ).astype( numpy.uint8 )
    
    # ok we are now doing this in tiles to save memory as we spam arrays all over the place
    # also we are going to have a primary work canvas in uint8, not float32
    TILE_DIMENSION = 512
    
    ( height, width, depth ) = primary_work_canvas_uint8.shape
    
    for y in range( 0, height, TILE_DIMENSION ):
        
        for x in range( 0, width, TILE_DIMENSION ):
            
            y_end = min( y + TILE_DIMENSION, height )
            x_end = min( x + TILE_DIMENSION, width )
            
            work_tile = primary_work_canvas_uint8[ y:y_end, x:x_end ].astype( numpy.float32 ) / 255.0
            
            work_tile_shape = work_tile.shape
            
            if work_tile.ndim == 3 and work_tile_shape[2] >= 3:
                
                work_tile_rgb = work_tile[..., :3]
                
                if work_tile_shape[2] == 4:
                    
                    work_tile_alpha = work_tile[ ..., 3 : 4 ]
                    
                else:
                    
                    work_tile_alpha = None
                    
                
            else:
                
                raise ValueError("Only RGB/RGBA images are supported.")
                
            
            # Processing Begins
            
            # Apply source gamma decoding
            rgb_linear = numpy.power( work_tile_rgb, display_gamma )
            
            # Apply RGB → XYZ → sRGB transform
            shape = rgb_linear.shape
            flat_rgb = rgb_linear.reshape( -1, 3 )
            transformed = flat_rgb @ M_total.T
            
            numpy.clip( transformed, 0, 1, out = transformed )
            
            transformed = MathSlop.srgb_encode( transformed )
            
            # Restore to image shape
            corrected_rgb = numpy.reshape( transformed, shape )
            
            # If alpha present, preserve it
            if work_tile_alpha is not None:
                
                corrected_tile = numpy.concatenate([ corrected_rgb, work_tile_alpha ], axis = 2 )
                
            else:
                
                corrected_tile = corrected_rgb
                
            
            corrected_tile = numpy.round( corrected_tile * 255.0 ).astype( numpy.uint8 )
            
            # Processing Done!
            
            primary_work_canvas_uint8[ y : y_end, x : x_end ] = corrected_tile
            
        
    
    converted_pil_image_modeless = PILImage.fromarray( primary_work_canvas_uint8 )
    
    converted_pil_image = converted_pil_image_modeless.convert( pil_image.mode ) # probably a no-op
    
    return converted_pil_image
    

def GenerateICCProfileBytesFromGammaAndChromaticityPNG( pil_image: PILImage.Image ):
    
    file_gamma = pil_image.info[ 'gamma' ]  # e.g. 0.45455
    
    # PNG gAMA stores "file gamma" = 1/encoding_gamma.
    # We want encoding_gamma for an ICC TRC.
    if not file_gamma:
        
        encoding_gamma = 2.2
        
    else:
        
        encoding_gamma = 1.0 / float( file_gamma )
        
    
    chroma = pil_image.info[ 'chromaticity' ]
    
    # Extract chromaticities (white, R, G, B)
    white_xy = (float(chroma[0]), float(chroma[1]))
    red_xy = (float(chroma[2]), float(chroma[3]))
    green_xy = (float(chroma[4]), float(chroma[5]))
    blue_xy = (float(chroma[6]), float(chroma[7]))
    
    # Compute RGB→XYZ matrix referenced to the PNG's stated white (commonly D65)
    M_rgb_to_xyz_src = MathSlop.chromaticities_to_rgb_to_xyz(white_xy, red_xy, green_xy, blue_xy)
    
    # ICC PCS is D50; adapt the matrix columns to D50 to match v2 expectations
    M_rgb_to_xyz_D50 = MathSlop.adapt_rgb_to_xyz_matrix_to_D50(M_rgb_to_xyz_src, white_xy)
    
    icc_profile_bytes = HydrusImageICCProfiles.make_gamma_and_chromaticity_icc_profile( encoding_gamma, M_rgb_to_xyz_D50 )
    
    return icc_profile_bytes
    

def SetDoICCProfileNormalisation( value: bool ):
    
    global DO_ICC_PROFILE_NORMALISATION
    
    if value != DO_ICC_PROFILE_NORMALISATION:
        
        DO_ICC_PROFILE_NORMALISATION = value
        
        HG.controller.pub( 'clear_image_cache' )
        HG.controller.pub( 'clear_image_tile_cache' )
        
    

def NormaliseNumPyImageToUInt8( numpy_image: numpy.ndarray ):
    
    if numpy_image.dtype == numpy.uint16:
        
        numpy_image = numpy.array( numpy_image // 256, dtype = numpy.uint8 )
        
    elif numpy_image.dtype == numpy.int16:
        
        numpy_image = numpy.array( ( numpy_image + 32768 ) // 256, dtype = numpy.uint8 )
        
    elif numpy_image.dtype != numpy.uint8:
        
        # this is hacky and is applying some crazy old-school flickr HDR to minmax our range, but it basically works
        # this MINMAX is a decent fallback since it seems that some satellite TIFF files have a range of -9999,9999, which is probably in the advanced metadata somewhere but we can't read it mate
        
        #numpy_image = cv2.normalize( numpy_image, None, 0, 255, cv2.NORM_MINMAX, dtype = cv2.CV_8U )
        
        # this is hacky and is applying some crazy old-school flickr HDR to minmax our range, but it basically works
        min_value = float( numpy.min( numpy_image ) )
        max_value = float( numpy.max( numpy_image ) )
        
        if min_value > 0:
            
            numpy_image = numpy_image - min_value
            
        
        range_value = ( max_value - min_value ) + 1
        
        if range_value > 0:
            
            magic_multiple = 256 / range_value
            
            numpy_image = ( numpy_image * magic_multiple ).clip( 0, 255 ).astype( numpy.uint8 )
            
        else:
            
            numpy_image = numpy_image.astype( numpy.uint8 )
            
        
    
    return numpy_image
    

def DequantizeFreshlyLoadedNumPyImage( numpy_image: numpy.ndarray ) -> numpy.ndarray:
    
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
    

def PILImageIsPNGWithGammaAndChromaticity( pil_image: PILImage.Image ):
    
    if pil_image.format == 'PNG' and pil_image.mode in ( 'RGB', 'RGBA' ) and 'gamma' in pil_image.info and 'chromaticity' in pil_image.info:
        
        linear_gamma = pil_image.info[ 'gamma' ]
        
        if linear_gamma == 0.0:
            
            return False
            
        
        if 0.0 in pil_image.info[ 'chromaticity' ]:
            
            return False
            
        
        return True
        
    
    return False
    

def PILImageIsPNGWithSRGB( pil_image: PILImage.Image ):
    
    if pil_image.format == 'PNG' and 'srgb' in pil_image.info:
        
        return True
        
    
    return False
    

def DequantizePILImage( pil_image: PILImage.Image ) -> PILImage.Image:
    
    if HydrusImageMetadata.HasICCProfile( pil_image ) and DO_ICC_PROFILE_NORMALISATION:
        
        try:
            
            icc_profile_bytes = HydrusImageMetadata.GetICCProfileBytes( pil_image )
            
            try:
                
                pil_image = NormaliseICCProfilePILImageToSRGB( icc_profile_bytes, pil_image )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                HydrusData.ShowText( 'Failed to normalise image with ICC profile.' )
                
            
        except HydrusExceptions.DataMissing:
            
            pass
            
        
    elif PILImageIsPNGWithSRGB( pil_image ):
        
        pass # we are already sRGB
        # the 'srgb' key has a value like 0 or 1. this is 'rendering intent' stuff and would be useful if we wanted to convert to another system
        
    elif PILImageIsPNGWithGammaAndChromaticity( pil_image ):
        
        # if a png has an ICC Profile, that overrides gamma/chromaticity, so this should be elif
        # there's also srgb, which has precedence between those two and we can consider if and when it comes up.
        # it looks like srgb just means it is already in srgb, no worries we don't need to do anything, but if that exists, we should be ignoring gmma/chrm
        
        # this doesn't work, but I think we are close! it would be great if we could figure this out since it works fast as anything
        # Qt does it but I couldn't replicate their colourspace and whitepoint conversions right
        
        icc_profile_bytes = GenerateICCProfileBytesFromGammaAndChromaticityPNG( pil_image )
        
        try:
            
            pil_image = NormaliseICCProfilePILImageToSRGB( icc_profile_bytes, pil_image )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            HydrusData.ShowText( 'Failed to normalise image with ICC profile.' )
            
        
        '''
        try:
            
            pil_image = ConvertGammaChromaticityPNGToSRGB( pil_image )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            HydrusData.ShowText( 'Failed to normalise PNG with gamma/chromaticity info.' )
            
        '''
    
    pil_image = NormalisePILImageToRGB( pil_image )
    
    return pil_image
    

def NormaliseICCProfilePILImageToSRGB( icc_profile_bytes: bytes, pil_image: PILImage.Image ) -> PILImage.Image:
    
    try:
        
        f = io.BytesIO( icc_profile_bytes )
        
        src_profile = PILImageCms.ImageCmsProfile( f )
        
        if pil_image.mode in ( 'I', 'I;16', 'I;16L', 'I;16B', 'I;16N', 'F', 'L', 'LA', 'P' ):
            
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
    
    if pil_image.format == 'PNG':
        
        # although pngs can store EXIF, it is in a weird custom frame and isn't fully supported
        # We have an example of a png with an Orientation=8, 112693c435e08e95751993f9c8bc6b2c49636354334f30eaa91a74429418433e, that shouldn't be rotated
        
        return pil_image
        
    
    exif_dict = HydrusImageMetadata.GetEXIFDict( pil_image )
    
    if exif_dict is not None:
        
        EXIF_ORIENTATION = 274
        
        if EXIF_ORIENTATION in exif_dict:
            
            orientation = exif_dict[ EXIF_ORIENTATION ]
            
            if orientation == 1:
                
                pass # normal
                
            elif orientation == 2:
                
                # mirrored horizontal
                
                pil_image = pil_image.transpose( PILImage.Transpose.FLIP_LEFT_RIGHT )
                
            elif orientation == 3:
                
                # 180
                
                pil_image = pil_image.transpose( PILImage.Transpose.ROTATE_180 )
                
            elif orientation == 4:
                
                # mirrored vertical
                
                pil_image = pil_image.transpose( PILImage.Transpose.FLIP_TOP_BOTTOM )
                
            elif orientation == 5:
                
                # seems like these 90 degree rotations are wrong, but fliping them works for my posh example images, so I guess the PIL constants are odd
                
                # mirrored horizontal, then 90 CCW
                
                pil_image = pil_image.transpose( PILImage.Transpose.FLIP_LEFT_RIGHT ).transpose( PILImage.Transpose.ROTATE_90 )
                
            elif orientation == 6:
                
                # 90 CW
                
                pil_image = pil_image.transpose( PILImage.Transpose.ROTATE_270 )
                
            elif orientation == 7:
                
                # mirrored horizontal, then 90 CCW
                
                pil_image = pil_image.transpose( PILImage.Transpose.FLIP_LEFT_RIGHT ).transpose( PILImage.Transpose.ROTATE_270 )
                
            elif orientation == 8:
                
                # 90 CCW
                
                pil_image = pil_image.transpose( PILImage.Transpose.ROTATE_90 )
                
            
        
    
    return pil_image
    

def StripOutAnyUselessAlphaChannel( numpy_image: numpy.ndarray ) -> numpy.ndarray:
    
    if HydrusImageColours.NumPyImageHasUselessAlphaChannel( numpy_image ):
        
        channel_number = HydrusImageColours.GetNumPyAlphaChannelNumber( numpy_image )
        
        numpy_image = numpy_image[:,:,:channel_number].copy()
        
        # old way, which doesn't actually remove the channel lmao lmao lmao
        '''
        convert = cv2.COLOR_RGBA2RGB
        
        numpy_image = cv2.cvtColor( numpy_image, convert )
        '''
    
    return numpy_image
    

def StripOutAnyAlphaChannel( numpy_image: numpy.ndarray ) -> numpy.ndarray:
    
    if HydrusImageColours.NumPyImageHasAlphaChannel( numpy_image ):
        
        channel_number = HydrusImageColours.GetNumPyAlphaChannelNumber( numpy_image )
        
        numpy_image = numpy_image[:,:,:channel_number].copy()
        
    
    return numpy_image
    
