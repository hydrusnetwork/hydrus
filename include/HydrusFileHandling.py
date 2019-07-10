import gc
import hashlib
from . import HydrusAudioHandling
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusDocumentHandling
from . import HydrusExceptions
from . import HydrusFlashHandling
from . import HydrusImageHandling
from . import HydrusNetwork
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusText
from . import HydrusVideoHandling
import os
import threading
import traceback

# Mime

header_and_mime = [
    ( 0, b'\xff\xd8', HC.IMAGE_JPEG ),
    ( 0, b'GIF87a', HC.IMAGE_GIF ),
    ( 0, b'GIF89a', HC.IMAGE_GIF ),
    ( 0, b'\x89PNG', HC.UNDETERMINED_PNG ),
    ( 8, b'WEBP', HC.IMAGE_WEBP ),
    ( 0, b'II*\x00', HC.IMAGE_TIFF ),
    ( 0, b'MM\x00*', HC.IMAGE_TIFF ),
    ( 0, b'BM', HC.IMAGE_BMP ),
    ( 0, b'\x00\x00\x01\x00', HC.IMAGE_ICON ),
    ( 0, b'\x00\x00\x02\x00', HC.IMAGE_ICON ),
    ( 0, b'CWS', HC.APPLICATION_FLASH ),
    ( 0, b'FWS', HC.APPLICATION_FLASH ),
    ( 0, b'ZWS', HC.APPLICATION_FLASH ),
    ( 0, b'FLV', HC.VIDEO_FLV ),
    ( 0, b'%PDF', HC.APPLICATION_PDF ),
    ( 0, b'8BPS\x00\x01', HC.APPLICATION_PSD ),
    ( 0, b'8BPS\x00\x02', HC.APPLICATION_PSD ), # PSB, which is basically PSD v2 and does giganto resolution
    ( 0, b'PK\x03\x04', HC.APPLICATION_ZIP ),
    ( 0, b'PK\x05\x06', HC.APPLICATION_ZIP ),
    ( 0, b'PK\x07\x08', HC.APPLICATION_ZIP ),
    ( 0, b'7z\xBC\xAF\x27\x1C', HC.APPLICATION_7Z ),
    ( 0, b'\x52\x61\x72\x21\x1A\x07\x00', HC.APPLICATION_RAR ),
    ( 0, b'\x52\x61\x72\x21\x1A\x07\x01\x00', HC.APPLICATION_RAR ),
    ( 0, b'hydrus encrypted zip', HC.APPLICATION_HYDRUS_ENCRYPTED_ZIP ),
    ( 4, b'ftypmp4', HC.VIDEO_MP4 ),
    ( 4, b'ftypisom', HC.VIDEO_MP4 ),
    ( 4, b'ftypM4V', HC.VIDEO_MP4 ),
    ( 4, b'ftypMSNV', HC.VIDEO_MP4 ),
    ( 4, b'ftypavc1', HC.VIDEO_MP4 ),
    ( 4, b'ftypFACE', HC.VIDEO_MP4 ),
    ( 4, b'ftypdash', HC.VIDEO_MP4 ),
    ( 4, b'ftypqt', HC.VIDEO_MOV ),
    ( 0, b'fLaC', HC.AUDIO_FLAC ),
    ( 8, b'AVI ', HC.VIDEO_AVI ),
    ( 0, b'\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C', HC.UNDETERMINED_WM )
    ]

def GenerateThumbnailBytes( path, target_resolution, mime, duration, num_frames, percentage_in = 35 ):
    
    if mime in ( HC.IMAGE_JPEG, HC.IMAGE_PNG, HC.IMAGE_GIF, HC.IMAGE_WEBP, HC.IMAGE_TIFF, HC.IMAGE_ICON ): # not apng atm
        
        thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesFromStaticImagePath( path, target_resolution, mime )
        
    else:
        
        if mime == HC.APPLICATION_FLASH:
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            try:
                
                HydrusFlashHandling.RenderPageToFile( path, temp_path, 1 )
                
                thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesFromStaticImagePath( temp_path, target_resolution, mime )
                
            except:
                
                thumb_path = os.path.join( HC.STATIC_DIR, 'flash.png' )
                
                thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesFromStaticImagePath( thumb_path, target_resolution, mime )
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
        else:
            
            renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration, num_frames, target_resolution )
            
            renderer.read_frame() # this initialises the renderer and loads the first frame as a fallback
            
            desired_thumb_frame = int( ( percentage_in / 100.0 ) * num_frames )
            
            renderer.set_position( desired_thumb_frame )
            
            numpy_image = renderer.read_frame()
            
            if numpy_image is None:
                
                raise Exception( 'Could not create a thumbnail from that video!' )
                
            
            numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, target_resolution ) # just in case ffmpeg doesn't deliver right
            
            thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesNumPy( numpy_image, mime )
            
            renderer.Stop()
            
            del renderer
            
        
    
    return thumbnail_bytes
    
def GetExtraHashesFromPath( path ):
    
    h_md5 = hashlib.md5()
    h_sha1 = hashlib.sha1()
    h_sha512 = hashlib.sha512()
    
    with open( path, 'rb' ) as f:
        
        for block in HydrusPaths.ReadFileLikeAsBlocks( f ):
            
            h_md5.update( block )
            h_sha1.update( block )
            h_sha512.update( block )
            
        
    
    md5 = h_md5.digest()
    sha1 = h_sha1.digest()
    sha512 = h_sha512.digest()
    
    return ( md5, sha1, sha512 )
    
