import numpy
import os
import re
import struct
import subprocess

from hydrus.core import HydrusAudioHandling
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusText
from hydrus.core import HydrusThreading

FFMPEG_MISSING_ERROR_PUBBED = False
FFMPEG_NO_CONTENT_ERROR_PUBBED = False

if HC.PLATFORM_WINDOWS:
    
    FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg.exe' )
    
else:
    
    FFMPEG_PATH = os.path.join( HC.BIN_DIR, 'ffmpeg' )
    
if not os.path.exists( FFMPEG_PATH ):
    
    FFMPEG_PATH = os.path.basename( FFMPEG_PATH )
    
def CheckFFMPEGError( lines ):
    
    if len( lines ) == 0:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not parse that file--no FFMPEG output given.' )
        
    
    if "No such file or directory" in lines[-1]:
        
        raise IOError( "File not found!" )
        
    
    if 'Invalid data' in lines[-1]:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'FFMPEG could not parse.' )
        
    
def GetAPNGACTLChunk( file_header_bytes: bytes ):
    
    apng_actl_chunk_header = b'acTL'
    apng_phys_chunk_header = b'pHYs'
    
    first_guess_header = file_header_bytes[ 37:128 ]
    
    if first_guess_header.startswith( apng_actl_chunk_header ):
        
        return first_guess_header
        
    elif first_guess_header.startswith( apng_phys_chunk_header ):
        
        # aha, some weird other png chunk
        # https://wiki.mozilla.org/APNG_Specification
        
        if apng_actl_chunk_header in first_guess_header:
            
            i = first_guess_header.index( apng_actl_chunk_header )
            
            return first_guess_header[i:]
            
        
    
    return None
    
def GetAPNGNumFrames( apng_actl_bytes ):
    
    ( num_frames, ) = struct.unpack( '>I', apng_actl_bytes[ 4 : 8 ] )
    
    return num_frames
    
