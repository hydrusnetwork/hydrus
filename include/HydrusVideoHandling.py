#import numpy.core.multiarray # important this comes before cv!
import cv2
from flvlib import tags as flv_tags
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusImageHandling
import HydrusThreading
import matroska
import numpy
import os
import re
import subprocess
import sys
import tempfile
import traceback
import threading
import time

if HC.PLATFORM_LINUX: FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg' )
elif HC.PLATFORM_OSX: FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg' )
elif HC.PLATFORM_WINDOWS: FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg.exe' )

if cv2.__version__.startswith( '2' ):
    
    CAP_PROP_FRAME_COUNT = cv2.cv.CV_CAP_PROP_FRAME_COUNT
    CAP_PROP_FPS = cv2.cv.CV_CAP_PROP_FPS
    CAP_PROP_FRAME_WIDTH = cv2.cv.CV_CAP_PROP_FRAME_WIDTH
    CAP_PROP_FRAME_HEIGHT = cv2.cv.CV_CAP_PROP_FRAME_HEIGHT
    CAP_PROP_CONVERT_RGB = cv2.cv.CV_CAP_PROP_CONVERT_RGB
    CAP_PROP_POS_FRAMES = cv2.cv.CV_CAP_PROP_POS_FRAMES
    
else:
    
    CAP_PROP_FRAME_COUNT = cv2.CAP_PROP_FRAME_COUNT
    CAP_PROP_FPS = cv2.CAP_PROP_FPS
    CAP_PROP_FRAME_WIDTH = cv2.CAP_PROP_FRAME_WIDTH
    CAP_PROP_FRAME_HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT
    CAP_PROP_CONVERT_RGB = cv2.CAP_PROP_CONVERT_RGB
    CAP_PROP_POS_FRAMES = cv2.CAP_PROP_POS_FRAMES
    
