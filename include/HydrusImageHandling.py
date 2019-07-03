from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusThreading
import io
import numpy
import numpy.core.multiarray # important this comes before cv!
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

PIL_ONLY_MIMETYPES = { HC.IMAGE_GIF, HC.IMAGE_ICON }

try:
    
    import cv2
    
    if cv2.__version__.startswith( '2' ):
        
        CV_IMREAD_FLAGS_SUPPORTS_ALPHA = cv2.CV_LOAD_IMAGE_UNCHANGED
        CV_IMREAD_FLAGS_SUPPORTS_EXIF_REORIENTATION = CV_IMREAD_FLAGS_SUPPORTS_ALPHA
        
        # there's something wrong with these, but I don't have an easy test env for it atm
        # CV_IMREAD_FLAGS_SUPPORTS_EXIF_REORIENTATION = cv2.CV_LOAD_IMAGE_ANYDEPTH | cv2.CV_LOAD_IMAGE_ANYCOLOR
        
        CV_JPEG_THUMBNAIL_ENCODE_PARAMS = []
        CV_PNG_THUMBNAIL_ENCODE_PARAMS = []
        
    else:
        
        CV_IMREAD_FLAGS_SUPPORTS_ALPHA = cv2.IMREAD_UNCHANGED
        CV_IMREAD_FLAGS_SUPPORTS_EXIF_REORIENTATION = cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR # this preserves colour info but does EXIF reorientation and flipping
        
        CV_JPEG_THUMBNAIL_ENCODE_PARAMS = [ cv2.IMWRITE_JPEG_QUALITY, 92 ]
        CV_PNG_THUMBNAIL_ENCODE_PARAMS = [ cv2.IMWRITE_PNG_COMPRESSION, 9 ]
        
    
    OPENCV_OK = True
    
except:
    
    OPENCV_OK = False
    

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
    
def GenerateNumPyImage( path, mime, force_pil = False ):
    
    if HG.media_load_report_mode:
        
        HydrusData.ShowText( 'Loading media: ' + path )
        
    
    if not OPENCV_OK:
        
        force_pil = True
        
    
    if mime in PIL_ONLY_MIMETYPES or force_pil:
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading with PIL' )
            
        
        pil_image = GeneratePILImage( path )
        
        numpy_image = GenerateNumPyImageFromPILImage( pil_image )
        
    else:
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading with OpenCV' )
            
        
        if mime == HC.IMAGE_JPEG:
            
            flags = CV_IMREAD_FLAGS_SUPPORTS_EXIF_REORIENTATION
            
        else:
            
            flags = CV_IMREAD_FLAGS_SUPPORTS_ALPHA
            
        
        numpy_image = cv2.imread( path, flags = flags )
        
        if numpy_image is None: # doesn't support static gifs and some random other stuff
            
            if HG.media_load_report_mode:
                
                HydrusData.ShowText( 'OpenCV Failed, loading with PIL' )
                
            
            pil_image = GeneratePILImage( path )
            
            numpy_image = GenerateNumPyImageFromPILImage( pil_image )
            
        else:
            
            if numpy_image.dtype == 'uint16':
                
                numpy_image //= 256
                
                numpy_image = numpy.array( numpy_image, dtype = 'uint8' )
                
            
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
    
