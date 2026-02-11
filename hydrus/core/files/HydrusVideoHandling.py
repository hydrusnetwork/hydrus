import numpy
import os
import re

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusAudioHandling
from hydrus.core.files import HydrusFFMPEG
from hydrus.core.processes import HydrusSubprocess

def FileIsAnimated( path ):
    
    # TODO: this guy can be better, or at least it deserves some work
    # surely we can have some sort of lines-inspection before we try the 'render first second' stuff, at least to discard obvious first stuff?
    # I dunno, it is tricky. I only use this guy atm 2025-11 for animated jxl, which is indeed tricky to read from
    # ffmpeg offers a slightly different codec, so maybe we could inspect that, but no duration data or anything, so what would a different ffmpeg version say?
    # maybe this is ok as a backstop
    
    try:
        
        ( resolution, duration_in_ms, num_frames, has_audio ) = GetFFMPEGVideoProperties( path )
        
        return num_frames > 1
        
    except Exception as e:
        
        return False
        
    

# bits of this were originally cribbed from moviepy
def GetFFMPEGInfoLines( path, count_frames_manually = False, only_first_second = False ):
    
    # open the file in a pipe, provoke an error, read output
    
    cmd = [ HydrusFFMPEG.FFMPEG_PATH, "-xerror", "-i", path ]
    
    if only_first_second:
        
        cmd.insert( 1, '-t' )
        cmd.insert( 2, '1' )
        
    
    if count_frames_manually:
        
        # added -an here to remove audio component, which was sometimes causing convert fails on single-frame music webms
        
        if HC.PLATFORM_WINDOWS:
            
            cmd += [ "-vf", "scale=-2:120", "-an", "-f", "null", "NUL" ]
            
        else:
            
            cmd += [ "-vf", "scale=-2:120", "-an", "-f", "null", "/dev/null" ]
            
        
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        ( stdout, stderr ) = HydrusSubprocess.RunSubprocess( cmd )
        
    except HydrusExceptions.SubprocessTimedOut:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'ffmpeg could not read file info quick enough!' )
        
    except FileNotFoundError as e:
        
        raise HydrusFFMPEG.HandleFFMPEGFileNotFoundAndGenerateException( e, path )
        
    
    text = stderr
    
    if text is None or len( text ) == 0:
        
        raise HydrusFFMPEG.HandleFFMPEGNoContentAndGenerateException( path, stdout, stderr )
        
    
    lines = text.splitlines()
    
    HydrusFFMPEG.CheckFFMPEGError( lines )
    
    return lines
    

def GetFFMPEGVideoProperties( path, force_count_frames_manually = False ):
    
    lines_for_first_second = GetFFMPEGInfoLines( path, count_frames_manually = True, only_first_second = True )
    
    ( has_video, video_format ) = ParseFFMPEGVideoFormat( lines_for_first_second )
    
    if not has_video:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Wanted to parse video data, but file did not appear to have a video stream!' )
        
    
    resolution = ParseFFMPEGVideoResolution( lines_for_first_second )
    
    ( file_duration_in_s, stream_duration_in_s ) = ParseFFMPEGDuration( lines_for_first_second )
    
    # this will have to be fixed when I add audio, and dynamically accounted for on dual vid/audio rendering
    duration_s = stream_duration_in_s
    
    ( fps, confident_fps ) = ParseFFMPEGFPS( lines_for_first_second )
    
    if duration_s is None and not confident_fps:
        
        # ok default to fall back on
        ( fps, confident_fps ) = ( 24, True )
        
    
    if fps is None or fps == 0:
        
        fps = 1
        
    
    if duration_s is None:
        
        force_count_frames_manually = True
        
    else:
        
        # if file is big or long, don't try to force a manual count when one not explicitly asked for
        # we don't care about a dropped frame on a 10min vid tbh
        num_frames_seems_ok_to_count = duration_s < 30
        file_is_ok_size = os.path.getsize( path ) < 256 * 1024 * 1024
        
        if num_frames_seems_ok_to_count and file_is_ok_size:
            
            last_frame_has_unusual_duration = ( duration_s * fps ) % 1 > 0
            
            unusual_video_start = file_duration_in_s != stream_duration_in_s
            
            if not confident_fps or last_frame_has_unusual_duration or unusual_video_start:
                
                force_count_frames_manually = True
                
            
        
    
    if force_count_frames_manually:
        
        lines = GetFFMPEGInfoLines( path, count_frames_manually = True )
        
        num_frames = ParseFFMPEGNumFramesManually( lines )
        
        if num_frames > 0 and duration_s is not None:
            
            implied_fps_given_what_we_know = num_frames / duration_s
            
            if 0 < fps < 1000 < implied_fps_given_what_we_know:
                
                # ok let's assume FFMPEG pulled 'duration = 40ms' for a file with 400 frames (looking at this now)
                # we'll trust out 'not confident' fps number over that
                duration_s = None
                
            
        
        if duration_s is None:
            
            duration_s = num_frames / fps
            
        
    else:
        
        num_frames = int( duration_s * fps )
        
    
    duration_in_ms = HydrusTime.MillisecondiseS( duration_s )
    
    has_audio = VideoHasAudio( path, lines_for_first_second )
    
    return ( resolution, duration_in_ms, num_frames, has_audio )
    

