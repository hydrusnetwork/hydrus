#import numpy.core.multiarray # important this comes before cv!
import cv2
from flvlib import tags as flv_tags
import HydrusConstants as HC
import matroska
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
    
    capture = cv2.VideoCapture( path )
    
    num_frames = int( capture.get( cv2.cv.CV_CAP_PROP_FRAME_COUNT ) )
    
    fps = capture.get( cv2.cv.CV_CAP_PROP_FPS )
    
    length_in_seconds = num_frames / fps
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    duration = length_in_ms
    
    width = int( capture.get( cv2.cv.CV_CAP_PROP_FRAME_WIDTH ) )
    
    height = int( capture.get( cv2.cv.CV_CAP_PROP_FRAME_HEIGHT ) )
    
    return ( ( width, height ), duration, num_frames )
    
def GetMatroskaOrWebm( path ):
    
    tags = matroska.parse( path )
    
    ebml = tags[ 'EBML' ][0]
    
    if ebml[ 'DocType' ][0] == 'matroska': return HC.VIDEO_MKV
    elif ebml[ 'DocType' ][0] == 'webm': return HC.VIDEO_WEBM
    
    raise Exception()
    
def GetMatroskaOrWebMProperties( path ):
    
    tags = matroska.parse( path )
    
    segment = tags['Segment'][0]
    
    info = segment['Info'][0]
    duration = int( ( info['Duration'][0] * info['TimecodeScale'][0] / 1e9 ) * 1000 )
    
    tracks = segment['Tracks'][0]
    trackentries = tracks['TrackEntry']
    
    for trackentry in trackentries:
        
        if 'Video' in trackentry:
            
            video = trackentry['Video'][0]
            
            width = video[ 'PixelWidth' ][0]
            height = video[ 'PixelHeight' ][0]
            
            break
            
        
    
    num_frames = 0
    
    return ( ( width, height ), duration, num_frames )
    