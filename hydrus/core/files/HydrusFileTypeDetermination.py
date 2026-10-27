import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core.files import HydrusAnimationHandling
from hydrus.core.files import HydrusArchiveHandling
from hydrus.core.files import HydrusAudioHandling
from hydrus.core.files import HydrusFFMPEG
from hydrus.core.files import HydrusProcreateHandling
from hydrus.core.files import HydrusUgoiraHandling
from hydrus.core.files import HydrusVideoHandling
from hydrus.core.files import HydrusOfficeOpenXMLHandling
from hydrus.core.files import HydrusOLEHandling
from hydrus.core.networking import HydrusNetwork

# TODO: replace this with a FileTypeChecker class or something that tucks all this messy data away more neatly
# do this the next time you visit this place
headers_and_mime = [
    ( ( ( [0], [b'\xff\xd8'] ), ), HC.IMAGE_JPEG ),
    ( ( ( [0], [b'\x89PNG'] ), ), HC.UNDETERMINED_PNG ),
    ( ( ( [0], [b'GIF87a', b'GIF89a'] ), ), HC.UNDETERMINED_GIF ),
    ( ( ( [8], [b'WEBP'] ), ), HC.UNDETERMINED_WEBP ),
    ( ( ( [0], [b'II*\x00', b'MM\x00*'] ), ), HC.IMAGE_TIFF ),
    ( ( ( [0], [b'BM'] ), ), HC.IMAGE_BMP ),
    ( ( ( [0], [b'\x00\x00\x01\x00', b'\x00\x00\x02\x00'] ), ), HC.IMAGE_ICON ),
    ( ( ( [0], [b'qoif'] ), ), HC.IMAGE_QOI ),
    ( ( ( [0], [b'\xFF\x0A', b'\0\0\0\x0CJXL \x0D\x0A\x87\x0A'] ), ), HC.UNDETERMINED_JXL ),
    ( ( ( [0], [b'CWS', b'FWS', b'ZWS'] ), ), HC.APPLICATION_FLASH ),
    ( ( ( [0], [b'FLV'] ), ), HC.VIDEO_FLV ),
    ( ( ( [0], [b'%PDF'] ), ), HC.APPLICATION_PDF ),
    ( ( ( [0], [b'8BPS\x00\x01', b'8BPS\x00\x02'] ), ), HC.APPLICATION_PSD ),
    ( ( ( [0], [b'CSFCHUNK'] ), ), HC.APPLICATION_CLIP ),
    ( ( ( [0], [b'SAI-CANVAS'] ), ), HC.APPLICATION_SAI2 ),
    ( ( ( [0], [b'gimp xcf '] ), ), HC.APPLICATION_XCF ),
    ( ( ( [38, 42, 58, 63],[ b'application/x-krita'] ), ), HC.APPLICATION_KRITA ), # important this comes before zip files because this is also a zip file
    ( ( ( [38, 42, 58, 63],[ b'image/openraster'] ), ), HC.IMAGE_OPENRASTER ),
    ( ( ( [0],[ b'PDN3'] ), ), HC.APPLICATION_PAINT_DOT_NET ), # Paint.NET 3.x, which is since 2006 and has xml data internally it seems
    ( ( ( [38, 43],[ b'application/epub+zip'] ), ), HC.APPLICATION_EPUB ),
    ( ( ( [4], [b'FORM'] ), ( [12], [b'DJVU', b'DJVM', b'PM44', b'BM44', b'SDJV'] ), ), HC.APPLICATION_DJVU ),
    ( ( ( [0], [b'{\\rtf'] ), ), HC.APPLICATION_RTF ),
    ( ( ( [0], [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'] ), ), HC.APPLICATION_ZIP ),
    ( ( ( [0], [b'7z\xBC\xAF\x27\x1C'] ), ), HC.APPLICATION_7Z ),
    ( ( ( [0], [b'\x52\x61\x72\x21\x1A\x07\x00', b'\x52\x61\x72\x21\x1A\x07\x01\x00'] ), ), HC.APPLICATION_RAR ),
    ( ( ( [0], [b'\x1f\x8b'] ), ), HC.APPLICATION_GZIP ),
    ( ( ( [0], [b'hydrus encrypted zip'] ), ), HC.APPLICATION_HYDRUS_ENCRYPTED_ZIP ),
    ( ( ( [4], [b'ftypavif'] ), ), HC.IMAGE_AVIF ),
    ( ( ( [4], [b'ftypavis'] ), ), HC.IMAGE_AVIF_SEQUENCE ),
    ( ( ( [4], [b'ftypmif1'] ), ( [16, 20, 24], [b'avif'] ), ), HC.IMAGE_AVIF ),
    ( ( ( [4], [b'ftypheic', b'ftypheix', b'ftypheim', b'ftypheis'] ), ), HC.IMAGE_HEIC ),
    ( ( ( [4], [b'ftyphevc', b'ftyphevx', b'ftyphevm', b'ftyphevs'] ), ), HC.IMAGE_HEIC_SEQUENCE ),
    ( ( ( [4], [b'ftypmif1'] ), ), HC.IMAGE_HEIF ),
    ( ( ( [4], [b'ftypmsf1'] ), ), HC.IMAGE_HEIF_SEQUENCE ),
    ( ( ( [4], [b'ftypmp4', b'ftypisom', b'ftypM4V', b'ftypMSNV', b'ftypavc1', b'ftypavc1', b'ftypFACE', b'ftypdash'] ), ), HC.UNDETERMINED_MP4 ),
    ( ( ( [4], [b'ftypqt'] ), ), HC.VIDEO_MOV ),
    ( ( ( [0], [b'fLaC'] ), ), HC.AUDIO_FLAC ),
    ( ( ( [0], [b'RIFF'] ), ( [8], [ b'WAVE' ] ) ), HC.AUDIO_WAVE ),
    ( ( ( [0], [b'wvpk'] ), ), HC.AUDIO_WAVPACK ),
    ( ( ( [8], [b'AVI '] ), ), HC.VIDEO_AVI ),
    ( ( ( [0], [b'\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C'] ), ), HC.UNDETERMINED_WM ),
    ( ( ( [0], [b'\x4D\x5A\x90\x00\x03'], ), ), HC.APPLICATION_WINDOWS_EXE ),
    ( ( ( [0], [b'\x31\xbe\x00\x00', b'PO^Q', b'\376\067\0\043', b'\333\245-\0\0\0', b'\xDB\xA5\x2D\x00'] ), ), HC.APPLICATION_DOC ),
    ( ( ( [0], [b'\xED\xDE\xAD\x0B', b'\x0B\xAD\xDE\xAD'], ), ), HC.APPLICATION_PPT ), # https://preservation.tylerthorsted.com/tag/hexspeak/
    ( ( ( [0], [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'] ), ), HC.UNDETERMINED_OLE )
]

def passes_offsets_and_headers_pair( offsets, headers, first_bytes_of_file ) -> bool:
    # TODO: rewrite this garbage
    
    for offset in offsets:
        
        for header in headers:
            
            if first_bytes_of_file[ offset : offset + len( header ) ] == header:
                
                return True
                
            
        
    
    return False
    

def passes_offsets_and_headers( offsets_and_headers, first_bytes_of_file ) -> bool:
    
    # ok we need to match every pair here
    for ( offsets, headers ) in offsets_and_headers:
        
        if not passes_offsets_and_headers_pair( offsets, headers, first_bytes_of_file ):
            
            return False
            
        
    
    return True
    

ALLOW_COMIC_BOOK_ARCHIVE_INSPECTION = True

def GetMime( path, ok_to_look_for_hydrus_updates = False ):
    
    size = os.path.getsize( path )
    
    if size == 0:
        
        raise HydrusExceptions.ZeroSizeFileException( 'File is of zero length!' )
        
    
    if ok_to_look_for_hydrus_updates and size < 64 * 1024 * 1024:
        
        with open( path, 'rb' ) as f:
            
            update_network_bytes = f.read()
            
        
        try:
            
            update = HydrusSerialisable.CreateFromNetworkBytes(
                update_network_bytes,
                False,
                {
                    HydrusSerialisable.SERIALISABLE_TYPE_CONTENT_UPDATE,
                    HydrusSerialisable.SERIALISABLE_TYPE_DEFINITIONS_UPDATE
                }
            )
            
            if isinstance( update, HydrusNetwork.ContentUpdate ):
                
                return HC.APPLICATION_HYDRUS_UPDATE_CONTENT
                
            elif isinstance( update, HydrusNetwork.DefinitionsUpdate ):
                
                return HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS
                
            
        except Exception as e:
            
            pass
            
        
    
    with open( path, 'rb' ) as f:
        
        first_bytes_of_file = f.read( 256 )
        
    
    for ( offsets_and_headers, mime ) in headers_and_mime:
        
        if passes_offsets_and_headers( offsets_and_headers, first_bytes_of_file ):
            
            if mime == HC.APPLICATION_ZIP:
                
                try:
                    
                    if HydrusArchiveHandling.IsEncryptedZip( path ):
                        
                        return HC.APPLICATION_ZIP
                        
                    
                except HydrusExceptions.DamagedOrUnusualFileException:
                    
                    return HC.APPLICATION_ZIP
                    
                
                opendoc_mime = HydrusArchiveHandling.MimeFromOpenDocument( path )

                if opendoc_mime is not None:
                    
                    return opendoc_mime
                    
                
                microsoft_mime = HydrusOfficeOpenXMLHandling.MimeFromMicrosoftOpenXMLDocument( path )
                
                if microsoft_mime is not None:
                    
                    return microsoft_mime
                    
                
                if HydrusProcreateHandling.ZipLooksLikeProcreate( path ):
                    
                    return HC.APPLICATION_PROCREATE
                    
                
                if HydrusUgoiraHandling.ZipLooksLikeUgoira( path ):
                    
                    return HC.ANIMATION_UGOIRA
                    
                
                if ALLOW_COMIC_BOOK_ARCHIVE_INSPECTION and HydrusArchiveHandling.ZipLooksLikeCBZ( path ):
                    
                    return HC.APPLICATION_CBZ
                    
                
                return HC.APPLICATION_ZIP
                
            elif mime in ( HC.UNDETERMINED_WM, HC.UNDETERMINED_MP4 ):
                
                return GetMimeFromFFMPEG( path )
                
            elif mime == HC.UNDETERMINED_PNG:
                
                if HydrusAnimationHandling.IsPNGAnimated( first_bytes_of_file ):
                    
                    return HC.ANIMATION_APNG
                    
                else:
                    
                    return HC.IMAGE_PNG
                    
                
            elif mime == HC.UNDETERMINED_GIF:
                
                if HydrusAnimationHandling.PILAnimationHasDuration( path ):
                    
                    return HC.ANIMATION_GIF
                    
                else:
                    
                    return HC.IMAGE_GIF
                    
                
            elif mime == HC.UNDETERMINED_JXL:
                
                # disabled animated jxl for now--ffmpeg getting in an infinite loop!
                if HydrusVideoHandling.FileIsAnimated( path ):
                    
                    return HC.ANIMATION_JXL
                    
                else:
                    
                    return HC.IMAGE_JXL
                    
                
            elif mime == HC.UNDETERMINED_WEBP:
                
                if HydrusAnimationHandling.PILAnimationHasDuration( path ):
                    
                    return HC.ANIMATION_WEBP
                    
                else:
                    
                    return HC.IMAGE_WEBP
                    
                
            if mime == HC.UNDETERMINED_OLE:
                
                return HydrusOLEHandling.MimeFromOLEFile( path )
                
            else:
                
                return mime
                
            
        
    
    # If the file starts with '{' it is probably JSON
    # but we can't know for sure so we send it over to be checked
    if first_bytes_of_file.startswith( b'{' ) or first_bytes_of_file.startswith( b'[' ):
        
        with open( path, 'rb' ) as f:
            
            potential_json_document_bytes = f.read()
            
            if HydrusText.LooksLikeJSON( potential_json_document_bytes ):
                
                return HC.APPLICATION_JSON
                
            
        
    
    if HydrusText.LooksLikeHTML( first_bytes_of_file ):
        
        return HC.TEXT_HTML
        
    
    if HydrusText.LooksLikeSVG( first_bytes_of_file ): 
        
        return HC.IMAGE_SVG
        
    
    # it is important this goes at the end, because ffmpeg has a billion false positives! and it takes CPU to true negative
    # for instance, it once thought some hydrus update files were mpegs
    # it also thinks txt files can be mpegs
    likely_to_false_positive = True in ( path.endswith( ext ) for ext in ( '.txt', '.log', '.json' ) )
    
    if not likely_to_false_positive:
        
        try:
            
            mime = GetMimeFromFFMPEG( path )
            
            if mime != HC.APPLICATION_UNKNOWN:
                
                return mime
                
            
        except HydrusExceptions.UnsupportedFileException:
            
            pass
            
        except Exception as e:
            
            HydrusData.Print( 'FFMPEG had trouble with: ' + path )
            HydrusData.PrintException( e, do_wait = False )
            
        
    
    return HC.APPLICATION_UNKNOWN
    

def GetMimeFromFFMPEG( path ):
    
    lines = HydrusFFMPEG.GetFFMPEGInfoLines( path )
    
    ( has_video, video_format, video_stream_mapping ) = HydrusVideoHandling.ParseFFMPEGVideoFormat( lines )
    ( has_audio, audio_format, audio_stream_mapping, image_stream_mapping ) = HydrusAudioHandling.ParseFFMPEGAudio( lines )
    
    if not ( has_video or has_audio ):
        
        return HC.APPLICATION_UNKNOWN
        
    
    try:
        
        # TODO: I think rework this guy
        # it is odd that we have nicer per-stream parsing above, with video_format and audio_format, and then use this weird thing to do most of the mime logic
        # maybe it makes sense, since we care about the _file_ container more than the streams, but let's have a look anyway
        mime_text = HydrusVideoHandling.ParseFFMPEGMimeText( lines )
        
    except HydrusExceptions.UnsupportedFileException:
        
        return HC.APPLICATION_UNKNOWN
        
    
    if 'matroska' in mime_text or 'webm' in mime_text:
        
        # a webm has at least vp8/vp9 video and optionally vorbis/opus audio
        
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
        
        container = HydrusVideoHandling.ParseFFMPEGMetadataContainer( lines )
        
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
        
        if HydrusVideoHandling.ParseFFMPEGHasVideo( lines ):
            
            return HC.VIDEO_REALMEDIA
            
        else:
            
            return HC.AUDIO_REALMEDIA
            
        
    elif mime_text == 'asf':
        
        if HydrusVideoHandling.ParseFFMPEGHasVideo( lines ):
            
            return HC.VIDEO_WMV
            
        else:
            
            return HC.AUDIO_WMA
            
        
    elif mime_text == 'wav':
        
        return HC.AUDIO_WAVE
        
    elif mime_text == 'wv':
        
        return HC.AUDIO_WAVPACK
        
    
    return HC.APPLICATION_UNKNOWN
    

headers_and_mime_png = [ ( offsets_and_headers, mime ) for ( offsets_and_headers, mime ) in headers_and_mime if mime in ( HC.UNDETERMINED_PNG, ) ]

def GetIsPNGRealQuick( path ):
    
    with open( path, 'rb' ) as f:
        
        bit_to_check = f.read( 256 )
        
    
    for ( offsets_and_headers, mime ) in headers_and_mime_png:
        
        if passes_offsets_and_headers( offsets_and_headers, bit_to_check ):
            
            return True
            
        
    
    return False
    

headers_and_mime_thumbnails = [ ( offsets_and_headers, mime ) for ( offsets_and_headers, mime ) in headers_and_mime if mime in ( HC.IMAGE_JPEG, HC.UNDETERMINED_PNG ) ]

def GetThumbnailMime( path ):
    
    with open( path, 'rb' ) as f:
        
        bit_to_check = f.read( 256 )
        
    
    for ( offsets_and_headers, mime ) in headers_and_mime_thumbnails:
        
        if passes_offsets_and_headers( offsets_and_headers, bit_to_check ):
            
            if mime == HC.UNDETERMINED_PNG:
                
                return HC.IMAGE_PNG
                
            
            return mime
            
        
    
    return GetMime( path )
    
