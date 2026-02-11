import numpy
import struct

from hydrus.core.files.images import HydrusImageMathSlop as MathSlop

# I've left some old stuff in here but it may be wrong/useless now, caveat emptor

def make_chad_tag_arbitrary_to_D50( src_white_xy ):
    
    chad_matrix = MathSlop.generate_bradford_adaptation_matrix( src_white_xy )
    
    tag = b'sf32' + b'\x00\x00\x00\x00'
    
    # Write matrix values row by row as 32-bit IEEE big-endian floats
    for row in chad_matrix:
        
        for value in row:
            
            tag += struct.pack( '>f', float( value ) )
            
        
    
    return tag
    

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
    

def make_chad_tag_identity() -> bytes:
    # 'sf32' identity 3x3 matrix, row-major, big-endian float32
    I = numpy.eye(3, dtype=float)
    tag = b"sf32" + b"\x00\x00\x00\x00"
    for row in I:
        for v in row:
            tag += struct.pack(">f", float(v))
    tag += b"\x00" * ((4 - (len(tag) % 4)) % 4)
    return tag
    

def make_chad_tag_src_to_D50(src_white_xy: tuple[float, float]) -> bytes:
    # 'sf32' 3x3 matrix, row-major, big-endian float32
    M = MathSlop.generate_bradford_adaptation_matrix(src_white_xy)
    tag = b"sf32" + b"\x00\x00\x00\x00"
    for row in M:
        for v in row:
            tag += struct.pack(">f", float(v))
    tag += b"\x00" * ((4 - (len(tag) % 4)) % 4)
    return tag
    

def make_curv_gamma_tag(gamma: float) -> bytes:
    # 'curv' curveType (ICC v2 classic)
    # For count == 1, the single uInt16 is gamma encoded as u8Fixed8Number.
    # (e.g. gamma 2.2 -> round(2.2 * 256) = 563 -> 0x0233)
    g_u8f8 = int(round(gamma * 256.0))
    g_u8f8 = max(0, min(g_u8f8, 0xFFFF))

    tag = (
        b"curv"
        + b"\x00\x00\x00\x00"
        + struct.pack(">I", 1)  # count
        + struct.pack(">H", g_u8f8)
    )

    # Pad to 4-byte boundary (count=1 leaves us 2 bytes short)
    tag += b"\x00" * ((4 - (len(tag) % 4)) % 4)
    return tag
    

def make_para_curve_tag( gamma: float ):
    
    tag_type = b'para'
    
    reserved = b'\x00\x00\x00\x00'
    
    func_type = struct.pack('>H', 0)  # type 0, one curve mate
    
    reserved2 = b'\x00\x00'
    
    gamma_fixed = struct.pack('>i', MathSlop.float_to_s15Fixed16( gamma ) )
    
    tag = tag_type + reserved + func_type + reserved2 + gamma_fixed
    
    while len(tag) % 4 != 0:
        
        tag += b'\x00'
        
    
    return tag
    

def make_wtpt_tag_D65():
    
    # D50 white point in XYZ
    return pack_xyz_tag( 0.95047, 1.0, 1.08883 )
    

def make_xyz_matrix_tags(m: numpy.ndarray) -> tuple[bytes, bytes, bytes]:
    # ICC expects columns are the XYZ values for R, G, B primaries
    r = pack_xyz_tag(*m[:, 0])
    g = pack_xyz_tag(*m[:, 1])
    b = pack_xyz_tag(*m[:, 2])
    return r, g, b
    

def make_desc_tag(text: str) -> bytes:
    # v2 'desc' textDescriptionType (not v4 mluc)
    # Layout: 'desc' + 4 reserved + uInt32 ASCII count (incl NUL) + ASCII + NUL + padding
    s = text.encode("ascii", errors="strict") + b"\x00"
    tag = b"desc" + b"\x00\x00\x00\x00" + struct.pack(">I", len(s)) + s
    tag += b"\x00" * ((4 - (len(tag) % 4)) % 4)
    return tag
    

def make_text_tag(text: str) -> bytes:
    # v2 'text' type: 'text' + 4 reserved + ASCII bytes (often NUL-terminated, but not required)
    s = text.encode("ascii", errors="replace")
    tag = b"text" + b"\x00\x00\x00\x00" + s
    tag += b"\x00" * ((4 - (len(tag) % 4)) % 4)
    return tag
    

def make_para_curve_tag_gamma(gamma: float) -> bytes:
    # 'para' parametricCurveType
    # Function type 0: Y = X^g, parameter count = 1
    # Layout: 'para' + 4 reserved + uInt16 functionType + uInt16 reserved + s15Fixed16 g
    tag = (
        b"para"
        + b"\x00\x00\x00\x00"
        + struct.pack(">H", 0)
        + b"\x00\x00"
        + struct.pack(">i", MathSlop.float_to_s15Fixed16(gamma))
    )
    tag += b"\x00" * ((4 - (len(tag) % 4)) % 4)
    return tag
    

def make_wtpt_tag_D50() -> bytes:
    # D50 in XYZ (ICC PCS illuminant / media white)
    return pack_xyz_tag(0.9642, 1.0, 0.8249)
    

def pack_xyz_tag(x: float, y: float, z: float) -> bytes:
    # Tag type 'XYZ ' + 4 reserved + three s15Fixed16 XYZ numbers
    return (
        b"XYZ "
        + b"\x00\x00\x00\x00"
        + struct.pack(
            ">iii",
            MathSlop.float_to_s15Fixed16(x),
            MathSlop.float_to_s15Fixed16(y),
            MathSlop.float_to_s15Fixed16(z),
        )
    )
    