def GetMime( path ):
    
    lines = GetFFMPEGInfoLines( path )
    
    try:
        
        mime_text = ParseFFMPEGMimeText( lines )
        
    except HydrusExceptions.UnsupportedFileException:
        
        return HC.APPLICATION_UNKNOWN
        
    
    ( has_video, video_format ) = ParseFFMPEGVideoFormat( lines )
    ( has_audio, audio_format ) = HydrusAudioHandling.ParseFFMPEGAudio( lines )
    
    if not ( has_video or has_audio ):
        
        return HC.APPLICATION_UNKNOWN
        
    
    if 'matroska' in mime_text or 'webm' in mime_text:
        
        # a webm has at least vp8/vp9 video and optionally vorbis audio
        
        has_webm_video = False
        
        if has_video:
            
            webm_video_formats = ( 'vp8', 'vp9', 'av1' )
            
            has_webm_video = True in ( webm_video_format in video_format for webm_video_format in webm_video_formats )
            
        
        if has_audio:
            
            webm_audio_formats = ( 'vorbis', 'opus' )
            
            has_webm_audio = True in ( webm_audio_format in audio_format for webm_audio_format in webm_audio_formats )
            
        else:
            
            # no audio at all is not a vote against webm
            has_webm_audio = True
            
        
        if has_webm_video and has_webm_audio:
            
            return HC.VIDEO_WEBM
            
        else:
            
            if has_video:
                
                return HC.VIDEO_MKV
                
            elif has_audio:
                
                return HC.AUDIO_MKV
                
            
        
    elif mime_text in ( 'mpeg', 'mpegvideo', 'mpegts' ):
        
        return HC.VIDEO_MPEG
        
    elif mime_text == 'flac':
        
        return HC.AUDIO_FLAC
        
    elif mime_text == 'wav':
        
        return HC.AUDIO_WAVE
        
    elif mime_text == 'mp3':
        
        return HC.AUDIO_MP3
        
    elif mime_text == 'tta':
        
        return HC.AUDIO_TRUEAUDIO
        
    elif 'mp4' in mime_text:
        
        container = ParseFFMPEGMetadataContainer( lines )
        
        if container == 'M4A':
            
            return HC.AUDIO_M4A
            
        elif container == 'qt':
            
            return HC.VIDEO_MOV
            
        elif container in ( 'isom', 'mp42' ): # mp42 is version 2 of mp4 standard
            
            if has_video:
                
                return HC.VIDEO_MP4
                
            elif has_audio:
                
                return HC.AUDIO_MP4
                
            
        
        if has_audio and 'mjpeg' in video_format:
            
            return HC.AUDIO_M4A
            
        elif has_video:
            
            return HC.VIDEO_MP4
            
        elif has_audio:
            
            return HC.AUDIO_MP4
            
        
    elif mime_text == 'ogg':
        
        if has_video:
            
            return HC.VIDEO_OGV
            
        else:
            
            return HC.AUDIO_OGG
            
        
    elif 'rm' in mime_text:
        
        if ParseFFMPEGHasVideo( lines ):
            
            return HC.VIDEO_REALMEDIA
            
        else:
            
            return HC.AUDIO_REALMEDIA
            
        
    elif mime_text == 'asf':
        
        if ParseFFMPEGHasVideo( lines ):
            
            return HC.VIDEO_WMV
            
        else:
            
            return HC.AUDIO_WMA
            
        
    elif mime_text == 'wav':
        
        return HC.AUDIO_WAVE
        
    elif mime_text == 'wv':
        
        return HC.AUDIO_WAVPACK
        
    
    return HC.APPLICATION_UNKNOWN
    

