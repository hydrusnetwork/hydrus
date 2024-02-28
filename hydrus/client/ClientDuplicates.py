import collections
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client import ClientTime
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaFileFilter
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

hashes_to_jpeg_quality = {}

def GetDuplicateComparisonScore( shown_media, comparison_media ):
    
    statements_and_scores = GetDuplicateComparisonStatements( shown_media, comparison_media )
    
    total_score = sum( ( score for ( statement, score ) in statements_and_scores.values() ) )
    
    return total_score
    

# TODO: ok, let's make an enum here at some point and a DuplicateComparisonSetting serialisable object
# Then we can attach 'show/hide' boolean and allow editable scores and whatnot in a nice class that will one day evolve the enum to an editable MetadataConditional/MetadataComparison object
# also have banding so we can have 'at this filesize difference, score 10, at this, score 15'
# show it in a listctrl or whatever in the options, ditch the hardcoding
# metadatacomparison needs to handle 'if one is a png and one is a jpeg', and then orient to A/B and give it a score

def GetDuplicateComparisonStatements( shown_media, comparison_media ):
    
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
    
    s_hash = shown_media.GetHash()
    c_hash = comparison_media.GetHash()
    
    s_mime = shown_media.GetMime()
    c_mime = comparison_media.GetMime()
    
    # size
    
    s_size = shown_media.GetSize()
    c_size = comparison_media.GetSize()
    
    is_a_pixel_dupe = False
    
    if s_mime in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH and c_mime in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH and shown_media.GetResolution() == comparison_media.GetResolution():
        
        s_pixel_hash = shown_media.GetFileInfoManager().pixel_hash
        c_pixel_hash = comparison_media.GetFileInfoManager().pixel_hash
        
        if s_pixel_hash is None or c_pixel_hash is None:
            
            statement = 'could not determine if files were pixel-for-pixel duplicates!'
            score = 0
            
            statements_and_scores[ 'pixel_duplicates' ] = ( statement, score )
            
        elif s_pixel_hash == c_pixel_hash:
            
            # this is not appropriate for, say, PSD files
            other_file_is_pixel_png_appropriate_filetypes = {
                HC.IMAGE_JPEG,
                HC.IMAGE_WEBP
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
                
            
            percentage_different_string = ' ({}{})'.format( sign, HydrusData.ConvertFloatToPercentage( percentage_difference ) )
            
            if is_a_pixel_dupe:
                
                score = 0
                
            
            statement = '{} {} {}{}'.format( HydrusData.ToHumanBytes( s_size ), operator, HydrusData.ToHumanBytes( c_size ), percentage_different_string )
            
            statements_and_scores[ 'filesize' ]  = ( statement, score )
            
        
    
    # higher/same res
    
    s_resolution = shown_media.GetResolution()
    c_resolution = comparison_media.GetResolution()
    
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
                
            
            if s_resolution in HC.NICE_RESOLUTIONS:
                
                s_string = HC.NICE_RESOLUTIONS[ s_resolution ]
                
            else:
                
                s_string = HydrusData.ConvertResolutionToPrettyString( s_resolution )
                
                if s_w % 2 == 1 or s_h % 2 == 1:
                    
                    s_string += ' (unusual)'
                    
                
            
            if c_resolution in HC.NICE_RESOLUTIONS:
                
                c_string = HC.NICE_RESOLUTIONS[ c_resolution ]
                
            else:
                
                c_string = HydrusData.ConvertResolutionToPrettyString( c_resolution )
                
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
    
    s_has_audio = shown_media.GetMediaResult().HasAudio()
    c_has_audio = comparison_media.GetMediaResult().HasAudio()
    
    if s_has_audio != c_has_audio:
        
        if s_has_audio:

            audio_statement = 'this has audio, the other does not'
            score = duplicate_comparison_score_has_audio

        else:
            
            audio_statement = 'the other has audio, this does not'
            score = 0
        
        statement = '{} vs {}'.format( s_has_audio, c_has_audio )

        statements_and_scores[ 'has_audio' ] = ( audio_statement, score )
    

    # more tags
    
    s_num_tags = len( shown_media.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
    c_num_tags = len( comparison_media.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
    
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
            
        
        statement = '{} tags {} {} tags'.format( HydrusData.ToHumanInt( s_num_tags ), operator, HydrusData.ToHumanInt( c_num_tags ) )
        
        statements_and_scores[ 'num_tags' ] = ( statement, score )
        
    
    # older
    
    s_import_timestamp = HydrusTime.SecondiseMS( shown_media.GetLocationsManager().GetTimesManager().GetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
    c_import_timestamp = HydrusTime.SecondiseMS( comparison_media.GetLocationsManager().GetTimesManager().GetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
    
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
            
        
        statement = '{}, {} {}'.format( ClientTime.TimestampToPrettyTimeDelta( s_import_timestamp, history_suffix = ' old' ), operator, ClientTime.TimestampToPrettyTimeDelta( c_import_timestamp, history_suffix = ' old' ) )
        
        statements_and_scores[ 'time_imported' ] = ( statement, score )
        
    
    if s_mime == HC.IMAGE_JPEG and c_mime == HC.IMAGE_JPEG:
        
        global hashes_to_jpeg_quality
        
        if s_hash not in hashes_to_jpeg_quality:
            
            path = CG.client_controller.client_files_manager.GetFilePath( s_hash, s_mime )
            
            try:
                
                raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
                
                result = HydrusImageMetadata.GetJPEGQuantizationQualityEstimate( raw_pil_image )
                
            except:
                
                result = ( 'unknown', None )
                
            
            hashes_to_jpeg_quality[ s_hash ] = result
            
        
        if c_hash not in hashes_to_jpeg_quality:
            
            path = CG.client_controller.client_files_manager.GetFilePath( c_hash, c_mime )
            
            try:
                
                raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
                
                result = HydrusImageMetadata.GetJPEGQuantizationQualityEstimate( raw_pil_image )
                
            except:
                
                result = ( 'unknown', None )
                
            
            hashes_to_jpeg_quality[ c_hash ] = result
            
        
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
            
        
    
    s_has_transparency = shown_media.GetFileInfoManager().has_transparency
    c_has_transparency = comparison_media.GetFileInfoManager().has_transparency
    
    if s_has_transparency ^ c_has_transparency:
        
        if s_has_transparency:
            
            transparency_statement = 'this has transparency, the other is opaque'
            
        else:
            
            transparency_statement = 'this is opaque, the other has transparency'
            
        
        statements_and_scores[ 'has_transparency' ] = ( transparency_statement, 0 )
        
    
    s_has_exif = shown_media.GetFileInfoManager().has_exif
    c_has_exif = comparison_media.GetFileInfoManager().has_exif
    
    if s_has_exif ^ c_has_exif:
        
        if s_has_exif:
            
            exif_statement = 'this has exif data, the other does not'
            
        else:
            
            exif_statement = 'the other has exif data, this does not'
            
        
        statements_and_scores[ 'exif_data' ] = ( exif_statement, 0 )
        
    
    s_has_human_readable_embedded_metadata = shown_media.GetFileInfoManager().has_human_readable_embedded_metadata
    c_has_human_readable_embedded_metadata = comparison_media.GetFileInfoManager().has_human_readable_embedded_metadata
    
    if s_has_human_readable_embedded_metadata ^ c_has_human_readable_embedded_metadata:
        
        if s_has_human_readable_embedded_metadata:
            
            embedded_metadata_statement = 'this has embedded metadata, the other does not'
            
        else:
            
            embedded_metadata_statement = 'the other has embedded metadata, this does not'
            
        
        statements_and_scores[ 'embedded_metadata' ] = ( embedded_metadata_statement, 0 )
        
    
    s_has_icc = shown_media.GetMediaResult().GetFileInfoManager().has_icc_profile
    c_has_icc = comparison_media.GetMediaResult().GetFileInfoManager().has_icc_profile
    
    if s_has_icc ^ c_has_icc:
        
        if s_has_icc:
            
            icc_statement = 'this has icc profile, the other does not'
            
        else:
            
            icc_statement = 'the other has icc profile, this does not'
            
        
        statements_and_scores[ 'icc_profile' ] = ( icc_statement, 0 )
        
    
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
                
                work_time = work_time_ms / 1000
                
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
                        
                    
                
                text = 'searching: {}'.format( HydrusData.ConvertValueRangeToPrettyString( num_searched_estimate, total_num_files ) )
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
            
        
    

SYNC_ARCHIVE_NONE = 0
SYNC_ARCHIVE_IF_ONE_DO_BOTH = 1
SYNC_ARCHIVE_DO_BOTH_REGARDLESS = 2

def get_updated_domain_modified_timestamp_datas( destination_media: ClientMedia.MediaSingleton, source_media: ClientMedia.MediaSingleton, urls: typing.Collection[ str ] ):
    
    from hydrus.client.networking import ClientNetworkingFunctions
    
    domains = { ClientNetworkingFunctions.ConvertURLIntoDomain( url ) for url in urls }
    
    timestamp_datas = []
    source_timestamp_manager = source_media.GetLocationsManager().GetTimesManager()
    destination_timestamp_manager = destination_media.GetLocationsManager().GetTimesManager()
    
    for domain in domains:
        
        source_timestamp_ms = source_timestamp_manager.GetDomainModifiedTimestampMS( domain )
        
        if source_timestamp_ms is not None:
            
            timestamp_data = ClientTime.TimestampData.STATICDomainModifiedTime( domain, source_timestamp_ms )
            
            destination_timestamp_ms = destination_timestamp_manager.GetDomainModifiedTimestampMS( domain )
            
            if destination_timestamp_ms is None or ClientTime.ShouldUpdateModifiedTime( destination_timestamp_ms, source_timestamp_ms ):
                
                timestamp_datas.append( timestamp_data )
                
            
        
    
    return timestamp_datas
    

def get_domain_modified_content_updates( destination_media: ClientMedia.MediaSingleton, source_media: ClientMedia.MediaSingleton, urls: typing.Collection[ str ] ):
    
    timestamp_datas = get_updated_domain_modified_timestamp_datas( destination_media, source_media, urls )
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( destination_media.GetHash(), ), timestamp_data ) ) for timestamp_data in timestamp_datas ]
    
    return content_updates
    

class DuplicateContentMergeOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_CONTENT_MERGE_OPTIONS
    SERIALISABLE_NAME = 'Duplicate Content Merge Options'
    SERIALISABLE_VERSION = 7
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._tag_service_actions = []
        self._rating_service_actions = []
        self._sync_notes_action = HC.CONTENT_MERGE_ACTION_NONE
        self._sync_note_import_options = NoteImportOptions.NoteImportOptions()
        self._sync_archive_action = SYNC_ARCHIVE_NONE
        self._sync_urls_action = HC.CONTENT_MERGE_ACTION_NONE
        self._sync_file_modified_date_action = HC.CONTENT_MERGE_ACTION_COPY
        
    
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
        
    
    def ProcessPairIntoContentUpdatePackage( self, first_media: ClientMedia.MediaSingleton, second_media: ClientMedia.MediaSingleton, delete_first = False, delete_second = False, file_deletion_reason = None, do_not_do_deletes = False ) -> ClientContentUpdates.ContentUpdatePackage:
        
        if file_deletion_reason is None:
            
            file_deletion_reason = 'unknown reason'
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        first_hash = first_media.GetHash()
        second_hash = second_media.GetHash()
        first_hashes = { first_hash }
        second_hashes = { second_hash }
        
        first_media_result = first_media.GetMediaResult()
        second_media_result = second_media.GetMediaResult()
        
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
                
            
            first_tags = first_media.GetTagsManager().GetCurrentAndPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            second_tags = second_media.GetTagsManager().GetCurrentAndPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            
            first_tags = tag_filter.Filter( first_tags )
            second_tags = tag_filter.Filter( second_tags )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_tags.difference( first_tags )
                second_needs = first_tags.difference( second_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, second_hashes ) ) for tag in second_needs ) )
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_tags.difference( first_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                
            elif service_type == HC.LOCAL_TAG and action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_needs = second_tags.difference( first_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, second_hashes ) ) for tag in second_tags ) )
                
            
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
                
            
            first_current_value = first_media.GetRatingsManager().GetRating( service_key )
            second_current_value = second_media.GetRatingsManager().GetRating( service_key )
            
            service_type = service.GetServiceType()
            
            if service_type in HC.STAR_RATINGS_SERVICES:
                
                if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                    
                    if worth_updating_rating( first_current_value, second_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( first_current_value, second_hashes ) ) )
                        
                    elif worth_updating_rating( second_current_value, first_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_COPY:
                    
                    if worth_updating_rating( second_current_value, first_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                    
                    if second_current_value is not None:
                        
                        if worth_updating_rating( second_current_value, first_current_value ):
                            
                            content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                            
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, second_hashes ) ) )
                        
                    
                
            elif service_type == HC.LOCAL_RATING_INCDEC:
                
                sum_value = first_current_value + second_current_value
                
                if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, first_hashes ) ) )
                        
                    
                    if first_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, second_hashes ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_COPY:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, first_hashes ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, first_hashes ) ) )
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0, second_hashes ) ) )
                        
                    
                
            else:
                
                continue
                
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        #
        
        if self._sync_notes_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_names_and_notes = list( first_media.GetNotesManager().GetNamesToNotes().items() )
            second_names_and_notes = list( second_media.GetNotesManager().GetNamesToNotes().items() )
            
            # TODO: rework this to UpdateeNamesToNotes
            
            if self._sync_notes_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( first_media_result, second_names_and_notes )
                second_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( second_media_result, first_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                content_update_package.AddContentUpdatePackage( second_content_update_package )
                
            elif self._sync_notes_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( first_media_result, second_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                
            elif self._sync_notes_action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( first_media_result, second_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                
                content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( second_hash, name ) ) for ( name, note ) in second_names_and_notes ]
                
                content_update_package.AddContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, content_updates )
                
            
        
        #
        
        content_update_archive_first = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, first_hashes )
        content_update_archive_second = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, second_hashes )
        
        # and not delete_first gubbins here to help out the delete lock lmao. don't want to archive and then try to delete
        # TODO: this is obviously a bad solution, so better to refactor this function to return a list of content_update_packages and stick the delete command right up top, tested for locks on current info
        
        if self._sync_archive_action == SYNC_ARCHIVE_IF_ONE_DO_BOTH:
            
            if first_media.HasInbox() and second_media.HasArchive() and not delete_first:
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update_archive_first )
                
            elif first_media.HasArchive() and second_media.HasInbox() and not delete_second:
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update_archive_second )
                
            
        elif self._sync_archive_action == SYNC_ARCHIVE_DO_BOTH_REGARDLESS:
            
            if first_media.HasInbox() and not delete_first:
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update_archive_first )
                
            
            if second_media.HasInbox() and not delete_second:
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update_archive_second )
                
            
        
        #
        
        if self._sync_file_modified_date_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_timestamp_ms = first_media.GetMediaResult().GetTimesManager().GetFileModifiedTimestampMS()
            second_timestamp_ms = second_media.GetMediaResult().GetTimesManager().GetFileModifiedTimestampMS()
            
            if self._sync_file_modified_date_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                if ClientTime.ShouldUpdateModifiedTime( first_timestamp_ms, second_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( first_hash, ), ClientTime.TimestampData.STATICFileModifiedTime( second_timestamp_ms ) ) ) )
                    
                elif ClientTime.ShouldUpdateModifiedTime( second_timestamp_ms, first_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( second_hash, ), ClientTime.TimestampData.STATICFileModifiedTime( first_timestamp_ms ) ) ) )
                    
                
            elif self._sync_file_modified_date_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                if ClientTime.ShouldUpdateModifiedTime( first_timestamp_ms, second_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( first_hash, ), ClientTime.TimestampData.STATICFileModifiedTime( second_timestamp_ms ) ) ) )
                    
                
            
        
        #
        
        if self._sync_urls_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_urls = set( first_media.GetLocationsManager().GetURLs() )
            second_urls = set( second_media.GetLocationsManager().GetURLs() )
            
            if self._sync_urls_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_urls.difference( first_urls )
                second_needs = first_urls.difference( second_urls )
                
                if len( first_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, first_hashes ) ) )
                    
                    content_update_package.AddContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, get_domain_modified_content_updates( first_media, second_media, first_needs ) )
                    
                
                if len( second_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( second_needs, second_hashes ) ) )
                    
                    content_update_package.AddContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, get_domain_modified_content_updates( second_media, first_media, second_needs ) )
                    
                
            elif self._sync_urls_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_urls.difference( first_urls )
                
                if len( first_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, first_hashes ) ) )
                    
                    content_update_package.AddContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, get_domain_modified_content_updates( first_media, second_media, first_needs ) )
                    
                
            
        
        #
        
        deletee_media = []
        
        if delete_first:
            
            deletee_media.append( first_media )
            
        
        if delete_second:
            
            deletee_media.append( second_media )
            
        
        for media in deletee_media:
            
            if do_not_do_deletes:
                
                continue
                
            
            if media.HasDeleteLocked():
                
                ClientMediaFileFilter.ReportDeleteLockFailures( [ media ] )
                
                continue
                
            
            if media.GetLocationsManager().IsTrashed():
                
                deletee_service_keys = ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, )
                
            else:
                
                local_file_service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
                
                deletee_service_keys = media.GetLocationsManager().GetCurrent().intersection( local_file_service_keys )
                
            
            for deletee_service_key in deletee_service_keys:
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, media.GetHashes(), reason = file_deletion_reason )
                
                content_update_package.AddContentUpdate( deletee_service_key, content_update )
                
            
        
        #
        
        return content_update_package
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_CONTENT_MERGE_OPTIONS ] = DuplicateContentMergeOptions
