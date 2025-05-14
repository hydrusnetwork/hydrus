import collections
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client import ClientTime
from hydrus.client.files.images import ClientImageHistograms
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH = 0
DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH = 1
DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES = 2

SIMILAR_FILES_PIXEL_DUPES_REQUIRED = 0
SIMILAR_FILES_PIXEL_DUPES_ALLOWED = 1
SIMILAR_FILES_PIXEL_DUPES_EXCLUDED = 2

similar_files_pixel_dupes_string_lookup = {
    SIMILAR_FILES_PIXEL_DUPES_REQUIRED : 'must be pixel dupes',
    SIMILAR_FILES_PIXEL_DUPES_ALLOWED : 'can be pixel dupes',
    SIMILAR_FILES_PIXEL_DUPES_EXCLUDED : 'must not be pixel dupes'
}

SYNC_ARCHIVE_NONE = 0
SYNC_ARCHIVE_IF_ONE_DO_BOTH = 1
SYNC_ARCHIVE_DO_BOTH_REGARDLESS = 2

hashes_to_jpeg_quality = {}

def GetDuplicateComparisonScore( shown_media_result: ClientMediaResult.MediaResult, comparison_media_result: ClientMediaResult.MediaResult ):
    
    statements_and_scores = GetDuplicateComparisonStatements( shown_media_result, comparison_media_result )
    
    total_score = sum( ( score for ( statement, score ) in statements_and_scores.values() ) )
    
    return total_score
    