def HasVideoStream( path ) -> bool:
    
    lines = GetFFMPEGInfoLines( path )
    
    return ParseFFMPEGHasVideo( lines )
    

def ParseFFMPEGDuration( lines ):
    
    # get duration (in seconds)
    #   Duration: 00:00:02.46, start: 0.033000, bitrate: 1069 kb/s
    try:
        
        # had a vid with 'Duration:' in title, ha ha, so now a regex
        line = [ line for line in lines if re.search( r'^\s*Duration:', line ) is not None ][0]
        
        if 'Duration: N/A' in line:
            
            return ( None, None )
            
        
        if 'start:' in line:
            
            m = re.search( r'(start: )-?[0-9]+\.[0-9]*', line )
            
            start_offset = float( line[ m.start() + 7 : m.end() ] )
            
        else:
            
            start_offset = 0
            
        
        match = re.search("[0-9]+:[0-9][0-9]:[0-9][0-9].[0-9][0-9]", line)
        hms = [ float( float_string ) for float_string in line[match.start():match.end()].split(':') ]
        
        duration_s = 0
        
        if len( hms ) == 1:
            
            duration_s = hms[0]
            
        elif len( hms ) == 2:
            
            duration_s = 60 * hms[0] + hms[1]
            
        elif len( hms ) == 3:
            
            duration_s = 3600 * hms[0] + 60 * hms[1] + hms[2]
            
        
        if duration_s == 0:
            
            return ( None, None )
            
        
        if start_offset > 0.85 * duration_s:
            
            # as an example, Duration: 127:57:31.25, start: 460633.291000 lmao
            
            return ( None, None )
            
        
        # we'll keep this for now I think
        if start_offset > 1:
            
            start_offset = 0
            
        
        file_duration_s = duration_s + start_offset
        stream_duration_s = duration_s
        
        return ( file_duration_s, stream_duration_s )
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Error reading duration!' )
        
    
def ParseFFMPEGFPS( lines, png_ok = False ):
    
    try:
        
        line = ParseFFMPEGVideoLine( lines, png_ok = png_ok )
        
        ( possible_results, confident ) = ParseFFMPEGFPSPossibleResults( line )
        
        if len( possible_results ) == 0:
            
            fps = 1
            confident = False
            
        else:
            
            fps = min( possible_results )
            
        
        return ( fps, confident )
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Error estimating framerate!' )
        
    