def GetFFMPEGVersion():
    
    cmd = [ FFMPEG_PATH, '-version' ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        sbp_kwargs = HydrusData.GetSubprocessKWArgs( text = True )
        
        process = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError:
        
        return 'no ffmpeg found at path "{}"'.format( FFMPEG_PATH )
        
    except Exception as e:
        
        HydrusData.ShowException( e )
        
        return 'unable to execute ffmpeg at path "{}"'.format( FFMPEG_PATH )
        
    
    ( stdout, stderr ) = HydrusThreading.SubprocessCommunicate( process )
    
    del process
    
    lines = stdout.splitlines()
    
    if len( lines ) > 0:
        
        # typically 'ffmpeg version [VERSION] Copyright ...
        top_line = lines[0]
        
        if top_line.startswith( 'ffmpeg version ' ):
            
            top_line = top_line.replace( 'ffmpeg version ', '' )
            
            if ' ' in top_line:
                
                version_string = top_line.split( ' ' )[0]
                
                return version_string
                
            
        
    
    message = 'FFMPEG was recently contacted to fetch version information. While FFMPEG could be found, the response could not be understood. Significant debug information has been printed to the log, which hydrus_dev would be interested in.'
    
    HydrusData.ShowText( message )
    
    message += os.linesep * 2
    message += str( sbp_kwargs )
    message += os.linesep * 2
    message += str( os.environ )
    message += os.linesep * 2
    message += 'STDOUT Response: {}'.format( stdout )
    message += os.linesep * 2
    message += 'STDERR Response: {}'.format( stderr )
    
    HydrusData.Print( message )
    
    global FFMPEG_NO_CONTENT_ERROR_PUBBED
    
    FFMPEG_NO_CONTENT_ERROR_PUBBED = True
    
    return 'unknown'
    
# bits of this were originally cribbed from moviepy
def GetFFMPEGInfoLines( path, count_frames_manually = False, only_first_second = False ):
    
    # open the file in a pipe, provoke an error, read output
    
    cmd = [ FFMPEG_PATH, "-i", path ]
    
    if only_first_second:
        
        cmd.insert( 1, '-t' )
        cmd.insert( 2, '1' )
        
    
    if count_frames_manually:
        
        # added -an here to remove audio component, which was sometimes causing convert fails on single-frame music webms
        
        if HC.PLATFORM_WINDOWS:
            
            cmd += [ "-vf", "scale=-2:120", "-an", "-f", "null", "NUL" ]
            
        else:
            
            cmd += [ "-vf", "scale=-2:120", "-an", "-f", "null", "/dev/null" ]
            
        
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs()
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        process = subprocess.Popen( cmd, bufsize = 10**5, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError as e:
        
        global FFMPEG_MISSING_ERROR_PUBBED
        
        if not FFMPEG_MISSING_ERROR_PUBBED:
            
            message = 'FFMPEG, which hydrus uses to parse and render video, was not found! This may be due to it not being available on your system, or hydrus being unable to find it.'
            message += os.linesep * 2
            
            if HC.PLATFORM_WINDOWS:
                
                message += 'You are on Windows, so there should be a copy of ffmpeg.exe in your install_dir/bin folder. If not, please check if your anti-virus has removed it and restore it through a new install.'
                
            else:
                
                message += 'If you are certain that FFMPEG is installed on your OS and accessible in your PATH, please let hydrus_dev know, as this problem is likely due to an environment problem. You may be able to solve this problem immediately by putting a static build of the ffmpeg executable in your install_dir/bin folder.'
                
            
            message += os.linesep * 2
            message += 'You can check your current FFMPEG status through help->about.'
            
            HydrusData.ShowText( message )
            
            FFMPEG_MISSING_ERROR_PUBBED = True
            
        
        raise FileNotFoundError( 'Cannot interact with video because FFMPEG not found--are you sure it is installed? Full error: ' + str( e ) )
        
    
    ( stdout, stderr ) = HydrusThreading.SubprocessCommunicate( process )
    
    data_bytes = stderr
    
    if len( data_bytes ) == 0:
        
        global FFMPEG_NO_CONTENT_ERROR_PUBBED
        
        if not FFMPEG_NO_CONTENT_ERROR_PUBBED:
            
            message = 'FFMPEG, which hydrus uses to parse and render video, did not return any data on a recent file metadata check! More debug info has been written to the log.'
            message += os.linesep * 2
            message += 'You can check this info again through help->about.'
            
            HydrusData.ShowText( message )
            
            message += os.linesep * 2
            message += str( sbp_kwargs )
            message += os.linesep * 2
            message += str( os.environ )
            message += os.linesep * 2
            message += 'STDOUT Response: {}'.format( stdout )
            message += os.linesep * 2
            message += 'STDERR Response: {}'.format( stderr )
            
            HydrusData.DebugPrint( message )
            
            FFMPEG_NO_CONTENT_ERROR_PUBBED = True
            
        
        raise HydrusExceptions.DataMissing( 'Cannot interact with video because FFMPEG did not return any content.' )
        
    
    del process
    
    ( text, encoding ) = HydrusText.NonFailingUnicodeDecode( data_bytes, 'utf-8' )
    
    lines = text.splitlines()
    
    CheckFFMPEGError( lines )
    
    return lines
    
def GetFFMPEGAPNGProperties( path ):
    
    with open( path, 'rb' ) as f:
        
        file_header_bytes = f.read( 256 )
        
    
    apng_actl_bytes = GetAPNGACTLChunk( file_header_bytes )
    
    if apng_actl_bytes is None:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'This APNG had an unusual file header!' )
        
    
    num_frames = GetAPNGNumFrames( apng_actl_bytes )
    
    lines = GetFFMPEGInfoLines( path )
    
    resolution = ParseFFMPEGVideoResolution( lines, png_ok = True )
    
    ( fps, confident_fps ) = ParseFFMPEGFPS( lines, png_ok = True )
    
    if not confident_fps:
        
        fps = 24
        
    
    duration = num_frames / fps
    
    duration_in_ms = int( duration * 1000 )
    
    has_audio = False
    
    return ( resolution, duration_in_ms, num_frames, has_audio )
    
def GetFFMPEGVideoProperties( path, force_count_frames_manually = False ):
    
    lines_for_first_second = GetFFMPEGInfoLines( path, count_frames_manually = True, only_first_second = True )
    
    ( has_video, video_format ) = ParseFFMPEGVideoFormat( lines_for_first_second )
    
    if not has_video:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'File did not appear to have a video stream!' )
        
    
    resolution = ParseFFMPEGVideoResolution( lines_for_first_second )
    
    ( file_duration_in_s, stream_duration_in_s ) = ParseFFMPEGDuration( lines_for_first_second )
    
    # this will have to be fixed when I add audio, and dynamically accounted for on dual vid/audio rendering
    duration = stream_duration_in_s
    
    ( fps, confident_fps ) = ParseFFMPEGFPS( lines_for_first_second )
    
    if duration is None and not confident_fps:
        
        # ok default to fall back on
        ( fps, confident_fps ) = ( 24, True )
        
    
    if fps is None or fps == 0:
        
        fps = 1
        
    
    if duration is None:
        
        force_count_frames_manually = True
        
    else:
        
        num_frames_estimate = int( duration * fps )
        
        # if file is big or long, don't try to force a manual count when one not explicitly asked for
        # we don't care about a dropped frame on a 10min vid tbh
        num_frames_seems_ok_to_count = duration < 15 or num_frames_estimate < 2400
        file_is_ok_size = os.path.getsize( path ) < 128 * 1024 * 1024
        
        if num_frames_seems_ok_to_count and file_is_ok_size:
            
            last_frame_has_unusual_duration = num_frames_estimate != duration * fps
            
            unusual_video_start = file_duration_in_s != stream_duration_in_s
            
            if not confident_fps or last_frame_has_unusual_duration or unusual_video_start:
                
                force_count_frames_manually = True
                
            
        
    
    if force_count_frames_manually:
        
        lines = GetFFMPEGInfoLines( path, count_frames_manually = True )
        
        num_frames = ParseFFMPEGNumFramesManually( lines )
        
        if duration is None:
            
            duration = num_frames / fps
            
        
    else:
        
        num_frames = int( duration * fps )
        
    
    duration_in_ms = int( duration * 1000 )
    
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
    
    if 'matroska' in mime_text or 'webm' in mime_text:
        
        # a webm has at least vp8/vp9 video and optionally vorbis audio
        
        has_webm_video = False
        has_webm_audio = False
        
        if has_video:
            
            webm_video_formats = ( 'vp8', 'vp9' )
            
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
            
            return HC.VIDEO_MKV
            
        
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
        
        if has_audio and ( not has_video or 'mjpeg' in video_format ):
            
            return HC.AUDIO_M4A
            
        else:
            
            return HC.VIDEO_MP4
            
        
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
            
        
    
    return HC.APPLICATION_UNKNOWN
    
