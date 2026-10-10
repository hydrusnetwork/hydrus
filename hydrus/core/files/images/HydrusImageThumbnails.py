import collections

from PIL import Image as PILImage
from PIL import ImageOps as PILImageOps

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTemp
from hydrus.core.files import HydrusArchiveHandling
from hydrus.core.files import HydrusClipHandling
from hydrus.core.files import HydrusFFMPEGRendering
from hydrus.core.files import HydrusFileTypeDetermination
from hydrus.core.files import HydrusKritaHandling
from hydrus.core.files import HydrusPaintNETHandling
from hydrus.core.files import HydrusPDFHandling
from hydrus.core.files import HydrusProcreateHandling
from hydrus.core.files import HydrusPSDHandling
from hydrus.core.files import HydrusSVGHandling
from hydrus.core.files import HydrusUgoiraHandling
from hydrus.core.files import HydrusVideoHandling
from hydrus.core.files import HydrusOfficeOpenXMLHandling
from hydrus.core.files import HydrusORAHandling
from hydrus.core.files.images import HydrusImageHandling

THUMBNAIL_SCALE_DOWN_ONLY = 0
THUMBNAIL_SCALE_TO_FIT = 1
THUMBNAIL_SCALE_TO_FILL = 2

thumbnail_scale_str_lookup = {
    THUMBNAIL_SCALE_DOWN_ONLY : 'scale down only',
    THUMBNAIL_SCALE_TO_FIT : 'scale to fit',
    THUMBNAIL_SCALE_TO_FILL : 'scale to fill'
}

mimes_to_default_thumbnail_paths = collections.defaultdict( lambda: HydrusStaticDir.GetStaticPath( 'hydrus.png' ) )

def InitialiseMimesToDefaultThumbnailPaths():
    
    for mime in HC.AUDIO:
        
        mimes_to_default_thumbnail_paths[ mime ] = HydrusStaticDir.GetStaticPath( 'audio.png' )
        
    
    for mime in HC.VIDEO:
        
        mimes_to_default_thumbnail_paths[ mime ] = HydrusStaticDir.GetStaticPath( 'video.png' )
        
    
    for mime in HC.ANIMATIONS:
        
        mimes_to_default_thumbnail_paths[ mime ] = HydrusStaticDir.GetStaticPath( 'video.png' )
        
    
    for mime in HC.ARCHIVES:
        
        mimes_to_default_thumbnail_paths[ mime ] = HydrusStaticDir.GetStaticPath( 'zip.png' )
        
    
    for mime in HC.IMAGES:
        
        mimes_to_default_thumbnail_paths[ mime ] = HydrusStaticDir.GetStaticPath( 'image.png' )
        
    
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_UNKNOWN ] = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
    
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_PDF ] = HydrusStaticDir.GetStaticPath( 'pdf.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_DOCX ] = HydrusStaticDir.GetStaticPath( 'docx.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_XLSX ] = HydrusStaticDir.GetStaticPath( 'xlsx.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_PPTX ] = HydrusStaticDir.GetStaticPath( 'pptx.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_DOC ] = HydrusStaticDir.GetStaticPath( 'doc.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_XLS ] = HydrusStaticDir.GetStaticPath( 'xls.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_PPT ] = HydrusStaticDir.GetStaticPath( 'ppt.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_EPUB ] = HydrusStaticDir.GetStaticPath( 'epub.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_DJVU ] = HydrusStaticDir.GetStaticPath( 'djvu.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_PSD ] = HydrusStaticDir.GetStaticPath( 'psd.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_CLIP ] = HydrusStaticDir.GetStaticPath( 'clip.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_SAI2 ] = HydrusStaticDir.GetStaticPath( 'sai.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_KRITA ] = HydrusStaticDir.GetStaticPath( 'krita.png' )
    mimes_to_default_thumbnail_paths[ HC.IMAGE_OPENRASTER ] = HydrusStaticDir.GetStaticPath( 'image.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_PAINT_DOT_NET ] = HydrusStaticDir.GetStaticPath( 'paintnet.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_FLASH ] = HydrusStaticDir.GetStaticPath( 'flash.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_XCF ] = HydrusStaticDir.GetStaticPath( 'xcf.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_PROCREATE ] = HydrusStaticDir.GetStaticPath( 'procreate.png' )
    mimes_to_default_thumbnail_paths[ HC.APPLICATION_RTF ] = HydrusStaticDir.GetStaticPath( 'rtf.png' )
    mimes_to_default_thumbnail_paths[ HC.IMAGE_SVG ] = HydrusStaticDir.GetStaticPath( 'svg.png' )
    

