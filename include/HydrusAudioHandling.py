import HydrusConstants as HC
import mp3play
import mutagen
import mutagen.flac
import mutagen.mp3
import mutagen.oggvorbis
import os
import threading
import time
import traceback
import wx

parsed_noises = {}

def GetFLACDuration( file ):
    
    path = HC.TEMP_DIR + os.path.sep + 'flac_parse.flac'
    
    with HC.o( path, 'wb' ) as f: f.write( file )
    
    try: flac_object = mutagen.flac.FLAC( path )
    except: raise Exception( 'Could not parse the ogg!' )
    
    length_in_seconds = flac_object.info.length
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    del flac_object
    
    os.unlink( path )
    
    return length_in_ms
    
def GetMP3Duration( file ):
    
    path = HC.TEMP_DIR + os.path.sep + 'mp3_parse.mp3'
    
    with HC.o( path, 'wb' ) as f: f.write( file )
    
    try: mp3_object = mutagen.mp3.MP3( path )
    except: raise Exception( 'Could not parse the mp3!' )
    
    length_in_seconds = mp3_object.info.length
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    del mp3_object
    
    os.unlink( path )
    
    return length_in_ms
    
def GetOGGVorbisDuration( file ):
    
    path = HC.TEMP_DIR + os.path.sep + 'oggvorbis_parse.ogg'
    
    with HC.o( path, 'wb' ) as f: f.write( file )
    
    try: ogg_object = mutagen.oggvorbis.OggVorbis( path )
    except: raise Exception( 'Could not parse the ogg!' )
    
    length_in_seconds = ogg_object.info.length
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    del ogg_object
    
    os.unlink( path )
    
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
    