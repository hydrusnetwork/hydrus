import itertools
import os
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusExceptions
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientFiles
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesMaintenance
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBServices

def GenerateRepositoryDefinitionTableNames( service_id: int ):
    
    suffix = str( service_id )
    
    hash_id_map_table_name = 'external_master.repository_hash_id_map_{}'.format( suffix )
    tag_id_map_table_name = 'external_master.repository_tag_id_map_{}'.format( suffix )
    
    return ( hash_id_map_table_name, tag_id_map_table_name )
    
def GenerateRepositoryFileDefinitionTableName( service_id: int ):
    
    ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
    
    return hash_id_map_table_name
    
def GenerateRepositoryTagDefinitionTableName( service_id: int ):
    
    ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
    
    return tag_id_map_table_name
    
def GenerateRepositoryUpdatesTableName( service_id: int ):
    
    repository_updates_table_name = 'repository_updates_{}'.format( service_id )
    
    return repository_updates_table_name
    
class ClientDBRepositories( HydrusDBModule.HydrusDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        cursor_transaction_wrapper: HydrusDB.DBCursorTransactionWrapper,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_tags_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalTags,
        modules_files_maintenance: ClientDBFilesMaintenance.ClientDBFilesMaintenance
        ):
        
        # since we'll mostly be talking about hashes and tags we don't have locally, I think we shouldn't use the local caches
        
        HydrusDBModule.HydrusDBModule.__init__( self, 'client repositories', cursor )
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_services = modules_services
        self.modules_files_storage = modules_files_storage
        self.modules_files_maintenance = modules_files_maintenance
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_tags_local_cache = modules_tags_local_cache
        
    
    def _GetInitialIndexGenerationTuples( self ):
        
        index_generation_tuples = []
        
        return index_generation_tuples
        
    
    def _HandleCriticalRepositoryDefinitionError( self, service_id, name, bad_ids ):
        
        self._ReprocessRepository( service_id, ( HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS, ) )
        
        self._ScheduleRepositoryUpdateFileMaintenance( service_id, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA )
        self._ScheduleRepositoryUpdateFileMaintenance( service_id, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
        
        self._cursor_transaction_wrapper.CommitAndBegin()
        
        message = 'A critical error was discovered with one of your repositories: its definition reference is in an invalid state. Your repository should now be paused, and all update files have been scheduled for an integrity and metadata check. Please permit file maintenance to check them, or tell it to do so manually, before unpausing your repository. Once unpaused, it will reprocess your definition files and attempt to fill the missing entries. If this error occurs again once that is complete, please inform hydrus dev.'
        message += os.linesep * 2
        message += 'Error: {}: {}'.format( name, bad_ids )
        
        raise Exception( message )
        
    
    def _ReprocessRepository( self, service_id, update_mime_types ):
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        update_hash_ids = set()
        
        for update_mime_type in update_mime_types:
            
            hash_ids = self._STL( self._c.execute( 'SELECT hash_id FROM {} NATURAL JOIN files_info WHERE mime = ? AND processed = ?;'.format( repository_updates_table_name ), ( update_mime_type, True ) ) )
            
            update_hash_ids.update( hash_ids )
            
        
        self._c.executemany( 'UPDATE {} SET processed = ? WHERE hash_id = ?;'.format( repository_updates_table_name ), ( ( False, hash_id ) for hash_id in update_hash_ids ) )
        
    
    def _ScheduleRepositoryUpdateFileMaintenance( self, service_id, job_type ):
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        update_hash_ids = self._STL( self._c.execute( 'SELECT hash_id FROM {};'.format( repository_updates_table_name ) ) )
        
        self.modules_files_maintenance.AddJobs( update_hash_ids, job_type )
        
    
    def AssociateRepositoryUpdateHashes( self, service_key: bytes, metadata_slice: HydrusNetwork.Metadata ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        processed = False
        
        inserts = []
        
        for ( update_index, update_hashes ) in metadata_slice.GetUpdateIndicesAndHashes():
            
            for update_hash in update_hashes:
                
                hash_id = self.modules_hashes_local_cache.GetHashId( update_hash )
                
                inserts.append( ( update_index, hash_id, processed ) )
                
            
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        self._c.executemany( 'INSERT OR IGNORE INTO {} ( update_index, hash_id, processed ) VALUES ( ?, ?, ? );'.format( repository_updates_table_name ), inserts )
        
    
    def CreateInitialTables( self ):
        
        pass
        
    
    def DropRepositoryTables( self, service_id: int ):
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        self._c.execute( 'DROP TABLE IF EXISTS {};'.format( repository_updates_table_name ) )
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
        
        self._c.execute( 'DROP TABLE IF EXISTS {};'.format( hash_id_map_table_name ) )
        self._c.execute( 'DROP TABLE IF EXISTS {};'.format( tag_id_map_table_name ) )
        
    
    def GenerateRepositoryTables( self, service_id: int ):
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS {} ( update_index INTEGER, hash_id INTEGER, processed INTEGER_BOOLEAN, PRIMARY KEY ( update_index, hash_id ) );'.format( repository_updates_table_name ) )
        self._CreateIndex( repository_updates_table_name, [ 'hash_id' ] )
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS {} ( service_hash_id INTEGER PRIMARY KEY, hash_id INTEGER );'.format( hash_id_map_table_name ) )
        self._c.execute( 'CREATE TABLE IF NOT EXISTS {} ( service_tag_id INTEGER PRIMARY KEY, tag_id INTEGER );'.format( tag_id_map_table_name ) )
        
    
    def GetExpectedTableNames( self ) -> typing.Collection[ str ]:
        
        expected_table_names = [
        ]
        
        return expected_table_names
        
    
    def GetRepositoryProgress( self, service_key: bytes ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        ( num_updates, ) = self._c.execute( 'SELECT COUNT( * ) FROM {};'.format( repository_updates_table_name ) ).fetchone()
        
        ( num_processed_updates, ) = self._c.execute( 'SELECT COUNT( * ) FROM {} WHERE processed = ?;'.format( repository_updates_table_name ), ( True, ) ).fetchone()
        
        table_join = self.modules_files_storage.GetCurrentTableJoinPhrase( self.modules_services.local_update_service_id, repository_updates_table_name )
        
        ( num_local_updates, ) = self._c.execute( 'SELECT COUNT( * ) FROM {};'.format( table_join ) ).fetchone()
        
        return ( num_local_updates, num_processed_updates, num_updates )
        
    
    def GetRepositoryUpdateHashesICanProcess( self, service_key: bytes ):
        
        # it is important that we use lists and sort by update index!
        # otherwise add/delete actions can occur in the wrong order
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        result = self._c.execute( 'SELECT 1 FROM {} CROSS JOIN files_info USING ( hash_id ) WHERE mime = ? AND processed = ?;'.format( repository_updates_table_name ), ( HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS, True ) ).fetchone()
        
        this_is_first_definitions_work = result is None
        
        result = self._c.execute( 'SELECT 1 FROM {} CROSS JOIN files_info USING ( hash_id ) WHERE mime = ? AND processed = ?;'.format( repository_updates_table_name ), ( HC.APPLICATION_HYDRUS_UPDATE_CONTENT, True ) ).fetchone()
        
        this_is_first_content_work = result is None
        
        update_indices_to_unprocessed_hash_ids = HydrusData.BuildKeyToSetDict( self._c.execute( 'SELECT update_index, hash_id FROM {} WHERE processed = ?;'.format( repository_updates_table_name ), ( False, ) ) )
        
        unprocessed_hash_ids = list( itertools.chain.from_iterable( update_indices_to_unprocessed_hash_ids.values() ) )
        
        definition_hashes = []
        content_hashes = []
        
        if len( unprocessed_hash_ids ) > 0:
            
            local_hash_ids = self.modules_files_storage.FilterCurrentHashIds( self.modules_services.local_update_service_id, unprocessed_hash_ids )
            
            hash_ids_i_can_process = []
            
            update_indices = sorted( update_indices_to_unprocessed_hash_ids.keys() )
            
            for update_index in update_indices:
                
                this_update_unprocessed_hash_ids = update_indices_to_unprocessed_hash_ids[ update_index ]
                
                if local_hash_ids.issuperset( this_update_unprocessed_hash_ids ):
                    
                    # if we have all the updates, we can process this index
                    
                    hash_ids_i_can_process.extend( this_update_unprocessed_hash_ids )
                    
                else:
                    
                    # if we don't have them all, we shouldn't do any more
                    
                    break
                    
                
            
            if len( hash_ids_i_can_process ) > 0:
                
                with HydrusDB.TemporaryIntegerTable( self._c, hash_ids_i_can_process, 'hash_id' ) as temp_hash_ids_table_name:
                    
                    hash_ids_to_hashes_and_mimes = { hash_id : ( hash, mime ) for ( hash_id, hash, mime ) in self._c.execute( 'SELECT hash_id, hash, mime FROM {} CROSS JOIN hashes USING ( hash_id ) CROSS JOIN files_info USING ( hash_id );'.format( temp_hash_ids_table_name ) ) }
                    
                
                if len( hash_ids_to_hashes_and_mimes ) < len( hash_ids_i_can_process ):
                    
                    self._ScheduleRepositoryUpdateFileMaintenance( service_id, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA )
                    self._ScheduleRepositoryUpdateFileMaintenance( service_id, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                    
                    self._cursor_transaction_wrapper.CommitAndBegin()
                    
                    raise Exception( 'An error was discovered during repository processing--some update files are missing file info or hashes. A maintenance routine will try to scan these files and fix this problem, but it may be more complicated to fix. Please contact hydev and let him know the details!' )
                    
                
                for hash_id in hash_ids_i_can_process:
                    
                    ( hash, mime ) = hash_ids_to_hashes_and_mimes[ hash_id ]
                    
                    if mime == HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS:
                        
                        definition_hashes.append( hash )
                        
                    elif mime == HC.APPLICATION_HYDRUS_UPDATE_CONTENT:
                        
                        content_hashes.append( hash )
                        
                    
                
            
        
        return ( this_is_first_definitions_work, definition_hashes, this_is_first_content_work, content_hashes )
        
    
    def GetRepositoryUpdateHashesIDoNotHave( self, service_key: bytes ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        desired_hash_ids = self._STL( self._c.execute( 'SELECT hash_id FROM {} ORDER BY update_index ASC;'.format( repository_updates_table_name ) ) )
        
        table_join = self.modules_files_storage.GetCurrentTableJoinPhrase( self.modules_services.local_update_service_id, repository_updates_table_name )
        
        existing_hash_ids = self._STS( self._c.execute( 'SELECT hash_id FROM {};'.format( table_join ) ) )
        
        needed_hash_ids = [ hash_id for hash_id in desired_hash_ids if hash_id not in existing_hash_ids ]
        
        needed_hashes = self.modules_hashes_local_cache.GetHashes( needed_hash_ids )
        
        return needed_hashes
        
    
    def GetRepositoryUpdateHashesUnprocessed( self, service_key: bytes ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        unprocessed_hash_ids = self._STL( self._c.execute( 'SELECT hash_id FROM {} WHERE processed = ?;'.format( repository_updates_table_name ), ( False, ) ) )
        
        hashes = self.modules_hashes_local_cache.GetHashes( unprocessed_hash_ids )
        
        return hashes
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if HC.CONTENT_TYPE_HASH:
            
            for service_id in self.modules_services.GetServiceIds( HC.REPOSITORIES ):
                
                repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
                hash_id_map_table_name = GenerateRepositoryFileDefinitionTableName( service_id )
                
                tables_and_columns.extend( [
                    ( repository_updates_table_name, 'hash_id' ),
                    ( hash_id_map_table_name, 'hash_id' )
                ] )
                
            
        elif HC.CONTENT_TYPE_TAG:
            
            for service_id in self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES ):
                
                tag_id_map_table_name = GenerateRepositoryTagDefinitionTableName( service_id )
                
                tables_and_columns.extend( [
                    ( tag_id_map_table_name, 'tag_id' )
                ] )
                
            
        
        return tables_and_columns
        
    
    def NormaliseServiceHashId( self, service_id: int, service_hash_id: int ) -> int:
        
        hash_id_map_table_name = GenerateRepositoryFileDefinitionTableName( service_id )
        
        result = self._c.execute( 'SELECT hash_id FROM {} WHERE service_hash_id = ?;'.format( hash_id_map_table_name ), ( service_hash_id, ) ).fetchone()
        
        if result is None:
            
            self._HandleCriticalRepositoryDefinitionError( service_id, 'hash_id', service_hash_id )
            
        
        ( hash_id, ) = result
        
        return hash_id
        
    
    def NormaliseServiceHashIds( self, service_id: int, service_hash_ids: typing.Collection[ int ] ) -> typing.Set[ int ]:
        
        hash_id_map_table_name = GenerateRepositoryFileDefinitionTableName( service_id )
        
        with HydrusDB.TemporaryIntegerTable( self._c, service_hash_ids, 'service_hash_id' ) as temp_table_name:
            
            # temp service hashes to lookup
            hash_ids_potentially_dupes = self._STL( self._c.execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( service_hash_id );'.format( temp_table_name, hash_id_map_table_name ) ) )
            
        
        # every service_id can only exist once, but technically a hash_id could be mapped to two service_ids
        if len( hash_ids_potentially_dupes ) != len( service_hash_ids ):
            
            bad_service_hash_ids = []
            
            for service_hash_id in service_hash_ids:
                
                result = self._c.execute( 'SELECT hash_id FROM {} WHERE service_hash_id = ?;'.format( hash_id_map_table_name ), ( service_hash_id, ) ).fetchone()
                
                if result is None:
                    
                    bad_service_hash_ids.append( service_hash_id )
                    
                
            
            self._HandleCriticalRepositoryDefinitionError( service_id, 'hash_ids', bad_service_hash_ids )
            
        
        hash_ids = set( hash_ids_potentially_dupes )
        
        return hash_ids
        
    
    def NormaliseServiceTagId( self, service_id: int, service_tag_id: int ) -> int:
        
        tag_id_map_table_name = GenerateRepositoryTagDefinitionTableName( service_id )
        
        result = self._c.execute( 'SELECT tag_id FROM {} WHERE service_tag_id = ?;'.format( tag_id_map_table_name ), ( service_tag_id, ) ).fetchone()
        
        if result is None:
            
            self._HandleCriticalRepositoryDefinitionError( service_id, 'tag_id', service_tag_id )
            
        
        ( tag_id, ) = result
        
        return tag_id
        
    
    def ProcessRepositoryDefinitions( self, service_key: bytes, definition_hash: bytes, definition_iterator_dict, job_key, work_time ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        precise_time_to_stop = HydrusData.GetNowPrecise() + work_time
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
        
        num_rows_processed = 0
        
        if 'service_hash_ids_to_hashes' in definition_iterator_dict:
            
            i = definition_iterator_dict[ 'service_hash_ids_to_hashes' ]
            
            for chunk in HydrusData.SplitIteratorIntoAutothrottledChunks( i, 50, precise_time_to_stop ):
                
                inserts = []
                
                for ( service_hash_id, hash ) in chunk:
                    
                    hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                    
                    inserts.append( ( service_hash_id, hash_id ) )
                    
                
                self._c.executemany( 'REPLACE INTO {} ( service_hash_id, hash_id ) VALUES ( ?, ? );'.format( hash_id_map_table_name ), inserts )
                
                num_rows_processed += len( inserts )
                
                if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                    
                    return num_rows_processed
                    
                
            
            del definition_iterator_dict[ 'service_hash_ids_to_hashes' ]
            
        
        if 'service_tag_ids_to_tags' in definition_iterator_dict:
            
            i = definition_iterator_dict[ 'service_tag_ids_to_tags' ]
            
            for chunk in HydrusData.SplitIteratorIntoAutothrottledChunks( i, 50, precise_time_to_stop ):
                
                inserts = []
                
                for ( service_tag_id, tag ) in chunk:
                    
                    try:
                        
                        tag_id = self.modules_tags_local_cache.GetTagId( tag )
                        
                    except HydrusExceptions.TagSizeException:
                        
                        # in future what we'll do here is assign this id to the 'do not show' table, so we know it exists, but it is knowingly filtered out
                        # _or something_. maybe a small 'invalid' table, so it isn't mixed up with potentially re-addable tags
                        tag_id = self.modules_tags_local_cache.GetTagId( 'invalid repository tag' )
                        
                    
                    inserts.append( ( service_tag_id, tag_id ) )
                    
                
                self._c.executemany( 'REPLACE INTO {} ( service_tag_id, tag_id ) VALUES ( ?, ? );'.format( tag_id_map_table_name ), inserts )
                
                num_rows_processed += len( inserts )
                
                if HydrusData.TimeHasPassedPrecise( precise_time_to_stop ) or job_key.IsCancelled():
                    
                    return num_rows_processed
                    
                
            
            del definition_iterator_dict[ 'service_tag_ids_to_tags' ]
            
        
        self.SetUpdateProcessed( service_id, definition_hash )
        
        return num_rows_processed
        
    
    def ReprocessRepository( self, service_key: bytes, update_mime_types: typing.Collection[ int ] ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        self._ReprocessRepository( service_id, update_mime_types )
        
    
    def ScheduleRepositoryUpdateFileMaintenance( self, service_key, job_type ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        self._ScheduleRepositoryUpdateFileMaintenance( service_id, job_type )
        
    
    def SetRepositoryUpdateHashes( self, service_key: bytes, metadata: HydrusNetwork.Metadata ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        current_update_hash_ids = self._STS( self._c.execute( 'SELECT hash_id FROM {};'.format( repository_updates_table_name ) ) )
        
        all_future_update_hash_ids = self.modules_hashes_local_cache.GetHashIds( metadata.GetUpdateHashes() )
        
        deletee_hash_ids = current_update_hash_ids.difference( all_future_update_hash_ids )
        
        self._c.executemany( 'DELETE FROM {} WHERE hash_id = ?;'.format( repository_updates_table_name ), ( ( hash_id, ) for hash_id in deletee_hash_ids ) )
        
        inserts = []
        
        for ( update_index, update_hashes ) in metadata.GetUpdateIndicesAndHashes():
            
            for update_hash in update_hashes:
                
                hash_id = self.modules_hashes_local_cache.GetHashId( update_hash )
                
                result = self._c.execute( 'SELECT processed FROM {} WHERE hash_id = ?;'.format( repository_updates_table_name ), ( hash_id, ) ).fetchone()
                
                if result is None:
                    
                    processed = False
                    
                    inserts.append( ( update_index, hash_id, processed ) )
                    
                else:
                    
                    ( processed, ) = result
                    
                    self._c.execute( 'UPDATE {} SET update_index = ?, processed = ? WHERE hash_id = ?;'.format( repository_updates_table_name ), ( update_index, processed, hash_id ) )
                    
                
            
        
        self._c.executemany( 'INSERT OR IGNORE INTO {} ( update_index, hash_id, processed ) VALUES ( ?, ?, ? );'.format( repository_updates_table_name ), inserts )
        
    
    def SetUpdateProcessed( self, service_id, update_hash: bytes ):
        
        repository_updates_table_name = GenerateRepositoryUpdatesTableName( service_id )
        
        update_hash_id = self.modules_hashes_local_cache.GetHashId( update_hash )
        
        self._c.execute( 'UPDATE {} SET processed = ? WHERE hash_id = ?;'.format( repository_updates_table_name ), ( True, update_hash_id ) )
        
    