import numpy
import struct

from hydrus.core import HydrusDateTime
from hydrus.core.files.images import HydrusImageICCProfilesTagSlop as TagSlop
from hydrus.core.files.images import HydrusImageMathSlop as MathSlop

# ok this is essentially pure sloppa now, but it works for my test files. there were like 5 spec errors in the old hackmess
# the old manual gamma/chromaticity stuff took 10s on a 8,000x7,000 image; it takes about 1s with this ICC Profile

def make_icc_header(profile_size: int) -> bytes:
    """Create a 128-byte ICC header (ICC v2.1)."""
    
    now = HydrusDateTime.nowutc()
    
    # Date/time is 6x uInt16: year, month, day, hour, minute, second
    dt_bytes = struct.pack(">6H", now.year, now.month, now.day, now.hour, now.minute, now.second)
    
    # Device attributes is a uInt64
    device_attributes = 0
    
    # Profile ID is 16 bytes (optional in v2; leave zero)
    profile_id = b"\x00" * 16
    
    # Reserved is 28 bytes
    reserved = b"\x00" * 28
    
    header = b"".join(
        [
            struct.pack(">I", profile_size),  # profile size
            b"lcms",  # preferred CMM type
            bytes.fromhex("02100000"),  # profile version 2.1.0.0
            b"mntr",  # profile/device class
            b"RGB ",  # data color space
            b"XYZ ",  # PCS
            dt_bytes,  # creation date/time
            b"acsp",  # file signature
            b"    ",  # primary platform
            struct.pack(">I", 0),  # profile flags
            struct.pack(">I", 0),  # device manufacturer
            struct.pack(">I", 0),  # device model
            struct.pack(">Q", device_attributes),  # device attributes
            struct.pack(">I", 0),  # rendering intent (0=perceptual)
            struct.pack(">iii",  # PCS illuminant (D50) as XYZNumber
                        MathSlop.float_to_s15Fixed16(0.9642),
                        MathSlop.float_to_s15Fixed16(1.0),
                        MathSlop.float_to_s15Fixed16(0.8249)),
            b"none",  # profile creator
            profile_id,
            reserved,
        ]
    )
    
    return header
    

def make_gamma_and_chromaticity_icc_profile(
    gamma: float,
    chromaticity_xyz_matrix_D50: numpy.ndarray,
) -> bytes:
    
    # Core tags
    desc = TagSlop.make_desc_tag("iccp")
    cprt = TagSlop.make_text_tag("Generated from PNG gamma/chromaticities")
    rXYZ, gXYZ, bXYZ = TagSlop.make_xyz_matrix_tags(chromaticity_xyz_matrix_D50)
    trc = TagSlop.make_curv_gamma_tag(gamma)
    
    # Tag list (sig, data)
    tag_items: list[tuple[bytes, bytes]] = [
        (b"desc", desc),
        (b"cprt", cprt),
        
        # For Display class profiles, mediaWhitePoint is expected to be D50.
        (b"wtpt", TagSlop.make_wtpt_tag_D50()),
        
        # In ICC v2 practice, matrix columns are typically already adapted to D50.
        # Provide identity chad (or omit entirely) to avoid double-adaptation in some CMMs.
        (b"chad", TagSlop.make_chad_tag_identity()),
        
        (b"rXYZ", rXYZ),
        (b"gXYZ", gXYZ),
        (b"bXYZ", bXYZ),
        (b"rTRC", trc),
        (b"gTRC", trc),
        (b"bTRC", trc),
    ]
    
    # Compute offsets in a second pass (header is 128 bytes)
    tag_count = len(tag_items)
    tag_table_size = 4 + tag_count * 12
    offset = 128 + tag_table_size
    
    tag_table = struct.pack(">I", tag_count)
    data_blocks: list[bytes] = []
    
    for sig, data in tag_items:
        data_padded = data + b"\x00" * ((4 - (len(data) % 4)) % 4)
        size = len(data)

        tag_table += struct.pack(">4sII", sig, offset, size)
        data_blocks.append(data_padded)
        offset += len(data_padded)
    
    profile_body = tag_table + b"".join(data_blocks)
    
    # Total profile bytes must be 4-byte aligned, and header size must match *final* size.
    total_size = 128 + len(profile_body)
    final_pad = (4 - (total_size % 4)) % 4
    total_size += final_pad
    
    header = make_icc_header(total_size)
    
    profile = header + profile_body + (b"\x00" * final_pad)
    
    return profile
    
