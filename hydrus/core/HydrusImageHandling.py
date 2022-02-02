import hashlib
import io
import numpy
import numpy.core.multiarray # important this comes before cv!
import struct
import warnings

try:
    
    # more hidden imports for pyinstaller
    
    import numpy.random.common  # pylint: disable=E0401
    import numpy.random.bounded_integers  # pylint: disable=E0401
    import numpy.random.entropy  # pylint: disable=E0401
    
except:
    
    pass # old version of numpy, screw it
    

from PIL import _imaging
from PIL import ImageFile as PILImageFile
from PIL import Image as PILImage
from PIL import ImageCms as PILImageCms

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTemp

PIL_SRGB_PROFILE = PILImageCms.createProfile( 'sRGB' )

def EnableLoadTruncatedImages():
    
    if hasattr( PILImageFile, 'LOAD_TRUNCATED_IMAGES' ):
        
        # this can now cause load hangs due to the trunc load code adding infinite fake EOFs to the file stream, wew lad
        # hence debug only
        PILImageFile.LOAD_TRUNCATED_IMAGES = True
        
        return True
        
    else:
        
        return False
        
    
if not hasattr( PILImage, 'DecompressionBombError' ):
    
    # super old versions don't have this, so let's just make a stub, wew
    
    class DBE_stub( Exception ):
        
        pass
        
    
    PILImage.DecompressionBombError = DBE_stub
    
if not hasattr( PILImage, 'DecompressionBombWarning' ):
    
    # super old versions don't have this, so let's just make a stub, wew
    
    class DBW_stub( Exception ):
        
        pass
        
    
    PILImage.DecompressionBombWarning = DBW_stub
    
warnings.simplefilter( 'ignore', PILImage.DecompressionBombWarning )
warnings.simplefilter( 'ignore', PILImage.DecompressionBombError )

OLD_PIL_MAX_IMAGE_PIXELS = PILImage.MAX_IMAGE_PIXELS
PILImage.MAX_IMAGE_PIXELS = None # this turns off decomp check entirely, wew

PIL_ONLY_MIMETYPES = { HC.IMAGE_GIF, HC.IMAGE_ICON }

try:
    
    import cv2
    
    if cv2.__version__.startswith( '2' ):
        
        CV_IMREAD_FLAGS_PNG = cv2.CV_LOAD_IMAGE_UNCHANGED
        CV_IMREAD_FLAGS_JPEG = CV_IMREAD_FLAGS_PNG
        CV_IMREAD_FLAGS_WEIRD = CV_IMREAD_FLAGS_PNG
        
        CV_JPEG_THUMBNAIL_ENCODE_PARAMS = []
        CV_PNG_THUMBNAIL_ENCODE_PARAMS = []
        
    else:
        
        # allows alpha channel
        CV_IMREAD_FLAGS_PNG = cv2.IMREAD_UNCHANGED
        # this preserves colour info but does EXIF reorientation and flipping
        CV_IMREAD_FLAGS_JPEG = cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR
        # this seems to allow weirdass tiffs to load as non greyscale, although the LAB conversion 'whitepoint' or whatever can be wrong
        CV_IMREAD_FLAGS_WEIRD = cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR
        
        CV_JPEG_THUMBNAIL_ENCODE_PARAMS = [ cv2.IMWRITE_JPEG_QUALITY, 92 ]
        CV_PNG_THUMBNAIL_ENCODE_PARAMS = [ cv2.IMWRITE_PNG_COMPRESSION, 9 ]
        
    
    OPENCV_OK = True
    
except:
    
    OPENCV_OK = False
    
def MakeClipRectFit( image_resolution, clip_rect ):
    
    ( im_width, im_height ) = image_resolution
    ( x, y, clip_width, clip_height ) = clip_rect
    
    x = max( 0, x )
    y = max( 0, y )
    
    clip_width = min( clip_width, im_width )
    clip_height = min( clip_height, im_height )
    
    if x + clip_width > im_width:
        
        x = im_width - clip_width
        
    
    if y + clip_height > im_height:
        
        y = im_height - clip_height
        
    
    return ( x, y, clip_width, clip_height )
    
def ClipNumPyImage( numpy_image: numpy.array, clip_rect ):
    
    if len( numpy_image.shape ) == 3:
        
        ( im_height, im_width, depth ) = numpy_image.shape
        
    else:
        
        ( im_height, im_width ) = numpy_image.shape
        
    
    ( x, y, clip_width, clip_height ) = MakeClipRectFit( ( im_width, im_height ), clip_rect )
    
    return numpy_image[ y : y + clip_height, x : x + clip_width ]
    
