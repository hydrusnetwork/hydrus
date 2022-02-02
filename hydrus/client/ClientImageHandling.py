from functools import reduce

import numpy
import numpy.core.multiarray # important this comes before cv!

import cv2

from hydrus.client import ClientConstants as CC
from hydrus.core import HydrusData
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusGlobals as HG

cv_interpolation_enum_lookup = {}

cv_interpolation_enum_lookup[ CC.ZOOM_NEAREST ] = cv2.INTER_NEAREST
cv_interpolation_enum_lookup[ CC.ZOOM_LINEAR ] = cv2.INTER_LINEAR
cv_interpolation_enum_lookup[ CC.ZOOM_AREA ] = cv2.INTER_AREA
cv_interpolation_enum_lookup[ CC.ZOOM_CUBIC ] = cv2.INTER_CUBIC
cv_interpolation_enum_lookup[ CC.ZOOM_LANCZOS4 ] = cv2.INTER_LANCZOS4

def DiscardBlankPerceptualHashes( perceptual_hashes ):
    
    perceptual_hashes = { perceptual_hash for perceptual_hash in perceptual_hashes if HydrusData.Get64BitHammingDistance( perceptual_hash, CC.BLANK_PERCEPTUAL_HASH ) > 4 }
    
    return perceptual_hashes
    
def GenerateNumPyImage( path, mime ):
    
    force_pil = HG.client_controller.new_options.GetBoolean( 'load_images_with_pil' )
    
    return HydrusImageHandling.GenerateNumPyImage( path, mime, force_pil = force_pil )
    
def GenerateShapePerceptualHashes( path, mime ):
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: loading image' )
        
    
    numpy_image = GenerateNumPyImage( path, mime )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: image shape: {}'.format( numpy_image.shape ) )
        
    
    ( y, x, depth ) = numpy_image.shape
    
    if depth == 4:
        
        # doing this on 10000x10000 pngs eats ram like mad
        # we don't want to do GetThumbnailResolutionAndClipRegion as for extremely wide or tall images, we'll then scale below 32 pixels for one dimension, losing information!
        # however, it does not matter if we stretch the image a bit, since we'll be coercing 32x32 in a minute
        
        new_x = min( 256, x )
        new_y = min( 256, y )
        
        numpy_image = cv2.resize( numpy_image, ( new_x, new_y ), interpolation = cv2.INTER_AREA )
        
        ( y, x, depth ) = numpy_image.shape
        
        # create weight and transform numpy_image to greyscale
        
        numpy_alpha = numpy_image[ :, :, 3 ]
        
        numpy_image_rgb = numpy_image[ :, :, :3 ]
        
        numpy_image_gray_bare = cv2.cvtColor( numpy_image_rgb, cv2.COLOR_RGB2GRAY )
        
        # create a white greyscale canvas
        
        white = numpy.full( ( y, x ), 255.0 )
        
        # paste the grayscale image onto the white canvas using: pixel * alpha_float + white * ( 1 - alpha_float )
        
        # note alpha 255 = opaque, alpha 0 = transparent
        
        # also, note:
        # white * ( 1 - alpha_float )
        # =
        # 255 * ( 1 - ( alpha / 255 ) )
        # =
        # 255 - alpha
        
        numpy_image_gray = numpy.uint8( ( numpy_image_gray_bare * ( numpy_alpha / 255.0 ) ) + ( white - numpy_alpha ) )
        
    else:
        
        # this single step is nice and fast, so we won't scale to 256x256 beforehand
        numpy_image_gray = cv2.cvtColor( numpy_image, cv2.COLOR_RGB2GRAY )
        
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: grey image shape: {}'.format( numpy_image_gray.shape ) )
        
    
    numpy_image_tiny = cv2.resize( numpy_image_gray, ( 32, 32 ), interpolation = cv2.INTER_AREA )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: tiny image shape: {}'.format( numpy_image_tiny.shape ) )
        
    
    # convert to float and calc dct
    
    numpy_image_tiny_float = numpy.float32( numpy_image_tiny )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: tiny float image shape: {}'.format( numpy_image_tiny_float.shape ) )
        HydrusData.ShowText( 'phash generation: generating dct' )
        
    
    dct = cv2.dct( numpy_image_tiny_float )
    
    # take top left 8x8 of dct
    
    dct_88 = dct[:8,:8]
    
    # get median of dct
    # exclude [0,0], which represents flat colour
    # this [0,0] exclusion is apparently important for mean, but maybe it ain't so important for median--w/e
    
    # old mean code
    # mask = numpy.ones( ( 8, 8 ) )
    # mask[0,0] = 0
    # average = numpy.average( dct_88, weights = mask )
    
    median = numpy.median( dct_88.reshape( 64 )[1:] )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: median: {}'.format( median ) )
        
    
    # make a monochromatic, 64-bit hash of whether the entry is above or below the median
    
    dct_88_boolean = dct_88 > median
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: collapsing bytes' )
        
    
    # convert TTTFTFTF to 11101010 by repeatedly shifting answer and adding 0 or 1
    # you can even go ( a << 1 ) + b and leave out the initial param on the reduce call as bools act like ints for this
    # but let's not go crazy for another two nanoseconds
    def collapse_bools_to_binary_uint( a, b ):
        
        return ( a << 1 ) + int( b )
        
    
    list_of_bytes = []
    
    for i in range( 8 ):
        
        '''
        # old way of doing it, which compared value to median every time
        byte = 0
        
        for j in range( 8 ):
            
            byte <<= 1 # shift byte one left
            
            value = dct_88[i,j]
            
            if value > median:
                
                byte |= 1
                
            
        '''
        
        # this is a 0-255 int
        byte = reduce( collapse_bools_to_binary_uint, dct_88_boolean[i], 0 )
        
        list_of_bytes.append( byte )
        
    
    perceptual_hash = bytes( list_of_bytes ) # this works!
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: perceptual_hash: {}'.format( perceptual_hash.hex() ) )
        
    
    # now discard the blank hash, which is 1000000... and not useful
    
    perceptual_hashes = set()
    
    perceptual_hashes.add( perceptual_hash )
    
    perceptual_hashes = DiscardBlankPerceptualHashes( perceptual_hashes )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: final perceptual_hashes: {}'.format( len( perceptual_hashes ) ) )
        
    
    # we good
    
    return perceptual_hashes
    
def ResizeNumPyImageForMediaViewer( mime, numpy_image, target_resolution ):
    
    ( target_width, target_height ) = target_resolution
    new_options = HG.client_controller.new_options
    
    ( scale_up_quality, scale_down_quality ) = new_options.GetMediaZoomQuality( mime )
    
    ( image_height, image_width, depth ) = numpy_image.shape
    
    if ( target_width, target_height ) == ( image_height, image_width ):
        
        return numpy_image
        
    else:
        
        if target_width > image_width or target_height > image_height:
            
            interpolation = cv_interpolation_enum_lookup[ scale_up_quality ]
            
        else:
            
            interpolation = cv_interpolation_enum_lookup[ scale_down_quality ]
            
        
        return cv2.resize( numpy_image, ( target_width, target_height ), interpolation = interpolation )
        
    
