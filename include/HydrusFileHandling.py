import gc
import hashlib
import hsaudiotag
import hsaudiotag.auto
import hsaudiotag.flac
import hsaudiotag.mpeg
import hsaudiotag.ogg
import HydrusAudioHandling
import HydrusConstants as HC
import HydrusDocumentHandling
import HydrusExceptions
import HydrusFlashHandling
import HydrusImageHandling
import HydrusVideoHandling
import os
import tempfile
import threading
import traceback
import cStringIO
import subprocess
import HydrusData

# Mime

header_and_mime = [
    ( 0, '\xff\xd8', HC.IMAGE_JPEG ),
    ( 0, 'GIF87a', HC.IMAGE_GIF ),
    ( 0, 'GIF89a', HC.IMAGE_GIF ),
    ( 0, '\x89PNG', HC.IMAGE_PNG ),
    ( 0, 'BM', HC.IMAGE_BMP ),
    ( 0, 'CWS', HC.APPLICATION_FLASH ),
    ( 0, 'FWS', HC.APPLICATION_FLASH ),
    ( 0, 'FLV', HC.VIDEO_FLV ),
    ( 0, '%PDF', HC.APPLICATION_PDF ),
    ( 0, 'PK\x03\x04', HC.APPLICATION_ZIP ),
    ( 0, 'hydrus encrypted zip', HC.APPLICATION_HYDRUS_ENCRYPTED_ZIP ),
    ( 4, 'ftypmp4', HC.VIDEO_MP4 ),
    ( 4, 'ftypisom', HC.VIDEO_MP4 ),
    ( 4, 'ftypM4V', HC.VIDEO_MP4 ),
    ( 0, 'fLaC', HC.AUDIO_FLAC ),
    ( 0, '\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C', HC.UNDETERMINED_WM )
    ]

def ConvertAbsPathToPortablePath( abs_path ):
    
    if abs_path == '': return None
    
    try: return os.path.relpath( abs_path, HC.BASE_DIR )
    except: return abs_path

def CleanUpTempPath( os_file_handle, temp_path ):
    
    try:
        
        os.close( os_file_handle )
        
    except OSError:
        
        gc.collect()
        
        try:
            
            os.close( os_file_handle )
            
        except OSError:
            
            print( 'Could not close the temporary file ' + temp_path )
            
            return
            
        
    
    try:
        
        os.remove( temp_path )
        
    except OSError:
        
        gc.collect()
        
        try:
            
            os.remove( temp_path )
            
        except OSError:
            
            print( 'Could not delete the temporary file ' + temp_path )
            
        
    
def CopyFileLikeToFileLike( f_source, f_dest ):
    
    for block in HydrusData.ReadFileLikeAsBlocks( f_source ): f_dest.write( block )
    
def GenerateThumbnail( path, dimensions = HC.UNSCALED_THUMBNAIL_DIMENSIONS ):
    
    mime = GetMime( path )
    
    if mime in HC.IMAGES:
        
        pil_image = HydrusImageHandling.GeneratePILImage( path )
        
        HydrusImageHandling.EfficientlyThumbnailPILImage( pil_image, dimensions )
        
        f = cStringIO.StringIO()
        
        if pil_image.mode == 'P' and pil_image.info.has_key( 'transparency' ):
            
            pil_image.save( f, 'PNG', transparency = pil_image.info[ 'transparency' ] )
            
        elif pil_image.mode == 'RGBA': pil_image.save( f, 'PNG' )
        else:
            
            pil_image = pil_image.convert( 'RGB' )
            
            pil_image.save( f, 'JPEG', quality=92 )
            
        
        f.seek( 0 )
        
        thumbnail = f.read()
        
        f.close()
        
    else:
        
        ( size, mime, width, height, duration, num_frames, num_words ) = GetFileInfo( path )
        
        cropped_dimensions = HydrusImageHandling.GetThumbnailResolution( ( width, height ), dimensions )
        
        renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration, num_frames, cropped_dimensions )
        
        numpy_image = renderer.read_frame()
        
        pil_image = HydrusImageHandling.GeneratePILImageFromNumpyImage( numpy_image )
        
        f = cStringIO.StringIO()
        
        pil_image.save( f, 'JPEG', quality=92 )
        
        f.seek( 0 )
        
        thumbnail = f.read()
        
        f.close()
        
    
    return thumbnail
    
def GetExtraHashesFromPath( path ):
    
    h_md5 = hashlib.md5()
    h_sha1 = hashlib.sha1()
    h_sha512 = hashlib.sha512()
    
    with open( path, 'rb' ) as f:
        
        for block in HydrusData.ReadFileLikeAsBlocks( f ):
            
            h_md5.update( block )
            h_sha1.update( block )
            h_sha512.update( block )
            
        
    
    md5 = h_md5.digest()
    sha1 = h_sha1.digest()
    sha512 = h_sha512.digest()
    
    return ( md5, sha1, sha512 )
    