def ClipPILImage( pil_image: PILImage.Image, clip_rect ):
    
    ( x, y, clip_width, clip_height ) = MakeClipRectFit( pil_image.size, clip_rect )
    
    return pil_image.crop( box = ( x, y, x + clip_width, y + clip_height ) )
    
def ConvertToPNGIfBMP( path ):
    
    with open( path, 'rb' ) as f:
        
        header = f.read( 2 )
        
    
    if header == b'BM':
        
        ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
        
        try:
            
            with open( path, 'rb' ) as f_source:
                
                with open( temp_path, 'wb' ) as f_dest:
                    
                    HydrusPaths.CopyFileLikeToFileLike( f_source, f_dest )
                    
                
            
            pil_image = GeneratePILImage( temp_path )
            
            pil_image.save( path, 'PNG' )
            
        finally:
            
            HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
def DequantizeNumPyImage( numpy_image: numpy.array ) -> numpy.array:
    
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
    
    if HasICCProfile( pil_image ):
        
        try:
            
            pil_image = NormaliseICCProfilePILImageToSRGB( pil_image )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            HydrusData.ShowText( 'Failed to normalise image ICC profile.' )
            
        
    
    pil_image = NormalisePILImageToRGB( pil_image )
    
    return pil_image
    
def GenerateNumPyImage( path, mime, force_pil = False ) -> numpy.array:
    
    if HG.media_load_report_mode:
        
        HydrusData.ShowText( 'Loading media: ' + path )
        
    
    if not OPENCV_OK:
        
        force_pil = True
        
    
    if not force_pil:
        
        try:
            
            pil_image = RawOpenPILImage( path )
            
            try:
                
                pil_image.verify()
                
            except:
                
                raise HydrusExceptions.UnsupportedFileException()
                
            
            # I and F are some sort of 32-bit monochrome or whatever, doesn't seem to work in PIL well, with or without ICC
            if pil_image.mode not in ( 'I', 'F' ):
                
                if pil_image.mode == 'LAB':
                    
                    force_pil = True
                    
                
                if HasICCProfile( pil_image ):
                    
                    if HG.media_load_report_mode:
                        
                        HydrusData.ShowText( 'Image has ICC, so switching to PIL' )
                        
                    
                    force_pil = True
                    
                
            
        except HydrusExceptions.UnsupportedFileException:
            
            # pil had trouble, let's cross our fingers cv can do it
            pass
            
        
    
    if mime in PIL_ONLY_MIMETYPES or force_pil:
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading with PIL' )
            
        
        pil_image = GeneratePILImage( path )
        
        numpy_image = GenerateNumPyImageFromPILImage( pil_image )
        
    else:
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading with OpenCV' )
            
        
        if mime == HC.IMAGE_JPEG:
            
            flags = CV_IMREAD_FLAGS_JPEG
            
        elif mime == HC.IMAGE_PNG:
            
            flags = CV_IMREAD_FLAGS_PNG
            
        else:
            
            flags = CV_IMREAD_FLAGS_WEIRD
            
        
        numpy_image = cv2.imread( path, flags = flags )
        
        if numpy_image is None: # doesn't support some random stuff
            
            if HG.media_load_report_mode:
                
                HydrusData.ShowText( 'OpenCV Failed, loading with PIL' )
                
            
            pil_image = GeneratePILImage( path )
            
            numpy_image = GenerateNumPyImageFromPILImage( pil_image )
            
        else:
            
            numpy_image = DequantizeNumPyImage( numpy_image )
            
        
    
    if NumPyImageHasOpaqueAlphaChannel( numpy_image ):
        
        convert = cv2.COLOR_RGBA2RGB
        
        numpy_image = cv2.cvtColor( numpy_image, convert )
        
    
    return numpy_image
    
def GenerateNumPyImageFromPILImage( pil_image: PILImage.Image ) -> numpy.array:
    
    ( w, h ) = pil_image.size
    
    try:
        
        s = pil_image.tobytes()
        
    except OSError as e: # e.g. OSError: unrecognized data stream contents when reading image file
        
        raise HydrusExceptions.UnsupportedFileException( str( e ) )
        
    
    depth = len( s ) // ( w * h )
    
    return numpy.fromstring( s, dtype = 'uint8' ).reshape( ( h, w, depth ) )
    
