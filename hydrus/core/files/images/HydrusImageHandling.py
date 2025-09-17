# noinspection PyUnresolvedReferences
from hydrus.core.files.images import HydrusImageInit # right up top

import numpy
import numpy.core.multiarray # important this comes before cv!

import cv2
import hashlib
import io
import typing
import warnings

from PIL import features as PILFeatures
from PIL import ImageFile as PILImageFile
from PIL import Image as PILImage
from PIL import ImageOps as PILImageOps

from hydrus.core import HydrusData

with warnings.catch_warnings():
    
    warnings.simplefilter( 'ignore', UserWarning )
    
    PIL_HAS_HEIF = PILFeatures.check( 'heif' )
    

HEIF_PLUGIN_OK = False

if not PIL_HAS_HEIF:
    
    try:
        
        # TODO: clean up this import mess
        
        from pillow_heif import register_heif_opener
        
        register_heif_opener(thumbnails=False)
        
        try:
            
            import pillow_heif.options
            
            pillow_heif.options.DISABLE_SECURITY_LIMITS = True # no 512MB/768MB bitmap limit for file loading
            
        except:
            
            pass
            
        
        HEIF_PLUGIN_OK = True
        
    except:
        
        HydrusData.Print( 'Could not register HEIF Opener with plugin library.' )
        
    

HEIF_OK = PIL_HAS_HEIF or HEIF_PLUGIN_OK

with warnings.catch_warnings():
    
    warnings.simplefilter( 'ignore', UserWarning )
    
    # should be true as of PIL 11.3
    PIL_HAS_AVIF = PILFeatures.check( 'avif' )
    

AVIF_PLUGIN_OK = False
AVIF_BACKUP_PLUGIN_OK = False

if not PIL_HAS_AVIF:
    
    try:
        
        import pillow_avif
        
        AVIF_PLUGIN_OK = True
        
    except:
        
        try:
            
            import pillow_heif
            
            if hasattr( pillow_heif, 'register_avif_opener' ):
                
                try:
                    
                    # noinspection PyUnresolvedReferences
                    from pillow_heif import register_avif_opener
                    
                    register_avif_opener(thumbnails=False) # this is now deprecated 2024-04, pillow_heif 0.22.0
                    
                    AVIF_BACKUP_PLUGIN_OK = True
                    
                    HydrusData.Print( 'AVIF Opener registered with legacy library.' )
                    
                except:
                    
                    HydrusData.Print( 'Could not register AVIF Opener with main or legacy library.' )
                    
                
            
        except:
            
            HydrusData.Print( 'Could not register AVIF Opener with main or legacy plugin library.' )
            
        
    

AVIF_OK = PIL_HAS_AVIF or AVIF_PLUGIN_OK or AVIF_BACKUP_PLUGIN_OK

with warnings.catch_warnings():
    
    warnings.simplefilter( 'ignore', UserWarning )
    
    PIL_HAS_JXL = PILFeatures.check( 'jpegxl' )
    

JXL_PLUGIN_OK = False

if not PIL_HAS_JXL:
    
    try:
        
        import pillow_jxl
        
        JXL_PLUGIN_OK = True
        
        JXL_ERROR_TEXT = 'Jpeg-XL seems fine!'
        
    except Exception as e:
        
        import traceback
        
        JXL_ERROR_TEXT = traceback.format_exc()
        
    

JXL_OK = PIL_HAS_JXL or JXL_PLUGIN_OK

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core.files import HydrusKritaHandling
from hydrus.core.files import HydrusPSDHandling
from hydrus.core.files.images import HydrusImageColours
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageNormalisation
from hydrus.core.files.images import HydrusImageOpening

def SetEnableLoadTruncatedImages( value: bool ):
    
    if hasattr( PILImageFile, 'LOAD_TRUNCATED_IMAGES' ):
        
        if PILImageFile.LOAD_TRUNCATED_IMAGES != value:
            
            # this has previously caused load hangs due to the trunc load code adding infinite fake EOFs to the file stream, wew lad
            PILImageFile.LOAD_TRUNCATED_IMAGES = value
            
            HG.controller.pub( 'clear_image_cache' )
            HG.controller.pub( 'clear_image_tile_cache' )
            
        
        return True
        
    else:
        
        try:
            
            import PIL
            
            HydrusData.Print( f'Could not set the PIL image trunctation value to {value}--perhaps this version of PIL ({PIL.__version__})does not support it?' )
            
        except:
            
            HydrusData.Print( f'Could not set the PIL image trunctation value to {value}, and could not determine the PIL version! Something is busted!' )
            
        
        return False
        
    

