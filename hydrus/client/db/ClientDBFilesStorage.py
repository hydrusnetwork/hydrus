import collections
import collections.abc
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientTime
from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

FILES_CURRENT_PREFIX = 'current_files_'
FILES_DELETED_PREFIX = 'deleted_files_'
FILES_PENDING_PREFIX = 'pending_files_'
FILES_PETITIONED_PREFIX = 'petitioned_files_'

def GenerateFilesTableNames( service_id: int ) -> tuple[ str, str, str, str ]:
    
    suffix = str( service_id )
    
    current_files_table_name = f'main.{FILES_CURRENT_PREFIX}{suffix}'
    
    deleted_files_table_name = f'main.{FILES_DELETED_PREFIX}{suffix}'
    
    pending_files_table_name = f'main.{FILES_PENDING_PREFIX}{suffix}'
    
    petitioned_files_table_name = f'main.{FILES_PETITIONED_PREFIX}{suffix}'
    
    return ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name )
    

def GenerateFilesTableName( service_id: int, status: int ) -> str:
    
    ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
    
    if status == HC.CONTENT_STATUS_CURRENT:
        
        return current_files_table_name
        
    elif status == HC.CONTENT_STATUS_DELETED:
        
        return deleted_files_table_name
        
    elif status == HC.CONTENT_STATUS_PENDING:
        
        return pending_files_table_name
        
    else:
        
        return petitioned_files_table_name
        
    

class DBLocationContext( object ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, *args, **kwargs ):
        
        self.location_context = location_context
        
        super().__init__( *args, **kwargs )
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self.location_context
        
    
    def GetMultipleFilesTableNames( self ):
        
        raise HydrusExceptions.DataMissing( 'Sorry, this DB Location Context has no multiple file tables!' )
        
    
    def GetSingleFilesTableName( self ):
        
        raise HydrusExceptions.DataMissing( 'Sorry, this DB Location Context has no single file table!' )
        
    
    def GetTableJoinIteratedByFileDomain( self, table_phrase: str ) -> str:
        
        raise NotImplementedError()
        
    
    def GetTableJoinLimitedByFileDomain( self, table_phrase: str ) -> str:
        
        raise NotImplementedError()
        
    
    def SingleTableIsFast( self ) -> bool:
        
        return False
        
    

class DBLocationContextAllKnownFiles( DBLocationContext ):
    
    def GetTableJoinIteratedByFileDomain( self, table_phrase: str ) -> str:
        
        return table_phrase
        
    
    def GetTableJoinLimitedByFileDomain( self, table_phrase: str ) -> str:
        
        return table_phrase
        
    

class DBLocationContextLeaf( DBLocationContext ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, files_table_name: str ):
        
        super().__init__( location_context )
        
        self._files_table_name = files_table_name
        
    
    def GetMultipleFilesTableNames( self ):
        
        return [ self.GetSingleFilesTableName() ]
        
    
    def GetSingleFilesTableName( self ):
        
        return self._files_table_name
        
    
    def GetTableJoinIteratedByFileDomain( self, table_phrase: str ) -> str:
        
        return '{} CROSS JOIN {} USING ( hash_id )'.format( self._files_table_name, table_phrase )
        
    
    def GetTableJoinLimitedByFileDomain( self, table_phrase: str ) -> str:
        
        return '{} CROSS JOIN {} USING ( hash_id )'.format( table_phrase, self._files_table_name )
        
    
    def SingleTableIsFast( self ) -> bool:
        
        return True
        
    

