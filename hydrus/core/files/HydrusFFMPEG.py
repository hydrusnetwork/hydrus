import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusEnvironment
from hydrus.core import HydrusExceptions
from hydrus.core.processes import HydrusSubprocess

FFMPEG_MISSING_ERROR_PUBBED = False
FFMPEG_NO_CONTENT_ERROR_PUBBED = False

if HC.PLATFORM_WINDOWS:
    
    FFMPEG_EXE_NAME = 'ffmpeg.exe'
    
else:
    
    FFMPEG_EXE_NAME = 'ffmpeg'
    

HYDRUS_BIN_FFMPEG_WAS_LOOKED_FOR = False
HYDRUS_BIN_FFMPEG_EXISTS = False
PREFER_SYSTEM_FFMPEG = False

FFMPEG_SUBPROCESS_TIMEOUT = 15

def GetCurrentFFMPEGPath() -> str:
    
    if not PREFER_SYSTEM_FFMPEG:
        
        hydrus_bin_ffmpeg_path = os.path.join( HC.BIN_DIR, FFMPEG_EXE_NAME )
        
        global HYDRUS_BIN_FFMPEG_WAS_LOOKED_FOR
        global HYDRUS_BIN_FFMPEG_EXISTS
        
        if not HYDRUS_BIN_FFMPEG_WAS_LOOKED_FOR:
            
            HYDRUS_BIN_FFMPEG_WAS_LOOKED_FOR = True
            
            HYDRUS_BIN_FFMPEG_EXISTS = os.path.exists( hydrus_bin_ffmpeg_path )
            
        
        if HYDRUS_BIN_FFMPEG_WAS_LOOKED_FOR and HYDRUS_BIN_FFMPEG_EXISTS:
            
            return hydrus_bin_ffmpeg_path
            
        
    
    return FFMPEG_EXE_NAME
    

def CheckFFMPEGError( lines ):
    
    if len( lines ) == 0:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not parse that file--no FFMPEG output given.' )
        
    
    if "No such file or directory" in lines[-1]:
        
        raise IOError( "File not found!" )
        
    
    if 'Invalid data' in lines[-1]:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'FFMPEG could not parse.' )
        
    

# bits of this were originally cribbed from moviepy
def GetFFMPEGInfoLines( path: str, video_stream_mapping_to_count_frames_manually: str | None = None ):
    
    ffmpeg_path = GetCurrentFFMPEGPath()
    
    # ffmpeg -i input.mp4, nice and simple
    
    cmd = [ ffmpeg_path ]
    
    cmd += [ "-xerror", "-i", path ]
    
    if video_stream_mapping_to_count_frames_manually is not None:
        
        # ok what this does is quickly render the video to a null output, which has ffmpeg output the current num_frames in a rolling stdout or whatever
        # the line that is like `frame=123456 789456kB 0.56 frames/s`
        # a later parser can just read the final line and see the actual num frames
        
        # selecting 0:1 of an avifs etc..
        cmd += [ '-map', video_stream_mapping_to_count_frames_manually ]
        
        # I added the -an here originally as a hack to try to handle single-frame webms, but it probably isn't needed with the explicit video_stream_mapping selection
        # let's keep explicitly excluding audio for now though, since we don't care about it and it can only interfere
        
        if HC.PLATFORM_WINDOWS:
            
            cmd += [ "-vf", "scale=-2:120", "-an", "-f", "null", "NUL" ]
            
        else:
            
            cmd += [ "-vf", "scale=-2:120", "-an", "-f", "null", "/dev/null" ]
            
        
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        ( stdout, stderr, returncode ) = HydrusSubprocess.RunSubprocess( cmd, timeout = FFMPEG_SUBPROCESS_TIMEOUT )
        
    except HydrusExceptions.SubprocessTimedOut:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'ffmpeg could not read file info quick enough!' )
        
    except FileNotFoundError as e:
        
        raise HandleFFMPEGFileNotFoundAndGenerateException( e, path )
        
    
    text = stderr
    
    if text is None or len( text ) == 0:
        
        raise HandleFFMPEGNoContentAndGenerateException( path, stdout, stderr )
        
    
    lines = text.splitlines()
    
    lines = [ line.strip() for line in lines ]
    
    CheckFFMPEGError( lines )
    
    return lines
    

