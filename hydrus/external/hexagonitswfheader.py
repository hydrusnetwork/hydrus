import struct
import lzma
import zlib

# hydrus_dev added ZWS support
# hydrus_dev mangled this to work on py3

def parse(input):
    """Parses the header information from an SWF file."""
    if hasattr(input, 'read'):
        input.seek(0)
    else:
        input = open(input, 'rb')

    def read_ui8(c):
        return struct.unpack('<B', c)[0]

    def read_ui16(c):
        return struct.unpack('<H', c)[0]

    def read_ui32(c):
        return struct.unpack('<I', c)[0]

    header = {}

    # Read the 3-byte signature field
    signature = b''.join(struct.unpack('<3c', input.read(3)))
    
    signature = str( signature, 'utf-8' )
    
    if signature not in ( 'FWS', 'CWS', 'ZWS' ):
        
        raise ValueError( 'Invalid SWF signature: {}'.format( signature ) )
        

    # Compression
    header['compressed'] = signature.startswith( 'C' ) or signature.startswith( 'Z' )

    # Version
    header['version'] = read_ui8(input.read(1))

    # File size (stored as a 32-bit integer)
    header['size'] = read_ui32(input.read(4))

    # Payload
    if signature.startswith( 'F' ):
        
        buffer = input.read(header['size'])
        
    elif signature.startswith( 'C' ):
        buffer = input.read(header['size'])
        # Unpack the zlib compression
        buffer = zlib.decompress(buffer)
    elif signature.startswith( 'Z' ):
        
        uncompressed_size = input.read( 4 )
        
        # hydev thanks based stackexchange search yet again
        # https://stackoverflow.com/a/39777419
        
        try:
            
            five = input.read( 5 )
            unknown_uncompressed_size_8byte = 8 * b'\xff'
            the_rest = input.read()
            
            buffer = lzma.decompress( five + unknown_uncompressed_size_8byte + the_rest )
            
        except Exception as e:
            
            raise Exception( 'This flash file is too weird, could not parse it!' )
            
            

    # Containing rectangle (struct RECT)

    # The number of bits used to store the each of the RECT values are
    # stored in first five bits of the first byte.
    nbits = read_ui8(buffer[:1]) >> 3

    current_byte, buffer = read_ui8(buffer[:1]), buffer[1:]
    bit_cursor = 5

    for item in 'xmin', 'xmax', 'ymin', 'ymax':
        value = 0
        for value_bit in range(nbits - 1, -1, -1):  # == reversed(range(nbits))
            if (current_byte << bit_cursor) & 0x80:
                value |= 1 << value_bit
            # Advance the bit cursor to the next bit
            bit_cursor += 1

            if bit_cursor > 7:
                # We've exhausted the current byte, consume the next one
                # from the buffer.
                current_byte, buffer = read_ui8(buffer[:1]), buffer[1:]
                bit_cursor = 0

        # Convert value from TWIPS to a pixel value
        header[item] = value // 20

    header['width'] = header['xmax'] - header['xmin']
    header['height'] = header['ymax'] - header['ymin']

    # Appendix A of the SWF specification states the following about the FPS
    # field:
    #
    #    [FPS] is supposed to be stored as a 16-bit integer, but the first
    #    byte (or last depending on how you look at it) is completely ignored.
    #
    # We handle this by parsing the value as UI16 and taking only the first
    # byte as the value.
    header['fps'] = read_ui16(buffer[0:2]) >> 8
    header['frames'] = read_ui16(buffer[2:4])

    input.close()
    return header
    
