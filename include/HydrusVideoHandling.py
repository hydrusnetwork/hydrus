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

if HC.PLATFORM_LINUX or HC.PLATFORM_OSX:
    
    FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg' )
    
elif HC.PLATFORM_WINDOWS:
    
    FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg.exe' )
    
if not os.path.exists( FFMPEG_PATH ):
    
    FFMPEG_PATH = os.path.basename( FFMPEG_PATH )
    
def GetFFMPEGVersion():
    # open the file in a pipe, provoke an error, read output
    
    cmd = [ FFMPEG_PATH, '-version' ]
    
    try:
        
        proc = subprocess.Popen( cmd, bufsize=10**5, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
        
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
    
def GetFFMPEGVideoProperties( path ):
    
    info = Hydrusffmpeg_parse_infos( path )
    
    ( w, h ) = info[ 'video_size' ]
    
    duration_in_s = info[ 'duration' ]
    
    duration = int( duration_in_s * 1000 )
    
    num_frames = info[ 'video_nframes' ]
    
    return ( ( w, h ), duration, num_frames )
    
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
    
def GetMimeFromFFMPEG( path ):
    
    info = Hydrusffmpeg_parse_infos( path )
    
    if 'mime_text' in info:
        
        mime_text = info[ 'mime_text' ]
        
        if 'matroska' in mime_text or 'webm' in mime_text:
            
            # typically it is 'matroska,webm'
            
            return GetMatroskaOrWebm( path )
            
        elif mime_text in ( 'mpeg', 'mpegvideo', 'mpegts' ):
            
            return HC.VIDEO_MPEG
            
        elif mime_text == 'flac':
            
            return HC.AUDIO_FLAC
            
        elif mime_text == 'mp3':
            
            return HC.AUDIO_MP3
            
        elif mime_text == 'ogg':
            
            return HC.AUDIO_OGG
            
        elif mime_text == 'asf':
            
            if info[ 'video_found' ]:
                
                return HC.VIDEO_WMV
                
            else:
                
                return HC.AUDIO_WMA
                
            
        
    
    return HC.APPLICATION_UNKNOWN
    
def HasVideoStream( path ):
    
    try:
        
        info = Hydrusffmpeg_parse_infos( path )
        
    except IOError as e:
        
        HydrusData.ShowException( 'Determining the mime for the file at ' + path + ' caused the following problem:' )
        HydrusData.ShowException( e )
        
        return False
        
    
    return info[ 'video_found' ]
    
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
    
    try:
        
        proc = subprocess.Popen( cmd, bufsize=10**5, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
        
    except:
        
        if not os.path.exists( FFMPEG_PATH ):
            
            raise Exception( 'FFMPEG was not found!' )
            
        else:
            
            raise
            
        
    
    infos = proc.stderr.read().decode('utf8')
    
    proc.terminate()
    
    del proc
    
    if print_infos:
        # print the whole info text returned by FFMPEG
        HydrusData.Print( infos )
    
    lines = infos.splitlines()
    if "No such file or directory" in lines[-1]:
        raise IOError("%s not found ! Wrong path ?"%filename)
    if 'Invalid data' in lines[-1]:
        raise HydrusExceptions.MimeException( 'FFMPEG could not parse.' )
    
    result = dict()
    
    # get duration (in seconds)
    #   Duration: 00:00:02.46, start: 0.033000, bitrate: 1069 kb/s
    try:
        keyword = ('frame=' if is_GIF else 'Duration: ')
        line = [l for l in lines if keyword in l][0]
        
        if 'start:' in line:
            
            m = re.search( '(start\\: )' + '-?[0-9]+\\.[0-9]*', line )
            
            start_offset = float( line[ m.start() + 7 : m.end() ] )
            
            if abs( start_offset ) > 1.0: # once had a file with start offset of 957499 seconds jej
                
                start_offset = 0
                
            
        else:
            
            start_offset = 0
            
        
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
    
    try:
        
        ( input_line, ) = [ l for l in lines if l.startswith( 'Input #0' ) ]
        
        # Input #0, matroska, webm, from 'm.mkv':
        
        text = input_line[10:]
        
        mime_text = text.split( ', from' )[0]
        
        result[ 'mime_text' ] = mime_text
        
    except:
        
        pass
        
    
    # get the output line that speaks about video
    lines_video = [ l for l in lines if ' Video: ' in l and not ( ' Video: png' in l or ' Video: jpg' in l ) ] # mp3 says it has a 'png' video stream
    
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
            
        
        try:
            
            self.process = subprocess.Popen( cmd, bufsize = self.bufsize, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
            
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
        
    
