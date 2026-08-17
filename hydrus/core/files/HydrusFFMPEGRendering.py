from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core.processes import HydrusSubprocess

from hydrus.core.files import HydrusFFMPEG
from hydrus.core.files import HydrusFFMPEGParsing

def RenderAnyAttachedStillImageToPath( file_path, output_path ):
    
    lines = HydrusFFMPEG.GetFFMPEGInfoLines( file_path )
    
    image_lines = HydrusFFMPEGParsing.GetImageStreamLines( lines )
    
    image_stream_mapping = None
    
    if len( image_lines ) > 0:
        
        image_line = image_lines[0]
        
        try:
            
            image_stream_mapping = HydrusFFMPEGParsing.ParseStreamMappingFromStreamLine( image_line )
            
        except Exception as e:
            
            return False
            
        
    
    if image_stream_mapping is None:
        
        return False
        
    
    ffmpeg_path = HydrusFFMPEG.GetCurrentFFMPEGPath()
    
    # no dimensions here, so called is responsible for reshaping numpy array or whatever
    
    # ffmpeg -xerror -y -i m.mp3 -map 0:1 -frames:v 1 -update 1 -f image2 -c:v png output.png
    # note the "-update 1" says "keep overwriting every frame onto the output" just to suppress a warning; -frames:v 1 makes it moot
    cmd = [ ffmpeg_path, "-xerror", '-y', '-i', file_path, '-map', image_stream_mapping, '-frames:v', '1', '-update', '1', '-f', 'image2', '-c:v', 'png', output_path ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        HydrusSubprocess.RunSubprocess( cmd, timeout = HydrusFFMPEG.FFMPEG_SUBPROCESS_TIMEOUT, bufsize = 1024 * 512, text = False )
        
    except HydrusExceptions.SubprocessTimedOut:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'ffmpeg could not render it quick enough!' )
        
    except FileNotFoundError as e:
        
        raise HydrusFFMPEG.HandleFFMPEGFileNotFoundAndGenerateException( e, file_path )
        
    
    return True
    

def RenderImageToImagePath( path, temp_image_path ):
    
    ffmpeg_path = HydrusFFMPEG.GetCurrentFFMPEGPath()
    
    # -y to overwrite the temp path
    
    if temp_image_path.endswith( '.jpg' ):
        
        # '-q:v 1' does high quality
        cmd = [ ffmpeg_path, "-xerror", '-y', "-i", path, "-q:v", "1", temp_image_path ]
        
    else:
        
        cmd = [ ffmpeg_path, "-xerror", '-y', "-i", path, temp_image_path ]
        
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        HydrusSubprocess.RunSubprocess( cmd, timeout = HydrusFFMPEG.FFMPEG_SUBPROCESS_TIMEOUT )
        
    except HydrusExceptions.SubprocessTimedOut:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'ffmpeg could not render it quick enough!' )
        
    except FileNotFoundError as e:
        
        raise HydrusFFMPEG.HandleFFMPEGFileNotFoundAndGenerateException( e, path )
        
    

def RenderImageToRawRGBABytes( path ):
    
    ffmpeg_path = HydrusFFMPEG.GetCurrentFFMPEGPath()
    
    # no dimensions here, so called is responsible for reshaping numpy array or whatever
    
    cmd = [ ffmpeg_path, "-xerror", '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-' ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        ( stdout, stderr, returncode ) = HydrusSubprocess.RunSubprocess( cmd, timeout = HydrusFFMPEG.FFMPEG_SUBPROCESS_TIMEOUT, bufsize = 1024 * 512, text = False )
        
    except HydrusExceptions.SubprocessTimedOut:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'ffmpeg could not render it quick enough!' )
        
    except FileNotFoundError as e:
        
        raise HydrusFFMPEG.HandleFFMPEGFileNotFoundAndGenerateException( e, path )
        
    
    return stdout
    

def RenderImageToPNGBytes( path ):
    
    ffmpeg_path = HydrusFFMPEG.GetCurrentFFMPEGPath()
    
    cmd = [ ffmpeg_path, "-xerror", '-i', path, '-f', 'image2pipe', '-vcodec', 'png', '-' ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        ( stdout, stderr, returncode ) = HydrusSubprocess.RunSubprocess( cmd, timeout = HydrusFFMPEG.FFMPEG_SUBPROCESS_TIMEOUT, bufsize = 1024 * 512, text = False )
        
    except HydrusExceptions.SubprocessTimedOut:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'ffmpeg could not render it quick enough!' )
        
    except FileNotFoundError as e:
        
        raise HydrusFFMPEG.HandleFFMPEGFileNotFoundAndGenerateException( e, path )
        
    
    return stdout
    
