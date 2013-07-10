import HydrusConstants as HC
import mp3play
import mutagen
import mutagen.mp3
import os
import threading
import time
import traceback
import wx

parsed_noises = {}

def GetMP3Duration( file ):
    
    filename = HC.TEMP_DIR + os.path.sep + 'mp3_parse.mp3'
    
    with open( filename, 'wb' ) as f: f.write( file )
    
    try: mp3_object = mutagen.mp3.MP3( filename )
    except: raise Exception( 'Could not parse the mp3!' )
    
    length_in_seconds = mp3_object.info.length
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    return length_in_ms
    
def PlayNoise( name ):
    
    if name not in parsed_noises:
        
        if name == 'success': filename = 'success.mp3'
        elif name == 'error': filename = 'error.mp3'
        
        path = HC.STATIC_DIR + os.path.sep + filename
        
        noise = mp3play.load( path )
        
        parsed_noises[ name ] = noise
        
    
    noise = parsed_noises[ name ]
    
    noise.play()
    