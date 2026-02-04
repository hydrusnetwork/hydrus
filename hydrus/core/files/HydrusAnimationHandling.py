import io

import struct

from PIL import Image as PILImage

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.files.images import HydrusImageOpening

def GetAnimationProperties( path, mime ):
    
    pil_image = HydrusImageHandling.GeneratePILImage( path )
    
    ( width, height ) = pil_image.size
    
    width = max( width, 1 )
    height = max( height, 1 )
    
    if mime == HC.ANIMATION_APNG:
        
        ( duration_ms, num_frames ) = GetAPNGDurationMSAndNumFrames( path )
        
    elif mime == HC.ANIMATION_WEBP:
        
        ( frame_durations_ms, times_to_play ) = GetWebPFrameDurationsMS( path )
        
        duration_ms = sum( frame_durations_ms )
        num_frames = len( frame_durations_ms )
        
    else:
        
        ( frame_durations_ms, times_to_play ) = GetFrameDurationsMSPILAnimation( path )
        
        duration_ms = sum( frame_durations_ms )
        num_frames = len( frame_durations_ms )
        
    
    return ( ( width, height ), duration_ms, num_frames )
    

def GetAPNGChunks( file_header_bytes: bytes ) ->list:
    
    # https://wiki.mozilla.org/APNG_Specification
    # a chunk is:
    # 4 bytes of data size, unsigned int
    # 4 bytes of chunk name
    # n bytes of data
    # 4 bytes of CRC
    
    # ok this method went super slow when given a 200MB giga png
    # it turns out list slicing on a very large bytes object is extremely slow
    # so we'll move to a file-like BytesIO and just read the stream like a file
    
    # note lol that if you debug this you'll still get the mega slowdown as your IDE copies the giganto bytes around over and over for variable inspection
    
    chunks = []
    
    buffer = io.BytesIO( file_header_bytes )
    
    # lop off 8 bytes of 'this is a PNG' at the top
    buffer.read( 8 )
    
    while True:
        
        chunk_num_bytes = buffer.read( 4 )
        
        chunk_name = buffer.read( 4 )
        
        if len( chunk_num_bytes ) < 4 or len( chunk_name ) < 4:
            
            break
            
        
        ( num_data_bytes, ) = struct.unpack( '>I', chunk_num_bytes )
        
        chunk_data = buffer.read( num_data_bytes )
        
        if len( chunk_data ) < num_data_bytes:
            
            break
            
        
        buffer.read( 4 )
        
        chunks.append( ( chunk_name, chunk_data ) )
        
    
    # old solution
    '''
    remaining_chunk_bytes = file_header_bytes[8:]
    
    while len( remaining_chunk_bytes ) > 12:
        
        ( num_data_bytes, ) = struct.unpack( '>I', remaining_chunk_bytes[ : 4 ] )
        
        chunk_name = remaining_chunk_bytes[ 4 : 8 ]
        
        chunk_data = remaining_chunk_bytes[ 8 : 8 + num_data_bytes ]
        
        chunks.append( ( chunk_name, chunk_data ) )
        
        remaining_chunk_bytes = remaining_chunk_bytes[ 8 + num_data_bytes + 4 : ]
        
    '''
    
    return chunks
    

def GetAPNGACTLChunkData( file_header_bytes: bytes ) -> bytes | None:
    
    # the acTL chunk can be in different places, but it has to be near the top
    # although it is almost always in fixed position (I think byte 29), we have seen both pHYs and sRGB chunks appear before it
    # so to be proper we need to parse chunks and find the right one
    apng_actl_chunk_header = b'acTL'
    
    chunks = GetAPNGChunks( file_header_bytes )
    
    chunks = dict( chunks )
    
    if apng_actl_chunk_header in chunks:
        
        return chunks[ apng_actl_chunk_header ]
        
    else:
        
        return None
        
    