def GeneratePILImage( path, dequantize = True ) -> PILImage.Image:
    
    pil_image = RawOpenPILImage( path )
    
    if pil_image is None:
        
        raise Exception( 'The file at {} could not be rendered!'.format( path ) )
        
    
    RotateEXIFPILImage( pil_image )
    
    if dequantize:
        
        # note this destroys animated gifs atm, it collapses down to one frame
        pil_image = DequantizePILImage( pil_image )
        
    
    return pil_image
    
def GeneratePILImageFromNumPyImage( numpy_image: numpy.array ) -> PILImage.Image:
    
    # I'll leave this here as a neat artifact, but I really shouldn't ever be making a PIL from a cv2 image. the only PIL benefits are the .info dict, which this won't generate
    
    if len( numpy_image.shape ) == 2:
        
        ( h, w ) = numpy_image.shape
        
        format = 'L'
        
    else:
        
        ( h, w, depth ) = numpy_image.shape
        
        if depth == 1:
            
            format = 'L'
            
        elif depth == 2:
            
            format = 'LA'
            
        elif depth == 3:
            
            format = 'RGB'
            
        elif depth == 4:
            
            format = 'RGBA'
            
        
    
    pil_image = PILImage.frombytes( format, ( w, h ), numpy_image.data.tobytes() )
    
    return pil_image
    
def GenerateThumbnailBytesFromStaticImagePath( path, target_resolution, mime, clip_rect = None ) -> bytes:
    
    if OPENCV_OK:
        
        numpy_image = GenerateNumPyImage( path, mime )
        
        if clip_rect is not None:
            
            numpy_image = ClipNumPyImage( numpy_image, clip_rect )
            
        
        thumbnail_numpy_image = ResizeNumPyImage( numpy_image, target_resolution )
        
        try:
            
            thumbnail_bytes = GenerateThumbnailBytesNumPy( thumbnail_numpy_image, mime )
            
            return thumbnail_bytes
            
        except HydrusExceptions.CantRenderWithCVException:
            
            pass # fallback to PIL
            
        
    
    pil_image = GeneratePILImage( path )
    
    if clip_rect is None:
        
        pil_image = ClipPILImage( pil_image, clip_rect )
        
    
    thumbnail_pil_image = pil_image.resize( target_resolution, PILImage.ANTIALIAS )
    
    thumbnail_bytes = GenerateThumbnailBytesPIL( pil_image, mime )
    
    return thumbnail_bytes
    
def GenerateThumbnailBytesNumPy( numpy_image, mime ) -> bytes:
    
    ( im_height, im_width, depth ) = numpy_image.shape
    
    if depth == 4:
        
        convert = cv2.COLOR_RGBA2BGRA
        
    else:
        
        convert = cv2.COLOR_RGB2BGR
        
    
    numpy_image = cv2.cvtColor( numpy_image, convert )
    
    if mime == HC.IMAGE_PNG or depth == 4:
        
        ext = '.png'
        
        params = CV_PNG_THUMBNAIL_ENCODE_PARAMS
        
    else:
        
        ext = '.jpg'
        
        params = CV_JPEG_THUMBNAIL_ENCODE_PARAMS
        
    
    ( result_success, result_byte_array ) = cv2.imencode( ext, numpy_image, params )
    
    if result_success:
        
        thumbnail_bytes = result_byte_array.tostring()
        
        return thumbnail_bytes
        
    else:
        
        raise HydrusExceptions.CantRenderWithCVException( 'Thumb failed to encode!' )
        
    
def GenerateThumbnailBytesPIL( pil_image: PILImage.Image, mime ) -> bytes:
    
    f = io.BytesIO()
    
    if mime == HC.IMAGE_PNG or pil_image.mode == 'RGBA':
        
        pil_image.save( f, 'PNG' )
        
    else:
        
        pil_image.save( f, 'JPEG', quality = 92 )
        
    
    f.seek( 0 )
    
    thumbnail_bytes = f.read()
    
    f.close()
    
    return thumbnail_bytes
    
def GetGIFFrameDurations( path ):
    
    pil_image = RawOpenPILImage( path )
    
    times_to_play_gif = GetTimesToPlayGIFFromPIL( pil_image )
    
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
        
    
    return ( frame_durations, times_to_play_gif )
    
def GetICCProfileBytes( pil_image: PILImage.Image ) -> bytes:
    
    if HasICCProfile( pil_image ):
        
        return pil_image.info[ 'icc_profile' ]
        
    
    raise HydrusExceptions.DataMissing( 'This image has no ICC profile!' )
    
def GetImagePixelHash( path, mime ) -> bytes:
    
    numpy_image = GenerateNumPyImage( path, mime )
    
    return hashlib.sha256( numpy_image.data.tobytes() ).digest()
    