def GenerateNumPyImageFromPILImage( pil_image ):
    
    pil_image = Dequantize( pil_image )
    
    ( w, h ) = pil_image.size
    
    s = pil_image.tobytes()
    
    return numpy.fromstring( s, dtype = 'uint8' ).reshape( ( h, w, len( s ) // ( w * h ) ) )
    
def GeneratePILImage( path ):
    
    try:
        
        pil_image = PILImage.open( path )
        
    except Exception as e:
        
        raise HydrusExceptions.MimeException( 'Could not load the image--it was likely malformed!' )
        
    
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
    
def GeneratePILImageFromNumPyImage( numpy_image ):
    
    ( h, w, depth ) = numpy_image.shape
    
    if depth == 3:
        
        format = 'RGB'
        
    elif depth == 4:
        
        format = 'RGBA'
        
    
    pil_image = PILImage.frombytes( format, ( w, h ), numpy_image.data.tobytes() )
    
    return pil_image
    
def GenerateThumbnailBytesFromStaticImagePath( path, target_resolution, mime ):
    
    if OPENCV_OK:
        
        numpy_image = GenerateNumPyImage( path, mime )
        
        thumbnail_numpy_image = ResizeNumPyImage( numpy_image, target_resolution )
        
        try:
            
            thumbnail_bytes = GenerateThumbnailBytesNumPy( thumbnail_numpy_image, mime )
            
            return thumbnail_bytes
            
        except HydrusExceptions.CantRenderWithCVException:
            
            pass # fall back to pil
            
        
    
    pil_image = GeneratePILImage( path )
    
    pil_image = Dequantize( pil_image )
    
    thumbnail_pil_image = pil_image.resize( target_resolution, PILImage.ANTIALIAS )
    
    thumbnail_bytes = GenerateThumbnailBytesPIL( pil_image, mime )
    
    return thumbnail_bytes
    
def GenerateThumbnailBytesNumPy( numpy_image, mime ):
    
    if not OPENCV_OK:
        
        pil_image = GeneratePILImageFromNumPyImage( numpy_image )
        
        return GenerateThumbnailBytesPIL( pil_image, mime )
        
    
    ( im_y, im_x, depth ) = numpy_image.shape
    
    if depth == 4:
        
        convert = cv2.COLOR_RGBA2BGRA
        
    else:
        
        convert = cv2.COLOR_RGB2BGR
        
    
    numpy_image = cv2.cvtColor( numpy_image, convert )
    
    if mime == HC.IMAGE_JPEG:
        
        ext = '.jpg'
        
        params = CV_JPEG_THUMBNAIL_ENCODE_PARAMS
        
    else:
        
        ext = '.png'
        
        params = CV_PNG_THUMBNAIL_ENCODE_PARAMS
        
    
    ( result_success, result_byte_array ) = cv2.imencode( ext, numpy_image, params )
    
    if result_success:
        
        thumbnail_bytes = result_byte_array.tostring()
        
        return thumbnail_bytes
        
    else:
        
        raise HydrusExceptions.CantRenderWithCVException( 'Thumb failed to encode!' )
        
    
def GenerateThumbnailBytesPIL( pil_image, mime ):
    
    f = io.BytesIO()
    
    pil_image = Dequantize( pil_image )
    
    if mime == HC.IMAGE_PNG or pil_image.mode == 'RGBA':
        
        pil_image.save( f, 'PNG' )
        
    else:
        
        pil_image.save( f, 'JPEG', quality = 92 )
        
    
    f.seek( 0 )
    
    thumbnail_bytes = f.read()
    
    f.close()
    
    return thumbnail_bytes
    
def GetGIFFrameDurations( path ):
    
    pil_image = GeneratePILImage( path )
    
    frame_durations = []
    
    i = 0
    
    while True:
        
        try:
            
            pil_image.seek( i )
            
        except:
            
            break
            
        
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
    
    if OPENCV_OK and mime not in PIL_ONLY_MIMETYPES: # webp here too maybe eventually, or offload it all to ffmpeg
        
        numpy_image = GenerateNumPyImage( path, mime )
        
        ( width, height ) = GetResolutionNumPy( numpy_image )
        
        duration = None
        num_frames = None
        
    else:
        
        ( ( width, height ), num_frames ) = GetResolutionAndNumFramesPIL( path, mime )
        
        if num_frames > 1:
            
            durations = GetGIFFrameDurations( path )
            
            duration = sum( durations )
            
        else:
            
            duration = None
            num_frames = None
            
        
    
    return ( ( width, height ), duration, num_frames )
    
# bigger number is worse quality
# this is very rough and misses some finesse
def GetJPEGQuantizationQualityEstimate( path ):
    
    pil_image = GeneratePILImage( path )
    
    if hasattr( pil_image, 'quantization' ):
        
        table_arrays = list( pil_image.quantization.values() )
        
        if len( table_arrays ) == 0:
            
            return ( 'unknown', None )
            
        
        quality = sum( ( sum( table_array ) for table_array in table_arrays ) )
        
        quality /= len( table_arrays )
        
        if quality >= 3400:
            
            label = 'very low'
            
        elif quality >= 2000:
            
            label = 'low'
            
        elif quality >= 1400:
            
            label = 'medium low'
            
        elif quality >= 1000:
            
            label = 'medium'
            
        elif quality >= 700:
            
            label = 'medium high'
            
        elif quality >= 400:
            
            label = 'high'
            
        elif quality >= 200:
            
            label = 'very high'
            
        else:
            
            label = 'extremely high'
            
        
        return ( label, quality )
        
    
    return ( 'unknown', None )
    
def GetPSDResolution( path ):
    
    with open( path, 'rb' ) as f:
        
        f.seek( 14 )
        
        height_bytes = f.read( 4 )
        width_bytes = f.read( 4 )
        
    
    height = struct.unpack( '>L', height_bytes )[0]
    width = struct.unpack( '>L', width_bytes )[0]
    
    return ( width, height )
    
def GetResolutionNumPy( numpy_image ):
    
    ( image_height, image_width, depth ) = numpy_image.shape
    
    return ( image_width, image_height )
    
def GetResolutionAndNumFramesPIL( path, mime ):
    
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
    
def GetThumbnailResolution( image_resolution, bounding_dimensions ):
    
    ( im_width, im_height ) = image_resolution
    ( bounding_width, bounding_height ) = bounding_dimensions
    
    if bounding_width >= im_width and bounding_height >= im_height:
        
        return ( im_width, im_height )
        
    
    width_ratio = im_width / bounding_width
    height_ratio = im_height / bounding_height
    
    thumbnail_width = bounding_width
    thumbnail_height = bounding_height
    
    if width_ratio > height_ratio:
        
        thumbnail_height = im_height / width_ratio
        
    elif height_ratio > width_ratio:
        
        thumbnail_width = im_width / height_ratio
        
    
    thumbnail_width = max( int( thumbnail_width ), 1 )
    thumbnail_height = max( int( thumbnail_height ), 1 )
    
    return ( thumbnail_width, thumbnail_height )
    
def IsDecompressionBomb( path ):
    
    # I boosted this up x2 as a temp test
    PILImage.MAX_IMAGE_PIXELS = OLD_PIL_MAX_IMAGE_PIXELS * 2
    
    warnings.simplefilter( 'error', PILImage.DecompressionBombWarning )
    
    try:
        
        GeneratePILImage( path )
        
    except ( PILImage.DecompressionBombWarning, PILImage.DecompressionBombError ):
        
        return True
        
    finally:
        
        PILImage.MAX_IMAGE_PIXELS = None
        
        warnings.simplefilter( 'ignore', PILImage.DecompressionBombWarning )
        
    
    return False
    
def ResizeNumPyImage( numpy_image, target_resolution ):
    
    ( target_width, target_height ) = target_resolution
    ( image_width, image_height ) = GetResolutionNumPy( numpy_image )
    
    if target_width == image_width and target_height == target_width:
        
        return numpy_image
        
    elif target_width > image_height or target_height > image_width:
        
        interpolation = cv2.INTER_LANCZOS4
        
    else:
        
        interpolation = cv2.INTER_AREA
        
    
    return cv2.resize( numpy_image, ( target_width, target_height ), interpolation = interpolation )
    
