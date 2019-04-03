import numpy.core.multiarray # important this comes before cv!
from . import ClientConstants as CC
import cv2
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusImageHandling
from . import HydrusGlobals as HG
from functools import reduce

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
    
cv_interpolation_enum_lookup = {}

cv_interpolation_enum_lookup[ CC.ZOOM_NEAREST ] = cv2.INTER_NEAREST
cv_interpolation_enum_lookup[ CC.ZOOM_LINEAR ] = cv2.INTER_LINEAR
cv_interpolation_enum_lookup[ CC.ZOOM_AREA ] = cv2.INTER_AREA
cv_interpolation_enum_lookup[ CC.ZOOM_CUBIC ] = cv2.INTER_CUBIC
cv_interpolation_enum_lookup[ CC.ZOOM_LANCZOS4 ] = cv2.INTER_LANCZOS4

def GenerateNumpyImage( path, mime ):
    
    if HG.media_load_report_mode:
        
        HydrusData.ShowText( 'Loading media: ' + path )
        
    
    if mime == HC.IMAGE_GIF or HG.client_controller.new_options.GetBoolean( 'load_images_with_pil' ):
        
        if HG.media_load_report_mode:
            
            HydrusData.ShowText( 'Loading with PIL' )
            
        
        # a regular cv.imread call, can crash the whole process on random thumbs, hooray, so have this as backup
        # it was just the read that was the problem, so this seems to work fine, even if pil is only about half as fast
        
        pil_image = HydrusImageHandling.GeneratePILImage( path )
        
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
                
            
            pil_image = HydrusImageHandling.GeneratePILImage( path )
            
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
    
    pil_image = HydrusImageHandling.Dequantize( pil_image )
    
    ( w, h ) = pil_image.size
    
    s = pil_image.tobytes()
    
    return numpy.fromstring( s, dtype = 'uint8' ).reshape( ( h, w, len( s ) // ( w * h ) ) )
    
def GenerateShapePerceptualHashes( path, mime ):
    
    numpy_image = GenerateNumpyImage( path, mime )
    
    ( y, x, depth ) = numpy_image.shape
    
    if depth == 4:
        
        # doing this on 10000x10000 pngs eats ram like mad
        numpy_image = ThumbnailNumpyImage( numpy_image, ( 1024, 1024 ) )
        
        ( y, x, depth ) = numpy_image.shape
        
        # create weight and transform numpy_image to greyscale
        
        numpy_alpha = numpy_image[ :, :, 3 ]
        
        numpy_alpha_float = numpy_alpha / 255.0
        
        numpy_image_bgr = numpy_image[ :, :, :3 ]
        
        numpy_image_gray_bare = cv2.cvtColor( numpy_image_bgr, cv2.COLOR_RGB2GRAY )
        
        # create a white greyscale canvas
        
        white = numpy.ones( ( y, x ) ) * 255.0
        
        # paste the grayscale image onto the white canvas using: pixel * alpha + white * ( 1 - alpha )
        
        numpy_image_gray = numpy.uint8( ( numpy_image_gray_bare * numpy_alpha_float ) + ( white * ( numpy.ones( ( y, x ) ) - numpy_alpha_float ) ) )
        
    else:
        
        numpy_image_gray = cv2.cvtColor( numpy_image, cv2.COLOR_RGB2GRAY )
        
    
    numpy_image_tiny = cv2.resize( numpy_image_gray, ( 32, 32 ), interpolation = cv2.INTER_AREA )
    
    # convert to float and calc dct
    
    numpy_image_tiny_float = numpy.float32( numpy_image_tiny )
    
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
    
    # make a monochromatic, 64-bit hash of whether the entry is above or below the median
    
    dct_88_boolean = dct_88 > median
    
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
        
    
    phash = bytes( list_of_bytes ) # this works!
    
    # now discard the blank hash, which is 1000000... and not useful
    
    phashes = set()
    
    phashes.add( phash )
    
    phashes.discard( CC.BLANK_PHASH )
    
    # we good
    
    return phashes
    
def GenerateBytesFromCV( numpy_image, mime ):
    
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
        
    
def GenerateThumbnailBytesFromStaticImagePathCV( path, bounding_dimensions, mime ):
    
    if mime == HC.IMAGE_GIF:
        
        return HydrusFileHandling.GenerateThumbnailBytesFromStaticImagePathPIL( path, bounding_dimensions, mime )
        
    
    numpy_image = GenerateNumpyImage( path, mime )
    
    thumbnail_numpy_image = ThumbnailNumpyImage( numpy_image, bounding_dimensions )
    
    try:
        
        thumbnail_bytes = GenerateBytesFromCV( thumbnail_numpy_image, mime )
        
        return thumbnail_bytes
        
    except HydrusExceptions.CantRenderWithCVException:
        
        return HydrusFileHandling.GenerateThumbnailBytesFromStaticImagePathPIL( path, bounding_dimensions, mime )
        
    
from . import HydrusFileHandling

HydrusFileHandling.GenerateThumbnailBytesFromStaticImagePath = GenerateThumbnailBytesFromStaticImagePathCV
    
def GetNumPyImageResolution( numpy_image ):
    
    ( image_height, image_width, depth ) = numpy_image.shape
    
    return ( image_width, image_height )
    
def ResizeNumpyImage( numpy_image, target_resolution ):
    
    ( target_width, target_height ) = target_resolution
    ( image_width, image_height, depth ) = numpy_image.shape
    
    if target_width == image_width and target_height == target_width:
        
        return numpy_image
        
    elif target_width > image_height or target_height > image_width:
        
        interpolation = cv2.INTER_LANCZOS4
        
    else:
        
        interpolation = cv2.INTER_AREA
        
    
    return cv2.resize( numpy_image, ( target_width, target_height ), interpolation = interpolation )
    
def ResizeNumpyImageForMediaViewer( mime, numpy_image, target_resolution ):
    
    ( target_width, target_height ) = target_resolution
    new_options = HG.client_controller.new_options
    
    ( scale_up_quality, scale_down_quality ) = new_options.GetMediaZoomQuality( mime )
    
    ( image_width, image_height, depth ) = numpy_image.shape
    
    if ( target_width, target_height ) == ( image_height, image_width ):
        
        return numpy_image
        
    else:
        
        if target_width > image_height or target_height > image_width:
            
            interpolation = cv_interpolation_enum_lookup[ scale_up_quality ]
            
        else:
            
            interpolation = cv_interpolation_enum_lookup[ scale_down_quality ]
            
        
        return cv2.resize( numpy_image, ( target_width, target_height ), interpolation = interpolation )
        
    
def ThumbnailNumpyImage( numpy_image, bounding_dimensions ):
    
    ( bounding_width, bounding_height ) = bounding_dimensions
    ( image_width, image_height, depth ) = numpy_image.shape
    
    if bounding_width >= image_height and bounding_height >= image_width:
        
        return numpy_image
        
    
    target_resolution = HydrusImageHandling.GetThumbnailResolution( ( image_height, image_width ), ( bounding_width, bounding_height ) )
    
    return ResizeNumpyImage( numpy_image, target_resolution )
    
