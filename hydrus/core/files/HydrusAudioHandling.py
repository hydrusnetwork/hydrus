import re

def ParseFFMPEGAudio( lines ):
    
    # the ^\sStream is to exclude the 'title' line, when it exists, includes the string 'Audio: ', ha ha
    lines_audio = [ line for line in lines if re.search( r'^\s*Stream', line ) is not None and 'Audio: ' in line ]
    
    audio_found = lines_audio != []
    audio_format = None
    
    if audio_found:
        
        line = lines_audio[0]
        
        try:
            
            match = re.search(" [0-9]* Hz", line)
            
            audio_fps = int(line[match.start()+1:match.end()])
            
        except Exception as e:
            
            audio_fps = 'unknown'
            
        
        try:
            
            match = re.search( r'(?<=Audio:\s).+?(?=,)', line )
            
            audio_format = match.group()
            
        except Exception as e:
            
            audio_format = 'unknown'
            
        
    
    return ( audio_found, audio_format )
    
