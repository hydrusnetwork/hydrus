import cStringIO
from flvlib import tags as flv_tags
import HydrusConstants as HC
import mutagen
import mutagen.mp4
import os
import traceback

def GetFLVProperties( file ):
    
    file_handle = cStringIO.StringIO( file )
    
    flv = flv_tags.FLV( file_handle )
    
    script_tag = None
    
    for tag in flv.iter_tags():
        
        if isinstance( tag, flv_tags.ScriptTag ):
            
            script_tag = tag
            
            break
            
        
    
    width = 853
    height = 480
    duration = 0
    num_frames = 0
    
    if script_tag is not None:
        
        tag_dict = script_tag.variable
        
        # tag_dict can sometimes be a float?
        # it is on the broken one I tried!
        
        if 'width' in tag_dict: width = tag_dict[ 'width' ]
        if 'height' in tag_dict: height = tag_dict[ 'height' ]
        if 'duration' in tag_dict: duration = int( tag_dict[ 'duration' ] * 1000 )
        if 'framerate' in tag_dict: num_frames = int( ( duration / 1000.0 ) * tag_dict[ 'framerate' ] )
        
    
    return ( ( width, height ), duration, num_frames )

def GetMP4Duration( file ):
    
    # wait, this only does the audio component!
    
    filename = HC.TEMP_DIR + os.path.sep + 'mp4_parse.mp4'
    
    with HC.o( filename, 'wb' ) as f: f.write( file )
    
    try: mp4_object = mutagen.mp4.MP4( filename )
    except: raise Exception( 'Could not parse the mp4!' )
    
    length_in_seconds = mp4_object.info.length
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    return length_in_ms
    