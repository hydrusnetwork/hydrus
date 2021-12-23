import collections
import itertools
import random
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusText
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

hashes_to_jpeg_quality = {}
hashes_to_pixel_hashes = {}

def FilterServiceKeysToContentUpdates( full_service_keys_to_content_updates, hashes ):
    
    if not isinstance( hashes, set ):
        
        hashes = set( hashes )
        
    
    filtered_service_keys_to_content_updates = collections.defaultdict( list )
    
    for ( service_key, full_content_updates ) in full_service_keys_to_content_updates.items():
        
        filtered_content_updates = []
        
        for content_update in full_content_updates:
            
            if not hashes.isdisjoint( content_update.GetHashes() ):
                
                filtered_content_updates.append( content_update )
                
            
        
        if len( filtered_content_updates ) > 0:
            
            filtered_service_keys_to_content_updates[ service_key ] = filtered_content_updates
            
        
    
    return filtered_service_keys_to_content_updates

def FlattenMedia( media_list ):
    
    flat_media = []
    
    for media in media_list:
        
        if media.IsCollection():
            
            flat_media.extend( media.GetFlatMedia() )
            
        else:
            
            flat_media.append( media )
            
        
    
    return flat_media
    
def GetDuplicateComparisonScore( shown_media, comparison_media ):
    
    statements_and_scores = GetDuplicateComparisonStatements( shown_media, comparison_media )
    
    total_score = sum( ( score for ( statement, score ) in statements_and_scores.values() ) )
    
    return total_score
    
def GetDuplicateComparisonStatements( shown_media, comparison_media ):
    
    new_options = HG.client_controller.new_options
    
    duplicate_comparison_score_higher_jpeg_quality = new_options.GetInteger( 'duplicate_comparison_score_higher_jpeg_quality' )
    duplicate_comparison_score_much_higher_jpeg_quality = new_options.GetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality' )
    duplicate_comparison_score_higher_filesize = new_options.GetInteger( 'duplicate_comparison_score_higher_filesize' )
    duplicate_comparison_score_much_higher_filesize = new_options.GetInteger( 'duplicate_comparison_score_much_higher_filesize' )
    duplicate_comparison_score_higher_resolution = new_options.GetInteger( 'duplicate_comparison_score_higher_resolution' )
    duplicate_comparison_score_much_higher_resolution = new_options.GetInteger( 'duplicate_comparison_score_much_higher_resolution' )
    duplicate_comparison_score_more_tags = new_options.GetInteger( 'duplicate_comparison_score_more_tags' )
    duplicate_comparison_score_older = new_options.GetInteger( 'duplicate_comparison_score_older' )
    duplicate_comparison_score_nicer_ratio = new_options.GetInteger( 'duplicate_comparison_score_nicer_ratio' )
    
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
    
    if shown_media.IsStaticImage() and comparison_media.IsStaticImage() and shown_media.GetResolution() == comparison_media.GetResolution():
        
        global hashes_to_pixel_hashes
        
        if s_hash not in hashes_to_pixel_hashes:
            
            path = HG.client_controller.client_files_manager.GetFilePath( s_hash, s_mime )
            
            hashes_to_pixel_hashes[ s_hash ] = HydrusImageHandling.GetImagePixelHash( path, s_mime )
            
        
        if c_hash not in hashes_to_pixel_hashes:
            
            path = HG.client_controller.client_files_manager.GetFilePath( c_hash, c_mime )
            
            hashes_to_pixel_hashes[ c_hash ] = HydrusImageHandling.GetImagePixelHash( path, c_mime )
            
        
        s_pixel_hash = hashes_to_pixel_hashes[ s_hash ]
        c_pixel_hash = hashes_to_pixel_hashes[ c_hash ]
        
        if s_pixel_hash == c_pixel_hash:
            
            is_a_pixel_dupe = True
            
            if s_mime == HC.IMAGE_PNG and c_mime != HC.IMAGE_PNG:
                
                statement = 'this is a pixel-for-pixel duplicate png!'
                
                score = -100
                
            elif s_mime != HC.IMAGE_PNG and c_mime == HC.IMAGE_PNG:
                
                statement = 'other file is a pixel-for-pixel duplicate png!'
                
                score = 100
                
            else:
                
                statement = 'images are pixel-for-pixel duplicates!'
                
                score = 0
                
            
            statements_and_scores[ 'pixel_duplicates' ] = ( statement, score )
            
        
    
    if s_size != c_size:
        
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
            
            operator = CC.UNICODE_ALMOST_EQUAL_TO
            score = 0
            
        
        if is_a_pixel_dupe:
            
            score = 0
            
        
        statement = '{} {} {}'.format( HydrusData.ToHumanBytes( s_size ), operator, HydrusData.ToHumanBytes( c_size ) )
        
        statements_and_scores[ 'filesize' ]  = ( statement, score )
        
    
    # higher/same res
    
    s_resolution = shown_media.GetResolution()
    c_resolution = comparison_media.GetResolution()
    
    if s_resolution is not None and c_resolution is not None and s_resolution != c_resolution:
        
        s_res = shown_media.GetResolution()
        c_res = comparison_media.GetResolution()
        
        ( s_w, s_h ) = s_res
        ( c_w, c_h ) = c_res
        
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
            
        
        if s_res in HC.NICE_RESOLUTIONS:
            
            s_string = HC.NICE_RESOLUTIONS[ s_res ]
            
        else:
            
            s_string = HydrusData.ConvertResolutionToPrettyString( s_resolution )
            
            if s_w % 2 == 1 or s_h % 2 == 1:
                
                s_string += ' (unusual)'
                
            
        
        if c_res in HC.NICE_RESOLUTIONS:
            
            c_string = HC.NICE_RESOLUTIONS[ c_res ]
            
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
    
    if s_mime != c_mime:
        
        statement = '{} vs {}'.format( HC.mime_string_lookup[ s_mime ], HC.mime_string_lookup[ c_mime ] )
        score = 0
        
        statements_and_scores[ 'mime' ] = ( statement, score )
        
    
    # more tags
    
    s_num_tags = len( shown_media.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ) )
    c_num_tags = len( comparison_media.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ) )
    
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
    
    s_ts = shown_media.GetLocationsManager().GetCurrentTimestamp( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
    c_ts = comparison_media.GetLocationsManager().GetCurrentTimestamp( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
    
    one_month = 86400 * 30
    
    if s_ts is not None and c_ts is not None and abs( s_ts - c_ts ) > one_month:
        
        if s_ts < c_ts:
            
            operator = 'older than'
            score = duplicate_comparison_score_older
            
        else:
            
            operator = 'newer than'
            score = -duplicate_comparison_score_older
            
        
        if is_a_pixel_dupe:
            
            score = 0
            
        
        statement = '{}, {} {}'.format( ClientData.TimestampToPrettyTimeDelta( s_ts, history_suffix = ' old' ), operator, ClientData.TimestampToPrettyTimeDelta( c_ts, history_suffix = ' old' ) )
        
        statements_and_scores[ 'time_imported' ] = ( statement, score )
        
    
    if s_mime == HC.IMAGE_JPEG and c_mime == HC.IMAGE_JPEG:
        
        global hashes_to_jpeg_quality
        
        if s_hash not in hashes_to_jpeg_quality:
            
            path = HG.client_controller.client_files_manager.GetFilePath( s_hash, s_mime )
            
            hashes_to_jpeg_quality[ s_hash ] = HydrusImageHandling.GetJPEGQuantizationQualityEstimate( path )
            
        
        if c_hash not in hashes_to_jpeg_quality:
            
            path = HG.client_controller.client_files_manager.GetFilePath( c_hash, c_mime )
            
            hashes_to_jpeg_quality[ c_hash ] = HydrusImageHandling.GetJPEGQuantizationQualityEstimate( path )
            
        
        ( s_label, s_jpeg_quality ) = hashes_to_jpeg_quality[ s_hash ]
        ( c_label, c_jpeg_quality ) = hashes_to_jpeg_quality[ c_hash ]
        
        score = 0
        
        if s_label != c_label:
            
            if c_jpeg_quality is None or s_jpeg_quality is None:
                
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
            
        
    
    return statements_and_scores
    
def GetMediasTags( pool, tag_service_key, tag_display_type, content_statuses ):
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection():
            
            tags_managers.extend( media.GetSingletonsTagsManagers() )
            
        else:
            
            tags_managers.append( media.GetTagsManager() )
            
        
    
    tags = set()
    
    for tags_manager in tags_managers:
        
        statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, tag_display_type )
        
        for content_status in content_statuses:
            
            tags.update( statuses_to_tags[ content_status ] )
            
        
    
    return tags
    
def GetMediaResultsTagCount( media_results, tag_service_key, tag_display_type ):
    
    tags_managers = [ media_result.GetTagsManager() for media_result in media_results ]
    
    return GetTagsManagersTagCount( tags_managers, tag_service_key, tag_display_type )
    
def GetMediasTagCount( pool, tag_service_key, tag_display_type ):
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection():
            
            tags_managers.extend( media.GetSingletonsTagsManagers() )
            
        else:
            
            tags_managers.append( media.GetTagsManager() )
            
        
    
    return GetTagsManagersTagCount( tags_managers, tag_service_key, tag_display_type )
    
def GetTagsManagersTagCount( tags_managers, tag_service_key, tag_display_type ):
    
    current_tags_to_count = collections.Counter()
    deleted_tags_to_count = collections.Counter()
    pending_tags_to_count = collections.Counter()
    petitioned_tags_to_count = collections.Counter()
    
    for tags_manager in tags_managers:
        
        statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, tag_display_type )
        
        current_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ] )
        deleted_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_DELETED ] )
        pending_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] )
        petitioned_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ] )
        
    
    return ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
    
