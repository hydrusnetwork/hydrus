import collections
import collections.abc
import itertools
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork

from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesMaintenanceQueue
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.files import ClientFilesMaintenance

REPOSITORY_HASH_ID_MAP_PREFIX = 'repository_hash_id_map_'
REPOSITORY_TAG_ID_MAP_PREFIX = 'repository_tag_id_map_'

REPOSITORY_UPDATES_PREFIX = 'repository_updates_'
REPOSITORY_UNREGISTERED_UPDATES_PREFIX = 'repository_unregistered_updates_'
REPOSITORY_UPDATES_PROCESSED_PREFIX = 'repository_updates_processed_'

def GenerateRepositoryDefinitionTableNames( service_id: int ):
    
    suffix = str( service_id )
    
    hash_id_map_table_name = 'external_master.{}{}'.format( REPOSITORY_HASH_ID_MAP_PREFIX, suffix )
    tag_id_map_table_name = 'external_master.{}{}'.format( REPOSITORY_TAG_ID_MAP_PREFIX, suffix )
    
    return ( hash_id_map_table_name, tag_id_map_table_name )
    

def GenerateRepositoryFileDefinitionTableName( service_id: int ):
    
    ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
    
    return hash_id_map_table_name
    

def GenerateRepositoryTagDefinitionTableName( service_id: int ):
    
    ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
    
    return tag_id_map_table_name
    

def GenerateRepositoryUpdatesTableNames( service_id: int ):
    
    repository_updates_table_name = '{}{}'.format( REPOSITORY_UPDATES_PREFIX, service_id )
    repository_unregistered_updates_table_name = '{}{}'.format( REPOSITORY_UNREGISTERED_UPDATES_PREFIX, service_id )
    repository_updates_processed_table_name = '{}{}'.format( REPOSITORY_UPDATES_PROCESSED_PREFIX, service_id )
    
    return ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name )
    