OLD_PIL_MAX_IMAGE_PIXELS = PILImage.MAX_IMAGE_PIXELS
PILImage.MAX_IMAGE_PIXELS = None # this turns off decomp check entirely, wew

# allows alpha channel
CV_IMREAD_FLAGS_PNG = cv2.IMREAD_UNCHANGED
# this preserves colour info but does EXIF reorientation and flipping
CV_IMREAD_FLAGS_JPEG = cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR
# this seems to allow weirdass tiffs to load as non greyscale, although the LAB conversion 'whitepoint' or whatever can be wrong
CV_IMREAD_FLAGS_WEIRD = CV_IMREAD_FLAGS_PNG

CV_JPEG_THUMBNAIL_ENCODE_PARAMS = [ cv2.IMWRITE_JPEG_QUALITY, 92 ]
CV_PNG_THUMBNAIL_ENCODE_PARAMS = [ cv2.IMWRITE_PNG_COMPRESSION, 9 ]

PIL_ONLY_MIMETYPES = { HC.ANIMATION_GIF, HC.IMAGE_ICON, HC.IMAGE_WEBP, HC.IMAGE_QOI, HC.IMAGE_BMP, HC.ANIMATION_WEBP, HC.IMAGE_JXL, HC.IMAGE_AVIF }.union( HC.PIL_HEIF_MIMES )

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
    
def ClipNumPyImage( numpy_image: numpy.ndarray, clip_rect ):
    
    if len( numpy_image.shape ) == 3:
        
        ( im_height, im_width, depth ) = numpy_image.shape
        
    else:
        
        ( im_height, im_width ) = numpy_image.shape
        
    
    ( x, y, clip_width, clip_height ) = MakeClipRectFit( ( im_width, im_height ), clip_rect )
    
    return numpy_image[ y : y + clip_height, x : x + clip_width ]
    

def ClipPILImage( pil_image: PILImage.Image, clip_rect ):
    
    ( x, y, clip_width, clip_height ) = MakeClipRectFit( pil_image.size, clip_rect )
    
    return pil_image.crop( box = ( x, y, x + clip_width, y + clip_height ) )
    

FORCE_PIL_ALWAYS = True

def GenerateNumPyImage( path, mime, force_pil = False, human_file_description = None ) -> numpy.ndarray:
    
    force_pil = force_pil or FORCE_PIL_ALWAYS
    
    if HG.media_load_report_mode:
        
        HydrusData.ShowText( 'Loading media: ' + path )
        
    
    if mime == HC.APPLICATION_PSD:
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading PSD' )
            
        
        pil_image = HydrusPSDHandling.GeneratePILImageFromPSD( path )
        
        return GenerateNumPyImageFromPILImage( pil_image )
        
    
    if mime == HC.APPLICATION_KRITA:
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading KRA' )
            
        
        pil_image = HydrusKritaHandling.MergedPILImageFromKra( path )
        
        return GenerateNumPyImageFromPILImage( pil_image )
        
    
    if mime in PIL_ONLY_MIMETYPES:
        
        force_pil = True
        
    
    if not force_pil:
        
        pil_image = HydrusImageOpening.RawOpenPILImage( path, human_file_description = human_file_description )
        
        if pil_image.mode == 'LAB':
            
            force_pil = True
            
        
        if HydrusImageMetadata.HasICCProfile( pil_image ):
            
            if HG.media_load_report_mode:
                
                HydrusData.ShowText( 'Image has ICC, so switching to PIL' )
                
            
            force_pil = True
            
        
    
    if force_pil:
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading with PIL' )
            
        
        pil_image = GeneratePILImage( path )
        
        numpy_image = GenerateNumPyImageFromPILImage( pil_image )
        
    else:
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading with OpenCV' )
            
        
        if mime in ( HC.IMAGE_JPEG, HC.IMAGE_TIFF ):
            
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
            
            numpy_image = HydrusImageNormalisation.DequantizeFreshlyLoadedNumPyImage( numpy_image )
            
            numpy_image = HydrusImageNormalisation.StripOutAnyUselessAlphaChannel( numpy_image )
            
        
    
    return numpy_image
    
