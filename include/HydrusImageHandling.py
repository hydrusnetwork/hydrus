import cStringIO
import numpy.core.multiarray # important this comes before cv!
import cv2
import HydrusConstants as HC
import HydrusExceptions
import HydrusThreading
import lz4
import numpy
import os
from PIL import _imaging
from PIL import Image as PILImage
import shutil
import struct
import threading
import time
import traceback
import HydrusData
import HydrusFileHandling
import HydrusGlobals

#LINEAR_SCALE_PALETTE = [ 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 16, 16, 16, 17, 17, 17, 18, 18, 18, 19, 19, 19, 20, 20, 20, 21, 21, 21, 22, 22, 22, 23, 23, 23, 24, 24, 24, 25, 25, 25, 26, 26, 26, 27, 27, 27, 28, 28, 28, 29, 29, 29, 30, 30, 30, 31, 31, 31, 32, 32, 32, 33, 33, 33, 34, 34, 34, 35, 35, 35, 36, 36, 36, 37, 37, 37, 38, 38, 38, 39, 39, 39, 40, 40, 40, 41, 41, 41, 42, 42, 42, 43, 43, 43, 44, 44, 44, 45, 45, 45, 46, 46, 46, 47, 47, 47, 48, 48, 48, 49, 49, 49, 50, 50, 50, 51, 51, 51, 52, 52, 52, 53, 53, 53, 54, 54, 54, 55, 55, 55, 56, 56, 56, 57, 57, 57, 58, 58, 58, 59, 59, 59, 60, 60, 60, 61, 61, 61, 62, 62, 62, 63, 63, 63, 64, 64, 64, 65, 65, 65, 66, 66, 66, 67, 67, 67, 68, 68, 68, 69, 69, 69, 70, 70, 70, 71, 71, 71, 72, 72, 72, 73, 73, 73, 74, 74, 74, 75, 75, 75, 76, 76, 76, 77, 77, 77, 78, 78, 78, 79, 79, 79, 80, 80, 80, 81, 81, 81, 82, 82, 82, 83, 83, 83, 84, 84, 84, 85, 85, 85, 86, 86, 86, 87, 87, 87, 88, 88, 88, 89, 89, 89, 90, 90, 90, 91, 91, 91, 92, 92, 92, 93, 93, 93, 94, 94, 94, 95, 95, 95, 96, 96, 96, 97, 97, 97, 98, 98, 98, 99, 99, 99, 100, 100, 100, 101, 101, 101, 102, 102, 102, 103, 103, 103, 104, 104, 104, 105, 105, 105, 106, 106, 106, 107, 107, 107, 108, 108, 108, 109, 109, 109, 110, 110, 110, 111, 111, 111, 112, 112, 112, 113, 113, 113, 114, 114, 114, 115, 115, 115, 116, 116, 116, 117, 117, 117, 118, 118, 118, 119, 119, 119, 120, 120, 120, 121, 121, 121, 122, 122, 122, 123, 123, 123, 124, 124, 124, 125, 125, 125, 126, 126, 126, 127, 127, 127, 128, 128, 128, 129, 129, 129, 130, 130, 130, 131, 131, 131, 132, 132, 132, 133, 133, 133, 134, 134, 134, 135, 135, 135, 136, 136, 136, 137, 137, 137, 138, 138, 138, 139, 139, 139, 140, 140, 140, 141, 141, 141, 142, 142, 142, 143, 143, 143, 144, 144, 144, 145, 145, 145, 146, 146, 146, 147, 147, 147, 148, 148, 148, 149, 149, 149, 150, 150, 150, 151, 151, 151, 152, 152, 152, 153, 153, 153, 154, 154, 154, 155, 155, 155, 156, 156, 156, 157, 157, 157, 158, 158, 158, 159, 159, 159, 160, 160, 160, 161, 161, 161, 162, 162, 162, 163, 163, 163, 164, 164, 164, 165, 165, 165, 166, 166, 166, 167, 167, 167, 168, 168, 168, 169, 169, 169, 170, 170, 170, 171, 171, 171, 172, 172, 172, 173, 173, 173, 174, 174, 174, 175, 175, 175, 176, 176, 176, 177, 177, 177, 178, 178, 178, 179, 179, 179, 180, 180, 180, 181, 181, 181, 182, 182, 182, 183, 183, 183, 184, 184, 184, 185, 185, 185, 186, 186, 186, 187, 187, 187, 188, 188, 188, 189, 189, 189, 190, 190, 190, 191, 191, 191, 192, 192, 192, 193, 193, 193, 194, 194, 194, 195, 195, 195, 196, 196, 196, 197, 197, 197, 198, 198, 198, 199, 199, 199, 200, 200, 200, 201, 201, 201, 202, 202, 202, 203, 203, 203, 204, 204, 204, 205, 205, 205, 206, 206, 206, 207, 207, 207, 208, 208, 208, 209, 209, 209, 210, 210, 210, 211, 211, 211, 212, 212, 212, 213, 213, 213, 214, 214, 214, 215, 215, 215, 216, 216, 216, 217, 217, 217, 218, 218, 218, 219, 219, 219, 220, 220, 220, 221, 221, 221, 222, 222, 222, 223, 223, 223, 224, 224, 224, 225, 225, 225, 226, 226, 226, 227, 227, 227, 228, 228, 228, 229, 229, 229, 230, 230, 230, 231, 231, 231, 232, 232, 232, 233, 233, 233, 234, 234, 234, 235, 235, 235, 236, 236, 236, 237, 237, 237, 238, 238, 238, 239, 239, 239, 240, 240, 240, 241, 241, 241, 242, 242, 242, 243, 243, 243, 244, 244, 244, 245, 245, 245, 246, 246, 246, 247, 247, 247, 248, 248, 248, 249, 249, 249, 250, 250, 250, 251, 251, 251, 252, 252, 252, 253, 253, 253, 254, 254, 254, 255, 255, 255 ]

