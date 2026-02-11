import numpy

def adapt_rgb_to_xyz_matrix_to_D50(m_rgb_to_xyz: numpy.ndarray, src_white_xy: tuple[float, float]) -> numpy.ndarray:
    """Given an RGB→XYZ matrix referenced to src_white_xy (typically D65), adapt its XYZ basis to D50."""
    A = generate_bradford_adaptation_matrix(src_white_xy, (0.34567, 0.35850))
    return A @ m_rgb_to_xyz
    

def adapt_white_point( XYZ_src_white, XYZ_dst_white ):
    
    # Bradford adaptation matrix
    M = numpy.array( [
        [ 0.8951,  0.2664, -0.1614],
        [-0.7502,  1.7135,  0.0367],
        [ 0.0389, -0.0685,  1.0296],
    ] )
    
    M_inv = numpy.linalg.inv( M )
    
    src_cone = M @ XYZ_src_white
    dst_cone = M @ XYZ_dst_white
    scale = dst_cone / src_cone
    
    adapt = M_inv @ numpy.diag(scale) @ M
    
    return adapt
    

def chromaticities_to_rgb_to_xyz( white, red, green, blue ):
    
    W = xy_to_xyz( white[0], white[1] )
    R = xy_to_xyz( red[0], red[1] )
    G = xy_to_xyz( green[0], green[1] )
    B = xy_to_xyz( blue[0], blue[1] )
    
    # Build unscaled RGB→XYZ matrix
    M = numpy.column_stack( ( R, G, B ) )
    
    # Solve scaling factors so that M @ S = W
    S = numpy.linalg.solve( M, W )
    
    # Scale each column
    return M * S
    

def float_to_s15Fixed16(val: float) -> int:
    # s15Fixed16Number: signed 32-bit, 16.16 fixed point
    return int(round(val * 65536.0))
    

def generate_bradford_adaptation_matrix(src_xy: tuple[float, float], dst_xy: tuple[float, float] = (0.34567, 0.35850)) -> numpy.ndarray:
    """Bradford chromatic adaptation matrix from src white xy to dst white xy (default D50)."""
    
    # Bradford cone response matrix
    M = numpy.array(
        [
            [0.8951, 0.2664, -0.1614],
            [-0.7502, 1.7135, 0.0367],
            [0.0389, -0.0685, 1.0296],
        ],
        dtype=float,
    )
    
    M_inv = numpy.linalg.inv(M)
    
    src_xyz = xy_to_xyz(*src_xy)
    dst_xyz = xy_to_xyz(*dst_xy)
    
    src_cone = M @ src_xyz
    dst_cone = M @ dst_xyz
    
    scale = numpy.diag(dst_cone / src_cone)
    
    # Adaptation matrix in XYZ space
    return M_inv @ scale @ M
    

def srgb_encode(c):
    
    a = 0.055
    
    return numpy.where(
        c <= 0.0031308,
        12.92 * c,
        (1 + a) * numpy.power(c, 1/2.4) - a
    )
    

def xy_to_xyz(x: float, y: float) -> numpy.ndarray:
    
    return numpy.array([x / y, 1.0, (1.0 - x - y) / y], dtype=float)
    