def GetImageProperties( path, mime ):
    
    if OPENCV_OK and mime not in PIL_ONLY_MIMETYPES: # webp here too maybe eventually, or offload it all to ffmpeg
        
        numpy_image = GenerateNumPyImage( path, mime )
        
        ( width, height ) = GetResolutionNumPy( numpy_image )
        
        duration = None
        num_frames = None
        
    else:
        
        ( ( width, height ), num_frames ) = GetResolutionAndNumFramesPIL( path, mime )
        
        if num_frames > 1:
            
            ( durations, times_to_play_gif ) = GetGIFFrameDurations( path )
            
            duration = sum( durations )
            
        else:
            
            duration = None
            num_frames = None
            
        
    
    return ( ( width, height ), duration, num_frames )
    
# bigger number is worse quality
# this is very rough and misses some finesse
def GetJPEGQuantizationQualityEstimate( path ):
    
    try:
        
        pil_image = RawOpenPILImage( path )
        
    except HydrusExceptions.UnsupportedFileException:
        
        return ( 'unknown', None )
        
    
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
    
    pil_image = GeneratePILImage( path, dequantize = False )
    
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
                    
                except:
                    
                    break
                    
                
            
        except:
            
            num_frames = 1
            
        
    else:
        
        num_frames = 1
        
    
    return ( ( x, y ), num_frames )
    
THUMBNAIL_SCALE_DOWN_ONLY = 0
THUMBNAIL_SCALE_TO_FIT = 1
THUMBNAIL_SCALE_TO_FILL = 2

thumbnail_scale_str_lookup = {
    THUMBNAIL_SCALE_DOWN_ONLY : 'scale down only',
    THUMBNAIL_SCALE_TO_FIT : 'scale to fit',
    THUMBNAIL_SCALE_TO_FILL : 'scale to fill'
}

def GetThumbnailResolutionAndClipRegion( image_resolution, bounding_dimensions, thumbnail_scale_type: int ):
    
    clip_rect = None
    
    ( im_width, im_height ) = image_resolution
    ( bounding_width, bounding_height ) = bounding_dimensions
    
    if thumbnail_scale_type == THUMBNAIL_SCALE_DOWN_ONLY:
        
        if bounding_width >= im_width and bounding_height >= im_height:
            
            return ( clip_rect, ( im_width, im_height ) )
            
        
    
    width_ratio = im_width / bounding_width
    height_ratio = im_height / bounding_height
    
    thumbnail_width = bounding_width
    thumbnail_height = bounding_height
    
    if thumbnail_scale_type in ( THUMBNAIL_SCALE_DOWN_ONLY, THUMBNAIL_SCALE_TO_FIT ):
        
        if width_ratio > height_ratio:
            
            thumbnail_height = im_height / width_ratio
            
        elif height_ratio > width_ratio:
            
            thumbnail_width = im_width / height_ratio
            
        
    elif thumbnail_scale_type == THUMBNAIL_SCALE_TO_FILL:
        
        if width_ratio == height_ratio:
            
            # we have something that fits bounding region perfectly, no clip region required
            
            pass
            
        else:
            
            clip_x = 0
            clip_y = 0
            clip_width = im_width
            clip_height = im_height
            
            if width_ratio > height_ratio:
                
                clip_width = max( int( im_width * height_ratio / width_ratio ), 1 )
                clip_x = ( im_width - clip_width ) // 2
                
            elif height_ratio > width_ratio:
                
                clip_height = max( int( im_height * width_ratio / height_ratio ), 1 )
                clip_y = ( im_height - clip_height ) // 2
                
            
            clip_rect = ( clip_x, clip_y, clip_width, clip_height )
            
        
    
    thumbnail_width = max( int( thumbnail_width ), 1 )
    thumbnail_height = max( int( thumbnail_height ), 1 )
    
    return ( clip_rect, ( thumbnail_width, thumbnail_height ) )
    
def GetTimesToPlayGIF( path ) -> int:
    
    try:
        
        pil_image = RawOpenPILImage( path )
        
    except HydrusExceptions.UnsupportedFileException:
        
        return 1
        
    
    return GetTimesToPlayGIFFromPIL( pil_image )
    
def GetTimesToPlayGIFFromPIL( pil_image: PILImage.Image ) -> int:
    
    if 'loop' in pil_image.info:
        
        times_to_play_gif = pil_image.info[ 'loop' ]
        
    else:
        
        times_to_play_gif = 1
        
    
    return times_to_play_gif
    