def GenerateNumPyImageFromPILImage( pil_image: PILImage.Image, strip_useless_alpha = True ) -> numpy.ndarray:
    
    try:
        
        # this seems to magically work, I guess asarray either has a match for Image or Image provides some common shape/datatype properties that it can hook into
        numpy_image = numpy.asarray( pil_image )
        
    except IOError:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Looks like a truncated file that PIL could not handle!' )
        
    
    if numpy_image.shape == ():
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Looks like a weird truncated file!' )
        
    
    if strip_useless_alpha:
        
        numpy_image = HydrusImageNormalisation.StripOutAnyUselessAlphaChannel( numpy_image )
        
    
    return numpy_image
    

def GeneratePILImage( path: typing.Union[ str, typing.BinaryIO ], dequantize = True, human_file_description = None ) -> PILImage.Image:
    
    pil_image = HydrusImageOpening.RawOpenPILImage( path, human_file_description = human_file_description )
    
    try:
        
        pil_image = HydrusImageNormalisation.RotateEXIFPILImage( pil_image )
        
        if dequantize:
            
            if pil_image.mode in ( 'I', 'I;16', 'I;16L', 'I;16B', 'I;16N', 'F' ):
                
                # 'I' = greyscale, uint16
                # 'F' = float, np.float32
                
                # calling "pil_image.convert( 'L' )" and similar on an I doesn't seem to normalise the intensity, it just blows out the image crazy???
                # so we'll hack it ourselves. these are so rare it is fine if we are a bit weird and lose the extra metadata
                
                numpy_image = GenerateNumPyImageFromPILImage( pil_image )
                
                numpy_image = HydrusImageNormalisation.NormaliseNumPyImageToUInt8( numpy_image )
                
                pil_image = GeneratePILImageFromNumPyImage( numpy_image )
                
            
            # note this destroys animated gifs atm, it collapses down to one frame
            pil_image = HydrusImageNormalisation.DequantizePILImage( pil_image )
            
        
        return pil_image
        
    except IOError:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Looks like a truncated file that PIL could not handle!' )
        
    

def GeneratePILImageFromNumPyImage( numpy_image: numpy.ndarray ) -> PILImage.Image:
    
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
    

def GenerateFileBytesNumPy( numpy_image, ext: str = '.png', params: typing.Optional[ list[ int ] ] = None ) -> bytes:
    
    if params is None:
        
        params = []
        
    
    if len( numpy_image.shape ) == 2:
        
        convert = cv2.COLOR_GRAY2RGB
        
    else:
        
        ( im_height, im_width, depth ) = numpy_image.shape
                
        if depth == 4:
            
            convert = cv2.COLOR_RGBA2BGRA
            
        else:
            
            convert = cv2.COLOR_RGB2BGR
            
        
    
    numpy_image = cv2.cvtColor( numpy_image, convert )
    
    ( result_success, result_byte_array ) = cv2.imencode( ext, numpy_image, params )
    
    if result_success:
        
        # noinspection PyUnresolvedReferences
        return result_byte_array.tobytes()
        
    else:
        
        raise HydrusExceptions.CantRenderWithCVException( 'Image failed to encode!' )
        
    

def GenerateFileBytesForRenderAPI( numpy_image, format: int, quality: int ):
    
    ext = HC.mime_ext_lookup[format]
    
    params = []
    
    if format == HC.IMAGE_PNG:
        
        params = [ cv2.IMWRITE_PNG_COMPRESSION, quality ]
        
    elif format == HC.IMAGE_JPEG:
        
        params = [ cv2.IMWRITE_JPEG_QUALITY, quality, cv2.IMWRITE_JPEG_PROGRESSIVE, 1 ]
        
    elif format == HC.IMAGE_WEBP:
        
        params = [ cv2.IMWRITE_WEBP_QUALITY, quality ]
        
    
    return GenerateFileBytesNumPy( numpy_image, ext, params )
    

def GenerateThumbnailNumPyFromStaticImagePath( path, target_resolution, mime ):
    
    numpy_image = GenerateNumPyImage( path, mime )
    
    thumbnail_numpy_image = ResizeNumPyImage( numpy_image, target_resolution )
    
    return thumbnail_numpy_image
    

