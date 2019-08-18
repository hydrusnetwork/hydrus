from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusVideoHandling
import os
import re
import subprocess
import threading
import time
import traceback

def ParseFFMPEGAudio( lines ):
    
    # the ^\sStream is to exclude the 'title' line, when it exists, includes the string 'Audio: ', ha ha
    lines_audio = [ l for l in lines if re.search( r'^\s*Stream', l ) is not None and 'Audio: ' in l ]
    
    audio_found = lines_audio != []
    audio_format = None
    
    if audio_found:
        
        line = lines_audio[0]
        
        try:
            
            match = re.search(" [0-9]* Hz", line)
            
            audio_fps = int(line[match.start()+1:match.end()])
            
        except:
            
            audio_fps = 'unknown'
            
        
        try:
            
            match = re.search( r'(?<=Audio\:\s).+?(?=,)', line )
            
            audio_format = match.group()
            
        except:
            
            audio_format = 'unknown'
            
        
    
    return ( audio_found, audio_format )
    
def VideoHasAudio( path ):
    
    info_lines = HydrusVideoHandling.GetFFMPEGInfoLines( path )
    
    ( audio_found, audio_format ) = ParseFFMPEGAudio( info_lines )
    
    if not audio_found:
        
        return False
        
    
    # just because video metadata has an audio stream doesn't mean it has audio. some vids have silent audio streams lmao
    # so, let's read it as PCM and see if there is any noise
    # this obviously only works for single audio stream vids, we'll adapt this if someone discovers a multi-stream mkv with a silent channel that doesn't work here
    
    cmd = [ HydrusVideoHandling.FFMPEG_PATH ]
    
    # this is perhaps not sensible for eventual playback and I should rather go for wav file-like and feed into python 'wave' in order to maintain stereo/mono and so on and have easy chunk-reading
    
    cmd.extend( [ '-i', path,
        '-loglevel', 'quiet',
        '-f', 's16le',
        '-' ] )
        
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs()
    
    try:
        
        process = subprocess.Popen( cmd, bufsize = 65536, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError as e:
        
        HydrusData.ShowText( 'Cannot render audio--FFMPEG not found!' )
        
        raise
        
    
    # silent PCM data is just 00 bytes
    # every now and then, you'll get a couple ffs for some reason, but this is not legit audio data
    
    try:
        
        chunk_of_pcm_data = process.stdout.read( 65536 )
        
        while len( chunk_of_pcm_data ) > 0:
            
            # iterating over bytes gives you ints, recall
            if True in ( b != 0 and b != 255 for b in chunk_of_pcm_data ):
                
                return True
                
            
            chunk_of_pcm_data = process.stdout.read( 65536 )
            
        
        return False
        
    finally:
        
        process.terminate()
        
        process.stdout.close()
        process.stderr.close()
        
    
