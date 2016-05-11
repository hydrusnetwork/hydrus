import numpy.core.multiarray # important this comes before cv!
import cv2
import HydrusImageHandling
import HydrusGlobals

if cv2.__version__.startswith( '2' ):
    
    IMREAD_UNCHANGED = cv2.CV_LOAD_IMAGE_UNCHANGED
    
else:
    
    IMREAD_UNCHANGED = cv2.IMREAD_UNCHANGED
    
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
    
    # this used to be a regular cv.imread call, but it was crashing the whole process on random thumbs, hooray
    # it was just the read that was the problem, so this seems to work fine, even if pil is only about half as fast
    
    pil_image = HydrusImageHandling.GeneratePILImage( path )
    
    numpy_image = GenerateNumPyImageFromPILImage( pil_image )
    
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
    
    numpy_image = GenerateNumpyImage( path )
    
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
    