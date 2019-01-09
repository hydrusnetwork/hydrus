from . import HydrusConstants as HC
import os
import threading
import time
import traceback

#if HC.PLATFORM_WINDOWS: import mp3play

# There used to be hsaudiotag duration stuff here, but I moved it all to FFMPEG

'''
def PlayNoise( name ):
    
    if HC.PLATFORM_OSX: return
    
    if name not in parsed_noises:
        
        if name == 'success': filename = 'success.mp3'
        elif name == 'error': filename = 'error.mp3'
        
        path = os.path.join( HC.STATIC_DIR, filename )
        
        noise = mp3play.load( path )
        
        parsed_noises[ name ] = noise
        
    
    noise = parsed_noises[ name ]
    
    noise.play()
    '''