def GetFFMPEGVersion():
    
    ffmpeg_path = GetCurrentFFMPEGPath()
    
    cmd = [ ffmpeg_path, '-version' ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        ( stdout, stderr, returncode ) = HydrusSubprocess.RunSubprocess( cmd, timeout = FFMPEG_SUBPROCESS_TIMEOUT )
        
    except FileNotFoundError:
        
        return 'no ffmpeg found at path "{}"'.format( ffmpeg_path )
        
    except HydrusExceptions.SubprocessTimedOut:
        
        return f'ffmpeg took too long to respond from path "{ffmpeg_path}"'
        
    except Exception as e:
        
        HydrusData.ShowException( e )
        
        return 'unable to execute ffmpeg at path "{}"'.format( ffmpeg_path )
        
    
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
    
    message += '\n' * 2
    message += 'STDOUT Response: {}'.format( stdout )
    message += '\n' * 2
    message += 'STDERR Response: {}'.format( stderr )
    
    HydrusData.Print( message )
    
    HydrusEnvironment.DumpEnv()
    
    global FFMPEG_NO_CONTENT_ERROR_PUBBED
    
    FFMPEG_NO_CONTENT_ERROR_PUBBED = True
    
    return 'unknown'
    

def HandleFFMPEGFileNotFoundAndGenerateException( e, path ):
    
    global FFMPEG_MISSING_ERROR_PUBBED
    
    if not FFMPEG_MISSING_ERROR_PUBBED:
        
        message = f'FFMPEG, which hydrus uses to parse and render some media, and here was trying to look at "{path}", was not found! This may be due to it not being available on your system--or hydrus just being unable to find it.'
        message += '\n' * 2
        
        if HC.PLATFORM_WINDOWS:
            
            message += 'You are on Windows, so there should be a copy of ffmpeg.exe in your install_dir/bin folder. If not, please check if your anti-virus has removed it and restore it through a new install.'
            
        else:
            
            message += 'If you are certain that FFMPEG is installed on your OS and accessible in your PATH, please let hydrus_dev know, as this problem is likely due to an environment issue. You may be able to solve this problem immediately by putting a static build of the ffmpeg executable in your install_dir/bin folder.'
            
        
        message += '\n' * 2
        message += 'You can check your current FFMPEG status through help->about.'
        
        HydrusData.ShowText( message )
        
        FFMPEG_MISSING_ERROR_PUBBED = True
        
    
    return FileNotFoundError( 'Cannot interact with media because FFMPEG not found--are you sure it is installed? Full error: ' + str( e ) )
    

def HandleFFMPEGNoContentAndGenerateException( path, stdout, stderr ):
    
    global FFMPEG_NO_CONTENT_ERROR_PUBBED
    
    if not FFMPEG_NO_CONTENT_ERROR_PUBBED:
        
        message = f'FFMPEG, which hydrus uses to parse and render some media, and here was trying to look at "{path}", did not return any data on a recent file metadata check! More debug info has been written to the log.'
        
        HydrusData.ShowText( message )
        
        message += '\n' * 2
        message += 'STDOUT Response: {}'.format( stdout )
        message += '\n' * 2
        message += 'STDERR Response: {}'.format( stderr )
        
        HydrusData.DebugPrint( message )
        
        HydrusEnvironment.DumpEnv()
        
        FFMPEG_NO_CONTENT_ERROR_PUBBED = True
        
    
    return HydrusExceptions.DataMissing( 'Cannot interact with media because FFMPEG did not return any content.' )
    