class ClientDBRepositories( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper,
        modules_db_maintenance: ClientDBMaintenance.ClientDBMaintenance,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_files_metadata_basic: ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_tags_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalTags,
        modules_files_maintenance_queue: ClientDBFilesMaintenanceQueue.ClientDBFilesMaintenanceQueue
        ):
        
        # since we'll mostly be talking about hashes and tags we don't have locally, I think we shouldn't use the local caches
        
        super().__init__( 'client repositories', cursor )
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_db_maintenance = modules_db_maintenance
        self.modules_services = modules_services
        self.modules_files_storage = modules_files_storage
        self.modules_files_metadata_basic = modules_files_metadata_basic
        self.modules_files_maintenance_queue = modules_files_maintenance_queue
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_tags_local_cache = modules_tags_local_cache
        
        self._service_ids_to_content_types_to_outstanding_local_processing = collections.defaultdict( dict )
        
    
    def _ClearOutstandingWorkCache( self, service_id, content_type = None ):
        
        if service_id not in self._service_ids_to_content_types_to_outstanding_local_processing:
            
            return
            
        
        if content_type is None:
            
            del self._service_ids_to_content_types_to_outstanding_local_processing[ service_id ]
            
        else:
            
            if content_type in self._service_ids_to_content_types_to_outstanding_local_processing[ service_id ]:
                
                del self._service_ids_to_content_types_to_outstanding_local_processing[ service_id ][ content_type ]
                
            
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        # TODO: move some remote thumb calls from ClientDB to here
        return {
            'main.remote_thumbnails' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, hash_id INTEGER, PRIMARY KEY ( service_id, hash_id ) );', 50 )
        }
        
    
    def _GetServiceIndexGenerationDict( self, service_id ) -> dict:
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        index_generation_dict = {}
        
        index_generation_dict[ repository_updates_table_name ] = [
            ( [ 'hash_id' ], True, 449 )
        ]
        
        index_generation_dict[ repository_updates_processed_table_name ] = [
            ( [ 'content_type' ], False, 449 )
        ]
        
        return index_generation_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
        
        return {
            repository_updates_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( update_index INTEGER, hash_id INTEGER, PRIMARY KEY ( update_index, hash_id ) );', 449 ),
            repository_unregistered_updates_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 449 ),
            repository_updates_processed_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, content_type INTEGER, processed INTEGER_BOOLEAN, PRIMARY KEY ( hash_id, content_type ) );', 449 ),
            hash_id_map_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( service_hash_id INTEGER PRIMARY KEY, hash_id INTEGER );', 400 ),
            tag_id_map_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( service_tag_id INTEGER PRIMARY KEY, tag_id INTEGER );', 400 )
        }
        
    
    def _GetServiceTablePrefixes( self ):
        
        return {
            REPOSITORY_HASH_ID_MAP_PREFIX,
            REPOSITORY_TAG_ID_MAP_PREFIX,
            REPOSITORY_UPDATES_PREFIX,
            REPOSITORY_UNREGISTERED_UPDATES_PREFIX,
            REPOSITORY_UPDATES_PROCESSED_PREFIX
        }
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return self.modules_services.GetServiceIds( HC.REPOSITORIES )
        
    
    def _HandleCriticalRepositoryDefinitionError( self, service_id, name, bad_ids ):
        
        self._ReprocessRepository( service_id, ( HC.CONTENT_TYPE_DEFINITIONS, ) )
        
        self._ScheduleRepositoryUpdateFileMaintenance( service_id, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD )
        self._ScheduleRepositoryUpdateFileMaintenance( service_id, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
        
        self._cursor_transaction_wrapper.CommitAndBegin()
        
        message = 'A critical error was discovered with one of your repositories: its definition reference is in an invalid state. Your repository should now be paused, and all update files have been scheduled for an integrity and metadata check. Please permit file maintenance to check them, or tell it to do so manually, before unpausing your repository. Once unpaused, it will reprocess your definition files and attempt to fill the missing entries. If this error occurs again once that is complete, please inform hydrus dev.'
        message += '\n' * 2
        message += 'Error: {}: {}'.format( name, bad_ids )
        
        raise Exception( message )
        
    
    def _RegisterLocalUpdates( self, service_id, hash_ids = None ):
        
        # this function takes anything in 'unregistered', sees what is local, and figures out the correct 'content types' for those hash ids in the 'processed' table. converting unknown/bad hash_ids to correct and ready to process
        
        # it is ok if this guy gets hash ids that are already in the 'processed' table--it'll now resync them and correct if needed
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        if hash_ids is None:
            
            hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( repository_unregistered_updates_table_name ) ) )
            
        else:
            
            with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, repository_unregistered_updates_table_name ) ) )
                
            
        
        if len( hash_ids ) > 0:
            
            service_type = self.modules_services.GetService( service_id ).GetServiceType()
            
            with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                hash_ids_to_mimes = { hash_id : mime for ( hash_id, mime ) in self._Execute( 'SELECT hash_id, mime FROM {} CROSS JOIN files_info USING ( hash_id );'.format( temp_hash_ids_table_name ) ) }
                
                current_rows = set( self._Execute( 'SELECT hash_id, content_type FROM {} CROSS JOIN {} USING ( hash_id );'.format( temp_hash_ids_table_name, repository_updates_processed_table_name ) ) )
                
            
            correct_rows = set()
            
            for ( hash_id, mime ) in hash_ids_to_mimes.items():
                
                if mime == HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS:
                    
                    content_types = ( HC.CONTENT_TYPE_DEFINITIONS, )
                    
                else:
                    
                    content_types = tuple( HC.SERVICE_TYPES_TO_CONTENT_TYPES[ service_type ] )
                    
                
                correct_rows.update( ( ( hash_id, content_type ) for content_type in content_types ) )
                
            
            deletee_rows = current_rows.difference( correct_rows )
            
            if len( deletee_rows ) > 0:
                
                # these were registered wrong at some point
                self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ? AND content_type = ?;'.format( repository_updates_processed_table_name ), deletee_rows )
                
            
            insert_rows = correct_rows.difference( current_rows )
            
            if len( insert_rows ) > 0:
                
                processed = False
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id, content_type, processed ) VALUES ( ?, ?, ? );'.format( repository_updates_processed_table_name ), ( ( hash_id, content_type, processed ) for ( hash_id, content_type ) in insert_rows ) )
                
            
            if len( hash_ids_to_mimes ) > 0:
                
                self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( repository_unregistered_updates_table_name ), ( ( hash_id, ) for hash_id in hash_ids_to_mimes.keys() ) )
                
            
            if len( deletee_rows ) + len( insert_rows ) > 0:
                
                content_types_that_changed = { content_type for ( hash_id, content_type ) in deletee_rows.union( insert_rows ) }
                
                for content_type in content_types_that_changed:
                    
                    self._ClearOutstandingWorkCache( service_id, content_type = content_type )
                    
                
            
        
    
    def _ReprocessRepository( self, service_id, content_types ):
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        self._ExecuteMany( 'UPDATE {} SET processed = ? WHERE content_type = ?;'.format( repository_updates_processed_table_name ), ( ( False, content_type ) for content_type in content_types ) )
        
        self._ClearOutstandingWorkCache( service_id )
        
    
    def _ScheduleRepositoryUpdateFileMaintenance( self, service_id, job_type ):
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.local_update_service_id, repository_updates_table_name, HC.CONTENT_STATUS_CURRENT )
        
        update_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( table_join ) ) )
        
        self.modules_hashes_local_cache.SyncHashIds( update_hash_ids )
        
        # so we are also going to pull from here in case there are orphan records!!!
        other_table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.combined_local_file_service_id, repository_updates_table_name, HC.CONTENT_STATUS_CURRENT )
        
        other_update_hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {};'.format( other_table_join ) ) )
        
        update_hash_ids.update( other_update_hash_ids )
        
        self.modules_files_maintenance_queue.AddJobs( update_hash_ids, job_type )
        
    
    def AssociateRepositoryUpdateHashes( self, service_key: bytes, metadata_slice: HydrusNetwork.Metadata ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        inserts = []
        
        for ( update_index, update_hashes ) in metadata_slice.GetUpdateIndicesAndHashes():
            
            hash_ids = self.modules_hashes_local_cache.GetHashIds( update_hashes )
            
            inserts.extend( ( ( update_index, hash_id ) for hash_id in hash_ids ) )
            
        
        if len( inserts ) > 0:
            
            ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( update_index, hash_id ) VALUES ( ?, ? );'.format( repository_updates_table_name ), inserts )
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id ) VALUES ( ? );'.format( repository_unregistered_updates_table_name ), ( ( hash_id, ) for ( update_index, hash_id ) in inserts ) )
            
        
        self._RegisterLocalUpdates( service_id )
        
    
    def DropRepositoryTables( self, service_id: int ):
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        self.modules_db_maintenance.DeferredDropTable( repository_updates_table_name )
        self.modules_db_maintenance.DeferredDropTable( repository_unregistered_updates_table_name )
        self.modules_db_maintenance.DeferredDropTable( repository_updates_processed_table_name )
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
        
        self.modules_db_maintenance.DeferredDropTable( hash_id_map_table_name )
        self.modules_db_maintenance.DeferredDropTable( tag_id_map_table_name )
        
        self._ClearOutstandingWorkCache( service_id )
        
    
    def DoOutstandingUpdateRegistration( self ):
        
        for service_id in self.modules_services.GetServiceIds( HC.REPOSITORIES ):
            
            self._RegisterLocalUpdates( service_id )
            
        
    
    def GenerateRepositoryTables( self, service_id: int ):
        
        table_generation_dict = self._GetServiceTableGenerationDict( service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._CreateTable( create_query_without_name, table_name )
            
        
        index_generation_dict = self._GetServiceIndexGenerationDict( service_id )
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
    def GetRepositoryProgress( self, service_key: bytes ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        ( num_updates, ) = self._Execute( 'SELECT COUNT( * ) FROM {}'.format( repository_updates_table_name ) ).fetchone()
        
        table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.local_update_service_id, repository_updates_table_name, HC.CONTENT_STATUS_CURRENT )
        
        ( num_local_updates, ) = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( table_join ) ).fetchone()
        
        content_types_to_num_updates = collections.Counter( dict( self._Execute( 'SELECT content_type, COUNT( * ) FROM {} GROUP BY content_type;'.format( repository_updates_processed_table_name ) ) ) )
        content_types_to_num_processed_updates = collections.Counter( dict( self._Execute( 'SELECT content_type, COUNT( * ) FROM {} WHERE processed = ? GROUP BY content_type;'.format( repository_updates_processed_table_name ), ( True, ) ) ) )
        
        # little helpful thing that pays off later
        for content_type in content_types_to_num_updates:
            
            if content_type not in content_types_to_num_processed_updates:
                
                content_types_to_num_processed_updates[ content_type ] = 0
                
            
        
        return ( num_local_updates, num_updates, content_types_to_num_processed_updates, content_types_to_num_updates )
        
    
    def GetRepositoryUpdateHashesICanProcess( self, service_key: bytes, content_types_to_process ):
        
        # it is important that we use lists and sort by update index!
        # otherwise add/delete actions can occur in the wrong order
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        result = self._Execute( 'SELECT 1 FROM {} WHERE content_type = ? AND processed = ?;'.format( repository_updates_processed_table_name ), ( HC.CONTENT_TYPE_DEFINITIONS, True ) ).fetchone()
        
        this_is_first_definitions_work = result is None
        
        result = self._Execute( 'SELECT 1 FROM {} WHERE content_type != ? AND processed = ?;'.format( repository_updates_processed_table_name ), ( HC.CONTENT_TYPE_DEFINITIONS, True ) ).fetchone()
        
        this_is_first_content_work = result is None
        
        min_unregistered_update_index = None
        
        result = self._Execute( 'SELECT MIN( update_index ) FROM {} CROSS JOIN {} USING ( hash_id );'.format( repository_unregistered_updates_table_name, repository_updates_table_name ) ).fetchone()
        
        if result is not None:
            
            ( min_unregistered_update_index, ) = result
            
        
        predicate_phrase = 'processed = ? AND content_type IN {}'.format( HydrusLists.SplayListForDB( content_types_to_process ) )
        
        if min_unregistered_update_index is not None:
            
            # can't process an update if any of its files are as yet unregistered (these are both unprocessed and unavailable)
            # also, we mustn't skip any update indices, so if there is an invalid one, we won't do any after that!
            
            predicate_phrase = '{} AND update_index < {}'.format( predicate_phrase, min_unregistered_update_index )
            
        
        query = 'SELECT update_index, hash_id, content_type FROM {} CROSS JOIN {} USING ( hash_id ) WHERE {};'.format( repository_updates_processed_table_name, repository_updates_table_name, predicate_phrase )
        
        rows = self._Execute( query, ( False, ) ).fetchall()
        
        update_indices_to_unprocessed_hash_ids = HydrusData.BuildKeyToSetDict( ( ( update_index, hash_id ) for ( update_index, hash_id, content_type ) in rows ) )
        hash_ids_to_content_types_to_process = HydrusData.BuildKeyToSetDict( ( ( hash_id, content_type ) for ( update_index, hash_id, content_type ) in rows ) )
        
        all_hash_ids = set( hash_ids_to_content_types_to_process.keys() )
        
        all_local_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( self.modules_services.local_update_service_id, all_hash_ids, HC.CONTENT_STATUS_CURRENT )
        
        for sorted_update_index in sorted( update_indices_to_unprocessed_hash_ids.keys() ):
            
            unprocessed_hash_ids = update_indices_to_unprocessed_hash_ids[ sorted_update_index ]
            
            if not unprocessed_hash_ids.issubset( all_local_hash_ids ):
                
                # can't process an update if any of its unprocessed files are not local
                # normally they'll always be available if registered, but just in case a user deletes one manually etc...
                # also, we mustn't skip any update indices, so if there is an invalid one, we won't do any after that!
                
                update_indices_to_unprocessed_hash_ids = { update_index : unprocessed_hash_ids for ( update_index, unprocessed_hash_ids ) in update_indices_to_unprocessed_hash_ids.items() if update_index < sorted_update_index }
                
                break
                
            
        
        # all the hashes are now good to go
        
        all_hash_ids = set( itertools.chain.from_iterable( update_indices_to_unprocessed_hash_ids.values() ) )
        
        hash_ids_to_hashes = self.modules_hashes_local_cache.GetHashIdsToHashes( hash_ids = all_hash_ids )
        
        definition_hashes_and_content_types = []
        content_hashes_and_content_types = []
        
        if len( update_indices_to_unprocessed_hash_ids ) > 0:
            
            for update_index in sorted( update_indices_to_unprocessed_hash_ids.keys() ):
                
                unprocessed_hash_ids = update_indices_to_unprocessed_hash_ids[ update_index ]
                
                definition_hash_ids = { hash_id for hash_id in unprocessed_hash_ids if HC.CONTENT_TYPE_DEFINITIONS in hash_ids_to_content_types_to_process[ hash_id ] }
                content_hash_ids = { hash_id for hash_id in unprocessed_hash_ids if hash_id not in definition_hash_ids }
                
                for ( hash_ids, hashes_and_content_types ) in [
                    ( definition_hash_ids, definition_hashes_and_content_types ),
                    ( content_hash_ids, content_hashes_and_content_types )
                ]:
                    
                    hashes_and_content_types.extend( ( ( hash_ids_to_hashes[ hash_id ], hash_ids_to_content_types_to_process[ hash_id ] ) for hash_id in hash_ids ) )
                    
                
            
        
        return ( this_is_first_definitions_work, definition_hashes_and_content_types, this_is_first_content_work, content_hashes_and_content_types )
        
    
    def GetRepositoryUpdateHashesIDoNotHave( self, service_key: bytes ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        all_hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM {} ORDER BY update_index ASC;'.format( repository_updates_table_name ) ) )
        
        table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( self.modules_services.local_update_service_id, repository_updates_table_name, HC.CONTENT_STATUS_CURRENT )
        
        existing_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( table_join ) ) )
        
        needed_hash_ids = [ hash_id for hash_id in all_hash_ids if hash_id not in existing_hash_ids ]
        
        needed_hashes = self.modules_hashes_local_cache.GetHashes( needed_hash_ids )
        
        return needed_hashes
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'remote_thumbnails', 'hash_id' ) )
            
            for service_id in self.modules_services.GetServiceIds( HC.REPOSITORIES ):
                
                ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
                hash_id_map_table_name = GenerateRepositoryFileDefinitionTableName( service_id )
                
                tables_and_columns.extend( [
                    ( repository_updates_table_name, 'hash_id' ),
                    ( hash_id_map_table_name, 'hash_id' )
                ] )
                
            
        elif content_type == HC.CONTENT_TYPE_TAG:
            
            for service_id in self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES ):
                
                tag_id_map_table_name = GenerateRepositoryTagDefinitionTableName( service_id )
                
                tables_and_columns.extend( [
                    ( tag_id_map_table_name, 'tag_id' )
                ] )
                
            
        
        return tables_and_columns
        
    
    def HasLotsOfOutstandingLocalProcessing( self, service_id, content_types ):
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        content_types_to_outstanding_local_processing = self._service_ids_to_content_types_to_outstanding_local_processing[ service_id ]
        
        for content_type in content_types:
            
            if content_type not in content_types_to_outstanding_local_processing:
                
                result = self._STL( self._Execute( 'SELECT 1 FROM {} WHERE content_type = ? AND processed = ?;'.format( repository_updates_processed_table_name ), ( content_type, False ) ).fetchmany( 20 ) )
                
                content_types_to_outstanding_local_processing[ content_type ] = len( result ) >= 20
                
            
            if content_types_to_outstanding_local_processing[ content_type ]:
                
                return True
                
            
        
        return False
        
    
    def NormaliseServiceHashId( self, service_id: int, service_hash_id: int ) -> int:
        
        hash_id_map_table_name = GenerateRepositoryFileDefinitionTableName( service_id )
        
        result = self._Execute( 'SELECT hash_id FROM {} WHERE service_hash_id = ?;'.format( hash_id_map_table_name ), ( service_hash_id, ) ).fetchone()
        
        if result is None:
            
            self._HandleCriticalRepositoryDefinitionError( service_id, 'hash_id', service_hash_id )
            
        
        ( hash_id, ) = result
        
        return hash_id
        
    
    def NormaliseServiceHashIds( self, service_id: int, service_hash_ids: collections.abc.Collection[ int ] ) -> set[ int ]:
        
        hash_id_map_table_name = GenerateRepositoryFileDefinitionTableName( service_id )
        
        with self._MakeTemporaryIntegerTable( service_hash_ids, 'service_hash_id' ) as temp_table_name:
            
            # temp service hashes to lookup
            hash_ids_potentially_dupes = self._STL( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN {} USING ( service_hash_id );'.format( temp_table_name, hash_id_map_table_name ) ) )
            
        
        # every service_id can only exist once, but technically a hash_id could be mapped to two service_ids
        if len( hash_ids_potentially_dupes ) != len( service_hash_ids ):
            
            bad_service_hash_ids = []
            
            for service_hash_id in service_hash_ids:
                
                result = self._Execute( 'SELECT hash_id FROM {} WHERE service_hash_id = ?;'.format( hash_id_map_table_name ), ( service_hash_id, ) ).fetchone()
                
                if result is None:
                    
                    bad_service_hash_ids.append( service_hash_id )
                    
                
            
            self._HandleCriticalRepositoryDefinitionError( service_id, 'hash_ids', bad_service_hash_ids )
            
        
        hash_ids = set( hash_ids_potentially_dupes )
        
        return hash_ids
        
    
    def NormaliseServiceTagId( self, service_id: int, service_tag_id: int ) -> int:
        
        tag_id_map_table_name = GenerateRepositoryTagDefinitionTableName( service_id )
        
        result = self._Execute( 'SELECT tag_id FROM {} WHERE service_tag_id = ?;'.format( tag_id_map_table_name ), ( service_tag_id, ) ).fetchone()
        
        if result is None:
            
            self._HandleCriticalRepositoryDefinitionError( service_id, 'tag_id', service_tag_id )
            
        
        ( tag_id, ) = result
        
        return tag_id
        
    
    def NotifyUpdatesChanged( self, hash_ids ):
        
        # a mime changed
        
        for service_id in self.modules_services.GetServiceIds( HC.REPOSITORIES ):
            
            ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id ) VALUES ( ? );'.format( repository_unregistered_updates_table_name ), ( ( hash_id, ) for hash_id in hash_ids ) )
            
            self._RegisterLocalUpdates( service_id, hash_ids )
            
        
    
    def NotifyUpdatesImported( self, hash_ids ):
        
        for service_id in self.modules_services.GetServiceIds( HC.REPOSITORIES ):
            
            self._RegisterLocalUpdates( service_id, hash_ids )
            
        
    
    def ProcessRepositoryDefinitions( self, service_key: bytes, definition_hash: bytes, definition_iterator_dict, content_types, job_status, work_period ):
        
        # ignore content_types for now
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        precise_time_to_stop = HydrusTime.GetNowPrecise() + work_period
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryDefinitionTableNames( service_id )
        
        num_rows_processed = 0
        
        if 'service_hash_ids_to_hashes' in definition_iterator_dict:
            
            i = definition_iterator_dict[ 'service_hash_ids_to_hashes' ]
            
            for chunk in HydrusLists.SplitIteratorIntoAutothrottledChunks( i, 50, precise_time_to_stop ):
                
                inserts = []
                
                for ( service_hash_id, hash ) in chunk:
                    
                    hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                    
                    inserts.append( ( service_hash_id, hash_id ) )
                    
                
                self._ExecuteMany( 'REPLACE INTO {} ( service_hash_id, hash_id ) VALUES ( ?, ? );'.format( hash_id_map_table_name ), inserts )
                
                num_rows_processed += len( inserts )
                
                if HydrusTime.TimeHasPassedPrecise( precise_time_to_stop ) or job_status.IsCancelled():
                    
                    return num_rows_processed
                    
                
            
            del definition_iterator_dict[ 'service_hash_ids_to_hashes' ]
            
        
        if 'service_tag_ids_to_tags' in definition_iterator_dict:
            
            i = definition_iterator_dict[ 'service_tag_ids_to_tags' ]
            
            for chunk in HydrusLists.SplitIteratorIntoAutothrottledChunks( i, 50, precise_time_to_stop ):
                
                inserts = []
                
                for ( service_tag_id, tag ) in chunk:
                    
                    try:
                        
                        tag_id = self.modules_tags_local_cache.GetTagId( tag )
                        
                    except HydrusExceptions.TagSizeException:
                        
                        # in future what we'll do here is assign this id to the 'do not show' table, so we know it exists, but it is knowingly filtered out
                        # _or something_. maybe a small 'invalid' table, so it isn't mixed up with potentially re-addable tags
                        tag_id = self.modules_tags_local_cache.GetTagId( 'invalid repository tag' )
                        
                    
                    inserts.append( ( service_tag_id, tag_id ) )
                    
                
                self._ExecuteMany( 'REPLACE INTO {} ( service_tag_id, tag_id ) VALUES ( ?, ? );'.format( tag_id_map_table_name ), inserts )
                
                num_rows_processed += len( inserts )
                
                if HydrusTime.TimeHasPassedPrecise( precise_time_to_stop ) or job_status.IsCancelled():
                    
                    return num_rows_processed
                    
                
            
            del definition_iterator_dict[ 'service_tag_ids_to_tags' ]
            
        
        self.SetUpdateProcessed( service_id, definition_hash, ( HC.CONTENT_TYPE_DEFINITIONS, ) )
        
        return num_rows_processed
        
    
    def ReprocessRepository( self, service_key: bytes, content_types: collections.abc.Collection[ int ] ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        self._ReprocessRepository( service_id, content_types )
        
    
    def ScheduleRepositoryUpdateFileMaintenance( self, service_key, job_type ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        self._ScheduleRepositoryUpdateFileMaintenance( service_id, job_type )
        
    
    def SetRepositoryUpdateHashes( self, service_key: bytes, metadata: HydrusNetwork.Metadata ):
        
        # this is a full metadata resync
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        all_future_update_hash_ids = self.modules_hashes_local_cache.GetHashIds( metadata.GetUpdateHashes() )
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        #
        
        current_update_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( repository_updates_table_name ) ) )
        
        self._Execute( 'DELETE FROM {};'.format( repository_updates_table_name ) )
        
        #
        
        self._Execute( 'DELETE FROM {};'.format( repository_unregistered_updates_table_name ) )
        
        # we want to keep 'yes we processed this' records on a full metadata resync
        
        good_current_hash_ids = current_update_hash_ids.intersection( all_future_update_hash_ids )
        
        current_processed_table_update_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( repository_updates_processed_table_name ) ) )
        
        deletee_processed_table_update_hash_ids = current_processed_table_update_hash_ids.difference( good_current_hash_ids )
        
        self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( repository_updates_processed_table_name ), ( ( hash_id, ) for hash_id in deletee_processed_table_update_hash_ids ) )
        
        #
        
        inserts = []
        
        for ( update_index, update_hashes ) in metadata.GetUpdateIndicesAndHashes():
            
            for update_hash in update_hashes:
                
                hash_id = self.modules_hashes_local_cache.GetHashId( update_hash )
                
                inserts.append( ( update_index, hash_id ) )
                
            
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( update_index, hash_id ) VALUES ( ?, ? );'.format( repository_updates_table_name ), inserts )
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id ) VALUES ( ? );'.format( repository_unregistered_updates_table_name ), ( ( hash_id, ) for hash_id in all_future_update_hash_ids ) )
        
        self._RegisterLocalUpdates( service_id )
        
    
    def SetUpdateProcessed( self, service_id: int, update_hash: bytes, content_types: collections.abc.Collection[ int ] ):
        
        ( repository_updates_table_name, repository_unregistered_updates_table_name, repository_updates_processed_table_name ) = GenerateRepositoryUpdatesTableNames( service_id )
        
        update_hash_id = self.modules_hashes_local_cache.GetHashId( update_hash )
        
        self._ExecuteMany( 'UPDATE {} SET processed = ? WHERE hash_id = ? AND content_type = ?;'.format( repository_updates_processed_table_name ), ( ( True, update_hash_id, content_type ) for content_type in content_types ) )
        
        for content_type in content_types:
            
            self._ClearOutstandingWorkCache( service_id, content_type )
            
        