class Media( object ):
    
    def __init__( self ):
        
        self._id = HydrusData.GenerateKey()
        self._id_hash = self._id.__hash__()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Media ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self._id_hash
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def GetDisplayMedia( self ) -> 'Media':
        
        raise NotImplementedError()
        
    
    def GetDuration( self ) -> typing.Optional[ int ]:
        
        raise NotImplementedError()
        
    
    def GetFileViewingStatsManager( self ) -> ClientMediaManagers.FileViewingStatsManager:
        
        raise NotImplementedError()
        
    
    def GetHash( self ) -> bytes:
        
        raise NotImplementedError()
        
    
    def GetHashes( self, has_location = None, discriminant = None, not_uploaded_to = None, ordered = False ):
        
        raise NotImplementedError()
        
    
    def GetLocationsManager( self ) -> ClientMediaManagers.LocationsManager:
        
        raise NotImplementedError()
        
    
    def GetMime( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetNumFiles( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetNumFrames( self ) -> typing.Optional[ int ]:
        
        raise NotImplementedError()
        
    
    def GetNumInbox( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetNumWords( self ) -> typing.Optional[ int ]:
        
        raise NotImplementedError()
        
    
    def GetCurrentTimestamp( self, service_key: bytes ) -> typing.Optional[ int ]:
        
        raise NotImplementedError()
        
    
    def GetDeletedTimestamps( self, service_key: bytes ) -> typing.Tuple[ typing.Optional[ int ], typing.Optional[ int ] ]:
        
        raise NotImplementedError()
        
    
    def GetPrettyInfoLines( self ) -> typing.List[ str ]:
        
        raise NotImplementedError()
        
    
    def GetRatingsManager( self ) -> ClientMediaManagers.RatingsManager:
        
        raise NotImplementedError()
        
    
    def GetResolution( self ) -> typing.Tuple[ int, int ]:
        
        raise NotImplementedError()
        
    
    def GetSize( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetTagsManager( self ) -> ClientMediaManagers.TagsManager:
        
        raise NotImplementedError()
        
    
    def HasAnyOfTheseHashes( self, hashes ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasArchive( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasAudio( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasDuration( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasImages( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasInbox( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasNotes( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsCollection( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsImage( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsSizeDefinite( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def UpdateFileInfo( self, hashes_to_media_results ):
        
        raise NotImplementedError()
        
    
class MediaCollect( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_COLLECT
    SERIALISABLE_NAME = 'Media Collect'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, namespaces = None, rating_service_keys = None, collect_unmatched = None ):
        
        if namespaces is None:
            
            namespaces = []
            
        
        if rating_service_keys is None:
            
            rating_service_keys = []
            
        
        if collect_unmatched is None:
            
            collect_unmatched = True
            
        
        self.namespaces = namespaces
        self.rating_service_keys = rating_service_keys
        self.collect_unmatched = collect_unmatched
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_rating_service_keys = [ key.hex() for key in self.rating_service_keys ]
        
        return ( self.namespaces, serialisable_rating_service_keys, self.collect_unmatched )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.namespaces, serialisable_rating_service_keys, self.collect_unmatched ) = serialisable_info
        
        self.rating_service_keys = [ bytes.fromhex( serialisable_key ) for serialisable_key in serialisable_rating_service_keys ]
        
    
    def DoesACollect( self ):
        
        return len( self.namespaces ) > 0 or len( self.rating_service_keys ) > 0
        
    
    def ToString( self ):
        
        s_list = list( self.namespaces )
        s_list.extend( [ HG.client_controller.services_manager.GetName( service_key ) for service_key in self.rating_service_keys if HG.client_controller.services_manager.ServiceExists( service_key ) ] )
        
        if len( s_list ) == 0:
            
            return 'no collections'
            
        else:
            
            return ', '.join( s_list )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_COLLECT ] = MediaCollect

class MediaList( object ):
    
    def __init__( self, file_service_key, media_results ):
        
        hashes_seen = set()
        
        media_results_dedupe = []
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            if hash in hashes_seen:
                
                continue
                
            
            media_results_dedupe.append( media_result )
            hashes_seen.add( hash )
            
        
        media_results = media_results_dedupe
        
        self._file_service_key = file_service_key
        
        self._hashes = set()
        self._hashes_ordered = []
        
        self._hashes_to_singleton_media = {}
        self._hashes_to_collected_media = {}
        
        self._media_sort = MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        self._media_collect = MediaCollect()
        
        self._sorted_media = SortedList( [ self._GenerateMediaSingleton( media_result ) for media_result in media_results ] )
        self._selected_media = set()
        
        self._singleton_media = set( self._sorted_media )
        self._collected_media = set()
        
        self._RecalcHashes()
        
    
    def __len__( self ):
        
        return len( self._singleton_media ) + sum( map( len, self._collected_media ) )
        
    
    def _CalculateCollectionKeysToMedias( self, media_collect, medias ):
        
        keys_to_medias = collections.defaultdict( list )
        
        namespaces_to_collect_by = list( media_collect.namespaces )
        ratings_to_collect_by = list( media_collect.rating_service_keys )
        
        for media in medias:
            
            if len( namespaces_to_collect_by ) > 0:
                
                namespace_key = media.GetTagsManager().GetNamespaceSlice( namespaces_to_collect_by, ClientTags.TAG_DISPLAY_ACTUAL )
                
            else:
                
                namespace_key = frozenset()
                
            
            if len( ratings_to_collect_by ) > 0:
                
                rating_key = media.GetRatingsManager().GetRatingSlice( ratings_to_collect_by )
                
            else:
                
                rating_key = frozenset()
                
            
            keys_to_medias[ ( namespace_key, rating_key ) ].append( media )
            
        
        return keys_to_medias
        
    
    def _GenerateMediaCollection( self, media_results ):
        
        return MediaCollection( self._file_service_key, media_results )
        
    
    def _GenerateMediaSingleton( self, media_result ):
        
        return MediaSingleton( media_result )
        
    
    def _GetFirst( self ):
        
        if len( self._sorted_media ) > 0:
            
            return self._sorted_media[ 0 ]
            
        else:
            
            return None
            
        
    
    def _GetLast( self ):
        
        if len( self._sorted_media ) > 0:
            
            return self._sorted_media[ -1 ]
            
        else:
            
            return None
            
        
    
    def _GetMedia( self, hashes, discriminator = None ):
        
        if hashes.isdisjoint( self._hashes ):
            
            return []
            
        
        medias = []
        
        if discriminator is None or discriminator == 'singletons':
            
            medias.extend( ( self._hashes_to_singleton_media[ hash ] for hash in hashes if hash in self._hashes_to_singleton_media ) )
            
        
        if discriminator is None or discriminator == 'collections':
            
            medias.extend( { self._hashes_to_collected_media[ hash ] for hash in hashes if hash in self._hashes_to_collected_media } )
            
        
        return medias
        
    
    def _GetNext( self, media ):
        
        if media is None:
            
            return None
            
        
        next_index = self._sorted_media.index( media ) + 1
        
        if next_index == len( self._sorted_media ):
            
            return self._GetFirst()
            
        else:
            
            return self._sorted_media[ next_index ]
            
        
    
    def _GetPrevious( self, media ):
        
        if media is None: return None
        
        previous_index = self._sorted_media.index( media ) - 1
        
        if previous_index == -1:
            
            return self._GetLast()
            
        else:
            
            return self._sorted_media[ previous_index ]
            
        
    
    def _HasHashes( self, hashes ):
        
        for hash in hashes:
            
            if hash in self._hashes:
                
                return True
                
            
        
        return False
        
    
    def _RecalcAfterContentUpdates( self, service_keys_to_content_updates ):
        
        pass
        
    
    def _RecalcAfterMediaRemove( self ):
        
        self._RecalcHashes()
        
    
    def _RecalcHashes( self ):
        
        self._hashes = set()
        self._hashes_ordered = []
        
        self._hashes_to_singleton_media = {}
        self._hashes_to_collected_media = {}
        
        for m in self._sorted_media:
            
            if isinstance( m, MediaCollection ):
                
                hashes = m.GetHashes( ordered = True )
                
                self._hashes.update( hashes )
                self._hashes_ordered.extend( hashes )
                
                for hash in hashes:
                    
                    self._hashes_to_collected_media[ hash ] = m
                    
                
            else:
                
                hash = m.GetHash()
                
                self._hashes.add( hash )
                self._hashes_ordered.append( hash )
                
                self._hashes_to_singleton_media[ hash ] = m
                
            
        
    
    def _RemoveMediaByHashes( self, hashes ):
        
        if not isinstance( hashes, set ):
            
            hashes = set( hashes )
            
        
        affected_singleton_media = self._GetMedia( hashes, discriminator = 'singletons' )
        
        for media in self._collected_media:
            
            media._RemoveMediaByHashes( hashes )
            
        
        affected_collected_media = [ media for media in self._collected_media if media.HasNoMedia() ]
        
        self._RemoveMediaDirectly( affected_singleton_media, affected_collected_media )
        
    
    def _RemoveMediaDirectly( self, singleton_media, collected_media ):
        
        if not isinstance( singleton_media, set ):
            
            singleton_media = set( singleton_media )
            
        
        if not isinstance( collected_media, set ):
            
            collected_media = set( collected_media )
            
        
        self._singleton_media.difference_update( singleton_media )
        self._collected_media.difference_update( collected_media )
        
        self._sorted_media.remove_items( singleton_media.union( collected_media ) )
        
        self._RecalcAfterMediaRemove()
        
    
    def AddMedia( self, new_media ):
        
        new_media = FlattenMedia( new_media )
        
        addable_media = []
        
        for media in new_media:
            
            hash = media.GetHash()
            
            if hash in self._hashes:
                
                continue
                
            
            addable_media.append( media )
            
            self._hashes.add( hash )
            self._hashes_ordered.append( hash )
            
            self._hashes_to_singleton_media[ hash ] = media
            
        
        self._singleton_media.update( addable_media )
        self._sorted_media.append_items( addable_media )
        
        return new_media
        
    
    def Collect( self, media_collect = None ):
        
        if media_collect == None:
            
            media_collect = self._media_collect
            
        
        self._media_collect = media_collect
        
        flat_media = list( self._singleton_media )
        
        for media in self._collected_media:
            
            flat_media.extend( [ self._GenerateMediaSingleton( media_result ) for media_result in media.GenerateMediaResults() ] )
            
        
        if self._media_collect.DoesACollect():
            
            keys_to_medias = self._CalculateCollectionKeysToMedias( media_collect, flat_media )
            
            # add an option here I think, to media_collect to say if collections with one item should be singletons or not
            
            self._singleton_media = set()#{ medias[0] for ( key, medias ) in keys_to_medias.items() if len( medias ) == 1 }
            
            if not self._media_collect.collect_unmatched:
                
                unmatched_key = ( frozenset(), frozenset() )
                
                if unmatched_key in keys_to_medias:
                    
                    unmatched_medias = keys_to_medias[ unmatched_key ]
                    
                    self._singleton_media.update( unmatched_medias )
                    
                    del keys_to_medias[ unmatched_key ]
                    
                
            
            self._collected_media = { self._GenerateMediaCollection( [ media.GetMediaResult() for media in medias ] ) for ( key, medias ) in keys_to_medias.items() }# if len( medias ) > 1 }
            
        else:
            
            self._singleton_media = set( flat_media )
            
            self._collected_media = set()
            
        
        self._sorted_media = SortedList( list( self._singleton_media ) + list( self._collected_media ) )
        
        self._RecalcHashes()
        
    
    def DeletePending( self, service_key ):
        
        for media in self._collected_media:
            
            media.DeletePending( service_key )
            
        
    
    def GetFilteredFileCount( self, file_filter ):
        
        if file_filter.filter_type == FILE_FILTER_ALL:
            
            return self.GetNumFiles()
            
        elif file_filter.filter_type == FILE_FILTER_SELECTED:
            
            return sum( ( m.GetNumFiles() for m in self._selected_media ) )
            
        elif file_filter.filter_type == FILE_FILTER_NOT_SELECTED:
            
            return self.GetNumFiles() - sum( ( m.GetNumFiles() for m in self._selected_media ) )
            
        elif file_filter.filter_type == FILE_FILTER_NONE:
            
            return 0
            
        elif file_filter.filter_type == FILE_FILTER_INBOX:
            
            return sum( ( m.GetNumInbox() for m in self._selected_media ) )
            
        elif file_filter.filter_type == FILE_FILTER_ARCHIVE:
            
            return self.GetNumFiles() - sum( ( m.GetNumInbox() for m in self._selected_media ) )
            
        else:
            
            flat_media = self.GetFlatMedia()
            
            if file_filter.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = file_filter.filter_data
                
                return sum( ( 1 for m in flat_media if file_service_key in m.GetLocationsManager().GetCurrent() ) )
                
            elif file_filter.filter_type == FILE_FILTER_LOCAL:
                
                return sum( ( 1 for m in flat_media if m.GetLocationsManager().IsLocal() ) )
                
            elif file_filter.filter_type == FILE_FILTER_REMOTE:
                
                return sum( ( 1 for m in flat_media if m.GetLocationsManager().IsRemote() ) )
                
            elif file_filter.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = file_filter.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    return sum( ( 1 for m in flat_media if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ) ) ) )
                    
                elif and_or_or == 'OR':
                    
                    return sum( ( 1 for m in flat_media if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), select_tags ) ) )
                    
                
            
        
        return 0
        
    
    def GetFilteredHashes( self, file_filter ):
        
        if file_filter.filter_type == FILE_FILTER_ALL:
            
            return self._hashes
            
        elif file_filter.filter_type == FILE_FILTER_SELECTED:
            
            hashes = set()
            
            for m in self._selected_media:
                
                hashes.update( m.GetHashes() )
                
            
            return hashes
            
        elif file_filter.filter_type == FILE_FILTER_NOT_SELECTED:
            
            hashes = set()
            
            for m in self._sorted_media:
                
                if m not in self._selected_media:
                    
                    hashes.update( m.GetHashes() )
                    
                
            
            return hashes
            
        elif file_filter.filter_type == FILE_FILTER_NONE:
            
            return set()
            
        else:
            
            flat_media = self.GetFlatMedia()
            
            if file_filter.filter_type == FILE_FILTER_INBOX:
                
                filtered_media = [ m for m in flat_media if m.HasInbox() ]
                
            elif file_filter.filter_type == FILE_FILTER_ARCHIVE:
                
                filtered_media = [ m for m in flat_media if not m.HasInbox() ]
                
            elif file_filter.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = file_filter.filter_data
                
                filtered_media = [ m for m in flat_media if file_service_key in m.GetLocationsManager().GetCurrent() ]
                
            elif file_filter.filter_type == FILE_FILTER_LOCAL:
                
                filtered_media = [ m for m in flat_media if m.GetLocationsManager().IsLocal() ]
                
            elif file_filter.filter_type == FILE_FILTER_REMOTE:
                
                filtered_media = [ m for m in flat_media if m.GetLocationsManager().IsRemote() ]
                
            elif file_filter.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = file_filter.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    filtered_media = [ m for m in flat_media if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ) ) ]
                    
                elif and_or_or == 'OR':
                    
                    filtered_media = [ m for m in flat_media if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), select_tags ) ]
                    
                
            
            hashes = { m.GetHash() for m in filtered_media }
            
            return hashes
            
        
        return set()
        
    
    def GetFilteredMedia( self, file_filter ):
        
        if file_filter.filter_type == FILE_FILTER_ALL:
            
            return set( self._sorted_media )
            
        elif file_filter.filter_type == FILE_FILTER_SELECTED:
            
            return self._selected_media
            
        elif file_filter.filter_type == FILE_FILTER_NOT_SELECTED:
            
            return { m for m in self._sorted_media if m not in self._selected_media }
            
        elif file_filter.filter_type == FILE_FILTER_NONE:
            
            return set()
            
        else:
            
            if file_filter.filter_type == FILE_FILTER_INBOX:
                
                filtered_media = { m for m in self._sorted_media if m.HasInbox() }
                
            elif file_filter.filter_type == FILE_FILTER_ARCHIVE:
                
                filtered_media = { m for m in self._sorted_media if not m.HasInbox() }
                
            elif file_filter.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = file_filter.filter_data
                
                filtered_media = { m for m in self._sorted_media if file_service_key in m.GetLocationsManager().GetCurrent() }
                
            elif file_filter.filter_type == FILE_FILTER_LOCAL:
                
                filtered_media = { m for m in self._sorted_media if m.GetLocationsManager().IsLocal() }
                
            elif file_filter.filter_type == FILE_FILTER_REMOTE:
                
                filtered_media = { m for m in self._sorted_media if m.GetLocationsManager().IsRemote() }
                
            elif file_filter.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = file_filter.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    filtered_media = { m for m in self._sorted_media if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ) ) }
                    
                elif and_or_or == 'OR':
                    
                    filtered_media = { m for m in self._sorted_media if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), select_tags ) }
                    
                
            
            return filtered_media
            
        
        return set()
        
    
    def GenerateMediaResults( self, has_location = None, discriminant = None, selected_media = None, unrated = None, for_media_viewer = False ):
        
        media_results = []
        
        for media in self._sorted_media:
            
            if has_location is not None:
                
                locations_manager = media.GetLocationsManager()
                
                if has_location not in locations_manager.GetCurrent():
                    
                    continue
                    
                
            
            if selected_media is not None and media not in selected_media:
                
                continue
                
            
            if media.IsCollection():
                
                # don't include selected_media here as it is not valid at the deeper collection level
                
                media_results.extend( media.GenerateMediaResults( has_location = has_location, discriminant = discriminant, unrated = unrated, for_media_viewer = True ) )
                
            else:
                
                if discriminant is not None:
                    
                    locations_manager = media.GetLocationsManager()
                    
                    if discriminant == CC.DISCRIMINANT_INBOX:
                        
                        p = media.HasInbox()
                        
                    elif discriminant == CC.DISCRIMINANT_ARCHIVE:
                        
                        p = not media.HasInbox()
                        
                    elif discriminant == CC.DISCRIMINANT_LOCAL:
                        
                        p = locations_manager.IsLocal()
                        
                    elif discriminant == CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH:
                        
                        p = locations_manager.IsLocal() and not locations_manager.IsTrashed()
                        
                    elif discriminant == CC.DISCRIMINANT_NOT_LOCAL:
                        
                        p = not locations_manager.IsLocal()
                        
                    elif discriminant == CC.DISCRIMINANT_DOWNLOADING:
                        
                        p = locations_manager.IsDownloading()
                        
                    
                    if not p:
                        
                        continue
                        
                    
                
                if unrated is not None:
                    
                    ratings_manager = media.GetRatingsManager()
                    
                    if ratings_manager.GetRating( unrated ) is not None:
                        
                        continue
                        
                    
                
                if for_media_viewer:
                    
                    new_options = HG.client_controller.new_options
                    
                    ( media_show_action, media_start_paused, media_start_with_embed ) = new_options.GetMediaShowAction( media.GetMime() )
                    
                    if media_show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
                        
                        continue
                        
                    
                
                media_results.append( media.GetMediaResult() )
                
            
        
        return media_results
        
    
    def GetAPIInfoDict( self, simple ):
        
        d = {}
        
        d[ 'num_files' ] = self.GetNumFiles()
        
        flat_media = self.GetFlatMedia()
        
        d[ 'hash_ids' ] = [ m.GetMediaResult().GetHashId() for m in flat_media ]
        
        if not simple:
            
            hashes = self.GetHashes( ordered = True )
            
            d[ 'hashes' ] = [ hash.hex() for hash in hashes ]
            
        
        return d
        
    
    def GetFirst( self ):
        
        return self._GetFirst()
        
    
    def GetFlatMedia( self ):
        
        flat_media = []
        
        for media in self._sorted_media:
            
            if media.IsCollection():
                
                flat_media.extend( media.GetFlatMedia() )
                
            else:
                
                flat_media.append( media )
                
            
        
        return flat_media
        
    
    def GetHashes( self, has_location = None, discriminant = None, not_uploaded_to = None, ordered = False ):
        
        if has_location is None and discriminant is None and not_uploaded_to is None:
            
            if ordered:
                
                return self._hashes_ordered
                
            else:
                
                return self._hashes
                
            
        else:
            
            if ordered:
                
                result = []
                
                for media in self._sorted_media:
                    
                    result.extend( media.GetHashes( has_location, discriminant, not_uploaded_to, ordered ) )
                    
                
            else:
                
                result = set()
                
                for media in self._sorted_media:
                    
                    result.update( media.GetHashes( has_location, discriminant, not_uploaded_to, ordered ) )
                    
                
            
            return result
            
        
    
    def GetLast( self ):
        
        return self._GetLast()
        
    
    def GetMediaIndex( self, media ):
        
        return self._sorted_media.index( media )
        
    
    def GetNext( self, media ):
        
        return self._GetNext( media )
        
    
    def GetNumArchive( self ):
        
        num_archive = sum( ( 1 for m in self._singleton_media if not m.HasInbox() ) ) + sum( ( m.GetNumArchive() for m in self._collected_media ) )
        
        return num_archive
        
    
    def GetNumFiles( self ):
        
        return len( self._hashes )
        
    
    def GetNumInbox( self ):
        
        num_inbox = sum( ( 1 for m in self._singleton_media if m.HasInbox() ) ) + sum( ( m.GetNumInbox() for m in self._collected_media ) )
        
        return num_inbox
        
    
    def GetPrevious( self, media ):
        
        return self._GetPrevious( media )
        
    
    def GetSortedMedia( self ):
        
        return self._sorted_media
        
    
    def HasAnyOfTheseHashes( self, hashes: set ):
        
        return not hashes.isdisjoint( self._hashes )
        
    
    def HasMedia( self, media ):
        
        if media is None:
            
            return False
            
        
        if media in self._singleton_media:
            
            return True
            
        elif media in self._collected_media:
            
            return True
            
        else:
            
            for media_collection in self._collected_media:
                
                if media_collection.HasMedia( media ):
                    
                    return True
                    
                
            
        
        return False
        
    
    def HasNoMedia( self ):
        
        return len( self._sorted_media ) == 0
        
    
    def ProcessContentUpdates( self, full_service_keys_to_content_updates ):
        
        service_keys_to_content_updates = FilterServiceKeysToContentUpdates( full_service_keys_to_content_updates, self._hashes )
        
        if len( service_keys_to_content_updates ) == 0:
            
            return
            
        
        for m in self._collected_media:
            
            m.ProcessContentUpdates( service_keys_to_content_updates )
            
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                hashes = content_update.GetHashes()
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action == HC.CONTENT_UPDATE_DELETE:
                        
                        local_file_domains = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
                        non_trash_local_file_services = list( local_file_domains ) + [ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ]
                        all_local_file_services = list( non_trash_local_file_services ) + [ CC.TRASH_SERVICE_KEY ]
                        
                        #
                        
                        physically_deleted = service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                        trashed = service_key in local_file_domains
                        deleted_from_our_domain = service_key == self._file_service_key
                        
                        physically_deleted_and_local_view = physically_deleted and self._file_service_key in all_local_file_services
                        
                        user_says_remove_and_trashed_from_non_trash_local_view = HC.options[ 'remove_trashed_files' ] and trashed and self._file_service_key in non_trash_local_file_services
                        
                        deleted_from_repo_and_repo_view = service_key not in all_local_file_services and deleted_from_our_domain
                        
                        if physically_deleted_and_local_view or user_says_remove_and_trashed_from_non_trash_local_view or deleted_from_repo_and_repo_view:
                            
                            self._RemoveMediaByHashes( hashes )
                            
                        
                    
                
            
        
        self._RecalcAfterContentUpdates( service_keys_to_content_updates )
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        for ( service_key, service_updates ) in list(service_keys_to_service_updates.items()):
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action == HC.SERVICE_UPDATE_DELETE_PENDING:
                    
                    self.DeletePending( service_key )
                    
                elif action == HC.SERVICE_UPDATE_RESET:
                    
                    self.ResetService( service_key )
                    
                
            
        
    
    def ResetService( self, service_key ):
        
        if service_key == self._file_service_key:
            
            self._RemoveMediaDirectly( self._singleton_media, self._collected_media )
            
        else:
            
            for media in self._collected_media: media.ResetService( service_key )
            
        
    
    def Sort( self, media_sort = None ):
        
        for media in self._collected_media:
            
            media.Sort( media_sort )
            
        
        if media_sort is None:
            
            media_sort = self._media_sort
            
        
        self._media_sort = media_sort
        
        media_sort_fallback = HG.client_controller.new_options.GetFallbackSort()
        
        ( sort_key, reverse ) = media_sort_fallback.GetSortKeyAndReverse( self._file_service_key )
        
        self._sorted_media.sort( sort_key, reverse = reverse )
        
        # this is a stable sort, so the fallback order above will remain for equal items
        
        ( sort_key, reverse ) = self._media_sort.GetSortKeyAndReverse( self._file_service_key )
        
        self._sorted_media.sort( sort_key = sort_key, reverse = reverse )
        
        self._RecalcHashes()
        
    