def HasICCProfile( pil_image: PILImage.Image ) -> bool:
    
    if 'icc_profile' in pil_image.info:
        
        icc_profile = pil_image.info[ 'icc_profile' ]
        
        if isinstance( icc_profile, bytes ) and len( icc_profile ) > 0:
            
            return True
            
        
    
    return False
    
def IsDecompressionBomb( path ) -> bool:
    
    # there are two errors here, the 'Warning' and the 'Error', which atm is just a test vs a test x 2 for number of pixels
    # 256MB bmp by default, ( 1024 ** 3 ) // 4 // 3
    # we'll set it at 512MB, and now catching error should be about 1GB
    
    PILImage.MAX_IMAGE_PIXELS = ( 512 * ( 1024 ** 2 ) ) // 3
    
    warnings.simplefilter( 'error', PILImage.DecompressionBombError )
    
    try:
        
        RawOpenPILImage( path )
        
    except ( PILImage.DecompressionBombError ):
        
        return True
        
    except:
        
        # pil was unable to load it, which does not mean it was a decomp bomb
        return False
        
    finally:
        
        PILImage.MAX_IMAGE_PIXELS = None
        
        warnings.simplefilter( 'ignore', PILImage.DecompressionBombError )
        
    
    return False
    
def NormaliseICCProfilePILImageToSRGB( pil_image: PILImage.Image ):
    
    try:
        
        icc_profile_bytes = GetICCProfileBytes( pil_image )
        
    except HydrusExceptions.DataMissing:
        
        return pil_image
        
    
    try:
        
        f = io.BytesIO( icc_profile_bytes )
        
        src_profile = PILImageCms.ImageCmsProfile( f )
        
        if pil_image.mode in ( 'L', 'LA' ):
            
            # had a bunch of LA pngs that turned pure white on RGBA ICC conversion
            # but seem to work fine if keep colourspace the same for now
            # it is a mystery, I guess a PIL bug, but presumably L and LA are technically sRGB so it is still ok to this
            
            outputMode = pil_image.mode
            
        else:
            
            if PILImageHasAlpha( pil_image ):
                
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
        
    
    pil_image = NormalisePILImageToRGB( pil_image )
    
    return pil_image
    
def NormalisePILImageToRGB( pil_image: PILImage.Image ):
    
    if PILImageHasAlpha( pil_image ):
        
        desired_mode = 'RGBA'
        
    else:
        
        desired_mode = 'RGB'
        
    
    if pil_image.mode != desired_mode:
        
        if pil_image.mode == 'LAB':
            
            pil_image = PILImageCms.profileToProfile( pil_image, PILImageCms.createProfile( 'LAB' ), PIL_SRGB_PROFILE, outputMode = 'RGB' )
            
        else:
            
            pil_image = pil_image.convert( desired_mode )
            
        
    
    return pil_image
    
def NumPyImageHasOpaqueAlphaChannel( numpy_image: numpy.array ):
    
    shape = numpy_image.shape
    
    if len( shape ) == 2:
        
        return False
        
    
    if shape[2] == 4:
        
        # RGBA image
        # if the alpha channel is all opaque, there is no use storing that info in our pixel hash
        # opaque means 255
        
        alpha_channel = numpy_image[:,:,3]
        
        if ( alpha_channel == numpy.full( ( shape[0], shape[1] ), 255, dtype = 'uint8' ) ).all():
            
            return True
            
        
    
    return False
    
def PILImageHasAlpha( pil_image: PILImage.Image ):
    
    return pil_image.mode in ( 'LA', 'RGBA' ) or ( pil_image.mode == 'P' and 'transparency' in pil_image.info )
    
def RawOpenPILImage( path ) -> PILImage.Image:
    
    try:
        
        pil_image = PILImage.open( path )
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not load the image--it was likely malformed!' )
        
    
    return pil_image
    
def ResizeNumPyImage( numpy_image: numpy.array, target_resolution ) -> numpy.array:
    
    ( target_width, target_height ) = target_resolution
    ( image_width, image_height ) = GetResolutionNumPy( numpy_image )
    
    if target_width == image_width and target_height == target_width:
        
        return numpy_image
        
    elif target_width > image_height or target_height > image_width:
        
        interpolation = cv2.INTER_LANCZOS4
        
    else:
        
        interpolation = cv2.INTER_AREA
        
    
    return cv2.resize( numpy_image, ( target_width, target_height ), interpolation = interpolation )
    
def RotateEXIFPILImage( pil_image: PILImage.Image ):
    
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
                    
                
            
        
    
    return pil_image
    
