import collections
import sqlite3
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusDB

from hydrus.client.db import ClientDBMappingsCacheCombinedFilesDisplay
from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBMappingsCountsUpdate
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.metadata import ClientTags

class ClientDBMappingsCacheCombinedFilesStorage( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts, modules_mappings_counts_update: ClientDBMappingsCountsUpdate.ClientDBMappingsCountsUpdate, modules_mappings_cache_combined_files_display: ClientDBMappingsCacheCombinedFilesDisplay.ClientDBMappingsCacheCombinedFilesDisplay ):
        
        self.modules_services = modules_services
        self.modules_mappings_counts = modules_mappings_counts
        self.modules_mappings_counts_update = modules_mappings_counts_update
        self.modules_mappings_cache_combined_files_display = modules_mappings_cache_combined_files_display
        
        ClientDBModule.ClientDBModule.__init__( self, 'client combined files storage mappings cache', cursor )
        
    
    def Clear( self, tag_service_id, keep_pending = False ):
        
        self.modules_mappings_counts.ClearCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, keep_pending = keep_pending )
        
        self.modules_mappings_cache_combined_files_display.Clear( tag_service_id, keep_pending = keep_pending )
        
    
    def Drop( self, tag_service_id ):
        
        self.modules_mappings_counts.DropTables( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id )
        
        self.modules_mappings_cache_combined_files_display.Drop( tag_service_id )
        
    
    def Generate( self, tag_service_id ):
        
        self.modules_mappings_counts.CreateTables( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id )
        
        #
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
        
        current_mappings_exist = self._Execute( 'SELECT 1 FROM ' + current_mappings_table_name + ' LIMIT 1;' ).fetchone() is not None
        pending_mappings_exist = self._Execute( 'SELECT 1 FROM ' + pending_mappings_table_name + ' LIMIT 1;' ).fetchone() is not None
        
        if current_mappings_exist or pending_mappings_exist: # not worth iterating through all known tags for an empty service
            
            for ( group_of_ids, num_done, num_to_do ) in HydrusDB.ReadLargeIdQueryInSeparateChunks( self._c, 'SELECT tag_id FROM tags;', 10000 ): # must be a cleverer way of doing this
                
                with self._MakeTemporaryIntegerTable( group_of_ids, 'tag_id' ) as temp_table_name:
                    
                    current_counter = collections.Counter()
                    
                    # temp tags to mappings
                    for ( tag_id, count ) in self._Execute( 'SELECT tag_id, COUNT( * ) FROM {} CROSS JOIN {} USING ( tag_id ) GROUP BY ( tag_id );'.format( temp_table_name, current_mappings_table_name ) ):
                        
                        current_counter[ tag_id ] = count
                        
                    
                    pending_counter = collections.Counter()
                    
                    # temp tags to mappings
                    for ( tag_id, count ) in self._Execute( 'SELECT tag_id, COUNT( * ) FROM {} CROSS JOIN {} USING ( tag_id ) GROUP BY ( tag_id );'.format( temp_table_name, pending_mappings_table_name ) ):
                        
                        pending_counter[ tag_id ] = count
                        
                    
                
                all_ids_seen = set( current_counter.keys() )
                all_ids_seen.update( pending_counter.keys() )
                
                counts_cache_changes = [ ( tag_id, current_counter[ tag_id ], pending_counter[ tag_id ] ) for tag_id in all_ids_seen ]
                
                if len( counts_cache_changes ) > 0:
                    
                    self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
                    
                
            
        
        self.modules_mappings_cache_combined_files_display.Generate( tag_service_id )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def RegeneratePending( self, tag_service_id, status_hook = None ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
        
        if status_hook is not None:
            
            message = 'clearing old combined display data'
            
            status_hook( message )
            
        
        all_pending_storage_tag_ids = self._STS( self._Execute( 'SELECT DISTINCT tag_id FROM {};'.format( pending_mappings_table_name ) ) )
        
        self.modules_mappings_counts.ClearCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, keep_current = True )
        
        counts_cache_changes = []
        
        num_to_do = len( all_pending_storage_tag_ids )
        
        for ( i, storage_tag_id ) in enumerate( all_pending_storage_tag_ids ):
            
            if i % 100 == 0 and status_hook is not None:
                
                message = 'regenerating pending tags {}'.format( HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) )
                
                status_hook( message )
                
            
            ( pending_delta, ) = self._Execute( 'SELECT COUNT( DISTINCT hash_id ) FROM {} WHERE tag_id = ?;'.format( pending_mappings_table_name ), ( storage_tag_id, ) ).fetchone()
            
            counts_cache_changes.append( ( storage_tag_id, 0, pending_delta ) )
            
        
        self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
        
        self.modules_mappings_cache_combined_files_display.RegeneratePending( tag_service_id, status_hook = status_hook )
        
