import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB

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
        column_name = 'archived_timestamp'
        
    elif timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE:
        
        table_name = 'file_modified_timestamps'
        column_name = 'file_modified_timestamp'
        
    else:
        
        raise Exception( 'Not a simple timestamp type!' )
        
    
    return ( table_name, column_name )
    

class ClientDBFilesTimestamps( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_urls: ClientDBMaster.ClientDBMasterURLs, modules_files_viewing_stats: ClientDBFilesViewingStats.ClientDBFilesViewingStats, modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files timestamps', cursor )
        
        self.modules_urls = modules_urls
        self.modules_files_viewing_stats = modules_files_viewing_stats
        self.modules_files_storage = modules_files_storage
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.archive_timestamps' ] = [
            ( [ 'archived_timestamp' ], False, 474 )
        ]
        
        index_generation_dict[ 'main.file_domain_modified_timestamps' ] = [
            ( [ 'file_modified_timestamp' ], False, 476 )
        ]
        
        index_generation_dict[ 'main.file_modified_timestamps' ] = [
            ( [ 'file_modified_timestamp' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.archive_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, archived_timestamp INTEGER );', 474 ),
            'main.file_domain_modified_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, domain_id INTEGER, file_modified_timestamp INTEGER, PRIMARY KEY ( hash_id, domain_id ) );', 476 ),
            'main.file_modified_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, file_modified_timestamp INTEGER );', 400 )
        }
        
    
    def _ClearSimpleTimestamps( self, timestamp_type: int, hash_ids: typing.Collection[ int ] ):
        
        ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_type )
        
        self._ExecuteMany( f'DELETE FROM {table_name} WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def ClearArchivedTimestamps( self, hash_ids: typing.Collection[ int ] ):
        
        self._ClearSimpleTimestamps( HC.TIMESTAMP_TYPE_ARCHIVED, hash_ids )
        
    
    def ClearTimestamp( self, hash_id: int, timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data.location is None:
                
                return
                
            
            domain_id = self.modules_urls.GetURLDomainId( timestamp_data.location )
            
            self._Execute( 'DELETE FROM file_domain_modified_timestamps WHERE hash_id = ? AND domain_id = ?;', ( hash_id, domain_id ) )
            
        elif timestamp_data.timestamp_type in ClientTime.SIMPLE_TIMESTAMP_TYPES:
            
            self._ClearSimpleTimestamps( timestamp_data.timestamp_type, [ hash_id ] )
            
        
        # can't clear a file timestamp or file viewing timestamp from here, can't do it from UI either, so we good for now
        
    
    def GetHashIdsInRange( self, timestamp_type: int, ranges, job_key: typing.Optional[ ClientThreading.JobKey ] = None ):
        
        cancelled_hook = None
        
        if job_key is not None:
            
            cancelled_hook = job_key.IsCancelled
            
        
        if timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE:
            
            modified_timestamp_predicates = []
            
            if '>' in ranges:
                
                modified_timestamp_predicates.append( 'MIN( file_modified_timestamp ) >= {}'.format( ranges[ '>' ] ) )
                
            
            if '<' in ranges:
                
                modified_timestamp_predicates.append( 'MIN( file_modified_timestamp ) <= {}'.format( ranges[ '<' ] ) )
                
            
            if len( modified_timestamp_predicates ) > 0:
                
                pred_string = ' AND '.join( modified_timestamp_predicates )
                
                q1 = 'SELECT hash_id, file_modified_timestamp FROM file_modified_timestamps'
                q2 = 'SELECT hash_id, file_modified_timestamp FROM file_domain_modified_timestamps'
                
                query = 'SELECT hash_id FROM ( {} UNION {} ) GROUP BY hash_id HAVING {};'.format( q1, q2, pred_string )
                
                modified_timestamp_hash_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
                
                return modified_timestamp_hash_ids
                
            
        elif timestamp_type in ClientTime.REAL_SIMPLE_TIMESTAMP_TYPES:
            
            ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_type )
            
            predicates = []
            
            if '>' in ranges:
                
                value = ranges[ '>' ]
                
                predicates.append( f'{column_name} >= {value}' )
                
            
            if '<' in ranges:
                
                value = ranges[ '<' ]
                
                predicates.append( f'{column_name} <= {value}' )
                
            
            if len( predicates ) > 0:
                
                pred_string = ' AND '.join( predicates )
                
                query = f'SELECT hash_id FROM {table_name} WHERE {pred_string};'
                
                hash_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
                
                return hash_ids
                
            
        
        return set()
        
    
    def GetHashIdsToHalfInitialisedTimestampsManagers( self, hash_ids: typing.Collection[ int ], hash_ids_table_name: str ) -> typing.Dict[ int, ClientMediaManagers.TimestampsManager ]:
        
        # note that this doesn't fetch everything, just the stuff this module handles directly and can fetch efficiently
        
        hash_ids_to_archive_timestamps = self.GetSimpleTimestamps( HC.TIMESTAMP_TYPE_ARCHIVED, hash_ids_table_name )
        
        hash_ids_to_file_modified_timestamps = self.GetSimpleTimestamps( HC.TIMESTAMP_TYPE_MODIFIED_FILE, hash_ids_table_name )
        
        hash_ids_to_domain_modified_timestamps = HydrusData.BuildKeyToListDict( ( ( hash_id, ( domain, timestamp ) ) for ( hash_id, domain, timestamp ) in self._Execute( 'SELECT hash_id, domain, file_modified_timestamp FROM {} CROSS JOIN file_domain_modified_timestamps USING ( hash_id ) CROSS JOIN url_domains USING ( domain_id );'.format( hash_ids_table_name ) ) ) )
        
        hash_ids_to_timestamp_managers = {}
        
        for hash_id in hash_ids:
            
            timestamps_manager = ClientMediaManagers.TimestampsManager()
            
            if hash_id in hash_ids_to_file_modified_timestamps:
                
                timestamps_manager.SetFileModifiedTimestamp( hash_ids_to_file_modified_timestamps[ hash_id ] )
                
            
            if hash_id in hash_ids_to_domain_modified_timestamps:
                
                for ( domain, modified_timestamp ) in hash_ids_to_domain_modified_timestamps[ hash_id ]:
                    
                    timestamps_manager.SetDomainModifiedTimestamp( domain, modified_timestamp )
                    
                
            
            if hash_id in hash_ids_to_archive_timestamps:
                
                timestamps_manager.SetArchivedTimestamp( hash_ids_to_archive_timestamps[ hash_id ] )
                
            
            hash_ids_to_timestamp_managers[ hash_id ] = timestamps_manager
            
        
        return hash_ids_to_timestamp_managers
        
    
    def GetSimpleTimestamps( self, timestamp_type: int, hash_ids_table_name: str ) -> typing.Dict[ int, int ]:
        
        ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_type )
        
        query = f'SELECT hash_id, {column_name} FROM {hash_ids_table_name} CROSS JOIN {table_name} USING ( hash_id );'
        
        return dict( self._Execute( query ) )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            return [
                ( 'archive_timestamps', 'hash_id' ),
                ( 'file_domain_modified_timestamps', 'hash_id' ),
                ( 'file_modified_timestamps', 'hash_id' )
            ]
            
        
        return []
        
    
    def GetTimestamp( self, hash_id: int, timestamp_data: ClientTime.TimestampData ) -> typing.Optional[ int ]:
        
        result = None
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data.location is None:
                
                return None
                
            
            domain_id = self.modules_urls.GetURLDomainId( timestamp_data.location )
            
            result = self._Execute( 'SELECT file_modified_timestamp FROM file_domain_modified_timestamps WHERE hash_id = ? AND domain_id = ?;', ( hash_id, domain_id ) ).fetchone()
            
        elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            return self.modules_files_viewing_stats.GetTimestamp( hash_id, timestamp_data )
            
        elif timestamp_data.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            return self.modules_files_storage.GetTimestamp( hash_id, timestamp_data )
            
        elif timestamp_data.timestamp_type in ClientTime.REAL_SIMPLE_TIMESTAMP_TYPES:
            
            ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_data.timestamp_type )
            
            result = self._Execute( f'SELECT {column_name} FROM {table_name} WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
        
        if result is None:
            
            return None
            
        
        ( timestamp, ) = result
        
        return timestamp
        
    
    def SetSimpleTimestamps( self, timestamp_type: int, rows ):
        
        ( table_name, column_name ) = GetSimpleTimestampTableNames( timestamp_type )
        
        self._ExecuteMany( f'REPLACE INTO {table_name} ( hash_id, {column_name} ) VALUES ( ?, ? );', rows )
        
    
    def SetTimestamp( self, hash_id: int, timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp is None:
            
            return
            
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data.location is None:
                
                return
                
            
            domain_id = self.modules_urls.GetURLDomainId( timestamp_data.location )
            
            self._Execute( 'REPLACE INTO file_domain_modified_timestamps ( hash_id, domain_id, file_modified_timestamp ) VALUES ( ?, ?, ? );', ( hash_id, domain_id, timestamp_data.timestamp ) )
            
        elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            self.modules_files_viewing_stats.SetTimestamp( hash_id, timestamp_data)
            
        elif timestamp_data.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            self.modules_files_storage.SetTimestamp( hash_id, timestamp_data )
            
        elif timestamp_data.timestamp_type in ClientTime.REAL_SIMPLE_TIMESTAMP_TYPES:
            
            self.SetSimpleTimestamps( timestamp_data.timestamp_type, [ ( hash_id, timestamp_data.timestamp ) ] )
            
        
    
    def UpdateTimestamp( self, hash_id: int, timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp is None:
            
            return
            
        
        should_update = True
        
        existing_timestamp = self.GetTimestamp( hash_id, timestamp_data )
        
        if existing_timestamp is not None:
            
            should_update = ClientTime.ShouldUpdateModifiedTime( existing_timestamp, timestamp_data.timestamp )
            
        
        if should_update:
            
            self.SetTimestamp( hash_id, timestamp_data )
            
        
    
