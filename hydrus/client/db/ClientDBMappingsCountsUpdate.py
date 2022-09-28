import sqlite3
import typing

from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBTagDisplay
from hydrus.client.db import ClientDBTagSearch
from hydrus.client.metadata import ClientTags

class ClientDBMappingsCountsUpdate( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts, modules_tags_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalTags, modules_tag_display: ClientDBTagDisplay.ClientDBTagDisplay, modules_tag_search: ClientDBTagSearch.ClientDBTagSearch ):
        
        self.modules_services = modules_services
        self.modules_mappings_counts = modules_mappings_counts
        self.modules_tags_local_cache = modules_tags_local_cache
        self.modules_tag_display = modules_tag_display
        self.modules_tag_search = modules_tag_search
        
        ClientDBModule.ClientDBModule.__init__( self, 'client mappings counts update', cursor )
        
    
    def AddCounts( self, tag_display_type, file_service_id, tag_service_id, ac_cache_changes ):
        
        ( new_tag_ids, new_local_tag_ids ) = self.modules_mappings_counts.AddCounts( tag_display_type, file_service_id, tag_service_id, ac_cache_changes )
        
        if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE and len( new_tag_ids ) > 0:
            
            if not self.modules_services.FileServiceIsCoveredByAllLocalFiles( file_service_id ):
                
                self.modules_tag_search.AddTags( file_service_id, tag_service_id, new_tag_ids )
                
            
            if len( new_local_tag_ids ) > 0:
                
                self.modules_tags_local_cache.AddTagIdsToCache( new_local_tag_ids )
                
            
        
    
    def FilterExistingTags( self, service_key: bytes, tags: typing.Collection[ str ] ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        tag_ids_to_tags = { self.modules_tags_local_cache.GetTagId( tag ) : tag for tag in tags }
        
        tag_ids = set( tag_ids_to_tags.keys() )
        
        with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_tag_id_table_name:
            
            counts = self.modules_mappings_counts.GetCountsForTags( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, service_id, temp_tag_id_table_name )
            
        
        existing_tag_ids = [ tag_id for ( tag_id, current_count, pending_count ) in counts if current_count > 0 ]
        
        filtered_tags = { tag_ids_to_tags[ tag_id ] for tag_id in existing_tag_ids }
        
        return filtered_tags
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def ReduceCounts( self, tag_display_type, file_service_id, tag_service_id, ac_cache_changes ):
        
        # this takes positive counts, despite ultimately being a reduce guy
        
        ( deleted_tag_ids, deleted_local_tag_ids ) = self.modules_mappings_counts.ReduceCounts( tag_display_type, file_service_id, tag_service_id, ac_cache_changes )
        
        if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE and len( deleted_tag_ids ) > 0:
            
            if not self.modules_services.FileServiceIsCoveredByAllLocalFiles( file_service_id ):
                
                # we don't want to delete chained stuff from definitions cache, even if count goes to zero!
                
                chained_tag_ids = self.modules_tag_display.FilterChained( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, deleted_tag_ids )
                
                deleted_tag_ids.difference_update( chained_tag_ids )
                
                self.modules_tag_search.DeleteTags( file_service_id, tag_service_id, deleted_tag_ids )
                
            
            if len( deleted_local_tag_ids ) > 0:
                
                include_current = True
                include_pending = False
                
                ids_to_count = self.modules_mappings_counts.GetCounts( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_tag_service_id, self.modules_services.combined_local_file_service_id, deleted_local_tag_ids, include_current, include_pending )
                
                useful_tag_ids = [ tag_id for ( tag_id, ( current_min, current_max, pending_min, pending_max ) ) in ids_to_count.items() if current_min > 0 ]
                
                bad_tag_ids = set( deleted_local_tag_ids ).difference( useful_tag_ids )
                
                self.modules_tags_local_cache.DropTagIdsFromCache( bad_tag_ids )
                
            
        
    
    def UpdateCounts( self, tag_display_type, file_service_id, tag_service_id, ac_cache_changes ):
        
        # unlike 'reduce' above, this can take positive as well as negative, so we'll split here for simplicity
        
        add_ac_cache_changes = []
        reduce_ac_cache_changes = []
        
        for ( tag_id, current_delta, pending_delta ) in ac_cache_changes:
            
            current_add_delta = 0
            pending_add_delta = 0
            
            current_reduce_delta = 0
            pending_reduce_delta = 0
            
            if current_delta > 0:
                
                current_add_delta = current_delta
                
            else:
                
                current_reduce_delta = abs( current_delta )
                
            
            if pending_delta > 0:
                
                pending_add_delta = pending_delta
                
            else:
                
                pending_reduce_delta = abs( pending_delta )
                
            
            if current_add_delta > 0 or pending_add_delta > 0:
                
                add_ac_cache_changes.append( ( tag_id, current_add_delta, pending_add_delta ) )
                
            
            if current_reduce_delta > 0 or pending_reduce_delta > 0:
                
                reduce_ac_cache_changes.append( ( tag_id, current_reduce_delta, pending_reduce_delta ) )
                
            
        
        if len( add_ac_cache_changes ) > 0:
            
            self.AddCounts( tag_display_type, file_service_id, tag_service_id, add_ac_cache_changes )
            
        
        if len( reduce_ac_cache_changes ) > 0:
            
            self.ReduceCounts( tag_display_type, file_service_id, tag_service_id, reduce_ac_cache_changes )
            
        
