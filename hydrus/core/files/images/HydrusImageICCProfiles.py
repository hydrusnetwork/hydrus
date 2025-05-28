import datetime
import numpy
import struct

def make_icc_header( profile_size: int ) -> bytes:
    
    # Here's how Qt does it: https://codebrowser.dev/qt6/qtbase/src/gui/painting/qicc.cpp.html#484
    # QColorSpace: https://codebrowser.dev/qt6/qtbase/src/gui/painting/qcolorspace.cpp.html#734
    # and reads a PNG: https://codebrowser.dev/qt6/qtbase/src/gui/image/qpnghandler.cpp.html#890
    # ICC Spec: https://www.color.org/specification/ICC.1-2022-05.pdf
    
    # ONE OPTION HERE IS JUST TO HAVE A HOOK THAT LOADS IT FROM QT QColorSpace
    # we could compare the icc profile from the jxl with the png one Qt generates. there still seems to be a pixel hash difference, but if the icc profile is the same, no worries about that
    
    now = datetime.datetime.now( datetime.UTC )
    
    # b'\x00\x00\xF6\xD6',              # Rendering intent (0 = perceptual)
    # b'2.1\x00',                       # Profile version (v2.1.0)
    # bytes.fromhex( '02400000' ),      # Profile version (v2.1.0)
    # now.year, now.month, now.day, now.hour, now.minute, now.second # Creation date/time
    # b'    ',                          # Primary platform (unspecified)
    # 0,                                # Flags
    # 0,                                # Device manufacturer
    # 0,                                # Device model
    # 0,                                # Device attributes
    
    return struct.pack(
        '>I4s4s4s4s4s12s4s24sIIII4s44s',
        profile_size,                 # Profile size
        b'lcms',                          # Preferred CMM type
        bytes.fromhex( '04400000' ),      # Profile version (v4.4)
        b'mntr',                          # Profile/device class
        b'RGB ',                          # Data color space
        b'XYZ ',                          # PCS
        b'\x00' * 12,                     # Creation date/time
        b'acsp',                          # ICC Signature
        b'\x00' * 24,                     # Gubbins
        0,                              # Rendering intent (0 = perceptual)
        *[int(x * 65536) for x in (0.9642, 1.0000, 0.8249)],  # PCS illuminant D50 (XYZ)
        b'none',                          # Profile creator
        b'\x00' * 44                      # Reserved
    )
    

def make_desc_tag( text: str ) -> bytes:
    
    s = text.encode('ascii') + b'\x00'
    
    n = len(s)
    
    tag = b'desc' + b'\x00\x00\x00\x00' + struct.pack('>I', n) + s
    
    while len(tag) % 4 != 0:
        
        tag += b'\x00'
        
    
    return tag
    

def float_to_s15Fixed16(val: float) -> int:
    
    return int( round( val * 65536.0 ) )
    

def pack_xyz_tag( x, y, z ):
    
    return (
        b'XYZ ' + b'\x00\x00\x00\x00' +
        struct.pack('>iii', float_to_s15Fixed16(x), float_to_s15Fixed16(y), float_to_s15Fixed16(z))
    )
    

def make_xyz_matrix_tags( m: numpy.ndarray ):
    
    r = pack_xyz_tag( *m[ :, 0 ] )
    g = pack_xyz_tag( *m[ :, 1 ] )
    b = pack_xyz_tag( *m[ :, 2 ] )
    
    return r, g, b
    

def make_para_curve_tag( gamma: float ):
    
    tag_type = b'para'
    
    reserved = b'\x00\x00\x00\x00'
    
    func_type = struct.pack('>H', 0)  # type 0, one curve mate
    
    reserved2 = b'\x00\x00'
    
    gamma_fixed = struct.pack('>i', float_to_s15Fixed16( gamma ) )

    tag = tag_type + reserved + func_type + reserved2 + gamma_fixed
    
    while len(tag) % 4 != 0:
        
        tag += b'\x00'
        
    
    return tag
    

def make_wtpt_tag_D50():
    
    # D50 white point in XYZ
    return pack_xyz_tag( 0.9642, 1.0, 0.8249 )
    

def make_wtpt_tag_D65():
    
    # D50 white point in XYZ
    return pack_xyz_tag( 0.95047, 1.0, 1.08883 )
    

