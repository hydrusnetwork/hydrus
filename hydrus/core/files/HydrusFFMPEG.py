import os
import subprocess

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusEnvironment
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusProcess
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
        
    

def GetFFMPEGVersion():
    
    cmd = [ FFMPEG_PATH, '-version' ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        sbp_kwargs = HydrusProcess.GetSubprocessKWArgs( text = True )
        
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
    
    message += '\n' * 2
    message += str( sbp_kwargs )
    message += '\n' * 2
    message += 'STDOUT Response: {}'.format( stdout )
    message += '\n' * 2
    message += 'STDERR Response: {}'.format( stderr )
    
    HydrusData.Print( message )
    
    HydrusEnvironment.DumpEnv()
    
    global FFMPEG_NO_CONTENT_ERROR_PUBBED
    
    FFMPEG_NO_CONTENT_ERROR_PUBBED = True
    
    return 'unknown'
    

def HandleFFMPEGFileNotFound( e, path ):
    
    global FFMPEG_MISSING_ERROR_PUBBED
    
    if not FFMPEG_MISSING_ERROR_PUBBED:
        
        message = f'FFMPEG, which hydrus uses to parse and render some media, and here was trying to look at "{path}", was not found! This may be due to it not being available on your system--or hydrus just being unable to find it.'
        message += '\n' * 2
        
        if HC.PLATFORM_WINDOWS:
            
            message += 'You are on Windows, so there should be a copy of ffmpeg.exe in your install_dir/bin folder. If not, please check if your anti-virus has removed it and restore it through a new install.'
            
        else:
            
            message += 'If you are certain that FFMPEG is installed on your OS and accessible in your PATH, please let hydrus_dev know, as this problem is likely due to an environment problem. You may be able to solve this problem immediately by putting a static build of the ffmpeg executable in your install_dir/bin folder.'
            
        
        message += '\n' * 2
        message += 'You can check your current FFMPEG status through help->about.'
        
        HydrusData.ShowText( message )
        
        FFMPEG_MISSING_ERROR_PUBBED = True
        
    
    raise FileNotFoundError( 'Cannot interact with media because FFMPEG not found--are you sure it is installed? Full error: ' + str( e ) )
    

def HandleFFMPEGNoContent( path, sbp_kwargs, stdout, stderr ):
    
    global FFMPEG_NO_CONTENT_ERROR_PUBBED
    
    if not FFMPEG_NO_CONTENT_ERROR_PUBBED:
        
        message = f'FFMPEG, which hydrus uses to parse and render some media, and here was trying to look at "{path}", did not return any data on a recent file metadata check! More debug info has been written to the log.'
        
        HydrusData.ShowText( message )
        
        message += '\n' * 2
        message += str( sbp_kwargs )
        message += '\n' * 2
        message += 'STDOUT Response: {}'.format( stdout )
        message += '\n' * 2
        message += 'STDERR Response: {}'.format( stderr )
        
        HydrusData.DebugPrint( message )
        
        HydrusEnvironment.DumpEnv()
        
        FFMPEG_NO_CONTENT_ERROR_PUBBED = True
        
    
    raise HydrusExceptions.DataMissing( 'Cannot interact with media because FFMPEG did not return any content.' )
    

def RenderImageToImagePath( path, temp_image_path ):
    
    # -y to overwrite the temp path
    
    if temp_image_path.endswith( '.jpg' ):
        
        # '-q:v 1' does high quality
        cmd = [ FFMPEG_PATH, '-y', "-i", path, "-q:v", "1", temp_image_path ]
        
    else:
        
        cmd = [ FFMPEG_PATH, '-y', "-i", path, temp_image_path ]
        
    
    sbp_kwargs = HydrusProcess.GetSubprocessKWArgs()
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        process = subprocess.Popen( cmd, bufsize = 10**5, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError as e:
        
        HandleFFMPEGFileNotFound( e, path )
        
    
    ( stdout, stderr ) = HydrusThreading.SubprocessCommunicate( process )
    

def RenderImageToRawRGBABytes( path ):
    
    # no dimensions here, so called is responsible for reshaping numpy array or whatever
    
    cmd = [ FFMPEG_PATH, '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-' ]
    
    sbp_kwargs = HydrusProcess.GetSubprocessKWArgs()
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        process = subprocess.Popen( cmd, bufsize = 10**5, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError as e:
        
        HandleFFMPEGFileNotFound( e, path )
        
    
    ( stdout, stderr ) = HydrusThreading.SubprocessCommunicate( process )
    
    return stdout
    

def RenderImageToPNGBytes( path ):
    
    cmd = [ FFMPEG_PATH, '-i', path, '-f', 'image2pipe', '-vcodec', 'png', '-' ]
    
    sbp_kwargs = HydrusProcess.GetSubprocessKWArgs()
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        process = subprocess.Popen( cmd, bufsize = 10**5, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
    except FileNotFoundError as e:
        
        HandleFFMPEGFileNotFound( e, path )
        
    
    ( stdout, stderr ) = HydrusThreading.SubprocessCommunicate( process )
    
    return stdout
    
