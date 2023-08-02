import collections
import itertools
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime

from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBMappingsCacheSpecificDisplay
from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBMappingsCountsUpdate
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.metadata import ClientTags

class FilteredHashesGenerator( object ):
    
    def __init__( self, file_service_ids_to_valid_hash_ids ):
        
        self._file_service_ids_to_valid_hash_ids = file_service_ids_to_valid_hash_ids
        
    
    def GetHashes( self, file_service_id, hash_ids ):
        
        return self._file_service_ids_to_valid_hash_ids[ file_service_id ].intersection( hash_ids )
        
    
    def IterateHashes( self, hash_ids ):
        
        for ( file_service_id, valid_hash_ids ) in self._file_service_ids_to_valid_hash_ids.items():
            
            if len( valid_hash_ids ) == 0:
                
                continue
                
            
            filtered_hash_ids = valid_hash_ids.intersection( hash_ids )
            
            if len( filtered_hash_ids ) == 0:
                
                continue
                
            
            yield ( file_service_id, filtered_hash_ids )
            
        
    
class FilteredMappingsGenerator( object ):
    
    def __init__( self, file_service_ids_to_valid_hash_ids, mappings_ids ):
        
        self._file_service_ids_to_valid_hash_ids = file_service_ids_to_valid_hash_ids
        self._mappings_ids = mappings_ids
        
    
    def IterateMappings( self, file_service_id ):
        
        valid_hash_ids = self._file_service_ids_to_valid_hash_ids[ file_service_id ]
        
        if len( valid_hash_ids ) > 0:
            
            for ( tag_id, hash_ids ) in self._mappings_ids:
                
                hash_ids = valid_hash_ids.intersection( hash_ids )
                
                if len( hash_ids ) == 0:
                    
                    continue
                    
                
                yield ( tag_id, hash_ids )
                
            
        
    
