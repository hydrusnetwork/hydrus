import gc
import hashlib
import HydrusAudioHandling
import HydrusConstants as HC
import HydrusDocumentHandling
import HydrusExceptions
import HydrusFlashHandling
import HydrusImageHandling
import HydrusPaths
import HydrusVideoHandling
import os
import tempfile
import threading
import traceback
import cStringIO
import HydrusData

# Mime

header_and_mime = [
    ( 0, '\xff\xd8', HC.IMAGE_JPEG ),
    ( 0, 'GIF87a', HC.IMAGE_GIF ),
    ( 0, 'GIF89a', HC.IMAGE_GIF ),
    ( 0, '\x89PNG', HC.UNDETERMINED_PNG ),
    ( 0, 'BM', HC.IMAGE_BMP ),
    ( 0, 'CWS', HC.APPLICATION_FLASH ),
    ( 0, 'FWS', HC.APPLICATION_FLASH ),
    ( 0, 'ZWS', HC.APPLICATION_FLASH ),
    ( 0, 'FLV', HC.VIDEO_FLV ),
    ( 0, '%PDF', HC.APPLICATION_PDF ),
    ( 0, 'PK\x03\x04', HC.APPLICATION_ZIP ),
    ( 0, 'PK\x05\x06', HC.APPLICATION_ZIP ),
    ( 0, 'PK\x07\x08', HC.APPLICATION_ZIP ),
    ( 0, '7z\xBC\xAF\x27\x1C', HC.APPLICATION_7Z ),
    ( 0, '\x52\x61\x72\x21\x1A\x07\x00', HC.APPLICATION_RAR ),
    ( 0, '\x52\x61\x72\x21\x1A\x07\x01\x00', HC.APPLICATION_RAR ),
    ( 0, 'hydrus encrypted zip', HC.APPLICATION_HYDRUS_ENCRYPTED_ZIP ),
    ( 4, 'ftypmp4', HC.VIDEO_MP4 ),
    ( 4, 'ftypisom', HC.VIDEO_MP4 ),
    ( 4, 'ftypM4V', HC.VIDEO_MP4 ),
    ( 4, 'ftypMSNV', HC.VIDEO_MP4 ),
    ( 4, 'ftypavc1', HC.VIDEO_MP4 ),
    ( 4, 'ftypFACE', HC.VIDEO_MP4 ),
    ( 4, 'ftypdash', HC.VIDEO_MP4 ),
    ( 4, 'ftypqt', HC.VIDEO_MOV ),
    ( 0, 'fLaC', HC.AUDIO_FLAC ),
    ( 8, 'AVI ', HC.VIDEO_AVI ),
    ( 0, '\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C', HC.UNDETERMINED_WM )
    ]

def SaveThumbnailToStreamPIL( pil_image, dimensions, f ):
    
    # when the palette is limited, the thumbnail antialias won't add new colours, so you get nearest-neighbour-like behaviour
    
    original_file_was_png = pil_image.format == 'PNG'
    
    pil_image = HydrusImageHandling.Dequantize( pil_image )
    
    HydrusImageHandling.EfficientlyThumbnailPILImage( pil_image, dimensions )
    
    if original_file_was_png or pil_image.mode == 'RGBA':
        
        pil_image.save( f, 'PNG' )
        
    else:
        
        pil_image.save( f, 'JPEG', quality = 92 )
        
    
