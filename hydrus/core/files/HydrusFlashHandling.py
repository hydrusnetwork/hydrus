import os
import subprocess
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime

from hydrus.external import hexagonitswfheader

if HC.PLATFORM_LINUX:
    
    SWFRENDER_PATH = os.path.join( HC.BIN_DIR, 'swfrender_linux' )
    
elif HC.PLATFORM_MACOS:
    
    SWFRENDER_PATH = os.path.join( HC.BIN_DIR, 'swfrender_osx' )
    
elif HC.PLATFORM_WINDOWS:
    
    SWFRENDER_PATH = os.path.join( HC.BIN_DIR, 'swfrender_win32.exe' )
    

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
            
        
        duration = ( 1000 * num_frames ) // fps
        
        return ( ( width, height ), duration, num_frames )
        
    

def RenderPageToFile( path, temp_path, page_index ):
    
    cmd = [ SWFRENDER_PATH, path,  '-o', temp_path, '-p', str( page_index ) ]
    
    timeout = HydrusTime.GetNow() + 60
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs()
    
    sbp_kwargs[ 'stdout' ] = subprocess.DEVNULL
    sbp_kwargs[ 'stderr' ] = subprocess.DEVNULL
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    p = subprocess.Popen( cmd, **sbp_kwargs )
    
    while p.poll() is None:
        
        if HydrusTime.TimeHasPassed( timeout ):
            
            p.terminate()
            
            raise Exception( 'Could not render the swf page within 60 seconds!' )
            
        
        time.sleep( 0.5 )
        
    
    HydrusThreading.SubprocessCommunicate( p )
    