def GetAPNGDurationMS( apng_bytes: bytes ) -> float:
    
    frame_control_chunk_name = b'fcTL'
    
    chunks = GetAPNGChunks( apng_bytes )
    
    total_duration_s = 0
    
    CRAZY_FALLBACK_FRAME_DURATION_S = 0.1
    MIN_FRAME_DURATION_S = 0.001
    
    for ( chunk_name, chunk_data ) in chunks:
        
        if chunk_name == frame_control_chunk_name and len( chunk_data ) >= 24:
            
            ( delay_numerator, ) = struct.unpack( '>H', chunk_data[20:22] )
            ( delay_denominator, ) = struct.unpack( '>H', chunk_data[22:24] )
            
            if delay_denominator == 0:
                
                duration_s = CRAZY_FALLBACK_FRAME_DURATION_S
                
            else:
                
                duration_s = max( delay_numerator / delay_denominator, MIN_FRAME_DURATION_S )
                
            
            total_duration_s += duration_s
            
        
    
    duration_ms_float = total_duration_s * 1000
    
    duration_ms = int( total_duration_s * 1000 )
    
    if duration_ms == 0 and duration_ms_float > 0:
        
        duration_ms = 1
        
    
    return duration_ms
    

def GetAPNGNumFrames( apng_actl_bytes: bytes ) -> int:
    
    ( num_frames, ) = struct.unpack( '>I', apng_actl_bytes[ : 4 ] )
    
    return num_frames
    

def GetAPNGDurationMSAndNumFrames( path ):
    
    with open( path, 'rb' ) as f:
        
        file_header_bytes = f.read( 256 )
        
    
    apng_actl_bytes = GetAPNGACTLChunkData( file_header_bytes )
    
    if apng_actl_bytes is None:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'This APNG had an unusual file header!' )
        
    
    num_frames = GetAPNGNumFrames( apng_actl_bytes )
    
    with open( path, 'rb' ) as f:
        
        file_bytes = f.read()
        
    
    duration_ms = GetAPNGDurationMS( file_bytes )
    
    return ( duration_ms, num_frames )
    

def GetFrameDurationsMSPILAnimation( path, human_file_description = None ):
    
    pil_image = HydrusImageOpening.RawOpenPILImage( path, human_file_description = human_file_description )
    
    times_to_play = GetTimesToPlayPILAnimationFromPIL( pil_image )
    
    assumed_num_frames = -1
    
    if hasattr( pil_image, 'n_frames' ):
        
        assumed_num_frames = pil_image.n_frames
        
    
    assumed_num_frames_is_sensible = assumed_num_frames > 0
    
    fallback_frame_duration_ms = 83 # (83ms -- 1000 / 12) Set a 12 fps default when duration is missing or too funky to extract. most stuff looks ok at this.
    
    frame_durations_ms = []
    
    i = 0
    
    while True:
        
        if assumed_num_frames_is_sensible and i >= assumed_num_frames:
            
            break
            
        
        try:
            
            pil_image.seek( i )
            
        except EOFError:
            
            break
            
        except Exception as e:
            
            # seek and fellows can raise OSError on a truncated file lmao
            # trying to keep walking through such a gif using PIL is rife with trouble (although mpv may be ok at a later stage), so let's fudge a solution
            
            if len( frame_durations_ms ) > 0:
                
                fill_in_duration = int( sum( frame_durations_ms ) / len( frame_durations_ms ) )
                
            else:
                
                fill_in_duration = fallback_frame_duration_ms
                
            
            if assumed_num_frames_is_sensible:
                
                num_frames_remaining = assumed_num_frames - len( frame_durations_ms )
                
                frame_durations_ms.extend( [ fill_in_duration for j in range( num_frames_remaining ) ] )
                
            
            return ( frame_durations_ms, times_to_play )
            
        
        if 'duration' not in pil_image.info:
            
            duration_ms = fallback_frame_duration_ms
            
        else:
            
            duration_ms = pil_image.info[ 'duration' ]
            
            # In the gif frame header, 10 is stored as 1ms. This 1 is commonly as utterly wrong as 0.
            if duration_ms in ( 0, 10 ):
                
                duration_ms = fallback_frame_duration_ms
                
            
        
        frame_durations_ms.append( duration_ms )
        
        i += 1
        
    
    return ( frame_durations_ms, times_to_play )
    

def GetTimesToPlayAPNG( path: str ) -> int:
    
    with open( path, 'rb' ) as f:
        
        file_header_bytes = f.read( 256 )
        
    
    apng_actl_bytes = GetAPNGACTLChunkData( file_header_bytes )
    
    if apng_actl_bytes is None:
        
        return 0
        
    
    ( num_plays, ) = struct.unpack( '>I', apng_actl_bytes[ 4 : 8 ] )
    
    return num_plays
    