def GenerateDefaultThumbnailNumPyFromPath( path: str, target_resolution: tuple[ int, int ] ):
    
    thumb_image = HydrusImageHandling.GeneratePILImage( path )
    
    try:
        
        pil_image = PILImageOps.pad( thumb_image, target_resolution, PILImage.Resampling.LANCZOS )
        
        try:
            
            result = HydrusImageHandling.GenerateNumPyImageFromPILImage( pil_image, strip_useless_alpha = False )
            
        finally:
            
            pil_image.close()
            
        
    finally:
        
        thumb_image.close()
        
    
    return result
    

def GenerateThumbnailBytesFromNumPy( numpy_image ) -> bytes:
    
    if len( numpy_image.shape ) == 2:
        
        depth = 3
        
    else:
        
        ( im_height, im_width, depth ) = numpy_image.shape
        
    
    if depth == 4:
        
        ext = '.png'
        
        params = HydrusImageHandling.CV_PNG_THUMBNAIL_ENCODE_PARAMS
        
    else:
        
        ext = '.jpg'
        
        params = HydrusImageHandling.CV_JPEG_THUMBNAIL_ENCODE_PARAMS
        
    
    return HydrusImageHandling.GenerateFileBytesNumPy( numpy_image, ext, params )
    

def GetThumbnailResolution( image_resolution: tuple[ int, int ], bounding_dimensions: tuple[ int, int ], thumbnail_scale_type: int, thumbnail_dpr_percent: int ) -> tuple[ int, int ]:
    
    ( im_width, im_height ) = image_resolution
    ( bounding_width, bounding_height ) = bounding_dimensions
    
    if thumbnail_dpr_percent != 100:
        
        thumbnail_dpr = thumbnail_dpr_percent / 100
        
        bounding_height = int( bounding_height * thumbnail_dpr )
        bounding_width = int( bounding_width * thumbnail_dpr )
        
    
    # this is appropriate for the crazy (0x0) svg or whatever we have, since we will _try_ to render it properly later on
    # but if it fails to render, we'll still get a fairly nice filetype.png or hydrus.png fallback
    # we don't want to pass around 0x0 and have a handler everywhere
    if im_width is None or im_width == 0 or im_height is None or im_height == 0:
        
        im_width = bounding_width
        im_height = bounding_width
        
    
    # TODO SVG thumbs should always scale up to the bounding dimensions
    
    if thumbnail_scale_type == THUMBNAIL_SCALE_DOWN_ONLY:
        
        if bounding_width >= im_width and bounding_height >= im_height:
            
            return ( im_width, im_height )
            
        
    
    image_ratio = im_width / im_height
    
    width_ratio = im_width / bounding_width
    height_ratio = im_height / bounding_height
    
    image_is_wider_than_bounding_box = width_ratio > height_ratio
    image_is_taller_than_bounding_box = height_ratio > width_ratio
    
    thumbnail_width = bounding_width
    thumbnail_height = bounding_height
    
    if thumbnail_scale_type in ( THUMBNAIL_SCALE_DOWN_ONLY, THUMBNAIL_SCALE_TO_FIT ):
        
        if image_is_taller_than_bounding_box: # i.e. the height will be at bounding height
            
            thumbnail_width = im_width / height_ratio
            
        elif image_is_wider_than_bounding_box: # i.e. the width will be at bounding width
            
            thumbnail_height = im_height / width_ratio
            
        
    elif thumbnail_scale_type == THUMBNAIL_SCALE_TO_FILL:
        
        # we do min 5.0 here to stop really tall and thin images getting zoomed in from width 1px to 150 and getting a thumbnail with a height of 75,000 pixels
        # in this case the line image is already crazy distorted, so we don't mind squishing it
        
        if image_is_taller_than_bounding_box: # i.e. the width will be at bounding width, the height will spill over
            
            thumbnail_height = bounding_width * min( 5.0, 1 / image_ratio )
            
        elif image_is_wider_than_bounding_box: # i.e. the height will be at bounding height, the width will spill over
            
            thumbnail_width = bounding_height * min( 5.0, image_ratio )
            
        
        # old stuff that actually clipped the size of the thing
        '''
        clip_x = 0
        clip_y = 0
        clip_width = im_width
        clip_height = im_height
        
        if width_ratio > height_ratio:
            
            clip_width = max( int( im_width * height_ratio / width_ratio ), 1 )
            clip_x = ( im_width - clip_width ) // 2
            
        elif height_ratio > width_ratio:
            
            clip_height = max( int( im_height * width_ratio / height_ratio ), 1 )
            clip_y = ( im_height - clip_height ) // 2
            
        
        clip_rect = ( clip_x, clip_y, clip_width, clip_height )
        '''
        
    
    thumbnail_width = int( thumbnail_width )
    thumbnail_height = int( thumbnail_height )
    
    thumbnail_width = max( thumbnail_width, 1 )
    thumbnail_height = max( thumbnail_height, 1 )
    
    return ( thumbnail_width, thumbnail_height )
    









