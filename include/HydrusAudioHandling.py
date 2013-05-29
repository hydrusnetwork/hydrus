import HydrusConstants as HC
import mp3play
import os
import threading
import time
import traceback
import wx

parsed_noises = {}

def PlayNoise( name ):
    
    if name not in parsed_noises:
        
        if name == 'success': filename = 'success.mp3'
        elif name == 'error': filename = 'error.mp3'
        
        path = HC.STATIC_DIR + os.path.sep + filename
        
        noise = mp3play.load( path )
        
        parsed_noises[ name ] = noise
        
    
    noise = parsed_noises[ name ]
    
    noise.play()
    