def make_chad_tag_D50():
    
    # sf32 tag type + reserved
    tag = b'sf32' + b'\x00\x00\x00\x00'
    
    # Identity matrix, row-major
    identity = [1.0, 0.0, 0.0,
                0.0, 1.0, 0.0,
                0.0, 0.0, 1.0]
    
    for value in identity:
        
        tag += struct.pack('>f', value)
        
    
    return tag
    

def make_chad_tag_D65_to_D50():
    
    # sf32 tag type + reserved
    tag = b'sf32' + b'\x00\x00\x00\x00'
    
    bradford_d65_to_d50 = [0.9555766, -0.0230393,  0.0631636,
                        -0.0282895, 1.0099416,  0.0210077,
                        0.0122982, -0.0204830,  1.3299098]
    
    for value in bradford_d65_to_d50:
        
        tag += struct.pack( '>f', float( value ) )
        
    
    return tag
    

def xy_to_xyz(x, y):
    
    return numpy.array( [x / y, 1.0, (1 - x - y) / y] )
    

def generate_chromatic_adaptation_matrix( src_xy, dst_xy = (0.34567, 0.35850) ):
    """Compute Bradford chromatic adaptation matrix from src_xy to dst_xy, default dest is D50"""
    
    # I think this matrix is flipped wrong somehow, not sure if this method works correctly or provides the inverse result wew
    # Bradford cone response matrix
    M = numpy.array( [
        [ 0.8951,  0.2664, -0.1614],
        [-0.7502,  1.7135,  0.0367],
        [ 0.0389, -0.0685,  1.0296],
    ] )
    
    M_inv = numpy.linalg.inv( M )
    
    # Convert source and destination xy to XYZ
    src_xyz = xy_to_xyz(*src_xy)
    dst_xyz = xy_to_xyz(*dst_xy)
    
    # Compute cone responses
    src_cone = M @ src_xyz
    dst_cone = M @ dst_xyz
    
    # Diagonal scaling matrix
    scale = numpy.diag( dst_cone / src_cone )
    
    # Final adaptation matrix
    return M_inv @ scale @ M
    

def make_chad_tag_arbitrary_to_D50( src_white_xy ):
    
    chad_matrix = generate_chromatic_adaptation_matrix( src_white_xy )
    
    tag = b'sf32' + b'\x00\x00\x00\x00'

    # Write matrix values row by row as 32-bit IEEE big-endian floats
    for row in chad_matrix:
        
        for value in row:
            
            tag += struct.pack( '>f', float( value ) )
            
        

    return tag
    

def make_gamma_and_chromaticity_icc_profile( gamma: float, white_xy: tuple, chromaticity_xyz_matrix: numpy.ndarray ) -> bytes:
    
    desc = make_desc_tag( 'iccp' )
    rXYZ, gXYZ, bXYZ = make_xyz_matrix_tags( chromaticity_xyz_matrix )
    gamma_para_curve_tag = make_para_curve_tag( gamma )
    
    tags = []
    tag_data_blocks = []
    offset = 128 + 4 + ( 9 * 12 )  # header + tag count + 7 tags
    
    def add_tag( tag_sig, data_bytes ):
        
        nonlocal offset
        
        size = len( data_bytes )
        
        tags.append( ( tag_sig.encode( 'ascii' ), offset, size ) )
        
        tag_data_blocks.append( data_bytes )
        
        pad = (4 - (size % 4)) % 4
        
        offset += size + pad
        
    
    add_tag( 'wtpt', make_wtpt_tag_D65() )
    add_tag( 'chad', make_chad_tag_arbitrary_to_D50( white_xy ) )
    add_tag( 'desc', desc )
    add_tag( 'rXYZ', rXYZ )
    add_tag( 'gXYZ', gXYZ )
    add_tag( 'bXYZ', bXYZ )
    add_tag( 'rTRC', gamma_para_curve_tag )
    add_tag( 'gTRC', gamma_para_curve_tag )
    add_tag( 'bTRC', gamma_para_curve_tag )
    
    # Build tag table
    tag_table = struct.pack('>I', len( tags ) )
    
    for sig, off, sz in tags:
        tag_table += struct.pack('>4sII', sig, off, sz)
    
    profile_body = tag_table + b''.join(
        block + b'\x00' * ((4 - len(block) % 4) % 4)
        for block in tag_data_blocks
    )
    
    profile_size = 128 + len( profile_body )
    header = make_icc_header( profile_size )

    return header + profile_body + b'\x00' * ( 4 - ( profile_size % 4 ) )
    
