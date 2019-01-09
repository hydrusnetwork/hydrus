from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusThreading
import os
from PIL import _imaging
from PIL import ImageFile as PILImageFile
from PIL import Image as PILImage
import shutil
import struct
import threading
import time
import traceback
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusPaths
import warnings

if hasattr( PILImageFile, 'LOAD_TRUNCATED_IMAGES' ):
    
    PILImageFile.LOAD_TRUNCATED_IMAGES = True
    
if not hasattr( PILImage, 'DecompressionBombWarning' ):
    
    # super old versions don't have this, so let's just make a stub, wew
    
    class DBW_stub( Exception ):
        
        pass
        
    
    PILImage.DecompressionBombWarning = DBW_stub
    

warnings.simplefilter( 'ignore', PILImage.DecompressionBombWarning )

OLD_PIL_MAX_IMAGE_PIXELS = PILImage.MAX_IMAGE_PIXELS
PILImage.MAX_IMAGE_PIXELS = None # this turns off decomp check entirely, wew

def ConvertToPngIfBmp( path ):
    
    with open( path, 'rb' ) as f:
        
        header = f.read( 2 )
        
    
    if header == b'BM':
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            with open( path, 'rb' ) as f_source:
                
                with open( temp_path, 'wb' ) as f_dest:
                    
                    HydrusPaths.CopyFileLikeToFileLike( f_source, f_dest )
                    
                
            
            pil_image = GeneratePILImage( temp_path )
            
            pil_image.save( path, 'PNG' )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
def Dequantize( pil_image ):
    
    if pil_image.mode not in ( 'RGBA', 'RGB' ):
        
        if pil_image.mode == 'LA' or ( pil_image.mode == 'P' and 'transparency' in pil_image.info ):
            
            pil_image = pil_image.convert( 'RGBA' )
            
        else:
            
            pil_image = pil_image.convert( 'RGB' )
            
        
    
    return pil_image
    
def EfficientlyResizePILImage( pil_image, target_resolution ):
    
    ( target_x, target_y ) = target_resolution
    ( im_x, im_y ) = pil_image.size
    
    if target_x >= im_x and target_y >= im_y: return pil_image
    
    #if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
    #    
    #    if im_x > 2 * target_x and im_y > 2 * target_y: pil_image.thumbnail( ( 2 * target_x, 2 * target_y ), PILImage.NEAREST )
    #    
    
    return pil_image.resize( ( target_x, target_y ), PILImage.ANTIALIAS )
    
def EfficientlyThumbnailPILImage( pil_image, target_resolution ):
    
    ( target_x, target_y ) = target_resolution
    ( im_x, im_y ) = pil_image.size
    
    #if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
    #    
    #    if im_x > 2 * target_x or im_y > 2 * target_y: pil_image.thumbnail( ( 2 * target_x, 2 * target_y ), PILImage.NEAREST )
    #    
    
    if im_x > target_x or im_y > target_y:
        
        pil_image.thumbnail( ( target_x, target_y ), PILImage.ANTIALIAS )
        
    
def GeneratePILImage( path ):
    
    fp = open( path, 'rb' )
    
    try:
        
        pil_image = PILImage.open( fp )
        
    except:
        
        # pil doesn't clean up its open file on exception, jej
        
        fp.close()
        
        raise
        
    
    if pil_image.format == 'JPEG' and hasattr( pil_image, '_getexif' ):
        
        try:
            
            exif_dict = pil_image._getexif()
            
        except:
            
            exif_dict = None
            
        
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
                    
                
            
        
    
    if pil_image is None:
        
        raise Exception( 'The file at ' + path + ' could not be rendered!' )
        
    
    return pil_image
    
def GeneratePILImageFromNumpyImage( numpy_image ):
    
    ( h, w, depth ) = numpy_image.shape
    
    if depth == 3:
        
        format = 'RGB'
        
    elif depth == 4:
        
        format = 'RGBA'
        
    
    pil_image = PILImage.frombytes( format, ( w, h ), numpy_image.data.tobytes() )
    
    return pil_image
    
def GetGIFFrameDurations( path ):
    
    pil_image = GeneratePILImage( path )
    
    frame_durations = []
    
    i = 0
    
    while True:
        
        try: pil_image.seek( i )
        except: break
        
        if 'duration' not in pil_image.info:
            
            duration = 83 # (83ms -- 1000 / 12) Set a 12 fps default when duration is missing or too funky to extract. most stuff looks ok at this.
            
        else:
            
            duration = pil_image.info[ 'duration' ]
            
            # In the gif frame header, 10 is stored as 1ms. This 1 is commonly as utterly wrong as 0.
            if duration in ( 0, 10 ):
                
                duration = 83
                
            
        
        frame_durations.append( duration )
        
        i += 1
        
    
    return frame_durations
    
def GetImageProperties( path, mime ):
    
    ( ( width, height ), num_frames ) = GetResolutionAndNumFrames( path, mime )
    
    if num_frames > 1:
        
        durations = GetGIFFrameDurations( path )
        
        duration = sum( durations )
        
    else:
        
        duration = None
        num_frames = None
        
    
    return ( ( width, height ), duration, num_frames )
    
def GetResolutionAndNumFrames( path, mime ):
    
    pil_image = GeneratePILImage( path )
    
    ( x, y ) = pil_image.size
    
    if mime == HC.IMAGE_GIF: # some jpegs came up with 2 frames and 'duration' because of some embedded thumbnail in the metadata
        
        try:
            
            pil_image.seek( 1 )
            pil_image.seek( 0 )
            
            num_frames = 1
            
            while True:
                
                try:
                    
                    pil_image.seek( pil_image.tell() + 1 )
                    num_frames += 1
                    
                except: break
                
            
        except:
            
            num_frames = 1
            
        
    else:
        
        num_frames = 1
        
    
    return ( ( x, y ), num_frames )
    
def GetThumbnailResolution( image_resolution, target_resolution ):
    
    ( im_x, im_y ) = image_resolution
    ( target_x, target_y ) = target_resolution
    
    if target_x >= im_x and target_y >= im_y:
        
        return ( im_x, im_y )
        
    
    x_ratio = im_x / target_x
    y_ratio = im_y / target_y
    
    if x_ratio > y_ratio:
        
        target_y = im_y / x_ratio
        
    elif y_ratio > x_ratio:
        
        target_x = im_x / y_ratio
        
    
    target_x = max( int( target_x ), 1 )
    target_y = max( int( target_y ), 1 )
    
    return ( target_x, target_y )
    
def IsDecompressionBomb( path ):
    
    PILImage.MAX_IMAGE_PIXELS = OLD_PIL_MAX_IMAGE_PIXELS
    
    warnings.simplefilter( 'error', PILImage.DecompressionBombWarning )
    
    try:
        
        GeneratePILImage( path )
        
    except ( PILImage.DecompressionBombWarning, PILImage.DecompressionBombError ):
        
        return True
        
    finally:
        
        PILImage.MAX_IMAGE_PIXELS = None
        
        warnings.simplefilter( 'ignore', PILImage.DecompressionBombWarning )
        
    
    return False
    