def GenerateThumbnailBytesFromNumPy( numpy_image ) -> bytes:
    
    if len( numpy_image.shape ) == 2:
        
        depth = 3
        
    else:
        
        ( im_height, im_width, depth ) = numpy_image.shape
        
    
    if depth == 4:
        
        ext = '.png'
        
        params = CV_PNG_THUMBNAIL_ENCODE_PARAMS
        
    else:
        
        ext = '.jpg'
        
        params = CV_JPEG_THUMBNAIL_ENCODE_PARAMS
        
    
    return GenerateFileBytesNumPy(numpy_image, ext, params)
    

def GenerateThumbnailBytesFromPIL( pil_image: PILImage.Image ) -> bytes:
    
    f = io.BytesIO()
    
    if HydrusImageColours.PILImageHasTransparency( pil_image ):
        
        pil_image.save( f, 'PNG' )
        
    else:
        
        pil_image.save( f, 'JPEG', quality = 92 )
        
    
    f.seek( 0 )
    
    thumbnail_bytes = f.read()
    
    f.close()
    
    return thumbnail_bytes
    


def GetImagePixelHash( path, mime ) -> bytes:
    
    numpy_image = GenerateNumPyImage( path, mime )
    
    return GetImagePixelHashNumPy( numpy_image )
    

def GetImagePixelHashNumPy( numpy_image ):
    
    # Yo, this does not take dimensions into account! flat colour images of differing dimensions but same num_pixels have the same hash!
    # same for some carefully designed checkerboard patterns etc..
    # _at some point_ we could change this and force a regen for all files, I guess
    # don't do a 'newline at end of every line', since there may be other strange collisions. do 'encode big int width/height at start of pixel hash'
    # is there anything else we want to encode?
    return hashlib.sha256( numpy_image.data.tobytes() ).digest()
    

def GetImageResolution( path, mime ):
    
    # PIL first here, rather than numpy, as it loads image headers real quick
    try:
        
        pil_image = GeneratePILImage( path, dequantize = False )
        
        ( width, height ) = pil_image.size
        
    except HydrusExceptions.DamagedOrUnusualFileException:
        
        # desperate situation
        numpy_image = GenerateNumPyImage( path, mime )
        
        if len( numpy_image.shape ) == 3:
            
            ( height, width, depth ) = numpy_image.shape
            
        else:
            
            ( height, width ) = numpy_image.shape
            
        
    
    width = max( width, 1 )
    height = max( height, 1 )
    
    return ( width, height )
    

def GetResolutionNumPy( numpy_image ):
    
    ( image_height, image_width, depth ) = numpy_image.shape
    
    return ( image_width, image_height )
    

THUMBNAIL_SCALE_DOWN_ONLY = 0
THUMBNAIL_SCALE_TO_FIT = 1
THUMBNAIL_SCALE_TO_FILL = 2

thumbnail_scale_str_lookup = {
    THUMBNAIL_SCALE_DOWN_ONLY : 'scale down only',
    THUMBNAIL_SCALE_TO_FIT : 'scale to fit',
    THUMBNAIL_SCALE_TO_FILL : 'scale to fill'
}