def GenerateDefaultThumbnail( mime: int, target_resolution: tuple[ int, int ] ):
    
    thumb_path = mimes_to_default_thumbnail_paths[ mime ]
    
    return GenerateDefaultThumbnailNumPyFromPath( thumb_path, target_resolution )
    

def GenerateThumbnailBytes( path, target_resolution, mime, duration_ms, num_frames, percentage_in = 35 ):
    
    thumbnail_numpy = GenerateThumbnailNumPy( path, target_resolution, mime, duration_ms, num_frames, percentage_in = percentage_in )

    return GenerateThumbnailBytesFromNumPy( thumbnail_numpy )
    

def GenerateThumbnailNumPyFromStaticImagePath( path, target_resolution, mime ):
    
    numpy_image = HydrusImageHandling.GenerateNumPyImage( path, mime )
    
    thumbnail_numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, target_resolution )
    
    return thumbnail_numpy_image
    

def PrintMoreThumbErrorInfo( e: Exception, message, extra_description: str | None = None ):
    
    if not isinstance( e, HydrusExceptions.NoThumbnailFileException ):
        
        HydrusData.Print( message )
        
        if extra_description is not None:
            
            HydrusData.Print( f'Extra info: {extra_description}' )
            
        
        HydrusData.PrintException( e )
        
    

def GenerateThumbnailNumPy( path, target_resolution, mime, duration_ms, num_frames, percentage_in = 35, extra_description = None ):
    
    thumbnail_numpy = None
    
    if mime in HC.IMAGES or mime == HC.ANIMATION_WEBP:
        
        try:
            
            thumbnail_numpy = GenerateThumbnailNumPyFromStaticImagePath( path, target_resolution, mime )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime == HC.ANIMATION_UGOIRA:
        
        try:
            
            desired_thumb_frame_index = int( ( percentage_in / 100.0 ) * ( num_frames - 1 ) )
            
            thumbnail_numpy = HydrusUgoiraHandling.GenerateThumbnailNumPyFromUgoiraPath( path, target_resolution, desired_thumb_frame_index )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime in HC.VIDEO or mime in HC.ANIMATIONS:
        
        thumbnail_numpy = GenerateThumbnailNumPyUsingFFMPEGVideoRenderer( path, target_resolution, mime, duration_ms, num_frames, percentage_in = percentage_in, extra_description = extra_description )
        
    elif mime in HC.AUDIO:
        
        thumbnail_numpy = GenerateThumbnailNumPyAudio( path, target_resolution, mime, extra_description = extra_description )
        
    elif mime in HC.IMAGE_PROJECT_FILES or mime in HC.APPLICATIONS or mime in HC.ARCHIVES:
        
        thumbnail_numpy = GenerateThumbnailNumPyWeirdApplicationGubbins( path, target_resolution, mime, extra_description = extra_description )
        
    
    if thumbnail_numpy is None:
        
        return GenerateDefaultThumbnail( mime, target_resolution )
        
    
    return thumbnail_numpy
    

def GenerateThumbnailNumPyAudio( path, target_resolution, mime, extra_description = None ):
    
    thumbnail_numpy = None
    
    ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath( 'audio_image' )
    
    try:
        
        there_was_one = HydrusFFMPEGRendering.RenderAnyAttachedStillImageToPath( path, temp_path )
        
        if there_was_one:
            
            image_mime = HydrusFileTypeDetermination.GetMime( temp_path )
            
            thumbnail_numpy = GenerateThumbnailNumPyFromStaticImagePath( temp_path, target_resolution, image_mime )
            
        
    except Exception as e:
        
        PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
        
        thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
        
    finally:
        
        HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
        
    
    return thumbnail_numpy
    

def GenerateThumbnailNumPyUsingFFMPEGVideoRenderer( path, target_resolution, mime, duration_ms, num_frames, percentage_in = 35, extra_description = None ):
    
    thumbnail_numpy = None
    
    desired_thumb_frame_index = int( ( percentage_in / 100.0 ) * ( num_frames - 1 ) )
    
    try:
        
        renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration_ms, num_frames, target_resolution, start_pos = desired_thumb_frame_index )
        
        try:
            
            thumbnail_numpy = renderer.read_frame()
            
        finally:
            
            renderer.Stop()
            
        
    except Exception as e:
        
        message = 'Problem generating thumbnail for "{}" at frame {} ({})--FFMPEG could not render it.'.format( path, desired_thumb_frame_index, HydrusNumbers.FloatToPercentage( percentage_in / 100.0 ) )
        
        PrintMoreThumbErrorInfo( e, message, extra_description = extra_description )
        
        thumbnail_numpy = None
        
    
    if thumbnail_numpy is None and desired_thumb_frame_index != 0:
        
        # try first frame instead
        
        try:
            
            renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration_ms, num_frames, target_resolution )
            
            try:
                
                thumbnail_numpy = renderer.read_frame()
                
            finally:
                
                renderer.Stop()
                
            
        except Exception as e:
            
            message = 'Problem generating thumbnail for "{}" at first frame--FFMPEG could not render it.'.format( path )
            
            PrintMoreThumbErrorInfo( e, message, extra_description = extra_description )
            
            thumbnail_numpy = None
            
        
    
    if thumbnail_numpy is not None:
        
        thumbnail_numpy =  HydrusImageHandling.ResizeNumPyImage( thumbnail_numpy, target_resolution ) # just in case ffmpeg doesn't deliver right
        
    
    return thumbnail_numpy
    