class ClientDBMappingsCacheSpecificStorage( ClientDBModule.ClientDBModule ):
    
    CAN_REPOPULATE_ALL_MISSING_DATA = True
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_db_maintenance: ClientDBMaintenance.ClientDBMaintenance, modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts, modules_mappings_counts_update: ClientDBMappingsCountsUpdate.ClientDBMappingsCountsUpdate, modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage, modules_mappings_cache_specific_display: ClientDBMappingsCacheSpecificDisplay.ClientDBMappingsCacheSpecificDisplay ):
        
        self.modules_services = modules_services
        self.modules_db_maintenance = modules_db_maintenance
        self.modules_mappings_counts = modules_mappings_counts
        self.modules_mappings_counts_update = modules_mappings_counts_update
        self.modules_files_storage = modules_files_storage
        self.modules_mappings_cache_specific_display = modules_mappings_cache_specific_display
        
        self._missing_tag_service_pairs = set()
        
        ClientDBModule.ClientDBModule.__init__( self, 'client specific display mappings cache', cursor )
        
    
    def _GetServiceIndexGenerationDictSingle( self, file_service_id, tag_service_id ):
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        version = 486 if file_service_id == self.modules_services.combined_local_media_service_id else 400
        
        index_generation_dict = {}
        
        index_generation_dict[ cache_current_mappings_table_name ] = [
            ( [ 'tag_id', 'hash_id' ], True, version )
        ]
        
        index_generation_dict[ cache_deleted_mappings_table_name ] = [
            ( [ 'tag_id', 'hash_id' ], True, version )
        ]
        
        index_generation_dict[ cache_pending_mappings_table_name ] = [
            ( [ 'tag_id', 'hash_id' ], True, version )
        ]
        
        return index_generation_dict
        
    
    def _GetServiceIndexGenerationDict( self, service_id ) -> dict:
        
        tag_service_id = service_id
        
        index_dict = {}
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ) )
        
        for file_service_id in file_service_ids:
            
            single_index_dict = self._GetServiceIndexGenerationDictSingle( file_service_id, tag_service_id )
            
            index_dict.update( single_index_dict )
            
        
        return index_dict
        
    
    def _GetServiceTableGenerationDictSingle( self, file_service_id, tag_service_id ):
        
        table_dict = {}
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        version = 486 if file_service_id == self.modules_services.combined_local_media_service_id else 400
        
        table_dict[ cache_current_mappings_table_name ] = ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) ) WITHOUT ROWID;', version )
        table_dict[ cache_deleted_mappings_table_name ] = ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) ) WITHOUT ROWID;', version )
        table_dict[ cache_pending_mappings_table_name ] = ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) ) WITHOUT ROWID;', version )
        
        return table_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        tag_service_id = service_id
        
        table_dict = {}
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ) )
        
        for file_service_id in file_service_ids:
            
            single_table_dict = self._GetServiceTableGenerationDictSingle( file_service_id, tag_service_id )
            
            table_dict.update( single_table_dict )
            
        
        return table_dict
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        
    
    def _RepairRepopulateTables( self, table_names, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ) )
        tag_service_ids = list( self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES ) )
        
        for tag_service_id in tag_service_ids:
            
            for file_service_id in file_service_ids:
                
                table_dict_for_this = self._GetServiceTableGenerationDictSingle( file_service_id, tag_service_id )
                
                table_names_for_this = set( table_dict_for_this.keys() )
                
                if not table_names_for_this.isdisjoint( table_names ):
                    
                    self._missing_tag_service_pairs.add( ( file_service_id, tag_service_id ) )
                    
                
            
        
    
    def AddFiles( self, file_service_id, tag_service_id, hash_ids, hash_ids_table_name ):
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
        
        # deleted don't have a/c counts to update, so we can do it all in one go here
        self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id, tag_id ) SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( cache_deleted_mappings_table_name, hash_ids_table_name, deleted_mappings_table_name ) )
        
        # temp hashes to mappings
        current_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, current_mappings_table_name ) ).fetchall()
        
        current_mapping_ids_dict = HydrusData.BuildKeyToSetDict( current_mapping_ids_raw )
        
        # temp hashes to mappings
        pending_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, pending_mappings_table_name ) ).fetchall()
        
        pending_mapping_ids_dict = HydrusData.BuildKeyToSetDict( pending_mapping_ids_raw )
        
        all_ids_seen = set( current_mapping_ids_dict.keys() )
        all_ids_seen.update( pending_mapping_ids_dict.keys() )
        
        counts_cache_changes = []
        
        for tag_id in all_ids_seen:
            
            current_hash_ids = current_mapping_ids_dict[ tag_id ]
            
            current_delta = len( current_hash_ids )
            
            if current_delta > 0:
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_current_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in current_hash_ids ) )
                
                current_delta = self._GetRowCount()
                
            
            #
            
            pending_hash_ids = pending_mapping_ids_dict[ tag_id ]
            
            pending_delta = len( pending_hash_ids )
            
            if pending_delta > 0:
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_pending_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in pending_hash_ids ) )
                
                pending_delta = self._GetRowCount()
                
            
            #
            
            if current_delta > 0 or pending_delta > 0:
                
                counts_cache_changes.append( ( tag_id, current_delta, pending_delta ) )
                
            
        
        if len( counts_cache_changes ) > 0:
            
            self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def AddMappings( self, tag_service_id, tag_id, hash_ids, filtered_hashes_generator: FilteredHashesGenerator ):
        
        for ( file_service_id, filtered_hash_ids ) in filtered_hashes_generator.IterateHashes( hash_ids ):
            
            ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
            
            # we have to interleave this into the iterator so that if two siblings with the same ideal are pend->currented at once, we remain logic consistent for soletag lookups!
            self.modules_mappings_cache_specific_display.RescindPendingMappings( file_service_id, tag_service_id, tag_id, filtered_hash_ids )
            
            self._ExecuteMany( 'DELETE FROM ' + cache_pending_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in filtered_hash_ids ) )
            
            num_pending_rescinded = self._GetRowCount()
            
            #
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_current_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in filtered_hash_ids ) )
            
            num_current_inserted = self._GetRowCount()
            
            #
            
            self._ExecuteMany( 'DELETE FROM ' + cache_deleted_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in filtered_hash_ids ) )
            
            if num_current_inserted > 0:
                
                counts_cache_changes = [ ( tag_id, num_current_inserted, 0 ) ]
                
                self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, counts_cache_changes )
                
            
            if num_pending_rescinded > 0:
                
                counts_cache_changes = [ ( tag_id, 0, num_pending_rescinded ) ]
                
                self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, counts_cache_changes )
                
            
            self.modules_mappings_cache_specific_display.AddMappings( file_service_id, tag_service_id, tag_id, filtered_hash_ids )
            
        
    
    def Clear( self, file_service_id, tag_service_id, keep_pending = False ):
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        self._Execute( 'DELETE FROM {};'.format( cache_current_mappings_table_name ) )
        self._Execute( 'DELETE FROM {};'.format( cache_deleted_mappings_table_name ) )
        
        if not keep_pending:
            
            self._Execute( 'DELETE FROM {};'.format( cache_pending_mappings_table_name ) )
            
        
        self.modules_mappings_counts.ClearCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, keep_pending = keep_pending )
        
        self.modules_mappings_cache_specific_display.Clear( file_service_id, tag_service_id, keep_pending = keep_pending )
        
    
    def CreateTables( self, file_service_id, tag_service_id ):
        
        table_generation_dict = self._GetServiceTableGenerationDictSingle( file_service_id, tag_service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._CreateTable( create_query_without_name, table_name )
            
        
        self.modules_mappings_counts.CreateTables( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id )
        
    
    def Drop( self, file_service_id, tag_service_id ):
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        self.modules_db_maintenance.DeferredDropTable( cache_current_mappings_table_name )
        self.modules_db_maintenance.DeferredDropTable( cache_deleted_mappings_table_name )
        self.modules_db_maintenance.DeferredDropTable( cache_pending_mappings_table_name )
        
        self.modules_mappings_counts.DropTables( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id )
        
        self.modules_mappings_cache_specific_display.Drop( file_service_id, tag_service_id )
        
    
    def DeleteFiles( self, file_service_id, tag_service_id, hash_ids, hash_id_table_name ):
        
        self.modules_mappings_cache_specific_display.DeleteFiles( file_service_id, tag_service_id, hash_ids, hash_id_table_name )
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        # temp hashes to mappings
        deleted_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_id_table_name, cache_deleted_mappings_table_name ) ).fetchall()
        
        if len( deleted_mapping_ids_raw ) > 0:
            
            self._ExecuteMany( 'DELETE FROM {} WHERE tag_id = ? AND hash_id = ?;'.format( cache_deleted_mappings_table_name ), deleted_mapping_ids_raw )
            
        
        # temp hashes to mappings
        current_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_id_table_name, cache_current_mappings_table_name ) ).fetchall()
        
        current_mapping_ids_dict = HydrusData.BuildKeyToSetDict( current_mapping_ids_raw )
        
        # temp hashes to mappings
        pending_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_id_table_name, cache_pending_mappings_table_name ) ).fetchall()
        
        pending_mapping_ids_dict = HydrusData.BuildKeyToSetDict( pending_mapping_ids_raw )
        
        all_ids_seen = set( current_mapping_ids_dict.keys() )
        all_ids_seen.update( pending_mapping_ids_dict.keys() )
        
        counts_cache_changes = []
        
        for tag_id in all_ids_seen:
            
            current_hash_ids = current_mapping_ids_dict[ tag_id ]
            
            num_current = len( current_hash_ids )
            
            #
            
            pending_hash_ids = pending_mapping_ids_dict[ tag_id ]
            
            num_pending = len( pending_hash_ids )
            
            counts_cache_changes.append( ( tag_id, num_current, num_pending ) )
            
        
        self._ExecuteMany( 'DELETE FROM ' + cache_current_mappings_table_name + ' WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        self._ExecuteMany( 'DELETE FROM ' + cache_pending_mappings_table_name + ' WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
        if len( counts_cache_changes ) > 0:
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def DeleteMappings( self, tag_service_id, tag_id, hash_ids, filtered_hashes_generator: FilteredHashesGenerator ):
        
        for ( file_service_id, filtered_hash_ids ) in filtered_hashes_generator.IterateHashes( hash_ids ):
            
            ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
            
            self.modules_mappings_cache_specific_display.DeleteMappings( file_service_id, tag_service_id, tag_id, filtered_hash_ids )
            
            self._ExecuteMany( 'DELETE FROM ' + cache_current_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in filtered_hash_ids ) )
            
            num_deleted = self._GetRowCount()
            
            #
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_deleted_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in filtered_hash_ids ) )
            
            if num_deleted > 0:
                
                counts_cache_changes = [ ( tag_id, num_deleted, 0 ) ]
                
                self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, counts_cache_changes )
                
            
        
    
    def Generate( self, file_service_id, tag_service_id ):
        
        self.CreateTables( file_service_id, tag_service_id )
        
        #
        
        hash_ids = self.modules_files_storage.GetCurrentHashIdsList( file_service_id )
        
        BLOCK_SIZE = 10000
        
        for ( i, block_of_hash_ids ) in enumerate( HydrusLists.SplitListIntoChunks( hash_ids, BLOCK_SIZE ) ):
            
            with self._MakeTemporaryIntegerTable( block_of_hash_ids, 'hash_id' ) as temp_hash_id_table_name:
                
                self.AddFiles( file_service_id, tag_service_id, block_of_hash_ids, temp_hash_id_table_name )
                
            
        
        index_generation_dict = self._GetServiceIndexGenerationDictSingle( file_service_id, tag_service_id )
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
        self.modules_db_maintenance.TouchAnalyzeNewTables()
        
        self.modules_mappings_cache_specific_display.Generate( file_service_id, tag_service_id, populate_from_storage = True )
        
    
    def GetFilteredHashesGenerator( self, file_service_ids, tag_service_id, hash_ids ) -> FilteredHashesGenerator:
        
        file_service_ids_to_valid_hash_ids = collections.defaultdict( set )
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_table_name:
            
            for file_service_id in file_service_ids:
                
                table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( file_service_id, temp_table_name, HC.CONTENT_STATUS_CURRENT )
                
                valid_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( table_join ) ) )
                
                file_service_ids_to_valid_hash_ids[ file_service_id ] = valid_hash_ids
                
            
        
        return FilteredHashesGenerator( file_service_ids_to_valid_hash_ids )
        
    
    def GetFilteredMappingsGenerator( self, file_service_ids, tag_service_id, mappings_ids ) -> FilteredMappingsGenerator:
        
        all_hash_ids = set( itertools.chain.from_iterable( ( hash_ids for ( tag_id, hash_ids ) in mappings_ids ) ) )
        
        file_service_ids_to_valid_hash_ids = collections.defaultdict( set )
        
        with self._MakeTemporaryIntegerTable( all_hash_ids, 'hash_id' ) as temp_table_name:
            
            for file_service_id in file_service_ids:
                
                table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( file_service_id, temp_table_name, HC.CONTENT_STATUS_CURRENT )
                
                valid_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( table_join ) ) )
                
                file_service_ids_to_valid_hash_ids[ file_service_id ] = valid_hash_ids
                
            
        
        return FilteredMappingsGenerator( file_service_ids_to_valid_hash_ids, mappings_ids )
        
    
    def GetMissingServicePairs( self ):
        
        return self._missing_tag_service_pairs
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_TAG:
            
            table_dict = self._GetServicesTableGenerationDict()
            
            for table_name in table_dict.keys():
                
                tables_and_columns.append( ( table_name, 'tag_id' ) )
                
            
        elif content_type == HC.CONTENT_TYPE_HASH:
            
            table_dict = self._GetServicesTableGenerationDict()
            
            for table_name in table_dict.keys():
                
                tables_and_columns.append( ( table_name, 'hash_id' ) )
                
            
        
        return tables_and_columns
        
    
    def PendMappings( self, tag_service_id, tag_id, hash_ids, filtered_hashes_generator: FilteredHashesGenerator ):
        
        for ( file_service_id, filtered_hash_ids ) in filtered_hashes_generator.IterateHashes( hash_ids ):
            
            ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_pending_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in filtered_hash_ids ) )
            
            num_added = self._GetRowCount()
            
            if num_added > 0:
                
                counts_cache_changes = [ ( tag_id, 0, num_added ) ]
                
                self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, counts_cache_changes )
                
            
            self.modules_mappings_cache_specific_display.PendMappings( file_service_id, tag_service_id, tag_id, filtered_hash_ids )
            
        
    
    def RegeneratePending( self, file_service_id, tag_service_id, status_hook = None ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        if status_hook is not None:
            
            message = 'clearing old specific data'
            
            status_hook( message )
            
        
        all_pending_storage_tag_ids = self._STS( self._Execute( 'SELECT DISTINCT tag_id FROM {};'.format( pending_mappings_table_name ) ) )
        
        self.modules_mappings_counts.ClearCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, keep_current = True )
        
        self._Execute( 'DELETE FROM {};'.format( cache_pending_mappings_table_name ) )
        
        counts_cache_changes = []
        
        num_to_do = len( all_pending_storage_tag_ids )
        
        select_table_join = self.modules_files_storage.GetTableJoinLimitedByFileDomain( file_service_id, pending_mappings_table_name, HC.CONTENT_STATUS_CURRENT )
        
        for ( i, storage_tag_id ) in enumerate( all_pending_storage_tag_ids ):
            
            if i % 100 == 0 and status_hook is not None:
                
                message = 'regenerating pending tags {}'.format( HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) )
                
                status_hook( message )
                
            
            self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id, hash_id ) SELECT tag_id, hash_id FROM {} WHERE tag_id = ?;'.format( cache_pending_mappings_table_name, select_table_join ), ( storage_tag_id, ) )
            
            pending_delta = self._GetRowCount()
            
            counts_cache_changes.append( ( storage_tag_id, 0, pending_delta ) )
            
        
        self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, counts_cache_changes )
        
        self.modules_mappings_cache_specific_display.RegeneratePending( file_service_id, tag_service_id, status_hook = status_hook )
        
    
    def RescindPendingMappings( self, tag_service_id, tag_id, hash_ids, filtered_hashes_generator: FilteredHashesGenerator ):
        
        for ( file_service_id, filtered_hash_ids ) in filtered_hashes_generator.IterateHashes( hash_ids ):
            
            ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
            
            ac_counts = collections.Counter()
            
            self.modules_mappings_cache_specific_display.RescindPendingMappings( file_service_id, tag_service_id, tag_id, filtered_hash_ids )
            
            self._ExecuteMany( 'DELETE FROM ' + cache_pending_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in filtered_hash_ids ) )
            
            num_deleted = self._GetRowCount()
            
            if num_deleted > 0:
                
                counts_cache_changes = [ ( tag_id, 0, num_deleted ) ]
                
                self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, counts_cache_changes )
                
            
        
    