def GetCVVideoProperties( path ):
    
    capture = cv2.VideoCapture( path )
    
    num_frames = int( capture.get( CAP_PROP_FRAME_COUNT ) )
    
    fps = capture.get( CAP_PROP_FPS )
    
    length_in_seconds = num_frames / fps
    
    length_in_ms = int( length_in_seconds * 1000 )
    
    duration = length_in_ms
    
    width = int( capture.get( CAP_PROP_FRAME_WIDTH ) )
    
    height = int( capture.get( CAP_PROP_FRAME_HEIGHT ) )
    
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
    
    fps = cv_video.get( CAP_PROP_FPS )
    
    if fps == 0: raise HydrusExceptions.CantRenderWithCVException()
    
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
    
    cmd = [ FFMPEG_PATH, "-i", filename ]
    
    is_GIF = filename.endswith('.gif')
    
    if is_GIF:
        if HC.PLATFORM_WINDOWS: cmd += ["-f", "null", "NUL"]
        else: cmd += ["-f", "null", "/dev/null"]
    
    proc = subprocess.Popen( cmd, bufsize=10**5, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
    
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
    #   Duration: 00:00:02.46, start: 0.033000, bitrate: 1069 kb/s
    try:
        keyword = ('frame=' if is_GIF else 'Duration: ')
        line = [l for l in lines if keyword in l][0]
        
        if 'start:' in line:
            
            m = re.search( '(start\\: )' + '[0-9]\\.[0-9]*', line )
            
            start_offset = float( line[ m.start() + 7 : m.end() ] )
            
        else: start_offset = 0
        
        match = re.search("[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9]", line)
        hms = map(float, line[match.start()+1:match.end()].split(':'))
        
        if len(hms) == 1:
            result['duration'] = hms[0]
        elif len(hms) == 2:
            result['duration'] = 60*hms[0]+hms[1]
        elif len(hms) ==3:
            result['duration'] = 3600*hms[0]+60*hms[1]+hms[2]
        
        result[ 'duration' ] -= start_offset
        
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
        
        num_frames = result['duration'] * result['video_fps']
        
        if num_frames != int( num_frames ): num_frames += 1 # rounding up
        
        result['video_nframes'] = int( num_frames )
        
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
    
# This was built from moviepy's FFMPEG_VideoReader
class VideoRendererFFMPEG( object ):

    def __init__( self, path, mime, duration, num_frames, target_resolution, pix_fmt = "rgb24" ):
        
        self._path = path
        self._mime = mime
        self._duration = float( duration ) / 1000.0
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        
        self.lastread = None
        
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
        
        cmd = [ FFMPEG_PATH,
            '-ss', "%.03f" % ss,
            '-i', self._path,
            '-loglevel', 'quiet',
            '-f', 'image2pipe',
            "-pix_fmt", self.pix_fmt,
            "-s", str( w ) + 'x' + str( h ),
            '-vcodec', 'rawvideo', '-' ]
            
        
        self.process = subprocess.Popen( cmd, bufsize = self.bufsize, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
        
        self.skip_frames( skip_frames )
        
    
    def skip_frames( self, n ):
        
        ( w, h ) = self._target_resolution
        
        for i in range( n ):
            
            if self.process is not None:
                
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
        
    
# the cv code was initially written by @fluffy_cub
class GIFRenderer( object ):
    
    def __init__( self, path, num_frames, target_resolution ):
        
        self._path = path
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        
        if cv2.__version__.startswith( '2' ):
            
            self._InitialisePIL()
            
        else:
            
            self._InitialiseCV()
            
        
    
    def _GetCurrentFrame( self ):
        
        if self._cv_mode:
            
            ( retval, numpy_image ) = self._cv_video.read()
            
            if not retval:
                
                self._next_render_index = ( self._next_render_index + 1 ) % self._num_frames
                
                raise HydrusExceptions.CantRenderWithCVException( 'CV could not render frame ' + str( self._next_render_index - 1 ) + '.' )
                
            
        else:
            
            if self._pil_image.mode == 'P' and 'transparency' in self._pil_image.info:
                
                # The gif problems seem to be here.
                # I think that while some transparent animated gifs expect their frames to be pasted over each other, the others expect them to be fresh every time.
                # Determining which is which doesn't seem to be available in PIL, and PIL's internal calculations seem to not be 100% correct.
                # Just letting PIL try to do it on its own with P rather than converting to RGBA sometimes produces artifacts
                
                current_frame = self._pil_image.convert( 'RGBA' )
                
                if self._pil_canvas is None: self._pil_canvas = current_frame
                else: self._pil_canvas.paste( current_frame, None, current_frame ) # use the rgba image as its own mask
                
            else: self._pil_canvas = self._pil_image
            
            numpy_image = HydrusImageHandling.GenerateNumPyImageFromPILImage( self._pil_canvas )
            
        
        self._next_render_index = ( self._next_render_index + 1 ) % self._num_frames
        
        if self._next_render_index == 0:
            
            self._RewindGIF()
            
        else:
            
            if not self._cv_mode:
                
                self._pil_image.seek( self._next_render_index )
                
                if self._pil_global_palette is not None and self._pil_image.palette == self._pil_global_palette: # for some reason, when pil falls back from local palette to global palette, a bunch of important variables reset!
                    
                    self._pil_image.palette.dirty = self._pil_dirty
                    self._pil_image.palette.mode = self._pil_mode
                    self._pil_image.palette.rawmode = self._pil_rawmode
                    
                
            
        
        return numpy_image
        
    
    def _InitialiseCV( self ):
        
        self._cv_mode = True
        
        self._cv_video = cv2.VideoCapture( self._path )
        
        self._cv_video.set( CAP_PROP_CONVERT_RGB, True )
        
        self._next_render_index = 0
        self._last_frame = None
        
    
    def _InitialisePIL( self ):
        
        self._cv_mode = False
        
        self._pil_image = HydrusImageHandling.GeneratePILImage( self._path )
        
        self._pil_canvas = None
        
        self._pil_global_palette = self._pil_image.palette
        
        if self._pil_global_palette is not None:
            
            self._pil_dirty = self._pil_image.palette.dirty
            self._pil_mode = self._pil_image.palette.mode
            self._pil_rawmode = self._pil_image.palette.rawmode
            
        
        self._next_render_index = 0
        self._last_frame = None
        
        # believe it or not, doing this actually fixed a couple of gifs!
        self._pil_image.seek( 1 )
        self._pil_image.seek( 0 )
        
    
    def _RenderCurrentFrame( self ):
        
        if self._cv_mode:
            
            try:
                
                numpy_image = self._GetCurrentFrame()
                
                numpy_image = HydrusImageHandling.EfficientlyResizeNumpyImage( numpy_image, self._target_resolution )
                
                numpy_image = cv2.cvtColor( numpy_image, cv2.COLOR_BGR2RGB )
                
            except HydrusExceptions.CantRenderWithCVException:
                
                if self._last_frame is None:
                    
                    self._InitialisePIL()
                    
                    numpy_image = self._RenderCurrentFrame()
                    
                else: numpy_image = self._last_frame
                
            
        else:
            
            numpy_image = self._GetCurrentFrame()
            
            numpy_image = HydrusImageHandling.EfficientlyResizeNumpyImage( numpy_image, self._target_resolution )
            
        
        self._last_frame = numpy_image
        
        return numpy_image
        
    
    def _RewindGIF( self ):
        
        if self._cv_mode:
            
            self._cv_video.release()
            self._cv_video.open( self._path )
            
            #self._cv_video.set( CAP_PROP_POS_FRAMES, 0.0 )
            
        else:
            
            self._pil_image.seek( 0 )
            
        
        self._next_render_index = 0
        
    
    def read_frame( self ): return self._RenderCurrentFrame()
    
    def set_position( self, index ):
        
        if index == self._next_render_index: return
        elif index < self._next_render_index: self._RewindGIF()
        
        while self._next_render_index < index: self._GetCurrentFrame()
        
        #self._cv_video.set( CV_CAP_PROP_POS_FRAMES, index )
        
    