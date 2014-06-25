#import cv2
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
import threading
import time
import traceback
import wx
import cStringIO

# Mime

#magic_mime = magic.Magic( HC.STATIC_DIR + os.path.sep + 'magic.mime', HC.STATIC_DIR + os.path.sep + 'magic.mime.cache' )

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
        
        #numpy_image = cv2.cvtColor( numpy_image, cv2.COLOR_RGB2BGR )
        
        #( retval, thumbnail ) = cv2.imencode( '.jpg', numpy_image, ( cv2.cv.CV_IMWRITE_JPEG_QUALITY, 92 ) )
        
        #if not retval: raise Exception( 'Could not export thumbnail for ' + HC.u( path ) + '!' )
        
    
    return thumbnail
    
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
    
    block_size = 65536
    
    with open( path, 'rb' ) as f:
        
        next_block = f.read( 65536 )
        
        while next_block != '':
            
            h.update( next_block )
            
            next_block = f.read( 65536 )
            
        
        return h.digest()
        
    
def GetMD5AndSHA1FromPath( path ):
    
    h_md5 = hashlib.md5()
    h_sha1 = hashlib.sha1()
    
    block_size = 65536
    
    with open( path, 'rb' ) as f:
        
        next_block = f.read( 65536 )
        
        while next_block != '':
            
            h_md5.update( next_block )
            h_sha1.update( next_block )
            
            next_block = f.read( 65536 )
            
        
        md5 = h_md5.digest()
        sha1 = h_sha1.digest()
        
        return ( md5, sha1 )
        
    
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
    ( 0, 'fLaC', HC.AUDIO_FLAC ),
    ( 0, '\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C', HC.UNDETERMINED_WM )
    ]

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
    