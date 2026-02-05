import collections
import collections.abc
import cv2
import numpy
import struct

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusCompression
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTemp
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions

# ok, the serialised png format is:

# the png is monochrome, no alpha channel (mode 'L' in PIL)
# the data is read left to right in visual pixels. one pixel = one byte
# first two bytes (i.e. ( 0, 0 ) and ( 1, 0 )), are a big endian unsigned short (!H), and say how tall the header is in number of rows. the actual data starts after that
# first four bytes of data are a big endian unsigned int (!I) saying how long the payload is in bytes
# read that many pixels after that, you got the payload
# it should be zlib compressed these days and is most likely a dumped hydrus serialisable object, which is a json guy with a whole complicated loading system. utf-8 it into a string and you are half way there :^)

IMREAD_UNCHANGED = cv2.IMREAD_UNCHANGED

def CreateTopImage( width, title, payload_description, text ):
    
    text_extent_qt_image = CG.client_controller.bitmap_manager.GetQtImage( 20, 20, 24 )
    
    painter = QG.QPainter( text_extent_qt_image )
    
    text_font = QW.QApplication.font()
    
    basic_font_size = text_font.pointSize()
    
    payload_description_font = QW.QApplication.font()
    
    payload_description_font.setPointSize( int( basic_font_size * 1.4 ) )
    
    title_font = QW.QApplication.font()
    
    title_font.setPointSize( int( basic_font_size * 2.0 ) )
    
    texts_to_draw = []
    
    current_y = 6
    
    for ( t, f ) in ( ( title, title_font ), ( payload_description, payload_description_font ), ( text, text_font ) ):
        
        painter.setFont( f )
        
        wrapped_texts = WrapText( painter, t, width - 20 )
        line_height = painter.fontMetrics().height()
        
        wrapped_texts_with_ys = []
        
        if len( wrapped_texts ) > 0:
            
            current_y += 10
            
            for wrapped_text in wrapped_texts:
                
                wrapped_texts_with_ys.append( ( wrapped_text, current_y ) )
                
                current_y += line_height + 4
                
            
        
        texts_to_draw.append( ( wrapped_texts_with_ys, f ) )
        
    
    current_y += 6
    
    top_height = current_y
    
    del painter
    del text_extent_qt_image
    
    #
    
    top_qt_image = CG.client_controller.bitmap_manager.GetQtImage( width, top_height, 24 )
    
    painter = QG.QPainter( top_qt_image )
    
    painter.setBackground( QG.QBrush( QC.Qt.GlobalColor.white ) )
    
    painter.eraseRect( painter.viewport() )
    
    #
    
    painter.drawPixmap( width-16-5, 5, CC.global_pixmaps().file_repository )
    
    #
    
    for ( wrapped_texts_with_ys, f ) in texts_to_draw:
        
        painter.setFont( f )
        
        for ( wrapped_text, y ) in wrapped_texts_with_ys:
            
            ( text_size, wrapped_text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, wrapped_text )
            
            ClientGUIFunctions.DrawText( painter, ( width - text_size.width() ) // 2, y, wrapped_text )
            
        
    
    del painter
    
    top_image_rgb = ClientGUIFunctions.ConvertQtImageToNumPy( top_qt_image )
    
    top_image = cv2.cvtColor( top_image_rgb, cv2.COLOR_RGB2GRAY )
    
    top_height_header = struct.pack( '!H', top_height )
    
    byte0 = top_height_header[0:1]
    byte1 = top_height_header[1:2]
    
    top_image[0][0] = ord( byte0 )
    top_image[0][1] = ord( byte1 )
    
    return top_image
    
def DumpToPNG( width, payload_bytes, title, payload_description, text, path ):
    
    payload_bytes_length = len( payload_bytes )
    
    header_and_payload_bytes_length = payload_bytes_length + 4
    
    payload_height = int( header_and_payload_bytes_length / width )
    
    if ( header_and_payload_bytes_length / width ) % 1.0 > 0:
        
        payload_height += 1
        
    
    top_image = CreateTopImage( width, title, payload_description, text )
    
    payload_length_header = struct.pack( '!I', payload_bytes_length )
    
    num_empty_bytes = payload_height * width - header_and_payload_bytes_length
    
    header_and_payload_bytes = payload_length_header + payload_bytes + b'\x00' * num_empty_bytes
    
    payload_image = numpy.frombuffer( header_and_payload_bytes, dtype = 'uint8' ).reshape( ( payload_height, width ) )
    
    finished_image = numpy.concatenate( ( top_image, payload_image ) )
    
    # this is to deal with unicode paths, which cv2 can't handle
    ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath( suffix = '.png' )
    
    try:
        
        cv2.imwrite( temp_path, finished_image, [ cv2.IMWRITE_PNG_COMPRESSION, 9 ] )
        
        HydrusPaths.MirrorFile( temp_path, path )
        
    except Exception as e:
        
        HydrusData.ShowException( e )
        
        raise Exception( 'Could not save the png!' ) from e
        
    finally:
        
        HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
        
    
def GetPayloadBytesAndLength( payload_obj ):
    
    if isinstance( payload_obj, bytes ):
        
        return ( HydrusCompression.CompressBytesToBytes( payload_obj ), len( payload_obj ) )
        
    elif isinstance( payload_obj, str ):
        
        return ( HydrusCompression.CompressStringToBytes( payload_obj ), len( payload_obj ) )
        
    else:
        
        payload_string = payload_obj.DumpToString()
        
        return ( HydrusCompression.CompressStringToBytes( payload_string ), len( payload_string ) )
        
    
def GetPayloadTypeString( payload_obj ):
    
    if isinstance( payload_obj, bytes ):
        
        return 'Bytes'
        
    elif isinstance( payload_obj, str ):
        
        return 'String'
        
    elif isinstance( payload_obj, HydrusSerialisable.SerialisableList ):
        
        type_string_counts = collections.Counter()
        
        for o in payload_obj:
            
            type_string_counts[ GetPayloadTypeString( o ) ] += 1
            
        
        type_string = ', '.join( ( HydrusNumbers.ToHumanInt( count ) + ' ' + s for ( s, count ) in list(type_string_counts.items()) ) )
        
        return 'A list of ' + type_string
        
    elif isinstance( payload_obj, HydrusSerialisable.SerialisableBase ):
        
        return payload_obj.SERIALISABLE_NAME
        
    else:
        
        return repr( type( payload_obj ) )
        
    
def GetPayloadDescriptionAndBytes( payload_obj ):
    
    ( payload_bytes, payload_length ) = GetPayloadBytesAndLength( payload_obj )
    
    payload_description = GetPayloadTypeString( payload_obj ) + ' - ' + HydrusData.ToHumanBytes( payload_length )
    
    return ( payload_description, payload_bytes )
    

def LoadFromQtImage( qt_image: QG.QImage ):
    
    numpy_image = ClientGUIFunctions.ConvertQtImageToNumPy( qt_image )
    
    return LoadFromNumPyImage( numpy_image )
    

def LoadFromPNG( path ):
    
    # this is to deal with unicode paths, which cv2 can't handle
    ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
    
    try:
        
        HydrusPaths.MirrorFile( path, temp_path )
        
        try:
            
            # unchanged because we want exact byte data, no conversions or other gubbins
            numpy_image = cv2.imread( temp_path, flags = IMREAD_UNCHANGED )
            
            if numpy_image is None:
                
                raise Exception()
                
            
        except Exception as e:
            
            try:
                
                # dequantize = False because we don't want to convert our greyscale bytes to RGB
                
                pil_image = HydrusImageHandling.GeneratePILImage( temp_path, dequantize = False )
                
                # leave strip_useless_alpha = True in here just to catch the very odd LA situation
                
                numpy_image = HydrusImageHandling.GenerateNumPyImageFromPILImage( pil_image )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                raise Exception( '"{}" did not appear to be a valid image!'.format( path ) ) from e
                
            
        
    finally:
        
        HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
        
    
    return LoadFromNumPyImage( numpy_image )
    

def LoadFromNumPyImage( numpy_image: numpy.ndarray ):
    
    try:
        
        height = numpy_image.shape[0]
        width = numpy_image.shape[1]
        
        if len( numpy_image.shape ) > 2:
            
            depth = numpy_image.shape[2]
            
            if depth != 1:
                
                numpy_image = numpy_image[:,:,0].copy() # let's fetch one channel. if the png is a perfect RGB conversion of the original (or, let's say, a Firefox bmp export), this actually works
                
            
        
        try:
            
            complete_data = numpy_image.tobytes()
            
            top_height_header = complete_data[:2]
            
            ( top_height, ) = struct.unpack( '!H', top_height_header )
            
            payload_and_header_bytes = complete_data[ width * top_height : ]
            
        except Exception as e:
            
            raise Exception( 'Header bytes were invalid!' )
            
        
        try:
            
            payload_length_header = payload_and_header_bytes[:4]
            
            ( payload_bytes_length, ) = struct.unpack( '!I', payload_length_header )
            
            payload_bytes = payload_and_header_bytes[ 4 : 4 + payload_bytes_length ]
            
        except Exception as e:
            
            raise Exception( 'Payload bytes were invalid!' )
            
        
    except Exception as e:
        
        HydrusData.PrintException( e )
        
        message = 'The image loaded, but it did not seem to be a hydrus serialised png! The error was: {}'.format( repr( e ) )
        message += '\n' * 2
        message += 'If you believe this is a legit non-resized, non-converted hydrus serialised png, please send it to hydrus_dev.'
        
        raise Exception( message )
        
    
    return payload_bytes
    
def LoadStringFromPNG( path: str ) -> str:
    
    payload_bytes = LoadFromPNG( path )
    
    try:
        
        payload_string = HydrusCompression.DecompressBytesToString( payload_bytes )
        
    except Exception as e:
        
        # older payloads were not compressed
        payload_string = str( payload_bytes, 'utf-8' )
        
    
    return payload_string
    
def TextExceedsWidth( painter, text, width ):
    
    ( text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
    
    return text_size.width() > width
    
def WrapText( painter, text, width ):
    
    words = text.split( ' ' )
    
    lines = []
    
    next_line = []
    
    for word in words:
        
        if word == '':
            
            continue
            
        
        potential_next_line = list( next_line )
        
        potential_next_line.append( word )
        
        if TextExceedsWidth( painter, ' '.join( potential_next_line ), width ):
            
            if len( potential_next_line ) == 1: # one very long word
                
                lines.append( ' '.join( potential_next_line ) )
                
                next_line = []
                
            else:
                
                lines.append( ' '.join( next_line ) )
                
                next_line = [ word ]
                
            
        else:
            
            next_line = potential_next_line
            
        
    
    if len( next_line ) > 0:
        
        lines.append( ' '.join( next_line ) )
        
    
    return lines
    
