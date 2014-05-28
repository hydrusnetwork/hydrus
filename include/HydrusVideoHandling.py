#import numpy.core.multiarray # important this comes before cv!
import ClientConstants as CC
import cv2
from flvlib import tags as flv_tags
import HydrusConstants as HC
import HydrusExceptions
import HydrusImageHandling
import HydrusThreading
import matroska
import os
import traceback
import threading
import time
from wx import wx

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
        
    
def GetVideoFrameDuration( path ):

    cv_video = cv2.VideoCapture( path )
    
    fps = cv_video.get( cv2.cv.CV_CAP_PROP_FPS )
    
    return 1000.0 / fps
    
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
    
class VideoContainer( HydrusImageHandling.RasterContainer ):
    
    NUM_FRAMES_BACKWARDS = 30
    NUM_FRAMES_FORWARDS = 15
    
    def __init__( self, media, target_resolution = None, init_position = 0 ):
        
        HydrusImageHandling.RasterContainer.__init__( self, media, target_resolution )
        
        self._frames = {}
        self._last_index_asked_for = -1
        self._minimum_frame_asked_for = 0
        self._maximum_frame_asked_for = 0
        
        if self._media.GetMime() == HC.IMAGE_GIF: self._durations = HydrusImageHandling.GetGIFFrameDurations( self._path )
        else: self._frame_duration = GetVideoFrameDuration( self._path )
        
        self._renderer = VideoRenderer( self, self._media, self._target_resolution )
        
        num_frames = self.GetNumFrames()
        
        self.SetPosition( init_position )
        
    
    def _MaintainBuffer( self ):
        
        deletees = []
        
        for index in self._frames.keys():
            
            if self._minimum_frame_asked_for < self._maximum_frame_asked_for:
                
                if index < self._minimum_frame_asked_for or self._maximum_frame_asked_for < index: deletees.append( index )
                
            else:
                
                if self._maximum_frame_asked_for < index and index < self._minimum_frame_asked_for: deletees.append( index )
                
            
        
        for i in deletees: del self._frames[ i ]
        
    
    def AddFrame( self, index, frame ): self._frames[ index ] = frame
    
    def GetDuration( self, index ):
        
        if self._media.GetMime() == HC.IMAGE_GIF: return self._durations[ index ]
        else: return self._frame_duration
        
    
    def GetFrame( self, index ):
        
        frame = self._frames[ index ]
        
        self._last_index_asked_for = index
        
        self._MaintainBuffer()
        
        return frame
        
    
    def GetHash( self ): return self._media.GetHash()
    
    def GetKey( self ): return ( self._media.GetHash(), self._target_resolution )
    
    def GetNumFrames( self ): return self._media.GetNumFrames()
    
    def GetResolution( self ): return self._media.GetResolution()
    
    def GetSize( self ): return self._target_resolution
    
    def GetTotalDuration( self ):
        
        if self._media.GetMime() == HC.IMAGE_GIF: return sum( self._durations )
        else: return self._frame_duration * self.GetNumFrames()
        
    
    def GetZoom( self ): return self._zoom
    
    def HasFrame( self, index ): return index in self._frames
    
    def IsScaled( self ): return self._zoom != 1.0
    
    def SetPosition( self, index ):
        
        num_frames = self.GetNumFrames()
        
        if num_frames > self.NUM_FRAMES_BACKWARDS + 1 + self.NUM_FRAMES_FORWARDS:
            
            new_minimum_frame_to_ask_for = max( 0, index - self.NUM_FRAMES_BACKWARDS ) % num_frames
            
            new_maximum_frame_to_ask_for = ( index + self.NUM_FRAMES_FORWARDS ) % num_frames
            
            if index == self._last_index_asked_for: return
            elif index < self._last_index_asked_for:
                
                if index < self._minimum_frame_asked_for:
                    
                    self._minimum_frame_asked_for = new_minimum_frame_to_ask_for
                    
                    self._renderer.SetPosition( self._minimum_frame_asked_for )
                    
                    self._maximum_frame_asked_for = new_maximum_frame_to_ask_for
                    
                    self._renderer.SetRenderToPosition( self._maximum_frame_asked_for)
                    
                
            else:
                
                no_wraparound = self._minimum_frame_asked_for < self._maximum_frame_asked_for
                
                self._minimum_frame_asked_for = new_minimum_frame_to_ask_for
                
                if no_wraparound:
                    
                    if index > self._maximum_frame_asked_for:
                        
                        self._renderer.SetPosition( self._minimum_frame_asked_for )
                        
                    
                
                self._maximum_frame_asked_for = new_maximum_frame_to_ask_for
                
                self._renderer.SetRenderToPosition( self._maximum_frame_asked_for )
                
            
        else:
            
            if self._maximum_frame_asked_for == 0:
                
                self._minimum_frame_asked_for = 0
                
                self._renderer.SetPosition( 0 )
                
                self._maximum_frame_asked_for = num_frames - 1
                
                self._renderer.SetRenderToPosition( self._maximum_frame_asked_for )
                
            
        
        self._MaintainBuffer()

