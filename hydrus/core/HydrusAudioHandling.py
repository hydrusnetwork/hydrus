import re
import subprocess

from hydrus.core import HydrusData

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
    
