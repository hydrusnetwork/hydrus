from . import hexagonitswfheader
from . import HydrusConstants as HC
from . import HydrusData
import os
import subprocess
import time
import traceback

if HC.PLATFORM_LINUX:
    
    SWFRENDER_PATH = os.path.join( HC.BIN_DIR, 'swfrender_linux' )
    
elif HC.PLATFORM_OSX:
    
    SWFRENDER_PATH = os.path.join( HC.BIN_DIR, 'swfrender_osx' )
    
elif HC.PLATFORM_WINDOWS:
    
    SWFRENDER_PATH = os.path.join( HC.BIN_DIR, 'swfrender_win32.exe' )
    
# to all out there who write libraries:
# hexagonit.swfheader is a perfect library. it is how you are supposed to do it.
def GetFlashProperties( path ):
    
    with open( path, 'rb' ) as f:
        
        metadata = hexagonitswfheader.parse( f )
        
        width = metadata[ 'width' ]
        height = metadata[ 'height' ]
        
        num_frames = metadata[ 'frames' ]
        fps = metadata[ 'fps' ]
        
        duration = ( 1000 * num_frames ) // fps
        
        return ( ( width, height ), duration, num_frames )
        
    
def RenderPageToFile( path, temp_path, page_index ):
    
    cmd = [ SWFRENDER_PATH, path,  '-o', temp_path, '-p', str( page_index ) ]
    
    timeout = HydrusData.GetNow() + 60
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs()
    
    p = subprocess.Popen( cmd, **sbp_kwargs )
    
    while p.poll() is None:
        
        if HydrusData.TimeHasPassed( timeout ):
            
            p.terminate()
            
            raise Exception( 'Could not render the swf page within 60 seconds!' )
            
        
        time.sleep( 0.5 )
        
    
    p.communicate()
    
