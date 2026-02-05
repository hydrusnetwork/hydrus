from functools import reduce

import math
import numpy
import numpy.core.multiarray # important this comes before cv!

import cv2

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientConstants as CC

def DiscardBlankPerceptualHashes( perceptual_hashes ):
    
    perceptual_hashes = { perceptual_hash for perceptual_hash in perceptual_hashes if HydrusData.Get64BitHammingDistance( perceptual_hash, CC.BLANK_PERCEPTUAL_HASH ) > 4 }
    
    return perceptual_hashes
    

def GenerateUsefulShapePerceptualHashes( path, mime ):
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: loading image' )
        
    
    try:
        
        numpy_image = HydrusImageHandling.GenerateNumPyImage( path, mime )
        
        return GenerateUsefulShapePerceptualHashesNumPy( numpy_image )
        
    except Exception as e:
        
        return set()
        
    

def PILDCT( greyscale_numpy_image: numpy.ndarray ) -> numpy.ndarray:
    # this emulates cv2.dct and was figured out by prkc. there is some OpenCV secret magic that differs from 'typical' DCT
    # it should be a complete drop-in other than tiny floating-point calc differences 3.9204849e+02 vs 3.92048486e+02
    # experimentally, I ran the final phash on 500 different files and every single one was exactly the same!
    # also, W and Norm can be precomputed if you like!
    w, h = 2 * greyscale_numpy_image.shape[0], 2 * greyscale_numpy_image.shape[1]
    extended = numpy.zeros((w,h), numpy.float64)
    extended[0:w//2,0:h//2] = greyscale_numpy_image
    extended[0:w//2,h//2:h] = numpy.fliplr(greyscale_numpy_image)
    extended[w//2:w,:] = numpy.flipud(extended[0:w//2,:])
    dct_ = numpy.fft.fft2(extended, norm="ortho")[0:w//2,0:h//2]
    invsqrt2 = 1/math.sqrt(2)
    W = lambda N, k: numpy.exp(-1j*k*math.pi/N)*(invsqrt2 if k == 0 else 1.0)
    Norm = numpy.fromfunction(numpy.vectorize(lambda i,j: W(w,i)*W(h,j)), (w//2,h//2), dtype=numpy.cdouble)
    return numpy.real(numpy.multiply(Norm,dct_))
    

def GenerateShapePerceptualHashNumPy( numpy_image: numpy.ndarray, phash_length = 64 ):
    
    if phash_length == 64:
        
        phash_dimension = 8
        
    elif phash_length == 256:
        
        phash_dimension = 16
        
    else:
        
        raise NotImplementedError( 'Unknown phash length!' )
        
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: image shape: {}'.format( numpy_image.shape ) )
        
    
    if len( numpy_image.shape ) == 3:
        
        ( y, x, depth ) = numpy_image.shape
        
        if depth == 4:
            
            # doing this on 10000x10000 pngs eats ram like mad
            # we don't want to do GetThumbnailResolution as for extremely wide or tall images, we'll then scale below 32 pixels for one dimension, losing information!
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
            
        elif depth == 3:
            
            # this single step is nice and fast, so we won't scale to 256x256 beforehand
            numpy_image_gray = cv2.cvtColor( numpy_image, cv2.COLOR_RGB2GRAY )
            
        
    else:
        
        numpy_image_gray = numpy_image
        
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: grey image shape: {}'.format( numpy_image_gray.shape ) )
        
    
    tiny_dimension = phash_dimension * 4
    
    numpy_image_tiny = cv2.resize( numpy_image_gray, ( tiny_dimension, tiny_dimension ), interpolation = cv2.INTER_AREA )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: tiny image shape: {}'.format( numpy_image_tiny.shape ) )
        
    
    # convert to float and calc dct
    
    numpy_image_tiny_float = numpy.float32( numpy_image_tiny )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: tiny float image shape: {}'.format( numpy_image_tiny_float.shape ) )
        HydrusData.ShowText( 'phash generation: generating dct' )
        
    
    dct_full = PILDCT( numpy_image_tiny_float )
    
    # take top left square (8x8 for 64bit) of dct
    
    dct_useful = dct_full[:phash_dimension,:phash_dimension]
    
    # get median of dct
    # exclude [0,0], which represents flat colour
    # this [0,0] exclusion is apparently important for mean, but maybe it ain't so important for median--w/e
    
    # old mean code
    # mask = numpy.ones( ( 8, 8 ) )
    # mask[0,0] = 0
    # average = numpy.average( dct_useful, weights = mask )
    
    median = numpy.median( dct_useful.reshape( phash_dimension * phash_dimension )[1:] )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: median: {}'.format( median ) )
        
    
    # make a monochromatic, 64-bit hash of whether the entry is above or below the median
    
    dct_useful_boolean = dct_useful > median
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: collapsing bytes' )
        
    
    # convert TTTFTFTF to 11101010 by repeatedly shifting answer and adding 0 or 1
    # you can even go ( a << 1 ) + b and leave out the initial param on the reduce call as bools act like ints for this
    # but let's not go crazy for another two nanoseconds
    def collapse_bools_to_binary_uint( a, b ):
        
        return ( a << 1 ) + int( b )
        
    
    list_of_bytes = []
    
    if phash_dimension == 8:
        
        for i in range( 8 ):
            
            '''
            # old way of doing it, which compared value to median every time
            byte = 0
            
            for j in range( 8 ):
                
                byte <<= 1 # shift byte one left
                
                value = dct_useful[i,j]
                
                if value > median:
                    
                    byte |= 1
                    
                
            '''
            
            # this is a 0-255 int
            byte = reduce( collapse_bools_to_binary_uint, dct_useful_boolean[i], 0 )
            
            list_of_bytes.append( byte )
            
        
        perceptual_hash = bytes( list_of_bytes ) # this works!
        
    else:
        
        bits = dct_useful_boolean.astype( numpy.uint ).reshape( -1, 8 )
        
        byte_values = numpy.packbits( bits, axis = 1 )
        
        perceptual_hash = byte_values.flatten().tobytes()
        
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: perceptual_hash: {}'.format( perceptual_hash.hex() ) )
        
    
    return perceptual_hash
    

def GenerateUsefulShapePerceptualHashesNumPy( numpy_image: numpy.ndarray ):
    
    perceptual_hash = GenerateShapePerceptualHashNumPy( numpy_image )
    
    # now discard the blank hash, which is 1000000... and not useful
    # 2025-12 Update: Interesting submission by a user of two white pages that matched in the system--they were pure white, so phashes were being discarded ok here, but they were the same res, and thus pixel dupes!
    
    perceptual_hashes = set()
    
    perceptual_hashes.add( perceptual_hash )
    
    perceptual_hashes = DiscardBlankPerceptualHashes( perceptual_hashes )
    
    if HG.phash_generation_report_mode:
        
        HydrusData.ShowText( 'phash generation: final perceptual_hashes: {}'.format( [ phash.hexh() for phash in perceptual_hashes ] ) )
        
    
    # we good
    
    return perceptual_hashes
    
