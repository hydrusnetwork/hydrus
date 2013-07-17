import HydrusAudioHandling
import HydrusConstants as HC
import HydrusDocumentHandling
import HydrusFlashHandling
import HydrusImageHandling
import HydrusVideoHandling
import mutagen
import mutagen.flac
import mutagen.mp3
import mutagen.mp4
import mutagen.oggvorbis
import os
import cStringIO
import threading
import time
import traceback
import wx
from magic import magic

# Mime

magic_mime = magic.Magic( HC.STATIC_DIR + os.path.sep + 'magic.mime', HC.STATIC_DIR + os.path.sep + 'magic.mime.cache' )

def GetFileInfo( file, hash ):
    
    size = len( file )
    
    if size == 0: raise HC.SizeException( 'File is of zero length!' )
    
    mime = GetMimeFromString( file )
    
    if mime not in HC.ALLOWED_MIMES: raise HC.MimeException( 'Filetype is not permitted!' )
    
    width = None
    height = None
    duration = None
    num_frames = None
    num_words = None
    
    if mime in HC.IMAGES:
        
        try: image_container = HydrusImageHandling.RenderImageFromFile( file, hash )
        except: raise HC.ForbiddenException( 'Could not load that file as an image.' )
        
        ( width, height ) = image_container.GetSize()
        
        if image_container.IsAnimated():
            
            duration = image_container.GetTotalDuration()
            num_frames = image_container.GetNumFrames()
            
        
    elif mime == HC.APPLICATION_FLASH:
        
        ( ( width, height ), duration, num_frames ) = HydrusFlashHandling.GetFlashProperties( file )
        
    elif mime == HC.VIDEO_FLV:
        
        ( ( width, height ), duration, num_frames ) = HydrusVideoHandling.GetFLVProperties( file )
        
    elif mime == HC.APPLICATION_PDF: num_words = HydrusDocumentHandling.GetPDFNumWords( file )
    elif mime == HC.AUDIO_MP3: duration = HydrusAudioHandling.GetMP3Duration( file )
    elif mime == HC.AUDIO_OGG: duration = HydrusAudioHandling.GetOGGVorbisDuration( file )
    elif mime == HC.AUDIO_FLAC: duration = HydrusAudioHandling.GetFLACDuration( file )
    
    return ( size, mime, width, height, duration, num_frames, num_words )
    
def GetMimeFromPath( filename ):
    
    with open( filename, 'rb' ) as f: return GetMimeFromFilePointer( f )
    
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
    ( 4, 'ftypmp4', HC.VIDEO_MP4 )
    ]

def GetMimeFromFilePointer( f ):
    
    try:
        
        classification = magic_mime.classify_from_file_object( f )
        
        if classification in HC.mime_enum_lookup: return HC.mime_enum_lookup[ classification ]
        else:
            
            f.seek( 0 )
            
            bit_to_check = f.read( 256 )
            
            for ( offset, header, mime ) in header_and_mime:
                
                offset_bit_to_check = bit_to_check[ offset: ]
                
                if offset_bit_to_check.startswith( header ): return mime
                
            
            f.seek( 0 )
            
            path = HC.TEMP_DIR + os.path.sep + 'mime_parsing'
            
            with open( path, 'wb' ) as temp_f:
                
                block = f.read( 65536 )
                
                while block != '':
                    
                    temp_f.write( block )
                    
                    block = f.read( 65536 )
                    
                
            
            try:
                
                mutagen_object = mutagen.File( path )
                
                if type( mutagen_object ) == mutagen.oggvorbis.OggVorbis: return HC.AUDIO_OGG
                elif type( mutagen_object ) == mutagen.flac.FLAC: return HC.AUDIO_FLAC
                elif type( mutagen_object ) == mutagen.mp3.MP3: return HC.AUDIO_MP3
                elif type( mutagen_object ) == mutagen.mp4.MP4 or mutagen_object is None:
                    
                    # mutagen sometimes does not auto-detect mp3s properly, so try it explicitly
                    mutagen_object = mutagen.mp3.MP3( path )
                    
                    if type( mutagen_object ) == mutagen.mp3.MP3: return HC.AUDIO_MP3
                    
                
            except: print( traceback.format_exc() )
            
            return HC.mime_enum_lookup[ 'unknown mime' ]
            
        
    except:
        wx.MessageBox( traceback.format_exc() )
        raise Exception( 'I could not identify the mime of the file' )
    
def GetMimeFromString( file ):
    
    f = cStringIO.StringIO( file )
    
    return GetMimeFromFilePointer( f )
    