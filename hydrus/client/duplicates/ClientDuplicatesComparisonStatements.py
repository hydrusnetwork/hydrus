import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client.caches import ClientCachesBase
from hydrus.client.files.images import ClientVisualData
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

COMPLEX_COMPARISON_FILETYPES = set()
COMPLEX_COMPARISON_FILETYPES.update( HC.IMAGE_PROJECT_FILES )
COMPLEX_COMPARISON_FILETYPES.update( HC.APPLICATIONS )
COMPLEX_COMPARISON_FILETYPES.update( HC.ARCHIVES )

def GetDuplicateComparisonScoreFast( shown_media_result: ClientMediaResult.MediaResult, comparison_media_result: ClientMediaResult.MediaResult ):
    
    ( statements_and_scores, they_are_pixel_duplicates ) = GetDuplicateComparisonStatementsFast( shown_media_result, comparison_media_result )
    
    total_score = sum( ( score for ( statement, score ) in statements_and_scores.values() ) )
    
    return total_score
    

# TODO: All this will be replaced by tools being developed for the duplicates auto-resolution system
def GetDuplicateComparisonStatementsFast( shown_media_result: ClientMediaResult.MediaResult, comparison_media_result: ClientMediaResult.MediaResult ):
    
    new_options = CG.client_controller.new_options
    
    duplicate_comparison_score_higher_filesize = new_options.GetInteger( 'duplicate_comparison_score_higher_filesize' )
    duplicate_comparison_score_much_higher_filesize = new_options.GetInteger( 'duplicate_comparison_score_much_higher_filesize' )
    duplicate_comparison_score_higher_resolution = new_options.GetInteger( 'duplicate_comparison_score_higher_resolution' )
    duplicate_comparison_score_much_higher_resolution = new_options.GetInteger( 'duplicate_comparison_score_much_higher_resolution' )
    duplicate_comparison_score_more_tags = new_options.GetInteger( 'duplicate_comparison_score_more_tags' )
    duplicate_comparison_score_older = new_options.GetInteger( 'duplicate_comparison_score_older' )
    duplicate_comparison_score_nicer_ratio = new_options.GetInteger( 'duplicate_comparison_score_nicer_ratio' )
    duplicate_comparison_score_has_audio = new_options.GetInteger( 'duplicate_comparison_score_has_audio' )
    
    #
    
    statements_and_scores = {}
    
    s_mime = shown_media_result.GetMime()
    c_mime = comparison_media_result.GetMime()
    
    # size
    
    s_size = shown_media_result.GetSize()
    c_size = comparison_media_result.GetSize()
    
    they_are_pixel_duplicates = False
    
    if s_mime in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH and c_mime in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH and shown_media_result.GetResolution() == comparison_media_result.GetResolution():
        
        s_pixel_hash = shown_media_result.GetFileInfoManager().pixel_hash
        c_pixel_hash = comparison_media_result.GetFileInfoManager().pixel_hash
        
        s_width = shown_media_result.GetFileInfoManager().width
        c_width = comparison_media_result.GetFileInfoManager().width
        
        if s_pixel_hash is None or c_pixel_hash is None:
            
            statement = 'could not determine if files were pixel-for-pixel duplicates!'
            score = 0
            
            statements_and_scores[ 'pixel_duplicates' ] = ( statement, score )
            
        elif s_pixel_hash == c_pixel_hash and s_width == c_width:
            
            # this is not appropriate for, say, PSD files
            # TODO: if and when we get 'this webp is lossy/lossless' detection, we can do this for a webp
            other_file_is_pixel_png_appropriate_filetypes = {
                HC.IMAGE_JPEG
            }
            
            they_are_pixel_duplicates = True
            
            if s_mime == HC.IMAGE_PNG and c_mime in other_file_is_pixel_png_appropriate_filetypes:
                
                statement = 'this is a pixel-for-pixel duplicate png!\nit is almost certainly a derivative copy!'
                
                score = -100
                
            elif s_mime in other_file_is_pixel_png_appropriate_filetypes and c_mime == HC.IMAGE_PNG:
                
                statement = 'other file is a pixel-for-pixel duplicate png!\nthis is almost certainly an original!'
                
                score = 100
                
            else:
                
                statement = 'images are pixel-for-pixel duplicates!'
                
                score = 0
                
            
            statements_and_scores[ 'pixel_duplicates' ] = ( statement, score )
            
        
    
    if s_size != c_size:
        
        all_measurements_are_good = None not in ( s_size, c_size ) and True not in ( d <= 0 for d in ( s_size, c_size ) )
        
        if all_measurements_are_good:
            
            absolute_size_ratio = max( s_size, c_size ) / min( s_size, c_size )
            
            if absolute_size_ratio > 2.0:
                
                if s_size > c_size:
                    
                    operator = '>>'
                    score = duplicate_comparison_score_much_higher_filesize
                    
                else:
                    
                    operator = '<<'
                    score = -duplicate_comparison_score_much_higher_filesize
                    
                
            elif absolute_size_ratio > 1.05:
                
                if s_size > c_size:
                    
                    operator = '>'
                    score = duplicate_comparison_score_higher_filesize
                    
                else:
                    
                    operator = '<'
                    score = -duplicate_comparison_score_higher_filesize
                    
                
            else:
                
                operator = HC.UNICODE_APPROX_EQUAL
                score = 0
                
            
            if s_size > c_size:
                
                sign = '+'
                percentage_difference = ( s_size / c_size ) - 1.0
                
            else:
                
                sign = ''
                percentage_difference = ( s_size / c_size ) - 1.0
                
            
            percentage_different_string = ' ({}{})'.format( sign, HydrusNumbers.FloatToPercentage( percentage_difference ) )
            
            if they_are_pixel_duplicates:
                
                score = 0
                
            
            statement = '{} {} {}{}'.format( HydrusData.ToHumanBytes( s_size ), operator, HydrusData.ToHumanBytes( c_size ), percentage_different_string )
            
            statements_and_scores[ 'filesize' ]  = ( statement, score )
            
        
    
    # higher/same res
    
    s_resolution = shown_media_result.GetResolution()
    c_resolution = comparison_media_result.GetResolution()
    
    ( s_w, s_h ) = s_resolution
    ( c_w, c_h ) = c_resolution
    
    all_measurements_are_good = None not in ( s_w, s_h, c_w, c_h ) and True not in ( d <= 0 for d in ( s_w, s_h, c_w, c_h ) )
    
    if all_measurements_are_good:
        
        if s_w == c_w and s_h == c_h:
            
            score = 0
            statement = f'both are {ClientData.ResolutionToPrettyString(s_resolution)}'
            
            statements_and_scores[ 'resolution' ] = ( statement, score )
            
        else:
            
            resolution_ratio = ( s_w * s_h ) / ( c_w * c_h )
            
            if resolution_ratio == 1.0:
                
                operator = '!='
                score = 0
                
            elif resolution_ratio > 2.0:
                
                operator = '>>'
                score = duplicate_comparison_score_much_higher_resolution
                
            elif resolution_ratio > 1.00:
                
                operator = '>'
                score = duplicate_comparison_score_higher_resolution
                
            elif resolution_ratio < 0.5:
                
                operator = '<<'
                score = -duplicate_comparison_score_much_higher_resolution
                
            else:
                
                operator = '<'
                score = -duplicate_comparison_score_higher_resolution
                
            
            s_string = ClientData.ResolutionToPrettyString( s_resolution )
            
            if s_w % 2 == 1 or s_h % 2 == 1:
                
                s_string += ' (unusual)'
                
            
            c_string = ClientData.ResolutionToPrettyString( c_resolution )
            
            if c_w % 2 == 1 or c_h % 2 == 1:
                
                c_string += ' (unusual)'
                
            
            statement = '{} {} {}'.format( s_string, operator, c_string )
            
            statements_and_scores[ 'resolution' ] = ( statement, score )
            
            #
            
            s_ratio = s_w / s_h
            c_ratio = c_w / c_h
            
            s_nice = s_ratio in HC.NICE_RATIOS
            c_nice = c_ratio in HC.NICE_RATIOS
            
            if s_nice or c_nice:
                
                if s_nice:
                    
                    s_string = HC.NICE_RATIOS[ s_ratio ]
                    
                else:
                    
                    s_string = 'unusual'
                    
                
                if c_nice:
                    
                    c_string = HC.NICE_RATIOS[ c_ratio ]
                    
                else:
                    
                    c_string = 'unusual'
                    
                
                if s_nice and c_nice:
                    
                    operator = '-'
                    score = 0
                    
                elif s_nice:
                    
                    operator = '>'
                    score = duplicate_comparison_score_nicer_ratio
                    
                elif c_nice:
                    
                    operator = '<'
                    score = -duplicate_comparison_score_nicer_ratio
                    
                
                if s_string == c_string:
                    
                    statement = 'both {}'.format( s_string )
                    
                else:
                    
                    statement = '{} {} {}'.format( s_string, operator, c_string )
                    
                
                statements_and_scores[ 'ratio' ] = ( statement, score )
                
                
            
        
    
    
    # same/diff mime
    
    if s_mime in COMPLEX_COMPARISON_FILETYPES or c_mime in COMPLEX_COMPARISON_FILETYPES:
        
        score = -100 
        
    else:
        
        score = 0
        
    
    if s_mime == c_mime:
        
        statement = 'both are {}s'.format( HC.mime_string_lookup[ s_mime ] )
        
        statements_and_scores[ 'mime' ] = ( statement, score )
        
    else:
        
        statement = '{} vs {}'.format( HC.mime_string_lookup[ s_mime ], HC.mime_string_lookup[ c_mime ] )
        
        statements_and_scores[ 'mime' ] = ( statement, score )
        
    
    # audio/no audio
    
    s_has_audio = shown_media_result.HasAudio()
    c_has_audio = comparison_media_result.HasAudio()
    
    if s_has_audio or c_has_audio:
        
        if s_has_audio and c_has_audio:
            
            audio_statement = 'both have audio'
            score = 0
            
        elif s_has_audio:
            
            audio_statement = 'this has audio, the other does not'
            score = duplicate_comparison_score_has_audio
            
        else:
            
            audio_statement = 'the other has audio, this does not'
            score = - duplicate_comparison_score_has_audio
            
        
        statements_and_scores[ 'has_audio' ] = ( audio_statement, score )
        

    # more tags
    
    s_num_tags = len( shown_media_result.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
    c_num_tags = len( comparison_media_result.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
    
    if s_num_tags == c_num_tags:
        
        score = 0
        statement = f'both have {HydrusNumbers.ToHumanInt(s_num_tags)} tags'
        
    else:
        
        operator = '?'
        
        if s_num_tags > 0 and c_num_tags > 0:
            
            if s_num_tags > c_num_tags:
                
                operator = '>'
                score = duplicate_comparison_score_more_tags
                
            else:
                
                operator = '<'
                score = -duplicate_comparison_score_more_tags
                
            
        elif s_num_tags > 0:
            
            operator = '>>'
            score = duplicate_comparison_score_more_tags
            
        elif c_num_tags > 0:
            
            operator = '<<'
            score = -duplicate_comparison_score_more_tags
            
        
        statement = '{} tags {} {} tags'.format( HydrusNumbers.ToHumanInt( s_num_tags ), operator, HydrusNumbers.ToHumanInt( c_num_tags ) )
        
    
    statements_and_scores[ 'num_tags' ] = ( statement, score )
    
    # older
    
    s_import_timestamp = HydrusTime.SecondiseMS( shown_media_result.GetLocationsManager().GetTimesManager().GetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
    c_import_timestamp = HydrusTime.SecondiseMS( comparison_media_result.GetLocationsManager().GetTimesManager().GetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
    
    one_month = 86400 * 30
    
    if s_import_timestamp is not None and c_import_timestamp is not None:
        
        if abs( s_import_timestamp - c_import_timestamp ) < one_month:
            
            score = 0
            
            statement = 'imported at similar time ({})'.format( HydrusTime.TimestampToPrettyTimeDelta( int( ( s_import_timestamp + c_import_timestamp ) / 2 ) ) )
            
        else:
            
            if s_import_timestamp < c_import_timestamp:
                
                operator = 'older than'
                score = duplicate_comparison_score_older
                
            else:
                
                operator = 'newer than'
                score = -duplicate_comparison_score_older
                
            
            if they_are_pixel_duplicates:
                
                score = 0
                
            
            statement = '{}, {} {}'.format( HydrusTime.TimestampToPrettyTimeDelta( s_import_timestamp, history_suffix = ' old' ), operator, HydrusTime.TimestampToPrettyTimeDelta( c_import_timestamp, history_suffix = ' old' ) )
            
        
        statements_and_scores[ 'time_imported' ] = ( statement, score )
        
    
    s_has_transparency = shown_media_result.GetFileInfoManager().has_transparency
    c_has_transparency = comparison_media_result.GetFileInfoManager().has_transparency
    
    if s_has_transparency or c_has_transparency:
        
        if s_has_transparency and c_has_transparency:
            
            transparency_statement = 'both have transparency'
            
        elif s_has_transparency:
            
            transparency_statement = 'this has transparency, the other is opaque'
            
        else:
            
            transparency_statement = 'this is opaque, the other has transparency'
            
        
        statements_and_scores[ 'has_transparency' ] = ( transparency_statement, 0 )
        
    
    s_has_exif = shown_media_result.GetFileInfoManager().has_exif
    c_has_exif = comparison_media_result.GetFileInfoManager().has_exif
    
    if s_has_exif or c_has_exif:
        
        if s_has_exif and c_has_exif:
            
            exif_statement = 'both have exif data'
            
        elif s_has_exif:
            
            exif_statement = 'this has exif data, the other does not'
            
        else:
            
            exif_statement = 'the other has exif data, this does not'
            
        
        statements_and_scores[ 'exif_data' ] = ( exif_statement, 0 )
        
    
    s_has_human_readable_embedded_metadata = shown_media_result.GetFileInfoManager().has_human_readable_embedded_metadata
    c_has_human_readable_embedded_metadata = comparison_media_result.GetFileInfoManager().has_human_readable_embedded_metadata
    
    if s_has_human_readable_embedded_metadata ^ c_has_human_readable_embedded_metadata:
        
        if s_has_human_readable_embedded_metadata:
            
            embedded_metadata_statement = 'this has embedded metadata, the other does not'
            
        else:
            
            embedded_metadata_statement = 'the other has embedded metadata, this does not'
            
        
        statements_and_scores[ 'embedded_metadata' ] = ( embedded_metadata_statement, 0 )
        
    
    s_has_icc = shown_media_result.GetFileInfoManager().has_icc_profile
    c_has_icc = comparison_media_result.GetFileInfoManager().has_icc_profile
    
    if s_has_icc or c_has_icc:
        
        if s_has_icc and c_has_icc:
            
            icc_statement = 'both have icc profile'
            
        elif s_has_icc:
            
            icc_statement = 'this has icc profile, the other does not'
            
        else:
            
            icc_statement = 'the other has icc profile, this does not'
            
        
        statements_and_scores[ 'icc_profile' ] = ( icc_statement, 0 )
        
    
    # hacky, for vid dedupe
    
    s_has_duration = shown_media_result.HasDuration()
    c_has_duration = comparison_media_result.HasDuration()
    
    if s_has_duration or c_has_duration:
        
        s_duration_s = shown_media_result.GetDurationS()
        c_duration_s = comparison_media_result.GetDurationS()
        
        if s_has_duration and c_has_duration:
            
            if s_duration_s == c_duration_s:
                
                statement = 'same duration'
                score = 0
                
            else:
                
                duration_multiple = max( s_duration_s, c_duration_s ) / min( s_duration_s, c_duration_s )
                
                score = max( 1, min( 50, int( ( duration_multiple - 1 ) * 50 ) ) )
                
                if s_duration_s > c_duration_s:
                    
                    operator = '>'
                    
                    sign = '+'
                    percentage_difference = ( s_duration_s / c_duration_s ) - 1.0
                    
                else:
                    
                    operator = '<'
                    score = -score
                    
                    sign = ''
                    percentage_difference = ( s_duration_s / c_duration_s ) - 1.0
                    
                
                statement = f'{HydrusTime.TimeDeltaToPrettyTimeDelta( s_duration_s )} {operator} {HydrusTime.TimeDeltaToPrettyTimeDelta( c_duration_s )} ({sign}{HydrusNumbers.FloatToPercentage(percentage_difference)})'
                
            
        elif s_has_duration:
            
            statement = f'this has duration ({HydrusTime.TimeDeltaToPrettyTimeDelta( s_duration_s )}), the other does not'
            score = 0
            
        else:
            
            statement = f'the other has duration ({HydrusTime.TimeDeltaToPrettyTimeDelta( c_duration_s )}), this does not'
            score = 0
            
        
        statements_and_scores[ 'duration' ] = ( statement, score )
        
    
    return ( statements_and_scores, they_are_pixel_duplicates )
    

def GetDuplicateComparisonStatementsSlow( shown_media_result: ClientMediaResult.MediaResult, comparison_media_result: ClientMediaResult.MediaResult, they_are_pixel_duplicates: bool ):
    
    new_options = CG.client_controller.new_options
    
    s_hash = shown_media_result.GetHash()
    c_hash = comparison_media_result.GetHash()
    
    duplicate_comparison_score_higher_jpeg_quality = new_options.GetInteger( 'duplicate_comparison_score_higher_jpeg_quality' )
    duplicate_comparison_score_much_higher_jpeg_quality = new_options.GetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality' )
    
    statements_and_scores = {}
    
    s_mime = shown_media_result.GetMime()
    c_mime = comparison_media_result.GetMime()
    
    # jpeg quality
    
    if s_mime == HC.IMAGE_JPEG and c_mime == HC.IMAGE_JPEG:
        
        jpeg_quality_storage = JpegQualityStorage.instance()
        
        for jpeg_hash in ( s_hash, c_hash ): 
            
            if not jpeg_quality_storage.HasData( jpeg_hash ):
                
                path = CG.client_controller.client_files_manager.GetFilePath( jpeg_hash, HC.IMAGE_JPEG )
                
                subsampling = HydrusImageMetadata.SUBSAMPLING_UNKNOWN
                quality_result = ( 'unknown', None )
                
                try:
                    
                    raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
                    
                    subsampling = HydrusImageMetadata.GetJpegSubsamplingRaw( raw_pil_image )
                    
                    quality_result = HydrusImageMetadata.GetJPEGQuantizationQualityEstimate( raw_pil_image )
                    
                except:
                    
                    pass
                
                
                ( quality_label, quality ) = quality_result
                
                jpeg_quality = JpegQuality( subsampling, quality_label, quality )
                
                jpeg_quality_storage.AddData( jpeg_hash, jpeg_quality )
                
            
        
        s_jpeg_quality = typing.cast( JpegQuality, jpeg_quality_storage.GetData( s_hash ) )
        c_jpeg_quality = typing.cast( JpegQuality, jpeg_quality_storage.GetData( c_hash ) )
        
        s_subsampling_quality = HydrusImageMetadata.subsampling_quality_lookup.get( s_jpeg_quality.subsampling, 0 )
        c_subsampling_quality = HydrusImageMetadata.subsampling_quality_lookup.get( c_jpeg_quality.subsampling, 0 )
        
        if s_subsampling_quality == c_subsampling_quality:
            
            score = 0
            statement = f'both {HydrusImageMetadata.subsampling_str_lookup[ s_jpeg_quality.subsampling ]}'
            
        else:
            
            if s_jpeg_quality.subsampling == HydrusImageMetadata.SUBSAMPLING_GREYSCALE or c_jpeg_quality.subsampling == HydrusImageMetadata.SUBSAMPLING_GREYSCALE:
                
                score = 0
                
            else:
                
                if s_subsampling_quality > c_subsampling_quality:
                    
                    score = 10
                    
                else:
                    
                    score = -10
                    
                
            
            statement = f'{HydrusImageMetadata.subsampling_str_lookup[ s_jpeg_quality.subsampling ]} vs {HydrusImageMetadata.subsampling_str_lookup[ c_jpeg_quality.subsampling ]}'
            
        
        statements_and_scores[ 'jpeg_subsampling' ] = ( statement, score )
        
        #
        
        score = 0
        
        if c_jpeg_quality.quality is None or s_jpeg_quality.quality is None or c_jpeg_quality.quality <= 0 or s_jpeg_quality.quality <= 0:
            
            score = 0
            
        else:
            
            if s_jpeg_quality.quality_label == c_jpeg_quality.quality_label:
                
                score = 0
                statement = f'both {s_jpeg_quality.quality_label} quality'
                
            else:
                
                # low score is good here
                quality_ratio = c_jpeg_quality.quality / s_jpeg_quality.quality
                
                if quality_ratio > 2.0:
                    
                    score = duplicate_comparison_score_much_higher_jpeg_quality
                    
                elif quality_ratio > 1.0:
                    
                    score = duplicate_comparison_score_higher_jpeg_quality
                    
                elif quality_ratio < 0.5:
                    
                    score = -duplicate_comparison_score_much_higher_jpeg_quality
                    
                else:
                    
                    score = -duplicate_comparison_score_higher_jpeg_quality
                    
                
                statement = '{} vs {} jpeg quality'.format( s_jpeg_quality.quality_label, c_jpeg_quality.quality_label )
                
            
            statements_and_scores[ 'jpeg_quality' ] = ( statement, score )
            
        
    
    # visual duplicates
    
    if not they_are_pixel_duplicates:
        
        if s_mime in HC.IMAGES and c_mime in HC.IMAGES:
            
            try:
                
                s_visual_data = GetVisualData( shown_media_result )
                c_visual_data = GetVisualData( comparison_media_result )
                
                ( simple_seems_good, simple_result, simple_score_statement ) = ClientVisualData.FilesAreVisuallySimilarSimple( s_visual_data, c_visual_data )
                
                if simple_seems_good:
                    
                    s_visual_data_tiled = GetVisualDataTiled( shown_media_result )
                    c_visual_data_tiled = GetVisualDataTiled( comparison_media_result )
                    
                    ( regional_seems_good, regional_result, regional_score_statement ) = ClientVisualData.FilesAreVisuallySimilarRegional( s_visual_data_tiled, c_visual_data_tiled )
                    
                    score = 0 if regional_seems_good else -5
                    
                    statements_and_scores[ 'a_and_b_are_visual_duplicates' ] = ( regional_score_statement, score )
                    
                else:
                    
                    statements_and_scores[ 'a_and_b_are_visual_duplicates' ] = ( simple_score_statement, -10 )
                    
                
            except HydrusExceptions.ShutdownException:
                
                pass
                
            except Exception as e:
                
                HydrusData.ShowException( e, do_wait = False )
                
                HydrusData.ShowText( 'The "A and B are visual duplicates" test threw an error! Please let hydev know the details.' )
                
            
        
    
    return statements_and_scores
    

def GetVisualData( media_result: ClientMediaResult.MediaResult ) -> ClientVisualData.VisualData:
    
    hash = media_result.GetHash()
    
    visual_data_cache = ClientVisualData.VisualDataStorage.instance()
    
    if not visual_data_cache.HasData( hash ):
        
        image_renderer = CG.client_controller.images_cache.GetImageRenderer( media_result )
        
        while not image_renderer.IsReady():
            
            if HydrusThreading.IsThreadShuttingDown():
                
                raise HydrusExceptions.ShutdownException( 'Seems like program is shutting down!' )
                
            
            time.sleep( 0.1 )
            
        
        numpy_image = image_renderer.GetNumPyImage()
        
        visual_data = ClientVisualData.GenerateImageVisualDataNumPy( numpy_image, hash )
        
        visual_data_cache.AddData( hash, visual_data )
        
    
    return typing.cast( ClientVisualData.VisualData, visual_data_cache.GetData( hash ) )
    

def GetVisualDataTiled( media_result: ClientMediaResult.MediaResult ) -> ClientVisualData.VisualDataTiled:
    
    hash = media_result.GetHash()
    
    visual_data_tiled_cache = ClientVisualData.VisualDataTiledStorage.instance()
    
    if not visual_data_tiled_cache.HasData( hash ):
        
        image_renderer = CG.client_controller.images_cache.GetImageRenderer( media_result )
        
        while not image_renderer.IsReady():
            
            if HydrusThreading.IsThreadShuttingDown():
                
                raise HydrusExceptions.ShutdownException( 'Seems like program is shutting down!' )
                
            
            time.sleep( 0.1 )
            
        
        numpy_image = image_renderer.GetNumPyImage()
        
        visual_data_tiled = ClientVisualData.GenerateImageVisualDataTiledNumPy( numpy_image, hash )
        
        visual_data_tiled_cache.AddData( hash, visual_data_tiled )
        
    
    return typing.cast( ClientVisualData.VisualDataTiled, visual_data_tiled_cache.GetData( hash ) )
    

class JpegQuality( ClientCachesBase.CacheableObject ):
    
    def __init__( self, subsampling, quality_label, quality ):
        
        self.subsampling = subsampling
        
        self.quality_label = quality_label
        self.quality = quality
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        return 64 # w/e
        
    

class JpegQualityStorage( ClientCachesBase.DataCache ):
    
    my_instance = None
    
    def __init__( self ):
        
        super().__init__( CG.client_controller, 'jpeg_quality', 1 * 1024 * 1024 )
        
    
    @staticmethod
    def instance() -> 'JpegQualityStorage':
        
        if JpegQualityStorage.my_instance is None:
            
            JpegQualityStorage.my_instance = JpegQualityStorage()
            
        
        return JpegQualityStorage.my_instance
        
    
