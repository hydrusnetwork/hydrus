import collections
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBBase

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

def GenerateFilesTableNames( service_id: int ) -> typing.Tuple[ str, str, str, str ]:
    
    suffix = str( service_id )
    
    current_files_table_name = 'main.current_files_{}'.format( suffix )
    
    deleted_files_table_name = 'main.deleted_files_{}'.format( suffix )
    
    pending_files_table_name = 'main.pending_files_{}'.format( suffix )
    
    petitioned_files_table_name = 'main.petitioned_files_{}'.format( suffix )
    
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
    
    def __init__( self, location_context: ClientLocation.LocationContext ):
        
        self.location_context = location_context
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self.location_context
        
    
    def GetTableJoinIteratedByFileDomain( self, table_phrase: str ) -> str:
        
        raise NotImplementedError()
        
    
    def GetTableJoinLimitedByFileDomain( self, table_phrase: str ) -> str:
        
        raise NotImplementedError()
        
    
class DBLocationContextAllKnownFiles( DBLocationContext ):
    
    def GetTableJoinIteratedByFileDomain( self, table_phrase: str ) -> str:
        
        return table_phrase
        
    
    def GetTableJoinLimitedByFileDomain( self, table_phrase: str ) -> str:
        
        return table_phrase
        
    
class DBLocationContextBranch( DBLocationContext ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, files_table_name: str ):
        
        DBLocationContext.__init__( self, location_context )
        
        self.files_table_name = files_table_name
        
    
    def GetTableJoinIteratedByFileDomain( self, table_phrase: str ) -> str:
        
        return '{} CROSS JOIN {} USING ( hash_id )'.format( self.files_table_name, table_phrase )
        
    
    def GetTableJoinLimitedByFileDomain( self, table_phrase: str ) -> str:
        
        return '{} CROSS JOIN {} USING ( hash_id )'.format( table_phrase, self.files_table_name )
        
    
