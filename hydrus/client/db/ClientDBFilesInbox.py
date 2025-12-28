import collections.abc
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBFilesTimestamps
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

# obviously some user might have updated three months later, but this is the rough v474 release time (2022-02-16)
TIMESTAMP_MS_WHEN_WE_STARTED_TRACKING_ARCHIVED_TIMES = 1644991200000

class ClientDBFilesInbox( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_files_metadata_timestamps: ClientDBFilesTimestamps.ClientDBFilesTimestamps
    ):
        
        self.modules_services = modules_services
        self.modules_files_storage = modules_files_storage
        self.modules_files_metadata_timestamps = modules_files_metadata_timestamps
        
        self.inbox_hash_ids = set()
        
        super().__init__( 'client files inbox', cursor )
        
        self._InitCaches()
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.file_inbox' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 400 )
        }
        
    
    def _InitCaches( self ):
        
        # TODO: see about making this guy a 'property' or whatever and initialising on first request?
        # this, otherwise, is asking it on every reconnection, which is not ideal
        if self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'file_inbox', ) ).fetchone() is not None:
            
            self.inbox_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM file_inbox;' ) )
            
        
    
    def ArchiveFiles( self, hash_ids ):
        
        if not isinstance( hash_ids, set ):
            
            hash_ids = set( hash_ids )
            
        
        archiveable_hash_ids = hash_ids.intersection( self.inbox_hash_ids )
        
        if len( archiveable_hash_ids ) > 0:
            
            self._ExecuteMany( 'DELETE FROM file_inbox WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in archiveable_hash_ids ) )
            
            self.inbox_hash_ids.difference_update( archiveable_hash_ids )
            
            now_ms = HydrusTime.GetNowMS()
            
            self.modules_files_metadata_timestamps.SetSimpleTimestampsMS( HC.TIMESTAMP_TYPE_ARCHIVED, [ ( hash_id, now_ms ) for hash_id in archiveable_hash_ids ] )
            
            service_ids_to_counts = self.modules_files_storage.GetServiceIdCounts( archiveable_hash_ids )
            
            update_rows = list( service_ids_to_counts.items() )
            
            self._ExecuteMany( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in update_rows ] )
            
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'file_inbox', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
    def InboxFiles( self, hash_ids: collections.abc.Collection[ int ] ):
        
        if not isinstance( hash_ids, set ):
            
            hash_ids = set( hash_ids )
            
        
        location_context = ClientLocation.LocationContext( current_service_keys = ( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ) )
        
        hash_ids = self.modules_files_storage.FilterHashIds( location_context, hash_ids )
        
        inboxable_hash_ids = hash_ids.difference( self.inbox_hash_ids )
        
        if len( inboxable_hash_ids ) > 0:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO file_inbox VALUES ( ? );', ( ( hash_id, ) for hash_id in inboxable_hash_ids ) )
            
            self.inbox_hash_ids.update( inboxable_hash_ids )
            
            self.modules_files_metadata_timestamps.ClearArchivedTimes( inboxable_hash_ids )
            
            service_ids_to_counts = self.modules_files_storage.GetServiceIdCounts( inboxable_hash_ids )
            
            if len( service_ids_to_counts ) > 0:
                
                self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in service_ids_to_counts.items() ] )
                
            
        
    
    def FillInMissingImportArchiveTimestamps( self, job_status: ClientThreading.JobStatus | None = None ):
        
        if job_status is not None:
            
            job_status.SetStatusText( 'missing import archive timestamps' )
            
        
        import_lambda = lambda timestamp: timestamp > TIMESTAMP_MS_WHEN_WE_STARTED_TRACKING_ARCHIVED_TIMES
        
        num_fixed = 0
        
        for ( hash_id, imported_timestamp_ms, deleted_timestamp_ms ) in self._IterateMissingArchiveTimestampData( import_lambda, job_status = job_status ):
            
            if imported_timestamp_ms is None:
                
                continue
                
            
            self.modules_files_metadata_timestamps.SetSimpleTimestampsMS( HC.TIMESTAMP_TYPE_ARCHIVED, [ ( hash_id, imported_timestamp_ms ) ] )
            
            HydrusData.Print( f'Filling in import archive time for {hash_id}: {imported_timestamp_ms}!' )
            
            num_fixed += 1
            
            if job_status is not None:
                
                job_status.SetStatusText( f'missing import archive timestamps: {HydrusNumbers.ToHumanInt(num_fixed)} fixed' )
                
            
        
        if num_fixed > 0:
            
            HydrusData.ShowText( f'{HydrusNumbers.ToHumanInt( num_fixed )} missing import archive times fixed!' )
            
        
        if job_status is not None:
            
            job_status.DeleteStatusText()
            
        
    
    def FillInMissingLegacyArchiveTimestamps( self, job_status: ClientThreading.JobStatus | None = None ):
        
        if job_status is not None:
            
            job_status.SetStatusText( 'missing legacy archive timestamps' )
            
        
        legacy_lambda = lambda timestamp: timestamp < TIMESTAMP_MS_WHEN_WE_STARTED_TRACKING_ARCHIVED_TIMES
        
        num_fixed = 0
        
        for ( hash_id, imported_timestamp_ms, deleted_timestamp_ms ) in self._IterateMissingArchiveTimestampData( legacy_lambda, job_status = job_status ):
            
            if imported_timestamp_ms is None:
                
                continue
                
            
            if deleted_timestamp_ms is None:
                
                endpoint_timestamp_ms = TIMESTAMP_MS_WHEN_WE_STARTED_TRACKING_ARCHIVED_TIMES
                
            else:
                
                endpoint_timestamp_ms = deleted_timestamp_ms
                
            
            if imported_timestamp_ms > endpoint_timestamp_ms:
                
                continue
                
            
            archive_time_ms = int( imported_timestamp_ms + ( ( endpoint_timestamp_ms - imported_timestamp_ms ) / 5 ) )
            
            self.modules_files_metadata_timestamps.SetSimpleTimestampsMS( HC.TIMESTAMP_TYPE_ARCHIVED, [ ( hash_id, archive_time_ms ) ] )
            
            HydrusData.Print( f'Filling in legacy archive time for {hash_id}: {archive_time_ms}!' )
            
            num_fixed += 1
            
            if job_status is not None:
                
                job_status.SetStatusText( f'missing legacy archive timestamps: {HydrusNumbers.ToHumanInt(num_fixed)} fixed' )
                
            
        
        if num_fixed > 0:
            
            HydrusData.ShowText( f'{HydrusNumbers.ToHumanInt( num_fixed )} missing legacy archive times fixed!' )
            
        
        if job_status is not None:
            
            job_status.DeleteStatusText()
            
        
    
    def _IterateMissingArchiveTimestampData( self, import_timestamp_lambda = None, job_status: ClientThreading.JobStatus | None = None ):
        
        try:
            
            # are there any non-inbox local files or any deleted files for which we have an import time (actual or deletion memory) before the magic time for which there is no accompanying archive time? 
            
            # current media PLUS current trash
            current_hash_ids = set( self.modules_files_storage.GetCurrentHashIdsList( self.modules_services.combined_local_file_domains_service_id ) )
            current_hash_ids.update( self.modules_files_storage.GetCurrentHashIdsList( self.modules_services.trash_service_id ) )
            
            current_archived_hash_ids = current_hash_ids.difference( self.inbox_hash_ids )
            
            BLOCK_SIZE = 4096
            
            for ( num_done, num_to_do, batch_of_hash_ids ) in HydrusLists.SplitListIntoChunksRich( current_archived_hash_ids, BLOCK_SIZE ):
                
                message = f'Searching current files: {HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}'
                
                CG.client_controller.frame_splash_status.SetSubtext( message )
                
                if job_status is not None:
                    
                    job_status.SetStatusText( message, level = 2 )
                    job_status.SetGauge( num_done, num_to_do, level = 2 )
                    
                    if job_status.IsCancelled():
                        
                        return
                        
                    
                
                batch_of_hash_ids_to_current_timestamps_ms = self.modules_files_storage.GetCurrentHashIdsToTimestampsMS( self.modules_services.hydrus_local_file_storage_service_id, batch_of_hash_ids )
                
                batch_of_hash_ids_to_current_timestamps_ms = { hash_id : timestamp for ( hash_id, timestamp ) in batch_of_hash_ids_to_current_timestamps_ms.items() if timestamp is not None }
                
                if import_timestamp_lambda is not None:
                    
                    batch_of_hash_ids_to_current_timestamps_ms = { hash_id : timestamp for ( hash_id, timestamp ) in batch_of_hash_ids_to_current_timestamps_ms.items() if import_timestamp_lambda( timestamp ) }
                    
                
                filtered_batch_of_hash_ids = set( batch_of_hash_ids_to_current_timestamps_ms.keys() )
                
                hash_ids_to_archived_timestamps = self.modules_files_metadata_timestamps.GetHashIdsToArchivedTimestampsMS( filtered_batch_of_hash_ids )
                
                for ( hash_id, current_timestamp_ms ) in batch_of_hash_ids_to_current_timestamps_ms.items():
                    
                    if hash_ids_to_archived_timestamps[ hash_id ] is None:
                        
                        yield ( hash_id, current_timestamp_ms, None )
                        
                    
                
            
            #
            
            # deleted from my media EX current trash. these are all archived
            deleted_hash_ids = set( self.modules_files_storage.GetDeletedHashIdsList( self.modules_services.combined_local_file_domains_service_id ) )
            deleted_hash_ids.difference_update( self.modules_files_storage.GetCurrentHashIdsList( self.modules_services.trash_service_id ) )
            
            BLOCK_SIZE = 4096
            
            for ( num_done, num_to_do, batch_of_hash_ids ) in HydrusLists.SplitListIntoChunksRich( deleted_hash_ids, BLOCK_SIZE ):
                
                message = f'Searching deleted files: {HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}'
                
                CG.client_controller.frame_splash_status.SetSubtext( message )
                
                if job_status is not None:
                    
                    job_status.SetStatusText( message, level = 2 )
                    job_status.SetGauge( num_done, num_to_do, level = 2 )
                    
                    if job_status.IsCancelled():
                        
                        return
                        
                    
                
                batch_of_hash_ids_to_deleted_timestamps_ms = self.modules_files_storage.GetDeletedHashIdsToTimestampsMS( self.modules_services.combined_local_file_domains_service_id, batch_of_hash_ids )
                
                batch_of_hash_ids_to_deleted_timestamps_ms = { hash_id : ( deleted_timestamp_ms, original_import_timestamp_ms ) for ( hash_id, ( deleted_timestamp_ms, original_import_timestamp_ms ) ) in batch_of_hash_ids_to_deleted_timestamps_ms.items() if original_import_timestamp_ms is not None }
                
                if import_timestamp_lambda is not None:
                    
                    batch_of_hash_ids_to_deleted_timestamps_ms = { hash_id : ( deleted_timestamp_ms, original_import_timestamp_ms ) for ( hash_id, ( deleted_timestamp_ms, original_import_timestamp_ms ) ) in batch_of_hash_ids_to_deleted_timestamps_ms.items() if import_timestamp_lambda( original_import_timestamp_ms ) }
                    
                
                filtered_batch_of_hash_ids = set( batch_of_hash_ids_to_deleted_timestamps_ms.keys() )
                
                hash_ids_to_archived_timestamps = self.modules_files_metadata_timestamps.GetHashIdsToArchivedTimestampsMS( filtered_batch_of_hash_ids )
                
                for ( hash_id, ( deleted_timestamp_ms, original_import_timestamp_ms ) ) in batch_of_hash_ids_to_deleted_timestamps_ms.items():
                    
                    if hash_ids_to_archived_timestamps[ hash_id ] is None:
                        
                        yield ( hash_id, original_import_timestamp_ms, deleted_timestamp_ms )
                        
                    
                
            
        finally:
            
            CG.client_controller.frame_splash_status.SetSubtext( '' )
            
            if job_status is not None:
                
                job_status.DeleteStatusText( level = 2 )
                job_status.DeleteGauge( level = 2 )
                
            
        
    
    def NumMissingImportArchiveTimestamps( self, job_status: ClientThreading.JobStatus | None = None ) -> int:
        
        if job_status is not None:
            
            job_status.SetStatusText( 'scanning for missing import archive timestamps' )
            
        
        try:
            
            num = 0
            
            import_lambda = lambda timestamp: timestamp > TIMESTAMP_MS_WHEN_WE_STARTED_TRACKING_ARCHIVED_TIMES
            
            for item in self._IterateMissingArchiveTimestampData( import_lambda, job_status = job_status ):
                
                num += 1
                
            
            return num
            
        finally:
            
            if job_status is not None:
                
                job_status.DeleteStatusText()
                
            
        
    
    def NumMissingLegacyArchiveTimestamps( self, job_status: ClientThreading.JobStatus | None = None ) -> int:
        
        if job_status is not None:
            
            job_status.SetStatusText( 'scanning for missing legacy archive timestamps' )
            
        
        try:
            
            num = 0
            
            legacy_lambda = lambda timestamp: timestamp < TIMESTAMP_MS_WHEN_WE_STARTED_TRACKING_ARCHIVED_TIMES
            
            for item in self._IterateMissingArchiveTimestampData( legacy_lambda, job_status = job_status ):
                
                num += 1
                
            
            return num
            
        finally:
            
            if job_status is not None:
                
                job_status.DeleteStatusText()
                
            
        
    
    def WeHaveMissingImportArchiveTimestamps( self, job_status: ClientThreading.JobStatus | None = None ) -> bool:
        
        if job_status is not None:
            
            job_status.SetStatusText( 'scanning for missing import archive timestamps' )
            
        
        try:
            
            import_lambda = lambda timestamp: timestamp > TIMESTAMP_MS_WHEN_WE_STARTED_TRACKING_ARCHIVED_TIMES
            
            for item in self._IterateMissingArchiveTimestampData( import_lambda, job_status = job_status ):
                
                return True
                
            
            return False
            
        finally:
            
            if job_status is not None:
                
                job_status.DeleteStatusText()
                
            
        
    
    def WeHaveMissingLegacyArchiveTimestamps( self, job_status: ClientThreading.JobStatus | None = None ) -> bool:
        
        if job_status is not None:
            
            job_status.SetStatusText( 'scanning for missing legacy archive timestamps' )
            
        
        try:
            
            legacy_lambda = lambda timestamp: timestamp < TIMESTAMP_MS_WHEN_WE_STARTED_TRACKING_ARCHIVED_TIMES
            
            for item in self._IterateMissingArchiveTimestampData( legacy_lambda, job_status = job_status ):
                
                return True
                
            
            return False
            
        finally:
            
            if job_status is not None:
                
                job_status.DeleteStatusText()
                
            
        
    
