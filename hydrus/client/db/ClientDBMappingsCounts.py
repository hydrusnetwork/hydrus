import collections
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusDBBase

from hydrus.client import ClientData
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.metadata import ClientTags

def GenerateCombinedFilesMappingsCountsCacheTableName( tag_display_type, tag_service_id ):
    
    if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE:
        
        name = 'combined_files_ac_cache'
        
    elif tag_display_type == ClientTags.TAG_DISPLAY_ACTUAL:
        
        name = 'combined_files_display_ac_cache'
        
    
    suffix = str( tag_service_id )
    
    combined_counts_cache_table_name = 'external_caches.{}_{}'.format( name, suffix )
    
    return combined_counts_cache_table_name
    
def GenerateSpecificCountsCacheTableName( tag_display_type, file_service_id, tag_service_id ):
    
    if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE:
        
        name = 'specific_ac_cache'
        
    elif tag_display_type == ClientTags.TAG_DISPLAY_ACTUAL:
        
        name = 'specific_display_ac_cache'
        
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    specific_counts_cache_table_name = 'external_caches.{}_{}'.format( name, suffix )
    
    return specific_counts_cache_table_name
    
class ClientDBMappingsCounts( ClientDBModule.ClientDBModule ):
    
    CAN_REPOPULATE_ALL_MISSING_DATA = True
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices ):
        
        self.modules_services = modules_services
        
        ClientDBModule.ClientDBModule.__init__( self, 'client mappings counts', cursor )
        
        self._missing_storage_tag_service_pairs = set()
        self._missing_display_tag_service_pairs = set()
        
    
    def _GetServiceTableGenerationDictSingle( self, tag_display_type, file_service_id, tag_service_id ):
        
        table_dict = {}
        
        table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        # the version was earlier here but we updated when adding combined delete files and ipfs to these tables
        version = 465
        
        table_dict[ table_name ] = ( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER PRIMARY KEY, current_count INTEGER, pending_count INTEGER );', version )
        
        return table_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        tag_service_id = service_id
        
        table_dict = {}
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ) )
        file_service_ids.append( self.modules_services.combined_file_service_id )
        
        for file_service_id in file_service_ids:
            
            for tag_display_type in ( ClientTags.TAG_DISPLAY_STORAGE, ClientTags.TAG_DISPLAY_ACTUAL ):
                
                single_table_dict = self._GetServiceTableGenerationDictSingle( tag_display_type, file_service_id, tag_service_id )
                
                table_dict.update( single_table_dict )
                
            
        
        return table_dict
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        
    
    def _RepairRepopulateTables( self, table_names, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES ) )
        file_service_ids.append( self.modules_services.combined_file_service_id )
        
        tag_service_ids = list( self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES ) )
        
        for tag_service_id in tag_service_ids:
            
            for file_service_id in file_service_ids:
                
                storage_table_dict_for_this = self._GetServiceTableGenerationDictSingle( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id )
                
                storage_table_names_for_this = set( storage_table_dict_for_this.keys() )
                
                if not storage_table_names_for_this.isdisjoint( table_names ):
                    
                    self._missing_storage_tag_service_pairs.add( ( file_service_id, tag_service_id ) )
                    
                
                display_table_dict_for_this = self._GetServiceTableGenerationDictSingle( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id )
                
                display_table_names_for_this = set( display_table_dict_for_this.keys() )
                
                if not display_table_names_for_this.isdisjoint( table_names ):
                    
                    self._missing_display_tag_service_pairs.add( ( file_service_id, tag_service_id ) )
                    
                
            
        
    
    def AddCounts( self, tag_display_type, file_service_id, tag_service_id, ac_cache_changes ):
        
        counts_cache_table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        new_tag_ids = set()
        new_local_tag_ids = set()
        
        for ( tag_id, current_delta, pending_delta ) in ac_cache_changes:
            
            self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id, current_count, pending_count ) VALUES ( ?, ?, ? );'.format( counts_cache_table_name ), ( tag_id, current_delta, pending_delta ) )
            
            if self._GetRowCount() > 0:
                
                new_tag_ids.add( tag_id )
                
                if file_service_id == self.modules_services.combined_local_file_service_id: # and tag_service_id = all known tags
                    
                    new_local_tag_ids.add( tag_id )
                    
                
            
        
        if len( new_tag_ids ) < len( ac_cache_changes ):
            
            self._ExecuteMany( 'UPDATE {} SET current_count = current_count + ?, pending_count = pending_count + ? WHERE tag_id = ?;'.format( counts_cache_table_name ), ( ( num_current, num_pending, tag_id ) for ( tag_id, num_current, num_pending ) in ac_cache_changes if tag_id not in new_tag_ids ) )
            
        
        return ( new_tag_ids, new_local_tag_ids )
        
    
    def ClearCounts( self, tag_display_type, file_service_id, tag_service_id, keep_current = False, keep_pending = False ):
        
        table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        if keep_current:
            
            self._Execute( 'UPDATE {} SET pending_count = 0 WHERE pending_count > 0;'.format( table_name ) )
            
            self._Execute( 'DELETE FROM {} WHERE current_count = 0 AND pending_count = 0;'.format( table_name ) )
            
        elif keep_pending:
            
            self._Execute( 'UPDATE {} SET current_count = 0 WHERE current_count > 0;'.format( table_name ) )
            
            self._Execute( 'DELETE FROM {} WHERE current_count = 0 AND pending_count = 0;'.format( table_name ) )
            
        else:
            
            self._Execute( 'DELETE FROM {};'.format( table_name ) )
            
        
    
    def CreateTables( self, tag_display_type, file_service_id, tag_service_id, populate_from_storage = False ):
        
        table_generation_dict = self._GetServiceTableGenerationDictSingle( tag_display_type, file_service_id, tag_service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._Execute( create_query_without_name.format( table_name ) )
            
        
        #
        
        if tag_display_type == ClientTags.TAG_DISPLAY_ACTUAL and populate_from_storage:
            
            display_table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
            storage_table_name = self.GetCountsCacheTableName( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id )
            
            self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id, current_count, pending_count ) SELECT tag_id, current_count, pending_count FROM {};'.format( display_table_name, storage_table_name ) )
            
        
    
    def DropTables( self, tag_display_type, file_service_id, tag_service_id ):
        
        table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( table_name ) )
        
    
    def FilterExistingTagIds( self, tag_display_type, file_service_id, tag_service_id, tag_ids_table_name ):
        
        counts_cache_table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        return self._STS( self._Execute( 'SELECT tag_id FROM {} CROSS JOIN {} USING ( tag_id );'.format( tag_ids_table_name, counts_cache_table_name ) ) )
        
    
    def GetCounts( self, tag_display_type, tag_service_id, file_service_id, tag_ids, include_current, include_pending, domain_is_cross_referenced = True, zero_count_ok = False, job_key = None, tag_ids_table_name = None ):
        
        if len( tag_ids ) == 0:
            
            return {}
            
        
        if tag_service_id == self.modules_services.combined_tag_service_id and file_service_id == self.modules_services.combined_file_service_id:
            
            ids_to_count = {}
            
            return ids_to_count
            
        
        if tag_service_id == self.modules_services.combined_tag_service_id:
            
            search_tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = [ tag_service_id ]
            
        
        cache_results = []
        
        if len( tag_ids ) > 1:
            
            if tag_ids_table_name is None:
                
                with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_tag_id_table_name:
                    
                    for search_tag_service_id in search_tag_service_ids:
                        
                        if job_key is not None and job_key.IsCancelled():
                            
                            return {}
                            
                        
                        cache_results.extend( self.GetCountsForTags( tag_display_type, file_service_id, search_tag_service_id, temp_tag_id_table_name ) )
                        
                    
                
            else:
                
                for search_tag_service_id in search_tag_service_ids:
                    
                    if job_key is not None and job_key.IsCancelled():
                        
                        return {}
                        
                    
                    cache_results.extend( self.GetCountsForTags( tag_display_type, file_service_id, search_tag_service_id, tag_ids_table_name ) )
                    
                
            
        else:
            
            ( tag_id, ) = tag_ids
            
            for search_tag_service_id in search_tag_service_ids:
                
                cache_results.extend( self.GetCountsForTag( tag_display_type, file_service_id, search_tag_service_id, tag_id ) )
                
            
        
        #
        
        ids_to_count = {}
        
        for ( tag_id, current_count, pending_count ) in cache_results:
            
            if not include_current:
                
                current_count = 0
                
            
            if not include_pending:
                
                pending_count = 0
                
            
            if current_count == 0 and pending_count == 0 and not zero_count_ok:
                
                continue
                
            
            current_max = current_count
            pending_max = pending_count
            
            if domain_is_cross_referenced:
                
                # file counts are perfectly accurate
                
                current_min = current_count
                pending_min = pending_count
                
            else:
                
                # for instance this is a search for 'my files' deleted files, but we are searching on 'all deleted files' domain
                
                current_min = 0
                pending_min = 0
                
            
            if tag_id in ids_to_count:
                
                ( existing_current_min, existing_current_max, existing_pending_min, existing_pending_max ) = ids_to_count[ tag_id ]
                
                ( current_min, current_max ) = ClientData.MergeCounts( existing_current_min, existing_current_max, current_min, current_max )
                ( pending_min, pending_max ) = ClientData.MergeCounts( existing_pending_min, existing_pending_max, pending_min, pending_max )
                
            
            ids_to_count[ tag_id ] = ( current_min, current_max, pending_min, pending_max )
            
        
        if zero_count_ok:
            
            for tag_id in tag_ids:
                
                if tag_id not in ids_to_count:
                    
                    ids_to_count[ tag_id ] = ( 0, 0, 0, 0 )
                    
                
            
        
        return ids_to_count
        
    
    def GetCountsCacheTableName( self, tag_display_type, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            counts_cache_table_name = GenerateCombinedFilesMappingsCountsCacheTableName( tag_display_type, tag_service_id )
            
        else:
            
            counts_cache_table_name = GenerateSpecificCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
            
        
        return counts_cache_table_name
        
    
    def GetCountsEstimate( self, tag_display_type: int, tag_service_id: int, file_service_id: int, tag_ids: typing.Collection[ int ], include_current_tags: bool, include_pending_tags: bool ):
        
        ids_to_count = collections.Counter()
        
        if not include_current_tags and not include_pending_tags:
            
            return ids_to_count
            
        
        ids_to_count_statuses = self.GetCountsEstimateStatuses( tag_display_type, tag_service_id, file_service_id, tag_ids )
        
        for ( tag_id, ( current_count, pending_count ) ) in ids_to_count_statuses.items():
            
            count = 0
            
            if include_current_tags:
                
                count += current_count
                
            
            if include_current_tags:
                
                count += pending_count
                
            
            ids_to_count[ tag_id ] = count
            
        
        return ids_to_count
        
    
    def GetCountsEstimateStatuses( self, tag_display_type: int, tag_service_id: int, file_service_id: int, tag_ids: typing.Collection[ int ] ):
        
        include_current_tags = True
        include_pending_tags = True
        
        ids_to_count_full = self.GetCounts( tag_display_type, tag_service_id, file_service_id, tag_ids, include_current_tags, include_pending_tags )
        
        ids_to_count_statuses = collections.defaultdict( lambda: ( 0, 0 ) )
        
        for ( tag_id, ( current_min, current_max, pending_min, pending_max ) ) in ids_to_count_full.items():
            
            ids_to_count_statuses[ tag_id ] = ( current_min, pending_min )
            
        
        return ids_to_count_statuses
        
    
    def GetCountsForTag( self, tag_display_type, file_service_id, tag_service_id, tag_id ):
        
        counts_cache_table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        return self._Execute( 'SELECT tag_id, current_count, pending_count FROM {} WHERE tag_id = ?;'.format( counts_cache_table_name ), ( tag_id, ) ).fetchall()
        
    
    def GetCountsForTags( self, tag_display_type, file_service_id, tag_service_id, temp_tag_id_table_name ):
        
        counts_cache_table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        # temp tags to counts
        return self._Execute( 'SELECT tag_id, current_count, pending_count FROM {} CROSS JOIN {} USING ( tag_id );'.format( temp_tag_id_table_name, counts_cache_table_name ) ).fetchall()
        
    
    def GetCurrentPendingPositiveCountsAndWeights( self, tag_display_type, file_service_id, tag_service_id, tag_ids, tag_ids_table_name = None ):
        
        include_current = True
        include_pending = True
        
        ids_to_count = self.GetCounts( tag_display_type, tag_service_id, file_service_id, tag_ids, include_current, include_pending, tag_ids_table_name = tag_ids_table_name )
        
        current_tag_ids = set()
        current_tag_weight = 0
        pending_tag_ids = set()
        pending_tag_weight = 0
        
        for ( tag_id, ( current_min, current_max, pending_min, pending_max ) ) in ids_to_count.items():
            
            if current_min > 0:
                
                current_tag_ids.add( tag_id )
                current_tag_weight += current_min
                
            
            if pending_min > 0:
                
                pending_tag_ids.add( tag_id )
                pending_tag_weight += pending_min
                
            
        
        return ( current_tag_ids, current_tag_weight, pending_tag_ids, pending_tag_weight )
        
    
    def GetMissingTagCountServicePairs( self ):
        
        return ( self._missing_storage_tag_service_pairs, self._missing_display_tag_service_pairs )
        
    
    def GetQueryPhraseForCurrentTagIds( self, tag_display_type, file_service_id, tag_service_id ):
        
        counts_cache_table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        return 'SELECT tag_id FROM {} WHERE current_count > 0'.format( counts_cache_table_name )
    
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_TAG:
            
            table_dict = self._GetServicesTableGenerationDict()
            
            for table_name in table_dict.keys():
                
                tables_and_columns.append( ( table_name, 'tag_id' ) )
                
            
        
        return tables_and_columns
        
    
    def GetTotalCurrentCount( self, tag_display_type, file_service_id, tag_service_id ):
        
        counts_cache_table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        result = self._Execute( 'SELECT SUM( current_count ) FROM {};'.format( counts_cache_table_name ) ).fetchone()
        
        if result is None or result[0] is None:
            
            count = 0
            
        else:
            
            ( count, ) = result
            
        
        return count
        
    
    def ReduceCounts( self, tag_display_type, file_service_id, tag_service_id, ac_cache_changes ):
        
        # this takes positive counts, despite ultimately being a reduce guy
        
        counts_cache_table_name = self.GetCountsCacheTableName( tag_display_type, file_service_id, tag_service_id )
        
        deleted_tag_ids = set()
        deleted_local_tag_ids = set()
        
        for ( tag_id, current_delta, pending_delta ) in ac_cache_changes:
            
            self._Execute( 'DELETE FROM {} WHERE tag_id = ? AND current_count = ? AND pending_count = ?;'.format( counts_cache_table_name ), ( tag_id, current_delta, pending_delta ) )
            
            if self._GetRowCount() > 0:
                
                deleted_tag_ids.add( tag_id )
                
                if file_service_id == self.modules_services.combined_local_file_service_id: # and tag_service_id = all known tags
                    
                    deleted_local_tag_ids.add( tag_id )
                    
                
            
        
        if len( deleted_tag_ids ) < len( ac_cache_changes ):
            
            self._ExecuteMany( 'UPDATE {} SET current_count = current_count - ?, pending_count = pending_count - ? WHERE tag_id = ?;'.format( counts_cache_table_name ), ( ( current_delta, pending_delta, tag_id ) for ( tag_id, current_delta, pending_delta ) in ac_cache_changes if tag_id not in deleted_tag_ids ) )
            
        
        return ( deleted_tag_ids, deleted_local_tag_ids )
        
    