def ParseFFMPEGFPSFromFirstSecond( lines_for_first_second ):
    
    try:
        
        line = ParseFFMPEGVideoLine( lines_for_first_second )
        
        ( possible_results, confident ) = ParseFFMPEGFPSPossibleResults( line )
        
        num_frames_in_first_second = ParseFFMPEGNumFramesManually( lines_for_first_second )
        
        if len( possible_results ) == 0:
            
            fps = num_frames_in_first_second
            confident = False
            
        else:
            
            # in some cases, fps is 0.77 and tbr is incorrectly 20. extreme values cause bad results. let's default to slowest, but test our actual first second for most legit-looking
            
            sensible_first_second = 1 <= num_frames_in_first_second <= 288
            
            fps = min( possible_results )
            
            fps_matches_with_first_second = False
            
            for possible_fps in possible_results:
                
                if num_frames_in_first_second - 1 <= possible_fps <= num_frames_in_first_second + 1:
                    
                    fps = possible_fps
                    
                    fps_matches_with_first_second = True
                    
                    break
                    
                
            
            confident = sensible_first_second and fps_matches_with_first_second
            
        
        if fps is None or fps == 0:
            
            fps = 1
            confident = False
            
        
        return ( fps, confident )
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Error estimating framerate!' )
        
    

def ParseFFMPEGFPSPossibleResults( video_line ) -> tuple[ set[ float ], bool ]:
    
    def that_fps_string_is_likely_stupid( fps: str ) -> bool:
        
        if fps.endswith( 'k' ):
            
            return True
            
        
        fps = float( fps )
        
        return fps <= 1 or fps == 100 or fps > 144
        
    
    # get the frame rate
    
    possible_results = set()
    
    match = re.search("( [0-9]*.| )[0-9]* tbr", video_line)
    
    if match is not None:
        
        tbr = video_line[match.start():match.end()].split(' ')[1]
        
        if not that_fps_string_is_likely_stupid( tbr ):
            
            possible_results.add( float( tbr ) )
            
        
    
    #
    
    match = re.search("( [0-9]*.| )[0-9]* fps", video_line)
    
    if match is not None:
        
        fps = video_line[match.start():match.end()].split(' ')[1]
        
        if not that_fps_string_is_likely_stupid( fps ):
            
            possible_results.add( float( fps ) )
            
        
    
    possible_results.discard( 0 )
    
    if len( possible_results ) == 0:
        
        confident = False
        
    else:
        
        # if we have 60 and 59.99, that's fine mate
        max_fps = max( possible_results )
        
        if False not in ( possible_fps >= max_fps * 0.95 for possible_fps in possible_results ):
            
            confident = True
            
        else:
            
            confident = len( possible_results ) <= 1
            
        
    
    return ( possible_results, confident )
    
def ParseFFMPEGHasVideo( lines ) -> bool:
    
    try:
        
        ParseFFMPEGVideoLine( lines )
        
    except HydrusExceptions.UnsupportedFileException:
        
        return False
        
    
    return True
    
def ParseFFMPEGMetadataContainer( lines ) -> str:
    
    #  Metadata:
    #    major_brand     : isom
    
    match_metadata_line_re = r'\s*Metadata:\s*'
    
    metadata_line_index = None
    
    for ( i, line ) in enumerate( lines ):
        
        if re.match( match_metadata_line_re, line ) is not None:
            
            metadata_line_index = i
            
            break
            
        
    
    if metadata_line_index is None:
        
        return ''
        
    
    match_major_brand_re = r'\s*major_brand\s*:.+'
    
    for line in lines[ metadata_line_index : ]:
        
        if re.match( match_major_brand_re, line ) is not None:
            
            container = line.split( ':', 1 )[1].strip()
            
            return container
            
        
    
    return ''
    
def ParseFFMPEGMimeText( lines ):
    
    try:
        
        ( input_line, ) = [ line for line in lines if line.startswith( 'Input #0' ) ]
        
        # Input #0, matroska, webm, from 'm.mkv':
        
        text = input_line[10:]
        
        mime_text = text.split( ', from' )[0]
        
        return mime_text
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Error reading file type!' )
        
    
def ParseFFMPEGNumFramesManually( lines ) -> int:
    
    frame_lines = [ line for line in lines if line.startswith( 'frame=' ) ]
    
    if len( frame_lines ) == 0:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Video appears to be broken and non-renderable--perhaps a damaged single-frame video?' )
        
    
    final_line = frame_lines[-1] # there will be many progress rows, counting up as the file renders. we hence want the final one
    
    line = final_line
    
    line = line.replace( 'frame=', '' )
    
    while line.startswith( ' ' ):
        
        line = line[1:]
        
    
    try:
        
        frames_string = line.split( ' ' )[0]
        
        num_frames = int( frames_string )
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Video was unable to render correctly--could not parse ffmpeg output line: "{}"'.format( final_line ) )
        
    
    return num_frames
    