FILE_FILTER_ALL = 0
FILE_FILTER_NOT_SELECTED = 1
FILE_FILTER_NONE = 2
FILE_FILTER_INBOX = 3
FILE_FILTER_ARCHIVE = 4
FILE_FILTER_FILE_SERVICE = 5
FILE_FILTER_LOCAL = 6
FILE_FILTER_REMOTE = 7
FILE_FILTER_TAGS = 8
FILE_FILTER_SELECTED = 9
FILE_FILTER_MIME = 10

file_filter_str_lookup = {}

file_filter_str_lookup[ FILE_FILTER_ALL ] = 'all'
file_filter_str_lookup[ FILE_FILTER_NOT_SELECTED ] = 'not selected'
file_filter_str_lookup[ FILE_FILTER_SELECTED ] = 'selected'
file_filter_str_lookup[ FILE_FILTER_NONE ] = 'none'
file_filter_str_lookup[ FILE_FILTER_INBOX ] = 'inbox'
file_filter_str_lookup[ FILE_FILTER_ARCHIVE ] = 'archive'
file_filter_str_lookup[ FILE_FILTER_FILE_SERVICE ] = 'file service'
file_filter_str_lookup[ FILE_FILTER_LOCAL ] = 'local'
file_filter_str_lookup[ FILE_FILTER_REMOTE ] = 'not local'
file_filter_str_lookup[ FILE_FILTER_TAGS ] = 'tags'
file_filter_str_lookup[ FILE_FILTER_MIME ] = 'filetype'

