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
    
def GetFFMPEGVideoProperties( path ):
    
    info = Hydrusffmpeg_parse_infos( path )
    
    ( w, h ) = info[ 'video_size' ]
    
    duration_in_s = info[ 'duration' ]
    
    duration = int( duration_in_s * 1000 )
    
    num_frames = info[ 'video_nframes' ]
    
    return ( ( w, h ), duration, num_frames )
    
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
    
# this is cribbed from moviepy
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
    
    # always perform fast null-output
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
    # fetch 'result line'
    # gif: frame=   52 fps=0.0 q=0.0 Lsize=N/A time=00:00:02.05 bitrate=N/A
    # vid: frame=  467 fps=0.0 q=0.0 Lsize=N/A time=00:00:19.45 bitrate=N/A
    try:
        line = [l for l in lines if "frame=" in l][0]

        _frames = None
        _offset = 0.0
        _duration = None
            
        match_frames = re.search(r'(?<=frame\=).+?(?=fps)', line)        
        if match_frames != None:
            _frames = int(match_frames.group().strip())

        # get duration from result line, because "Duration" line can be "N/A", result-line always has a time
        match_duration = re.search(r"(?<=time\=)(?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d)\.(?P<ms>\d\d)", line)
        if match_duration != None and len(match_duration.groups()) == 4:
            _hours = int(match_duration.group('hour'))
            _minutes = int(match_duration.group('minute'))
            _seconds = _hours * 60 * 60 + _minutes * 60 * 60 + int(match_duration.group('second'))
            
            _duration = float('{}.{}'.format(_seconds, match_duration.group('ms')))
        
        
        # get duration and start-offset
        line = [l for l in lines if "Duration: " in l][0]
        
        match_startOffset = re.search(r'(?<=start\:).*?(?P<offset>[\d\.]+?)(?=\,)', line)
        if match_startOffset != None and len(match_startOffset.groups()) > 0:
            _offset = float(match_startOffset.group('offset').strip())

    
        result[ 'duration' ] = _duration - _offset
    
        result['video_fps'] = 24.0 if _frames == None or _duration == None else _frames / _duration
        result['video_duration'] = result['duration']
        result['video_nframes'] = _frames

    except:
        raise IOError("Error reading duration in file %s,"%(filename)+
                      "Text parsed: %s"%infos)
        
    # get information about stream size
    # and override fps if found
    #
    # line starts with Stream
    # Stream #0:0: Video: vp8, yuv420p, 720x408, SAR 8:13 DAR 240:221, 29.97 fps, 29.97 tbr, 1k tbn, 1k tbc (default)
        
    lines_stream = [l for l in lines if 'Stream #' in l]
    if len(lines_stream) > 0:
        line = lines_stream[0]
        
        match_frames = re.search(r'(?<=\, )(?P<width>\d+)x(?P<height>\d+)\,.+?(?P<fps>[\.\d]+) fps', line)
        if match_frames != None and len(match_frames.groups()) == 3:
            result['video_size'] = (int(match_frames.group('width')), int(match_frames.group('height')))
            result['video_fps'] = float(match_frames.group('fps'))


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
        self._buffer_start_index = -1
        self._buffer_end_index = -1
        
        ( x, y ) = self._target_resolution
        
        frame_buffer_length = self.BUFFER_SIZE / ( x * y * 3 )
        
        self._num_frames_backwards = frame_buffer_length * 2 / 3
        self._num_frames_forwards = frame_buffer_length / 3
        
        self._render_lock = threading.Lock()
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        path = CC.GetFilePath( hash, mime )
        
        duration = self._media.GetDuration()
        num_frames = self._media.GetNumFrames()
        
        #subprocess.Popen('echo {}'.format(duration), shell=True)

        # 24fps => 1 frame -> 41.66ms
        self._frame_duration = 41.66 if duration == None or num_frames == None else duration / num_frames
        
        self._ffmpeg_reader = VideoRendererFFMPEG( path, mime, duration, num_frames, target_resolution )
        
        self._next_render_index = 0
        self._render_to_index = -1
        self._rendered_first_frame = False
        
        self.SetPosition( init_position )
        
    
    def _MaintainBuffer( self ):
        
        deletees = []
        
        for index in self._frames.keys():
            
            if self._buffer_start_index < self._buffer_end_index:
                
                if index < self._buffer_start_index or self._buffer_end_index < index: deletees.append( index )
                
            else:
                
                if self._buffer_end_index < index and index < self._buffer_start_index: deletees.append( index )
                
            
        
        for i in deletees: del self._frames[ i ]
        
    
    def _RENDERERSetRenderToPosition( self, index ):
        
        with self._render_lock:
            
            if self._render_to_index != index:
                
                self._render_to_index = index
                
                HydrusThreading.CallToThread( self.THREADRender )
                
            
        
    
    def _RENDERERSetPosition( self, index ):
        
        with self._render_lock:
            
            if index == self._next_render_index: return
            else:
                
                self._ffmpeg_reader.set_position( index )
                
                self._next_render_index = index
                self._render_to_index = index
                
            
        
    
    def THREADRender( self ):
        
        num_frames = self._media.GetNumFrames()
        
        while True:
            
            time.sleep( 0.00001 ) # thread yield
            
            with self._render_lock:
                
                if not self._rendered_first_frame or self._next_render_index != ( self._render_to_index + 1 ) % num_frames:
                    
                    self._rendered_first_frame = True
                    
                    frame_index = self._next_render_index # keep this before the get call, as it increments in a clock arithmetic way afterwards
                    
                    try: numpy_image = self._ffmpeg_reader.read_frame()
                    except Exception as e:
                        
                        HC.ShowException( e )
                        
                        break
                        
                    finally: self._next_render_index = ( self._next_render_index + 1 ) % num_frames
                    
                    frame = HydrusImageHandling.GenerateHydrusBitmapFromNumPyImage( numpy_image )
                    
                    wx.CallAfter( self.AddFrame, frame_index, frame )
                    
                else: break
                
            
        
    
    def AddFrame( self, index, frame ): self._frames[ index ] = frame
    
    def GetDuration( self, index ): return self._frame_duration
        
    
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
    
    def GetTotalDuration( self ): return self._frame_duration * self.GetNumFrames()
        
    
    def GetZoom( self ): return self._zoom
    
    def HasFrame( self, index ): return index in self._frames
    
    def IsScaled( self ): return self._zoom != 1.0
    
    def SetPosition( self, index ):
        
        num_frames = self.GetNumFrames()
        
        if num_frames > self._num_frames_backwards + 1 + self._num_frames_forwards:
            
            new_buffer_start_index = max( 0, index - self._num_frames_backwards ) % num_frames
            
            new_buffer_end_index = ( index + self._num_frames_forwards ) % num_frames
            
            if index == self._last_index_asked_for: return
            elif index < self._last_index_asked_for:
                
                if index < self._buffer_start_index:
                    
                    self._buffer_start_index = new_buffer_start_index
                    
                    self._RENDERERSetPosition( self._buffer_start_index )
                    
                    self._buffer_end_index = new_buffer_end_index
                    
                    self._RENDERERSetRenderToPosition( self._buffer_end_index )
                    
                
            else: # index > self._last_index_asked_for
                
                currently_no_wraparound = self._buffer_start_index < self._buffer_end_index
                
                self._buffer_start_index = new_buffer_start_index
                
                if currently_no_wraparound:
                    
                    if index > self._buffer_end_index:
                        
                        self._RENDERERSetPosition( self._buffer_start_index )
                        
                    
                
                self._buffer_end_index = new_buffer_end_index
                
                self._RENDERERSetRenderToPosition( self._buffer_end_index )
                
            
        else:
            
            if self._buffer_end_index == -1:
                
                self._buffer_start_index = 0
                
                self._RENDERERSetPosition( 0 )
                
                self._buffer_end_index = num_frames - 1
                
                self._RENDERERSetRenderToPosition( self._buffer_end_index )
                
            
        
        self._MaintainBuffer()
        

