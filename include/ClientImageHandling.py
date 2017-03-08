import numpy.core.multiarray # important this comes before cv!
import ClientConstants as CC
import cv2
import HydrusImageHandling
import HydrusGlobals

if cv2.__version__.startswith( '2' ):
    
    IMREAD_UNCHANGED = cv2.CV_LOAD_IMAGE_UNCHANGED
    
else:
    
    IMREAD_UNCHANGED = cv2.IMREAD_UNCHANGED
    
cv_interpolation_enum_lookup = {}

cv_interpolation_enum_lookup[ CC.ZOOM_NEAREST ] = cv2.INTER_NEAREST
cv_interpolation_enum_lookup[ CC.ZOOM_LINEAR ] = cv2.INTER_LINEAR
cv_interpolation_enum_lookup[ CC.ZOOM_AREA ] = cv2.INTER_AREA
cv_interpolation_enum_lookup[ CC.ZOOM_CUBIC ] = cv2.INTER_CUBIC
cv_interpolation_enum_lookup[ CC.ZOOM_LANCZOS4 ] = cv2.INTER_LANCZOS4
    
def EfficientlyResizeNumpyImage( numpy_image, ( target_x, target_y ) ):
    
    ( im_y, im_x, depth ) = numpy_image.shape
    
    if target_x >= im_x and target_y >= im_y: return numpy_image
    
    # this seems to slow things down a lot, at least for cv!
    #if im_x > 2 * target_x and im_y > 2 * target_y: result = cv2.resize( numpy_image, ( 2 * target_x, 2 * target_y ), interpolation = cv2.INTER_NEAREST )
    
    return cv2.resize( numpy_image, ( target_x, target_y ), interpolation = cv2.INTER_AREA )
    
def EfficientlyThumbnailNumpyImage( numpy_image, ( target_x, target_y ) ):
    
    ( im_y, im_x, depth ) = numpy_image.shape
    
    if target_x >= im_x and target_y >= im_y: return numpy_image
    
    ( target_x, target_y ) = HydrusImageHandling.GetThumbnailResolution( ( im_x, im_y ), ( target_x, target_y ) )
    
    return cv2.resize( numpy_image, ( target_x, target_y ), interpolation = cv2.INTER_AREA )
    
def GenerateNumpyImage( path ):
    
    if HydrusGlobals.client_controller.GetNewOptions().GetBoolean( 'load_images_with_pil' ):
        
        # a regular cv.imread call, can crash the whole process on random thumbs, hooray, so have this as backup
        # it was just the read that was the problem, so this seems to work fine, even if pil is only about half as fast
        
        pil_image = HydrusImageHandling.GeneratePILImage( path )
        
        numpy_image = GenerateNumPyImageFromPILImage( pil_image )
        
    else:
        
        numpy_image = cv2.imread( path, flags = IMREAD_UNCHANGED )
        
        if numpy_image is None: # doesn't support static gifs and some random other stuff
            
            pil_image = HydrusImageHandling.GeneratePILImage( path )
            
            numpy_image = GenerateNumPyImageFromPILImage( pil_image )
            
        else:
            
            if numpy_image.dtype == 'uint16':
                
                numpy_image /= 256
                
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
    
def GenerateShapePerceptualHashes( path ):
    
    numpy_image = GenerateNumpyImage( path )
    
    ( y, x, depth ) = numpy_image.shape
    
    if depth == 4:
        
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
        
    
    bytes = []
    
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
        
        byte = reduce( collapse_bools_to_binary_uint, dct_88_boolean[i], 0 )
        
        bytes.append( byte )
        
    
    phash = str( bytearray( bytes ) )
    
    # now discard the blank hash, which is 1000000... and not useful
    
    phashes = set()
    
    phashes.add( phash )
    
    phashes.discard( CC.BLANK_PHASH )
    
    # we good
    
    return phashes
    
def ResizeNumpyImage( mime, numpy_image, ( target_x, target_y ) ):
    
    new_options = HydrusGlobals.client_controller.GetNewOptions()
    
    ( scale_up_quality, scale_down_quality ) = new_options.GetMediaZoomQuality( mime )
    
    ( im_y, im_x, depth ) = numpy_image.shape
    
    if ( target_x, target_y ) == ( im_x, im_y ):
        
        return numpy_image
        
    else:
        
        if target_x > im_x or target_y > im_y:
            
            interpolation = cv_interpolation_enum_lookup[ scale_up_quality ]
            
        else:
            
            interpolation = cv_interpolation_enum_lookup[ scale_down_quality ]
            
        
        return cv2.resize( numpy_image, ( target_x, target_y ), interpolation = interpolation )
        
    