def GenerateThumbnailNumPyWeirdApplicationGubbins( path, target_resolution, mime, extra_description = None ):
    
    thumbnail_numpy = None
    
    if mime == HC.APPLICATION_CBZ or mime == HC.APPLICATION_EPUB:
        
        ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath( 'cover_page_thumb' )
        
        try:
            
            HydrusArchiveHandling.ExtractCoverPage( path, temp_path, mime )
            
            cover_mime = HydrusFileTypeDetermination.GetMime( temp_path )
            
            if cover_mime == HC.TEXT_HTML:
                
                raise HydrusExceptions.NoThumbnailFileException( 'Do not support an HTML thumbnail for epubs yet!' )
                
            elif cover_mime == HC.IMAGE_SVG:
                
                thumbnail_numpy = HydrusSVGHandling.GenerateThumbnailNumPyFromSVGPath( temp_path, target_resolution )
                
            else:
                
                thumbnail_numpy = GenerateThumbnailNumPyFromStaticImagePath( temp_path, target_resolution, cover_mime )
                
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        finally:
            
            HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
            
        
    elif mime == HC.APPLICATION_CLIP:
        
        ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath( 'clip_thumb' )
        
        try:
            
            HydrusClipHandling.ExtractDBPNGToPath( path, temp_path )
            
            thumbnail_numpy = GenerateThumbnailNumPyFromStaticImagePath( temp_path, target_resolution, HC.IMAGE_PNG )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        finally:
            
            HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
            
        
    elif mime == HC.APPLICATION_KRITA:
        
        try:
            
            thumbnail_numpy = HydrusKritaHandling.GenerateThumbnailNumPyFromKraPath( path, target_resolution )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime == HC.IMAGE_OPENRASTER:
        
        try:
            
            thumbnail_numpy = HydrusORAHandling.GenerateThumbnailNumPyFromOraPath( path, target_resolution )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime == HC.APPLICATION_PAINT_DOT_NET:
        
        try:
            
            thumbnail_numpy = HydrusPaintNETHandling.GenerateThumbnailNumPyFromPaintNET( path, target_resolution )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime == HC.APPLICATION_PROCREATE:
        
        ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath( 'procreate_thumb' )
        
        try:
            
            HydrusProcreateHandling.ExtractZippedThumbnailToPath( path, temp_path )
            
            thumbnail_numpy = GenerateThumbnailNumPyFromStaticImagePath( temp_path, target_resolution, HC.IMAGE_PNG )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        finally:
            
            HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
            
        
    elif mime == HC.APPLICATION_PSD:
        
        try:
            
            thumbnail_numpy = HydrusPSDHandling.GenerateThumbnailNumPyFromPSDPath( path, target_resolution )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime == HC.IMAGE_SVG: 
        
        try:
            
            thumbnail_numpy = HydrusSVGHandling.GenerateThumbnailNumPyFromSVGPath( path, target_resolution )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime == HC.APPLICATION_PDF:
        
        try:
            
            thumbnail_numpy = HydrusPDFHandling.GenerateThumbnailNumPyFromPDFPath( path, target_resolution )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime == HC.APPLICATION_PPTX:
        
        try:
            
            thumbnail_numpy = HydrusOfficeOpenXMLHandling.GenerateThumbnailNumPyFromOfficePath( path, target_resolution )
            
        except HydrusExceptions.NoThumbnailFileException:
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        except Exception as e:
            
            PrintMoreThumbErrorInfo( e, f'Problem generating thumbnail for "{path}".', extra_description = extra_description )
            
            thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
            
        
    elif mime == HC.APPLICATION_FLASH:
        
        # leaving this in place for now, rather than saying 'flash has no thumbs now', to keep legacy flash thumbs alive
        thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
        
    
    if thumbnail_numpy is None:
        
        thumbnail_numpy = GenerateDefaultThumbnail( mime, target_resolution )
        
    
    return thumbnail_numpy
    
