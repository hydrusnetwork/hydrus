import ClientImageHandling
import cv2
import HydrusSerialisable
import numpy
import struct

def DumpToPng( payload, title, payload_type, text, path ):
    
    payload_length = len( payload )
    
    payload_string_length = payload_length + 4
    
    square_width = int( float( payload_string_length ) ** 0.5 )
    
    width = max( 512, square_width )
    
    payload_height = float( payload_string_length ) / width
    
    if float( payload_string_length ) / width % 1.0 > 0:
        
        payload_height += 1
        
    
    # given this width, figure out how much height we need for title and text and object type
    # does cv have gettextentent or similar?
    # getTextSize looks like the one
    # intelligently wrap the text to fit into our width sans padding
    
    # we now know our height
    top_height = 250
    
    top_image = numpy.empty( ( top_height, width ), dtype = 'uint8' )
    
    top_image.fill( 255 )
    
    # draw hydrus icon in the corner
    # draw title
    # draw payload_type
    # draw text
    top_height_header = struct.pack( '!H', top_height )
    
    ( byte0, byte1 ) = top_height_header
    
    top_image[0][0] = ord( byte0 )
    top_image[0][1] = ord( byte1 )
    
    payload_length_header = struct.pack( '!I', payload_length )
    
    num_empty_bytes = payload_height * width - payload_string_length
    
    full_payload_string = payload_length_header + payload + '\x00' * num_empty_bytes
    
    payload_image = numpy.fromstring( full_payload_string, dtype = 'uint8' ).reshape( ( payload_height, width ) )
    
    # if this works out wrong, you can change axis or do stack_vertically instead or something. one of those will do the trick
    finished_image = numpy.concatenate( top_image, payload_image )
    
    # make sure this is how cv 'params' work
    cv2.imwrite( path, finished_image, params = { cv2.IMWRITE_PNG_COMPRESSION : 9 } )
    
def LoadFromPng( path ):
    
    numpy_image = cv2.imread( path )
    
    ( height, width ) = numpy_image.shape
    
    complete_data = numpy_image.tostring()
    
    top_height_header = complete_data[:2]
    
    ( top_height, ) = struct.unpack( '!H', top_height_header )
    
    full_payload_string = complete_data[ width * top_height : ]
    
    payload_length_header = full_payload_string[:4]
    
    ( payload_length, ) = struct.unpack( '!I', payload_length_header )
    
    payload = full_payload_string[ 4 : 4 + payload_length ]
    
    return payload
    