import collections.abc
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientTime
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBFilesViewingStats
from hydrus.client.media import ClientMediaManagers

def GetSimpleTimestampTableNames( timestamp_type: int ):
    
    if timestamp_type == HC.TIMESTAMP_TYPE_ARCHIVED:
        
        table_name = 'archive_timestamps'
        column_name = 'archived_timestamp_ms'
        
    elif timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE:
        
        table_name = 'file_modified_timestamps'
        column_name = 'file_modified_timestamp_ms'
        
    else:
        
        raise Exception( 'Not a simple timestamp type!' )
        
    
    return ( table_name, column_name )
    

class ClientDBFilesTimestamps( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_urls: ClientDBMaster.ClientDBMasterURLs, modules_files_viewing_stats: ClientDBFilesViewingStats.ClientDBFilesViewingStats, modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage ):
        
        super().__init__( 'client files timestamps', cursor )
        
        self.modules_urls = modules_urls
        self.modules_files_viewing_stats = modules_files_viewing_stats
        self.modules_files_storage = modules_files_storage
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.archive_timestamps' ] = [
            ( [ 'archived_timestamp_ms' ], False, 559 )
        ]
        
        index_generation_dict[ 'main.file_domain_modified_timestamps' ] = [
            ( [ 'file_modified_timestamp_ms' ], False, 559 )
        ]
        
        index_generation_dict[ 'main.file_modified_timestamps' ] = [
            ( [ 'file_modified_timestamp_ms' ], False, 559 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.archive_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, archived_timestamp_ms INTEGER );', 474 ),
            'main.file_domain_modified_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, domain_id INTEGER, file_modified_timestamp_ms INTEGER, PRIMARY KEY ( hash_id, domain_id ) );', 476 ),
            'main.file_modified_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, file_modified_timestamp_ms INTEGER );', 400 )
        }
        
    
    def _ClearSimpleTimes( self, timestamp_type: int, hash_ids: collections.abc.Collection[ int ] ):
        
        ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_type )
        
        self._ExecuteMany( f'DELETE FROM {table_name} WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def ClearArchivedTimes( self, hash_ids: collections.abc.Collection[ int ] ):
        
        self._ClearSimpleTimes( HC.TIMESTAMP_TYPE_ARCHIVED, hash_ids )
        
    
    def ClearTime( self, hash_ids: collections.abc.Collection[ int ], timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data.location is None:
                
                return
                
            
            domain_id = self.modules_urls.GetURLDomainId( timestamp_data.location )
            
            self._ExecuteMany( 'DELETE FROM file_domain_modified_timestamps WHERE hash_id = ? AND domain_id = ?;', ( ( hash_id, domain_id ) for hash_id in hash_ids ) )
            
        elif timestamp_data.timestamp_type in ClientTime.SIMPLE_TIMESTAMP_TYPES:
            
            self._ClearSimpleTimes( timestamp_data.timestamp_type, hash_ids )
            
        
        # can't clear a file timestamp or file viewing timestamp from here, can't do it from UI either, so we good for now
        
    
    def GetHashIdsInRange( self, timestamp_type: int, timestamp_ranges_ms, job_status: ClientThreading.JobStatus | None = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        if timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE:
            
            modified_timestamp_predicates = []
            
            if '>' in timestamp_ranges_ms:
                
                modified_timestamp_predicates.append( 'MIN( file_modified_timestamp_ms ) >= {}'.format( timestamp_ranges_ms[ '>' ] ) )
                
            
            if '<' in timestamp_ranges_ms:
                
                modified_timestamp_predicates.append( 'MIN( file_modified_timestamp_ms ) <= {}'.format( timestamp_ranges_ms[ '<' ] ) )
                
            
            if len( modified_timestamp_predicates ) > 0:
                
                pred_string = ' AND '.join( modified_timestamp_predicates )
                
                q1 = 'SELECT hash_id, file_modified_timestamp_ms FROM file_modified_timestamps'
                q2 = 'SELECT hash_id, file_modified_timestamp_ms FROM file_domain_modified_timestamps'
                
                query = 'SELECT hash_id FROM ( {} UNION {} ) GROUP BY hash_id HAVING {};'.format( q1, q2, pred_string )
                
                modified_timestamp_hash_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
                
                return modified_timestamp_hash_ids
                
            
        elif timestamp_type in ClientTime.REAL_SIMPLE_TIMESTAMP_TYPES:
            
            ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_type )
            
            predicates = []
            
            if '>' in timestamp_ranges_ms:
                
                value = timestamp_ranges_ms[ '>' ]
                
                predicates.append( f'{column_name} >= {value}' )
                
            
            if '<' in timestamp_ranges_ms:
                
                value = timestamp_ranges_ms[ '<' ]
                
                predicates.append( f'{column_name} <= {value}' )
                
            
            if len( predicates ) > 0:
                
                pred_string = ' AND '.join( predicates )
                
                query = f'SELECT hash_id FROM {table_name} WHERE {pred_string};'
                
                hash_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
                
                return hash_ids
                
            
        
        return set()
        
    
    def GetHashIdsToArchivedTimestampsMS( self, hash_ids: collections.abc.Collection[ int ] ):
        
        # TODO: generalise this to any timestamp_data stub, but it is a slight pain!
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_table_name:
            
            ( table_name, column_name ) = GetSimpleTimestampTableNames( HC.TIMESTAMP_TYPE_ARCHIVED )
            
            result = dict( self._Execute( f'SELECT hash_id, {column_name} FROM {temp_table_name} CROSS JOIN {table_name} USING ( hash_id );' ) )
            
        
        for hash_id in hash_ids:
            
            if hash_id not in result:
                
                result[ hash_id ] = None
                
            
        
        return result
        
    
    def GetHashIdsToHalfInitialisedTimesManagers( self, hash_ids: collections.abc.Collection[ int ], hash_ids_table_name: str ) -> dict[ int, ClientMediaManagers.TimesManager ]:
        
        # note that this doesn't fetch everything, just the stuff this module handles directly and can fetch efficiently
        
        hash_ids_to_archive_timestamps_ms = self.GetSimpleTimestampsMS( HC.TIMESTAMP_TYPE_ARCHIVED, hash_ids_table_name )
        
        hash_ids_to_file_modified_timestamps_ms = self.GetSimpleTimestampsMS( HC.TIMESTAMP_TYPE_MODIFIED_FILE, hash_ids_table_name )
        
        hash_ids_to_domain_modified_timestamps_ms = HydrusData.BuildKeyToListDict( ( ( hash_id, ( domain, timestamp_ms ) ) for ( hash_id, domain, timestamp_ms ) in self._Execute( 'SELECT hash_id, domain, file_modified_timestamp_ms FROM {} CROSS JOIN file_domain_modified_timestamps USING ( hash_id ) CROSS JOIN url_domains USING ( domain_id );'.format( hash_ids_table_name ) ) ) )
        
        hash_ids_to_timestamp_managers = {}
        
        for hash_id in hash_ids:
            
            times_manager = ClientMediaManagers.TimesManager()
            
            if hash_id in hash_ids_to_file_modified_timestamps_ms:
                
                times_manager.SetFileModifiedTimestampMS( hash_ids_to_file_modified_timestamps_ms[ hash_id ] )
                
            
            if hash_id in hash_ids_to_domain_modified_timestamps_ms:
                
                for ( domain, modified_timestamp_ms ) in hash_ids_to_domain_modified_timestamps_ms[ hash_id ]:
                    
                    times_manager.SetDomainModifiedTimestampMS( domain, modified_timestamp_ms )
                    
                
            
            if hash_id in hash_ids_to_archive_timestamps_ms:
                
                times_manager.SetArchivedTimestampMS( hash_ids_to_archive_timestamps_ms[ hash_id ] )
                
            
            hash_ids_to_timestamp_managers[ hash_id ] = times_manager
            
        
        return hash_ids_to_timestamp_managers
        
    
    def GetSimpleTimestampsMS( self, timestamp_type: int, hash_ids_table_name: str ) -> dict[ int, int ]:
        
        ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_type )
        
        query = f'SELECT hash_id, {column_name} FROM {hash_ids_table_name} CROSS JOIN {table_name} USING ( hash_id );'
        
        return dict( self._Execute( query ) )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            return [
                ( 'archive_timestamps', 'hash_id' ),
                ( 'file_domain_modified_timestamps', 'hash_id' ),
                ( 'file_modified_timestamps', 'hash_id' )
            ]
            
        
        return []
        
    
    def GetTimestampMS( self, hash_id: int, timestamp_data: ClientTime.TimestampData ) -> int | None:
        
        result = None
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data.location is None:
                
                return None
                
            
            domain_id = self.modules_urls.GetURLDomainId( timestamp_data.location )
            
            result = self._Execute( 'SELECT file_modified_timestamp_ms FROM file_domain_modified_timestamps WHERE hash_id = ? AND domain_id = ?;', ( hash_id, domain_id ) ).fetchone()
            
        elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            return self.modules_files_viewing_stats.GetTimestampMS( hash_id, timestamp_data )
            
        elif timestamp_data.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            return self.modules_files_storage.GetTimestampMS( hash_id, timestamp_data )
            
        elif timestamp_data.timestamp_type in ClientTime.REAL_SIMPLE_TIMESTAMP_TYPES:
            
            ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_data.timestamp_type )
            
            result = self._Execute( f'SELECT {column_name} FROM {table_name} WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
        
        if result is None:
            
            return None
            
        
        ( timestamp, ) = result
        
        return timestamp
        
    
    def SetSimpleTimestampsMS( self, timestamp_type: int, rows ):
        
        ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_type )
        
        self._ExecuteMany( f'REPLACE INTO {table_name} ( hash_id, {column_name} ) VALUES ( ?, ? );', rows )
        
    
    def SetTime( self, hash_ids: collections.abc.Collection[ int ], timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp_ms is None:
            
            return
            
        
        # TODO: wangle all these calls from hash_id to hash_ids
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data.location is None:
                
                return
                
            
            domain_id = self.modules_urls.GetURLDomainId( timestamp_data.location )
            
            self._ExecuteMany( 'REPLACE INTO file_domain_modified_timestamps ( hash_id, domain_id, file_modified_timestamp_ms ) VALUES ( ?, ?, ? );', ( ( hash_id, domain_id, timestamp_data.timestamp_ms ) for hash_id in hash_ids ) )
            
        elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            self.modules_files_viewing_stats.SetTime( hash_ids, timestamp_data )
            
        elif timestamp_data.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            self.modules_files_storage.SetTime( hash_ids, timestamp_data )
            
        elif timestamp_data.timestamp_type in ClientTime.REAL_SIMPLE_TIMESTAMP_TYPES:
            
            self.SetSimpleTimestampsMS( timestamp_data.timestamp_type, [ ( hash_id, timestamp_data.timestamp_ms ) for hash_id in hash_ids ] )
            
        
    
    def UpdateTime( self, hash_ids: collections.abc.Collection[ int ], timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp_ms is None:
            
            return
            
        
        updatable_hash_ids = []
        
        for hash_id in hash_ids:
            
            should_update = True
            
            existing_timestamp_ms = self.GetTimestampMS( hash_id, timestamp_data )
            
            if existing_timestamp_ms is not None:
                
                should_update = ClientTime.ShouldUpdateModifiedTime( existing_timestamp_ms, timestamp_data.timestamp_ms )
                
            
            if should_update:
                
                updatable_hash_ids.append( hash_id )
                
            
        
        if len( updatable_hash_ids ) > 0:
            
            self.SetTime( updatable_hash_ids, timestamp_data )
            
        
    