def HasVideoStream( path ):
    
    lines = GetFFMPEGInfoLines( path )
    
    return ParseFFMPEGHasVideo( lines )
    
def RenderImageToPNGPath( path, temp_png_path ):
    
    # -y to overwrite the temp path
    cmd = [ FFMPEG_PATH, '-y', "-i", path, temp_png_path ]
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs()
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        process = subprocess.Popen( cmd, bufsize = 10**5, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError as e:
        
        global FFMPEG_MISSING_ERROR_PUBBED
        
        if not FFMPEG_MISSING_ERROR_PUBBED:
            
            message = 'FFMPEG, which hydrus uses to parse and render video, was not found! This may be due to it not being available on your system, or hydrus being unable to find it.'
            message += os.linesep * 2
            
            if HC.PLATFORM_WINDOWS:
                
                message += 'You are on Windows, so there should be a copy of ffmpeg.exe in your install_dir/bin folder. If not, please check if your anti-virus has removed it and restore it through a new install.'
                
            else:
                
                message += 'If you are certain that FFMPEG is installed on your OS and accessible in your PATH, please let hydrus_dev know, as this problem is likely due to an environment problem. You may be able to solve this problem immediately by putting a static build of the ffmpeg executable in your install_dir/bin folder.'
                
            
            message += os.linesep * 2
            message += 'You can check your current FFMPEG status through help->about.'
            
            HydrusData.ShowText( message )
            
            FFMPEG_MISSING_ERROR_PUBBED = True
            
        
        raise FileNotFoundError( 'Cannot interact with video because FFMPEG not found--are you sure it is installed? Full error: ' + str( e ) )
        
    
    ( stdout, stderr ) = HydrusThreading.SubprocessCommunicate( process )
    
def ParseFFMPEGDuration( lines ):
    
    # get duration (in seconds)
    #   Duration: 00:00:02.46, start: 0.033000, bitrate: 1069 kb/s
    try:
        
        # had a vid with 'Duration:' in title, ha ha, so now a regex
        line = [ l for l in lines if re.search( r'^\s*Duration:', l ) is not None ][0]
        
        if 'Duration: N/A' in line:
            
            return ( None, None )
            
        
        if 'start:' in line:
            
            m = re.search( '(start\\: )' + '-?[0-9]+\\.[0-9]*', line )
            
            start_offset = float( line[ m.start() + 7 : m.end() ] )
            
        else:
            
            start_offset = 0
            
        
        match = re.search("[0-9]+:[0-9][0-9]:[0-9][0-9].[0-9][0-9]", line)
        hms = [ float( float_string ) for float_string in line[match.start():match.end()].split(':') ]
        
        if len( hms ) == 1:
            
            duration = hms[0]
            
        elif len( hms ) == 2:
            
            duration = 60 * hms[0] + hms[1]
            
        elif len( hms ) ==3:
            
            duration = 3600 * hms[0] + 60 * hms[1] + hms[2]
            
        
        if duration == 0:
            
            return ( None, None )
            
        
        if start_offset > 0.85 * duration:
            
            # as an example, Duration: 127:57:31.25, start: 460633.291000 lmao
            
            return ( None, None )
            
        
        # we'll keep this for now I think
        if start_offset > 1:
            
            start_offset = 0
            
        
        file_duration = duration + start_offset
        stream_duration = duration
        
        return ( file_duration, stream_duration )
        
    except:
        
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
        
    except:
        
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
                
                if num_frames_in_first_second - 1 <= possible_fps and possible_fps <= num_frames_in_first_second + 1:
                    
                    fps = possible_fps
                    
                    fps_matches_with_first_second = True
                    
                    break
                    
                
            
            confident = sensible_first_second and fps_matches_with_first_second
            
        
        if fps is None or fps == 0:
            
            fps = 1
            confident = False
            
        
        return ( fps, confident )
        
    except:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Error estimating framerate!' )
        
    
def ParseFFMPEGFPSPossibleResults( video_line ):
    
    # get the frame rate
    
    possible_results = set()
    
    match = re.search("( [0-9]*.| )[0-9]* tbr", video_line)
    
    if match is not None:
        
        tbr = video_line[match.start():match.end()].split(' ')[1]
        
        tbr_fps_is_likely_garbage = match is None or tbr.endswith( 'k' ) or float( tbr ) > 144
        
        if not tbr_fps_is_likely_garbage:
            
            possible_results.add( float( tbr ) )
            
        
    
    #
    
    match = re.search("( [0-9]*.| )[0-9]* fps", video_line)
    
    if match is not None:
        
        fps = video_line[match.start():match.end()].split(' ')[1]
        
        fps_is_likely_garbage = match is None or fps.endswith( 'k' ) or float( fps ) > 144
        
        if not fps_is_likely_garbage:
            
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
    
def ParseFFMPEGHasVideo( lines ):
    
    try:
        
        video_line = ParseFFMPEGVideoLine( lines )
        
    except HydrusExceptions.UnsupportedFileException:
        
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
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Error reading mime!' )
        
    
def ParseFFMPEGNumFramesManually( lines ):
    
    frame_lines = [ l for l in lines if l.startswith( 'frame=' ) ]
    
    if len( frame_lines ) == 0:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Video appears to be broken and non-renderable--perhaps a damaged single-frame video?' )
        
    
    final_line = frame_lines[-1] # there will be many progress rows, counting up as the file renders. we hence want the final one
    
    l = final_line
    
    l = l.replace( 'frame=', '' )
    
    while l.startswith( ' ' ):
        
        l = l[1:]
        
    
    try:
        
        frames_string = l.split( ' ' )[0]
        
        num_frames = int( frames_string )
        
    except:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Video was unable to render correctly--could not parse ffmpeg output line: "{}"'.format( final_line ) )
        
    
    return num_frames
    
def ParseFFMPEGVideoFormat( lines ):
    
    try:
        
        line = ParseFFMPEGVideoLine( lines )
        
    except HydrusExceptions.UnsupportedFileException:
        
        return ( False, 'unknown' )
        
    
    try:
        
        match = re.search( r'(?<=Video\:\s).+?(?=,)', line )
        
        video_format = match.group()
        
    except:
        
        video_format = 'unknown'
        
    
    return ( True, video_format )
    
def ParseFFMPEGVideoLine( lines, png_ok = False ):
    
    if png_ok:
        
        bad_video_formats = [ 'jpg' ]
        
    else:
        
        bad_video_formats = [ 'png', 'jpg' ]
        
    
    # get the output line that speaks about video
    # the ^\sStream is to exclude the 'title' line, when it exists, includes the string 'Video: ', ha ha
    lines_video = [ l for l in lines if re.search( r'^\s*Stream', l ) is not None and 'Video: ' in l and True not in ( 'Video: {}'.format( bad_video_format ) in l for bad_video_format in bad_video_formats ) ] # mp3 says it has a 'png' video stream
    
    if len( lines_video ) == 0:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not find video information!' )
        
    
    line = lines_video[0]
    
    return line
    
def ParseFFMPEGVideoResolution( lines, png_ok = False ):
    
    try:
        
        line = ParseFFMPEGVideoLine( lines, png_ok = png_ok )
        
        # get the size, of the form 460x320 (w x h)
        match = re.search(" [0-9]*x[0-9]*(,| )", line)
        
        resolution_string = line[match.start():match.end()-1]
        
        ( width_string, height_string ) = resolution_string.split( 'x' )
        
        width = int( width_string )
        height = int( height_string )
        
        sar_match = re.search( "[\\[\\s]SAR [0-9]*:[0-9]* ", line )
        
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
            
        
        return ( width, height )
        
    except:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Error parsing resolution!' )
        
    
def VideoHasAudio( path, info_lines ):
    
    ( audio_found, audio_format ) = HydrusAudioHandling.ParseFFMPEGAudio( info_lines )
    
    if not audio_found:
        
        return False
        
    
    # just because video metadata has an audio stream doesn't mean it has audio. some vids have silent audio streams lmao
    # so, let's read it as PCM and see if there is any noise
    # this obviously only works for single audio stream vids, we'll adapt this if someone discovers a multi-stream mkv with a silent channel that doesn't work here
    
    cmd = [ FFMPEG_PATH ]
    
    # this is perhaps not sensible for eventual playback and I should rather go for wav file-like and feed into python 'wave' in order to maintain stereo/mono and so on and have easy chunk-reading
    
    cmd.extend( [ '-i', path,
        '-loglevel', 'quiet',
        '-f', 's16le',
        '-' ] )
        
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs()
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        process = subprocess.Popen( cmd, bufsize = 65536, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError as e:
        
        HydrusData.ShowText( 'Cannot render audio--FFMPEG not found!' )
        
        raise
        
    
    # silent PCM data is just 00 bytes
    # every now and then, you'll get a couple ffs for some reason, but this is not legit audio data
    
    try:
        
        chunk_of_pcm_data = process.stdout.read( 65536 )
        
        while len( chunk_of_pcm_data ) > 0:
            
            # iterating over bytes gives you ints, recall
            if True in ( b != 0 and b != 255 for b in chunk_of_pcm_data ):
                
                return True
                
            
            chunk_of_pcm_data = process.stdout.read( 65536 )
            
        
        return False
        
    finally:
        
        process.terminate()
        
        process.stdout.close()
        process.stderr.close()
        
    
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
            
        
        do_fast_seek = True
        
        ( w, h ) = self._target_resolution
        
        cmd = [ FFMPEG_PATH ]
        
        if do_ss and do_fast_seek: # fast seek
            
            cmd.extend( [ '-ss', "%.03f" % ss ] )
            
        
        cmd.extend( [ '-i', self._path ] )
        
        if do_ss and not do_fast_seek: # slow seek
            
            cmd.extend( [ '-ss', "%.03f" % ss ] )
            
        
        cmd.extend( [
            '-loglevel', 'quiet',
            '-f', 'image2pipe',
            "-pix_fmt", self.pix_fmt,
            "-s", str( w ) + 'x' + str( h ),
            '-vsync', '0',
            '-vcodec', 'rawvideo',
            '-'
        ] )
            
        
        sbp_kwargs = HydrusData.GetSubprocessKWArgs()
        
        HydrusData.CheckProgramIsNotShuttingDown()
        
        try:
            
            self.process = subprocess.Popen( cmd, bufsize = self.bufsize, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
            
        except FileNotFoundError as e:
            
            HydrusData.ShowText( 'Cannot render video--FFMPEG not found!' )
            
            raise
            
        
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
                        
                        #frames_to_jump = self.pos
                        
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
        