def ConvertToPngIfBmp( path ):
    
    with open( path, 'rb' ) as f: header = f.read( 2 )
    
    if header == 'BM':
        
        ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
        
        try:
            
            with open( path, 'rb' ) as f_source:
                
                with open( temp_path, 'wb' ) as f_dest:
                    
                    HydrusFileHandling.CopyFileLikeToFileLike( f_source, f_dest )
                    
                
            
            pil_image = GeneratePILImage( temp_path )
            
            pil_image.save( path, 'PNG' )
            
        finally:
            
            HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
def EfficientlyResizeNumpyImage( numpy_image, ( target_x, target_y ) ):
    
    ( im_y, im_x, depth ) = numpy_image.shape
    
    if target_x >= im_x and target_y >= im_y: return numpy_image
    
    result = numpy_image
    
    # this seems to slow things down a lot, at least for cv!
    #if im_x > 2 * target_x and im_y > 2 * target_y: result = cv2.resize( numpy_image, ( 2 * target_x, 2 * target_y ), interpolation = cv2.INTER_NEAREST )
    
    return cv2.resize( result, ( target_x, target_y ), interpolation = cv2.INTER_LINEAR )
    
def EfficientlyResizePILImage( pil_image, ( target_x, target_y ) ):
    
    ( im_x, im_y ) = pil_image.size
    
    if target_x >= im_x and target_y >= im_y: return pil_image
    
    #if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
    #    
    #    if im_x > 2 * target_x and im_y > 2 * target_y: pil_image.thumbnail( ( 2 * target_x, 2 * target_y ), PILImage.NEAREST )
    #    
    
    return pil_image.resize( ( target_x, target_y ), PILImage.ANTIALIAS )
    
def EfficientlyThumbnailNumpyImage( numpy_image, ( target_x, target_y ) ):
    
    ( im_y, im_x, depth ) = numpy_image.shape
    
    if target_x >= im_x and target_y >= im_y: return numpy_image
    
    ( target_x, target_y ) = GetThumbnailResolution( ( im_x, im_y ), ( target_x, target_y ) )
    
    return cv2.resize( numpy_image, ( target_x, target_y ), interpolation = cv2.INTER_AREA )
    
def EfficientlyThumbnailPILImage( pil_image, ( target_x, target_y ) ):
    
    ( im_x, im_y ) = pil_image.size
    
    #if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
    #    
    #    if im_x > 2 * target_x or im_y > 2 * target_y: pil_image.thumbnail( ( 2 * target_x, 2 * target_y ), PILImage.NEAREST )
    #    
    
    pil_image.thumbnail( ( target_x, target_y ), PILImage.ANTIALIAS )
    
def GenerateNumpyImage( path ):
    
    numpy_image = cv2.imread( path, flags = -1 ) # flags = -1 loads alpha channel, if present
    
    ( width, height, depth ) = numpy_image.shape
    
    if width * height * depth != len( numpy_image.data ): raise Exception( 'CV could not understand this image; it was probably an unusual png!' )
    
    if depth == 4: raise Exception( 'CV is bad at alpha!' )
    else: numpy_image = cv2.cvtColor( numpy_image, cv2.COLOR_BGR2RGB )
    
    return numpy_image
    