def ParseFFMPEGVideoFormat( lines ):
    
    try:
        
        line = ParseFFMPEGVideoLine( lines )
        
    except HydrusExceptions.UnsupportedFileException:
        
        return ( False, 'unknown' )
        
    
    try:
        
        match = re.search( r'(?<=Video:\s).+?(?=,)', line )
        
        video_format = match.group()
        
        if video_format.startswith( 'none' ): # none (CRAW / mem_address), none, 6000x4000, blah blah
            
            return ( False, 'none' )
            
        
    except Exception as e:
        
        video_format = 'unknown'
        
    
    return ( True, video_format )
    

def ParseFFMPEGVideoLine( lines, png_ok = False ) -> str:
    
    if png_ok:
        
        bad_video_formats = [ 'jpg' ]
        
    else:
        
        bad_video_formats = [ 'png', 'jpg' ]
        
    
    # get the output line that speaks about video
    # the ^\sStream is to exclude the 'title' line, when it exists, includes the string 'Video: ', ha ha
    lines_video = [ line for line in lines if re.search( r'^\s*Stream', line ) is not None and 'Video: ' in line and True not in ( 'Video: {}'.format( bad_video_format ) in line for bad_video_format in bad_video_formats ) ] # mp3 says it has a 'png' video stream
    
    if len( lines_video ) == 0:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not find video information!' )
        
    
    line = lines_video[0]
    
    return line
    

def ParseFFMPEGVideoResolution( lines, png_ok = False ) -> tuple[ int, int ]:
    
    try:
        
        line = ParseFFMPEGVideoLine( lines, png_ok = png_ok )
        
        # get the size, of the form 460x320 (w x h)
        match = re.search(" [0-9]*x[0-9]*([, ])", line)
        
        resolution_string = line[match.start():match.end()-1]
        
        ( width_string, height_string ) = resolution_string.split( 'x' )
        
        width = int( width_string )
        height = int( height_string )
        
        # if a vid has an SAR, this 'sample' aspect ratio basically just stretches it
        # when you convert the width using SAR, the resulting resolution should match the DAR, 'display' aspect ratio, which is what we actually want in final product
        # MPC-HC seems to agree with this calculation, Firefox does not
        # examples:
        # '  Stream #0:0: Video: hevc (Main), yuv420p(tv, bt709), 1280x720 [SAR 69:80 DAR 23:15], 30 fps, 30 tbr, 1k tbn (default)'
        # '  Stream #0:0: Video: vp9 (Profile 0), yuv420p(tv, progressive), 1120x1080, SAR 10:11 DAR 280:297, 30 fps, 30 tbr, 1k tbn (default)'
        
        sar_match = re.search( "[\\[\\s]SAR [0-9]*:[0-9]*[,\\s]", line )
        
        if sar_match is not None:
            
            # ' SAR 2:3 '
            sar_string = line[ sar_match.start() : sar_match.end() ]
            
            # '2:3'
            sar_string = sar_string[5:-1]
            
            ( sar_width_string, sar_height_string ) = sar_string.split( ':' )
            
            sar_width = int( sar_width_string )
            sar_height = int( sar_height_string )
            
            width *= sar_width
            width //= sar_height
            
        
        # some vids are rotated, you get this line in the video stream section:
        #     Side data:
        #       displaymatrix: rotation of (-)90.00 degrees
        
        rotation_lines = [ line for line in lines if re.search( 'displaymatrix: rotation of -?90.00 degrees', line ) is not None ]
        
        if len( rotation_lines ) > 0:
            
            ( width, height ) = ( height, width )
            
        
        return ( width, height )
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Error parsing resolution!' )
        
    

