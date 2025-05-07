from hydrus.external import hexagonitswfheader

# to all out there who write libraries:
# hexagonit.swfheader is a perfect library. it is how you are supposed to do it.
def GetFlashProperties( path ):
    
    with open( path, 'rb' ) as f:
        
        metadata = hexagonitswfheader.parse( f )
        
        # abs since one flash delivered negatives, and hexagonit calcs by going width = ( xmax - xmin ) etc...
        
        width = abs( metadata[ 'width' ] )
        height = abs( metadata[ 'height' ] )
        
        num_frames = metadata[ 'frames' ]
        fps = metadata[ 'fps' ]
        
        if fps is None or fps == 0:
            
            fps = 1
            
        
        duration_ms = int( ( num_frames / fps ) * 1000 )
        
        return ( ( width, height ), duration_ms, num_frames )
        
    
