from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusImageHandling
from . import HydrusPaths
from . import HydrusText
from . import HydrusThreading
import numpy
import os
import re
import subprocess
import sys
import traceback
import threading
import time

if HC.PLATFORM_LINUX or HC.PLATFORM_OSX:
    
    FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg' )
    
elif HC.PLATFORM_WINDOWS:
    
    FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg.exe' )
    
if not os.path.exists( FFMPEG_PATH ):
    
    FFMPEG_PATH = os.path.basename( FFMPEG_PATH )
    
def CheckFFMPEGError( lines ):
    
    if len( lines ) == 0:
        
        raise HydrusExceptions.MimeException( 'Could not parse that file--no FFMPEG output given.' )
        
    
    if "No such file or directory" in lines[-1]:
        
        raise IOError( "File not found!" )
        
    
    if 'Invalid data' in lines[-1]:
        
        raise HydrusExceptions.MimeException( 'FFMPEG could not parse.' )
        
    
def GetFFMPEGVersion():
    
    cmd = [ FFMPEG_PATH, '-version' ]
    
    try:
        
        sbp_kwargs = HydrusData.GetSubprocessKWArgs( text = True )
        
        proc = subprocess.Popen( cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError:
        
        return 'no ffmpeg found'
        
    except Exception as e:
        
        HydrusData.ShowException( e )
        
        return 'unable to execute ffmpeg'
        
    
    infos = proc.stdout.read()
    
    proc.terminate()
    
    del proc
    
    lines = infos.splitlines()
    
    if len( lines ) > 0:
        
        # typically 'ffmpeg version [VERSION] Copyright ...
        top_line = lines[0]
        
        if top_line.startswith( 'ffmpeg version ' ):
            
            top_line = top_line.replace( 'ffmpeg version ', '' )
            
            if ' ' in top_line:
                
                version_string = top_line.split( ' ' )[0]
                
                return version_string
                
            
        
    
    return 'unknown'
    
# bits of this were originally cribbed from moviepy
def GetFFMPEGInfoLines( path, count_frames_manually = False ):
    
    # open the file in a pipe, provoke an error, read output
    
    cmd = [ FFMPEG_PATH, "-i", path ]
    
    if count_frames_manually:
        
        # added -an here to remove audio component, which was sometimes causing convert fails on single-frame music webms
        
        if HC.PLATFORM_WINDOWS:
            
            cmd += [ "-an", "-f", "null", "NUL" ]
            
        else:
            
            cmd += [ "-an", "-f", "null", "/dev/null" ]
            
        
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs()
    
    try:
        
        proc = subprocess.Popen( cmd, bufsize = 10**5, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError as e:
        
        raise FileNotFoundError( 'FFMPEG not found--are you sure it is installed? Full error: ' + str( e ) )
        
    
    data_bytes = proc.stderr.read()
    
    proc.communicate()
    
    del proc
    
    ( text, encoding ) = HydrusText.NonFailingUnicodeDecode( data_bytes, 'utf-8' )
    
    lines = text.splitlines()
    
    try:
        
        CheckFFMPEGError( lines )
        
    except:
        
        HydrusData.Print( 'FFMPEG had problem with file: ' + path )
        
        raise
        
    
    return lines
    
def GetFFMPEGVideoProperties( path, count_frames_manually = False ):
    
    lines = GetFFMPEGInfoLines( path, count_frames_manually )
    
    if not ParseFFMPEGHasVideo( lines ):
        
        raise HydrusExceptions.MimeException( 'File did not appear to have a video stream!' )
        
    
    resolution = ParseFFMPEGVideoResolution( lines )
    
    duration = ParseFFMPEGDuration( lines )
    
    if duration is None:
        
        fps = ParseFFMPEGFPS( lines )
        
        if fps is None:
            
            fps = 24 # screw it, let's just put one in there
            
        
        if not count_frames_manually:
            
            count_frames_manually = True
            
            lines = GetFFMPEGInfoLines( path, count_frames_manually )
            
        
        num_frames = ParseFFMPEGNumFramesManually( lines )
        
        duration = num_frames / fps
        
    else:
        
        num_frames = None
        
        if not count_frames_manually:
            
            fps = ParseFFMPEGFPS( lines )
            
            it_was_accurate = fps is not None
            
            if it_was_accurate:
                
                num_frames = duration * fps
                
                if num_frames != int( num_frames ): # we want whole numbers--anything else suggests start_offset is off or whatever
                    
                    if os.path.getsize( path ) < 30 * 1048576: # but only defer to a super precise +/- 1-frame manual count in this case when the file is small
                        
                        it_was_accurate = False
                        
                    
                
            
            if not it_was_accurate:
                
                count_frames_manually = True
                
                lines = GetFFMPEGInfoLines( path, count_frames_manually )
                
            
        
        if count_frames_manually:
            
            try:
                
                num_frames = ParseFFMPEGNumFramesManually( lines )
                
            except HydrusExceptions.MimeException:
                
                if num_frames is None:
                    
                    raise
                    
                
            
        
    
    duration_in_ms = int( duration * 1000 )
    num_frames = int( num_frames )
    
    return ( resolution, duration_in_ms, num_frames )
    
def GetMime( path ):
    
    lines = GetFFMPEGInfoLines( path )
    
    try:
        
        mime_text = ParseFFMPEGMimeText( lines )
        
    except HydrusExceptions.MimeException:
        
        return HC.APPLICATION_UNKNOWN
        
    
    if 'matroska' in mime_text or 'webm' in mime_text:
        
        # a webm has at least vp8/vp9 video and optionally vorbis audio
        
        has_webm_video = False
        has_webm_audio = False
        
        if ParseFFMPEGHasVideo( lines ):
            
            video_format = ParseFFMPEGVideoFormat( lines )
            
            webm_video_formats = ( 'vp8', 'vp9' )
            
            has_webm_video = True in ( webm_video_format in video_format for webm_video_format in webm_video_formats )
            
        
        ( has_audio, audio_format ) = ParseFFMPEGAudio( lines )
        
        if has_audio:
            
            webm_audio_formats = ( 'vorbis', 'opus' )
            
            has_webm_audio = True in ( webm_audio_format in audio_format for webm_audio_format in webm_audio_formats )
            
        else:
            
            # no audio at all is not a vote against webm
            has_webm_audio = True
            
        
        if has_webm_video and has_webm_audio:
            
            return HC.VIDEO_WEBM
            
        else:
            
            return HC.VIDEO_MKV
            
        
    elif mime_text in ( 'mpeg', 'mpegvideo', 'mpegts' ):
        
        return HC.VIDEO_MPEG
        
    elif mime_text == 'flac':
        
        return HC.AUDIO_FLAC
        
    elif mime_text == 'mp3':
        
        return HC.AUDIO_MP3
        
    elif 'mp4' in mime_text:
        
        return HC.VIDEO_MP4
        
    elif mime_text == 'ogg':
        
        return HC.AUDIO_OGG
        
    elif mime_text == 'asf':
        
        if ParseFFMPEGHasVideo( lines ):
            
            return HC.VIDEO_WMV
            
        else:
            
            return HC.AUDIO_WMA
            
        
    
    return HC.APPLICATION_UNKNOWN
    
def HasVideoStream( path ):
    
    lines = GetFFMPEGInfoLines( path )
    
    return ParseFFMPEGHasVideo( lines )
    
def ParseFFMPEGAudio( lines ):
    
    # this is from the old stuff--might be helpful later when we add audio
    
    lines_audio = [l for l in lines if 'Audio: ' in l]
    
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
            
            match = re.search( '(?<=Audio\:\s).+?(?=,)', line )
            
            audio_format = match.group()
            
        except:
            
            audio_format = 'unknown'
            
        
    
    return ( audio_found, audio_format )
    
def ParseFFMPEGDuration( lines ):
    
    # get duration (in seconds)
    #   Duration: 00:00:02.46, start: 0.033000, bitrate: 1069 kb/s
    try:
        
        line = [ l for l in lines if 'Duration:' in l ][0]
        
        if 'Duration: N/A' in line:
            
            return None
            
        
        if 'start:' in line:
            
            m = re.search( '(start\\: )' + '-?[0-9]+\\.[0-9]*', line )
            
            start_offset = float( line[ m.start() + 7 : m.end() ] )
            
            if abs( start_offset ) > 1.0: # once had a file with start offset of 957499 seconds jej
                
                start_offset = 0
                
            
        else:
            
            start_offset = 0
            
        
        match = re.search("[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9]", line)
        hms = list(map(float, line[match.start()+1:match.end()].split(':')))
        
        if len( hms ) == 1:
            
            duration = hms[0]
            
        elif len( hms ) == 2:
            
            duration = 60 * hms[0] + hms[1]
            
        elif len( hms ) ==3:
            
            duration = 3600 * hms[0] + 60 * hms[1] + hms[2]
            
        
        if duration == 0:
            
            return None
            
        
        duration -= start_offset
        
        return duration
        
    except:
        
        raise HydrusExceptions.MimeException( 'Error reading duration!' )
        
    
def ParseFFMPEGFPS( lines ):
    
    try:
        
        line = ParseFFMPEGVideoLine( lines )
        
        # get the frame rate
        
        possible_results = []
        
        match = re.search("( [0-9]*.| )[0-9]* tbr", line)
        
        if match is not None:
            
            tbr = line[match.start():match.end()].split(' ')[1]
            
            tbr_fps_is_likely_garbage = match is None or tbr.endswith( 'k' ) or float( tbr ) > 60
            
            if not tbr_fps_is_likely_garbage:
                
                possible_results.append( float( tbr ) )
                
            
        
        #
        
        match = re.search("( [0-9]*.| )[0-9]* fps", line)
        
        if match is not None:
            
            fps = line[match.start():match.end()].split(' ')[1]
            
            fps_is_likely_garbage = match is None or fps.endswith( 'k' ) or float( fps ) > 60
            
            if not fps_is_likely_garbage:
                
                possible_results.append( float( fps ) )
                
            
        
        if len( possible_results ) == 0:
            
            return None
            
        else:
            
            # in some cases, fps is 0.77 and tbr is incorrectly 20. extreme values cause bad results. let's try erroring on the side of slow
            # tbh in these cases, the frame are prob going to get counted manually anyway due to no neat ints at the end, so nbd
            
            return min( possible_results )
            
        
    except:
        
        raise HydrusExceptions.MimeException( 'Error estimating framerate!' )
        
    
def ParseFFMPEGHasVideo( lines ):
    
    try:
        
        video_line = ParseFFMPEGVideoLine( lines )
        
    except HydrusExceptions.MimeException:
        
        return False
        
    
    return True
    
def ParseFFMPEGMimeText( lines ):
    
    try:
        
        ( input_line, ) = [ l for l in lines if l.startswith( 'Input #0' ) ]
        
        # Input #0, matroska, webm, from 'm.mkv':
        
        text = input_line[10:]
        
        mime_text = text.split( ', from' )[0]
        
        return mime_text
        
    except:
        
        raise HydrusExceptions.MimeException( 'Error reading mime!' )
        
    
def ParseFFMPEGNumFramesManually( lines ):
    
    try:
        
        frame_lines = [ l for l in lines if l.startswith( 'frame= ' ) ]
        
        l = frame_lines[-1] # there will be several of these, counting up as the file renders. we hence want the final one
        
        while '  ' in l:
            
            l = l.replace( '  ', ' ' )
            
        
        num_frames = int( l.split( ' ' )[1] )
        
        return num_frames
        
    except:
        
        raise HydrusExceptions.MimeException( 'Error counting number of frames!' )
        
    
def ParseFFMPEGVideoFormat( lines ):
    
    line = ParseFFMPEGVideoLine( lines )
    
    try:
        
        match = re.search( '(?<=Video\:\s).+?(?=,)', line )
        
        video_format = match.group()
        
    except:
        
        video_format = 'unknown'
        
    
    return video_format
    
def ParseFFMPEGVideoLine( lines ):
    
    # get the output line that speaks about video
    # the ^\sStream is to exclude the 'title' line, when it exists, includes the string 'Video: ', ha ha
    lines_video = [ l for l in lines if re.search( '^\s*Stream', l ) is not None and 'Video: ' in l and not ( 'Video: png' in l or 'Video: jpg' in l ) ] # mp3 says it has a 'png' video stream
    
    if len( lines_video ) == 0:
        
        raise HydrusExceptions.MimeException( 'Could not find video information!' )
        
    
    line = lines_video[0]
    
    return line
    
def ParseFFMPEGVideoResolution( lines ):
    
    try:
        
        line = ParseFFMPEGVideoLine( lines )
        
        # get the size, of the form 460x320 (w x h)
        match = re.search(" [0-9]*x[0-9]*(,| )", line)
        
        resolution = list(map(int, line[match.start():match.end()-1].split('x')))
        
        sar_match = re.search( " SAR [0-9]*:[0-9]* ", line )
        
        if sar_match is not None:
            
            # ' SAR 2:3 '
            sar_string = line[ sar_match.start() : sar_match.end() ]
            
            # '2:3'
            sar_string = sar_string[5:-1]
            
            ( sar_w, sar_h ) = sar_string.split( ':' )
            
            ( sar_w, sar_h ) = ( int( sar_w ), int( sar_h ) )
            
            ( x, y ) = resolution
            
            x *= sar_w
            x //= sar_h
            
            resolution = ( x, y )
            
        
        return resolution
        
    except:
        
        raise HydrusExceptions.MimeException( 'Error parsing resolution!' )
        
    
# This was built from moviepy's FFMPEG_VideoReader
class VideoRendererFFMPEG( object ):
    
    def __init__( self, path, mime, duration, num_frames, target_resolution, pix_fmt = "rgb24" ):
        
        self._path = path
        self._mime = mime
        self._duration = duration / 1000.0
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        
        self.lastread = None
        
        self.fps = self._num_frames / self._duration
        
        if self.fps == 0:
            
            self.fps = 24
            
        
        self.pix_fmt = pix_fmt
        
        if pix_fmt == 'rgba': self.depth = 4
        else: self.depth = 3
        
        ( x, y ) = self._target_resolution
        
        bufsize = self.depth * x * y
        
        self.process = None
        
        self.bufsize = bufsize
        
        self.initialize()
        
    
    def close( self ):
        
        if self.process is not None:
            
            self.process.terminate()
            
            self.process.stdout.close()
            self.process.stderr.close()
            
            self.process = None
            
        
    
    def initialize( self, start_index = 0 ):
        
        self.close()
        
        if self._mime in ( HC.IMAGE_APNG, HC.IMAGE_GIF ):
            
            do_ss = False
            ss = 0
            self.pos = 0
            skip_frames = start_index
            
        else:
            
            if start_index == 0:
                
                do_ss = False
                
            else:
                
                do_ss = True
                
            
            ss = start_index / self.fps
            self.pos = start_index
            skip_frames = 0
            
        
        ( w, h ) = self._target_resolution
        
        cmd = [ FFMPEG_PATH ]
        
        if do_ss:
            
            cmd.extend( [ '-ss', "%.03f" % ss ] )
            
        
        cmd.extend( [ '-i', self._path,
            '-loglevel', 'quiet',
            '-f', 'image2pipe',
            "-pix_fmt", self.pix_fmt,
            "-s", str( w ) + 'x' + str( h ),
            '-vsync', '0',
            '-vcodec', 'rawvideo', '-' ] )
            
        
        sbp_kwargs = HydrusData.GetSubprocessKWArgs()
        
        self.process = subprocess.Popen( cmd, bufsize = self.bufsize, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **sbp_kwargs )
        
        if skip_frames > 0:
            
            self.skip_frames( skip_frames )
            
        
    
    def skip_frames( self, n ):
        
        n = int( n )
        
        ( w, h ) = self._target_resolution
        
        for i in range( n ):
            
            if self.process is not None:
                
                self.process.stdout.read( self.depth * w * h )
                
                self.process.stdout.flush()
                
            
            self.pos += 1
            
        
    
    def read_frame( self ):
        
        if self.pos == self._num_frames:
            
            self.initialize()
            
        
        if self.process is None:
            
            result = self.lastread
            
        else:
            
            ( w, h ) = self._target_resolution
            
            nbytes = self.depth * w * h
            
            s = self.process.stdout.read( nbytes )
            
            if len(s) != nbytes:
                
                if self.lastread is None:
                    
                    if self.pos != 0:
                        
                        # this renderer was asked to render starting from mid-vid and this was not possible due to broken key frame index whatever
                        # lets try and render from the vid start before we say the whole vid is broke
                        # I tried doing 'start from 0 and skip n frames', but this is super laggy so would need updates further up the pipe to display this to the user
                        # atm this error states does not communicate to the videocontainer that the current frame num has changed, so the frames are henceforth out of phase
                        
                        frames_to_jump = self.pos
                        
                        self.set_position( 0 )
                        
                        return self.read_frame()
                        
                    
                    raise Exception( 'Unable to render that video! Please send it to hydrus dev so he can look at it!' )
                    
                
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
        
        if rewind or jump_a_long_way_ahead:
            
            self.initialize( pos )
            
        else:
            
            self.skip_frames( pos - self.pos )
            
        
    
    def Stop( self ):
        
        self.close()
        