def VideoHasAudio( path, info_lines ) -> bool:
    
    ( audio_found, audio_format ) = HydrusAudioHandling.ParseFFMPEGAudio( info_lines )
    
    if not audio_found:
        
        return False
        
    
    # just because video metadata has an audio stream doesn't mean it has audio. some vids have silent audio streams lmao
    # so, let's read it as PCM and see if there is any noise
    # this obviously only works for single audio stream vids, we'll adapt this if someone discovers a multi-stream mkv with a silent channel that doesn't work here
    
    cmd = [ HydrusFFMPEG.FFMPEG_PATH ]
    
    # this is perhaps not sensible for eventual playback and I should rather go for wav file-like and feed into python 'wave' in order to maintain stereo/mono and so on and have easy chunk-reading
    
    cmd.extend( [ '-i', path,
        '-loglevel', 'quiet',
        '-f', 's16le',
        '-' ] )
        
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        with HydrusSubprocess.SubprocessContextStreamer( cmd, bufsize = 65536, text = False ) as streamer:
            
            # silent PCM data is just 00 bytes
            # every now and then, you'll get a couple ffs for some reason, but this is not legit audio data
            
            for chunk_of_pcm_data in streamer.IterateChunks():
                
                # iterating over bytes gives you ints, recall
                # this used to be 'if not 0 or 255', but I found some that had 1 too, so let's just change the tolerance to reduce false positives
                if True in ( 5 <= b <= 250 for b in chunk_of_pcm_data ):
                    
                    return True
                    
                
            
        
    except FileNotFoundError as e:
        
        raise HydrusFFMPEG.HandleFFMPEGFileNotFoundAndGenerateException( e, path )
        
    

