import numpy
import cv2

from hydrus.external import blurhash as external_blurhash

from hydrus.core.files.images import HydrusImageHandling

# pretty grunky but it seems to all work and this is low level so I'll endure it
def rgb_to_hsl( r, g, b ):
    
    # Normalize RGB to [0,1]
    r, g, b = [v / 255.0 for v in (r, g, b)]

    # Get min, max, and delta
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    delta = max_c - min_c

    # Compute Lightness
    L = (max_c + min_c) / 2

    # Compute Saturation
    if delta == 0:
        
        S = 0  # Achromatic (grayscale)
        
    else:
        
        S = delta / (2 - max_c - min_c) if L > 0.5 else delta / (max_c + min_c)
        

    # Compute Hue
    if delta == 0:
        H = 0  # Undefined for grayscale, set to 0
    elif max_c == r:
        H = (g - b) / delta % 6
    elif max_c == g:
        H = (b - r) / delta + 2
    else:  # max_c == b
        H = (r - g) / delta + 4

    H *= 60  # Convert to degrees

    return H, S, L
    

def rgb_to_xyz( r, g, b ):
    
    # Normalize to [0,1]
    r, g, b = [v / 255.0 for v in (r, g, b)]
    
    # Apply gamma correction (sRGB to linear RGB)
    def gamma_correct(v):
        
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        
    
    r, g, b = map(gamma_correct, (r, g, b))

    # Convert to XYZ (D65 illuminant)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    return x, y, z
    

def xyz_to_lab( x, y, z ):
    
    # Normalize for D65 white point
    x, y, z = x / 0.95047, y / 1.00000, z / 1.08883

    # Convert using the Lab transformation
    def f(t):
        
        return t ** (1/3) if t > 0.008856 else (7.787 * t) + (16 / 116)
        
    
    fx, fy, fz = map(f, (x, y, z))

    L = (116 * fy) - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    return L, a, b
    

def ConvertBlurhashToSortableChromaticMagnitude( blurhash: str, reverse: bool ):
    
    ( r, g, b ) = GetAverageColourFromBlurhash( blurhash )
    
    ( l, a, b ) = xyz_to_lab( *rgb_to_xyz( r, g, b ) )
    
    # chromatic magnitude is root of a-squared plus b-squared, but we don't need the root for the sort
    cm = ( a ** 2 ) + ( b ** 2 )
    
    return ( cm, l )
    

def ConvertBlurhashToSortableBlueYellow( blurhash: str, reverse: bool ):
    
    ( r, g, b ) = GetAverageColourFromBlurhash( blurhash )
    
    ( l, a, b ) = xyz_to_lab( *rgb_to_xyz( r, g, b ) )
    
    return ( b, -l )
    

def ConvertBlurhashToSortableGreenRed( blurhash: str, reverse: bool ):
    
    ( r, g, b ) = GetAverageColourFromBlurhash( blurhash )
    
    ( l, a, b ) = xyz_to_lab( *rgb_to_xyz( r, g, b ) )
    
    return ( a, -l )
    

def ConvertBlurhashToSortableHue( blurhash: str, reverse: bool ):
    
    ( r, g, b ) = GetAverageColourFromBlurhash( blurhash )
    
    ( h, s, l ) = rgb_to_hsl( r, g, b )
    
    if s < 0.03:
        
        # stuff greys at the bottom
        initial = -1 if reverse else 1
        
    else:
        
        initial = 0
        
    
    return ( initial, h, - s )
    

def ConvertBlurhashToSortableLightness( blurhash: str, reverse: bool ):
    
    ( r, g, b ) = GetAverageColourFromBlurhash( blurhash )
    
    ( l, a, b ) = xyz_to_lab( *rgb_to_xyz( r, g, b ) )
    
    # chromatic magnitude is root of a-squared plus b-squared, but we don't need the root for the sort
    cm = ( a ** 2 ) + ( b ** 2 )
    
    return ( l, cm )
    

def GetAverageColourFromBlurhash( blurhash: str ):
    
    # ok blurhash is basically a DCT, and the the second to sixth bytes are the DC component, which is average colour
    
    average_colour_encoded = blurhash[2:6]
    
    average_colour_int = external_blurhash.base83_decode( average_colour_encoded )
    
    r = ( average_colour_int >> 16 ) & 0xFF
    g = ( average_colour_int >> 8 ) & 0xFF
    b = average_colour_int & 0xFF
    
    return ( r, g, b )
    

def GetBlurhashFromNumPy( numpy_image: numpy.ndarray ) -> str:
    
    media_height = numpy_image.shape[0]
    media_width = numpy_image.shape[1]
    
    if media_width == 0 or media_height == 0:
        
        return ''
        
    
    ratio = media_width / media_height
    
    if ratio > 4 / 3:
        
        components_x = 5
        components_y = 3
        
    elif ratio < 3 / 4:
        
        components_x = 3
        components_y = 5
        
    else:
        
        components_x = 4
        components_y = 4
        
    
    CUTOFF_DIMENSION = 100
    
    if numpy_image.shape[0] > CUTOFF_DIMENSION or numpy_image.shape[1] > CUTOFF_DIMENSION:
        
        numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, ( CUTOFF_DIMENSION, CUTOFF_DIMENSION ), forced_interpolation = cv2.INTER_LINEAR )
        
    
    return external_blurhash.blurhash_encode( numpy_image, components_x, components_y )
    

def GetNumpyFromBlurhash( blurhash, width, height ) -> numpy.ndarray:
    
    # this thing is super slow, they recommend even in the documentation to render small and scale up
    if width > 32 or height > 32:
        
        numpy_image = numpy.array( external_blurhash.blurhash_decode( blurhash, 32, 32 ), dtype = 'uint8' )
        
        numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, ( width, height ) )
        
    else:
        
        numpy_image = numpy.array( external_blurhash.blurhash_decode( blurhash, width, height ), dtype = 'uint8' )
        
    
    return numpy_image
    
