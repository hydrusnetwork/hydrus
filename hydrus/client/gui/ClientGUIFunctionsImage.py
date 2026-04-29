import numpy

from qtpy import QtGui as QG

from hydrus.client.gui import QtInit
from hydrus.core.files.images import HydrusImageNormalisation

def ConvertQtImageToNumPy( qt_image: QG.QImage, strip_useless_alpha = True ):
    
    #        _     _                          _        _                           
    #    _  | |   (_)          _             | |      | |                          
    #  _| |_| |__  _  ___    _| |_ ___   ___ | |  _   | |__   ___  _   _  ____ ___ 
    # (_   _)  _ \| |/___)  (_   _) _ \ / _ \| |_/ )  |  _ \ / _ \| | | |/ ___)___)
    #   | |_| | | | |___ |    | || |_| | |_| |  _ (   | | | | |_| | |_| | |  |___ |
    #    \__)_| |_|_(___/      \__)___/ \___/|_| \_)  |_| |_|\___/|____/|_|  (___/ 
    #
    # Ok so I don't know what is going on, but QImage 'ARGB32' bitmaps seem to actually be stored BGRA!!!
    # if you tell them to convert to RGB888, they switch their bytes around to RGB, so this is probably some internal Qt gubbins
    # The spec says they are 0xAARRGGBB, so I'm guessing it is swapped for some X-endian reason???
    # unfortunately this messes with us a little, since we rip these bits and assume we are getting RGBA
    # Ok, I figured it out, just convert to RGBA8888 (which supposedly _is_ endian ordered) and it sorts itself out
    # I guess someone on different endian-ness won't get the right answer? I'd believe it if ARGB32 wasn't reversed
    # if that is the case, we can inspect the 'PixelFormat' of the bmp and it'll say our endianness, and then I guess I reverse or something
    # probably easier, whatever the case, to do that sort of clever channel swapping once we are in numpy
    # another ultimate answer is probably to convert to rgb888 and rip the alpha too and recombine, or just ditch the alpha who cares
    
    qt_image = qt_image.copy()
    
    if qt_image.hasAlphaChannel():
        
        if qt_image.format() != QG.QImage.Format.Format_RGBA8888:
            
            qt_image.convertTo( QG.QImage.Format.Format_RGBA8888 )
            
        
    else:
        
        if qt_image.format() != QG.QImage.Format.Format_RGB888:
            
            qt_image.convertTo( QG.QImage.Format.Format_RGB888 )
            
        
    
    width = qt_image.width()
    height = qt_image.height()
    
    if qt_image.depth() == 1:
        
        # this is probably super wrong, but whatever for now
        depth = 1
        
    else:
        
        # 8, 24, 32 etc...
        depth = qt_image.depth() // 8
        
    
    data_bytearray = qt_image.bits()
    
    if data_bytearray is None:
        
        raise Exception( 'Could not convert an image from Qt format to NumPy. Maybe out-of-memory issue?' )
        
    
    data_bytes = None
    
    if QtInit.WE_ARE_PYSIDE:
        
        data_bytes = bytes( data_bytearray )
        
    elif QtInit.WE_ARE_PYQT:
        
        if hasattr( data_bytearray, 'asstring' ):
            
            data_bytes = data_bytearray.asstring( height * width * depth )
            
        
    
    if data_bytes is None:
        
        raise Exception( 'Could not extract data_bytearray to data_bytes when pulling Qt Image data to NumPy array!' )
        
    
    if qt_image.bytesPerLine() == width * depth:
        
        numpy_image = numpy.frombuffer( data_bytes, dtype = 'uint8' ).reshape( ( height, width, depth ) )
        
    else:
        
        # ok bro, so in some cases a qt_image stores its lines with a bit of \x00 padding. you have a 990-pixel line that is 2970+2 bytes long
        # apparently this is system memory storage limitations blah blah blah. it can also happen when you qt_image.copy(), so I guess it makes for pleasant memory layout little-endian something
        # so far I have only encountered simple instances of this, with data up front and zero bytes at the end
        # so let's just strip it lad
        
        bytes_per_line = qt_image.bytesPerLine()
        desired_bytes_per_line = width * depth
        excess_bytes_to_trim = bytes_per_line - desired_bytes_per_line
        
        numpy_padded = numpy.frombuffer( data_bytes, dtype = 'uint8' ).reshape( ( height, bytes_per_line ) )
        
        numpy_image = numpy_padded[ :, : -excess_bytes_to_trim ].reshape( ( height, width, depth ) )
        
    
    if strip_useless_alpha:
        
        numpy_image = HydrusImageNormalisation.StripOutAnyUselessAlphaChannel( numpy_image )
        
    
    return numpy_image
    