def GetFileInfo( path, mime = None, ok_to_look_for_hydrus_updates = False ):
    
    size = os.path.getsize( path )
    
    if size == 0:
        
        raise HydrusExceptions.SizeException( 'File is of zero length!' )
        
    
    if mime is None:
        
        mime = GetMime( path, ok_to_look_for_hydrus_updates = ok_to_look_for_hydrus_updates )
        
    
    if mime not in HC.ALLOWED_MIMES:
        
        if mime == HC.TEXT_HTML:
            
            raise HydrusExceptions.MimeException( 'Looks like HTML -- maybe the client needs to be taught how to parse this?' )
            
        elif mime == HC.APPLICATION_UNKNOWN:
            
            raise HydrusExceptions.MimeException( 'Unknown filetype!' )
            
        else:
            
            raise HydrusExceptions.MimeException( 'Filetype is not permitted!' )
            
        
    
    width = None
    height = None
    duration = None
    num_frames = None
    num_words = None
    
    if mime in ( HC.IMAGE_JPEG, HC.IMAGE_PNG, HC.IMAGE_GIF, HC.IMAGE_WEBP, HC.IMAGE_TIFF, HC.IMAGE_ICON ):
        
        ( ( width, height ), duration, num_frames ) = HydrusImageHandling.GetImageProperties( path, mime )
        
    elif mime == HC.APPLICATION_FLASH:
        
        ( ( width, height ), duration, num_frames ) = HydrusFlashHandling.GetFlashProperties( path )
        
    elif mime in ( HC.IMAGE_APNG, HC.VIDEO_AVI, HC.VIDEO_FLV, HC.VIDEO_WMV, HC.VIDEO_MOV, HC.VIDEO_MP4, HC.VIDEO_MKV, HC.VIDEO_WEBM, HC.VIDEO_MPEG ):
        
        ( ( width, height ), duration, num_frames ) = HydrusVideoHandling.GetFFMPEGVideoProperties( path )
        
    elif mime == HC.APPLICATION_PDF:
        
        num_words = HydrusDocumentHandling.GetPDFNumWords( path ) # this now give None until a better solution can be found
        
    elif mime == HC.APPLICATION_PSD:
        
        ( width, height ) = HydrusImageHandling.GetPSDResolution( path )
        
    elif mime in HC.AUDIO:
        
        ffmpeg_lines = HydrusVideoHandling.GetFFMPEGInfoLines( path )
        
        ( file_duration_in_s, stream_duration_in_s ) = HydrusVideoHandling.ParseFFMPEGDuration( ffmpeg_lines )
        
        duration = int( file_duration_in_s * 1000 )
        
    
    if width is not None and width < 0:
        
        width *= -1
        
    
    if height is not None and height < 0:
        
        width *= -1
        
    
    if duration is not None and duration < 0:
        
        duration *= -1
        
    
    if num_frames is not None and num_frames < 0:
        
        num_frames *= -1
        
    
    if num_words is not None and num_words < 0:
        
        num_words *= -1
        
    
    return ( size, mime, width, height, duration, num_frames, num_words )
    
def GetHashFromPath( path ):
    
    h = hashlib.sha256()
    
    with open( path, 'rb' ) as f:
        
        for block in HydrusPaths.ReadFileLikeAsBlocks( f ):
            
            h.update( block )
            
        
    
    return h.digest()
    
def GetMime( path, ok_to_look_for_hydrus_updates = False ):
    
    size = os.path.getsize( path )
    
    if size == 0:
        
        raise HydrusExceptions.SizeException( 'File is of zero length!' )
        
    
    with open( path, 'rb' ) as f:
        
        bit_to_check = f.read( 256 )
        
    
    for ( offset, header, mime ) in header_and_mime:
        
        offset_bit_to_check = bit_to_check[ offset: ]
        
        if offset_bit_to_check.startswith( header ):
            
            if mime == HC.UNDETERMINED_WM:
                
                if HydrusVideoHandling.HasVideoStream( path ):
                    
                    return HC.VIDEO_WMV
                    
                
                # we'll catch and verify wma later
                
            elif mime == HC.UNDETERMINED_PNG:
                
                if HydrusVideoHandling.HasVideoStream( path ):
                    
                    return HC.IMAGE_APNG
                    
                else:
                    
                    return HC.IMAGE_PNG
                    
                
            else:
                
                return mime
                
            
        
    
    try:
        
        mime = HydrusVideoHandling.GetMime( path )
        
        if mime != HC.APPLICATION_UNKNOWN:
            
            return mime
            
        
    except HydrusExceptions.MimeException:
        
        pass
        
    except Exception as e:
        
        HydrusData.Print( 'FFMPEG had trouble with: ' + path )
        HydrusData.PrintException( e, do_wait = False )
        
    
    if HydrusText.LooksLikeHTML( bit_to_check ):
        
        return HC.TEXT_HTML
        
    
    if ok_to_look_for_hydrus_updates:
        
        with open( path, 'rb' ) as f:
            
            update_network_bytes = f.read()
            
        
        try:
            
            update = HydrusSerialisable.CreateFromNetworkBytes( update_network_bytes )
            
            if isinstance( update, HydrusNetwork.ContentUpdate ):
                
                return HC.APPLICATION_HYDRUS_UPDATE_CONTENT
                
            elif isinstance( update, HydrusNetwork.DefinitionsUpdate ):
                
                return HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS
                
            
        except:
            
            pass
            
        
    
    return HC.APPLICATION_UNKNOWN
    