def GenerateThumbnail( path, mime, dimensions = HC.UNSCALED_THUMBNAIL_DIMENSIONS ):
    
    if mime in ( HC.IMAGE_JPEG, HC.IMAGE_PNG, HC.IMAGE_GIF ):
        
        thumbnail = GenerateThumbnailFromStaticImage( path, dimensions, mime )
        
    else:
        
        f = cStringIO.StringIO()
        
        if mime == HC.APPLICATION_FLASH:
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            try:
                
                HydrusFlashHandling.RenderPageToFile( path, temp_path, 1 )
                
                pil_image = HydrusImageHandling.GeneratePILImage( temp_path )
                
                SaveThumbnailToStreamPIL( pil_image, dimensions, f )
                
            except:
                
                flash_default_path = os.path.join( HC.STATIC_DIR, 'flash.png' )
                
                pil_image = HydrusImageHandling.GeneratePILImage( flash_default_path )
                
                SaveThumbnailToStreamPIL( pil_image, dimensions, f )
                
            finally:
                
                del pil_image
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
        else:
            
            ( size, mime, width, height, duration, num_frames, num_words ) = GetFileInfo( path )
            
            cropped_dimensions = HydrusImageHandling.GetThumbnailResolution( ( width, height ), dimensions )
            
            renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration, num_frames, cropped_dimensions )
            
            numpy_image = renderer.read_frame()
            
            if numpy_image is None:
                
                raise Exception( 'Could not create a thumbnail from that video!' )
                
            
            pil_image = HydrusImageHandling.GeneratePILImageFromNumpyImage( numpy_image )
            
            SaveThumbnailToStreamPIL( pil_image, dimensions, f )
            
        
        f.seek( 0 )
        
        thumbnail = f.read()
        
        f.close()
        
    
    return thumbnail
    
def GenerateThumbnailFromStaticImagePIL( path, dimensions = HC.UNSCALED_THUMBNAIL_DIMENSIONS, mime = None ):
    
    f = cStringIO.StringIO()
    
    pil_image = HydrusImageHandling.GeneratePILImage( path )
    
    SaveThumbnailToStreamPIL( pil_image, dimensions, f )
    
    f.seek( 0 )
    
    thumbnail = f.read()
    
    f.close()
    
    return thumbnail
    
GenerateThumbnailFromStaticImage = GenerateThumbnailFromStaticImagePIL

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
    
def GetFileInfo( path, mime = None ):
    
    size = os.path.getsize( path )
    
    if size == 0:
        
        raise HydrusExceptions.SizeException( 'File is of zero length!' )
        
    
    if mime is None:
        
        mime = GetMime( path )
        
    
    if mime not in HC.ALLOWED_MIMES:
        
        raise HydrusExceptions.MimeException( 'Filetype is not permitted!' )
        
    
    width = None
    height = None
    duration = None
    num_frames = None
    num_words = None
    
    if mime in ( HC.IMAGE_JPEG, HC.IMAGE_PNG, HC.IMAGE_GIF ):
        
        ( ( width, height ), duration, num_frames ) = HydrusImageHandling.GetImageProperties( path )
        
    elif mime == HC.APPLICATION_FLASH:
        
        ( ( width, height ), duration, num_frames ) = HydrusFlashHandling.GetFlashProperties( path )
        
    elif mime in ( HC.IMAGE_APNG, HC.VIDEO_AVI, HC.VIDEO_FLV, HC.VIDEO_WMV, HC.VIDEO_MOV, HC.VIDEO_MP4, HC.VIDEO_MKV, HC.VIDEO_WEBM, HC.VIDEO_MPEG ):
        
        ( ( width, height ), duration, num_frames ) = HydrusVideoHandling.GetFFMPEGVideoProperties( path )
        
    elif mime == HC.APPLICATION_PDF:
        
        num_words = HydrusDocumentHandling.GetPDFNumWords( path )
        
    elif mime in HC.AUDIO:
        
        ffmpeg_lines = HydrusVideoHandling.GetFFMPEGInfoLines( path )
        
        duration_in_s = HydrusVideoHandling.ParseFFMPEGDuration( ffmpeg_lines )
        
        duration = int( duration_in_s * 1000 )
        
    
    return ( size, mime, width, height, duration, num_frames, num_words )
    
def GetHashFromPath( path ):
    
    h = hashlib.sha256()
    
    with open( path, 'rb' ) as f:
        
        for block in HydrusPaths.ReadFileLikeAsBlocks( f ):
            
            h.update( block )
            
        
    
    return h.digest()
    
def GetMime( path ):
    
    size = os.path.getsize( path )
    
    if size == 0:
        
        raise HydrusExceptions.SizeException( 'File is of zero length!' )
        
    
    with open( path, 'rb' ) as f:
        
        f.seek( 0 )
        
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
        
        HydrusData.Print( 'FFMPEG couldn\'t figure out the mime for: ' + path )
        
    except Exception as e:
        
        HydrusData.Print( 'FFMPEG couldn\'t figure out the mime for: ' + path )
        HydrusData.PrintException( e, do_wait = False )
        
    
    return HC.APPLICATION_UNKNOWN
    
