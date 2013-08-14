import numpy.core.multiarray # important this comes before cv!
import cv
from flvlib import tags as flv_tags
import HydrusConstants as HC
import os
import traceback

def GetFLVProperties( path ):
    
    with open( path, 'rb' ) as f:
        
        flv = flv_tags.FLV( f )
        
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
        

def GetCVVideoProperties( path ):
    
    cvcapture = cv.CaptureFromFile( path )
    
    num_frames = int( cv.GetCaptureProperty( cvcapture, cv.CV_CAP_PROP_FRAME_COUNT ) )
    
    fps = cv.GetCaptureProperty( cvcapture, cv.CV_CAP_PROP_FPS )
    
    length_in_seconds = num_frames / fps
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    duration = length_in_ms
    
    width = int( cv.GetCaptureProperty( cvcapture, cv.CV_CAP_PROP_FRAME_WIDTH ) )
    
    height = int( cv.GetCaptureProperty( cvcapture, cv.CV_CAP_PROP_FRAME_HEIGHT ) )
    
    return ( ( width, height ), duration, num_frames )
    