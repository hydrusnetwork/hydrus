import sqlite3
import typing

from hydrus.core import HydrusConstants as HC

from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

def DoingAFileJoinTagSearchIsFaster( estimated_file_row_count, estimated_tag_row_count ):
    
    # ok, so there are times we want to do a tag search when we already know a superset of the file results (e.g. 'get all of these files that are tagged with samus')
    # sometimes it is fastest to just do the search using tag outer-join-loop/indices and intersect/difference in python
    # sometimes it is fastest to do the search with a temp file table and CROSS JOIN or EXISTS or similar to effect file outer-join-loop/indices
    
    # with experimental profiling, it is generally 2.5 times as slow to look up mappings using file indices. it also takes about 0.1 the time to set up temp table and other misc overhead
    # so, when we have file result A, and we want to fetch B, if the estimated size of A is < 2.6 the estimated size of B, we can save a bunch of time
    
    # normally, we could let sqlite do NATURAL JOIN analyze profiling, but that sometimes fails for me when the queries get complex, I believe due to my wewlad 'temp table' queries and weird tag/file index distribution
    
    file_lookup_speed_ratio = 2.5
    temp_table_overhead = 0.1
    
    return estimated_file_row_count * ( file_lookup_speed_ratio + temp_table_overhead ) < estimated_tag_row_count
    
def GenerateMappingsTableNames( service_id: int ) -> typing.Tuple[ str, str, str, str ]:
    
    suffix = str( service_id )
    
    current_mappings_table_name = 'external_mappings.current_mappings_{}'.format( suffix )
    
    deleted_mappings_table_name = 'external_mappings.deleted_mappings_{}'.format( suffix )
    
    pending_mappings_table_name = 'external_mappings.pending_mappings_{}'.format( suffix )
    
    petitioned_mappings_table_name = 'external_mappings.petitioned_mappings_{}'.format( suffix )
    
    return ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name )
    
def GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id ):
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    cache_current_mappings_table_name = 'external_caches.specific_current_mappings_cache_{}'.format( suffix )
    
    cache_deleted_mappings_table_name = 'external_caches.specific_deleted_mappings_cache_{}'.format( suffix )
    
    cache_pending_mappings_table_name = 'external_caches.specific_pending_mappings_cache_{}'.format( suffix )
    
    return ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name )
    
class ClientDBMappingsStorage( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices ):
        
        self.modules_services = modules_services
        
        ClientDBModule.ClientDBModule.__init__( self, 'client mappings storage', cursor )
        
    
    def _GetServiceIndexGenerationDict( self, service_id ) -> dict:
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        index_generation_dict = {}
        
        index_generation_dict[ current_mappings_table_name ] = [
            ( [ 'hash_id', 'tag_id' ], True, 400 )
        ]
        
        index_generation_dict[ deleted_mappings_table_name ] = [
            ( [ 'hash_id', 'tag_id' ], True, 400 )
        ]
        
        index_generation_dict[ pending_mappings_table_name ] = [
            ( [ 'hash_id', 'tag_id' ], True, 400 )
        ]
        
        index_generation_dict[ petitioned_mappings_table_name ] = [
            ( [ 'hash_id', 'tag_id' ], True, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        return {
            current_mappings_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;', 400 ),
            deleted_mappings_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;', 400 ),
            pending_mappings_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;', 400 ),
            petitioned_mappings_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;', 400 )
        }
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        
    
    def ClearMappingsTables( self, service_id: int ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        self._Execute( 'DELETE FROM {};'.format( current_mappings_table_name ) )
        self._Execute( 'DELETE FROM {};'.format( deleted_mappings_table_name ) )
        self._Execute( 'DELETE FROM {};'.format( pending_mappings_table_name ) )
        self._Execute( 'DELETE FROM {};'.format( petitioned_mappings_table_name ) )
        
    
    def DropMappingsTables( self, service_id: int ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( current_mappings_table_name ) )
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( deleted_mappings_table_name ) )
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( pending_mappings_table_name ) )
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( petitioned_mappings_table_name ) )
        
    
    def GenerateMappingsTables( self, service_id: int ):
        
        table_generation_dict = self._GetServiceTableGenerationDict( service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._Execute( create_query_without_name.format( table_name ) )
            
        
        index_generation_dict = self._GetServiceIndexGenerationDict( service_id )
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
    def GetCurrentFilesCount( self, service_id: int ) -> int:
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        result = self._Execute( 'SELECT COUNT( DISTINCT hash_id ) FROM {};'.format( current_mappings_table_name ) ).fetchone()
        
        ( count, ) = result
        
        return count
        
    
    def GetDeletedMappingsCount( self, service_id: int ) -> int:
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        result = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( deleted_mappings_table_name ) ).fetchone()
        
        ( count, ) = result
        
        return count
        
    
    def GetFastestStorageMappingTableNames( self, file_service_id: int, tag_service_id: int ):
        
        statuses_to_table_names = {}
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( tag_service_id )
        
        statuses_to_table_names[ HC.CONTENT_STATUS_CURRENT ] = current_mappings_table_name
        statuses_to_table_names[ HC.CONTENT_STATUS_DELETED ] = deleted_mappings_table_name
        statuses_to_table_names[ HC.CONTENT_STATUS_PENDING ] = pending_mappings_table_name
        statuses_to_table_names[ HC.CONTENT_STATUS_PETITIONED ] = petitioned_mappings_table_name
        
        if file_service_id != self.modules_services.combined_file_service_id:
            
            ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
            
            statuses_to_table_names[ HC.CONTENT_STATUS_CURRENT ] = cache_current_mappings_table_name
            statuses_to_table_names[ HC.CONTENT_STATUS_DELETED ] = cache_deleted_mappings_table_name
            statuses_to_table_names[ HC.CONTENT_STATUS_PENDING ] = cache_pending_mappings_table_name
            
        
        return statuses_to_table_names
        
    
    def GetPendingMappingsCount( self, service_id: int ) -> int:
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        result = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( pending_mappings_table_name ) ).fetchone()
        
        ( count, ) = result
        
        return count
        
    
    def GetPetitionedMappingsCount( self, service_id: int ) -> int:
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        result = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( petitioned_mappings_table_name ) ).fetchone()
        
        ( count, ) = result
        
        return count
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            for service_id in self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES ):
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
                
                tables_and_columns.extend( [
                    ( current_mappings_table_name, 'hash_id' ),
                    ( deleted_mappings_table_name, 'hash_id' ),
                    ( pending_mappings_table_name, 'hash_id' ),
                    ( petitioned_mappings_table_name, 'hash_id' )
                ] )
                
            
        elif content_type == HC.CONTENT_TYPE_TAG:
            
            for service_id in self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES ):
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
                
                tables_and_columns.extend( [
                    ( current_mappings_table_name, 'tag_id' ),
                    ( deleted_mappings_table_name, 'tag_id' ),
                    ( pending_mappings_table_name, 'tag_id' ),
                    ( petitioned_mappings_table_name, 'tag_id' )
                ] )
                
            
        
        return tables_and_columns
        
    
