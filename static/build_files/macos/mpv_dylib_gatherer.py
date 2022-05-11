import ctypes.util
import os
import re
import shutil
import subprocess

print( 'Starting mpv dylib gather.' )

full_path = ctypes.util.find_library( 'mpv' )

if full_path is None:
    
    print( 'Failed to locate library!' )
    
else:
    
    filename = os.path.basename( full_path ) # libmpv.1.dylib or similar
    
    otool_out = subprocess.check_output( [ 'otool', '-L', filename ], encoding = 'utf-8' )
    
    output_dir = 'mpv_dylibs'
    
    #   /usr/local/opt/ffmpeg@4/lib/libavcodec.58.dylib (compatibility version 58.0.0, current version 58.134.100)
    for line in otool_out.splitlines():
        
        # don't want /System/Library stuff, do want /usr/lib stuff
        match = re.search( r'/usr/.*dylib(?=\s\()', line )
        
        if match is not None:
            
            source_path = line[ match.start() : match.end() ]
            
            destination_filename = os.path.basename( source_path )
            destination_path = os.path.join( output_dir, destination_filename )
            
            print( 'Gathering {} to {}.'.format( source_path, destination_path ) )
            
            shutil.copy2( source_path, destination_path )
            
        else:
            
            print( 'Not gathering {}.'.format( line ) )
            
        
    
