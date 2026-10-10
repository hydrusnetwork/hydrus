import hashlib
import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTemp
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusAnimationHandling
from hydrus.core.files import HydrusArchiveHandling
from hydrus.core.files import HydrusClipHandling
from hydrus.core.files import HydrusFFMPEG
from hydrus.core.files import HydrusFileTypeDetermination
from hydrus.core.files import HydrusFlashHandling
from hydrus.core.files import HydrusKritaHandling
from hydrus.core.files import HydrusPaintNETHandling
from hydrus.core.files import HydrusPDFHandling
from hydrus.core.files import HydrusProcreateHandling
from hydrus.core.files import HydrusPSDHandling
from hydrus.core.files import HydrusSVGHandling
from hydrus.core.files import HydrusUgoiraHandling
from hydrus.core.files import HydrusVideoHandling
from hydrus.core.files import HydrusOfficeOpenXMLHandling
from hydrus.core.files import HydrusOLEHandling
from hydrus.core.files import HydrusORAHandling
from hydrus.core.files.images import HydrusImageHandling

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
        
        raise HydrusExceptions.ZeroSizeFileException( 'File is of zero length!' )
        
    
    if mime is None:
        
        mime = HydrusFileTypeDetermination.GetMime( path, ok_to_look_for_hydrus_updates = ok_to_look_for_hydrus_updates )
        
    
    if mime not in HC.ALLOWED_MIMES:
        
        if mime == HC.TEXT_HTML:
            
            raise HydrusExceptions.UnsupportedFileException( 'Looks like HTML -- maybe the client needs to be taught how to recognise this URL and then parse it?' )
            
        elif mime == HC.APPLICATION_JSON:
            
            raise HydrusExceptions.UnsupportedFileException( 'Looks like JSON -- maybe the client needs to be taught how to recognise this URL and then parse it?' )
            
        elif mime == HC.APPLICATION_UNKNOWN:
            
            raise HydrusExceptions.UnsupportedFileException( 'Unknown filetype!' )
            
        else:
            
            raise HydrusExceptions.UnsupportedFileException( 'Filetype is not permitted!' )
            
        
    
    if mime in HC.PIL_HEIF_MIMES and not HydrusImageHandling.HEIF_OK:
        
        raise HydrusExceptions.UnsupportedFileException( 'Sorry, you do not have HEIF support, which is needed to support this filetype ({})! Please rebuild your venv.'.format( HC.mime_string_lookup[ mime ] ) )
        
    
    if mime in HC.PIL_AVIF_MIMES and not HydrusImageHandling.AVIF_OK:
        
        raise HydrusExceptions.UnsupportedFileException( 'Sorry, you do not have AVIF support! Please rebuild your venv.'.format( HC.mime_string_lookup[ mime ] ) )
        
    
    if mime == HC.IMAGE_JXL and not HydrusImageHandling.JXL_OK:
        
        raise HydrusExceptions.UnsupportedFileException( 'Sorry, you do not have JpegXL support! Please rebuild your venv.'.format( HC.mime_string_lookup[ mime ] ) )
        
    
    width = None
    height = None
    duration_ms = None
    num_frames = None
    num_words = None
    
    if mime in HC.MIMES_THAT_DEFINITELY_HAVE_AUDIO:
        
        has_audio = True
        
    else:
        
        has_audio = False
        
    
    # keep this in the specific-first, general-last test order
    if mime == HC.APPLICATION_CBZ or mime == HC.APPLICATION_EPUB:
        
        ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath( 'coverpage_file' )
        
        try:
            
            HydrusArchiveHandling.ExtractCoverPage( path, temp_path, mime )
            
            cover_mime = HydrusFileTypeDetermination.GetMime( temp_path )
            
            ( width, height ) = HydrusImageHandling.GetImageResolution( temp_path, cover_mime )
            
        except Exception as e:
            
            ( width, height ) = ( None, None )
            
        finally:
            
            HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
            
        
    elif mime == HC.APPLICATION_CLIP:
        
        ( ( width, height ), duration_ms, num_frames ) = HydrusClipHandling.GetClipProperties( path )
        
    elif mime == HC.APPLICATION_KRITA:
        
        try:
            
            ( width, height ) = HydrusKritaHandling.GetKraProperties( path )
            
        except HydrusExceptions.NoResolutionFileException:
            
            pass
            
        
    elif mime == HC.IMAGE_OPENRASTER:
        
        try:
            
            ( width, height ) = HydrusORAHandling.GetOraProperties( path )
            
        except HydrusExceptions.NoResolutionFileException:
            
            pass
            
        
    elif mime == HC.APPLICATION_PAINT_DOT_NET:
        
        try:
            
            ( width, height ) = HydrusPaintNETHandling.GetPaintNETResolution( path )
            
        except HydrusExceptions.NoResolutionFileException:
            
            pass
            
        
    elif mime == HC.APPLICATION_PROCREATE:
        
        try:
            
            ( width, height ) = HydrusProcreateHandling.GetProcreateResolution( path )
            
        except Exception as e:
            
            pass
            
        
    elif mime == HC.IMAGE_SVG:
        
        try:
            
            ( width, height ) = HydrusSVGHandling.GetSVGResolution( path )
            
        except HydrusExceptions.NoResolutionFileException:
            
            pass
            
        
    elif mime == HC.APPLICATION_PDF:
        
        try:
            
            ( num_words, ( width, height ) ) = HydrusPDFHandling.GetPDFInfo( path )
            
        except HydrusExceptions.LimitedSupportFileException:
            
            pass
            
        
    elif mime == HC.APPLICATION_PPTX:
        
        try:
            
            ( num_words, ( width, height ) ) = HydrusOfficeOpenXMLHandling.GetPPTXInfo( path )
            
        except HydrusExceptions.LimitedSupportFileException:
            
            pass
            
        
    elif mime == HC.APPLICATION_DOCX:
        
        try:
            
            num_words = HydrusOfficeOpenXMLHandling.GetDOCXInfo( path )
            
        except HydrusExceptions.LimitedSupportFileException:
            
            pass
            
        
    elif mime in HC.POTENTIAL_OFFICE_OLE_MIMES:
        
        try:
            
            num_words = HydrusOLEHandling.OfficeOLEDocumentWordCount( path )
            
        except HydrusExceptions.LimitedSupportFileException:
            
            pass
            
        
    elif mime == HC.APPLICATION_FLASH:
        
        ( ( width, height ), duration_ms, num_frames ) = HydrusFlashHandling.GetFlashProperties( path )
        
    elif mime == HC.APPLICATION_PSD:
        
        try:
            
            ( width, height ) = HydrusPSDHandling.GetPSDResolution( path )
            
        except Exception as e:
            
            HydrusData.Print( 'Problem calculating resolution for "{}":'.format( path ) )
            HydrusData.PrintException( e )
            
        
    elif mime == HC.ANIMATION_UGOIRA: # must be before VIEWABLE_ANIMATIONS
        
        ( ( width, height ), duration_ms, num_frames ) = HydrusUgoiraHandling.GetUgoiraProperties( path )
        
    elif mime in HC.VIDEO or mime in HC.HEIF_TYPE_SEQUENCES or mime in ( HC.IMAGE_AVIF_SEQUENCE, HC.ANIMATION_JXL ):
        
        ( ( width, height ), duration_ms, num_frames, has_audio ) = HydrusVideoHandling.GetFFMPEGVideoProperties( path )
        
    elif mime in HC.VIEWABLE_ANIMATIONS:
        
        ( ( width, height ), duration_ms, num_frames ) = HydrusAnimationHandling.GetAnimationProperties( path, mime )
        
    elif mime in HC.IMAGES:
        
        ( width, height ) = HydrusImageHandling.GetImageResolution( path, mime )
        
    elif mime in HC.AUDIO:
        
        ffmpeg_lines = HydrusFFMPEG.GetFFMPEGInfoLines( path )
        
        ( file_duration_in_s, stream_duration_in_s ) = HydrusVideoHandling.ParseFFMPEGDuration( ffmpeg_lines )
        
        if file_duration_in_s is None:
            
            raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not determine the duration of this file!' )
            
        
        duration_ms = int( file_duration_in_s * 1000 )
        
    
    if width is not None and width < 0:
        
        width *= -1
        
    
    if height is not None and height < 0:
        
        width *= -1
        
    
    if duration_ms is not None and duration_ms < 0:
        
        duration_ms *= -1
        
    
    if num_frames is not None and num_frames < 0:
        
        num_frames *= -1
        
    
    if num_words is not None and num_words < 0:
        
        num_words *= -1
        
    
    return ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words )
    

def GetFileModifiedTimestampMS( path ) -> int:
    
    return HydrusTime.MillisecondiseS( os.path.getmtime( path ) )
    

def GetHashFromPath( path ):
    
    h = hashlib.sha256()
    
    with open( path, 'rb' ) as f:
        
        for block in HydrusPaths.ReadFileLikeAsBlocks( f ):
            
            h.update( block )
            
        
    
    return h.digest()
    
