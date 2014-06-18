#import numpy.core.multiarray # important this comes before cv!
import ClientConstants as CC
import cv2
from flvlib import tags as flv_tags
import HydrusConstants as HC
import HydrusExceptions
import HydrusImageHandling
import HydrusThreading
import matroska
import numpy
import os
import re
import subprocess
import traceback
import threading
import time
from wx import wx

if HC.PLATFORM_LINUX: FFMPEG_PATH = '"' + HC.BIN_DIR + os.path.sep + 'ffmpeg"'
elif HC.PLATFORM_OSX: FFMPEG_PATH = '"' + HC.BIN_DIR + os.path.sep + 'ffmpeg"'
elif HC.PLATFORM_WINDOWS: FFMPEG_PATH = '"' + HC.BIN_DIR + os.path.sep + 'ffmpeg.exe"'

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
    
# This is cribbed from moviepy's FFMPEG_VideoReader
class HydrusFFMPEG_VideoReader( object ):

    def __init__(self, media, print_infos=False, bufsize = None, pix_fmt="rgb24"):
        
        self._media = media
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        self._path = CC.GetFilePath( hash, mime )
        
        self.size = self._media.GetResolution()
        self.duration = float( self._media.GetDuration() ) / 1000.0
        self.nframes = self._media.GetNumFrames()
        
        self.fps = float( self.nframes ) / self.duration
        
        self.pix_fmt = pix_fmt
        
        if pix_fmt == 'rgba': self.depth = 4
        else: self.depth = 3
        
        if bufsize is None:
            
            ( x, y ) = self.size
            bufsize = self.depth * x * y * 5
            

        self.process = None
        
        self.bufsize = bufsize
        
        self.initialize()
        
    
    def __del__( self ):
        
        self.close()
        
    
    def close(self):
        
        if self.process is not None:
            
            self.process.terminate()
            
            self.process.stdout.close()
            self.process.stderr.close()
            
            self.process = None
            
        
    
    def initialize( self, starttime=0 ):
        """Opens the file, creates the pipe. """
        
        self.close()
        
        if starttime != 0:
            
            offset = min( 1, starttime )
            
            i_arg = [ '-ss', "%.03f" % ( starttime - offset ), '-i', '"' + self._path + '"' ]
            
        else: i_arg = [ '-i', '"' + self._path + '"' ]
        
        cmd = ([FFMPEG_PATH]+ i_arg +
                ['-loglevel', 'error',
                '-f', 'image2pipe',
                "-pix_fmt", self.pix_fmt,
                '-vcodec', 'rawvideo', '-'])
        
        self.process = subprocess.Popen( ' '.join( cmd ), shell = True, bufsize= self.bufsize, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        
        self.pos = int( round( self.fps * starttime ) )
        

    def skip_frames(self, n=1):
        
        """Reads and throws away n frames """
        
        ( w, h ) = self.size
        
        for i in range( n ):
            
            self.process.stdout.read( self.depth * w * h )
            self.process.stdout.flush()
            
        
        self.pos += n
        

    def read_frame( self ):
        
        ( w, h ) = self.size
        
        nbytes = self.depth * w * h
        
        s = self.process.stdout.read(nbytes)
        
        self.pos += 1
        
        if len(s) != nbytes:
            
            print( "Warning: in file %s, "%(self._path)+
                   "%d bytes wanted but %d bytes read,"%(nbytes, len(s))+
                   "at frame %d/%d, at time %.02f/%.02f sec. "%(
                    self.pos,self.nframes,
                    1.0*self.pos/self.fps,
                    self.duration)+
                   "Using the last valid frame instead.")
            result = self.lastread
            
            self.close()
            
        else:
            
            result = numpy.fromstring( s, dtype = 'uint8' ).reshape( ( h, w, len( s ) // ( w * h ) ) )
            
            self.lastread = result
            
        
        return result
        
    
    def set_position( self, pos ):
        
        if ( pos < self.pos ) or ( pos > self.pos + 60 ):
            
            starttime = float( pos ) / self.fps
            
            self.initialize( starttime )
            
        else: self.skip_frames( pos - self.pos )
        
    
# same thing; this is cribbed from moviepy
def Hydrusffmpeg_parse_infos(filename, print_infos=False):
    """Get file infos using ffmpeg.

    Returns a dictionnary with the fields:
    "video_found", "video_fps", "duration", "video_nframes",
    "video_duration"
    "audio_found", "audio_fps"

    "video_duration" is slightly smaller than "duration" to avoid
    fetching the uncomplete frames at the end, which raises an error.

    """
    
    # open the file in a pipe, provoke an error, read output
    
    cmd = [FFMPEG_PATH, "-i", '"' + filename + '"']
    
    is_GIF = filename.endswith('.gif')
    
    if is_GIF:
        if HC.PLATFORM_WINDOWS: cmd += ["-f", "null", "NUL"]
        else: cmd += ["-f", "null", "/dev/null"]
    
    proc = subprocess.Popen( ' '.join( cmd ), shell = True, bufsize=10**5, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
    
    infos = proc.stderr.read().decode('utf8')
    proc.terminate()
    
    del proc
    
    if print_infos:
        # print the whole info text returned by FFMPEG
        print( infos )
    
    lines = infos.splitlines()
    if "No such file or directory" in lines[-1]:
        raise IOError("%s not found ! Wrong path ?"%filename)
    
    result = dict()
    
    # get duration (in seconds)
    try:
        keyword = ('frame=' if is_GIF else 'Duration: ')
        line = [l for l in lines if keyword in l][0]
        match = re.search("[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9]", line)
        hms = map(float, line[match.start()+1:match.end()].split(':'))
        
        if len(hms) == 1:
            result['duration'] = hms[0]
        elif len(hms) == 2:
            result['duration'] = 60*hms[0]+hms[1]
        elif len(hms) ==3:
            result['duration'] = 3600*hms[0]+60*hms[1]+hms[2]
        
    except:
        raise IOError("Error reading duration in file %s,"%(filename)+
                      "Text parsed: %s"%infos)

    # get the output line that speaks about video
    lines_video = [l for l in lines if ' Video: ' in l]
    
    result['video_found'] = ( lines_video != [] )
    
    if result['video_found']:
        
        line = lines_video[0]

        # get the size, of the form 460x320 (w x h)
        match = re.search(" [0-9]*x[0-9]*(,| )", line)
        s = list(map(int, line[match.start():match.end()-1].split('x')))
        result['video_size'] = s


        # get the frame rate
        try:
            match = re.search("( [0-9]*.| )[0-9]* tbr", line)
            result['video_fps'] = float(line[match.start():match.end()].split(' ')[1])
        except:
            match = re.search("( [0-9]*.| )[0-9]* fps", line)
            result['video_fps'] = float(line[match.start():match.end()].split(' ')[1])

        result['video_nframes'] = int(result['duration']*result['video_fps'])+1

        result['video_duration'] = result['duration']
        # We could have also recomputed the duration from the number
        # of frames, as follows:
        # >>> result['video_duration'] = result['video_nframes'] / result['video_fps']


    lines_audio = [l for l in lines if ' Audio: ' in l]
    
    result['audio_found'] = lines_audio != []
    
    if result['audio_found']:
        line = lines_audio[0]
        try:
            match = re.search(" [0-9]* Hz", line)
            result['audio_fps'] = int(line[match.start()+1:match.end()])
        except:
            result['audio_fps'] = 'unknown'

    return result

class VideoContainer( HydrusImageHandling.RasterContainer ):
    
    BUFFER_SIZE = 1024 * 1024 * 96
    
    def __init__( self, media, target_resolution = None, init_position = 0 ):
        
        HydrusImageHandling.RasterContainer.__init__( self, media, target_resolution )
        
        self._frames = {}
        self._last_index_asked_for = -1
        self._minimum_frame_asked_for = 0
        self._maximum_frame_asked_for = 0
        
        ( x, y ) = self._target_resolution
        
        frame_buffer_length = self.BUFFER_SIZE / ( x * y * 3 )
        
        self._num_frames_backwards = frame_buffer_length * 2 / 3
        self._num_frames_forwards = frame_buffer_length / 3
        
        if self._media.GetMime() == HC.IMAGE_GIF: self._durations = HydrusImageHandling.GetGIFFrameDurations( self._path )
        else: self._frame_duration = GetVideoFrameDuration( self._path )
        
        self._renderer = VideoRendererMoviePy( self, self._media, self._target_resolution )
        
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
        
        if num_frames > self._num_frames_backwards + 1 + self._num_frames_forwards:
            
            new_minimum_frame_to_ask_for = max( 0, index - self._num_frames_backwards ) % num_frames
            
            new_maximum_frame_to_ask_for = ( index + self._num_frames_forwards ) % num_frames
            
            if index == self._last_index_asked_for: return
            elif index < self._last_index_asked_for:
                
                if index < self._minimum_frame_asked_for:
                    
                    self._minimum_frame_asked_for = new_minimum_frame_to_ask_for
                    
                    self._renderer.SetPosition( self._minimum_frame_asked_for )
                    
                    self._maximum_frame_asked_for = new_maximum_frame_to_ask_for
                    
                    self._renderer.SetRenderToPosition( self._maximum_frame_asked_for )
                    
                
            else: # index > self._last_index_asked_for
                
                currently_no_wraparound = self._minimum_frame_asked_for < self._maximum_frame_asked_for
                
                self._minimum_frame_asked_for = new_minimum_frame_to_ask_for
                
                if currently_no_wraparound:
                    
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
        

class VideoRendererCV():
    
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
                
            
        
    
class VideoRendererMoviePy():
    
    def __init__( self, image_container, media, target_resolution ):
        
        self._image_container = image_container
        self._media = media
        self._target_resolution = target_resolution
        
        self._lock = threading.Lock()
        
        ( x, y ) = media.GetResolution()
        
        self._ffmpeg_reader = HydrusFFMPEG_VideoReader( media, bufsize = x * y * 3 * 5 )
        
        self._current_index = 0
        self._last_index_rendered = -1
        self._last_frame = None
        self._render_to_index = -1
        
    
    def _GetCurrentFrame( self ):
        
        try: image = self._ffmpeg_reader.read_frame()
        except Exception as e: raise HydrusExceptions.CantRenderWithCVException( 'FFMPEG could not render frame ' + HC.u( self._current_index ) + '.' + os.linesep * 2 + HC.u( e ) )
        
        self._last_index_rendered = self._current_index
        
        num_frames = self._media.GetNumFrames()
        
        self._current_index = ( self._current_index + 1 ) % num_frames
        
        if self._current_index == 0 and self._last_index_rendered != 0: self._ffmpeg_reader.initialize()
        
        return image
        
    
    def _RenderCurrentFrame( self ):
        
        try:
            
            image = self._GetCurrentFrame()
            
            image = HydrusImageHandling.EfficientlyResizeCVImage( image, self._target_resolution )
            
            self._last_frame = image
            
        except HydrusExceptions.CantRenderWithCVException:
            
            if self._last_frame is None: raise
            
            image = self._last_frame
            
        
        return HydrusImageHandling.GenerateHydrusBitmapFromCVImage( image )
        
    
    def _RenderFrames( self ):
        
        no_frames_yet = True
        
        while True:
            
            try:
                
                yield self._RenderCurrentFrame()
                
                no_frames_yet = False
                
            except HydrusExceptions.CantRenderWithCVException:
                
                if no_frames_yet: raise
                else: break
                
            
        
    
    def SetRenderToPosition( self, index ):
        
        with self._lock:
            
            if self._render_to_index != index:
                
                self._render_to_index = index
                
                HydrusThreading.CallToThread( self.THREADDoWork )
                
            
        
    
    def SetPosition( self, index ):
        
        with self._lock:
            
            if index == self._current_index: return
            else:
                
                if self._media.GetMime() == HC.IMAGE_GIF:
                    
                    if index < self._current_index:
                        
                        self._ffmpeg_reader.initialize()
                        
                        self._ffmpeg_reader.skip_frames( index )
                        
                    
                else:
                    
                    timecode = float( index ) / self._ffmpeg_reader.fps
                    
                    self._ffmpeg_reader.set_position( timecode )
                    
                
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
                
            
        
    