import hsaudiotag
import hsaudiotag.auto
import hsaudiotag.flac
import hsaudiotag.mpeg
import hsaudiotag.ogg
import HydrusConstants as HC
import os
import threading
import time
import traceback

#if HC.PLATFORM_WINDOWS: import mp3play

parsed_noises = {}

def GetFLACDuration( path ):
    
    hsaudio_object = hsaudiotag.flac.FLAC( path )
    
    if not hsaudio_object.valid: raise Exception( 'FLAC file was not valid!' )
    
    length_in_seconds = hsaudio_object.duration
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    return length_in_ms
    
def GetMP3Duration( path ):
    
    hsaudio_object = hsaudiotag.mpeg.Mpeg( path )
    
    if not hsaudio_object.valid: raise Exception( 'MP3 file was not valid!' )
    
    length_in_seconds = hsaudio_object.duration
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    return length_in_ms
    
def GetOGGVorbisDuration( path ):
    
    hsaudio_object = hsaudiotag.ogg.Vorbis( path )
    
    if not hsaudio_object.valid: raise Exception( 'Ogg Vorbis file was not valid!' )
    
    length_in_seconds = hsaudio_object.duration
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    return length_in_ms
    
def GetWMADuration( path ):
    
    hsaudio_object = hsaudiotag.wma.WMADecoder( path )
    
    if not hsaudio_object.valid: raise Exception( 'WMA file was not valid!' )
    
    length_in_seconds = hsaudio_object.duration
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    return length_in_ms

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