# This was built from moviepy's FFMPEG_VideoReader
class VideoRendererFFMPEG( object ):

    def __init__( self, path, mime, duration, num_frames, target_resolution, pix_fmt = "rgb24" ):
        
        self._path = path
        self._mime = mime
        self._duration = float( duration )
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        
        self.fps = float( self._num_frames ) / self._duration
        
        if self.fps == 0: self.fps = 24
        
        self.pix_fmt = pix_fmt
        
        if pix_fmt == 'rgba': self.depth = 4
        else: self.depth = 3
        
        ( x, y ) = self._target_resolution
        bufsize = self.depth * x * y
        
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
            
        
    
    def initialize( self, start_index = 0 ):
        
        self.close()
        
        if self._mime == HC.IMAGE_GIF:
            
            ss = 0
            self.pos = 0
            skip_frames = start_index
            
        else:
            
            ss = float( start_index ) / self.fps
            self.pos = start_index
            skip_frames = 0
            
        
        ( w, h ) = self._target_resolution
        
        cmd = ( [ FFMPEG_PATH,
            '-ss', "%.03f" % ss,
            '-i', '"' + self._path + '"',
            '-loglevel', 'quiet',
            '-f', 'image2pipe',
            "-pix_fmt", self.pix_fmt,
            "-s", str( w ) + 'x' + str( h ),
            '-vcodec', 'rawvideo', '-' ] )
        
        self.process = subprocess.Popen( ' '.join( cmd ), shell = True, bufsize= self.bufsize, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        
        self.skip_frames( skip_frames )
        
    
    def skip_frames( self, n ):
        
        ( w, h ) = self._target_resolution
        
        for i in range( n ):
            
            self.process.stdout.read( self.depth * w * h )
            
            self.process.stdout.flush()
            
            self.pos += 1
            
        
    
    def read_frame( self ):
        
        if self.pos == self._num_frames: self.initialize()
        
        if self.process is None: result = self.lastread
        else:
            
            ( w, h ) = self._target_resolution
            
            nbytes = self.depth * w * h
            
            s = self.process.stdout.read(nbytes)
            
            if len(s) != nbytes:
                
                print( "Warning: in file %s, "%(self._path)+
                       "%d bytes wanted but %d bytes read,"%(nbytes, len(s))+
                       "at frame %d/%d, at time %.02f/%.02f sec. "%(
                        self.pos,self._num_frames,
                        1.0*self.pos/self.fps,
                        self._duration)+
                       "Using the last valid frame instead.")
                
                result = self.lastread
                
                self.close()
                
            else:
                
                result = numpy.fromstring( s, dtype = 'uint8' ).reshape( ( h, w, len( s ) // ( w * h ) ) )
                
                self.lastread = result
                
            
        
        self.pos += 1
        
        return result
        
    
    def set_position( self, pos ):
        
        rewind = pos < self.pos
        jump_a_long_way_ahead = pos > self.pos + 60
        
        if rewind or jump_a_long_way_ahead: self.initialize( pos )
        else: self.skip_frames( pos - self.pos )
        
    
class OLDCODEVideoRendererCV():
    
    def __init__( self, image_container, media, target_resolution ):
        
        self._image_container = image_container
        self._media = media
        self._target_resolution = target_resolution
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        self._path = CC.GetFilePath( hash, mime )
        
        self._render_lock = threading.Lock()
        
        self._cv_video = cv2.VideoCapture( self._path )
        
        self._cv_video.set( cv2.cv.CV_CAP_PROP_CONVERT_RGB, True )
        
        self._next_render_index = 0
        self._last_index_rendered = -1
        self._last_frame = None
        self._render_to_index = -1
        
    
    def _GetCurrentFrame( self ):
        
        ( retval, cv_image ) = self._cv_video.read()
        
        self._last_index_rendered = self._next_render_index
        
        num_frames = self._media.GetNumFrames()
        
        self._next_render_index = ( self._next_render_index + 1 ) % num_frames
        
        if self._next_render_index == 0 and self._last_index_rendered != 0:
            
            if self._media.GetMime() == HC.IMAGE_GIF: self._RewindGIF()
            else: self._cv_video.set( cv2.cv.CV_CAP_PROP_POS_FRAMES, 0.0 )
            
        
        if not retval:
            
            raise HydrusExceptions.CantRenderWithCVException( 'CV could not render frame ' + HC.u( self._next_render_index ) + '.' )
            
        
        return cv_image
        
    
    def _RenderCurrentFrame( self ):
        
        try:
            
            cv_image = self._GetCurrentFrame()
            
            cv_image = HydrusImageHandling.EfficientlyResizeCVImage( cv_image, self._target_resolution )
            
            cv_image = cv2.cvtColor( cv_image, cv2.COLOR_BGR2RGB )
            
            self._last_frame = cv_image
            
        except HydrusExceptions.CantRenderWithCVException:
            
            cv_image = self._last_frame
            
        
        return HydrusImageHandling.GenerateHydrusBitmapFromNumPyImage( cv_image )
        
    
    def _RewindGIF( self ):
        
        self._cv_video.release()
        self._cv_video.open( self._path )
        
        self._next_render_index = 0
        
    
    def SetRenderToPosition( self, index ):
        
        with self._render_lock:
            
            if self._render_to_index != index:
                
                self._render_to_index = index
                
                HydrusThreading.CallToThread( self.THREADDoWork )
                
            
        
    
    def SetPosition( self, index ):
        
        with self._render_lock:
            
            if self._media.GetMime() == HC.IMAGE_GIF:
                
                if index == self._next_render_index: return
                elif index < self._next_render_index: self._RewindGIF()
                
                while self._next_render_index < index: self._GetCurrentFrame()
                
            else:
                
                self._cv_video.set( cv2.cv.CV_CAP_PROP_POS_FRAMES, index )
                
            
            self._render_to_index = index
            
        
    
    def THREADDoWork( self ):
        
        while True:
            
            time.sleep( 0.00001 ) # thread yield
            
            with self._render_lock:
                
                if self._last_index_rendered != self._render_to_index:
                    
                    index = self._next_render_index
                    
                    frame = self._RenderCurrentFrame()
                    
                    wx.CallAfter( self._image_container.AddFrame, index, frame )
                    
                else: break
                
            
        
    