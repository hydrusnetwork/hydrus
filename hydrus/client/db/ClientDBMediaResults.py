import collections
import collections.abc
import itertools
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientTime
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesInbox
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBFilesTimestamps
from hydrus.client.db import ClientDBFilesViewingStats
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBNotesMap
from hydrus.client.db import ClientDBRatings
from hydrus.client.db import ClientDBServicePaths
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.db import ClientDBTagDisplay
from hydrus.client.db import ClientDBURLMap
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.media import ClientMediaResultCache
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

class ClientDBMediaResults( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_tags_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalTags,
        modules_files_metadata_basic: ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_service_paths: ClientDBServicePaths.ClientDBServicePaths,
        modules_files_timestamps: ClientDBFilesTimestamps.ClientDBFilesTimestamps,
        modules_url_map: ClientDBURLMap.ClientDBURLMap,
        modules_files_viewing_stats: ClientDBFilesViewingStats.ClientDBFilesViewingStats,
        modules_ratings: ClientDBRatings.ClientDBRatings,
        modules_notes_map: ClientDBNotesMap.ClientDBNotesMap,
        modules_files_inbox: ClientDBFilesInbox.ClientDBFilesInbox,
        modules_mappings_storage: ClientDBMappingsStorage.ClientDBMappingsStorage,
        modules_tag_display: ClientDBTagDisplay.ClientDBTagDisplay,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles
    ):
        
        self.modules_services = modules_services
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_tags_local_cache = modules_tags_local_cache
        self.modules_files_metadata_basic = modules_files_metadata_basic
        self.modules_files_storage = modules_files_storage
        self.modules_service_paths = modules_service_paths
        self.modules_files_timestamps = modules_files_timestamps
        self.modules_url_map = modules_url_map
        self.modules_files_viewing_stats = modules_files_viewing_stats
        self.modules_ratings = modules_ratings
        self.modules_notes_map = modules_notes_map
        self.modules_files_inbox = modules_files_inbox
        self.modules_mappings_storage = modules_mappings_storage
        self.modules_tag_display = modules_tag_display
        self.modules_similar_files = modules_similar_files
        
        self._weakref_media_result_cache = ClientMediaResultCache.MediaResultCache()
        
        super().__init__( 'client media results', cursor )
        
    
    def ClearMediaResultCache( self ):
        
        self._weakref_media_result_cache = ClientMediaResultCache.MediaResultCache()
        
    
    def DropMediaResults( self, hash_ids_to_hashes ):
        
        hashes_that_need_refresh = set()
        
        for ( hash_id, hash ) in hash_ids_to_hashes.items():
            
            if self._weakref_media_result_cache.HasFile( hash_id ):
                
                self._weakref_media_result_cache.DropMediaResult( hash_id, hash )
                
                hashes_that_need_refresh.add( hash )
                
            
        
        return hashes_that_need_refresh
        
    
    def ForceRefreshFileInfoManagers( self, hash_ids_to_hashes: dict ):
        
        hash_ids = list( hash_ids_to_hashes.keys() )
        
        ( cached_media_results, missing_hash_ids ) = self._weakref_media_result_cache.GetMediaResultsAndMissing( hash_ids )
        
        cached_hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in cached_media_results }
        
        cached_hash_ids = list( cached_hash_ids_to_media_results.keys() )
        
        with self._MakeTemporaryIntegerTable( cached_hash_ids, 'hash_id' ) as temp_table_name:
            
            self._AnalyzeTempTable( temp_table_name )
            
            file_info_managers = self.GenerateFileInfoManagers( cached_hash_ids, temp_table_name )
            
        
        for file_info_manager in file_info_managers:
            
            cached_hash_ids_to_media_results[ file_info_manager.hash_id ].SetFileInfoManager( file_info_manager )
            
        
        updated_hashes = [ media_result.GetHash() for media_result in cached_hash_ids_to_media_results.values() ]
        
        CG.client_controller.pub( 'notify_files_need_cache_clear', updated_hashes )
        CG.client_controller.pub( 'notify_files_need_redraw', updated_hashes )
        
    
    def ForceRefreshFileModifiedTimestamps( self, hash_ids_to_hashes: dict ):
        
        hash_ids = list( hash_ids_to_hashes.keys() )
        
        ( cached_media_results, missing_hash_ids ) = self._weakref_media_result_cache.GetMediaResultsAndMissing( hash_ids )
        
        cached_hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in cached_media_results }
        
        for media_result in cached_hash_ids_to_media_results.values():
            
            result = self.modules_files_timestamps.GetTimestampMS( media_result.GetHashId(), ClientTime.TimestampData.STATICSimpleStub( HC.TIMESTAMP_TYPE_MODIFIED_FILE ) )
            
            media_result.GetTimesManager().SetFileModifiedTimestampMS( result )
            
        
        updated_hashes = [ media_result.GetHash() for media_result in cached_hash_ids_to_media_results.values() ]
        
        CG.client_controller.pub( 'notify_files_need_redraw', updated_hashes )
        
    
    def GenerateFileInfoManagers( self, hash_ids: collections.abc.Collection[ int ], hash_ids_table_name ) -> list[ ClientMediaManagers.FileInfoManager ]:
        
        hash_ids_to_hashes = self.modules_hashes_local_cache.GetHashIdsToHashes( hash_ids = hash_ids )
        
        # temp hashes to metadata
        hash_ids_to_file_info_managers = { hash_id : ClientMediaManagers.FileInfoManager( hash_id, hash_ids_to_hashes[ hash_id ], size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) for ( hash_id, size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) in self._Execute( 'SELECT * FROM {} CROSS JOIN files_info USING ( hash_id );'.format( hash_ids_table_name ) ) }
        
        hash_ids_to_pixel_hashes = self.modules_similar_files.GetHashIdsToPixelHashes( hash_ids_table_name )
        hash_ids_to_blurhashes = self.modules_files_metadata_basic.GetHashIdsToBlurhashes( hash_ids_table_name )
        hash_ids_to_forced_filetypes = self.modules_files_metadata_basic.GetHashIdsToForcedFiletypes( hash_ids_table_name )
        has_transparency_hash_ids = self.modules_files_metadata_basic.GetHasTransparencyHashIds( hash_ids_table_name )
        has_exif_hash_ids = self.modules_files_metadata_basic.GetHasEXIFHashIds( hash_ids_table_name )
        has_human_readable_embedded_metadata_hash_ids = self.modules_files_metadata_basic.GetHasHumanReadableEmbeddedMetadataHashIds( hash_ids_table_name )
        has_icc_profile_hash_ids = self.modules_files_metadata_basic.GetHasICCProfileHashIds( hash_ids_table_name )
        
        # build it
        
        file_info_managers = []
        
        for hash_id in hash_ids:
            
            if hash_id in hash_ids_to_file_info_managers:
                
                file_info_manager = hash_ids_to_file_info_managers[ hash_id ]
                
            else:
                
                hash = hash_ids_to_hashes[ hash_id ]
                
                file_info_manager = ClientMediaManagers.FileInfoManager( hash_id, hash )
                
            
            file_info_manager.pixel_hash = hash_ids_to_pixel_hashes.get( hash_id, None )
            file_info_manager.blurhash = hash_ids_to_blurhashes.get( hash_id, None )
            file_info_manager.has_transparency = hash_id in has_transparency_hash_ids
            file_info_manager.has_exif = hash_id in has_exif_hash_ids
            file_info_manager.has_human_readable_embedded_metadata = hash_id in has_human_readable_embedded_metadata_hash_ids
            file_info_manager.has_icc_profile = hash_id in has_icc_profile_hash_ids
            
            forced_mime = hash_ids_to_forced_filetypes.get( hash_id, None )
            
            if forced_mime is not None:
                
                file_info_manager.original_mime = file_info_manager.mime
                file_info_manager.mime = forced_mime
                
            
            file_info_managers.append( file_info_manager )
            
        
        return file_info_managers
        
    
    def GetFileInfoManagers( self, hash_ids: collections.abc.Collection[ int ], sorted = False ) -> list[ ClientMediaManagers.FileInfoManager ]:
        
        ( cached_media_results, missing_hash_ids ) = self._weakref_media_result_cache.GetMediaResultsAndMissing( hash_ids )
        
        file_info_managers = [ media_result.GetFileInfoManager() for media_result in cached_media_results ]
        
        if len( missing_hash_ids ) > 0:
            
            with self._MakeTemporaryIntegerTable( missing_hash_ids, 'hash_id' ) as temp_table_name:
                
                missing_file_info_managers = self.GenerateFileInfoManagers( missing_hash_ids, temp_table_name )
                
            
            file_info_managers.extend( missing_file_info_managers )
            
        
        if sorted:
            
            if len( hash_ids ) > len( file_info_managers ):
                
                hash_ids = HydrusData.DedupeList( hash_ids )
                
            
            hash_ids_to_file_info_managers = { file_info_manager.hash_id : file_info_manager for file_info_manager in file_info_managers }
            
            file_info_managers = [ hash_ids_to_file_info_managers[ hash_id ] for hash_id in hash_ids if hash_id in hash_ids_to_file_info_managers ]
            
        
        return file_info_managers
        
    
    def GetFileInfoManagersFromHashes( self, hashes: collections.abc.Collection[ bytes ], sorted: bool = False ) -> list[ ClientMediaManagers.FileInfoManager ]:
        
        query_hash_ids = set( self.modules_hashes_local_cache.GetHashIds( hashes ) )
        
        file_info_managers = self.GetFileInfoManagers( query_hash_ids )
        
        if sorted:
            
            if len( hashes ) > len( query_hash_ids ):
                
                hashes = HydrusData.DedupeList( hashes )
                
            
            hashes_to_file_info_managers = { file_info_manager.hash : file_info_manager for file_info_manager in file_info_managers }
            
            file_info_managers = [ hashes_to_file_info_managers[ hash ] for hash in hashes if hash in hashes_to_file_info_managers ]
            
        
        return file_info_managers
        
    
    def GetForceRefreshTagsManagers( self, hash_ids, hash_ids_to_current_file_service_ids = None ):
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_table_name:
            
            self._AnalyzeTempTable( temp_table_name )
            
            return self.GetForceRefreshTagsManagersWithTableHashIds( hash_ids, temp_table_name, hash_ids_to_current_file_service_ids = hash_ids_to_current_file_service_ids )
            
        
    
    def GetForceRefreshTagsManagersWithTableHashIds( self, hash_ids, hash_ids_table_name, hash_ids_to_current_file_service_ids = None ) -> dict[ int, ClientMediaManagers.TagsManager ]:
        
        if hash_ids_to_current_file_service_ids is None:
            
            hash_ids_to_current_file_service_ids = self.modules_files_storage.GetHashIdsToCurrentServiceIds( hash_ids_table_name )
            
        
        common_file_service_ids_to_hash_ids = self.modules_files_storage.GroupHashIdsByTagCachedFileServiceId( hash_ids, hash_ids_table_name, hash_ids_to_current_file_service_ids = hash_ids_to_current_file_service_ids )
        
        #
        
        tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        
        storage_tag_data = []
        display_tag_data = []
        
        for ( common_file_service_id, batch_of_hash_ids ) in common_file_service_ids_to_hash_ids.items():
            
            if len( batch_of_hash_ids ) == len( hash_ids ):
                
                ( batch_of_storage_tag_data, batch_of_display_tag_data ) = self.GetForceRefreshTagsManagersWithTableHashIdsTagData( common_file_service_id, tag_service_ids, hash_ids_table_name )
                
            else:
                
                with self._MakeTemporaryIntegerTable( batch_of_hash_ids, 'hash_id' ) as temp_batch_hash_ids_table_name:
                    
                    ( batch_of_storage_tag_data, batch_of_display_tag_data ) = self.GetForceRefreshTagsManagersWithTableHashIdsTagData( common_file_service_id, tag_service_ids, temp_batch_hash_ids_table_name )
                    
                
            
            storage_tag_data.extend( batch_of_storage_tag_data )
            display_tag_data.extend( batch_of_display_tag_data )
            
        
        seen_tag_ids = { tag_id for ( hash_id, ( tag_service_id, status, tag_id ) ) in storage_tag_data }
        seen_tag_ids.update( ( tag_id for ( hash_id, ( tag_service_id, status, tag_id ) ) in display_tag_data ) )
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = seen_tag_ids )
        
        service_ids_to_service_keys = self.modules_services.GetServiceIdsToServiceKeys()
        
        hash_ids_to_raw_storage_tag_data = HydrusData.BuildKeyToListDict( storage_tag_data )
        hash_ids_to_raw_display_tag_data = HydrusData.BuildKeyToListDict( display_tag_data )
        
        hash_ids_to_tag_managers = {}
        
        for hash_id in hash_ids:
            
            # service_id, status, tag_id
            raw_storage_tag_data = hash_ids_to_raw_storage_tag_data[ hash_id ]
            
            # service_id -> ( status, tag )
            service_ids_to_storage_tag_data = HydrusData.BuildKeyToListDict( ( ( tag_service_id, ( status, tag_ids_to_tags[ tag_id ] ) ) for ( tag_service_id, status, tag_id ) in raw_storage_tag_data ) )
            
            service_keys_to_statuses_to_storage_tags = collections.defaultdict(
                HydrusData.default_dict_set,
                { service_ids_to_service_keys[ tag_service_id ] : HydrusData.BuildKeyToSetDict( status_and_tag ) for ( tag_service_id, status_and_tag ) in service_ids_to_storage_tag_data.items() }
            )
            
            # service_id, status, tag_id
            raw_display_tag_data = hash_ids_to_raw_display_tag_data[ hash_id ]
            
            # service_id -> ( status, tag )
            service_ids_to_display_tag_data = HydrusData.BuildKeyToListDict( ( ( tag_service_id, ( status, tag_ids_to_tags[ tag_id ] ) ) for ( tag_service_id, status, tag_id ) in raw_display_tag_data ) )
            
            service_keys_to_statuses_to_display_tags = collections.defaultdict(
                HydrusData.default_dict_set,
                { service_ids_to_service_keys[ tag_service_id ] : HydrusData.BuildKeyToSetDict( status_and_tag ) for ( tag_service_id, status_and_tag ) in service_ids_to_display_tag_data.items() }
            )
            
            tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_storage_tags, service_keys_to_statuses_to_display_tags )
            
            hash_ids_to_tag_managers[ hash_id ] = tags_manager
            
        
        return hash_ids_to_tag_managers
        
    
    def GetForceRefreshTagsManagersWithTableHashIdsTagData( self, common_file_service_id, tag_service_ids, hash_ids_table_name ) -> tuple:
        
        storage_tag_data = []
        display_tag_data = []
        
        for tag_service_id in tag_service_ids:
            
            statuses_to_table_names = self.modules_mappings_storage.GetFastestStorageMappingTableNames( common_file_service_id, tag_service_id )
            
            for ( status, mappings_table_name ) in statuses_to_table_names.items():
                
                # temp hashes to mappings
                storage_tag_data.extend( ( hash_id, ( tag_service_id, status, tag_id ) ) for ( hash_id, tag_id ) in self._Execute( 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, mappings_table_name ) ) )
                
            
            if common_file_service_id != self.modules_services.combined_file_service_id:
                
                ( cache_current_display_mappings_table_name, cache_pending_display_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificDisplayMappingsCacheTableNames( common_file_service_id, tag_service_id )
                
                # temp hashes to mappings
                display_tag_data.extend( ( hash_id, ( tag_service_id, HC.CONTENT_STATUS_CURRENT, tag_id ) ) for ( hash_id, tag_id ) in self._Execute( 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, cache_current_display_mappings_table_name ) ) )
                display_tag_data.extend( ( hash_id, ( tag_service_id, HC.CONTENT_STATUS_PENDING, tag_id ) ) for ( hash_id, tag_id ) in self._Execute( 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, cache_pending_display_mappings_table_name ) ) )
                
            
        
        if common_file_service_id == self.modules_services.combined_file_service_id:
            
            # this is likely a 'all known files' query, which means we are in deep water without a cache
            # time to compute manually, which is semi hell mode, but not dreadful
            
            current_and_pending_storage_tag_data = [ ( hash_id, ( tag_service_id, status, tag_id ) ) for ( hash_id, ( tag_service_id, status, tag_id ) ) in storage_tag_data if status in ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) ]
            
            seen_service_ids_to_seen_tag_ids = HydrusData.BuildKeyToSetDict( ( ( tag_service_id, tag_id ) for ( hash_id, ( tag_service_id, status, tag_id ) ) in current_and_pending_storage_tag_data ) )
            
            seen_service_ids_to_tag_ids_to_implied_tag_ids = { tag_service_id : self.modules_tag_display.GetTagsToImplies( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, tag_ids ) for ( tag_service_id, tag_ids ) in seen_service_ids_to_seen_tag_ids.items() }
            
            display_tag_data = []
            
            for ( hash_id, ( tag_service_id, status, tag_id ) ) in current_and_pending_storage_tag_data:
                
                display_tag_data.extend( ( ( hash_id, ( tag_service_id, status, implied_tag_id ) ) for implied_tag_id in seen_service_ids_to_tag_ids_to_implied_tag_ids[ tag_service_id ][ tag_id ] ) )
                
            
        
        return ( storage_tag_data, display_tag_data )
        
    
    def GetMediaResult( self, hash_id: int ) -> ClientMediaResult.MediaResult:
        
        return self.GetMediaResults( ( hash_id, ) )[0]
        
    
    def GetMediaResults( self, hash_ids: collections.abc.Collection[ int ], sorted = False ) -> list[ ClientMediaResult.MediaResult ]:
        
        ( cached_media_results, missing_hash_ids ) = self._weakref_media_result_cache.GetMediaResultsAndMissing( hash_ids )
        
        if len( missing_hash_ids ) > 0:
            
            # get first detailed results
            
            with self._MakeTemporaryIntegerTable( missing_hash_ids, 'hash_id' ) as temp_table_name:
                
                # everything here is temp hashes to metadata
                
                file_info_managers = self.GenerateFileInfoManagers( missing_hash_ids, temp_table_name )
                
                hash_ids_to_file_info_managers = { file_info_manager.hash_id : file_info_manager for file_info_manager in file_info_managers }
                
                (
                    hash_ids_to_current_file_service_ids_to_timestamps_ms,
                    hash_ids_to_deleted_file_service_ids_to_timestamps_ms,
                    hash_ids_to_deleted_file_service_ids_to_previously_imported_timestamps_ms,
                    hash_ids_to_pending_file_service_ids,
                    hash_ids_to_petitioned_file_service_ids
                ) = self.modules_files_storage.GetHashIdsToServiceInfoDicts( temp_table_name )
                
                hash_ids_to_current_file_service_ids = { hash_id : list( file_service_ids_to_timestamps_ms.keys() ) for ( hash_id, file_service_ids_to_timestamps_ms ) in hash_ids_to_current_file_service_ids_to_timestamps_ms.items() }
                
                hash_ids_to_tags_managers = self.GetForceRefreshTagsManagersWithTableHashIds( missing_hash_ids, temp_table_name, hash_ids_to_current_file_service_ids = hash_ids_to_current_file_service_ids )
                
                # TODO: it is a little tricky, but it would be nice to have 'gettimestampmanagers' and 'getlocationsmanagers' here
                # don't forget that timestamp is held by both the media result and the locations manager, so either give it to location manager entirely for KISS or have another think
                
                hash_ids_to_half_initialised_timestamp_managers = self.modules_files_timestamps.GetHashIdsToHalfInitialisedTimesManagers( missing_hash_ids, temp_table_name )
                
                hash_ids_to_urls = self.modules_url_map.GetHashIdsToURLs( hash_ids_table_name = temp_table_name )
                
                hash_ids_to_service_ids_and_filenames = self.modules_service_paths.GetHashIdsToServiceIdsAndFilenames( temp_table_name )
                
                hash_ids_to_local_file_deletion_reasons = self.modules_files_storage.GetHashIdsToFileDeletionReasons( temp_table_name )
                
                hash_ids_to_file_viewing_stats = self.modules_files_viewing_stats.GetHashIdsToFileViewingStatsRows( temp_table_name )
                
                hash_ids_to_local_ratings = self.modules_ratings.GetHashIdsToRatings( temp_table_name )
                
                hash_ids_to_names_and_notes = self.modules_notes_map.GetHashIdsToNamesAndNotes( temp_table_name )
                
            
            # build it
            
            service_ids_to_service_keys = self.modules_services.GetServiceIdsToServiceKeys()
            
            missing_media_results = []
            
            for hash_id in missing_hash_ids:
                
                file_info_manager = hash_ids_to_file_info_managers[ hash_id ]
                tags_manager = hash_ids_to_tags_managers[ hash_id ]
                
                #
                
                current_file_service_keys_to_timestamps_ms = { service_ids_to_service_keys[ service_id ] : timestamp_ms for ( service_id, timestamp_ms ) in hash_ids_to_current_file_service_ids_to_timestamps_ms[ hash_id ].items() }
                
                deleted_file_service_keys_to_timestamps_ms = { service_ids_to_service_keys[ service_id ] : timestamp_ms for ( service_id, timestamp_ms ) in hash_ids_to_deleted_file_service_ids_to_timestamps_ms[ hash_id ].items() }
                
                deleted_file_service_keys_to_previously_imported_timestamps_ms = { service_ids_to_service_keys[ service_id ] : timestamp_ms for ( service_id, timestamp_ms ) in hash_ids_to_deleted_file_service_ids_to_previously_imported_timestamps_ms[ hash_id ].items() }
                
                pending_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_pending_file_service_ids[ hash_id ] }
                
                petitioned_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_petitioned_file_service_ids[ hash_id ] }
                
                inbox = hash_id in self.modules_files_inbox.inbox_hash_ids
                
                urls = hash_ids_to_urls[ hash_id ]
                
                service_ids_to_filenames = dict( hash_ids_to_service_ids_and_filenames[ hash_id ] )
                
                service_keys_to_filenames = { service_ids_to_service_keys[ service_id ] : filename for ( service_id, filename ) in service_ids_to_filenames.items() }
                
                if hash_id in hash_ids_to_half_initialised_timestamp_managers:
                    
                    times_manager = hash_ids_to_half_initialised_timestamp_managers[ hash_id ]
                    
                else:
                    
                    times_manager = ClientMediaManagers.TimesManager()
                    
                
                times_manager.SetImportedTimestampsMS( current_file_service_keys_to_timestamps_ms )
                times_manager.SetDeletedTimestampsMS( deleted_file_service_keys_to_timestamps_ms )
                times_manager.SetPreviouslyImportedTimestampsMS( deleted_file_service_keys_to_previously_imported_timestamps_ms )
                
                local_file_deletion_reason = hash_ids_to_local_file_deletion_reasons.get( hash_id, None )
                
                locations_manager = ClientMediaManagers.LocationsManager(
                    set( current_file_service_keys_to_timestamps_ms.keys() ),
                    set( deleted_file_service_keys_to_timestamps_ms.keys() ),
                    pending_file_service_keys,
                    petitioned_file_service_keys,
                    times_manager,
                    inbox = inbox,
                    urls = urls,
                    service_keys_to_filenames = service_keys_to_filenames,
                    local_file_deletion_reason = local_file_deletion_reason
                )
                
                #
                
                service_keys_to_ratings = { service_ids_to_service_keys[ service_id ] : rating for ( service_id, rating ) in hash_ids_to_local_ratings[ hash_id ] }
                
                ratings_manager = ClientMediaManagers.RatingsManager( service_keys_to_ratings )
                
                #
                
                if hash_id in hash_ids_to_names_and_notes:
                    
                    names_to_notes = dict( hash_ids_to_names_and_notes[ hash_id ] )
                    
                else:
                    
                    names_to_notes = dict()
                    
                
                notes_manager = ClientMediaManagers.NotesManager( names_to_notes )
                
                #
                
                if hash_id in hash_ids_to_file_viewing_stats:
                    
                    file_viewing_stats = hash_ids_to_file_viewing_stats[ hash_id ]
                    
                    file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager( times_manager, file_viewing_stats )
                    
                else:
                    
                    file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager( times_manager )
                    
                
                #
                
                missing_media_results.append( ClientMediaResult.MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager ) )
                
            
            self._weakref_media_result_cache.AddMediaResults( missing_media_results )
            
            cached_media_results.extend( missing_media_results )
            
        
        media_results = cached_media_results
        
        if sorted:
            
            hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
            
            media_results = [ hash_ids_to_media_results[ hash_id ] for hash_id in hash_ids if hash_id in hash_ids_to_media_results ]
            
        
        return media_results
        
    
    def GetMediaResultPairs( self, pairs_of_hash_ids ):
        
        all_hash_ids = set( itertools.chain.from_iterable( pairs_of_hash_ids ) )
        
        media_results = self.GetMediaResults( all_hash_ids )
        
        hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
        
        media_result_pairs = [
            ( hash_ids_to_media_results[ hash_id_a ], hash_ids_to_media_results[ hash_id_b ] )
            for ( hash_id_a, hash_id_b )
            in pairs_of_hash_ids
        ]
        
        return media_result_pairs
        
    
    def GetMediaResultFromHash( self, hash ) -> ClientMediaResult.MediaResult:
        
        media_results = self.GetMediaResultsFromHashes( [ hash ] )
        
        return media_results[0]
        
    
    def GetMediaResultsFromHashes( self, hashes: collections.abc.Collection[ bytes ], sorted: bool = False ) -> list[ ClientMediaResult.MediaResult ]:
        
        query_hash_ids = set( self.modules_hashes_local_cache.GetHashIds( hashes ) )
        
        media_results = self.GetMediaResults( query_hash_ids )
        
        if sorted:
            
            if len( hashes ) > len( query_hash_ids ):
                
                hashes = HydrusData.DedupeList( hashes )
                
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            media_results = [ hashes_to_media_results[ hash ] for hash in hashes if hash in hashes_to_media_results ]
            
        
        return media_results
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        # if content type is a domain, then give urls? bleh
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        self._weakref_media_result_cache.ProcessContentUpdatePackage( content_update_package )
        
    
    def RegenTagsManagersViaHashIdsAfterJob( self, hash_ids ):
        
        hash_ids_to_do = self._weakref_media_result_cache.FilterFiles( hash_ids )
        
        if len( hash_ids_to_do ) > 0:
            
            hash_ids_to_tags_managers = self.GetForceRefreshTagsManagers( hash_ids_to_do )
            
            self._weakref_media_result_cache.SilentlyTakeNewTagsManagers( hash_ids_to_tags_managers )
            
        
    
    def RegenTagsManagersViaTagsAfterJob( self, tags ) -> bool:
        
        work_done = False
        
        hash_ids_to_do = self._weakref_media_result_cache.FilterFilesWithTags( tags )
        
        if len( hash_ids_to_do ) > 0:
            
            hash_ids_to_tags_managers = self.GetForceRefreshTagsManagers( hash_ids_to_do )
            
            self._weakref_media_result_cache.SilentlyTakeNewTagsManagers( hash_ids_to_tags_managers )
            
            work_done = True
            
        
        return work_done
        
    
