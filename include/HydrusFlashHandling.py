import hexagonitswfheader
import HydrusConstants as HC
import traceback

# to all out there who write libraries:
# hexagonit.swfheader is a perfect library. it is how you are supposed to do it.
def GetFlashProperties( path ):
    
    with HC.o( path, 'rb' ) as f:
        
        metadata = hexagonitswfheader.parse( f )
        
        width = metadata[ 'width' ]
        height = metadata[ 'height' ]
        
        num_frames = metadata[ 'frames' ]
        fps = metadata[ 'fps' ]
        
        duration = ( 1000 * num_frames ) / fps
        
        return ( ( width, height ), duration, num_frames )
        
    