def GetFileInfo( path ):
    
    info = os.lstat( path )
    
    size = info[6]
    
    if size == 0: raise HydrusExceptions.SizeException( 'File is of zero length!' )
    
    mime = GetMime( path )
    
    if mime not in HC.ALLOWED_MIMES: raise HydrusExceptions.MimeException( 'Filetype is not permitted!' )
    
    width = None
    height = None
    duration = None
    num_frames = None
    num_words = None
    
    if mime in HC.IMAGES:
        
        ( ( width, height ), duration, num_frames ) = HydrusImageHandling.GetImageProperties( path )
        
    elif mime == HC.APPLICATION_FLASH:
        
        ( ( width, height ), duration, num_frames ) = HydrusFlashHandling.GetFlashProperties( path )
        
    elif mime == HC.VIDEO_FLV:
        
        ( ( width, height ), duration, num_frames ) = HydrusVideoHandling.GetFLVProperties( path )
        
    elif mime in ( HC.VIDEO_WMV, HC.VIDEO_MP4, HC.VIDEO_MKV, HC.VIDEO_WEBM ):
        
        ( ( width, height ), duration, num_frames ) = HydrusVideoHandling.GetFFMPEGVideoProperties( path )
        
    elif mime == HC.APPLICATION_PDF: num_words = HydrusDocumentHandling.GetPDFNumWords( path )
    elif mime == HC.AUDIO_MP3: duration = HydrusAudioHandling.GetMP3Duration( path )
    elif mime == HC.AUDIO_OGG: duration = HydrusAudioHandling.GetOGGVorbisDuration( path )
    elif mime == HC.AUDIO_FLAC: duration = HydrusAudioHandling.GetFLACDuration( path )
    elif mime == HC.AUDIO_WMA: duration = HydrusAudioHandling.GetWMADuration( path )
    
    return ( size, mime, width, height, duration, num_frames, num_words )
    
def GetHashFromPath( path ):
    
    h = hashlib.sha256()
    
    with open( path, 'rb' ) as f:
        
        for block in HydrusData.ReadFileLikeAsBlocks( f ): h.update( block )
        
    
    return h.digest()
    
def GetMime( path ):
    
    with open( path, 'rb' ) as f:
        
        f.seek( 0 )
        
        bit_to_check = f.read( 256 )
        
    
    for ( offset, header, mime ) in header_and_mime:
        
        offset_bit_to_check = bit_to_check[ offset: ]
        
        if offset_bit_to_check.startswith( header ):
            
            if mime == HC.UNDETERMINED_WM:
                
                try:
                    
                    ( ( width, height ), duration, num_frames ) = HydrusVideoHandling.GetCVVideoProperties( path )
                    
                    return HC.VIDEO_WMV
                    
                except: pass # we'll catch wma later
                
            else: return mime
            
        
    
    try:
        
        mime = HydrusVideoHandling.GetMatroskaOrWebm( path )
        
        return mime
        
    except: pass
    
    hsaudio_object = hsaudiotag.auto.File( path )
    
    if hsaudio_object.valid:
        
        if type( hsaudio_object.original ) == hsaudiotag.mpeg.Mpeg: return HC.AUDIO_MP3
        elif type( hsaudio_object.original ) == hsaudiotag.flac.FLAC: return HC.AUDIO_FLAC
        elif type( hsaudio_object.original ) == hsaudiotag.ogg.Vorbis: return HC.AUDIO_OGG
        elif type( hsaudio_object.original ) == hsaudiotag.wma.WMADecoder: return HC.AUDIO_WMA
        
    
    return HC.APPLICATION_UNKNOWN
    
def GetTempFile(): return tempfile.TemporaryFile()
def GetTempFileQuick(): return tempfile.SpooledTemporaryFile( max_size = 1024 * 1024 * 4 )
def GetTempPath(): return tempfile.mkstemp( prefix = 'hydrus' )

def IsImage( mime ): return mime in ( HC.IMAGE_JPEG, HC.IMAGE_GIF, HC.IMAGE_PNG, HC.IMAGE_BMP )

def LaunchDirectory( path ):
    
    def do_it():
        
        if HC.PLATFORM_WINDOWS:
            
            os.startfile( path )
            
        else:
            
            if HC.PLATFORM_OSX: cmd = [ 'open' ]
            elif HC.PLATFORM_LINUX: cmd = [ 'xdg-open' ]
            
            cmd.append( path )
            
            process = subprocess.Popen( cmd, startupinfo = HydrusData.GetSubprocessStartupInfo() )
            
            process.wait()
            
            process.communicate()
            
        
    
    threading.Thread( target = do_it ).start()
    
def LaunchFile( path ):
    
    def do_it():
        
        if HC.PLATFORM_WINDOWS:
            
            os.startfile( path )
            
        else:
            
            if HC.PLATFORM_OSX: cmd = [ 'open' ]
            elif HC.PLATFORM_LINUX: cmd = [ 'xdg-open' ]
            
            cmd.append( path )
            
            process = subprocess.Popen( cmd, startupinfo = HydrusData.GetSubprocessStartupInfo() )
            
            process.wait()
            
            process.communicate()        
            
        
    
    threading.Thread( target = do_it ).start()
    