class DBLocationContextBranch( DBLocationContext, ClientDBModule.ClientDBModule ):
    
    # this still sucks and should be random and then dropped neatly by a manager or something so we can have more than one of these guys at once
    SINGLE_TABLE_NAME = 'mem.temp_file_storage_hash_id'
    
    def __init__( self, cursor: sqlite3.Cursor, location_context: ClientLocation.LocationContext, files_table_names: collections.abc.Collection[ str ] ):
        
        super().__init__( location_context, 'db location (branch)', cursor )
        
        self._files_table_names = files_table_names
        self._single_table_initialised = False
        
    
    def _InitialiseSingleTableIfNeeded( self ):
        
        if self._single_table_initialised:
            
            return
            
        
        result = self._Execute( 'SELECT 1 FROM mem.sqlite_master WHERE name = ?;', ( self.SINGLE_TABLE_NAME, ) ).fetchone()
        
        if result is None:
            
            self._Execute( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );'.format( self.SINGLE_TABLE_NAME ) )
            
        else:
            
            self._Execute( 'DELETE FROM {};'.format( self.SINGLE_TABLE_NAME ) )
            
        
        select_query = ' UNION '.join( ( 'SELECT hash_id FROM {}'.format( table_name ) for table_name in self._files_table_names ) )
        
        # these notes are old and transplanted from a previous creation method that prepopulated the table and sent it to this class already made. now it happens on demand
        # feel free to clear out or reconsider, but my current feeling is we have to bite the bullet a little here. best use of time is working on gettablejoiniterated/limitedby. the callers there may be ok with multiple access too
        #
        # ok, so I _can_ just go:
        #
        # files_table_name = '({})'.format( select_query )
        #
        # here and not populate an actual temp table. basically making a VIEW. this seems to be SEARCH for two tables and SCAN for three or more, at least on newer SQLite. I'm pretty sure older SQLite has trouble optimising
        # so it is potentially super fast, but worst case is really bad since that SCAN will happen over and over
        # the temp table population puts a fixed one-time SCAN overhead so is lame but stable
        # the ideal answer is to rewrite all dblocationcontext code to handle multiple table names. this isn't possible for some requests like duplicates, although honestly they could do the table population themselves
        # THE ANSWER: since that is more complicated, what I really need is a new subclass of DBLocationClass object that can handle more complicated situations, write a method for single/multiple,
        # and if the consumer needs the single (as some dupe code does), then the class itself borrows a temp table name from a manager class, like tempinttables, and populates it there and then
        # MOVING THIS STUFF TO THIS NEW BRANCH OBJECT IS THIS WORK, MORE CAN BE DONE
        #
        # another possible solution might be another file table that I always keep synced, maybe something like ( hash_id, service_id, status ). that might be quickly searchable as a VIEW. quicker than this anyway
        # some experimentation with this results in some really bad worst case query planning at times. most of the time it is great, but sometimes it can't figure out the hash_id as the thing to SEARCH with
        #
        # another idea, if we are going to end up adding 'sync' code, is to have multiple not-so-temp tables for different service combinations and then just invalidate them (or even update them) on file changes
        # we can just re-use them mate
        
        self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id ) {};'.format( self.SINGLE_TABLE_NAME, select_query ) )
        
        self._single_table_initialised = True
        
    
    def GetMultipleFilesTableNames( self ):
        
        return self._files_table_names
        
    
    def GetSingleFilesTableName( self ):
        
        self._InitialiseSingleTableIfNeeded()
        
        return self.SINGLE_TABLE_NAME
        
    
    def GetTableJoinIteratedByFileDomain( self, table_phrase: str ) -> str:
        
        self._InitialiseSingleTableIfNeeded()
        
        return '{} CROSS JOIN {} USING ( hash_id )'.format( self.SINGLE_TABLE_NAME, table_phrase )
        
    
    def GetTableJoinLimitedByFileDomain( self, table_phrase: str ) -> str:
        
        self._InitialiseSingleTableIfNeeded()
        
        return '{} CROSS JOIN {} USING ( hash_id )'.format( table_phrase, self.SINGLE_TABLE_NAME )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        return []
        
    
    def SingleTableIsFast( self ) -> bool:
        
        return False
        
    

