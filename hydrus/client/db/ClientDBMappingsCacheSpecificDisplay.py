import collections
import itertools
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBMappingsCountsUpdate
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBTagDisplay
from hydrus.client.metadata import ClientTags

def GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id ):
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    cache_display_current_mappings_table_name = 'external_caches.specific_display_current_mappings_cache_{}'.format( suffix )
    
    cache_display_pending_mappings_table_name = 'external_caches.specific_display_pending_mappings_cache_{}'.format( suffix )
    
    return ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name )
    
class ClientDBMappingsCacheSpecificDisplay( ClientDBModule.ClientDBModule ):
    
    CAN_REPOPULATE_ALL_MISSING_DATA = True
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts, modules_mappings_counts_update: ClientDBMappingsCountsUpdate.ClientDBMappingsCountsUpdate, modules_mappings_storage: ClientDBMappingsStorage.ClientDBMappingsStorage, modules_tag_display: ClientDBTagDisplay.ClientDBTagDisplay ):
        
        self.modules_services = modules_services
        self.modules_mappings_counts = modules_mappings_counts
        self.modules_mappings_counts_update = modules_mappings_counts_update
        self.modules_mappings_storage = modules_mappings_storage
        self.modules_tag_display = modules_tag_display
        
        ClientDBModule.ClientDBModule.__init__( self, 'client mappings counts', cursor )
        
    
    def _GetServiceIndexGenerationDictSingle( self, file_service_id, tag_service_id ):
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        index_generation_dict = {}
        
        index_generation_dict[ cache_display_current_mappings_table_name ] = [
            ( [ 'tag_id', 'hash_id' ], True, 400 )
        ]
        
        index_generation_dict[ cache_display_pending_mappings_table_name ] = [
            ( [ 'tag_id', 'hash_id' ], True, 400 )
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
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        version = 400
        
        table_dict[ cache_display_current_mappings_table_name ] = ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) ) WITHOUT ROWID;', version )
        table_dict[ cache_display_pending_mappings_table_name ] = ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) ) WITHOUT ROWID;', version )
        
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
        
    
    def AddFiles( self, file_service_id, tag_service_id, hash_ids, hash_ids_table_name ):
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        # temp hashes to mappings
        storage_current_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, cache_current_mappings_table_name ) ).fetchall()
        
        storage_current_mapping_ids_dict = HydrusData.BuildKeyToSetDict( storage_current_mapping_ids_raw )
        
        # temp hashes to mappings
        storage_pending_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_ids_table_name, cache_pending_mappings_table_name ) ).fetchall()
        
        storage_pending_mapping_ids_dict = HydrusData.BuildKeyToSetDict( storage_pending_mapping_ids_raw )
        
        all_storage_tag_ids = set( storage_current_mapping_ids_dict.keys() )
        all_storage_tag_ids.update( storage_pending_mapping_ids_dict.keys() )
        
        storage_tag_ids_to_implies_tag_ids = self.modules_tag_display.GetTagsToImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, all_storage_tag_ids )
        
        display_tag_ids_to_implied_by_tag_ids = collections.defaultdict( set )
        
        for ( storage_tag_id, implies_tag_ids ) in storage_tag_ids_to_implies_tag_ids.items():
            
            for implies_tag_id in implies_tag_ids:
                
                display_tag_ids_to_implied_by_tag_ids[ implies_tag_id ].add( storage_tag_id )
                
            
        
        counts_cache_changes = []
        
        # for all display tags implied by the existing storage mappings, add them
        # btw, when we add files to a specific domain, we know that all inserts are new
        
        for ( display_tag_id, implied_by_tag_ids ) in display_tag_ids_to_implied_by_tag_ids.items():
            
            display_current_hash_ids = set( itertools.chain.from_iterable( ( storage_current_mapping_ids_dict[ implied_by_tag_id ] for implied_by_tag_id in implied_by_tag_ids ) ) )
            
            current_delta = len( display_current_hash_ids )
            
            if current_delta > 0:
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_display_current_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, display_tag_id ) for hash_id in display_current_hash_ids ) )
                
            
            #
            
            display_pending_hash_ids = set( itertools.chain.from_iterable( ( storage_pending_mapping_ids_dict[ implied_by_tag_id ] for implied_by_tag_id in implied_by_tag_ids ) ) )
            
            pending_delta = len( display_pending_hash_ids )
            
            if pending_delta > 0:
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_display_pending_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, display_tag_id ) for hash_id in display_pending_hash_ids ) )
                
            
            #
            
            if current_delta > 0 or pending_delta > 0:
                
                counts_cache_changes.append( ( display_tag_id, current_delta, pending_delta ) )
                
            
        
        if len( counts_cache_changes ) > 0:
            
            self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def AddImplications( self, file_service_id, tag_service_id, implication_tag_ids, tag_id, status_hook = None ):
        
        if len( implication_tag_ids ) == 0:
            
            return
            
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        statuses_to_count_delta = collections.Counter()
        
        ( current_implication_tag_ids, current_implication_tag_ids_weight, pending_implication_tag_ids, pending_implication_tag_ids_weight ) = self.modules_mappings_counts.GetCurrentPendingPositiveCountsAndWeights( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, implication_tag_ids )
        
        jobs = []
        
        jobs.append( ( HC.CONTENT_STATUS_CURRENT, cache_display_current_mappings_table_name, cache_current_mappings_table_name, current_implication_tag_ids, current_implication_tag_ids_weight ) )
        jobs.append( ( HC.CONTENT_STATUS_PENDING, cache_display_pending_mappings_table_name, cache_pending_mappings_table_name, pending_implication_tag_ids, pending_implication_tag_ids_weight ) )
        
        for ( status, cache_display_mappings_table_name, cache_mappings_table_name, add_tag_ids, add_tag_ids_weight ) in jobs:
            
            if add_tag_ids_weight == 0:
                
                # nothing to actually add, so nbd
                
                continue
                
            
            if len( add_tag_ids ) == 1:
                
                ( add_tag_id, ) = add_tag_ids
                
                self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id, tag_id ) SELECT hash_id, ? FROM {} WHERE tag_id = ?;'.format( cache_display_mappings_table_name, cache_mappings_table_name ), ( tag_id, add_tag_id ) )
                
                statuses_to_count_delta[ status ] = self._GetRowCount()
                
            else:
                
                with self._MakeTemporaryIntegerTable( add_tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
                    
                    # for all new implications, get files with those tags and not existing
                    
                    self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id, tag_id ) SELECT hash_id, ? FROM {} CROSS JOIN {} USING ( tag_id );'.format( cache_display_mappings_table_name, temp_tag_ids_table_name, cache_mappings_table_name ), ( tag_id, ) )
                    
                    statuses_to_count_delta[ status ] = self._GetRowCount()
                    
                
            
        
        current_delta = statuses_to_count_delta[ HC.CONTENT_STATUS_CURRENT ]
        pending_delta = statuses_to_count_delta[ HC.CONTENT_STATUS_PENDING ]
        
        if current_delta > 0 or pending_delta > 0:
            
            counts_cache_changes = ( ( tag_id, current_delta, pending_delta ), )
            
            self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def AddMappings( self, file_service_id, tag_service_id, tag_id, hash_ids ):
        
        # this guy doesn't do rescind pend because of storage calculation issues that need that to occur before deletes to storage tables
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        display_tag_ids = self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, tag_id )
        
        ac_counts = collections.Counter()
        
        for display_tag_id in display_tag_ids:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_display_current_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, display_tag_id ) for hash_id in hash_ids ) )
            
            num_added = self._GetRowCount()
            
            if num_added > 0:
                
                ac_counts[ display_tag_id ] += num_added
                
            
        
        if len( ac_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, current_delta, 0 ) for ( tag_id, current_delta ) in ac_counts.items() ]
            
            self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def Clear( self, file_service_id, tag_service_id, keep_pending = False ):
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        self._Execute( 'DELETE FROM {};'.format( cache_display_current_mappings_table_name ) )
        
        if not keep_pending:
            
            self._Execute( 'DELETE FROM {};'.format( cache_display_pending_mappings_table_name ) )
            
        
        self.modules_mappings_counts.ClearCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, keep_pending = keep_pending )
        
    
    def Drop( self, file_service_id, tag_service_id ):
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( cache_display_current_mappings_table_name ) )
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( cache_display_pending_mappings_table_name ) )
        
        self.modules_mappings_counts.DropTables( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id )
        
    
    def DeleteFiles( self, file_service_id, tag_service_id, hash_ids, hash_id_table_name ):
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        # temp hashes to mappings
        current_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_id_table_name, cache_display_current_mappings_table_name ) ).fetchall()
        
        current_mapping_ids_dict = HydrusData.BuildKeyToSetDict( current_mapping_ids_raw )
        
        # temp hashes to mappings
        pending_mapping_ids_raw = self._Execute( 'SELECT tag_id, hash_id FROM {} CROSS JOIN {} USING ( hash_id );'.format( hash_id_table_name, cache_display_pending_mappings_table_name ) ).fetchall()
        
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
            
        
        self._ExecuteMany( 'DELETE FROM ' + cache_display_current_mappings_table_name + ' WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        self._ExecuteMany( 'DELETE FROM ' + cache_display_pending_mappings_table_name + ' WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
        if len( counts_cache_changes ) > 0:
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def DeleteImplications( self, file_service_id, tag_service_id, implication_tag_ids, tag_id, status_hook = None ):
        
        if len( implication_tag_ids ) == 0:
            
            return
            
        
        statuses_to_count_delta = collections.Counter()
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        remaining_implication_tag_ids = set( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, tag_id ) ).difference( implication_tag_ids )
        
        ( current_implication_tag_ids, current_implication_tag_ids_weight, pending_implication_tag_ids, pending_implication_tag_ids_weight ) = self.modules_mappings_counts.GetCurrentPendingPositiveCountsAndWeights( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, implication_tag_ids )
        ( current_remaining_implication_tag_ids, current_remaining_implication_tag_ids_weight, pending_remaining_implication_tag_ids, pending_remaining_implication_tag_ids_weight ) = self.modules_mappings_counts.GetCurrentPendingPositiveCountsAndWeights( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, remaining_implication_tag_ids )
        
        jobs = []
        
        jobs.append( ( HC.CONTENT_STATUS_CURRENT, cache_display_current_mappings_table_name, cache_current_mappings_table_name, current_implication_tag_ids, current_implication_tag_ids_weight, current_remaining_implication_tag_ids, current_remaining_implication_tag_ids_weight ) )
        jobs.append( ( HC.CONTENT_STATUS_PENDING, cache_display_pending_mappings_table_name, cache_pending_mappings_table_name, pending_implication_tag_ids, pending_implication_tag_ids_weight, pending_remaining_implication_tag_ids, pending_remaining_implication_tag_ids_weight ) )
        
        for ( status, cache_display_mappings_table_name, cache_mappings_table_name, removee_tag_ids, removee_tag_ids_weight, keep_tag_ids, keep_tag_ids_weight ) in jobs:
            
            if removee_tag_ids_weight == 0:
                
                # nothing to remove, so nothing to do!
                
                continue
                
            
            # ultimately here, we are doing "delete all display mappings with hash_ids that have a storage mapping for a removee tag and no storage mappings for a keep tag
            # in order to reduce overhead, we go full meme and do a bunch of different situations
            
            with self._MakeTemporaryIntegerTable( [], 'tag_id' ) as temp_removee_tag_ids_table_name:
                
                with self._MakeTemporaryIntegerTable( [], 'tag_id' ) as temp_keep_tag_ids_table_name:
                    
                    if len( removee_tag_ids ) == 1:
                        
                        ( removee_tag_id, ) = removee_tag_ids
                        
                        hash_id_in_storage_remove = 'hash_id IN ( SELECT hash_id FROM {} WHERE tag_id = {} )'.format( cache_mappings_table_name, removee_tag_id )
                        
                    else:
                        
                        self._ExecuteMany( 'INSERT INTO {} ( tag_id ) VALUES ( ? );'.format( temp_removee_tag_ids_table_name ), ( ( removee_tag_id, ) for removee_tag_id in removee_tag_ids ) )
                        
                        hash_id_in_storage_remove = 'hash_id IN ( SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( tag_id ) )'.format( temp_removee_tag_ids_table_name, cache_mappings_table_name )
                        
                    
                    if keep_tag_ids_weight == 0:
                        
                        predicates_phrase = hash_id_in_storage_remove
                        
                    else:
                        
                        # WARNING, WARNING: Big Brain Query, potentially great/awful
                        # note that in the 'clever/file join' situation, the number of total mappings is many, but we are deleting a few
                        # we want to precisely scan the status of the potential hashes to delete, not scan through them all to see what not to do
                        # therefore, we do NOT EXISTS, which just scans the parts, rather than NOT IN, which does the whole query and then checks against all results
                        
                        if len( keep_tag_ids ) == 1:
                            
                            ( keep_tag_id, ) = keep_tag_ids
                            
                            if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( removee_tag_ids_weight, keep_tag_ids_weight ):
                                
                                hash_id_not_in_storage_keep = 'NOT EXISTS ( SELECT 1 FROM {} WHERE {}.hash_id = {}.hash_id and tag_id = {} )'.format( cache_mappings_table_name, cache_display_mappings_table_name, cache_mappings_table_name, keep_tag_id )
                                
                            else:
                                
                                hash_id_not_in_storage_keep = 'hash_id NOT IN ( SELECT hash_id FROM {} WHERE tag_id = {} )'.format( cache_mappings_table_name, keep_tag_id )
                                
                            
                        else:
                            
                            self._ExecuteMany( 'INSERT INTO {} ( tag_id ) VALUES ( ? );'.format( temp_keep_tag_ids_table_name ), ( ( keep_tag_id, ) for keep_tag_id in keep_tag_ids ) )
                            
                            if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( removee_tag_ids_weight, keep_tag_ids_weight ):
                                
                                # (files to) mappings to temp tags
                                hash_id_not_in_storage_keep = 'NOT EXISTS ( SELECT 1 FROM {} CROSS JOIN {} USING ( tag_id ) WHERE {}.hash_id = {}.hash_id )'.format( cache_mappings_table_name, temp_keep_tag_ids_table_name, cache_display_mappings_table_name, cache_mappings_table_name )
                                
                            else:
                                
                                # temp tags to mappings
                                hash_id_not_in_storage_keep = ' hash_id NOT IN ( SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( tag_id ) )'.format( temp_keep_tag_ids_table_name, cache_mappings_table_name )
                                
                            
                        
                        predicates_phrase = '{} AND {}'.format( hash_id_in_storage_remove, hash_id_not_in_storage_keep )
                        
                    
                    query = 'DELETE FROM {} WHERE tag_id = {} AND {};'.format( cache_display_mappings_table_name, tag_id, predicates_phrase )
                    
                    self._Execute( query )
                    
                    statuses_to_count_delta[ status ] = self._GetRowCount()
                    
                
            
        
        current_delta = statuses_to_count_delta[ HC.CONTENT_STATUS_CURRENT ]
        pending_delta = statuses_to_count_delta[ HC.CONTENT_STATUS_PENDING ]
        
        if current_delta > 0 or pending_delta > 0:
            
            counts_cache_changes = ( ( tag_id, current_delta, pending_delta ), )
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def DeleteMappings( self, file_service_id, tag_service_id, storage_tag_id, hash_ids ):
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        implies_tag_ids = self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, storage_tag_id )
        
        implies_tag_ids_to_implied_by_tag_ids = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, implies_tag_ids, tags_are_ideal = True )
        
        ac_counts = collections.Counter()
        
        for ( display_tag_id, implied_by_tag_ids ) in implies_tag_ids_to_implied_by_tag_ids.items():
            
            # for every tag implied by the storage tag being removed
            
            other_implied_by_tag_ids = set( implied_by_tag_ids )
            other_implied_by_tag_ids.discard( storage_tag_id )
            
            if len( other_implied_by_tag_ids ) == 0:
                
                # nothing else implies this tag on display, so can just straight up delete
                
                self._ExecuteMany( 'DELETE FROM {} WHERE tag_id = ? AND hash_id = ?;'.format( cache_display_current_mappings_table_name ), ( ( display_tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_deleted = self._GetRowCount()
                
            else:
                
                # other things imply this tag on display, so we need to check storage to see what else has it
                statuses_to_table_names = self.modules_mappings_storage.GetFastestStorageMappingTableNames( file_service_id, tag_service_id )
                
                mappings_table_name = statuses_to_table_names[ HC.CONTENT_STATUS_CURRENT ]
                
                with self._MakeTemporaryIntegerTable( other_implied_by_tag_ids, 'tag_id' ) as temp_table_name:
                    
                    delete = 'DELETE FROM {} WHERE tag_id = ? AND hash_id = ? AND NOT EXISTS ( SELECT 1 FROM {} CROSS JOIN {} USING ( tag_id ) WHERE hash_id = ? );'.format( cache_display_current_mappings_table_name, mappings_table_name, temp_table_name )
                    
                    self._ExecuteMany( delete, ( ( display_tag_id, hash_id, hash_id ) for hash_id in hash_ids ) )
                    
                    num_deleted = self._GetRowCount()
                    
                
            
            if num_deleted > 0:
                
                ac_counts[ display_tag_id ] += num_deleted
                
            
        
        if len( ac_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, current_delta, 0 ) for ( tag_id, current_delta ) in ac_counts.items() ]
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def Generate( self, file_service_id, tag_service_id, populate_from_storage = True, status_hook = None ):
        
        table_generation_dict = self._GetServiceTableGenerationDictSingle( file_service_id, tag_service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._Execute( create_query_without_name.format( table_name ) )
            
        
        if populate_from_storage:
            
            if status_hook is not None:
                
                status_hook( 'copying storage' )
                
            
            ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
            ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
            
            self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id, tag_id ) SELECT hash_id, tag_id FROM {};'.format( cache_display_current_mappings_table_name, cache_current_mappings_table_name ) )
            self._Execute( 'INSERT OR IGNORE INTO {} ( hash_id, tag_id ) SELECT hash_id, tag_id FROM {};'.format( cache_display_pending_mappings_table_name, cache_pending_mappings_table_name ) )
            
        
        self.modules_mappings_counts.CreateTables( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, populate_from_storage = populate_from_storage )
        
        if status_hook is not None:
            
            status_hook( 'optimising data' )
            
        
        index_generation_dict = self._GetServiceIndexGenerationDictSingle( file_service_id, tag_service_id )
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
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
        
    
    def PendMappings( self, file_service_id, tag_service_id, tag_id, hash_ids ):
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        ac_counts = collections.Counter()
        
        display_tag_ids = self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, tag_id )
        
        for display_tag_id in display_tag_ids:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO ' + cache_display_pending_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, display_tag_id ) for hash_id in hash_ids ) )
            
            num_added = self._GetRowCount()
            
            if num_added > 0:
                
                ac_counts[ display_tag_id ] += num_added
                
            
        
        if len( ac_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, 0, pending_delta ) for ( tag_id, pending_delta ) in ac_counts.items() ]
            
            self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def RegeneratePending( self, file_service_id, tag_service_id, status_hook = None ):
        
        ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        if status_hook is not None:
            
            message = 'clearing old specific display data'
            
            status_hook( message )
            
        
        all_pending_storage_tag_ids = self._STS( self._Execute( 'SELECT DISTINCT tag_id FROM {};'.format( cache_pending_mappings_table_name ) ) )
        
        storage_tag_ids_to_display_tag_ids = self.modules_tag_display.GetTagsToImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, all_pending_storage_tag_ids )
        
        all_pending_display_tag_ids = set( itertools.chain.from_iterable( storage_tag_ids_to_display_tag_ids.values() ) )
        
        del all_pending_storage_tag_ids
        del storage_tag_ids_to_display_tag_ids
        
        self.modules_mappings_counts.ClearCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, keep_current = True )
        
        self._Execute( 'DELETE FROM {};'.format( cache_display_pending_mappings_table_name ) )
        
        all_pending_display_tag_ids_to_implied_by_storage_tag_ids = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, all_pending_display_tag_ids, tags_are_ideal = True )
        
        counts_cache_changes = []
        
        num_to_do = len( all_pending_display_tag_ids_to_implied_by_storage_tag_ids )
        
        for ( i, ( display_tag_id, storage_tag_ids ) ) in enumerate( all_pending_display_tag_ids_to_implied_by_storage_tag_ids.items() ):
            
            if i % 100 == 0 and status_hook is not None:
                
                message = 'regenerating pending tags {}'.format( HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) )
                
                status_hook( message )
                
            
            if len( storage_tag_ids ) == 1:
                
                ( storage_tag_id, ) = storage_tag_ids
                
                self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id, hash_id ) SELECT ?, hash_id FROM {} WHERE tag_id = ?;'.format( cache_display_pending_mappings_table_name, cache_pending_mappings_table_name ), ( display_tag_id, storage_tag_id ) )
                
                pending_delta = self._GetRowCount()
                
            else:
                
                with self._MakeTemporaryIntegerTable( storage_tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
                    
                    # temp tags to mappings merged
                    self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id, hash_id ) SELECT DISTINCT ?, hash_id FROM {} CROSS JOIN {} USING ( tag_id );'.format( cache_display_pending_mappings_table_name, temp_tag_ids_table_name, cache_pending_mappings_table_name ), ( display_tag_id, ) )
                    
                    pending_delta = self._GetRowCount()
                    
                
            
            counts_cache_changes.append( ( display_tag_id, 0, pending_delta ) )
            
        
        self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
        
    
    def RescindPendingMappings( self, file_service_id, tag_service_id, storage_tag_id, hash_ids ):
        
        ( cache_display_current_mappings_table_name, cache_display_pending_mappings_table_name ) = GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
        
        implies_tag_ids = self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, storage_tag_id )
        
        implies_tag_ids_to_implied_by_tag_ids = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, implies_tag_ids, tags_are_ideal = True )
        
        ac_counts = collections.Counter()
        
        for ( display_tag_id, implied_by_tag_ids ) in implies_tag_ids_to_implied_by_tag_ids.items():
            
            # for every tag implied by the storage tag being removed
            
            other_implied_by_tag_ids = set( implied_by_tag_ids )
            other_implied_by_tag_ids.discard( storage_tag_id )
            
            if len( other_implied_by_tag_ids ) == 0:
                
                # nothing else implies this tag on display, so can just straight up delete
                
                self._ExecuteMany( 'DELETE FROM {} WHERE tag_id = ? AND hash_id = ?;'.format( cache_display_pending_mappings_table_name ), ( ( display_tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_rescinded = self._GetRowCount()
                
            else:
                
                # other things imply this tag on display, so we need to check storage to see what else has it
                statuses_to_table_names = self.modules_mappings_storage.GetFastestStorageMappingTableNames( file_service_id, tag_service_id )
                
                mappings_table_name = statuses_to_table_names[ HC.CONTENT_STATUS_PENDING ]
                
                with self._MakeTemporaryIntegerTable( other_implied_by_tag_ids, 'tag_id' ) as temp_table_name:
                    
                    # storage mappings to temp other tag ids
                    # delete mappings where it shouldn't exist for other reasons lad
                    delete = 'DELETE FROM {} WHERE tag_id = ? AND hash_id = ? AND NOT EXISTS ( SELECT 1 FROM {} CROSS JOIN {} USING ( tag_id ) WHERE hash_id = ? )'.format( cache_display_pending_mappings_table_name, mappings_table_name, temp_table_name )
                    
                    self._ExecuteMany( delete, ( ( display_tag_id, hash_id, hash_id ) for hash_id in hash_ids ) )
                    
                    num_rescinded = self._GetRowCount()
                    
                
            
            if num_rescinded > 0:
                
                ac_counts[ display_tag_id ] += num_rescinded
                
            
        
        if len( ac_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, 0, pending_delta ) for ( tag_id, pending_delta ) in ac_counts.items() ]
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_ACTUAL, file_service_id, tag_service_id, counts_cache_changes )
            
        
    