class VideoRenderer():
    
    def __init__( self, image_container, media, target_resolution ):
        
        self._image_container = image_container
        self._media = media
        self._target_resolution = target_resolution
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        self._path = CC.GetFilePath( hash, mime )
        
        self._lock = threading.Lock()
        
        self._cv_video = cv2.VideoCapture( self._path )
        
        self._cv_video.set( cv2.cv.CV_CAP_PROP_CONVERT_RGB, True )
        
        self._current_index = 0
        self._last_index_rendered = -1
        self._last_frame = None
        self._render_to_index = -1
        
    
    def _GetCurrentFrame( self ):
        
        ( retval, cv_image ) = self._cv_video.read()
        
        self._last_index_rendered = self._current_index
        
        num_frames = self._media.GetNumFrames()
        
        self._current_index = ( self._current_index + 1 ) % num_frames
        
        if self._current_index == 0 and self._last_index_rendered != 0:
            
            if self._media.GetMime() == HC.IMAGE_GIF: self._RewindGIF()
            else: self._cv_video.set( cv2.cv.CV_CAP_PROP_POS_FRAMES, 0.0 )
            
        
        if not retval:
            
            raise HydrusExceptions.CantRenderWithCVException( 'CV could not render frame ' + HC.u( self._current_index ) + '.' )
            
        
        return cv_image
        
    
    def _RenderCurrentFrame( self ):
        
        try:
            
            cv_image = self._GetCurrentFrame()
            
            cv_image = HydrusImageHandling.EfficientlyResizeCVImage( cv_image, self._target_resolution )
            
            cv_image = cv2.cvtColor( cv_image, cv2.COLOR_BGR2RGB )
            
            self._last_frame = cv_image
            
        except HydrusExceptions.CantRenderWithCVException:
            
            cv_image = self._last_frame
            
        
        return HydrusImageHandling.GenerateHydrusBitmapFromCVImage( cv_image )
        
    
    def _RenderFrames( self ):
        
        no_frames_yet = True
        
        while True:
            
            try:
                
                yield self._RenderCurrentFrame()
                
                no_frames_yet = False
                
            except HydrusExceptions.CantRenderWithCVException:
                
                if no_frames_yet: raise
                else: break
                
            
        
    
    def _RewindGIF( self ):
        
        self._cv_video.release()
        self._cv_video.open( self._path )
        
        self._current_index = 0
        
    
    def SetRenderToPosition( self, index ):
        
        with self._lock:
            
            if self._render_to_index != index:
                
                self._render_to_index = index
                
                HydrusThreading.CallToThread( self.THREADDoWork )
                
            
        
    
    def SetPosition( self, index ):
        
        with self._lock:
            
            if self._media.GetMime() == HC.IMAGE_GIF:
                
                if index == self._current_index: return
                elif index < self._current_index: self._RewindGIF()
                
                while self._current_index < index: self._GetCurrentFrame()
                
            else:
                
                self._cv_video.set( cv2.cv.CV_CAP_PROP_POS_FRAMES, index )
                
            
            self._render_to_index = index
            
        
    
    def THREADDoWork( self ):
        
        while True:
            
            time.sleep( 0.00001 ) # thread yield
            
            with self._lock:
                
                if self._last_index_rendered != self._render_to_index:
                    
                    index = self._current_index
                    
                    frame = self._RenderCurrentFrame()
                    
                    wx.CallAfter( self._image_container.AddFrame, index, frame )
                    
                else: break
                
            
        
    
        
        
    
    