# This was built from moviepy's FFMPEG_VideoReader
class VideoRendererFFMPEG( object ):
    
    def __init__( self, path, mime, duration_ms, num_frames, target_resolution, clip_rect = None, start_pos = None ):
        
        if duration_ms <= 0 or duration_ms is None:
            
            duration_ms = 100 # 100ms
            
        
        self._path = path
        self._mime = mime
        self._duration_s = HydrusTime.SecondiseMSFloat( duration_ms )
        self._num_frames = num_frames
        self._target_resolution = target_resolution
        self._clip_rect = clip_rect
        
        if self._mime in HC.MIMES_THAT_WE_CAN_CHECK_FOR_TRANSPARENCY:
            
            self.pix_fmt = 'rgba'
            
        else:
            
            self.pix_fmt = 'rgb24'
            
        
        self.lastread = None
        
        self.fps = self._num_frames / self._duration_s
        
        if self.fps == 0:
            
            self.fps = 24
            
        
        if self.pix_fmt == 'rgba':
            
            self.depth = 4
            
        else:
            
            self.depth = 3
            
        
        ( x, y ) = self._target_resolution
        
        bufsize = self.depth * x * y
        
        self.process_reader: HydrusSubprocess.SubprocessContextReader | None = None
        
        self.bufsize = bufsize
        
        if start_pos is None:
            
            start_pos = 0
            
        
        self.initialize( start_index = start_pos )
        
    
    def __del__( self ):
        
        self.close()
        
    
    def close( self ) -> None:
        
        if self.process_reader is not None:
            
            self.process_reader.CloseProcess()
            
            self.process_reader = None
            
        
    
    def initialize( self, start_index = 0 ):
        
        self.close()
        
        if self._mime in HC.ANIMATIONS: # ffmpeg is pretty bad at scanning these, and they tend to be short, so we'll skip frames instead
            
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
            
        
        do_fast_seek = True
        
        ( w, h ) = self._target_resolution
        
        cmd = [ HydrusFFMPEG.FFMPEG_PATH ]
        
        if do_ss and do_fast_seek: # fast seek
            
            cmd.extend( [ '-ss', "%.03f" % ss ] )
            
        
        cmd.extend( [ '-i', self._path ] )
        
        if do_ss and not do_fast_seek: # slow seek
            
            cmd.extend( [ '-ss', "%.03f" % ss ] )
            
        
        if self._clip_rect is not None:
            
            ( clip_x, clip_y, clip_width, clip_height ) = self._clip_rect
            
            cmd.extend( [ '-vf', 'crop={}:{}:{}:{}'.format( clip_width, clip_height, clip_x, clip_y ) ] )
            
        
        cmd.extend( [
            '-loglevel', 'quiet',
            '-f', 'image2pipe',
            "-pix_fmt", self.pix_fmt,
            "-s", str( w ) + 'x' + str( h ),
            '-vsync', '0',
            '-vcodec', 'rawvideo',
            '-'
        ] )
        
        
        HydrusData.CheckProgramIsNotShuttingDown()
        
        try:
            
            self.process_reader = HydrusSubprocess.SubprocessContextReader( cmd, bufsize = self.bufsize, text = False )
            
        except FileNotFoundError as e:
            
            raise HydrusFFMPEG.HandleFFMPEGFileNotFoundAndGenerateException( e, self._path )
            
        
        if skip_frames > 0:
            
            self.skip_frames( skip_frames )
            
        
    
    def skip_frames( self, n ) -> None:
        
        n = int( n )
        
        ( w, h ) = self._target_resolution
        
        for i in range( n ):
            
            if self.process_reader is not None:
                
                try:
                    
                    frame_of_data = self.process_reader.ReadChunk()
                    
                except HydrusExceptions.SubprocessTimedOut:
                    
                    self.process_reader = None
                    
                
            
            self.pos += 1
            
        
    
    def read_frame( self ):
        
        if self.pos == self._num_frames:
            
            self.initialize()
            
        
        if self.process_reader is None:
            
            result = self.lastread
            
        else:
            
            ( w, h ) = self._target_resolution
            
            frame_of_data = self.process_reader.ReadChunk()
            
            if len( frame_of_data ) != w * h * self.depth:
                
                if self.lastread is None:
                    
                    if self.pos != 0:
                        
                        # this renderer was asked to render starting from mid-vid and this was not possible due to broken key frame index whatever
                        # lets try and render from the vid start before we say the whole vid is broke
                        # I tried doing 'start from 0 and skip n frames', but this is super laggy so would need updates further up the pipe to display this to the user
                        # atm this error states does not communicate to the videocontainer that the current frame num has changed, so the frames are henceforth out of phase
                        
                        #frames_to_jump = self.pos
                        
                        self.set_position( 0 )
                        
                        return self.read_frame()
                        
                    
                    if HC.RUNNING_FROM_SOURCE:
                        
                        message = 'Unable to render that video! Please ensure your FFMPEG is updated (hit _help->about_ to check version), and if it the file still fails, please send it to hydrus dev so he can look at it!'
                        
                    else:
                        
                        message = 'Unable to render that video! It is probably just weird/broken, but hydev would be interested in seeing it!'
                        
                    
                    raise HydrusExceptions.DamagedOrUnusualFileException( message )
                    
                
                result = self.lastread
                
                self.close()
                
            else:
                
                result = numpy.frombuffer( frame_of_data, dtype = 'uint8' ).reshape( ( h, w, self.depth ) )
                
                self.lastread = result
                
            
        
        self.pos += 1
        
        return result
        
    
    def set_position( self, pos ) -> None:
        
        rewind = pos < self.pos
        jump_a_long_way_ahead = pos > self.pos + 60
        
        if rewind or jump_a_long_way_ahead:
            
            self.initialize( pos )
            
        else:
            
            self.skip_frames( pos - self.pos )
            
        
    
    def Stop( self ) -> None:
        
        self.close()
        
