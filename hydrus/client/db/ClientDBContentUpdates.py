import itertools
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesInbox
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBFileDeleteLock
from hydrus.client.db import ClientDBFilesMaintenanceQueue
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBFilesTimestamps
from hydrus.client.db import ClientDBFilesViewingStats
from hydrus.client.db import ClientDBMappingsCountsUpdate
from hydrus.client.db import ClientDBMappingsCacheCombinedFilesDisplay
from hydrus.client.db import ClientDBMappingsCacheSpecificDisplay
from hydrus.client.db import ClientDBMappingsCacheSpecificStorage
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBMediaResults
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBNotesMap
from hydrus.client.db import ClientDBRatings
from hydrus.client.db import ClientDBRepositories
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBServicePaths
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.db import ClientDBTagDisplay
from hydrus.client.db import ClientDBTagSiblings
from hydrus.client.db import ClientDBTagParents
from hydrus.client.db import ClientDBURLMap
from hydrus.client.media import ClientMediaFileFilter # don't remove this without care, it initialises serialised object early
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

# TODO: Ok I transplanted this giant list of modules here, and some of that is apprporiate, but we can consolidate. best candidates to start seem to be:
# file add/delete/undelete
# updatemappings
class ClientDBContentUpdates( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper,
        after_job_content_update_packages: list,
        regen_tags_managers_hash_ids: set,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_tags: ClientDBMaster.ClientDBMasterTags,
        modules_texts: ClientDBMaster.ClientDBMasterTexts,
        modules_files_metadata_basic: ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic,
        modules_files_viewing_stats: ClientDBFilesViewingStats.ClientDBFilesViewingStats,
        modules_url_map: ClientDBURLMap.ClientDBURLMap,
        modules_notes_map: ClientDBNotesMap.ClientDBNotesMap,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_files_timestamps: ClientDBFilesTimestamps.ClientDBFilesTimestamps,
        modules_files_inbox: ClientDBFilesInbox.ClientDBFilesInbox,
        modules_file_delete_lock: ClientDBFileDeleteLock.ClientDBFileDeleteLock,
        modules_hashes_local_cache: ClientDBDefinitionsCache,
        modules_ratings: ClientDBRatings.ClientDBRatings,
        modules_service_paths: ClientDBServicePaths.ClientDBServicePaths,
        modules_mappings_storage: ClientDBMappingsStorage.ClientDBMappingsStorage,
        modules_tag_siblings: ClientDBTagSiblings.ClientDBTagSiblings,
        modules_tag_parents: ClientDBTagParents.ClientDBTagParents,
        modules_tag_display: ClientDBTagDisplay.ClientDBTagDisplay,
        modules_mappings_counts_update: ClientDBMappingsCountsUpdate.ClientDBMappingsCountsUpdate,
        modules_mappings_cache_combined_files_display: ClientDBMappingsCacheCombinedFilesDisplay.ClientDBMappingsCacheCombinedFilesDisplay,
        modules_mappings_cache_specific_display: ClientDBMappingsCacheSpecificDisplay.ClientDBMappingsCacheSpecificDisplay,
        modules_mappings_cache_specific_storage: ClientDBMappingsCacheSpecificStorage.ClientDBMappingsCacheSpecificStorage,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles,
        modules_files_maintenance_queue: ClientDBFilesMaintenanceQueue.ClientDBFilesMaintenanceQueue,
        modules_repositories: ClientDBRepositories.ClientDBRepositories,
        modules_media_results: ClientDBMediaResults.ClientDBMediaResults
    ):
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self._after_job_content_update_packages = after_job_content_update_packages
        self._regen_tags_managers_hash_ids = regen_tags_managers_hash_ids
        self.modules_services = modules_services
        self.modules_tags = modules_tags
        self.modules_texts = modules_texts
        self.modules_files_metadata_basic = modules_files_metadata_basic
        self.modules_files_viewing_stats = modules_files_viewing_stats
        self.modules_url_map = modules_url_map
        self.modules_notes_map = modules_notes_map
        self.modules_files_storage = modules_files_storage
        self.modules_files_timestamps = modules_files_timestamps
        self.modules_files_inbox = modules_files_inbox
        self.modules_file_delete_lock = modules_file_delete_lock
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_ratings = modules_ratings
        self.modules_service_paths = modules_service_paths
        self.modules_mappings_storage = modules_mappings_storage
        self.modules_tag_siblings = modules_tag_siblings
        self.modules_tag_parents = modules_tag_parents
        self.modules_tag_display = modules_tag_display
        self.modules_mappings_counts_update = modules_mappings_counts_update
        self.modules_mappings_cache_combined_files_display = modules_mappings_cache_combined_files_display
        self.modules_mappings_cache_specific_display = modules_mappings_cache_specific_display
        self.modules_mappings_cache_specific_storage = modules_mappings_cache_specific_storage
        self.modules_similar_files = modules_similar_files
        self.modules_files_maintenance_queue = modules_files_maintenance_queue
        self.modules_repositories = modules_repositories
        self.modules_media_results = modules_media_results
        
        super().__init__( 'client content updates', cursor )
        
    
    def AddFiles( self, service_id, rows ):
        
        hash_ids = { row[0] for row in rows }
        
        existing_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
        
        new_hash_ids = hash_ids.difference( existing_hash_ids )
        
        if len( new_hash_ids ) > 0:
            
            service = self.modules_services.GetService( service_id )
            
            service_type = service.GetServiceType()
            
            valid_rows = [ ( hash_id, timestamp_ms ) for ( hash_id, timestamp_ms ) in rows if hash_id in new_hash_ids ]
            
            # if we are adding to a local file domain, either an import or an undelete, remove any from the trash and add to the umbrella services if needed
            
            if service_type == HC.LOCAL_FILE_DOMAIN:
                
                self.DeleteFiles( self.modules_services.trash_service_id, new_hash_ids )
                
                self.AddFiles( self.modules_services.combined_local_media_service_id, valid_rows )
                self.AddFiles( self.modules_services.combined_local_file_service_id, valid_rows )
                
            
            if service_type == HC.LOCAL_FILE_UPDATE_DOMAIN:
                
                self.AddFiles( self.modules_services.combined_local_file_service_id, valid_rows )
                
            
            # insert the files
            
            pending_changed = self.modules_files_storage.AddFiles( service_id, valid_rows )
            
            if pending_changed:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
                
            
            delta_size = self.modules_files_metadata_basic.GetTotalSize( new_hash_ids )
            num_viewable_files = self.modules_files_metadata_basic.GetNumViewable( new_hash_ids )
            num_files = len( new_hash_ids )
            num_inbox = len( new_hash_ids.intersection( self.modules_files_inbox.inbox_hash_ids ) )
            
            service_info_updates = []
            
            service_info_updates.append( ( delta_size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
            service_info_updates.append( ( num_viewable_files, service_id, HC.SERVICE_INFO_NUM_VIEWABLE_FILES ) )
            service_info_updates.append( ( num_files, service_id, HC.SERVICE_INFO_NUM_FILES ) )
            service_info_updates.append( ( num_inbox, service_id, HC.SERVICE_INFO_NUM_INBOX ) )
            
            # remove any records of previous deletion
            
            if service_id != self.modules_services.trash_service_id:
                
                num_deleted = self.modules_files_storage.ClearDeleteRecord( service_id, new_hash_ids )
                
                service_info_updates.append( ( -num_deleted, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) )
                
            
            # if entering the combined local domain, update the hash cache
            
            if service_id == self.modules_services.combined_local_file_service_id:
                
                self.modules_hashes_local_cache.AddHashIdsToCache( new_hash_ids )
                
            
            # if adding an update file, repo manager wants to know
            
            if service_id == self.modules_services.local_update_service_id:
                
                self.modules_repositories.NotifyUpdatesImported( new_hash_ids )
                
            
            # if we track tags for this service, update the a/c cache
            
            if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
                with self._MakeTemporaryIntegerTable( new_hash_ids, 'hash_id' ) as temp_hash_id_table_name:
                    
                    for tag_service_id in tag_service_ids:
                        
                        self.modules_mappings_cache_specific_storage.AddFiles( service_id, tag_service_id, new_hash_ids, temp_hash_id_table_name )
                        self.modules_mappings_cache_specific_display.AddFiles( service_id, tag_service_id, new_hash_ids, temp_hash_id_table_name )
                        
                    
                
            
            # now update the combined deleted files service
            
            if service_type in HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE:
                
                location_context = self.modules_files_storage.GetLocationContextForAllServicesDeletedFiles()
                
                still_deleted_hash_ids = self.modules_files_storage.FilterHashIds( location_context, new_hash_ids )
                
                no_longer_deleted_hash_ids = new_hash_ids.difference( still_deleted_hash_ids )
                
                self.DeleteFiles( self.modules_services.combined_deleted_file_service_id, no_longer_deleted_hash_ids )
                
            
            # push the service updates, done
            
            self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
            
        
    
    def DeleteFiles( self, service_id, hash_ids, only_if_current = False ):
        
        local_file_service_ids = self.modules_services.GetServiceIds( ( HC.LOCAL_FILE_DOMAIN, ) )
        
        # we go nuclear on the umbrella services, being very explicit to catch every possible problem
        
        if service_id == self.modules_services.combined_local_file_service_id:
            
            for local_file_service_id in local_file_service_ids:
                
                self.DeleteFiles( local_file_service_id, hash_ids, only_if_current = True )
                
            
            self.DeleteFiles( self.modules_services.combined_local_media_service_id, hash_ids, only_if_current = True )
            
            self.DeleteFiles( self.modules_services.local_update_service_id, hash_ids, only_if_current = True )
            self.DeleteFiles( self.modules_services.trash_service_id, hash_ids, only_if_current = True )
            
        
        if service_id == self.modules_services.combined_local_media_service_id:
            
            for local_file_service_id in local_file_service_ids:
                
                self.DeleteFiles( local_file_service_id, hash_ids, only_if_current = True )
                
            
        
        service = self.modules_services.GetService( service_id )
        
        service_type = service.GetServiceType()
        
        existing_hash_ids_to_timestamps_ms = self.modules_files_storage.GetCurrentHashIdsToTimestampsMS( service_id, hash_ids )
        
        existing_hash_ids = set( existing_hash_ids_to_timestamps_ms.keys() )
        
        service_info_updates = []
        
        # do delete outside, file repos and perhaps some other bananas situation can delete without ever having added
        
        now_ms = HydrusTime.GetNowMS()
        
        if service_type not in HC.FILE_SERVICES_WITH_NO_DELETE_RECORD:
            
            # make a deletion record
            
            if only_if_current:
                
                deletion_record_hash_ids = existing_hash_ids
                
            else:
                
                deletion_record_hash_ids = hash_ids
                
            
            if len( deletion_record_hash_ids ) > 0:
                
                insert_rows = [ ( hash_id, existing_hash_ids_to_timestamps_ms[ hash_id ] if hash_id in existing_hash_ids_to_timestamps_ms else None ) for hash_id in deletion_record_hash_ids ]
                
                num_new_deleted_files = self.modules_files_storage.RecordDeleteFiles( service_id, insert_rows )
                
                service_info_updates.append( ( num_new_deleted_files, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) )
                
            
        
        if len( existing_hash_ids ) > 0:
            
            # remove them from the service
            
            pending_changed = self.modules_files_storage.RemoveFiles( service_id, existing_hash_ids )
            
            if pending_changed:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
                
            
            delta_size = self.modules_files_metadata_basic.GetTotalSize( existing_hash_ids )
            num_viewable_files = self.modules_files_metadata_basic.GetNumViewable( existing_hash_ids )
            num_existing_files_removed = len( existing_hash_ids )
            num_inbox = len( existing_hash_ids.intersection( self.modules_files_inbox.inbox_hash_ids ) )
            
            service_info_updates.append( ( -delta_size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
            service_info_updates.append( ( -num_viewable_files, service_id, HC.SERVICE_INFO_NUM_VIEWABLE_FILES ) )
            service_info_updates.append( ( -num_existing_files_removed, service_id, HC.SERVICE_INFO_NUM_FILES ) )
            service_info_updates.append( ( -num_inbox, service_id, HC.SERVICE_INFO_NUM_INBOX ) )
            
            # now do special stuff
            
            # if we maintain tag counts for this service, update
            
            if service_type in HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES:
                
                tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
                with self._MakeTemporaryIntegerTable( existing_hash_ids, 'hash_id' ) as temp_hash_id_table_name:
                    
                    for tag_service_id in tag_service_ids:
                        
                        self.modules_mappings_cache_specific_storage.DeleteFiles( service_id, tag_service_id, existing_hash_ids, temp_hash_id_table_name )
                        
                    
                
            
            # update the combined deleted file service
            
            if service_type in HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE:
                
                rows = [ ( hash_id, now_ms ) for hash_id in existing_hash_ids ]
                
                self.AddFiles( self.modules_services.combined_deleted_file_service_id, rows )
                
            
            # if any files are no longer in any local file services, remove from the umbrella and send them to the trash
            
            if service_id in local_file_service_ids:
                
                other_local_file_service_ids = set( local_file_service_ids )
                other_local_file_service_ids.discard( service_id )
                
                hash_ids_still_in_another_service = self.modules_files_storage.FilterAllCurrentHashIds( existing_hash_ids, just_these_service_ids = other_local_file_service_ids )
                
                trashed_hash_ids = existing_hash_ids.difference( hash_ids_still_in_another_service )
                
                if len( trashed_hash_ids ) > 0:
                    
                    self.DeleteFiles( self.modules_services.combined_local_media_service_id, trashed_hash_ids )
                    
                    delete_rows = [ ( hash_id, now_ms ) for hash_id in trashed_hash_ids ]
                    
                    self.AddFiles( self.modules_services.trash_service_id, delete_rows )
                    
                
            
            # if we are deleting from repo updates, do a physical delete now
            
            if service_id == self.modules_services.local_update_service_id:
                
                self.DeleteFiles( self.modules_services.combined_local_file_service_id, existing_hash_ids )
                
            
            # if the files are being fully deleted, then physically delete them
            
            if service_id == self.modules_services.combined_local_file_service_id:
                
                self.modules_files_inbox.ArchiveFiles( existing_hash_ids )
                
                for hash_id in existing_hash_ids:
                    
                    self.modules_similar_files.StopSearchingFile( hash_id )
                    
                
                self.modules_files_maintenance_queue.CancelFiles( existing_hash_ids )
                
                self.modules_hashes_local_cache.DropHashIdsFromCache( existing_hash_ids )
                
            
        
        # push the info updates
        
        self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def ProcessContentUpdatePackage( self, content_update_package, publish_content_updates = True ):
        
        notify_new_downloads = False
        notify_new_pending = False
        notify_new_parents = False
        notify_new_siblings = False
        
        valid_content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
            
            try:
                
                service_id = self.modules_services.GetServiceId( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            valid_content_update_package.AddContentUpdates( service_key, content_updates )
            
            service = self.modules_services.GetService( service_id )
            
            service_type = service.GetServiceType()
            
            ultimate_mappings_ids = []
            ultimate_deleted_mappings_ids = []
            
            ultimate_pending_mappings_ids = []
            ultimate_pending_rescinded_mappings_ids = []
            
            ultimate_petitioned_mappings_ids = []
            ultimate_petitioned_rescinded_mappings_ids = []
            
            changed_sibling_tag_ids = set()
            changed_parent_tag_ids = set()
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if service_type in HC.REAL_FILE_SERVICES:
                    
                    if data_type == HC.CONTENT_TYPE_FILES:
                        
                        if action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                            
                            hashes = row
                            
                            if hashes is None:
                                
                                service_ids_to_nums_cleared = self.modules_files_storage.ClearLocalDeleteRecord()
                                
                                self.ResyncCombinedDeletedFiles()
                                
                            else:
                                
                                hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                                
                                service_ids_to_nums_cleared = self.modules_files_storage.ClearLocalDeleteRecord( hash_ids )
                                
                                self.ResyncCombinedDeletedFiles( hash_ids )
                                
                            
                            self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ( -num_cleared, clear_service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) for ( clear_service_id, num_cleared ) in service_ids_to_nums_cleared.items() ) )
                            
                        elif action == HC.CONTENT_UPDATE_ADD:
                            
                            if service_type in HC.LOCAL_FILE_SERVICES or service_type == HC.FILE_REPOSITORY:
                                
                                ( file_info_manager, timestamp_ms ) = row
                                
                                ( hash_id, hash, size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = file_info_manager.ToTuple()
                                
                                self.modules_files_metadata_basic.AddFilesInfo( [ ( hash_id, size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) ] )
                                
                            elif service_type == HC.IPFS:
                                
                                ( file_info_manager, multihash ) = row
                                
                                hash_id = file_info_manager.hash_id
                                
                                self.modules_service_paths.SetServiceFilename( service_id, hash_id, multihash )
                                
                                timestamp_ms = HydrusTime.GetNowMS()
                                
                            else:
                                
                                raise NotImplementedError( f'Got a file-add call on the wrong type of service ({service_type})!' )
                                
                            
                            self.AddFiles( service_id, [ ( hash_id, timestamp_ms ) ] )
                            
                        else:
                            
                            hashes = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            if action == HC.CONTENT_UPDATE_ARCHIVE:
                                
                                self.modules_files_inbox.ArchiveFiles( hash_ids )
                                
                            elif action == HC.CONTENT_UPDATE_INBOX:
                                
                                self.modules_files_inbox.InboxFiles( hash_ids )
                                
                            elif action in ( HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_DELETE_FROM_SOURCE_AFTER_MIGRATE ):
                                
                                actual_delete_hash_ids = hash_ids
                                
                                if action == HC.CONTENT_UPDATE_DELETE and service_key in ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY ):
                                    
                                    local_hash_ids = self.modules_files_storage.FilterHashIds( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ), hash_ids )
                                    
                                    actually_deletable_hash_ids = self.modules_file_delete_lock.FilterForPhysicalFileDeleteLock( local_hash_ids )
                                    
                                    if len( actually_deletable_hash_ids ) < len( local_hash_ids ):
                                        
                                        # ok we hit the lock on some
                                        undeletable_hash_ids = set( local_hash_ids ).difference( actually_deletable_hash_ids )
                                        
                                        media_results = self.modules_media_results.GetMediaResults( undeletable_hash_ids, sorted = False )
                                        
                                        ClientMediaFileFilter.ReportDeleteLockFailures( media_results )
                                        
                                    
                                    if len( actually_deletable_hash_ids ) < len( hash_ids ):
                                        
                                        hash_ids = actually_deletable_hash_ids
                                        
                                        hashes = self.modules_hashes_local_cache.GetHashes( hash_ids )
                                        
                                        content_update.SetRow( hashes )
                                        
                                    
                                
                                if service_type in ( HC.LOCAL_FILE_DOMAIN, HC.COMBINED_LOCAL_MEDIA, HC.COMBINED_LOCAL_FILE ):
                                    
                                    if content_update.HasReason():
                                        
                                        reason = content_update.GetReason()
                                        
                                        # let's be careful only to set deletion reasons on valid hash ids
                                        location_context = ClientLocation.LocationContext( current_service_keys = ( service_key, ) )
                                        
                                        reason_settable_hash_ids = self.modules_files_storage.FilterHashIds( location_context, hash_ids )
                                        
                                        if len( reason_settable_hash_ids ) > 0:
                                            
                                            self.modules_files_storage.SetFileDeletionReason( reason_settable_hash_ids, reason )
                                            
                                        
                                    
                                
                                if service_id == self.modules_services.trash_service_id:
                                    
                                    # shouldn't be called anymore, but just in case someone fidgets a trash delete with client api or something
                                    
                                    self.DeleteFiles( self.modules_services.combined_local_file_service_id, hash_ids )
                                    
                                else:
                                    
                                    self.DeleteFiles( service_id, hash_ids )
                                    
                                
                            elif action == HC.CONTENT_UPDATE_UNDELETE:
                                
                                self.UndeleteFiles( service_id, hash_ids )
                                
                            elif action == HC.CONTENT_UPDATE_PEND:
                                
                                invalid_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
                                
                                valid_hash_ids = hash_ids.difference( invalid_hash_ids )
                                
                                self.modules_files_storage.PendFiles( service_id, valid_hash_ids )
                                
                                if service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
                                    
                                    notify_new_downloads = True
                                    
                                else:
                                    
                                    notify_new_pending = True
                                    
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                reason = content_update.GetReason()
                                
                                reason_id = self.modules_texts.GetTextId( reason )
                                
                                valid_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
                                
                                self.modules_files_storage.PetitionFiles( service_id, reason_id, valid_hash_ids )
                                
                                notify_new_pending = True
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                self.modules_files_storage.RescindPendFiles( service_id, hash_ids )
                                
                                if service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
                                    
                                    notify_new_downloads = True
                                    
                                else:
                                    
                                    notify_new_pending = True
                                    
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                self.modules_files_storage.RescindPetitionFiles( service_id, hash_ids )
                                
                                notify_new_pending = True
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_DIRECTORIES:
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            ( hashes, dirname, note ) = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            result = self._Execute( 'SELECT SUM( size ) FROM files_info WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ).fetchone()
                            
                            total_size = self._GetSumResult( result )
                            
                            self.modules_service_paths.SetServiceDirectory( service_id, hash_ids, dirname, total_size, note )
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            dirname = row
                            
                            self.modules_service_paths.DeleteServiceDirectory( service_id, dirname )
                            
                        
                    elif data_type == HC.CONTENT_TYPE_URLS:
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            ( urls, hashes ) = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            for ( hash_id, url ) in itertools.product( hash_ids, urls ):
                                
                                self.modules_url_map.AddMapping( hash_id, url )
                                
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            ( urls, hashes ) = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            for ( hash_id, url ) in itertools.product( hash_ids, urls ):
                                
                                self.modules_url_map.DeleteMapping( hash_id, url )
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_TIMESTAMP:
                        
                        ( hashes, timestamp_data ) = row
                        
                        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            self.modules_files_timestamps.UpdateTime( hash_ids, timestamp_data )
                            
                        elif action == HC.CONTENT_UPDATE_SET:
                            
                            self.modules_files_timestamps.SetTime( hash_ids, timestamp_data )
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            self.modules_files_timestamps.ClearTime( hash_ids, timestamp_data )
                            
                        
                    elif data_type == HC.CONTENT_TYPE_FILE_VIEWING_STATS:
                        
                        if action == HC.CONTENT_UPDATE_ADVANCED:
                            
                            action = row
                            
                            if action == 'clear':
                                
                                self.modules_files_viewing_stats.ClearAllStats()
                                
                            
                        elif action == HC.CONTENT_UPDATE_ADD:
                            
                            ( hash, canvas_type, view_timestamp_ms, views_delta, viewtime_delta_ms ) = row
                            
                            hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                            
                            self.modules_files_viewing_stats.AddViews( hash_id, canvas_type, view_timestamp_ms, views_delta, viewtime_delta_ms )
                            
                        elif action == HC.CONTENT_UPDATE_SET:
                            
                            ( hash, canvas_type, view_timestamp_ms, views, viewtime_ms ) = row
                            
                            hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                            
                            self.modules_files_viewing_stats.SetViews( hash_id, canvas_type, view_timestamp_ms, views, viewtime_ms )
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            hashes = row
                            
                            hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                            
                            self.modules_files_viewing_stats.ClearViews( hash_ids )
                            
                        
                    
                elif service_type in HC.REAL_TAG_SERVICES:
                    
                    if data_type == HC.CONTENT_TYPE_MAPPINGS:
                        
                        ( tag, hashes ) = row
                        
                        try:
                            
                            potentially_dirty_tag = tag
                            
                            tag = HydrusTags.CleanTag( potentially_dirty_tag )
                            
                            if tag != potentially_dirty_tag:
                                
                                content_update.SetRow( ( tag, hashes ) )
                                
                            
                            tag_id = self.modules_tags.GetTagId( tag )
                            
                        except HydrusExceptions.TagSizeException:
                            
                            content_update.SetRow( ( 'bad tag', set() ) )
                            
                            continue
                            
                        
                        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                        
                        display_affected = action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_RESCIND_PEND )
                        
                        if display_affected and publish_content_updates and self.modules_tag_display.IsChained( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, service_id, tag_id ):
                            
                            self._regen_tags_managers_hash_ids.update( hash_ids )
                            
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            if not CG.client_controller.tag_display_manager.TagOK( ClientTags.TAG_DISPLAY_STORAGE, service_key, tag ):
                                
                                continue
                                
                            
                            ultimate_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            ultimate_deleted_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_PEND:
                            
                            if not CG.client_controller.tag_display_manager.TagOK( ClientTags.TAG_DISPLAY_STORAGE, service_key, tag ):
                                
                                continue
                                
                            
                            ultimate_pending_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                            
                            ultimate_pending_rescinded_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_PETITION:
                            
                            reason = content_update.GetReason()
                            
                            reason_id = self.modules_texts.GetTextId( reason )
                            
                            ultimate_petitioned_mappings_ids.append( ( tag_id, hash_ids, reason_id ) )
                            
                        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                            
                            ultimate_petitioned_rescinded_mappings_ids.append( ( tag_id, hash_ids ) )
                            
                        elif action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                            
                            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( service_id )
                            
                            self._ExecuteMany( 'DELETE FROM {} WHERE tag_id = ? AND hash_id = ?;'.format( deleted_mappings_table_name ), ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                            
                            self._Execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ) )
                            
                            cache_file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
                            
                            for cache_file_service_id in cache_file_service_ids:
                                
                                ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( cache_file_service_id, service_id )
                                
                                self._ExecuteMany( 'DELETE FROM ' + cache_deleted_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in hash_ids ) )
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_TAG_PARENTS:
                        
                        if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            ( child_tag, parent_tag ) = row
                            
                            try:
                                
                                child_tag_id = self.modules_tags.GetTagId( child_tag )
                                
                                parent_tag_id = self.modules_tags.GetTagId( parent_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            pairs = ( ( child_tag_id, parent_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_ADD:
                                
                                self.modules_tag_parents.AddTagParents( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                self.modules_tag_parents.DeleteTagParents( service_id, pairs )
                                
                            
                            changed_parent_tag_ids.update( ( child_tag_id, parent_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ):
                            
                            ( child_tag, parent_tag ) = row
                            
                            try:
                                
                                child_tag_id = self.modules_tags.GetTagId( child_tag )
                                
                                parent_tag_id = self.modules_tags.GetTagId( parent_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            reason = content_update.GetReason()
                            
                            reason_id = self.modules_texts.GetTextId( reason )
                            
                            triples = ( ( child_tag_id, parent_tag_id, reason_id ), )
                            
                            if action == HC.CONTENT_UPDATE_PEND:
                                
                                self.modules_tag_parents.PendTagParents( service_id, triples )
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                self.modules_tag_parents.PetitionTagParents( service_id, triples )
                                
                            
                            changed_parent_tag_ids.update( ( child_tag_id, parent_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                            
                            ( child_tag, parent_tag ) = row
                            
                            try:
                                
                                child_tag_id = self.modules_tags.GetTagId( child_tag )
                                
                                parent_tag_id = self.modules_tags.GetTagId( parent_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            pairs = ( ( child_tag_id, parent_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                self.modules_tag_parents.RescindPendingTagParents( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                self.modules_tag_parents.RescindPetitionedTagParents( service_id, pairs )
                                
                            
                            changed_parent_tag_ids.update( ( child_tag_id, parent_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        
                        notify_new_parents = True
                        
                    elif data_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
                        
                        if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            ( bad_tag, good_tag ) = row
                            
                            try:
                                
                                bad_tag_id = self.modules_tags.GetTagId( bad_tag )
                                
                                good_tag_id = self.modules_tags.GetTagId( good_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            pairs = ( ( bad_tag_id, good_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_ADD:
                                
                                self.modules_tag_siblings.AddTagSiblings( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                self.modules_tag_siblings.DeleteTagSiblings( service_id, pairs )
                                
                            
                            changed_sibling_tag_ids.update( ( bad_tag_id, good_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ):
                            
                            ( bad_tag, good_tag ) = row
                            
                            try:
                                
                                bad_tag_id = self.modules_tags.GetTagId( bad_tag )
                                
                                good_tag_id = self.modules_tags.GetTagId( good_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            reason = content_update.GetReason()
                            
                            reason_id = self.modules_texts.GetTextId( reason )
                            
                            triples = ( ( bad_tag_id, good_tag_id, reason_id ), )
                            
                            if action == HC.CONTENT_UPDATE_PEND:
                                
                                self.modules_tag_siblings.PendTagSiblings( service_id, triples )
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                self.modules_tag_siblings.PetitionTagSiblings( service_id, triples )
                                
                            
                            changed_sibling_tag_ids.update( ( bad_tag_id, good_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                            
                            ( bad_tag, good_tag ) = row
                            
                            try:
                                
                                bad_tag_id = self.modules_tags.GetTagId( bad_tag )
                                
                                good_tag_id = self.modules_tags.GetTagId( good_tag )
                                
                            except HydrusExceptions.TagSizeException:
                                
                                continue
                                
                            
                            pairs = ( ( bad_tag_id, good_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                self.modules_tag_siblings.RescindPendingTagSiblings( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                self.modules_tag_siblings.RescindPetitionedTagSiblings( service_id, pairs )
                                
                            
                            changed_sibling_tag_ids.update( ( bad_tag_id, good_tag_id ) )
                            
                            if service_type == HC.TAG_REPOSITORY:
                                
                                notify_new_pending = True
                                
                            
                        
                        notify_new_siblings = True
                        
                    
                elif service_type in HC.RATINGS_SERVICES:
                    
                    if action == HC.CONTENT_UPDATE_ADD:
                        
                        ( rating, hashes ) = row
                        
                        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
                        
                        self.modules_ratings.SetRating( service_id, hash_ids, rating )
                        
                    elif action == HC.CONTENT_UPDATE_ADVANCED:
                        
                        action = row
                        
                        if service_type in HC.STAR_RATINGS_SERVICES:
                            
                            if action == 'delete_for_deleted_files':
                                
                                deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_DELETED )
                                
                                self._Execute( 'DELETE FROM local_ratings WHERE service_id = ? and hash_id IN ( SELECT hash_id FROM {} );'.format( deleted_files_table_name ), ( service_id, ) )
                                
                                ratings_deleted = self._GetRowCount()
                                
                                self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( ratings_deleted, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            elif action == 'delete_for_non_local_files':
                                
                                current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_CURRENT )
                                
                                self._Execute( 'DELETE FROM local_ratings WHERE local_ratings.service_id = ? and hash_id NOT IN ( SELECT hash_id FROM {} );'.format( current_files_table_name ), ( service_id, ) )
                                
                                ratings_deleted = self._GetRowCount()
                                
                                self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( ratings_deleted, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            elif action == 'delete_for_all_files':
                                
                                self._Execute( 'DELETE FROM local_ratings WHERE service_id = ?;', ( service_id, ) )
                                
                                self._Execute( 'UPDATE service_info SET info = ? WHERE service_id = ? AND info_type = ?;', ( 0, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            
                        elif service_type == HC.LOCAL_RATING_INCDEC:
                            
                            if action == 'delete_for_deleted_files':
                                
                                deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_DELETED )
                                
                                self._Execute( 'DELETE FROM local_incdec_ratings WHERE service_id = ? and hash_id IN ( SELECT hash_id FROM {} );'.format( deleted_files_table_name ), ( service_id, ) )
                                
                                ratings_deleted = self._GetRowCount()
                                
                                self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( ratings_deleted, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            elif action == 'delete_for_non_local_files':
                                
                                current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_CURRENT )
                                
                                self._Execute( 'DELETE FROM local_incdec_ratings WHERE local_incdec_ratings.service_id = ? and hash_id NOT IN ( SELECT hash_id FROM {} );'.format( current_files_table_name ), ( service_id, ) )
                                
                                ratings_deleted = self._GetRowCount()
                                
                                self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( ratings_deleted, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            elif action == 'delete_for_all_files':
                                
                                self._Execute( 'DELETE FROM local_incdec_ratings WHERE service_id = ?;', ( service_id, ) )
                                
                                self._Execute( 'UPDATE service_info SET info = ? WHERE service_id = ? AND info_type = ?;', ( 0, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
                                
                            
                        
                    
                elif service_type == HC.LOCAL_NOTES:
                    
                    if action == HC.CONTENT_UPDATE_SET:
                        
                        ( hash, name, note ) = row
                        
                        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                        
                        self.modules_notes_map.SetNote( hash_id, name, note )
                        
                    elif action == HC.CONTENT_UPDATE_DELETE:
                        
                        ( hash, name ) = row
                        
                        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                        
                        self.modules_notes_map.DeleteNote( hash_id, name )
                        
                    
                
            
            if len( ultimate_mappings_ids ) + len( ultimate_deleted_mappings_ids ) + len( ultimate_pending_mappings_ids ) + len( ultimate_pending_rescinded_mappings_ids ) + len( ultimate_petitioned_mappings_ids ) + len( ultimate_petitioned_rescinded_mappings_ids ) > 0:
                
                self.UpdateMappings( service_id, mappings_ids = ultimate_mappings_ids, deleted_mappings_ids = ultimate_deleted_mappings_ids, pending_mappings_ids = ultimate_pending_mappings_ids, pending_rescinded_mappings_ids = ultimate_pending_rescinded_mappings_ids, petitioned_mappings_ids = ultimate_petitioned_mappings_ids, petitioned_rescinded_mappings_ids = ultimate_petitioned_rescinded_mappings_ids )
                
                if service_type == HC.TAG_REPOSITORY:
                    
                    notify_new_pending = True
                    
                
            
            if len( changed_sibling_tag_ids ) > 0:
                
                self.modules_tag_display.NotifySiblingsChanged( service_id, changed_sibling_tag_ids )
                
            
            if len( changed_parent_tag_ids ) > 0:
                
                self.modules_tag_display.NotifyParentsChanged( service_id, changed_parent_tag_ids )
                
            
        
        if publish_content_updates:
            
            if notify_new_pending:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_pending' )
                
            if notify_new_downloads:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_downloads' )
                
            if notify_new_siblings or notify_new_parents:
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
                
            
            self.pub_content_update_package_after_commit( valid_content_update_package )
            
        
    
    def pub_content_update_package_after_commit( self, content_update_package ):
        
        self._after_job_content_update_packages.append( content_update_package )
        
    
    def ResyncCombinedDeletedFiles( self, hash_ids = None, do_full_rebuild = False ):
        
        combined_files_stakeholder_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE )
        
        hash_ids_that_are_desired = set()
        
        if hash_ids is None:
            
            for service_id in combined_files_stakeholder_service_ids:
                
                hash_ids_that_are_desired.update( self.modules_files_storage.GetDeletedHashIdsList( service_id ) )
                
            
            existing_hash_ids = set( self.modules_files_storage.GetCurrentHashIdsList( self.modules_services.combined_deleted_file_service_id ) )
            
        else:
            
            for service_id in combined_files_stakeholder_service_ids:
                
                hash_ids_that_are_desired.update( self.modules_files_storage.FilterHashIdsToStatus( service_id, hash_ids, HC.CONTENT_STATUS_DELETED ) )
                
            
            existing_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( self.modules_services.combined_deleted_file_service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
            
        
        if do_full_rebuild:
            
            # this happens in the full 'regenerate' call from the UI database menu. full wipe and recalculation to get any errant timestamps
            
            hash_ids_to_remove = existing_hash_ids
            hash_ids_to_add = hash_ids_that_are_desired
            
        else:
            
            hash_ids_to_remove = existing_hash_ids.difference( hash_ids_that_are_desired )
            hash_ids_to_add = hash_ids_that_are_desired.difference( existing_hash_ids )
            
        
        if len( hash_ids_to_remove ) > 0:
            
            self.DeleteFiles( self.modules_services.combined_deleted_file_service_id, hash_ids_to_remove, only_if_current = True )
            
        
        if len( hash_ids_to_add ) > 0:
            
            hash_ids_to_earliest_timestamps_ms = {}
            
            for service_id in combined_files_stakeholder_service_ids:
                
                hash_ids_to_both_timestamps_ms = self.modules_files_storage.GetDeletedHashIdsToTimestampsMS( service_id, hash_ids_to_add )
                
                for ( hash_id, ( timestamp_ms, original_timestamp_ms ) ) in hash_ids_to_both_timestamps_ms.items():
                    
                    if hash_id in hash_ids_to_earliest_timestamps_ms:
                        
                        if timestamp_ms is not None:
                            
                            existing_timestamp = hash_ids_to_earliest_timestamps_ms[ hash_id ]
                            
                            if existing_timestamp is None or timestamp_ms < existing_timestamp:
                                
                                hash_ids_to_earliest_timestamps_ms[ hash_id ] = timestamp_ms
                                
                            
                        
                    else:
                        
                        hash_ids_to_earliest_timestamps_ms[ hash_id ] = timestamp_ms
                        
                    
                
            
            rows = list( hash_ids_to_earliest_timestamps_ms.items() )
            
            self.AddFiles( self.modules_services.combined_deleted_file_service_id, rows )
            
        
    
    def UndeleteFiles( self, service_id, hash_ids ):
        
        if service_id in ( self.modules_services.combined_local_file_service_id, self.modules_services.combined_local_media_service_id, self.modules_services.trash_service_id ):
            
            service_ids_to_do = self.modules_services.GetServiceIds( ( HC.LOCAL_FILE_DOMAIN, ) )
            
        else:
            
            service_ids_to_do = ( service_id, )
            
        
        for service_id_to_do in service_ids_to_do:
            
            rows = self.modules_files_storage.GetUndeleteRows( service_id_to_do, hash_ids )
            
            if len( rows ) > 0:
                
                self.AddFiles( service_id_to_do, rows )
                
            
        
    
    def UpdateMappings( self, tag_service_id, mappings_ids = None, deleted_mappings_ids = None, pending_mappings_ids = None, pending_rescinded_mappings_ids = None, petitioned_mappings_ids = None, petitioned_rescinded_mappings_ids = None ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
        
        if mappings_ids is None: mappings_ids = []
        if deleted_mappings_ids is None: deleted_mappings_ids = []
        if pending_mappings_ids is None: pending_mappings_ids = []
        if pending_rescinded_mappings_ids is None: pending_rescinded_mappings_ids = []
        if petitioned_mappings_ids is None: petitioned_mappings_ids = []
        if petitioned_rescinded_mappings_ids is None: petitioned_rescinded_mappings_ids = []
        
        mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, mappings_ids, HC.CONTENT_UPDATE_ADD )
        deleted_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, deleted_mappings_ids, HC.CONTENT_UPDATE_DELETE )
        pending_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, pending_mappings_ids, HC.CONTENT_UPDATE_PEND )
        pending_rescinded_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, pending_rescinded_mappings_ids, HC.CONTENT_UPDATE_RESCIND_PEND )
        petitioned_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, petitioned_mappings_ids, HC.CONTENT_UPDATE_PETITION )
        petitioned_rescinded_mappings_ids = self.modules_mappings_storage.FilterExistingUpdateMappings( tag_service_id, petitioned_rescinded_mappings_ids, HC.CONTENT_UPDATE_RESCIND_PETITION )
        
        tag_ids_to_filter_chained = { tag_id for ( tag_id, hash_ids ) in itertools.chain.from_iterable( ( mappings_ids, deleted_mappings_ids, pending_mappings_ids, pending_rescinded_mappings_ids ) ) }
        
        chained_tag_ids = self.modules_tag_display.FilterChained( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, tag_ids_to_filter_chained )
        
        file_service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
        
        change_in_num_mappings = 0
        change_in_num_deleted_mappings = 0
        change_in_num_pending_mappings = 0
        change_in_num_petitioned_mappings = 0
        change_in_num_files = 0
        
        hash_ids_lists = ( hash_ids for ( tag_id, hash_ids ) in itertools.chain.from_iterable( ( mappings_ids, pending_mappings_ids ) ) )
        hash_ids_being_added = { hash_id for hash_id in itertools.chain.from_iterable( hash_ids_lists ) }
        
        hash_ids_lists = ( hash_ids for ( tag_id, hash_ids ) in itertools.chain.from_iterable( ( deleted_mappings_ids, pending_rescinded_mappings_ids ) ) )
        hash_ids_being_removed = { hash_id for hash_id in itertools.chain.from_iterable( hash_ids_lists ) }
        
        hash_ids_being_altered = hash_ids_being_added.union( hash_ids_being_removed )
        
        filtered_hashes_generator = self.modules_mappings_cache_specific_storage.GetFilteredHashesGenerator( file_service_ids, tag_service_id, hash_ids_being_altered )
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS mem.temp_hash_ids ( hash_id INTEGER );' )
        
        self._ExecuteMany( 'INSERT INTO temp_hash_ids ( hash_id ) VALUES ( ? );', ( ( hash_id, ) for hash_id in hash_ids_being_altered ) )
        
        pre_existing_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM temp_hash_ids WHERE EXISTS ( SELECT 1 FROM {} WHERE hash_id = temp_hash_ids.hash_id );'.format( current_mappings_table_name ) ) )
        
        num_files_added = len( hash_ids_being_added.difference( pre_existing_hash_ids ) )
        
        change_in_num_files += num_files_added
        
        # BIG NOTE:
        # after testing some situations, it makes nicest logical sense to interleave all cache updates into the loops
        # otherwise, when there are conflicts due to sheer duplication or the display system applying two tags at once with the same implications, we end up relying on an out-of-date/unsynced (in cache terms) specific cache for combined etc...
        # I now extend this to counts, argh. this is not great in overhead terms, but many optimisations rely on a/c counts now, and the fallback is the combined storage ac count cache
        
        if len( mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in mappings_ids:
                
                if tag_id in chained_tag_ids:
                    
                    self.modules_mappings_cache_combined_files_display.AddMappingsForChained( tag_service_id, tag_id, hash_ids )
                    
                
                self._ExecuteMany( 'DELETE FROM ' + deleted_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_deleted_deleted = self._GetRowCount()
                
                self._ExecuteMany( 'DELETE FROM ' + pending_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_deleted = self._GetRowCount()
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + current_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_current_inserted = self._GetRowCount()
                
                change_in_num_deleted_mappings -= num_deleted_deleted
                change_in_num_pending_mappings -= num_pending_deleted
                change_in_num_mappings += num_current_inserted
                
                self.modules_mappings_counts_update.UpdateCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, num_current_inserted, - num_pending_deleted ) ] )
                
                if tag_id not in chained_tag_ids:
                    
                    self.modules_mappings_counts_update.UpdateCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, num_current_inserted, - num_pending_deleted ) ] )
                    
                
                self.modules_mappings_cache_specific_storage.AddMappings( tag_service_id, tag_id, hash_ids, filtered_hashes_generator )
                
            
        
        if len( deleted_mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in deleted_mappings_ids:
                
                if tag_id in chained_tag_ids:
                    
                    self.modules_mappings_cache_combined_files_display.DeleteMappingsForChained( tag_service_id, tag_id, hash_ids )
                    
                
                self._ExecuteMany( 'DELETE FROM ' + current_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_current_deleted = self._GetRowCount()
                
                self._ExecuteMany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_petitions_deleted = self._GetRowCount()
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + deleted_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_deleted_inserted = self._GetRowCount()
                
                change_in_num_mappings -= num_current_deleted
                change_in_num_petitioned_mappings -= num_petitions_deleted
                change_in_num_deleted_mappings += num_deleted_inserted
                
                self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, num_current_deleted, 0 ) ] )
                
                if tag_id not in chained_tag_ids:
                    
                    self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, num_current_deleted, 0 ) ] )
                    
                
                self.modules_mappings_cache_specific_storage.DeleteMappings( tag_service_id, tag_id, hash_ids, filtered_hashes_generator )
                
            
        
        if len( pending_mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in pending_mappings_ids:
                
                if tag_id in chained_tag_ids:
                    
                    self.modules_mappings_cache_combined_files_display.PendMappingsForChained( tag_service_id, tag_id, hash_ids )
                    
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + pending_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_inserted = self._GetRowCount()
                
                change_in_num_pending_mappings += num_pending_inserted
                
                self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, 0, num_pending_inserted ) ] )
                
                if tag_id not in chained_tag_ids:
                    
                    self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, 0, num_pending_inserted ) ] )
                    
                
                self.modules_mappings_cache_specific_storage.PendMappings( tag_service_id, tag_id, hash_ids, filtered_hashes_generator )
                
            
        
        if len( pending_rescinded_mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in pending_rescinded_mappings_ids:
                
                if tag_id in chained_tag_ids:
                    
                    self.modules_mappings_cache_combined_files_display.RescindPendingMappingsForChained( tag_service_id, tag_id, hash_ids )
                    
                
                self._ExecuteMany( 'DELETE FROM ' + pending_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_deleted = self._GetRowCount()
                
                change_in_num_pending_mappings -= num_pending_deleted
                
                self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, 0, num_pending_deleted ) ] )
                
                if tag_id not in chained_tag_ids:
                    
                    self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, [ ( tag_id, 0, num_pending_deleted ) ] )
                    
                
                self.modules_mappings_cache_specific_storage.RescindPendingMappings( tag_service_id, tag_id, hash_ids, filtered_hashes_generator )
                
            
        
        #
        
        post_existing_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM temp_hash_ids WHERE EXISTS ( SELECT 1 FROM {} WHERE hash_id = temp_hash_ids.hash_id );'.format( current_mappings_table_name ) ) )
        
        self._Execute( 'DROP TABLE temp_hash_ids;' )
        
        num_files_removed = len( pre_existing_hash_ids.intersection( hash_ids_being_removed ).difference( post_existing_hash_ids ) )
        
        change_in_num_files -= num_files_removed
        
        for ( tag_id, hash_ids, reason_id ) in petitioned_mappings_ids:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO ' + petitioned_mappings_table_name + ' VALUES ( ?, ?, ? );', [ ( tag_id, hash_id, reason_id ) for hash_id in hash_ids ] )
            
            num_petitions_inserted = self._GetRowCount()
            
            change_in_num_petitioned_mappings += num_petitions_inserted
            
        
        for ( tag_id, hash_ids ) in petitioned_rescinded_mappings_ids:
            
            self._ExecuteMany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
            
            num_petitions_deleted = self._GetRowCount()
            
            change_in_num_petitioned_mappings -= num_petitions_deleted
            
        
        service_info_updates = []
        
        if change_in_num_mappings != 0: service_info_updates.append( ( change_in_num_mappings, tag_service_id, HC.SERVICE_INFO_NUM_MAPPINGS ) )
        if change_in_num_deleted_mappings != 0: service_info_updates.append( ( change_in_num_deleted_mappings, tag_service_id, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ) )
        if change_in_num_pending_mappings != 0: service_info_updates.append( ( change_in_num_pending_mappings, tag_service_id, HC.SERVICE_INFO_NUM_PENDING_MAPPINGS ) )
        if change_in_num_petitioned_mappings != 0: service_info_updates.append( ( change_in_num_petitioned_mappings, tag_service_id, HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ) )
        if change_in_num_files != 0: service_info_updates.append( ( change_in_num_files, tag_service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
        
        if len( service_info_updates ) > 0: self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
        
    
