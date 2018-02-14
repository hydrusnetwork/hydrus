import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusImageHandling
import HydrusPaths
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

if HC.PLATFORM_LINUX or HC.PLATFORM_OSX:
    
    FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg' )
    
elif HC.PLATFORM_WINDOWS:
    
    FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg.exe' )
    
if not os.path.exists( FFMPEG_PATH ):
    
    FFMPEG_PATH = os.path.basename( FFMPEG_PATH )
    
def CheckFFMPEGError( lines ):
    
    if "No such file or directory" in lines[-1]:
        
        raise IOError( "File not found!" )
        
    
    if 'Invalid data' in lines[-1]:
        
        raise HydrusExceptions.MimeException( 'FFMPEG could not parse.' )
        
    
def GetFFMPEGVersion():
    
    # open the file in a pipe, provoke an error, read output
    
    cmd = [ FFMPEG_PATH, '-version' ]
    
    try:
        
        proc = subprocess.Popen( cmd, bufsize=10**5, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo = HydrusData.GetHideTerminalSubprocessStartupInfo() )
        
    except Exception as e:
        
        if not os.path.exists( FFMPEG_PATH ):
            
            return 'no ffmpeg found'
            
        else:
            
            HydrusData.ShowException( e )
            
            return 'unable to execute ffmpeg'
            
        
    
    infos = proc.stdout.read().decode( 'utf8' )
    
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
    
    try:
        
        path.encode( 'ascii' ) # throwing unicode at the console is a mess best left for Python 3
        
    except UnicodeEncodeError:
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        with open( path, 'rb' ) as source:
            
            with open( temp_path, 'wb' ) as dest:
                
                HydrusPaths.CopyFileLikeToFileLike( source, dest )
                
            
        
        try:
            
            return GetFFMPEGInfoLines( temp_path, count_frames_manually )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
    cmd = [ FFMPEG_PATH, "-i", path ]
    
    if count_frames_manually:
        
        if HC.PLATFORM_WINDOWS:
            
            cmd += [ "-f", "null", "NUL" ]
            
        else:
            
            cmd += [ "-f", "null", "/dev/null" ]
            
        
    
    try:
        
        proc = subprocess.Popen( cmd, bufsize = 10**5, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetHideTerminalSubprocessStartupInfo() )
        
    except:
        
        if not os.path.exists( FFMPEG_PATH ):
            
            raise Exception( 'FFMPEG was not found!' )
            
        else:
            
            raise
            
        
    
    raw_info = proc.stderr.read()
    
    try:
        
        info = raw_info.decode( 'utf8' )
        
    except UnicodeDecodeError:
        
        info = raw_info
        
    
    proc.wait()
    
    proc.communicate()
    
    del proc
    
    lines = info.splitlines()
    
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
        
        duration = num_frames / float( fps )
        
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
    
    return ( resolution, duration_in_ms, num_frames )
    
def GetMatroskaOrWebm( path ):
    
    try:
        
        # a whole bunch of otherwise good webms aren't parseable by this, so default to 'I guess it is a webm, then.'
        
        tags = matroska.parse( path )
        
        ebml = tags[ 'EBML' ][0]
        
        if ebml[ 'DocType' ][0] == 'matroska':
            
            return HC.VIDEO_MKV
            
        
    except:
        
        pass
        
    
    return HC.VIDEO_WEBM
    
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
    
def GetMime( path ):
    
    lines = GetFFMPEGInfoLines( path )
    
    try:
        
        mime_text = ParseFFMPEGMimeText( lines )
        
    except HydrusExceptions.MimeException:
        
        return HC.APPLICATION_UNKNOWN
        
    
    if 'matroska' in mime_text or 'webm' in mime_text:
        
        # typically it is 'matroska,webm'
        
        return GetMatroskaOrWebm( path )
        
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
    
    if audio_found:
        line = lines_audio[0]
        try:
            match = re.search(" [0-9]* Hz", line)
            audio_fps = int(line[match.start()+1:match.end()])
        except:
            audio_fps = 'unknown'
    
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
        hms = map(float, line[match.start()+1:match.end()].split(':'))
        
        if len( hms ) == 1:
            
            duration = hms[0]
            
        elif len( hms ) == 2:
            
            duration = 60 * hms[0] + hms[1]
            
        elif len( hms ) ==3:
            
            duration = 3600 * hms[0] + 60 * hms[1] + hms[2]
            
        
        duration -= start_offset
        
        return duration
        
    except:
        
        raise HydrusExceptions.MimeException( 'Error reading duration!' )
        
    
def ParseFFMPEGFPS( lines ):
    
    try:
        
        line = ParseFFMPEGVideoLine( lines )
        
        # get the frame rate
        
        match = re.search("( [0-9]*.| )[0-9]* tbr", line)
        
        if match is not None:
            
            fps = line[match.start():match.end()].split(' ')[1]
            
        
        tbr_fps_is_likely_garbage = match is None or fps.endswith( 'k' ) or float( fps ) > 60
        
        if tbr_fps_is_likely_garbage:
            
            match = re.search("( [0-9]*.| )[0-9]* fps", line)
            
            if match is not None:
                
                fps = line[match.start():match.end()].split(' ')[1]
                
            
            fps_is_likely_garbage = match is None or fps.endswith( 'k' ) or float( fps ) > 60
            
            if fps_is_likely_garbage:
                
                return None
                
            
        
        fps = float( fps )
        
        return fps
        
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
        
    
def ParseFFMPEGVideoLine( lines ):
    
    # get the output line that speaks about video
    lines_video = [ l for l in lines if 'Video: ' in l and not ( 'Video: png' in l or 'Video: jpg' in l ) ] # mp3 says it has a 'png' video stream
    
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
        self._duration = float( duration ) / 1000.0
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        
        self.lastread = None
        
        self.fps = float( self._num_frames ) / self._duration
        
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
                
            
            ss = float( start_index ) / self.fps
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
            
        
        try:
            
            self.process = subprocess.Popen( cmd, bufsize = self.bufsize, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo = HydrusData.GetHideTerminalSubprocessStartupInfo() )
            
        except:
            
            if not os.path.exists( FFMPEG_PATH ):
                
                raise Exception( 'FFMPEG was not found!' )
                
            else:
                
                raise
                
            
        
        if skip_frames > 0:
            
            self.skip_frames( skip_frames )
            
        
    
    def skip_frames( self, n ):
        
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
            
            s = self.process.stdout.read(nbytes)
            
            if len(s) != nbytes:
                
                if self.lastread is None:
                    
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
        
        if rewind or jump_a_long_way_ahead: self.initialize( pos )
        else: self.skip_frames( pos - self.pos )
        
    