def GetTimesToPlayPILAnimation( path, human_file_description = None ) -> int:
    
    try:
        
        pil_image = HydrusImageOpening.RawOpenPILImage( path, human_file_description = human_file_description )
        
    except HydrusExceptions.UnsupportedFileException:
        
        return 1
        
    
    return GetTimesToPlayPILAnimationFromPIL( pil_image )
    

def GetTimesToPlayPILAnimationFromPIL( pil_image: PILImage.Image ) -> int:
    
    if 'loop' in pil_image.info:
        
        times_to_play = pil_image.info[ 'loop' ]
        
    else:
        
        times_to_play = 1
        
    
    return times_to_play
    

def GetWebPChunks( file_bytes ):
    
    chunks = []
    
    offset = 12  # RIFF/size/WEBP
    
    num_bytes = len( file_bytes )
    
    while offset < num_bytes:
        
        if offset + 8 > num_bytes:
            
            break
            
        
        chunk_type = file_bytes[ offset : offset + 4 ]
        
        chunk_size_bytes = file_bytes[ offset + 4 : offset + 8 ]
        chunk_size = int.from_bytes( chunk_size_bytes, byteorder = 'little' )
        
        chunk_data_start = offset + 8
        
        chunk = file_bytes[ chunk_data_start : chunk_data_start + chunk_size ]
        
        chunks.append( ( chunk_type, chunk ) )
        
        total_chunk_size = 8 + chunk_size
        
        if total_chunk_size % 2 == 1:
            
            total_chunk_size += 1
            
        
        offset += total_chunk_size
        
    
    return chunks
    

def GetWebPFrameDurationsMS( path ):
    
    with open( path, 'rb' ) as f:
        
        file_bytes = f.read()
        
    
    webp_chunks = GetWebPChunks( file_bytes )
    
    fallback_frame_duration_ms = 83 # (83ms -- 1000 / 12) Set a 12 fps default when duration is missing or too funky to extract. most stuff looks ok at this.
    
    frame_durations_ms = []
    times_to_play = 0
    
    for ( chunk_type, chunk ) in webp_chunks:
        
        if chunk_type == b'ANIM':
            
            try:
                
                # Loop is 2 bytes at offset + 4
                
                loop_bytes = chunk[ 4 : 6 ]
                
                times_to_play = int.from_bytes( loop_bytes, byteorder = 'little' )
                
            except Exception as e:
                
                pass
                
            
        elif chunk_type == b'ANMF':
            
            try:
                
                if len( chunk ) < 16:
                    
                    raise ValueError( "ANMF chunk too small" )
                    
                
                # Duration is 3 bytes at offset + 12
                
                duration_bytes = chunk[ 12 : 15 ]
                
                duration_ms = int.from_bytes( duration_bytes, byteorder = 'little' )
                
                if duration_ms == 0:
                    
                    raise Exception( 'Zero-duration frame!' )
                    
                
            except Exception as e:
                
                duration_ms = fallback_frame_duration_ms
                
            
            frame_durations_ms.append( duration_ms )
            
        
    
    return ( frame_durations_ms, times_to_play )
    

def PILAnimationHasDuration( path ):
    
    pil_image = HydrusImageOpening.RawOpenPILImage( path )
    
    try:
        
        if hasattr( pil_image, 'is_animated' ):
            
            return pil_image.is_animated
            
        else:
            
            return False
            
        
    except Exception as e:
        
        return False
        
    

def IsPNGAnimated( file_header_bytes ):
    
    apng_actl_bytes = GetAPNGACTLChunkData( file_header_bytes )
    
    if apng_actl_bytes is not None:
        
        # this is an animated png
        
        # acTL chunk in an animated png is 4 bytes of num frames, then 4 bytes of num times to loop
        # https://wiki.mozilla.org/APNG_Specification#.60acTL.60:_The_Animation_Control_Chunk
        
        num_frames = GetAPNGNumFrames( apng_actl_bytes )
        
        if num_frames > 1:
            
            return True
            
        
    
    return False
    
