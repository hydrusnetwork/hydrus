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
import HydrusGlobals
import HydrusPaths

if cv2.__version__.startswith( '2' ):
    
    IMREAD_UNCHANGED = cv2.CV_LOAD_IMAGE_UNCHANGED
    
else:
    
    IMREAD_UNCHANGED = cv2.IMREAD_UNCHANGED
    
def ConvertToPngIfBmp( path ):
    
    with open( path, 'rb' ) as f: header = f.read( 2 )
    
    if header == 'BM':
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            with open( path, 'rb' ) as f_source:
                
                with open( temp_path, 'wb' ) as f_dest:
                    
                    HydrusPaths.CopyFileLikeToFileLike( f_source, f_dest )
                    
                
            
            pil_image = GeneratePILImage( temp_path )
            
            pil_image.save( path, 'PNG' )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
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
    
    numpy_image = cv2.imread( path, IMREAD_UNCHANGED )
    
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
    