class FileFilter( object ):
    
    def __init__( self, filter_type, filter_data = None ):
        
        self.filter_type = filter_type
        self.filter_data = filter_data
        
    
    def __eq__( self, other ):
        
        if isinstance( other, FileFilter ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        if self.filter_data is None:
            
            return self.filter_type.__hash__()
            
        else:
            
            return ( self.filter_type, self.filter_data ).__hash__()
            
        
    
    def PopulateFilterCounts( self, media_list: MediaList, filter_counts: dict ):
        
        if self not in filter_counts:
            
            if self.filter_type == FILE_FILTER_NONE:
                
                filter_counts[ self ] = 0
                
                return
                
            
            quick_inverse_lookups= {}
            
            quick_inverse_lookups[ FileFilter( FILE_FILTER_INBOX ) ] = FileFilter( FILE_FILTER_ARCHIVE )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_ARCHIVE ) ] = FileFilter( FILE_FILTER_INBOX )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_SELECTED ) ] = FileFilter( FILE_FILTER_NOT_SELECTED )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_NOT_SELECTED ) ] = FileFilter( FILE_FILTER_SELECTED )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_LOCAL ) ] = FileFilter( FILE_FILTER_REMOTE )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_REMOTE ) ] = FileFilter( FILE_FILTER_LOCAL )
            
            if self in quick_inverse_lookups:
                
                inverse = quick_inverse_lookups[ self ]
                
                all_filter = FileFilter( FILE_FILTER_ALL )
                
                if all_filter in filter_counts and inverse in filter_counts:
                    
                    filter_counts[ self ] = filter_counts[ all_filter ] - filter_counts[ inverse ]
                    
                    return
                    
                
            
            count = media_list.GetFilteredFileCount( self )
            
            filter_counts[ self ] = count
            
        
    
    def GetCount( self, media_list: MediaList, filter_counts: dict ):
        
        self.PopulateFilterCounts( media_list, filter_counts )
        
        return filter_counts[ self ]
        
    
    def ToString( self, media_list: MediaList, filter_counts: dict ):
        
        if self.filter_type == FILE_FILTER_FILE_SERVICE:
            
            file_service_key = self.filter_data
            
            s = HG.client_controller.services_manager.GetName( file_service_key )
            
        elif self.filter_type == FILE_FILTER_TAGS:
            
            ( tag_service_key, and_or_or, select_tags ) = self.filter_data
            
            s = and_or_or.join( select_tags )
            
            if tag_service_key != CC.COMBINED_TAG_SERVICE_KEY:
                
                s = '{} on {}'.format( s, HG.client_controller.services_manager.GetName( tag_service_key ) )
                
            
            s = HydrusText.ElideText( s, 64 )
            
        elif self.filter_type == FILE_FILTER_MIME:
            
            mime = self.filter_data
            
            s = HC.mime_string_lookup[ mime ]
            
        else:
            
            s = file_filter_str_lookup[ self.filter_type ]
            
        
        self.PopulateFilterCounts( media_list, filter_counts )
        
        my_count = filter_counts[ self ]
        
        s += ' ({})'.format( HydrusData.ToHumanInt( my_count ) )
        
        if self.filter_type == FILE_FILTER_ALL:
            
            inbox_filter = FileFilter( FILE_FILTER_INBOX )
            archive_filter = FileFilter( FILE_FILTER_ARCHIVE )
            
            inbox_filter.PopulateFilterCounts( media_list, filter_counts )
            archive_filter.PopulateFilterCounts( media_list, filter_counts )
            
            inbox_count = filter_counts[ inbox_filter ]
            
            if inbox_count > 0 and inbox_count == my_count:
                
                s += ' (all in inbox)'
                
            else:
                
                archive_count = filter_counts[ archive_filter ]
                
                if archive_count > 0 and archive_count == my_count:
                    
                    s += ' (all in archive)'
                    
                
            
        
        return s
        
    