class ClientDBFilesStorage( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper, modules_db_maintenance: ClientDBMaintenance.ClientDBMaintenance, modules_services: ClientDBServices.ClientDBMasterServices, modules_hashes: ClientDBMaster.ClientDBMasterHashes, modules_texts: ClientDBMaster.ClientDBMasterTexts ):
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_db_maintenance = modules_db_maintenance
        self.modules_services = modules_services
        self.modules_hashes = modules_hashes
        self.modules_texts = modules_texts
        
        super().__init__( 'client file locations', cursor )
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.local_file_deletion_reasons' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, reason_id INTEGER );', 400 ),
            'main.deferred_physical_file_deletes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 464 ),
            'main.deferred_physical_thumbnail_deletes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 464 )
            
        }
        
    
    def _GetServiceIndexGenerationDict( self, service_id ) -> dict:
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        index_generation_dict = {}
        
        index_generation_dict[ current_files_table_name ] = [
            ( [ 'timestamp_ms' ], False, 559 )
        ]
        
        index_generation_dict[ deleted_files_table_name ] = [
            ( [ 'timestamp_ms' ], False, 559 ),
            ( [ 'original_timestamp_ms' ], False, 559 )
        ]
        
        index_generation_dict[ petitioned_files_table_name ] = [
            ( [ 'reason_id' ], False, 447 )
        ]
        
        return index_generation_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        return {
            current_files_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, timestamp_ms INTEGER );', 447 ),
            deleted_files_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, timestamp_ms INTEGER, original_timestamp_ms INTEGER );', 447 ),
            pending_files_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 447 ),
            petitioned_files_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, reason_id INTEGER );', 447 )
        }
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return self.modules_services.GetServiceIds( HC.REAL_FILE_SERVICES )
        
    
    def _GetServiceTablePrefixes( self ):
        
        return {
            FILES_CURRENT_PREFIX,
            FILES_DELETED_PREFIX,
            FILES_PENDING_PREFIX,
            FILES_PETITIONED_PREFIX
        }
        
    
    def _GetTimestampMS( self, service_id: int, timestamp_type: int, hash_id: int ) -> int | None:
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        result = None
        
        if timestamp_type == HC.TIMESTAMP_TYPE_IMPORTED:
            
            result = self._Execute( 'SELECT timestamp_ms FROM {} WHERE hash_id = ?;'.format( current_files_table_name ), ( hash_id, ) ).fetchone()
            
        elif timestamp_type == HC.TIMESTAMP_TYPE_DELETED:
            
            result = self._Execute( 'SELECT timestamp_ms FROM {} WHERE hash_id = ?;'.format( deleted_files_table_name ), ( hash_id, ) ).fetchone()
            
        elif timestamp_type == HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED:
            
            result = self._Execute( 'SELECT original_timestamp_ms FROM {} WHERE hash_id = ?;'.format( deleted_files_table_name ), ( hash_id, ) ).fetchone()
            
        
        if result is None:
            
            return None
            
        else:
            
            ( timestamp_ms, ) = result
            
            return timestamp_ms
            
        
    
    def AddFiles( self, service_id, insert_rows ):
        
        # just a note, the timestamp in insert_rows can be None
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} VALUES ( ?, ? );'.format( current_files_table_name ), ( ( hash_id, timestamp_ms ) for ( hash_id, timestamp_ms ) in insert_rows ) )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( pending_files_table_name ), ( ( hash_id, ) for ( hash_id, timestamp_ms ) in insert_rows ) )
        
        pending_changed = self._GetRowCount() > 0
        
        if service_id == self.modules_services.hydrus_local_file_storage_service_id:
            
            for ( hash_id, timestamp_ms ) in insert_rows:
                
                self.ClearDeferredPhysicalDeleteIds( file_hash_id = hash_id, thumbnail_hash_id = hash_id )
                
            
        elif self.modules_services.GetService( service_id ).GetServiceType() in ( HC.FILE_REPOSITORY, HC.IPFS ):
            
            # it may be the case the files were just uploaded after being deleted
            self.DeferFilesDeleteIfNowOrphan( [ hash_id for ( hash_id, timestamp_ms ) in insert_rows ] )
            
        
        return pending_changed
        
    
    def ClearDeferredPhysicalDelete( self, file_hash = None, thumbnail_hash = None ):
        
        file_hash_id = None if file_hash is None else self.modules_hashes.GetHashId( file_hash )
        thumbnail_hash_id = None if thumbnail_hash is None else self.modules_hashes.GetHashId( thumbnail_hash )
        
        self.ClearDeferredPhysicalDeleteIds( file_hash_id = file_hash_id, thumbnail_hash_id = thumbnail_hash_id )
        
    
    def ClearDeferredPhysicalDeleteIds( self, file_hash_id = None, thumbnail_hash_id = None ):
        
        if file_hash_id is not None:
            
            self._Execute( 'DELETE FROM deferred_physical_file_deletes WHERE hash_id = ?;', ( file_hash_id, ) )
            
        
        if thumbnail_hash_id is not None:
            
            self._Execute( 'DELETE FROM deferred_physical_thumbnail_deletes WHERE hash_id = ?;', ( thumbnail_hash_id, ) )
            
        
    
    def ClearDeleteRecord( self, service_id, hash_ids ):
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( deleted_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
        num_deleted = self._GetRowCount()
        
        return num_deleted
        
    
    def ClearFileDeletionReason( self, hash_ids ):
        
        self._ExecuteMany( 'DELETE FROM local_file_deletion_reasons WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def ClearFilesTables( self, service_id: int, keep_pending = False ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        self._Execute( 'DELETE FROM {};'.format( current_files_table_name ) )
        self._Execute( 'DELETE FROM {};'.format( deleted_files_table_name ) )
        
        if not keep_pending:
            
            self._Execute( 'DELETE FROM {};'.format( pending_files_table_name ) )
            
        
        self._Execute( 'DELETE FROM {};'.format( petitioned_files_table_name ) )
        
    
    def ClearLocalDeleteRecord( self, hash_ids = None ):
        
        # Just as a side note, this guy should be accompanied by calls to SyncCombinedDeletedFiles above; this module can't do proper add/delete with mappings and stuff, so just this guy isn't enough
        
        # we delete from everywhere, but not for files currently in the trash
        
        service_ids_to_nums_cleared = {}
        
        local_non_trash_service_types = { HC.HYDRUS_LOCAL_FILE_STORAGE, HC.COMBINED_LOCAL_FILE_DOMAINS, HC.LOCAL_FILE_DOMAIN }
        
        local_non_trash_service_ids = self.modules_services.GetServiceIds( local_non_trash_service_types )
        
        if hash_ids is None:
            
            trash_current_files_table_name = GenerateFilesTableName( self.modules_services.trash_service_id, HC.CONTENT_STATUS_CURRENT )
            
            for service_id in local_non_trash_service_ids:
                
                deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
                
                self._Execute( 'DELETE FROM {} WHERE hash_id NOT IN ( SELECT hash_id FROM {} );'.format( deleted_files_table_name, trash_current_files_table_name ) )
                
                num_cleared = self._GetRowCount()
                
                service_ids_to_nums_cleared[ service_id ] = num_cleared
                
            
            self._Execute( 'DELETE FROM local_file_deletion_reasons WHERE hash_id NOT IN ( SELECT hash_id FROM {} );'.format( trash_current_files_table_name ) )
            
        else:
            
            trashed_hash_ids = self.FilterHashIdsToStatus( self.modules_services.trash_service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
            
            ok_to_clear_hash_ids = set( hash_ids ).difference( trashed_hash_ids )
            
            if len( ok_to_clear_hash_ids ) > 0:
                
                for service_id in local_non_trash_service_ids:
                    
                    deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
                    
                    self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( deleted_files_table_name ), ( ( hash_id, ) for hash_id in ok_to_clear_hash_ids ) )
                    
                    num_cleared = self._GetRowCount()
                    
                    service_ids_to_nums_cleared[ service_id ] = num_cleared
                    
                
                self.ClearFileDeletionReason( ok_to_clear_hash_ids )
                
            
        
        return service_ids_to_nums_cleared
        
    
    def DeferFilesDeleteIfNowOrphan( self, hash_ids, definitely_no_thumbnails = False, ignore_service_id = None ):
        
        orphan_hash_ids = self.FilterOrphanFileHashIds( hash_ids, ignore_service_id = ignore_service_id )
        
        if len( orphan_hash_ids ) > 0:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO deferred_physical_file_deletes ( hash_id ) VALUES ( ? );', ( ( hash_id, ) for hash_id in orphan_hash_ids ) )
            
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_physical_file_deletes' )
            self._cursor_transaction_wrapper.pub_after_job( 'notify_new_physical_file_delete_numbers' )
            
        
        if not definitely_no_thumbnails:
            
            orphan_hash_ids = self.FilterOrphanThumbnailHashIds( hash_ids, ignore_service_id = ignore_service_id )
            
            if len( orphan_hash_ids ) > 0:
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO deferred_physical_thumbnail_deletes ( hash_id ) VALUES ( ? );', ( ( hash_id, ) for hash_id in orphan_hash_ids ) )
                
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_physical_file_deletes' )
                self._cursor_transaction_wrapper.pub_after_job( 'notify_new_physical_file_delete_numbers' )
                
            
        
    
    def DeletePending( self, service_id: int ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        if self.modules_services.GetService( service_id ).GetServiceType() == HC.FILE_REPOSITORY:
            
            for ( block_of_hash_ids, num_done, num_to_do ) in HydrusDB.ReadLargeIdQueryInSeparateChunks( self._c, 'SELECT hash_id FROM {};'.format( pending_files_table_name ), 1024 ):
                
                self.DeferFilesDeleteIfNowOrphan( block_of_hash_ids, ignore_service_id = service_id )
                
            
        
        self._Execute( 'DELETE FROM {};'.format( pending_files_table_name ) )
        self._Execute( 'DELETE FROM {};'.format( petitioned_files_table_name ) )
        
    
    def DropFilesTables( self, service_id: int ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        if self.modules_services.GetService( service_id ).GetServiceType() == HC.FILE_REPOSITORY:
            
            for ( block_of_hash_ids, num_done, num_to_do ) in HydrusDB.ReadLargeIdQueryInSeparateChunks( self._c, 'SELECT hash_id FROM {};'.format( pending_files_table_name ), 1024 ):
                
                self.DeferFilesDeleteIfNowOrphan( block_of_hash_ids, ignore_service_id = service_id )
                
            
        
        self.modules_db_maintenance.DeferredDropTable( current_files_table_name )
        self.modules_db_maintenance.DeferredDropTable( deleted_files_table_name )
        self.modules_db_maintenance.DeferredDropTable( pending_files_table_name )
        self.modules_db_maintenance.DeferredDropTable( petitioned_files_table_name )
        
    
    def FilterAllCurrentHashIds( self, hash_ids, just_these_service_ids = None ):
        
        if just_these_service_ids is None:
            
            service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
        else:
            
            service_ids = just_these_service_ids
            
        
        current_hash_ids = set()
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            for service_id in service_ids:
                
                current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
                
                hash_id_iterator = self._STI( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ) )
                
                current_hash_ids.update( hash_id_iterator )
                
            
        
        return current_hash_ids
        
    
    def FilterAllLocalHashIds( self, hash_ids ):
        
        return self.FilterAllCurrentHashIds( hash_ids, ( self.modules_services.hydrus_local_file_storage_service_id, ) )
        
    
    def FilterAllPendingHashIds( self, hash_ids, just_these_service_ids = None ):
        
        if just_these_service_ids is None:
            
            service_ids = self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
            
        else:
            
            service_ids = just_these_service_ids
            
        
        pending_hash_ids = set()
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            for service_id in service_ids:
                
                pending_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PENDING )
                
                hash_id_iterator = self._STI( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, pending_files_table_name ) ) )
                
                pending_hash_ids.update( hash_id_iterator )
                
            
        
        return pending_hash_ids
        
    
    def FilterHashIds( self, location_context: ClientLocation.LocationContext, hash_ids ) -> set:
        
        if location_context.IsEmpty():
            
            return set()
            
        
        if location_context.IsAllKnownFiles():
            
            return hash_ids
            
        
        filtered_hash_ids = set()
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            for file_service_key in location_context.current_service_keys:
                
                service_id = self.modules_services.GetServiceId( file_service_key )
                
                current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
                
                matching_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ) )
                
                if len( matching_hash_ids ) > 0:
                    
                    filtered_hash_ids.update( matching_hash_ids )
                    
                    if len( filtered_hash_ids ) == len( hash_ids ):
                        
                        return filtered_hash_ids
                        
                    
                    self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( temp_hash_ids_table_name ), ( ( hash_id, ) for hash_id in matching_hash_ids ) )
                    
                
            
            for file_service_key in location_context.deleted_service_keys:
                
                service_id = self.modules_services.GetServiceId( file_service_key )
                
                deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
                
                matching_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, deleted_files_table_name ) ) )
                
                if len( matching_hash_ids ) > 0:
                    
                    filtered_hash_ids.update( matching_hash_ids )
                    
                    if len( filtered_hash_ids ) == len( hash_ids ):
                        
                        return filtered_hash_ids
                        
                    
                    self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( temp_hash_ids_table_name ), ( ( hash_id, ) for hash_id in matching_hash_ids ) )
                    
                
            
        
        return filtered_hash_ids
        
    
    def FilterHashIdsToStatus( self, service_id, hash_ids, status ) -> set[ int ]:
        
        if service_id == self.modules_services.combined_file_service_id:
            
            if status == HC.CONTENT_STATUS_CURRENT:
                
                return set( hash_ids )
                
            else:
                
                return set()
                
            
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            files_table_name = GenerateFilesTableName( service_id, status )
            
            result_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, files_table_name ) ) )
            
        
        return result_hash_ids
        
    
    def FilterOrphanFileHashIds( self, hash_ids, ignore_service_id = None ):
        
        useful_hash_ids = self.FilterHashIdsToStatus( self.modules_services.hydrus_local_file_storage_service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
        
        orphan_hash_ids = set( hash_ids ).difference( useful_hash_ids )
        
        if len( orphan_hash_ids ) > 0:
            
            just_these_service_ids = self.modules_services.GetServiceIds( ( HC.FILE_REPOSITORY, HC.IPFS ) )
            
            if ignore_service_id is not None:
                
                just_these_service_ids.discard( ignore_service_id )
                
            
            # anything pending upload somewhere, we want to keep
            useful_hash_ids = self.FilterAllPendingHashIds( orphan_hash_ids, just_these_service_ids = just_these_service_ids )
            
            orphan_hash_ids.difference_update( useful_hash_ids )
            
        
        return orphan_hash_ids
        
    
    def FilterOrphanThumbnailHashIds( self, hash_ids, ignore_service_id = None ):
        
        services = self.modules_services.GetServices( ( HC.HYDRUS_LOCAL_FILE_STORAGE, HC.FILE_REPOSITORY ) )
        
        current_service_keys = [ service.GetServiceKey() for service in services ]
        
        if ignore_service_id is not None:
            
            service = self.modules_services.GetService( ignore_service_id )
            
            ignore_service_key = service.GetServiceKey()
            
            if ignore_service_key in current_service_keys:
                
                current_service_keys.remove( ignore_service_key )
                
            
        
        location_context = ClientLocation.LocationContext.STATICCreateAllCurrent( current_service_keys )
        
        current_hash_ids = self.FilterHashIds( location_context, hash_ids )
        
        orphan_hash_ids = set( hash_ids ).difference( current_hash_ids )
        
        if len( orphan_hash_ids ) > 0:
            
            just_these_service_ids = self.modules_services.GetServiceIds( ( HC.FILE_REPOSITORY, ) )
            
            if ignore_service_id is not None:
                
                just_these_service_ids.discard( ignore_service_id )
                
            
            # anything pending upload somewhere, we want to keep since we'll be wanting the thumb soon anyway
            useful_hash_ids = self.FilterAllPendingHashIds( orphan_hash_ids, just_these_service_ids = just_these_service_ids )
            
            orphan_hash_ids.difference_update( useful_hash_ids )
            
        
        # we could try and be clever and say "and then filter xxx by 'mimes with thumbnails' using files_info", but let's not get too ahead of ourselves
        # the places where the difference would matter, like some client going back to an earlier version where .clips no longer have thumbs on a file repo, are complicated and would have little benefit when correct
        # no need to sharpen that knife too much
        
        return orphan_hash_ids
        
    
    def GenerateFilesTables( self, service_id: int ):
        
        table_generation_dict = self._GetServiceTableGenerationDict( service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._CreateTable( create_query_without_name, table_name )
            
        
        index_generation_dict = self._GetServiceIndexGenerationDict( service_id )
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
    def GetAPendingHashId( self, service_id ):
        
        pending_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PENDING )
        
        result = self._Execute( 'SELECT hash_id FROM {};'.format( pending_files_table_name ) ).fetchone()
        
        if result is None:
            
            return None
            
        else:
            
            ( hash_id, ) = result
            
            return hash_id
            
        
    
    def GetAPetitionedHashId( self, service_id ):
        
        petitioned_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PETITIONED )
        
        result = self._Execute( 'SELECT hash_id FROM {};'.format( petitioned_files_table_name ) ).fetchone()
        
        if result is None:
            
            return None
            
        else:
            
            ( hash_id, ) = result
            
            return hash_id
            
        
    
    def GetCurrentFilesCount( self, service_id, only_viewable = False ):
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        
        if only_viewable:
            
            # hashes to mimes
            result = self._Execute( 'SELECT COUNT( * ) FROM {} CROSS JOIN files_info USING ( hash_id ) WHERE mime IN {};'.format( current_files_table_name, HydrusLists.SplayListForDB( HC.SEARCHABLE_MIMES ) ) ).fetchone()
            
        else:
            
            result = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( current_files_table_name ) ).fetchone()
            
        
        ( count, ) = result
        
        return count
        
    
    def GetCurrentFilesInboxCount( self, service_id ):
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        
        result = self._Execute( 'SELECT COUNT( * ) FROM {} CROSS JOIN file_inbox USING ( hash_id );'.format( current_files_table_name ) ).fetchone()
        
        ( count, ) = result
        
        return count
        
    
    def GetCurrentHashIdsList( self, service_id ):
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        
        hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {};'.format( current_files_table_name ) ) )
        
        return hash_ids
        
    
    def GetCurrentFilesTotalSize( self, service_id ):
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        
        # hashes to size
        result = self._Execute( 'SELECT SUM( size ) FROM {} CROSS JOIN files_info USING ( hash_id );'.format( current_files_table_name ) ).fetchone()
        
        count = self._GetSumResult( result )
        
        return count
        
    
    def GetCurrentHashIdsToTimestampsMS( self, service_id, hash_ids ):
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            results_dict = dict( self._Execute( 'SELECT hash_id, timestamp_ms FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ) )
            
        
        return results_dict
        
    
    def GetDeferredPhysicalDelete( self ):
        
        file_result = self._Execute( 'SELECT hash_id FROM deferred_physical_file_deletes LIMIT 1;' ).fetchone()
        
        if file_result is not None:
            
            ( hash_id, ) = file_result
            
            file_result = self.modules_hashes.GetHash( hash_id )
            
        
        thumbnail_result = self._Execute( 'SELECT hash_id FROM deferred_physical_thumbnail_deletes LIMIT 1;' ).fetchone()
        
        if thumbnail_result is not None:
            
            ( hash_id, ) = thumbnail_result
            
            thumbnail_result = self.modules_hashes.GetHash( hash_id )
            
        
        return ( file_result, thumbnail_result )
        
    
    def GetDeferredPhysicalDeleteCounts( self ):
        
        ( num_files, ) = self._Execute( 'SELECT COUNT( * ) FROM deferred_physical_file_deletes;' ).fetchone()
        ( num_thumbnails, ) = self._Execute( 'SELECT COUNT( * ) FROM deferred_physical_thumbnail_deletes;' ).fetchone()
        
        return ( num_files, num_thumbnails )
        
    
    def GetDeletedFilesCount( self, service_id: int ) -> int:
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        result = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( deleted_files_table_name ) ).fetchone()
        
        ( count, ) = result
        
        return count
        
    
    def GetDeletedHashIdsList( self, service_id ):
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {};'.format( deleted_files_table_name ) ) )
        
        return hash_ids
        
    
    def GetDeletedHashIdsToTimestampsMS( self, service_id, hash_ids ):
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            rows = self._Execute( 'SELECT hash_id, timestamp_ms, original_timestamp_ms FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, deleted_files_table_name ) ).fetchall()
            
        
        return { hash_id : ( timestamp_ms, original_timestamp_ms ) for ( hash_id, timestamp_ms, original_timestamp_ms ) in rows }
        
    
    def GetDeletionStatus( self, service_id, hash_id ):
        
        # can have a value here and just be in trash, so we fetch it whatever the end result
        result = self._Execute( 'SELECT reason_id FROM local_file_deletion_reasons WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            file_deletion_reason = 'Unknown deletion reason.'
            
        else:
            
            ( reason_id, ) = result
            
            file_deletion_reason = self.modules_texts.GetText( reason_id )
            
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        is_deleted = False
        timestamp_ms = None
        
        result = self._Execute( 'SELECT timestamp_ms FROM {} WHERE hash_id = ?;'.format( deleted_files_table_name ), ( hash_id, ) ).fetchone()
        
        if result is not None:
            
            is_deleted = True
            
            ( timestamp_ms, ) = result
            
        
        return ( is_deleted, timestamp_ms, file_deletion_reason )
        
    
    def GetDBLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        if location_context.IsEmpty():
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY )
            
        
        if location_context.IsAllKnownFiles():
            
            # no table set, obviously
            
            return DBLocationContextAllKnownFiles( location_context )
            
        
        table_names = []
        
        for current_service_key in location_context.current_service_keys:
            
            service_id = self.modules_services.GetServiceId( current_service_key )
            
            table_names.append( GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT ) )
            
        
        for deleted_service_key in location_context.deleted_service_keys:
            
            service_id = self.modules_services.GetServiceId( deleted_service_key )
            
            table_names.append( GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED ) )
            
        
        if len( table_names ) == 1:
            
            files_table_name = table_names[0]
            
            return DBLocationContextLeaf( location_context, files_table_name )
            
        else:
            
            return DBLocationContextBranch( self._c, location_context, table_names )
            
        
    
    def GetHashIdsToCurrentServiceIds( self, temp_hash_ids_table_name ):
        
        hash_ids_to_current_file_service_ids = collections.defaultdict( list )
        
        for service_id in self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ):
            
            current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
            
            for hash_id in self._STI( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ) ):
                
                hash_ids_to_current_file_service_ids[ hash_id ].append( service_id )
                
            
        
        return hash_ids_to_current_file_service_ids
        
    
    def GetHashIdsToFileDeletionReasons( self, hash_ids_table_name ):
        
        return dict( self._Execute( 'SELECT hash_id, text FROM {} CROSS JOIN local_file_deletion_reasons USING ( hash_id ) CROSS JOIN texts ON ( reason_id = text_id );'.format( hash_ids_table_name ) ) )
        
    
    def GetHashIdsToServiceInfoDicts( self, temp_hash_ids_table_name ):
        
        hash_ids_to_current_file_service_ids_to_timestamps_ms = collections.defaultdict( dict )
        hash_ids_to_deleted_file_service_ids_to_timestamps_ms = collections.defaultdict( dict )
        hash_ids_to_deleted_file_service_ids_to_previously_imported_timestamps_ms = collections.defaultdict( dict )
        hash_ids_to_pending_file_service_ids = collections.defaultdict( list )
        hash_ids_to_petitioned_file_service_ids = collections.defaultdict( list )
        
        for service_id in self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ):
            
            ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
            
            for ( hash_id, timestamp_ms ) in self._Execute( 'SELECT hash_id, timestamp_ms FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ):
                
                hash_ids_to_current_file_service_ids_to_timestamps_ms[ hash_id ][ service_id ] = timestamp_ms
                
            
            for ( hash_id, timestamp_ms, original_timestamp_ms ) in self._Execute( 'SELECT hash_id, timestamp_ms, original_timestamp_ms FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, deleted_files_table_name ) ):
                
                hash_ids_to_deleted_file_service_ids_to_timestamps_ms[ hash_id ][ service_id ] = timestamp_ms
                hash_ids_to_deleted_file_service_ids_to_previously_imported_timestamps_ms[ hash_id ][ service_id ] = original_timestamp_ms
                
            
            for hash_id in self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, pending_files_table_name ) ):
                
                hash_ids_to_pending_file_service_ids[ hash_id ].append( service_id )
                
            
            for hash_id in self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, petitioned_files_table_name ) ):
                
                hash_ids_to_petitioned_file_service_ids[ hash_id ].append( service_id )
                
            
        
        return (
            hash_ids_to_current_file_service_ids_to_timestamps_ms,
            hash_ids_to_deleted_file_service_ids_to_timestamps_ms,
            hash_ids_to_deleted_file_service_ids_to_previously_imported_timestamps_ms,
            hash_ids_to_pending_file_service_ids,
            hash_ids_to_petitioned_file_service_ids
        )
        
    
    def GetImportedTimestampMS( self, service_id: int, hash_id: int ):
        
        return self._GetTimestampMS( service_id, HC.TIMESTAMP_TYPE_IMPORTED, hash_id )
        
    
    def GetLocationContextForAllServicesDeletedFiles( self ) -> ClientLocation.LocationContext:
        
        deleted_service_keys = { service.GetServiceKey() for service in self.modules_services.GetServices( limited_types = HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE ) }
        
        location_context = ClientLocation.LocationContext( [], deleted_service_keys )
        
        return location_context
        
    
    def GetNumLocal( self, service_id: int ) -> int:
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        combined_local_current_files_table_name = GenerateFilesTableName( self.modules_services.hydrus_local_file_storage_service_id, HC.CONTENT_STATUS_CURRENT )
        
        ( num_local, ) = self._Execute( 'SELECT COUNT( * ) FROM {} CROSS JOIN {} USING ( hash_id );'.format( current_files_table_name, combined_local_current_files_table_name ) ).fetchone()
        
        return num_local
        
    
    def GetPendingFilesCount( self, service_id: int ) -> int:
        
        pending_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PENDING )
        
        result = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( pending_files_table_name ) ).fetchone()
        
        ( count, ) = result
        
        return count
        
    
    def GetPetitionedFilesCount( self, service_id: int ) -> int:
        
        petitioned_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PETITIONED )
        
        result = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( petitioned_files_table_name ) ).fetchone()
        
        ( count, ) = result
        
        return count
        
    
    def GetServiceIdCounts( self, hash_ids ) -> dict[ int, int ]:
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            service_ids_to_counts = {}
            
            for service_id in self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ):
                
                current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
                
                # temp hashes to files
                ( count, ) = self._Execute( 'SELECT COUNT( * ) FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ).fetchone()
                
                service_ids_to_counts[ service_id ] = count
                
            
        
        return service_ids_to_counts
        
    
    def GetSomePetitionedRows( self, service_id: int ):
        
        petitioned_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PETITIONED )
        
        petitioned_rows = list( HydrusData.BuildKeyToListDict( self._Execute( 'SELECT reason_id, hash_id FROM {} ORDER BY reason_id LIMIT 100;'.format( petitioned_files_table_name ) ) ).items() )
        
        return petitioned_rows
        
    
    def GetTableJoinIteratedByFileDomain( self, service_id, table_name, status ):
        
        files_table_name = GenerateFilesTableName( service_id, status )
        
        return '{} CROSS JOIN {} USING ( hash_id )'.format( files_table_name, table_name )
        
    
    def GetTableJoinLimitedByFileDomain( self, service_id, table_name, status ):
        
        files_table_name = GenerateFilesTableName( service_id, status )
        
        return '{} CROSS JOIN {} USING ( hash_id )'.format( table_name, files_table_name )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.extend( [
                ( 'deferred_physical_file_deletes', 'hash_id' ),
                ( 'deferred_physical_thumbnail_deletes', 'hash_id' )
            ] )
            
            for service_id in self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ):
                
                ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
                
                tables_and_columns.extend( [
                    ( current_files_table_name, 'hash_id' ),
                    ( deleted_files_table_name, 'hash_id' ),
                    ( pending_files_table_name, 'hash_id' ),
                    ( petitioned_files_table_name, 'hash_id' )
                ] )
                
            
        
        return tables_and_columns
        
    
    def GetTimestampMS( self, hash_id: int, timestamp_data: ClientTime.TimestampData ) -> int | None:
        
        if timestamp_data.location is None:
            
            return
            
        
        service_key = timestamp_data.location
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        return self._GetTimestampMS( service_id, timestamp_data.timestamp_type, hash_id )
        
    
    def GetUndeleteRows( self, service_id, hash_ids ):
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            rows = self._Execute( 'SELECT hash_id, original_timestamp_ms FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, deleted_files_table_name ) ).fetchall()
            
        
        return rows
        
    
    def GroupHashIdsByTagCachedFileServiceId( self, hash_ids, hash_ids_table_name, hash_ids_to_current_file_service_ids = None ):
        
        # when we would love to do a fast cache lookup, it is useful to know if all the hash_ids are on one or two common file domains
        
        if hash_ids_to_current_file_service_ids is None:
            
            hash_ids_to_current_file_service_ids = self.GetHashIdsToCurrentServiceIds( hash_ids_table_name )
            
        
        cached_file_service_ids = set( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ) )
        
        file_service_ids_to_hash_ids = collections.defaultdict( set )
        
        for ( hash_id, file_service_ids ) in hash_ids_to_current_file_service_ids.items():
            
            for file_service_id in file_service_ids:
                
                if file_service_id in cached_file_service_ids:
                    
                    file_service_ids_to_hash_ids[ file_service_id ].add( hash_id )
                    
                
            
        
        # ok, we have our map, let's sort it out
        
        # sorting by most comprehensive service_id first
        file_service_ids_to_value = sorted( ( ( file_service_id, len( hash_ids ) ) for ( file_service_id, hash_ids ) in file_service_ids_to_hash_ids.items() ), key = lambda p: p[1], reverse = True )
        
        seen_hash_ids = set()
        
        # make our mapping non-overlapping
        for pair in file_service_ids_to_value:
            
            file_service_id = pair[0]
            
            this_services_hash_ids_set = file_service_ids_to_hash_ids[ file_service_id ]
            
            if len( seen_hash_ids ) > 0:
                
                this_services_hash_ids_set.difference_update( seen_hash_ids )
                
            
            if len( this_services_hash_ids_set ) == 0:
                
                del file_service_ids_to_hash_ids[ file_service_id ]
                
            else:
                
                seen_hash_ids.update( this_services_hash_ids_set )
                
            
        
        unmapped_hash_ids = set( hash_ids ).difference( seen_hash_ids )
        
        if len( unmapped_hash_ids ) > 0:
            
            file_service_ids_to_hash_ids[ self.modules_services.combined_file_service_id ] = unmapped_hash_ids
            
        
        return file_service_ids_to_hash_ids
        
    
    def PendFiles( self, service_id, hash_ids ):
        
        pending_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PENDING )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id ) VALUES ( ? );'.format( pending_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def PetitionFiles( self, service_id, reason_id, hash_ids ):
        
        petitioned_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PETITIONED )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( petitioned_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id, reason_id ) VALUES ( ?, ? );'.format( petitioned_files_table_name ), ( ( hash_id, reason_id ) for hash_id in hash_ids ) )
        
    
    def RecordDeleteFiles( self, service_id, insert_rows ):
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        now_ms = HydrusTime.GetNowMS()
        
        self._ExecuteMany(
            'INSERT OR IGNORE INTO {} ( hash_id, timestamp_ms, original_timestamp_ms ) VALUES ( ?, ?, ? );'.format( deleted_files_table_name ),
            ( ( hash_id, now_ms, original_timestamp_ms ) for ( hash_id, original_timestamp_ms ) in insert_rows )
        )
        
        num_new_deleted_files = self._GetRowCount()
        
        return num_new_deleted_files
        
    
    def RescindPendFiles( self, service_id, hash_ids ):
        
        pending_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PENDING )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( pending_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
        self.DeferFilesDeleteIfNowOrphan( hash_ids )
        
    
    def RescindPetitionFiles( self, service_id, hash_ids ):
        
        petitioned_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PETITIONED )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( petitioned_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def RemoveFiles( self, service_id, hash_ids ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( current_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( petitioned_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
        pending_changed = self._GetRowCount() > 0
        
        if self.modules_services.GetService( service_id ).GetServiceType() == HC.HYDRUS_LOCAL_FILE_STORAGE:
            
            self.DeferFilesDeleteIfNowOrphan( hash_ids )
            
        
        return pending_changed
        
    
    def SetFileDeletionReason( self, hash_ids, reason ):
        
        reason_id = self.modules_texts.GetTextId( reason )
        
        self._ExecuteMany( 'REPLACE INTO local_file_deletion_reasons ( hash_id, reason_id ) VALUES ( ?, ? );', ( ( hash_id, reason_id ) for hash_id in hash_ids ) )
        
    
    def SetTime( self, hash_ids: collections.abc.Collection[ int ], timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.location is None:
            
            return
            
        
        if timestamp_data.timestamp_ms is None:
            
            return
            
        
        service_key = timestamp_data.location
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        timestamp_ms = timestamp_data.timestamp_ms
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_IMPORTED:
            
            self._ExecuteMany( f'UPDATE {current_files_table_name} SET timestamp_ms = ? WHERE hash_id = ?;', ( ( timestamp_ms, hash_id ) for hash_id in hash_ids ) )
            
        elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_DELETED:
            
            self._ExecuteMany( f'UPDATE {deleted_files_table_name} SET timestamp_ms = ? WHERE hash_id = ?;', ( ( timestamp_ms, hash_id ) for hash_id in hash_ids ) )
            
        elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED:
            
            self._ExecuteMany( f'UPDATE {deleted_files_table_name} SET original_timestamp_ms = ? WHERE hash_id = ?;', ( ( timestamp_ms, hash_id ) for hash_id in hash_ids ) )
            
        
    