# TODO: All this will be replaced by tools being developed for the duplicates auto-resolution system
def GetDuplicateComparisonStatements( shown_media_result: ClientMediaResult.MediaResult, comparison_media_result: ClientMediaResult.MediaResult ):
    
    new_options = CG.client_controller.new_options
    
    duplicate_comparison_score_higher_jpeg_quality = new_options.GetInteger( 'duplicate_comparison_score_higher_jpeg_quality' )
    duplicate_comparison_score_much_higher_jpeg_quality = new_options.GetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality' )
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
    
    s_hash = shown_media_result.GetHash()
    c_hash = comparison_media_result.GetHash()
    
    s_mime = shown_media_result.GetMime()
    c_mime = comparison_media_result.GetMime()
    
    # size
    
    s_size = shown_media_result.GetSize()
    c_size = comparison_media_result.GetSize()
    
    is_a_pixel_dupe = False
    
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
            
            is_a_pixel_dupe = True
            
            if s_mime == HC.IMAGE_PNG and c_mime in other_file_is_pixel_png_appropriate_filetypes:
                
                statement = 'this is a pixel-for-pixel duplicate png! it is a waste of space!'
                
                score = -100
                
            elif s_mime in other_file_is_pixel_png_appropriate_filetypes and c_mime == HC.IMAGE_PNG:
                
                statement = 'other file is a pixel-for-pixel duplicate png!'
                
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
            
            if is_a_pixel_dupe:
                
                score = 0
                
            
            statement = '{} {} {}{}'.format( HydrusData.ToHumanBytes( s_size ), operator, HydrusData.ToHumanBytes( c_size ), percentage_different_string )
            
            statements_and_scores[ 'filesize' ]  = ( statement, score )
            
        
    
    # higher/same res
    
    s_resolution = shown_media_result.GetResolution()
    c_resolution = comparison_media_result.GetResolution()
    
    if s_resolution != c_resolution:
        
        ( s_w, s_h ) = s_resolution
        ( c_w, c_h ) = c_resolution
        
        all_measurements_are_good = None not in ( s_w, s_h, c_w, c_h ) and True not in ( d <= 0 for d in ( s_w, s_h, c_w, c_h ) )
        
        if all_measurements_are_good:
            
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
    
    if s_mime == c_mime:
        
        statement = 'both are {}s'.format( HC.mime_string_lookup[ s_mime ] )
        score = 0
        
        statements_and_scores[ 'mime' ] = ( statement, score )
        
    else:
        
        statement = '{} vs {}'.format( HC.mime_string_lookup[ s_mime ], HC.mime_string_lookup[ c_mime ] )
        score = 0
        
        statements_and_scores[ 'mime' ] = ( statement, score )
        
    
    # audio/no audio
    
    s_has_audio = shown_media_result.HasAudio()
    c_has_audio = comparison_media_result.HasAudio()
    
    if s_has_audio != c_has_audio:
        
        if s_has_audio:
            
            audio_statement = 'this has audio, the other does not'
            score = duplicate_comparison_score_has_audio
            
        else:
            
            audio_statement = 'the other has audio, this does not'
            score = - duplicate_comparison_score_has_audio
            
        
        statement = '{} vs {}'.format( s_has_audio, c_has_audio )

        statements_and_scores[ 'has_audio' ] = ( audio_statement, score )
    

    # more tags
    
    s_num_tags = len( shown_media_result.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
    c_num_tags = len( comparison_media_result.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
    
    if s_num_tags != c_num_tags:
        
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
    
    if s_import_timestamp is not None and c_import_timestamp is not None and abs( s_import_timestamp - c_import_timestamp ) > one_month:
        
        if s_import_timestamp < c_import_timestamp:
            
            operator = 'older than'
            score = duplicate_comparison_score_older
            
        else:
            
            operator = 'newer than'
            score = -duplicate_comparison_score_older
            
        
        if is_a_pixel_dupe:
            
            score = 0
            
        
        statement = '{}, {} {}'.format( HydrusTime.TimestampToPrettyTimeDelta( s_import_timestamp, history_suffix = ' old' ), operator, HydrusTime.TimestampToPrettyTimeDelta( c_import_timestamp, history_suffix = ' old' ) )
        
        statements_and_scores[ 'time_imported' ] = ( statement, score )
        
    
    if s_mime == HC.IMAGE_JPEG and c_mime == HC.IMAGE_JPEG:
        
        global hashes_to_jpeg_quality
        
        for jpeg_hash in ( s_hash, c_hash ): 
            
            if jpeg_hash not in hashes_to_jpeg_quality:
                
                path = CG.client_controller.client_files_manager.GetFilePath( jpeg_hash, HC.IMAGE_JPEG )
                
                try:
                    
                    raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
                    
                    result = HydrusImageMetadata.GetJPEGQuantizationQualityEstimate( raw_pil_image )
                    
                except:
                    
                    result = ( 'unknown', None )
                    
                
                hashes_to_jpeg_quality[ jpeg_hash ] = result
                
            
        
        ( s_label, s_jpeg_quality ) = hashes_to_jpeg_quality[ s_hash ]
        ( c_label, c_jpeg_quality ) = hashes_to_jpeg_quality[ c_hash ]
        
        score = 0
        
        if s_label != c_label:
            
            if c_jpeg_quality is None or s_jpeg_quality is None or c_jpeg_quality <= 0 or s_jpeg_quality <= 0:
                
                score = 0
                
            else:
                
                # other way around, low score is good here
                quality_ratio = c_jpeg_quality / s_jpeg_quality
                
                if quality_ratio > 2.0:
                    
                    score = duplicate_comparison_score_much_higher_jpeg_quality
                    
                elif quality_ratio > 1.0:
                    
                    score = duplicate_comparison_score_higher_jpeg_quality
                    
                elif quality_ratio < 0.5:
                    
                    score = -duplicate_comparison_score_much_higher_jpeg_quality
                    
                else:
                    
                    score = -duplicate_comparison_score_higher_jpeg_quality
                    
                
            
            statement = '{} vs {} jpeg quality'.format( s_label, c_label )
            
            statements_and_scores[ 'jpeg_quality' ] = ( statement, score )
            
        
    
    s_has_transparency = shown_media_result.GetFileInfoManager().has_transparency
    c_has_transparency = comparison_media_result.GetFileInfoManager().has_transparency
    
    if s_has_transparency ^ c_has_transparency:
        
        if s_has_transparency:
            
            transparency_statement = 'this has transparency, the other is opaque'
            
        else:
            
            transparency_statement = 'this is opaque, the other has transparency'
            
        
        statements_and_scores[ 'has_transparency' ] = ( transparency_statement, 0 )
        
    
    s_has_exif = shown_media_result.GetFileInfoManager().has_exif
    c_has_exif = comparison_media_result.GetFileInfoManager().has_exif
    
    if s_has_exif ^ c_has_exif:
        
        if s_has_exif:
            
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
    
    if s_has_icc ^ c_has_icc:
        
        if s_has_icc:
            
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
        
    
    # test for the new statement
    
    if not is_a_pixel_dupe and CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
        
        if s_mime in HC.IMAGES and c_mime in HC.IMAGES:
            
            try:
                
                def get_lab_histogram( media_result: ClientMediaResult.MediaResult ) -> ClientImageHistograms.LabHistogram:
                    
                    hash = media_result.GetHash()
                    
                    lab_histogram_cache = ClientImageHistograms.LabHistogramStorage.instance()
                    
                    if not lab_histogram_cache.HasData( hash ):
                        
                        image_renderer = CG.client_controller.images_cache.GetImageRenderer( media_result )
                        
                        while not image_renderer.IsReady():
                            
                            if HydrusThreading.IsThreadShuttingDown():
                                
                                raise HydrusExceptions.ShutdownException( 'Seems like program is shutting down!' )
                                
                            
                            time.sleep( 0.1 )
                            
                        
                        numpy_image = image_renderer.GetNumPyImage()
                        
                        lab_histogram = ClientImageHistograms.GenerateImageLabHistogramsNumPy( numpy_image )
                        
                        lab_histogram_cache.AddData( hash, lab_histogram )
                        
                    
                    return typing.cast( ClientImageHistograms.LabHistogram, lab_histogram_cache.GetData( hash ) )
                    
                
                def get_lab_tiles_histogram( media_result: ClientMediaResult.MediaResult ) -> ClientImageHistograms.LabTilesHistogram:
                    
                    hash = media_result.GetHash()
                    
                    lab_tiles_histogram_cache = ClientImageHistograms.LabTilesHistogramStorage.instance()
                    
                    if not lab_tiles_histogram_cache.HasData( hash ):
                        
                        image_renderer = CG.client_controller.images_cache.GetImageRenderer( media_result )
                        
                        while not image_renderer.IsReady():
                            
                            if HydrusThreading.IsThreadShuttingDown():
                                
                                raise HydrusExceptions.ShutdownException( 'Seems like program is shutting down!' )
                                
                            
                            time.sleep( 0.1 )
                            
                        
                        numpy_image = image_renderer.GetNumPyImage()
                        
                        lab_tiles_histogram = ClientImageHistograms.GenerateImageLabTilesHistogramsNumPy( numpy_image )
                        
                        lab_tiles_histogram_cache.AddData( hash, lab_tiles_histogram )
                        
                    
                    return typing.cast( ClientImageHistograms.LabTilesHistogram, lab_tiles_histogram_cache.GetData( hash ) )
                    
                
                s_lab_histogram = get_lab_histogram( shown_media_result )
                c_lab_histogram = get_lab_histogram( comparison_media_result )
                
                ( simple_seems_good, simple_score_statement ) = ClientImageHistograms.FilesAreVisuallySimilarSimple( s_lab_histogram, c_lab_histogram )
                
                if simple_seems_good:
                    
                    s_lab_tiles_histogram = get_lab_tiles_histogram( shown_media_result )
                    c_lab_tiles_histogram = get_lab_tiles_histogram( comparison_media_result )
                    
                    ( regional_seems_good, regional_score_statement ) = ClientImageHistograms.FilesAreVisuallySimilarRegional( s_lab_tiles_histogram, c_lab_tiles_histogram )
                    
                    statements_and_scores[ 'a_is_exact_match_b_advanced_test' ] = ( regional_score_statement, 0 )
                    
                else:
                    
                    statements_and_scores[ 'a_is_exact_match_b_advanced_test' ] = ( simple_score_statement, 0 )
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e, do_wait = False )
                
                HydrusData.ShowText( 'The "A is exact match of B" detector threw an error! Please let hydev know the details.' )
                
            
        
    
    return statements_and_scores
    

class DuplicatesManager( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        DuplicatesManager.my_instance = self
        
        self._similar_files_maintenance_status = None
        self._currently_refreshing_maintenance_numbers = False
        self._refresh_maintenance_numbers = True
        
        self._currently_doing_potentials_search = False
        
        self._lock = threading.Lock()
        
    
    @staticmethod
    def instance() -> 'DuplicatesManager':
        
        if DuplicatesManager.my_instance is None:
            
            DuplicatesManager()
            
        
        return DuplicatesManager.my_instance
        
    
    def GetMaintenanceNumbers( self ):
        
        with self._lock:
            
            if self._refresh_maintenance_numbers and not self._currently_refreshing_maintenance_numbers:
                
                self._refresh_maintenance_numbers = False
                self._currently_refreshing_maintenance_numbers = True
                
                CG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
                
                CG.client_controller.CallToThread( self.THREADRefreshMaintenanceNumbers )
                
            
            return ( self._similar_files_maintenance_status, self._currently_refreshing_maintenance_numbers, self._currently_doing_potentials_search )
            
        
    
    def RefreshMaintenanceNumbers( self ):
        
        with self._lock:
            
            self._refresh_maintenance_numbers = True
            
            CG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
            
        
    
    def NotifyNewPotentialsSearchNumbers( self ):
        
        CG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
        
    
    def StartPotentialsSearch( self ):
        
        with self._lock:
            
            if self._currently_doing_potentials_search or self._similar_files_maintenance_status is None:
                
                return
                
            
            self._currently_doing_potentials_search = True
            
            CG.client_controller.CallToThreadLongRunning( self.THREADSearchPotentials )
            
        
    
    def THREADRefreshMaintenanceNumbers( self ):
        
        try:
            
            similar_files_maintenance_status = CG.client_controller.Read( 'similar_files_maintenance_status' )
            
            with self._lock:
                
                self._similar_files_maintenance_status = similar_files_maintenance_status
                
                if self._refresh_maintenance_numbers:
                    
                    self._refresh_maintenance_numbers = False
                    
                    CG.client_controller.CallToThread( self.THREADRefreshMaintenanceNumbers )
                    
                else:
                    
                    self._currently_refreshing_maintenance_numbers = False
                    self._refresh_maintenance_numbers = False
                    
                
                CG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
                
            
        except:
            
            self._currently_refreshing_maintenance_numbers = False
            CG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
            
            raise
            
        
    
    def THREADSearchPotentials( self ):
        
        try:
            
            search_distance = CG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
            
            with self._lock:
                
                if self._similar_files_maintenance_status is None:
                    
                    return
                    
                
                searched_distances_to_count = self._similar_files_maintenance_status
                
                total_num_files = sum( searched_distances_to_count.values() )
                
                num_searched = sum( ( count for ( value, count ) in searched_distances_to_count.items() if value is not None and value >= search_distance ) )
                
                all_files_searched = num_searched >= total_num_files
                
                if all_files_searched:
                    
                    return # no work to do
                    
                
            
            num_searched_estimate = num_searched
            
            CG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            job_status.SetStatusTitle( 'searching for potential duplicates' )
            
            CG.client_controller.pub( 'message', job_status )
            
            still_work_to_do = True
            
            while still_work_to_do:
                
                search_distance = CG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
                
                start_time = HydrusTime.GetNowPrecise()
                
                work_time_ms = CG.client_controller.new_options.GetInteger( 'potential_duplicates_search_work_time_ms' )
                
                work_time = HydrusTime.SecondiseMSFloat( work_time_ms )
                
                ( still_work_to_do, num_done ) = CG.client_controller.WriteSynchronous( 'maintain_similar_files_search_for_potential_duplicates', search_distance, maintenance_mode = HC.MAINTENANCE_FORCED, job_status = job_status, work_time_float = work_time )
                
                time_it_took = HydrusTime.GetNowPrecise() - start_time
                
                num_searched_estimate += num_done
                
                if num_searched_estimate > total_num_files:
                    
                    similar_files_maintenance_status = CG.client_controller.Read( 'similar_files_maintenance_status' )
                    
                    if similar_files_maintenance_status is None:
                        
                        break
                        
                    
                    with self._lock:
                        
                        self._similar_files_maintenance_status = similar_files_maintenance_status
                        
                        searched_distances_to_count = self._similar_files_maintenance_status
                        
                        total_num_files = max( num_searched_estimate, sum( searched_distances_to_count.values() ) )
                        
                    
                
                text = 'searching: {}'.format( HydrusNumbers.ValueRangeToPrettyString( num_searched_estimate, total_num_files ) )
                job_status.SetStatusText( text )
                job_status.SetVariable( 'popup_gauge_1', ( num_searched_estimate, total_num_files ) )
                
                if job_status.IsCancelled() or HG.model_shutdown:
                    
                    break
                    
                
                rest_ratio = CG.client_controller.new_options.GetInteger( 'potential_duplicates_search_rest_percentage' ) / 100
                
                reasonable_work_time = min( 5 * work_time, time_it_took )
                
                time.sleep( reasonable_work_time * rest_ratio )
                
            
            job_status.FinishAndDismiss()
            
        finally:
            
            with self._lock:
                
                self._currently_doing_potentials_search = False
                
            
            self.RefreshMaintenanceNumbers()
            self.NotifyNewPotentialsSearchNumbers()
            
        
    

def get_updated_domain_modified_timestamp_datas( destination_media_result: ClientMediaResult.MediaResult, source_media_result: ClientMediaResult.MediaResult, urls: typing.Collection[ str ] ):
    
    from hydrus.client.networking import ClientNetworkingFunctions
    
    domains = set()
    
    for url in urls:
        
        try:
            
            domain = ClientNetworkingFunctions.ConvertURLIntoDomain( url )
            
            domains.add( domain )
            
        except:
            
            continue # not an url in the strict sense, let's skip since this method really wants to be dealing with nice URLs
            
        
    
    timestamp_datas = []
    source_timestamp_manager = source_media_result.GetTimesManager()
    destination_timestamp_manager = destination_media_result.GetTimesManager()
    
    for domain in domains:
        
        source_timestamp_ms = source_timestamp_manager.GetDomainModifiedTimestampMS( domain )
        
        if source_timestamp_ms is not None:
            
            timestamp_data = ClientTime.TimestampData.STATICDomainModifiedTime( domain, source_timestamp_ms )
            
            destination_timestamp_ms = destination_timestamp_manager.GetDomainModifiedTimestampMS( domain )
            
            if destination_timestamp_ms is None or ClientTime.ShouldUpdateModifiedTime( destination_timestamp_ms, source_timestamp_ms ):
                
                timestamp_datas.append( timestamp_data )
                
            
        
    
    return timestamp_datas
    

def get_domain_modified_content_updates( destination_media_result: ClientMediaResult.MediaResult, source_media_result: ClientMediaResult.MediaResult, urls: typing.Collection[ str ] ):
    
    timestamp_datas = get_updated_domain_modified_timestamp_datas( destination_media_result, source_media_result, urls )
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( destination_media_result.GetHash(), ), timestamp_data ) ) for timestamp_data in timestamp_datas ]
    
    return content_updates
    

class DuplicateContentMergeOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_CONTENT_MERGE_OPTIONS
    SERIALISABLE_NAME = 'Duplicate Metadata Merge Options'
    SERIALISABLE_VERSION = 7
    
    def __init__( self ):
        
        super().__init__()
        
        # it is important that the default init of this guy syncs absolutely nothing!
        # we use empty dupe merge option guys to do some other processing, so empty must mean empty
        
        self._tag_service_actions = []
        self._rating_service_actions = []
        self._sync_notes_action = HC.CONTENT_MERGE_ACTION_NONE
        self._sync_note_import_options = NoteImportOptions.NoteImportOptions()
        self._sync_archive_action = SYNC_ARCHIVE_NONE
        self._sync_urls_action = HC.CONTENT_MERGE_ACTION_NONE
        self._sync_file_modified_date_action = HC.CONTENT_MERGE_ACTION_NONE
        
    
    def _GetSerialisableInfo( self ):
        
        if CG.client_controller.IsBooted():
            
            services_manager = CG.client_controller.services_manager
            
            self._tag_service_actions = [ ( service_key, action, tag_filter ) for ( service_key, action, tag_filter ) in self._tag_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in HC.REAL_TAG_SERVICES ]
            self._rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._rating_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in HC.RATINGS_SERVICES ]
            
        
        serialisable_tag_service_actions = [ ( service_key.hex(), action, tag_filter.GetSerialisableTuple() ) for ( service_key, action, tag_filter ) in self._tag_service_actions ]
        serialisable_rating_service_actions = [ ( service_key.hex(), action ) for ( service_key, action ) in self._rating_service_actions ]
        
        serialisable_sync_note_import_options = self._sync_note_import_options.GetSerialisableTuple()
        
        return (
            serialisable_tag_service_actions,
            serialisable_rating_service_actions,
            self._sync_notes_action,
            serialisable_sync_note_import_options,
            self._sync_archive_action,
            self._sync_urls_action,
            self._sync_file_modified_date_action
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_tag_service_actions,
            serialisable_rating_service_actions,
            self._sync_notes_action,
            serialisable_sync_note_import_options,
            self._sync_archive_action,
            self._sync_urls_action,
            self._sync_file_modified_date_action
        ) = serialisable_info
        
        self._tag_service_actions = [ ( bytes.fromhex( serialisable_service_key ), action, HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filter ) ) for ( serialisable_service_key, action, serialisable_tag_filter ) in serialisable_tag_service_actions ]
        self._rating_service_actions = [ ( bytes.fromhex( serialisable_service_key ), action ) for ( serialisable_service_key, action ) in serialisable_rating_service_actions ]
        self._sync_note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_sync_note_import_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_service_actions, delete_second_file ) = old_serialisable_info
            
            tag_service_actions = []
            rating_service_actions = []
            
            # As the client isn't booted when this is loaded in options, there isn't a good way to figure out tag from rating
            # So, let's just dupe and purge later on, in serialisation
            for ( service_key_encoded, action ) in serialisable_service_actions:
                
                service_key = bytes.fromhex( service_key_encoded )
                
                tag_filter = HydrusTags.TagFilter()
                
                tag_service_actions.append( ( service_key, action, tag_filter ) )
                
                rating_service_actions.append( ( service_key, action ) )
                
            
            serialisable_tag_service_actions = [ ( service_key.hex(), action, tag_filter.GetSerialisableTuple() ) for ( service_key, action, tag_filter ) in tag_service_actions ]
            serialisable_rating_service_actions = [ ( service_key.hex(), action ) for ( service_key, action ) in rating_service_actions ]
            
            sync_archive = delete_second_file
            delete_both_files = False
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files ) = old_serialisable_info
            
            sync_urls_action = None
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files, sync_urls_action )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files, sync_urls_action ) = old_serialisable_info
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_archive, sync_urls_action )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_archive, sync_urls_action ) = old_serialisable_info
            
            if sync_archive:
                
                sync_archive_action = SYNC_ARCHIVE_IF_ONE_DO_BOTH
                
            else:
                
                sync_archive_action = SYNC_ARCHIVE_NONE
                
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_archive_action, sync_urls_action )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_archive_action, sync_urls_action ) = old_serialisable_info
            
            if sync_urls_action is None:
                
                sync_urls_action = HC.CONTENT_MERGE_ACTION_NONE
                
            
            sync_notes_action = HC.CONTENT_MERGE_ACTION_NONE
            sync_note_import_options = NoteImportOptions.NoteImportOptions()
            
            serialisable_sync_note_import_options = sync_note_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_notes_action, serialisable_sync_note_import_options, sync_archive_action, sync_urls_action )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            (
                serialisable_tag_service_actions,
                serialisable_rating_service_actions,
                sync_notes_action,
                serialisable_sync_note_import_options,
                sync_archive_action,
                sync_urls_action
            ) = old_serialisable_info
            
            sync_file_modified_date_action = HC.CONTENT_MERGE_ACTION_NONE
            
            new_serialisable_info = (
                serialisable_tag_service_actions,
                serialisable_rating_service_actions,
                sync_notes_action,
                serialisable_sync_note_import_options,
                sync_archive_action,
                sync_urls_action,
                sync_file_modified_date_action
            )
            
            return ( 7, new_serialisable_info )
            
        
    
    def GetMergeSummaryOnPair( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult, delete_a: bool, delete_b: bool, in_auto_resolution = False ):
        
        # do file delete; this guy only cares about the content merge
        content_update_packages = self.ProcessPairIntoContentUpdatePackages( media_result_a, media_result_b, delete_a = delete_a, delete_b = delete_b, in_auto_resolution = in_auto_resolution )
        
        hash_a = media_result_a.GetHash()
        hash_b = media_result_b.GetHash()
        
        a_work = collections.defaultdict( list )
        b_work = collections.defaultdict( list )
        
        for content_update_package in content_update_packages:
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                for content_update in content_updates:
                    
                    hashes = content_update.GetHashes()
                    
                    s = content_update.ToActionSummary()
                    
                    if hash_a in hashes:
                        
                        a_work[ service_key ].append( s )
                        
                    
                    if hash_b in hashes:
                        
                        b_work[ service_key ].append( s )
                        
                    
                
            
        
        work_strings = []
        
        for ( hash_name, work ) in [
            ( 'A', a_work ),
            ( 'B', b_work )
        ]:
            
            work_flat = sorted( [ ( CG.client_controller.services_manager.GetName( service_key ), sorted( summary_strings ) ) for ( service_key, summary_strings ) in work.items() ] )
            
            gubbins = '|'.join( [ name + ': ' + ', '.join( summary_strings ) for ( name, summary_strings ) in work_flat ] )
            
            if len( gubbins ) == 0:
                
                work_string = hash_name + ': no changes'
                
            else:
                
                work_string = hash_name + ': ' + gubbins
                
            
            work_strings.append( work_string )
            
        
        if len( work_strings ) > 0:
            
            return '\n'.join( work_strings )
            
        else:
            
            return 'no content updates'
            
        
    
    def GetRatingServiceActions( self ) -> typing.Collection[ tuple ]:
        
        return self._rating_service_actions
        
    
    def GetTagServiceActions( self ) -> typing.Collection[ tuple ]:
        
        return self._tag_service_actions
        
    
    def GetSyncArchiveAction( self ) -> int:
        
        return self._sync_archive_action
        
    
    def GetSyncFileModifiedDateAction( self ) -> int:
        
        return self._sync_file_modified_date_action
        
    
    def GetSyncNotesAction( self ) -> int:
        
        return self._sync_notes_action
        
    
    def GetSyncNoteImportOptions( self ) -> NoteImportOptions.NoteImportOptions:
        
        return self._sync_note_import_options
        
    
    def GetSyncURLsAction( self ) -> int:
        
        return self._sync_urls_action
        
    
    def SetRatingServiceActions( self, rating_service_actions: typing.Collection[ tuple ] ):
        
        self._rating_service_actions = rating_service_actions
        
    
    def SetTagServiceActions( self, tag_service_actions: typing.Collection[ tuple ] ):
        
        self._tag_service_actions = tag_service_actions
        
    
    def SetSyncArchiveAction( self, sync_archive_action: int ):
        
        self._sync_archive_action = sync_archive_action
        
    
    def SetSyncFileModifiedDateAction( self, sync_file_modified_date_action: int ):
        
        self._sync_file_modified_date_action = sync_file_modified_date_action
        
    
    def SetSyncNotesAction( self, sync_notes_action: int ):
        
        self._sync_notes_action = sync_notes_action
        
    
    def SetSyncNoteImportOptions( self, sync_note_import_options: NoteImportOptions.NoteImportOptions ):
        
        self._sync_note_import_options = sync_note_import_options
        
    
    def SetSyncURLsAction( self, sync_urls_action: int ):
        
        self._sync_urls_action = sync_urls_action
        
    
    def ProcessPairIntoContentUpdatePackages(
        self,
        media_result_a: ClientMediaResult.MediaResult,
        media_result_b: ClientMediaResult.MediaResult,
        delete_a = False,
        delete_b = False,
        file_deletion_reason = None,
        do_not_do_deletes = False,
        in_auto_resolution = False
    ) -> typing.List[ ClientContentUpdates.ContentUpdatePackage ]:
        
        # small note here, if we have BETTER/WORSE distinctions in any of the settings, A is better, B is worse. if we have HC.DUPLICATE_WORSE anywhere, which sets B as better, it must be flipped beforehand to BETTER and BA -> AB
        # TODO: since this is a crazy situation, maybe this guy should just take the duplicate action, and then it can convert to media_result_better as needed
        
        if file_deletion_reason is None:
            
            file_deletion_reason = 'unknown reason'
            
        
        content_update_packages = []
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        hash_a = media_result_a.GetHash()
        hash_b = media_result_b.GetHash()
        hash_a_set = { hash_a }
        hash_b_set = { hash_b }
        
        #
        
        services_manager = CG.client_controller.services_manager
        
        for ( service_key, action, tag_filter ) in self._tag_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service_type = service.GetServiceType()
            
            if service_type == HC.LOCAL_TAG:
                
                add_content_action = HC.CONTENT_UPDATE_ADD
                
            elif service_type == HC.TAG_REPOSITORY:
                
                add_content_action = HC.CONTENT_UPDATE_PEND
                
            else:
                
                continue
                
            
            first_tags = media_result_a.GetTagsManager().GetCurrentAndPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            second_tags = media_result_b.GetTagsManager().GetCurrentAndPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            
            first_tags = tag_filter.Filter( first_tags )
            second_tags = tag_filter.Filter( second_tags )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_tags.difference( first_tags )
                second_needs = first_tags.difference( second_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hash_a_set ) ) for tag in first_needs ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hash_b_set ) ) for tag in second_needs ) )
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_tags.difference( first_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hash_a_set ) ) for tag in first_needs ) )
                
            elif service_type == HC.LOCAL_TAG and action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_needs = second_tags.difference( first_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hash_a_set ) ) for tag in first_needs ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, hash_b_set ) ) for tag in second_tags ) )
                
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        def worth_updating_rating( source_rating, dest_rating ):
            
            if source_rating is not None:
                
                if dest_rating is None or source_rating > dest_rating:
                    
                    return True
                    
                
            
            return False
            
        
        for ( service_key, action ) in self._rating_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            first_current_value = media_result_a.GetRatingsManager().GetRating( service_key )
            second_current_value = media_result_b.GetRatingsManager().GetRating( service_key )
            
            service_type = service.GetServiceType()
            
            if service_type in HC.STAR_RATINGS_SERVICES:
                
                if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                    
                    if worth_updating_rating( first_current_value, second_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( first_current_value, hash_b_set ) ) )
                        
                    elif worth_updating_rating( second_current_value, first_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, hash_a_set ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_COPY:
                    
                    if worth_updating_rating( second_current_value, first_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, hash_a_set ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                    
                    if second_current_value is not None:
                        
                        if worth_updating_rating( second_current_value, first_current_value ):
                            
                            content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, hash_a_set ) ) )
                            
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, hash_b_set ) ) )
                        
                    
                
            elif service_type == HC.LOCAL_RATING_INCDEC:
                
                sum_value = first_current_value + second_current_value
                
                if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, hash_a_set ) ) )
                        
                    
                    if first_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, hash_b_set ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_COPY:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, hash_a_set ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, hash_a_set ) ) )
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0, hash_b_set ) ) )
                        
                    
                
            else:
                
                continue
                
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        #
        
        if self._sync_notes_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_names_and_notes = list( media_result_a.GetNotesManager().GetNamesToNotes().items() )
            second_names_and_notes = list( media_result_b.GetNotesManager().GetNamesToNotes().items() )
            
            # TODO: rework this to UpdateeNamesToNotes
            
            if self._sync_notes_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( media_result_a, second_names_and_notes )
                second_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( media_result_b, first_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                content_update_package.AddContentUpdatePackage( second_content_update_package )
                
            elif self._sync_notes_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( media_result_a, second_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                
            elif self._sync_notes_action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( media_result_a, second_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                
                content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash_b, name ) ) for ( name, note ) in second_names_and_notes ]
                
                content_update_package.AddContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, content_updates )
                
            
        
        #
        
        content_update_archive_first = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hash_a_set )
        content_update_archive_second = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hash_b_set )
        
        # the "and not delete_a" gubbins here is to help out the delete lock lmao. don't want to archive and then try to delete
        
        action_to_actually_consult = self._sync_archive_action
        
        # don't archive both files if the user hasn't seen them in the duplicate filter bruh
        if in_auto_resolution and action_to_actually_consult == SYNC_ARCHIVE_DO_BOTH_REGARDLESS:
            
            action_to_actually_consult = SYNC_ARCHIVE_IF_ONE_DO_BOTH
            
        
        first_locations_manager = media_result_a.GetLocationsManager()
        second_locations_manager = media_result_b.GetLocationsManager()
        
        if action_to_actually_consult == SYNC_ARCHIVE_IF_ONE_DO_BOTH:
            
            if first_locations_manager.inbox and not second_locations_manager.inbox and not delete_a:
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update_archive_first )
                
            elif not first_locations_manager.inbox and second_locations_manager.inbox and not delete_b:
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update_archive_second )
                
            
        elif action_to_actually_consult == SYNC_ARCHIVE_DO_BOTH_REGARDLESS:
            
            if first_locations_manager.inbox and not delete_a:
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update_archive_first )
                
            
            if second_locations_manager.inbox and not delete_b:
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update_archive_second )
                
            
        
        #
        
        if self._sync_file_modified_date_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_timestamp_ms = media_result_a.GetTimesManager().GetFileModifiedTimestampMS()
            second_timestamp_ms = media_result_b.GetTimesManager().GetFileModifiedTimestampMS()
            
            if self._sync_file_modified_date_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                if ClientTime.ShouldUpdateModifiedTime( first_timestamp_ms, second_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( hash_a, ), ClientTime.TimestampData.STATICFileModifiedTime( second_timestamp_ms ) ) ) )
                    
                elif ClientTime.ShouldUpdateModifiedTime( second_timestamp_ms, first_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( hash_b, ), ClientTime.TimestampData.STATICFileModifiedTime( first_timestamp_ms ) ) ) )
                    
                
            elif self._sync_file_modified_date_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                if ClientTime.ShouldUpdateModifiedTime( first_timestamp_ms, second_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( hash_a, ), ClientTime.TimestampData.STATICFileModifiedTime( second_timestamp_ms ) ) ) )
                    
                
            
        
        #
        
        if self._sync_urls_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_urls = set( media_result_a.GetLocationsManager().GetURLs() )
            second_urls = set( media_result_b.GetLocationsManager().GetURLs() )
            
            if self._sync_urls_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_urls.difference( first_urls )
                second_needs = first_urls.difference( second_urls )
                
                if len( first_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, hash_a_set ) ) )
                    
                    content_update_package.AddContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, get_domain_modified_content_updates( media_result_a, media_result_b, first_needs ) )
                    
                
                if len( second_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( second_needs, hash_b_set ) ) )
                    
                    content_update_package.AddContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, get_domain_modified_content_updates( media_result_b, media_result_a, second_needs ) )
                    
                
            elif self._sync_urls_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_urls.difference( first_urls )
                
                if len( first_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, hash_a_set ) ) )
                    
                    content_update_package.AddContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, get_domain_modified_content_updates( media_result_a, media_result_b, first_needs ) )
                    
                
            
        
        #
        
        if content_update_package.HasContent():
            
            content_update_packages.append( content_update_package )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage()
            
        
        #
        
        deletee_media_results = []
        
        if delete_a:
            
            deletee_media_results.append( media_result_a )
            
        
        if delete_b:
            
            deletee_media_results.append( media_result_b )
            
        
        for media_result in deletee_media_results:
            
            if do_not_do_deletes:
                
                continue
                
            
            if CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY in media_result.GetLocationsManager().GetCurrent():
                
                if not in_auto_resolution and CG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' ) and CG.client_controller.new_options.GetBoolean( 'delete_lock_reinbox_deletees_after_duplicate_filter' ):
                    
                    if not media_result.GetLocationsManager().inbox:
                        
                        content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, { media_result.GetHash() } ) )
                        
                        content_update_packages.append( content_update_package )
                        
                        content_update_package = ClientContentUpdates.ContentUpdatePackage()
                        
                    
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { media_result.GetHash() }, reason = file_deletion_reason )
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY, content_update )
                
            
        
        #
        
        if content_update_package.HasContent():
            
            content_update_packages.append( content_update_package )
            
        
        return content_update_packages
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_CONTENT_MERGE_OPTIONS ] = DuplicateContentMergeOptions