def GenerateNumPyImageFromPILImage( pil_image ):
    
    if pil_image.mode == 'RGBA' or ( pil_image.mode == 'P' and pil_image.info.has_key( 'transparency' ) ):
        
        if pil_image.mode == 'P': pil_image = pil_image.convert( 'RGBA' )
        
    else:
        
        if pil_image.mode != 'RGB': pil_image = pil_image.convert( 'RGB' )
        
    
    ( w, h ) = pil_image.size
    
    s = pil_image.tobytes()
    
    return numpy.fromstring( s, dtype = 'uint8' ).reshape( ( h, w, len( s ) // ( w * h ) ) )
    
def GeneratePerceptualHash( path ):
    
    numpy_image = cv2.imread( path, cv2.CV_LOAD_IMAGE_UNCHANGED )
    
    ( y, x, depth ) = numpy_image.shape
    
    if depth == 4:
        
        # create a white greyscale canvas
        
        white = numpy.ones( ( x, y ) ) * 255
        
        # create weight and transform numpy_image to greyscale
        
        numpy_alpha = numpy_image[ :, :, 3 ]
        
        numpy_image_bgr = numpy_image[ :, :, :3 ]
        
        numpy_image_gray = cv2.cvtColor( numpy_image_bgr, cv2.COLOR_BGR2GRAY )
        
        numpy_image_result = numpy.empty( ( y, x ), numpy.float32 )
        
        # paste greyscale onto the white
        
        # can't think of a better way to do this!
        # cv2.addWeighted only takes a scalar for weight!
        for i in range( y ):
            
            for j in range( x ):
                
                opacity = float( numpy_alpha[ i, j ] ) / 255.0
                
                grey_part = numpy_image_gray[ i, j ] * opacity
                white_part = 255 * ( 1 - opacity )
                
                pixel = grey_part + white_part
                
                numpy_image_result[ i, j ] = pixel
                
            
        
        numpy_image_gray = numpy_image_result
        
        # use 255 for white weight, alpha for image weight
        
    else:
        
        numpy_image_gray = cv2.cvtColor( numpy_image, cv2.COLOR_BGR2GRAY )
        
    
    numpy_image_tiny = cv2.resize( numpy_image_gray, ( 32, 32 ), interpolation = cv2.INTER_AREA )
    
    # convert to float and calc dct
    
    numpy_image_tiny_float = numpy.float32( numpy_image_tiny )
    
    dct = cv2.dct( numpy_image_tiny_float )
    
    # take top left 8x8 of dct
    
    dct_88 = dct[:8,:8]
    
    # get mean of dct, excluding [0,0]
    
    mask = numpy.ones( ( 8, 8 ) )
    
    mask[0,0] = 0
    
    average = numpy.average( dct_88, weights = mask )
    
    # make a monochromatic, 64-bit hash of whether the entry is above or below the mean
    
    bytes = []
    
    for i in range( 8 ):
        
        byte = 0
        
        for j in range( 8 ):
            
            byte <<= 1 # shift byte one left
            
            value = dct_88[i,j]
            
            if value > average: byte |= 1
            
        
        bytes.append( byte )
        
    
    answer = str( bytearray( bytes ) )
    
    # we good
    
    return answer
    
def GeneratePILImage( path ):
    
    pil_image = PILImage.open( path )
    
    if pil_image is None:
        
        raise Exception( 'The file at ' + path + ' could not be rendered!' )
        
    
    return pil_image
    
def GeneratePILImageFromNumpyImage( numpy_image ):
    
    ( h, w, depth ) = numpy_image.shape
    
    if depth == 3: format = 'RGB'
    elif depth == 4: format = 'RGBA'
    
    pil_image = PILImage.frombytes( format, ( w, h ), numpy_image.data )
    
    return pil_image
    
def GetGIFFrameDurations( path ):
    
    pil_image = GeneratePILImage( path )
    
    frame_durations = []
    
    i = 0
    
    while True:
        
        try: pil_image.seek( i )
        except: break
        
        if 'duration' not in pil_image.info:
            
            duration = 83 # Set a 12 fps default when duration is missing or too funky to extract. most stuff looks ok at this.
            
        else:
            
            duration = pil_image.info[ 'duration' ]
            
            # In the gif frame header, 10 is stored as 1ms. This 1 is commonly as utterly wrong as 0.
            if duration in ( 0, 10 ):
                
                duration = 80
                
            
        
        frame_durations.append( duration )
        
        i += 1
        
    
    return frame_durations
    
def GetImageProperties( path ):
    
    ( ( width, height ), num_frames ) = GetResolutionAndNumFrames( path )
    
    if num_frames > 1:
        
        durations = GetGIFFrameDurations( path )
        
        duration = sum( durations )
        
    else:
        
        duration = None
        num_frames = None
        
    
    return ( ( width, height ), duration, num_frames )
    
def GetResolutionAndNumFrames( path ):
    
    pil_image = GeneratePILImage( path )
    
    ( x, y ) = pil_image.size
    
    try:
        
        pil_image.seek( 1 )
        pil_image.seek( 0 )
        
        num_frames = 1
        
        while True:
            
            try:
                
                pil_image.seek( pil_image.tell() + 1 )
                num_frames += 1
                
            except: break
            
        
    except: num_frames = 1
    
    return ( ( x, y ), num_frames )
    
def GetThumbnailResolution( ( im_x, im_y ), ( target_x, target_y ) ):
    
    im_x = float( im_x )
    im_y = float( im_y )
    
    target_x = float( target_x )
    target_y = float( target_y )
    
    x_ratio = im_x / target_x
    y_ratio = im_y / target_y
    
    ratio_to_use = max( x_ratio, y_ratio )
    
    target_x = int( im_x / ratio_to_use )
    target_y = int( im_y / ratio_to_use )
    
    return ( target_x, target_y )
    