def GetThumbnailResolution( image_resolution: tuple[ int, int ], bounding_dimensions: tuple[ int, int ], thumbnail_scale_type: int, thumbnail_dpr_percent: int ) -> tuple[ int, int ]:
    
    ( im_width, im_height ) = image_resolution
    ( bounding_width, bounding_height ) = bounding_dimensions
    
    if thumbnail_dpr_percent != 100:
        
        thumbnail_dpr = thumbnail_dpr_percent / 100
        
        bounding_height = int( bounding_height * thumbnail_dpr )
        bounding_width = int( bounding_width * thumbnail_dpr )
        
    
    # this is appropriate for the crazy (0x0) svg or whatever we have, since we will _try_ to render it properly later on
    # but if it fails to render, we'll still get a fairly nice filetype.png or hydrus.png fallback
    # we don't want to pass around 0x0 and have a handler everywhere
    if im_width is None or im_width == 0 or im_height is None or im_height == 0:
        
        im_width = bounding_width
        im_height = bounding_width
        
    
    # TODO SVG thumbs should always scale up to the bounding dimensions
    
    if thumbnail_scale_type == THUMBNAIL_SCALE_DOWN_ONLY:
        
        if bounding_width >= im_width and bounding_height >= im_height:
            
            return ( im_width, im_height )
            
        
    
    image_ratio = im_width / im_height
    
    width_ratio = im_width / bounding_width
    height_ratio = im_height / bounding_height
    
    image_is_wider_than_bounding_box = width_ratio > height_ratio
    image_is_taller_than_bounding_box = height_ratio > width_ratio
    
    thumbnail_width = bounding_width
    thumbnail_height = bounding_height
    
    if thumbnail_scale_type in ( THUMBNAIL_SCALE_DOWN_ONLY, THUMBNAIL_SCALE_TO_FIT ):
        
        if image_is_taller_than_bounding_box: # i.e. the height will be at bounding height
            
            thumbnail_width = im_width / height_ratio
            
        elif image_is_wider_than_bounding_box: # i.e. the width will be at bounding width
            
            thumbnail_height = im_height / width_ratio
            
        
    elif thumbnail_scale_type == THUMBNAIL_SCALE_TO_FILL:
        
        # we do min 5.0 here to stop really tall and thin images getting zoomed in from width 1px to 150 and getting a thumbnail with a height of 75,000 pixels
        # in this case the line image is already crazy distorted, so we don't mind squishing it
        
        if image_is_taller_than_bounding_box: # i.e. the width will be at bounding width, the height will spill over
            
            thumbnail_height = bounding_width * min( 5.0, 1 / image_ratio )
            
        elif image_is_wider_than_bounding_box: # i.e. the height will be at bounding height, the width will spill over
            
            thumbnail_width = bounding_height * min( 5.0, image_ratio )
            
        
        # old stuff that actually clipped the size of the thing
        '''
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
        '''
        
    
    thumbnail_width = int( thumbnail_width )
    thumbnail_height = int( thumbnail_height )
    
    thumbnail_width = max( thumbnail_width, 1 )
    thumbnail_height = max( thumbnail_height, 1 )
    
    return ( thumbnail_width, thumbnail_height )
    

def IsDecompressionBomb( path, human_file_description = None ) -> bool:
    
    # there are two errors here, the 'Warning' and the 'Error', which atm is just a test vs a test x 2 for number of pixels
    # 256MB bmp by default, ( 1024 ** 3 ) // 4 // 3
    # we'll set it at 512MB, and now catching error should be about 1GB
    
    PILImage.MAX_IMAGE_PIXELS = ( 512 * ( 1024 ** 2 ) ) // 3
    
    warnings.simplefilter( 'error', PILImage.DecompressionBombError )
    
    try:
        
        HydrusImageOpening.RawOpenPILImage( path, human_file_description = human_file_description )
        
    except ( PILImage.DecompressionBombError ):
        
        return True
        
    except:
        
        # pil was unable to load it, which does not mean it was a decomp bomb
        return False
        
    finally:
        
        PILImage.MAX_IMAGE_PIXELS = None
        
        warnings.simplefilter( 'ignore', PILImage.DecompressionBombError )
        
    
    return False
    

def ResizeNumPyImage( numpy_image: numpy.ndarray, target_resolution, forced_interpolation = None ) -> numpy.ndarray:
    
    ( target_width, target_height ) = target_resolution
    ( image_width, image_height ) = GetResolutionNumPy( numpy_image )
    
    if target_width == image_width and target_height == target_width:
        
        return numpy_image
        
    elif target_width > image_height or target_height > image_width:
        
        interpolation = cv2.INTER_LANCZOS4
        
    else:
        
        interpolation = cv2.INTER_AREA
        
    
    if forced_interpolation is not None:
        
        interpolation = forced_interpolation
        
    
    return cv2.resize( numpy_image, ( target_width, target_height ), interpolation = interpolation )
    

def GenerateDefaultThumbnailNumPyFromPath( path: str, target_resolution: tuple[ int, int ] ):
    
    thumb_image = GeneratePILImage( path )
    
    pil_image = PILImageOps.pad( thumb_image, target_resolution, PILImage.Resampling.LANCZOS )
    
    return GenerateNumPyImageFromPILImage( pil_image, strip_useless_alpha = False )
    