class ClientDBFilesStorage( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper, modules_services: ClientDBServices.ClientDBMasterServices, modules_hashes: ClientDBMaster.ClientDBMasterHashes, modules_texts: ClientDBMaster.ClientDBMasterTexts ):
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_services = modules_services
        self.modules_hashes = modules_hashes
        self.modules_texts = modules_texts
        
        ClientDBModule.ClientDBModule.__init__( self, 'client file locations', cursor )
        
        self.temp_file_storage_table_name = None
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.local_file_deletion_reasons' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, reason_id INTEGER );', 400 ),
            'deferred_physical_file_deletes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 464 ),
            'deferred_physical_thumbnail_deletes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 464 )
            
        }
        
    
    def _GetServiceIndexGenerationDict( self, service_id ) -> dict:
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        index_generation_dict = {}
        
        index_generation_dict[ current_files_table_name ] = [
            ( [ 'timestamp' ], False, 447 )
        ]
        
        index_generation_dict[ deleted_files_table_name ] = [
            ( [ 'timestamp' ], False, 447 ),
            ( [ 'original_timestamp' ], False, 447 )
        ]
        
        index_generation_dict[ petitioned_files_table_name ] = [
            ( [ 'reason_id' ], False, 447 )
        ]
        
        return index_generation_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        return {
            current_files_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, timestamp INTEGER );', 447 ),
            deleted_files_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, timestamp INTEGER, original_timestamp INTEGER );', 447 ),
            pending_files_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 447 ),
            petitioned_files_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, reason_id INTEGER );', 447 )
        }
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES )
        
    
    def AddFiles( self, service_id, insert_rows ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} VALUES ( ?, ? );'.format( current_files_table_name ), ( ( hash_id, timestamp ) for ( hash_id, timestamp ) in insert_rows ) )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( pending_files_table_name ), ( ( hash_id, ) for ( hash_id, timestamp ) in insert_rows ) )
        
        if service_id == self.modules_services.combined_local_file_service_id:
            
            for ( hash_id, timestamp ) in insert_rows:
                
                self.ClearDeferredPhysicalDeleteIds( file_hash_id = hash_id, thumbnail_hash_id = hash_id )
                
            
        elif self.modules_services.GetService( service_id ).GetServiceType() == HC.FILE_REPOSITORY:
            
            # it may be the case the files were just uploaded after being deleted
            self.DeferFilesDeleteIfNowOrphan( [ hash_id for ( hash_id, timestamp ) in insert_rows ] )
            
        
        pending_changed = self._GetRowCount() > 0
        
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
        
        # we delete from everywhere, but not for files currently in the trash
        
        service_ids_to_nums_cleared = {}
        
        local_non_trash_service_ids = self.modules_services.GetServiceIds( ( HC.COMBINED_LOCAL_FILE, HC.LOCAL_FILE_DOMAIN ) )
        
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
                
            
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( current_files_table_name ) )
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( deleted_files_table_name ) )
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( pending_files_table_name ) )
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( petitioned_files_table_name ) )
        
    
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
        
        if not location_context.SearchesAnything():
            
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
        
    
    def FilterHashIdsToStatus( self, service_id, hash_ids, status ) -> typing.Set[ int ]:
        
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
        
        useful_hash_ids = self.FilterHashIdsToStatus( self.modules_services.combined_local_file_service_id, hash_ids, HC.CONTENT_STATUS_CURRENT )
        
        orphan_hash_ids = set( hash_ids ).difference( useful_hash_ids )
        
        if len( orphan_hash_ids ) > 0:
            
            just_these_service_ids = self.modules_services.GetServiceIds( ( HC.FILE_REPOSITORY, ) )
            
            if ignore_service_id is not None:
                
                just_these_service_ids.discard( ignore_service_id )
                
            
            # anything pending upload somewhere, we want to keep
            useful_hash_ids = self.FilterAllPendingHashIds( orphan_hash_ids, just_these_service_ids = just_these_service_ids )
            
            orphan_hash_ids.difference_update( useful_hash_ids )
            
        
        return orphan_hash_ids
        
    
    def FilterOrphanThumbnailHashIds( self, hash_ids, ignore_service_id = None ):
        
        services = self.modules_services.GetServices( ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ) )
        
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
            
            self._Execute( create_query_without_name.format( table_name ) )
            
        
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
            result = self._Execute( 'SELECT COUNT( * ) FROM {} CROSS JOIN files_info USING ( hash_id ) WHERE mime IN {};'.format( current_files_table_name, HydrusData.SplayListForDB( HC.SEARCHABLE_MIMES ) ) ).fetchone()
            
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
        
        ( count, ) = result
        
        return count
        
    
    def GetCurrentHashIdsToTimestamps( self, service_id, hash_ids ):
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            rows = dict( self._Execute( 'SELECT hash_id, timestamp FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ) )
            
        
        return rows
        
    
    def GetCurrentTimestamp( self, service_id: int, hash_id: int ):
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        
        result = self._Execute( 'SELECT timestamp FROM {} WHERE hash_id = ?;'.format( current_files_table_name ), ( hash_id, ) ).fetchone()
        
        if result is None:
            
            return None
            
        else:
            
            ( timestamp, ) = result
            
            return timestamp
            
        
    
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
        timestamp = None
        
        result = self._Execute( 'SELECT timestamp FROM {} WHERE hash_id = ?;'.format( deleted_files_table_name ), ( hash_id, ) ).fetchone()
        
        if result is not None:
            
            is_deleted = True
            
            ( timestamp, ) = result
            
        
        return ( is_deleted, timestamp, file_deletion_reason )
        
    
    def GetDBLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        if not location_context.SearchesAnything():
            
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
            
            table_name = table_names[0]
            
            files_table_name = table_name
            
        else:
            
            # while I could make a VIEW of the UNION SELECT, we'll populate an indexed single column table to help query planner later on
            # we're hardcoding the name to this class for now, so a limit of one db_location_context at a time _for now_
            # we make change this in future to use wrapper temp int tables, we'll see
            
            # maybe I should stick this guy in 'temp' to live through db connection resets, but we'll see I guess. it is generally ephemeral, not going to linger through weird vacuum maintenance or anything right?
            
            if self.temp_file_storage_table_name is None:
                
                self.temp_file_storage_table_name = 'mem.temp_file_storage_hash_id'
                
                self._Execute( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );'.format( self.temp_file_storage_table_name ) )
                
            else:
                
                self._Execute( 'DELETE FROM {};'.format( self.temp_file_storage_table_name ) )
                
            
            select_query = ' UNION '.join( ( 'SELECT hash_id FROM {}'.format( table_name ) for table_name in table_names ) )
            
            self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id ) {};'.format( self.temp_file_storage_table_name, select_query ) )
            
            files_table_name = self.temp_file_storage_table_name
            
        
        return DBLocationContextBranch( location_context, files_table_name )
        
    
    def GetHashIdsToCurrentServiceIds( self, temp_hash_ids_table_name ):
        
        hash_ids_to_current_file_service_ids = collections.defaultdict( list )
        
        for service_id in self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ):
            
            current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
            
            for hash_id in self._STI( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ) ):
                
                hash_ids_to_current_file_service_ids[ hash_id ].append( service_id )
                
            
        
        return hash_ids_to_current_file_service_ids
        
    
    def GetHashIdsToServiceInfoDicts( self, temp_hash_ids_table_name ):
        
        hash_ids_to_current_file_service_ids_and_timestamps = collections.defaultdict( list )
        hash_ids_to_deleted_file_service_ids_and_timestamps = collections.defaultdict( list )
        hash_ids_to_pending_file_service_ids = collections.defaultdict( list )
        hash_ids_to_petitioned_file_service_ids = collections.defaultdict( list )
        
        for service_id in self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ):
            
            ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
            
            for ( hash_id, timestamp ) in self._Execute( 'SELECT hash_id, timestamp FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, current_files_table_name ) ):
                
                hash_ids_to_current_file_service_ids_and_timestamps[ hash_id ].append( ( service_id, timestamp ) )
                
            
            for ( hash_id, timestamp, original_timestamp ) in self._Execute( 'SELECT hash_id, timestamp, original_timestamp FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, deleted_files_table_name ) ):
                
                hash_ids_to_deleted_file_service_ids_and_timestamps[ hash_id ].append( ( service_id, timestamp, original_timestamp ) )
                
            
            for hash_id in self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, pending_files_table_name ) ):
                
                hash_ids_to_pending_file_service_ids[ hash_id ].append( service_id )
                
            
            for hash_id in self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, petitioned_files_table_name ) ):
                
                hash_ids_to_petitioned_file_service_ids[ hash_id ].append( service_id )
                
            
        
        return (
            hash_ids_to_current_file_service_ids_and_timestamps,
            hash_ids_to_deleted_file_service_ids_and_timestamps,
            hash_ids_to_pending_file_service_ids,
            hash_ids_to_petitioned_file_service_ids
        )
        
    
    def GetLocationContextForAllServicesDeletedFiles( self ) -> ClientLocation.LocationContext:
        
        deleted_service_keys = { service.GetServiceKey() for service in self.modules_services.GetServices( limited_types = HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE ) }
        
        location_context = ClientLocation.LocationContext( [], deleted_service_keys )
        
        return location_context
        
    
    def GetNumLocal( self, service_id: int ) -> int:
        
        current_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_CURRENT )
        combined_local_current_files_table_name = GenerateFilesTableName( self.modules_services.combined_local_file_service_id, HC.CONTENT_STATUS_CURRENT )
        
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
        
    
    def GetServiceIdCounts( self, hash_ids ) -> typing.Dict[ int, int ]:
        
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
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = [
            ( 'deferred_physical_file_deletes', 'hash_id' ),
            ( 'deferred_physical_thumbnail_deletes', 'hash_id' )
        ]
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            for service_id in self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ):
                
                ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name ) = GenerateFilesTableNames( service_id )
                
                tables_and_columns.extend( [
                    ( current_files_table_name, 'hash_id' ),
                    ( deleted_files_table_name, 'hash_id' ),
                    ( pending_files_table_name, 'hash_id' ),
                    ( petitioned_files_table_name, 'hash_id' )
                ] )
                
            
        
        return tables_and_columns
        
    
    def GetUndeleteRows( self, service_id, hash_ids ):
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            rows = self._Execute( 'SELECT hash_id, original_timestamp FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, deleted_files_table_name ) ).fetchall()
            
        
        return rows
        
    
    def PendFiles( self, service_id, hash_ids ):
        
        pending_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PENDING )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id ) VALUES ( ? );'.format( pending_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def PetitionFiles( self, service_id, reason_id, hash_ids ):
        
        petitioned_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_PETITIONED )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( petitioned_files_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id, reason_id ) VALUES ( ?, ? );'.format( petitioned_files_table_name ), ( ( hash_id, reason_id ) for hash_id in hash_ids ) )
        
    
    def RecordDeleteFiles( self, service_id, insert_rows ):
        
        deleted_files_table_name = GenerateFilesTableName( service_id, HC.CONTENT_STATUS_DELETED )
        
        now = HydrusData.GetNow()
        
        self._ExecuteMany(
            'INSERT OR IGNORE INTO {} ( hash_id, timestamp, original_timestamp ) VALUES ( ?, ?, ? );'.format( deleted_files_table_name ),
            ( ( hash_id, now, original_timestamp ) for ( hash_id, original_timestamp ) in insert_rows )
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
        
        if self.modules_services.GetService( service_id ).GetServiceType() in ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
            
            self.DeferFilesDeleteIfNowOrphan( hash_ids )
            
        
        pending_changed = self._GetRowCount() > 0
        
        return pending_changed
        
    
    def SetFileDeletionReason( self, hash_ids, reason ):
        
        reason_id = self.modules_texts.GetTextId( reason )
        
        self._ExecuteMany( 'REPLACE INTO local_file_deletion_reasons ( hash_id, reason_id ) VALUES ( ?, ? );', ( ( hash_id, reason_id ) for hash_id in hash_ids ) )
        