class ListeningMediaList( MediaList ):
    
    def __init__( self, file_service_key, media_results ):
        
        MediaList.__init__( self, file_service_key, media_results )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
    
    def AddMediaResults( self, media_results ):
        
        new_media = []
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            if hash in self._hashes:
                
                continue
                
            
            new_media.append( self._GenerateMediaSingleton( media_result ) )
            
        
        self.AddMedia( new_media )
        
        return new_media
        
    
class MediaCollection( MediaList, Media ):
    
    def __init__( self, file_service_key, media_results ):
        
        # note for later: ideal here is to stop this multiple inheritance mess and instead have this be a media that *has* a list, not *is* a list
        
        Media.__init__( self )
        MediaList.__init__( self, file_service_key, media_results )
        
        self._archive = True
        self._inbox = False
        
        self._size = 0
        self._size_definite = True
        
        self._width = None
        self._height = None
        self._duration = None
        self._num_frames = None
        self._num_words = None
        self._has_audio = None
        self._tags_manager = None
        self._locations_manager = None
        self._file_viewing_stats_manager = None
        
        self._internals_dirty = False
        
        self._RecalcInternals()
        
    
    def _RecalcAfterContentUpdates( self, service_keys_to_content_updates ):
        
        archive_or_inbox = False
        
        data_types = set()
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            for content_update in content_updates:
                
                data_type = content_update.GetDataType()
                
                if data_type in ( HC.CONTENT_TYPE_URLS, HC.CONTENT_TYPE_NOTES ):
                    
                    continue
                    
                elif data_type == HC.CONTENT_TYPE_FILES:
                    
                    action = content_update.GetAction()
                    
                    if action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_INBOX ):
                        
                        archive_or_inbox = True
                        
                        continue
                        
                    
                
                data_types.add( data_type )
                
            
        
        if archive_or_inbox and data_types.issubset( {
            HC.CONTENT_TYPE_RATINGS,
            HC.CONTENT_TYPE_FILE_VIEWING_STATS,
            HC.CONTENT_TYPE_MAPPINGS
        }):
            
            if archive_or_inbox:
                
                self._RecalcArchiveInbox()
                
            
            for data_type in data_types:
                
                if data_type == HC.CONTENT_TYPE_RATINGS:
                    
                    self._RecalcRatings()
                    
                elif data_type == HC.CONTENT_TYPE_FILE_VIEWING_STATS:
                    
                    self._RecalcFileViewingStats()
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    self._RecalcTags()
                    
                
            
        elif len( data_types ) > 0:
            
            self._RecalcInternals()
            
        
    
    def _RecalcAfterMediaRemove( self ):
        
        MediaList._RecalcAfterMediaRemove( self )
        
        self._RecalcArchiveInbox()
        
    
    def _RecalcArchiveInbox( self ):
        
        self._archive = True in ( media.HasArchive() for media in self._sorted_media )
        self._inbox = True in ( media.HasInbox() for media in self._sorted_media )
        
    
    def _RecalcFileViewingStats( self ):
        
        preview_views = 0
        preview_viewtime = 0.0
        media_views = 0
        media_viewtime = 0.0
        
        for m in self._sorted_media:
            
            fvsm = m.GetFileViewingStatsManager()
            
            preview_views += fvsm.preview_views
            preview_viewtime += fvsm.preview_viewtime
            media_views += fvsm.media_views
            media_viewtime += fvsm.media_viewtime
            
        
        self._file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager( preview_views, preview_viewtime, media_views, media_viewtime )
        
    
    def _RecalcHashes( self ):
        
        MediaList._RecalcHashes( self )
        
        all_locations_managers = [ media.GetLocationsManager() for media in self._sorted_media ]
        
        current_to_timestamps = {}
        deleted_to_timestamps = {}
        
        for service_key in HG.client_controller.services_manager.GetServiceKeys( HC.FILE_SERVICES ):
            
            current_timestamps = [ timestamp for timestamp in ( locations_manager.GetCurrentTimestamp( service_key ) for locations_manager in all_locations_managers ) if timestamp is not None ]
            
            if len( current_timestamps ) > 0:
                
                current_to_timestamps[ service_key ] = max( current_timestamps )
                
            
            deleted_timestamps = [ timestamps for timestamps in ( locations_manager.GetDeletedTimestamps( service_key ) for locations_manager in all_locations_managers ) if timestamps is not None and timestamps[0] is not None ]
            
            if len( deleted_timestamps ) > 0:
                
                deleted_to_timestamps[ service_key ] = max( deleted_timestamps, key = lambda ts: ts[0] )
                
            
        
        pending = HydrusData.MassUnion( [ locations_manager.GetPending() for locations_manager in all_locations_managers ] )
        petitioned = HydrusData.MassUnion( [ locations_manager.GetPetitioned() for locations_manager in all_locations_managers ] )
        
        self._locations_manager = ClientMediaManagers.LocationsManager( current_to_timestamps, deleted_to_timestamps, pending, petitioned )
        
    
    def _RecalcInternals( self ):
        
        self._RecalcHashes()
        
        self._RecalcTags()
        
        self._RecalcArchiveInbox()
        
        self._size = sum( [ media.GetSize() for media in self._sorted_media ] )
        self._size_definite = not False in ( media.IsSizeDefinite() for media in self._sorted_media )
        
        duration_sum = sum( [ media.GetDuration() for media in self._sorted_media if media.HasDuration() ] )
        
        if duration_sum > 0: self._duration = duration_sum
        else: self._duration = None
        
        self._has_audio = True in ( media.HasAudio() for media in self._sorted_media )
        
        self._has_notes = True in ( media.HasNotes() for media in self._sorted_media )
        
        self._RecalcRatings()
        self._RecalcFileViewingStats()
        
    
    def _RecalcRatings( self ):
        
        # horrible compromise
        if len( self._sorted_media ) > 0:
            
            self._ratings_manager = self._sorted_media[0].GetRatingsManager()
            
        else:
            
            self._ratings_manager = ClientMediaManagers.RatingsManager( {} )
            
        
    
    def _RecalcTags( self ):
        
        tags_managers = [ m.GetTagsManager() for m in self._sorted_media ]
        
        self._tags_manager = ClientMediaManagers.TagsManager.MergeTagsManagers( tags_managers )
        
    
    def AddMedia( self, new_media ):
        
        MediaList.AddMedia( self, new_media )
        
        self._RecalcInternals()
        
    
    def DeletePending( self, service_key ):
        
        MediaList.DeletePending( self, service_key )
        
        self._RecalcInternals()
        
    
    def GetCurrentTimestamp( self, service_key: bytes ) -> typing.Optional[ int ]:
        
        return self._locations_manager.GetCurrentTimestamp( service_key )
        
    
    def GetDeletedTimestamps( self, service_key: bytes ) -> typing.Tuple[ typing.Optional[ int ], typing.Optional[ int ] ]:
        
        return self._locations_manager.GetDeletedTimestamps( service_key )
        
    
    def GetDisplayMedia( self ):
        
        first = self._GetFirst()
        
        if first is None:
            
            return None
            
        else:
            
            return first.GetDisplayMedia()
            
        
    
    def GetDuration( self ):
        
        return self._duration
        
    
    def GetFileViewingStatsManager( self ):
        
        return self._file_viewing_stats_manager
        
    
    def GetHash( self ):
        
        display_media = self.GetDisplayMedia()
        
        if display_media is None:
            
            return None
            
        else:
            
            return display_media.GetHash()
            
        
    
    def GetLocationsManager( self ): 
        
        return self._locations_manager
        
    
    def GetMime( self ):
        
        return HC.APPLICATION_HYDRUS_CLIENT_COLLECTION
        
    
    def GetNumInbox( self ):
        
        return sum( ( media.GetNumInbox() for media in self._sorted_media ) )
        
    
    def GetNumFrames( self ):
        
        num_frames = ( media.GetNumFrames() for media in self._sorted_media )
        
        return sum( ( nf for nf in num_frames if nf is not None ) )
        
    
    def GetNumWords( self ):
        
        num_words = ( media.GetNumWords() for media in self._sorted_media )
        
        return sum( ( nw for nw in num_words if nw is not None ) )
        
    
    def GetPrettyInfoLines( self ):
        
        size = HydrusData.ToHumanBytes( self._size )
        
        mime = HC.mime_string_lookup[ HC.APPLICATION_HYDRUS_CLIENT_COLLECTION ]
        
        info_string = size + ' ' + mime
        
        info_string += ' (' + HydrusData.ToHumanInt( self.GetNumFiles() ) + ' files)'
        
        return [ info_string ]
        
    
    def GetRatingsManager( self ):
        
        return self._ratings_manager
        
    
    def GetResolution( self ):
        
        if self._width is None:
            
            return ( 0, 0 )
            
        else:
            
            return ( self._width, self._height )
            
        
    
    def GetSingletonsTagsManagers( self ):
        
        tags_managers = [ m.GetTagsManager() for m in self._singleton_media ] 
        
        for m in self._collected_media: tags_managers.extend( m.GetSingletonsTagsManagers() )
        
        return tags_managers
        
    
    def GetSize( self ):
        
        return self._size
        
    
    def GetTagsManager( self ):
        
        return self._tags_manager
        
    
    def HasArchive( self ):
        
        return self._archive
        
    
    def HasAudio( self ):
        
        return self._has_audio
        
    
    def HasDuration( self ):
        
        return self._duration is not None
        
    
    def HasImages( self ):
        
        return True in ( media.HasImages() for media in self._sorted_media )
        
    
    def HasInbox( self ):
        
        return self._inbox
        
    
    def HasNotes( self ):
        
        return self._has_notes
        
    
    def IsCollection( self ):
        
        return True
        
    
    def IsImage( self ):
        
        return False
        
    
    def IsSizeDefinite( self ):
        
        return self._size_definite
        
    
    def RecalcInternals( self ):
        
        self._RecalcInternals()
        
    
    def ResetService( self, service_key ):
        
        MediaList.ResetService( self, service_key )
        
        self._RecalcInternals()
        
    
    def UpdateFileInfo( self, hashes_to_media_results ):
        
        for media in self._sorted_media:
            
            media.UpdateFileInfo( hashes_to_media_results )
            
        
        self._RecalcInternals()
        
    
class MediaSingleton( Media ):
    
    def __init__( self, media_result: ClientMediaResult.MediaResult ):
        
        Media.__init__( self )
        
        self._media_result = media_result
        
    
    def Duplicate( self ):
        
        return MediaSingleton( self._media_result.Duplicate() )
        
    
    def GetDisplayMedia( self ) -> 'MediaSingleton':
        
        return self
        
    
    def GetDuration( self ):
        
        return self._media_result.GetDuration()
        
    
    def GetFileViewingStatsManager( self ):
        
        return self._media_result.GetFileViewingStatsManager()
        
    
    def GetHash( self ):
        
        return self._media_result.GetHash()
        
    
    def GetHashId( self ):
        
        return self._media_result.GetHashId()
        
    
    def GetHashes( self, has_location = None, discriminant = None, not_uploaded_to = None, ordered = False ):
        
        if self.MatchesDiscriminant( has_location = has_location, discriminant = discriminant, not_uploaded_to = not_uploaded_to ):
            
            if ordered:
                
                return [ self._media_result.GetHash() ]
                
            else:
                
                return { self._media_result.GetHash() }
                
            
        else:
            
            if ordered:
                
                return []
                
            else:
                
                return set()
                
            
        
    
    def GetLocationsManager( self ):
        
        return self._media_result.GetLocationsManager()
        
    
    def GetMediaResult( self ): return self._media_result
    
    def GetMime( self ): return self._media_result.GetMime()
    
    def GetNotesManager( self ):
        
        return self._media_result.GetNotesManager()
        
    
    def GetNumFiles( self ): return 1
    
    def GetNumFrames( self ): return self._media_result.GetNumFrames()
    
    def GetNumInbox( self ):
        
        if self.HasInbox(): return 1
        else: return 0
        
    
    def GetNumWords( self ): return self._media_result.GetNumWords()
    
    def GetCurrentTimestamp( self, service_key ) -> typing.Optional[ int ]:
        
        return self._media_result.GetLocationsManager().GetCurrentTimestamp( service_key )
        
    
    def GetDeletedTimestamps( self, service_key: bytes ) -> typing.Tuple[ typing.Optional[ int ], typing.Optional[ int ] ]:
        
        return self._media_result.GetLocationsManager().GetDeletedTimestamps( service_key )
        
    
    def GetPrettyInfoLines( self ):
        
        file_info_manager = self._media_result.GetFileInfoManager()
        locations_manager = self._media_result.GetLocationsManager()
        
        ( hash_id, hash, size, mime, width, height, duration, num_frames, has_audio, num_words ) = file_info_manager.ToTuple()
        
        info_string = HydrusData.ToHumanBytes( size ) + ' ' + HC.mime_string_lookup[ mime ]
        
        if width is not None and height is not None:
            
            info_string += ' ({})'.format( HydrusData.ConvertResolutionToPrettyString( ( width, height ) ) )
            
        
        if duration is not None:
            
            info_string += ', ' + HydrusData.ConvertMillisecondsToPrettyTime( duration )
            
        
        if num_frames is not None:
            
            if duration is None or duration == 0 or num_frames == 0:
                
                framerate_insert = ''
                
            else:
                
                framerate_insert = ', {}fps'.format( round( num_frames / ( duration / 1000 ) ) )
                
            
            info_string += ' ({} frames{})'.format( HydrusData.ToHumanInt( num_frames ), framerate_insert )
            
        
        if has_audio:
            
            info_string += ', {}'.format( HG.client_controller.new_options.GetString( 'has_audio_label' ) )
            
        
        if num_words is not None: info_string += ' (' + HydrusData.ToHumanInt( num_words ) + ' words)'
        
        lines = [ info_string ]
        
        locations_manager = self._media_result.GetLocationsManager()
        
        current_service_keys = locations_manager.GetCurrent()
        deleted_service_keys = locations_manager.GetDeleted()
        
        local_file_services = HG.client_controller.services_manager.GetLocalMediaFileServices()
        
        current_local_file_services = [ service for service in local_file_services if service.GetServiceKey() in current_service_keys ]
        
        if len( current_local_file_services ) > 0:
            
            for local_file_service in current_local_file_services:
                
                timestamp = locations_manager.GetCurrentTimestamp( local_file_service.GetServiceKey() )
                
                lines.append( 'added to {} {}'.format( local_file_service.GetName(), ClientData.TimestampToPrettyTimeDelta( timestamp ) ) )
                
            
        elif CC.COMBINED_LOCAL_FILE_SERVICE_KEY in current_service_keys:
            
            timestamp = locations_manager.GetCurrentTimestamp( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
            lines.append( 'imported {}'.format( ClientData.TimestampToPrettyTimeDelta( timestamp ) ) )
            
        
        deleted_local_file_services = [ service for service in local_file_services if service.GetServiceKey() in deleted_service_keys ]
        
        if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in deleted_service_keys:
            
            ( timestamp, original_timestamp ) = locations_manager.GetDeletedTimestamps( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
            lines.append( 'deleted from this client {}'.format( ClientData.TimestampToPrettyTimeDelta( timestamp ) ) )
            
        elif len( deleted_local_file_services ) > 0:
            
            for local_file_service in deleted_local_file_services:
                
                ( timestamp, original_timestamp ) = locations_manager.GetDeletedTimestamps( local_file_service.GetServiceKey() )
                
                lines.append( 'removed from {} {}'.format( local_file_service.GetName(), ClientData.TimestampToPrettyTimeDelta( timestamp ) ) )
                
            
        
        if locations_manager.IsTrashed():
            
            lines.append( 'in the trash' )
            
        
        file_modified_timestamp = locations_manager.GetFileModifiedTimestamp()
        
        if file_modified_timestamp is not None:
            
            lines.append( 'file modified: {}'.format( ClientData.TimestampToPrettyTimeDelta( file_modified_timestamp ) ) )
            
        
        for service_key in current_service_keys.intersection( HG.client_controller.services_manager.GetServiceKeys( HC.REMOTE_FILE_SERVICES ) ):
            
            timestamp = locations_manager.GetCurrentTimestamp( service_key )
            
            try:
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service_type = service.GetServiceType()
            
            if service_type == HC.IPFS:
                
                status = 'pinned '
                
            else:
                
                status = 'uploaded '
                
            
            lines.append( status + 'to ' + service.GetName() + ' ' + ClientData.TimestampToPrettyTimeDelta( timestamp ) )
            
        
        return lines
        
    
    def GetRatingsManager( self ): return self._media_result.GetRatingsManager()
    
    def GetResolution( self ):
        
        ( width, height ) = self._media_result.GetResolution()
        
        if width is None:
            
            return ( 0, 0 )
            
        else:
            
            return ( width, height )
            
        
    
    def GetSize( self ):
        
        size = self._media_result.GetSize()
        
        if size is None: return 0
        else: return size
        
    
    def GetTagsManager( self ):
        
        return self._media_result.GetTagsManager()
        
    
    def GetTitleString( self ):
        
        new_options = HG.client_controller.new_options
        
        tag_summary_generator = new_options.GetTagSummaryGenerator( 'media_viewer_top' )
        
        tags = self.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
        
        if len( tags ) == 0:
            
            return ''
            
        
        summary = tag_summary_generator.GenerateSummary( tags )
        
        return summary
        
    
    def HasAnyOfTheseHashes( self, hashes ):
        
        return self._media_result.GetHash() in hashes
        
    
    def HasArchive( self ):
        
        return not self._media_result.GetInbox()
        
    
    def HasAudio( self ):
        
        return self._media_result.HasAudio()
        
    
    def HasDuration( self ):
        
        duration = self._media_result.GetDuration()
        
        return duration is not None and duration > 0
        
    
    def HasImages( self ): return self.IsImage()
    
    def HasInbox( self ): return self._media_result.GetInbox()
    
    def HasNotes( self ):
        
        return self._media_result.HasNotes()
        
    
    def IsCollection( self ): return False
    
    def IsImage( self ):
        
        return self._media_result.GetMime() in HC.IMAGES
        
    
    def IsSizeDefinite( self ): return self._media_result.GetSize() is not None
    
    def IsStaticImage( self ):
        
        return self._media_result.IsStaticImage()
        
    
    def MatchesDiscriminant( self, has_location = None, discriminant = None, not_uploaded_to = None ):
        
        if discriminant is not None:
            
            inbox = self._media_result.GetInbox()
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if discriminant == CC.DISCRIMINANT_INBOX:
                
                p = inbox
                
            elif discriminant == CC.DISCRIMINANT_ARCHIVE:
                
                p = not inbox
                
            elif discriminant == CC.DISCRIMINANT_LOCAL:
                
                p = locations_manager.IsLocal()
                
            elif discriminant == CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH:
                
                p = locations_manager.IsLocal() and not locations_manager.IsTrashed()
                
            elif discriminant == CC.DISCRIMINANT_NOT_LOCAL:
                
                p = not locations_manager.IsLocal()
                
            elif discriminant == CC.DISCRIMINANT_DOWNLOADING:
                
                p = locations_manager.IsDownloading()
                
            
            if not p:
                
                return False
                
            
        
        if has_location is not None:
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if has_location not in locations_manager.GetCurrent():
                
                return False
                
            
        
        if not_uploaded_to is not None:
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if not_uploaded_to in locations_manager.GetCurrent():
                
                return False
                
            
        
        return True
        
    
    def UpdateFileInfo( self, hashes_to_media_results ):
        
        hash = self.GetHash()
        
        if hash in hashes_to_media_results:
            
            media_result = hashes_to_media_results[ hash ]
            
            self._media_result = media_result
            
        
    
class MediaSort( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_SORT
    SERIALISABLE_NAME = 'Media Sort'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, sort_type = None, sort_order = None ):
        
        if sort_type is None:
            
            sort_type = ( 'system', CC.SORT_FILES_BY_FILESIZE )
            
        
        if sort_order is None:
            
            sort_order = CC.SORT_ASC
            
        
        ( sort_metatype, sort_data ) = sort_type
        
        if sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            sort_data = ( tuple( namespaces ), tag_display_type )
            
            sort_type = ( sort_metatype, sort_data )
            
        
        self.sort_type = sort_type
        self.sort_order = sort_order
        
    
    def _GetSerialisableInfo( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            serialisable_sort_data = sort_data
            
        elif sort_metatype == 'namespaces':
            
            serialisable_sort_data = sort_data
            
        elif sort_metatype == 'rating':
            
            service_key = sort_data
            
            serialisable_sort_data = service_key.hex()
            
        
        return ( sort_metatype, serialisable_sort_data, self.sort_order )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( sort_metatype, serialisable_sort_data, self.sort_order ) = serialisable_info
        
        if sort_metatype == 'system':
            
            sort_data = serialisable_sort_data
            
        elif sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = serialisable_sort_data
            
            sort_data = ( tuple( namespaces ), tag_display_type )
            
        elif sort_metatype == 'rating':
            
            sort_data = bytes.fromhex( serialisable_sort_data )
            
        
        self.sort_type = ( sort_metatype, sort_data )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( sort_metatype, serialisable_sort_data, sort_order ) = old_serialisable_info
            
            if sort_metatype == 'namespaces':
                
                namespaces = serialisable_sort_data
                serialisable_sort_data = ( namespaces, ClientTags.TAG_DISPLAY_ACTUAL )
                
            
            new_serialisable_info = ( sort_metatype, serialisable_sort_data, sort_order )
            
            return ( 2, new_serialisable_info )
            
        
    
    def CanAsc( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            if sort_data in ( CC.SORT_FILES_BY_MIME, CC.SORT_FILES_BY_RANDOM ):
                
                return False
                
            
        
        return True
        
    
    def GetNamespaces( self ):
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        if sort_metadata == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            return list( namespaces )
            
        else:
            
            return []
            
        
    
    def GetSortKeyAndReverse( self, file_service_key ):
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        def deal_with_none( x ):
            
            if x is None: return -1
            else: return x
            
        
        if sort_metadata == 'system':
            
            if sort_data == CC.SORT_FILES_BY_RANDOM:
                
                def sort_key( x ):
                    
                    return random.random()
                    
                
            elif sort_data == CC.SORT_FILES_BY_APPROX_BITRATE:
                
                def sort_key( x ):
                    
                    # videos > images > pdfs
                    # heavy vids first, heavy images first
                    
                    duration = x.GetDuration()
                    num_frames = x.GetNumFrames()
                    size = x.GetSize()
                    resolution = x.GetResolution()
                    
                    if duration is None or duration == 0:
                        
                        if size is None or size == 0:
                            
                            duration_bitrate = -1
                            frame_bitrate = -1
                            
                        else:
                            
                            duration_bitrate = 0
                            
                            if resolution is None:
                                
                                frame_bitrate = 0
                                
                            else:
                                
                                ( width, height ) = x.GetResolution()
                                
                                num_pixels = width * height
                                
                                if size is None or size == 0 or num_pixels == 0:
                                    
                                    frame_bitrate = -1
                                    
                                else:
                                    
                                    frame_bitrate = size / num_pixels
                                    
                                
                            
                        
                    else:
                        
                        if size is None or size == 0:
                            
                            duration_bitrate = -1
                            frame_bitrate = -1
                            
                        else:
                            
                            duration_bitrate = size / duration
                            
                            if num_frames is None or num_frames == 0:
                                
                                frame_bitrate = 0
                                
                            else:
                                
                                frame_bitrate = duration_bitrate / num_frames
                                
                            
                        
                    
                    return ( duration_bitrate, frame_bitrate )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FILESIZE:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetSize() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_DURATION:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetDuration() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FRAMERATE:
                
                def sort_key( x ):
                    
                    num_frames = x.GetNumFrames()
                    
                    if num_frames is None or num_frames == 0:
                        
                        return -1
                        
                    
                    duration = x.GetDuration()
                    
                    if duration is None or duration == 0:
                        
                        return -1
                        
                    
                    return num_frames / duration
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_COLLECTION_FILES:
                
                def sort_key( x ):
                    
                    return ( x.GetNumFiles(), isinstance( x, MediaCollection ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_FRAMES:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetNumFrames() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_HAS_AUDIO:
                
                def sort_key( x ):
                    
                    return - deal_with_none( x.HasAudio() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_IMPORT_TIME:
                
                file_service = HG.client_controller.services_manager.GetService( file_service_key )
                
                file_service_type = file_service.GetServiceType()
                
                if file_service_type == HC.LOCAL_FILE_DOMAIN:
                    
                    file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                    
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetCurrentTimestamp( file_service_key ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetLocationsManager().GetFileModifiedTimestamp() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_HEIGHT:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetResolution()[1] )
                    
                
            elif sort_data == CC.SORT_FILES_BY_WIDTH:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetResolution()[0] )
                    
                
            elif sort_data == CC.SORT_FILES_BY_RATIO:
                
                def sort_key( x ):
                    
                    ( width, height ) = x.GetResolution()
                    
                    if width is None or height is None or width == 0 or height == 0:
                        
                        return -1
                        
                    else:
                        
                        return width / height
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_PIXELS:
                
                def sort_key( x ):
                    
                    ( width, height ) = x.GetResolution()
                    
                    if width is None or height is None:
                        
                        return -1
                        
                    else:
                        
                        return width * height
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_TAGS:
                
                def sort_key( x ):
                    
                    tags_manager = x.GetTagsManager()
                    
                    return len( tags_manager.GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_MIME:
                
                def sort_key( x ):
                    
                    return x.GetMime()
                    
                
            elif sort_data == CC.SORT_FILES_BY_MEDIA_VIEWS:
                
                def sort_key( x ):
                    
                    fvsm = x.GetFileViewingStatsManager()
                    
                    # do not do viewtime as a secondary sort here, to allow for user secondary sort to help out
                    
                    return fvsm.media_views
                    
                
            elif sort_data == CC.SORT_FILES_BY_MEDIA_VIEWTIME:
                
                def sort_key( x ):
                    
                    fvsm = x.GetFileViewingStatsManager()
                    
                    # do not do views as a secondary sort here, to allow for user secondary sort to help out
                    
                    return fvsm.media_viewtime
                    
                
            
        elif sort_metadata == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            def sort_key( x ):
                
                x_tags_manager = x.GetTagsManager()
                
                return [ x_tags_manager.GetComparableNamespaceSlice( ( namespace, ), tag_display_type ) for namespace in namespaces ]
                
            
        elif sort_metadata == 'rating':
            
            service_key = sort_data
            
            def sort_key( x ):
                
                x_ratings_manager = x.GetRatingsManager()
                
                rating = deal_with_none( x_ratings_manager.GetRating( service_key ) )
                
                return rating
                
            
        
        reverse = self.sort_order == CC.SORT_DESC
        
        return ( sort_key, reverse )
        
    
    def GetSortOrderStrings( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            sort_string_lookup = {}
            
            sort_string_lookup[ CC.SORT_FILES_BY_APPROX_BITRATE ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FILESIZE ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_DURATION ] = ( 'shortest first', 'longest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FRAMERATE ] = ( 'slowest first', 'fastest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_COLLECTION_FILES ] = ( 'fewest first', 'most first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_FRAMES ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_HAS_AUDIO ] = ( 'audio first', 'silent first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_IMPORT_TIME ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_MIME ] = ( 'filetype', 'filetype', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_RANDOM ] = ( 'random', 'random', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_WIDTH ] = ( 'slimmest first', 'widest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_HEIGHT ] = ( 'shortest first', 'tallest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_RATIO ] = ( 'tallest first', 'widest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_PIXELS ] = ( 'ascending', 'descending', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_TAGS ] = ( 'ascending', 'descending', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_MEDIA_VIEWS ] = ( 'ascending', 'descending', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_MEDIA_VIEWTIME ] = ( 'ascending', 'descending', CC.SORT_DESC )
            
            return sort_string_lookup[ sort_data ]
            
        elif sort_metatype == 'namespaces':
            
            return ( 'a-z', 'z-a', CC.SORT_ASC )
            
        else:
            
            return ( 'ascending', 'descending', CC.SORT_DESC )
            
        
    
    def GetSortTypeString( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        sort_string = 'sort by '
        
        if sort_metatype == 'system':
            
            sort_string += CC.sort_type_string_lookup[ sort_data ]
            
        elif sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            sort_string += 'tags: ' + '-'.join( namespaces )
            
        elif sort_metatype == 'rating':
            
            service_key = sort_data
            
            try:
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
                name = service.GetName()
                
            except HydrusExceptions.DataMissing:
                
                name = 'unknown service'
                
            
            sort_string += 'rating: {}'.format( name )
            
        
        return sort_string
        
    
    def ToString( self ):
        
        sort_type_string = self.GetSortTypeString()
        
        ( asc_string, desc_string, sort_gumpf ) = self.GetSortOrderStrings()
        
        sort_order_string = asc_string if self.sort_order == CC.SORT_ASC else desc_string
        
        return '{}, {}'.format( sort_type_string, sort_order_string )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_SORT ] = MediaSort

class SortedList( object ):
    
    def __init__( self, initial_items = None ):
        
        if initial_items is None:
            
            initial_items = []
            
        
        self._sort_key = None
        self._sort_reverse = False
        
        self._sorted_list = list( initial_items )
        
        self._items_to_indices = {}
        self._indices_dirty = True
        
    
    def __contains__( self, item ):
        
        if self._indices_dirty:
            
            self._RecalcIndices()
            
        
        return self._items_to_indices.__contains__( item )
        
    
    def __getitem__( self, value ):
        
        return self._sorted_list.__getitem__( value )
        
    
    def __iter__( self ):
        
        return iter( self._sorted_list )
        
    
    def __len__( self ):
        
        return len( self._sorted_list )
        
    
    def _DirtyIndices( self ):
        
        self._indices_dirty = True
        
        self._items_to_indices = {}
        
    
    def _RecalcIndices( self ):
        
        self._items_to_indices = { item : index for ( index, item ) in enumerate( self._sorted_list ) }
        
        self._indices_dirty = False
        
    
    def append_items( self, items ):
        
        if self._indices_dirty is None:
            
            self._RecalcIndices()
            
        
        for ( i, item ) in enumerate( items, start = len( self._sorted_list ) ):
            
            self._items_to_indices[ item ] = i
            
        
        self._sorted_list.extend( items )
        
    
    def index( self, item ):
        
        if self._indices_dirty:
            
            self._RecalcIndices()
            
        
        try:
            
            result = self._items_to_indices[ item ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing()
            
        
        return result
        
    
    def insert_items( self, items ):
        
        self.append_items( items )
        
        self.sort()
        
    
    def remove_items( self, items ):
        
        deletee_indices = [ self.index( item ) for item in items ]
        
        deletee_indices.sort( reverse = True )
        
        for index in deletee_indices:
            
            del self._sorted_list[ index ]
            
        
        self._DirtyIndices()
        
    
    def sort( self, sort_key = None, reverse = False ):
        
        if sort_key is None:
            
            sort_key = self._sort_key
            reverse = self._sort_reverse
            
        else:
            
            self._sort_key = sort_key
            self._sort_reverse = reverse
            
        
        self._sorted_list.sort( key = sort_key, reverse = reverse )
        
        self._DirtyIndices()
        
    
