import collections
import itertools
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusTime

from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBMappingsCountsUpdate
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBTagDisplay
from hydrus.client.metadata import ClientTags

class ClientDBMappingsCacheCombinedFilesDisplay( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts, modules_mappings_counts_update: ClientDBMappingsCountsUpdate.ClientDBMappingsCountsUpdate, modules_mappings_storage: ClientDBMappingsStorage.ClientDBMappingsStorage, modules_tag_display: ClientDBTagDisplay.ClientDBTagDisplay, modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage ):
        
        self.modules_services = modules_services
        self.modules_mappings_counts = modules_mappings_counts
        self.modules_mappings_counts_update = modules_mappings_counts_update
        self.modules_mappings_storage = modules_mappings_storage
        self.modules_tag_display = modules_tag_display
        self.modules_files_storage = modules_files_storage
        
        ClientDBModule.ClientDBModule.__init__( self, 'client combined files display mappings cache', cursor )
        
    
    def AddImplications( self, tag_service_id, implication_tag_ids, tag_id, status_hook = None ):
        
        if len( implication_tag_ids ) == 0:
            
            return
            
        
        remaining_implication_tag_ids = set( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, tag_id ) ).difference( implication_tag_ids )
        
        ( current_delta, pending_delta ) = self.GetWithAndWithoutTagsFileCountCombined( tag_service_id, implication_tag_ids, remaining_implication_tag_ids )
        
        if current_delta > 0 or pending_delta > 0:
            
            counts_cache_changes = ( ( tag_id, current_delta, pending_delta ), )
            
            self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def AddMappingsForChained( self, tag_service_id, storage_tag_id, hash_ids ):
        
        ac_current_counts = collections.Counter()
        ac_pending_counts = collections.Counter()
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            display_tag_ids = self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, storage_tag_id )
            
            display_tag_ids_to_implied_by_tag_ids = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, display_tag_ids, tags_are_ideal = True )
            
            file_service_ids_to_hash_ids = self.modules_files_storage.GroupHashIdsByTagCachedFileServiceId( hash_ids, temp_hash_ids_table_name )
            
            for ( display_tag_id, implied_by_tag_ids ) in display_tag_ids_to_implied_by_tag_ids.items():
                
                other_implied_by_tag_ids = set( implied_by_tag_ids )
                other_implied_by_tag_ids.discard( storage_tag_id )
                
                # get the count of pending that are tagged by storage_tag_id but not tagged by any of the other implied_by
                
                num_pending_to_be_rescinded = self.GetWithAndWithoutTagsForFilesFileCount( HC.CONTENT_STATUS_PENDING, tag_service_id, ( storage_tag_id, ), other_implied_by_tag_ids, hash_ids, temp_hash_ids_table_name, file_service_ids_to_hash_ids )
                
                # get the count of current that already have any implication
                
                num_non_addable = self.GetWithAndWithoutTagsForFilesFileCount( HC.CONTENT_STATUS_CURRENT, tag_service_id, implied_by_tag_ids, set(), hash_ids, temp_hash_ids_table_name, file_service_ids_to_hash_ids )
                
                num_addable = len( hash_ids ) - num_non_addable
                
                if num_addable > 0:
                    
                    ac_current_counts[ display_tag_id ] += num_addable
                    
                
                if num_pending_to_be_rescinded > 0:
                    
                    ac_pending_counts[ display_tag_id ] += num_pending_to_be_rescinded
                    
                
            
        
        if len( ac_current_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, current_delta, 0 ) for ( tag_id, current_delta ) in ac_current_counts.items() ]
            
            self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
            
        
        if len( ac_pending_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, 0, pending_delta ) for ( tag_id, pending_delta ) in ac_pending_counts.items() ]
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def DeleteImplications( self, tag_service_id, implication_tag_ids, tag_id, status_hook = None ):
        
        if len( implication_tag_ids ) == 0:
            
            return
            
        
        remaining_implication_tag_ids = set( self.modules_tag_display.GetImpliedBy( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, tag_id ) ).difference( implication_tag_ids )
        
        ( current_delta, pending_delta ) = self.GetWithAndWithoutTagsFileCountCombined( tag_service_id, implication_tag_ids, remaining_implication_tag_ids )
        
        if current_delta > 0 or pending_delta > 0:
            
            counts_cache_changes = ( ( tag_id, current_delta, pending_delta ), )
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def DeleteMappingsForChained( self, tag_service_id, storage_tag_id, hash_ids ):
        
        ac_counts = collections.Counter()
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            display_tag_ids = self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, storage_tag_id )
            
            display_tag_ids_to_implied_by_tag_ids = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, display_tag_ids, tags_are_ideal = True )
            
            file_service_ids_to_hash_ids = self.modules_files_storage.GroupHashIdsByTagCachedFileServiceId( hash_ids, temp_hash_ids_table_name )
            
            for ( display_tag_id, implied_by_tag_ids ) in display_tag_ids_to_implied_by_tag_ids.items():
                
                other_implied_by_tag_ids = set( implied_by_tag_ids )
                other_implied_by_tag_ids.discard( storage_tag_id )
                
                # get the count of current that are tagged by storage_tag_id but not tagged by any of the other implied_by
                
                num_deletable = self.GetWithAndWithoutTagsForFilesFileCount( HC.CONTENT_STATUS_CURRENT, tag_service_id, ( storage_tag_id, ), other_implied_by_tag_ids, hash_ids, temp_hash_ids_table_name, file_service_ids_to_hash_ids )
                
                if num_deletable > 0:
                    
                    ac_counts[ display_tag_id ] += num_deletable
                    
                
            
        
        if len( ac_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, current_delta, 0 ) for ( tag_id, current_delta ) in ac_counts.items() ]
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def Clear( self, tag_service_id, keep_pending = False ):
        
        self.modules_mappings_counts.ClearCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, keep_pending = keep_pending )
        
    
    def Drop( self, tag_service_id ):
        
        self.modules_mappings_counts.DropTables( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id )
        
    
    def Generate( self, tag_service_id, status_hook = None ):
        
        if status_hook is not None:
            
            status_hook( 'copying storage counts' )
            
        
        self.modules_mappings_counts.CreateTables( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, populate_from_storage = True )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def GetWithAndWithoutTagsForFilesFileCount( self, status, tag_service_id, with_these_tag_ids, without_these_tag_ids, hash_ids, hash_ids_table_name, file_service_ids_to_hash_ids ):
        
        # ok, given this selection of files, how many of them on current/pending have any of these tags but not any these, real fast?
        
        count = 0
        
        with self._MakeTemporaryIntegerTable( with_these_tag_ids, 'tag_id' ) as temp_with_these_tag_ids_table_name:
            
            with self._MakeTemporaryIntegerTable( without_these_tag_ids, 'tag_id' ) as temp_without_these_tag_ids_table_name:
                
                for ( file_service_id, batch_of_hash_ids ) in file_service_ids_to_hash_ids.items():
                    
                    if len( batch_of_hash_ids ) == len( hash_ids ):
                        
                        subcount = self.GetWithAndWithoutTagsForFilesFileCountFileService( status, file_service_id, tag_service_id, with_these_tag_ids, temp_with_these_tag_ids_table_name, without_these_tag_ids, temp_without_these_tag_ids_table_name, hash_ids, hash_ids_table_name )
                        
                    else:
                        
                        with self._MakeTemporaryIntegerTable( batch_of_hash_ids, 'hash_id' ) as temp_batch_hash_ids_table_name:
                            
                            subcount = self.GetWithAndWithoutTagsForFilesFileCountFileService( status, file_service_id, tag_service_id, with_these_tag_ids, temp_with_these_tag_ids_table_name, without_these_tag_ids, temp_without_these_tag_ids_table_name, batch_of_hash_ids, temp_batch_hash_ids_table_name )
                            
                        
                    
                    count += subcount
                    
                
            
        
        return count
        
    
    def GetWithAndWithoutTagsForFilesFileCountFileService( self, status, file_service_id, tag_service_id, with_these_tag_ids, with_these_tag_ids_table_name, without_these_tag_ids, without_these_tag_ids_table_name, hash_ids, hash_ids_table_name ):
        
        # ପୁରୁଣା ଲୋକଙ୍କ ଶକ୍ତି ଦ୍ୱାରା, ଏହି କ୍ରସ୍ କାର୍ଯ୍ୟରେ ଯୋଗ ଦିଅନ୍ତୁ |
        
        # ok, given this selection of files, how many of them on current/pending have any of these tags but not any these, real fast?
        
        statuses_to_table_names = self.modules_mappings_storage.GetFastestStorageMappingTableNames( file_service_id, tag_service_id )
        
        ( current_with_tag_ids, current_with_tag_ids_weight, pending_with_tag_ids, pending_with_tag_ids_weight ) = self.modules_mappings_counts.GetCurrentPendingPositiveCountsAndWeights( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, with_these_tag_ids, tag_ids_table_name = with_these_tag_ids_table_name )
        ( current_without_tag_ids, current_without_tag_ids_weight, pending_without_tag_ids, pending_without_tag_ids_weight ) = self.modules_mappings_counts.GetCurrentPendingPositiveCountsAndWeights( ClientTags.TAG_DISPLAY_STORAGE, file_service_id, tag_service_id, without_these_tag_ids, tag_ids_table_name = without_these_tag_ids_table_name )
        
        mappings_table_name = statuses_to_table_names[ status ]
        
        if status == HC.CONTENT_STATUS_CURRENT:
            
            with_tag_ids = current_with_tag_ids
            with_tag_ids_weight = current_with_tag_ids_weight
            without_tag_ids = current_without_tag_ids
            without_tag_ids_weight = current_without_tag_ids_weight
            
        elif status == HC.CONTENT_STATUS_PENDING:
            
            with_tag_ids = pending_with_tag_ids
            with_tag_ids_weight = pending_with_tag_ids_weight
            without_tag_ids = pending_without_tag_ids
            without_tag_ids_weight = pending_without_tag_ids_weight
            
        
        if with_tag_ids_weight == 0:
            
            # nothing there, so nothing to do!
            
            return 0
            
        
        hash_ids_weight = len( hash_ids )
        
        # in order to reduce overhead, we go full meme and do a bunch of different situations
        
        with self._MakeTemporaryIntegerTable( [], 'tag_id' ) as temp_with_tag_ids_table_name:
            
            with self._MakeTemporaryIntegerTable( [], 'tag_id' ) as temp_without_tag_ids_table_name:
                
                if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( hash_ids_weight, with_tag_ids_weight ):
                    
                    select_with_weight = hash_ids_weight
                    
                else:
                    
                    select_with_weight = with_tag_ids_weight
                    
                
                if len( with_tag_ids ) == 1:
                    
                    ( with_tag_id, ) = with_tag_ids
                    
                    if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( hash_ids_weight, with_tag_ids_weight ):
                        
                        # temp files to mappings
                        select_with_hash_ids_on_storage = 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id ) WHERE tag_id = {}'.format( hash_ids_table_name, mappings_table_name, with_tag_id )
                        
                    else:
                        
                        # mappings to temp files
                        select_with_hash_ids_on_storage = 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id ) WHERE tag_id = {}'.format( mappings_table_name, hash_ids_table_name, with_tag_id )
                        
                    
                else:
                    
                    # distinct as with many tags hashes can appear twice (e.g. two siblings on the same file)
                    
                    self._ExecuteMany( 'INSERT INTO {} ( tag_id ) VALUES ( ? );'.format( temp_with_tag_ids_table_name ), ( ( with_tag_id, ) for with_tag_id in with_tag_ids ) )
                    
                    if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( hash_ids_weight, with_tag_ids_weight ):
                        
                        # temp files to mappings to temp tags
                        select_with_hash_ids_on_storage = 'SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( hash_id ) CROSS JOIN {} USING ( tag_id )'.format( hash_ids_table_name, mappings_table_name, temp_with_tag_ids_table_name )
                        
                    else:
                        
                        # temp tags to mappings to temp files
                        select_with_hash_ids_on_storage = 'SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( tag_id ) CROSS JOIN {} USING ( hash_id )'.format( temp_with_tag_ids_table_name, mappings_table_name, hash_ids_table_name )
                        
                    
                
                if without_tag_ids_weight == 0:
                    
                    table_phrase = '({})'.format( select_with_hash_ids_on_storage )
                    
                else:
                    
                    # WARNING, WARNING: Big Brain Query, potentially great/awful
                    # note that in the 'clever/file join' situation, the number of total mappings is many, but we are dealing with a few files
                    # in that situation, we want to say 'for every file in this list, check if it exists'. this is the 'NOT EXISTS' thing
                    # when we have lots of files, tag lookups are generally faster, so easier just to search by that tag in one go and check each file against that subquery result. this is 'hash_id NOT IN'
                    
                    if len( without_tag_ids ) == 1:
                        
                        ( without_tag_id, ) = without_tag_ids
                        
                        if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( select_with_weight, without_tag_ids_weight ):
                            
                            # (files to) mappings
                            hash_id_not_in_storage_without = 'NOT EXISTS ( SELECT 1 FROM {} as mt2 WHERE mt1.hash_id = mt2.hash_id and tag_id = {} )'.format( mappings_table_name, without_tag_id )
                            
                        else:
                            
                            hash_id_not_in_storage_without = 'hash_id NOT IN ( SELECT hash_id FROM {} WHERE tag_id = {} )'.format( mappings_table_name, without_tag_id )
                            
                        
                    else:
                        
                        self._ExecuteMany( 'INSERT INTO {} ( tag_id ) VALUES ( ? );'.format( temp_without_tag_ids_table_name ), ( ( without_tag_id, ) for without_tag_id in without_tag_ids ) )
                        
                        if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( select_with_weight, without_tag_ids_weight ):
                            
                            # (files to) mappings to temp tags
                            hash_id_not_in_storage_without = 'NOT EXISTS ( SELECT 1 FROM {} as mt2 CROSS JOIN {} USING ( tag_id ) WHERE mt1.hash_id = mt2.hash_id )'.format( mappings_table_name, temp_without_tag_ids_table_name )
                            
                        else:
                            
                            # temp tags to mappings to temp files
                            hash_id_not_in_storage_without = 'hash_id NOT IN ( SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( tag_id ) )'.format( temp_without_tag_ids_table_name, mappings_table_name )
                            
                        
                    
                    table_phrase = '({}) as mt1 WHERE {}'.format( select_with_hash_ids_on_storage, hash_id_not_in_storage_without )
                    
                
                query = 'SELECT COUNT ( * ) FROM {};'.format( table_phrase )
                
                ( count, ) = self._Execute( query ).fetchone()
                
                return count
                
            
        
    
    def GetWithAndWithoutTagsFileCountCombined( self, tag_service_id, with_these_tag_ids, without_these_tag_ids ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
        
        statuses_to_count = collections.Counter()
        
        ( current_with_tag_ids, current_with_tag_ids_weight, pending_with_tag_ids, pending_with_tag_ids_weight ) = self.modules_mappings_counts.GetCurrentPendingPositiveCountsAndWeights( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, with_these_tag_ids )
        ( current_without_tag_ids, current_without_tag_ids_weight, pending_without_tag_ids, pending_without_tag_ids_weight ) = self.modules_mappings_counts.GetCurrentPendingPositiveCountsAndWeights( ClientTags.TAG_DISPLAY_STORAGE, self.modules_services.combined_file_service_id, tag_service_id, without_these_tag_ids )
        
        jobs = []
        
        jobs.append( ( HC.CONTENT_STATUS_CURRENT, current_mappings_table_name, current_with_tag_ids, current_with_tag_ids_weight, current_without_tag_ids, current_without_tag_ids_weight ) )
        jobs.append( ( HC.CONTENT_STATUS_PENDING, pending_mappings_table_name, pending_with_tag_ids, pending_with_tag_ids_weight, pending_without_tag_ids, pending_without_tag_ids_weight ) )
        
        for ( status, mappings_table_name, with_tag_ids, with_tag_ids_weight, without_tag_ids, without_tag_ids_weight ) in jobs:
            
            if with_tag_ids_weight == 0:
                
                # nothing there, so nothing to do!
                
                continue
                
            
            if without_tag_ids_weight == 0 and len( with_tag_ids ) == 1:
                
                statuses_to_count[ status ] = with_tag_ids_weight
                
                continue
                
            
            if len( with_tag_ids ) > 1:
                
                # ok, when we are using with_tag_ids_weight as a 'this is how long the hash_ids list is' in later weight calculations, it does not account for overlap
                # in real world data, bad siblings tend to have a count of anywhere from 8% to 600% of the ideal (30-50% is common), but the overlap is significant, often 98%
                # so just to fudge this number a bit better, let's multiply it by 0.75
                
                with_tag_ids_weight = int( with_tag_ids_weight * 0.75 )
                
            
            # ultimately here, we are doing "delete all display mappings with hash_ids that have a storage mapping for a removee tag and no storage mappings for a keep tag
            # in order to reduce overhead, we go full meme and do a bunch of different situations
            
            with self._MakeTemporaryIntegerTable( [], 'tag_id' ) as temp_with_tag_ids_table_name:
                
                with self._MakeTemporaryIntegerTable( [], 'tag_id' ) as temp_without_tag_ids_table_name:
                    
                    if len( with_tag_ids ) == 1:
                        
                        ( with_tag_id, ) = with_tag_ids
                        
                        select_with_hash_ids_on_storage = 'SELECT hash_id FROM {} WHERE tag_id = {}'.format( mappings_table_name, with_tag_id )
                        
                    else:
                        
                        self._ExecuteMany( 'INSERT INTO {} ( tag_id ) VALUES ( ? );'.format( temp_with_tag_ids_table_name ), ( ( with_tag_id, ) for with_tag_id in with_tag_ids ) )
                        
                        # temp tags to mappings
                        select_with_hash_ids_on_storage = 'SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( tag_id )'.format( temp_with_tag_ids_table_name, mappings_table_name )
                        
                    
                    if without_tag_ids_weight == 0:
                        
                        table_phrase = '({})'.format( select_with_hash_ids_on_storage )
                        
                    else:
                        
                        # WARNING, WARNING: Big Brain Query, potentially great/awful
                        # note that in the 'clever/file join' situation, the number of total mappings is many, but we are deleting a few
                        # we want to precisely scan the status of the potential hashes to delete, not scan through them all to see what not to do
                        # therefore, we do NOT EXISTS, which just scans the parts, rather than NOT IN, which does the whole query and then checks against all results
                        
                        if len( without_tag_ids ) == 1:
                            
                            ( without_tag_id, ) = without_tag_ids
                            
                            if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( with_tag_ids_weight, without_tag_ids_weight ):
                                
                                hash_id_not_in_storage_without = 'NOT EXISTS ( SELECT 1 FROM {} as mt2 WHERE mt1.hash_id = mt2.hash_id and tag_id = {} )'.format( mappings_table_name, without_tag_id )
                                
                            else:
                                
                                hash_id_not_in_storage_without = 'hash_id NOT IN ( SELECT hash_id FROM {} WHERE tag_id = {} )'.format( mappings_table_name, without_tag_id )
                                
                            
                        else:
                            
                            self._ExecuteMany( 'INSERT INTO {} ( tag_id ) VALUES ( ? );'.format( temp_without_tag_ids_table_name ), ( ( without_tag_id, ) for without_tag_id in without_tag_ids ) )
                            
                            if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( with_tag_ids_weight, without_tag_ids_weight ):
                                
                                # (files to) mappings to temp tags
                                hash_id_not_in_storage_without = 'NOT EXISTS ( SELECT 1 FROM {} as mt2 CROSS JOIN {} USING ( tag_id ) WHERE mt1.hash_id = mt2.hash_id )'.format( mappings_table_name, temp_without_tag_ids_table_name )
                                
                            else:
                                
                                # temp tags to mappings
                                hash_id_not_in_storage_without = 'hash_id NOT IN ( SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( tag_id ) )'.format( temp_without_tag_ids_table_name, mappings_table_name )
                                
                            
                        
                        table_phrase = '({}) as mt1 WHERE {}'.format( select_with_hash_ids_on_storage, hash_id_not_in_storage_without )
                        
                    
                    query = 'SELECT COUNT ( * ) FROM {};'.format( table_phrase )
                    
                    ( count, ) = self._Execute( query ).fetchone()
                    
                    statuses_to_count[ status ] = count
                    
                
            
        
        current_count = statuses_to_count[ HC.CONTENT_STATUS_CURRENT ]
        pending_count = statuses_to_count[ HC.CONTENT_STATUS_PENDING ]
        
        return ( current_count, pending_count )
        
    
    def PendMappingsForChained( self, tag_service_id, storage_tag_id, hash_ids ):
        
        ac_counts = collections.Counter()
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            display_tag_ids = self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, storage_tag_id )
            
            display_tag_ids_to_implied_by_tag_ids = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, display_tag_ids, tags_are_ideal = True )
            
            file_service_ids_to_hash_ids = self.modules_files_storage.GroupHashIdsByTagCachedFileServiceId( hash_ids, temp_hash_ids_table_name )
            
            for ( display_tag_id, implied_by_tag_ids ) in display_tag_ids_to_implied_by_tag_ids.items():
                
                # get the count of current that are tagged by any of the implications
                
                num_non_pendable = self.GetWithAndWithoutTagsForFilesFileCount( HC.CONTENT_STATUS_PENDING, tag_service_id, implied_by_tag_ids, set(), hash_ids, temp_hash_ids_table_name, file_service_ids_to_hash_ids )
                
                num_pendable = len( hash_ids ) - num_non_pendable
                
                if num_pendable > 0:
                    
                    ac_counts[ display_tag_id ] += num_pendable
                    
                
            
        
        if len( ac_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, 0, pending_delta ) for ( tag_id, pending_delta ) in ac_counts.items() ]
            
            self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
            
        
    
    def RegeneratePending( self, tag_service_id, status_hook = None ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
        
        if status_hook is not None:
            
            message = 'clearing old combined display data'
            
            status_hook( message )
            
        
        all_pending_storage_tag_ids = self._STS( self._Execute( 'SELECT DISTINCT tag_id FROM {};'.format( pending_mappings_table_name ) ) )
        
        storage_tag_ids_to_display_tag_ids = self.modules_tag_display.GetTagsToImplies( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, all_pending_storage_tag_ids )
        
        all_pending_display_tag_ids = set( itertools.chain.from_iterable( storage_tag_ids_to_display_tag_ids.values() ) )
        
        del all_pending_storage_tag_ids
        del storage_tag_ids_to_display_tag_ids
        
        self.modules_mappings_counts.ClearCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, keep_current = True )
        
        all_pending_display_tag_ids_to_implied_by_storage_tag_ids = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, all_pending_display_tag_ids, tags_are_ideal = True )
        
        counts_cache_changes = []
        
        num_to_do = len( all_pending_display_tag_ids_to_implied_by_storage_tag_ids )
        
        for ( i, ( display_tag_id, storage_tag_ids ) ) in enumerate( all_pending_display_tag_ids_to_implied_by_storage_tag_ids.items() ):
            
            if i % 100 == 0 and status_hook is not None:
                
                message = 'regenerating pending tags {}'.format( HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) )
                
                status_hook( message )
                
            
            # we'll do these counts from raw tables, not 'get withandwithout count' cleverness, since this is a recovery function and other caches may be dodgy atm
            
            if len( storage_tag_ids ) == 1:
                
                ( storage_tag_id, ) = storage_tag_ids
                
                ( pending_delta, ) = self._Execute( 'SELECT COUNT( DISTINCT hash_id ) FROM {} WHERE tag_id = ?;'.format( pending_mappings_table_name ), ( storage_tag_id, ) ).fetchone()
                
            else:
                
                with self._MakeTemporaryIntegerTable( storage_tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
                    
                    # temp tags to mappings merged
                    ( pending_delta, ) = self._Execute( 'SELECT COUNT( DISTINCT hash_id ) FROM {} CROSS JOIN {} USING ( tag_id );'.format( temp_tag_ids_table_name, pending_mappings_table_name ) ).fetchone()
                    
                
            
            counts_cache_changes.append( ( display_tag_id, 0, pending_delta ) )
            
        
        self.modules_mappings_counts_update.AddCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
        
    
    def RescindPendingMappingsForChained( self, tag_service_id, storage_tag_id, hash_ids ):
        
        ac_counts = collections.Counter()
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            display_tag_ids = self.modules_tag_display.GetImplies( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, storage_tag_id )
            
            display_tag_ids_to_implied_by_tag_ids = self.modules_tag_display.GetTagsToImpliedBy( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, display_tag_ids, tags_are_ideal = True )
            
            file_service_ids_to_hash_ids = self.modules_files_storage.GroupHashIdsByTagCachedFileServiceId( hash_ids, temp_hash_ids_table_name )
            
            for ( display_tag_id, implied_by_tag_ids ) in display_tag_ids_to_implied_by_tag_ids.items():
                
                other_implied_by_tag_ids = set( implied_by_tag_ids )
                other_implied_by_tag_ids.discard( storage_tag_id )
                
                # get the count of current that are tagged by storage_tag_id but not tagged by any of the other implications
                
                num_rescindable = self.GetWithAndWithoutTagsForFilesFileCount( HC.CONTENT_STATUS_PENDING, tag_service_id, ( storage_tag_id, ), other_implied_by_tag_ids, hash_ids, temp_hash_ids_table_name, file_service_ids_to_hash_ids )
                
                if num_rescindable > 0:
                    
                    ac_counts[ display_tag_id ] += num_rescindable
                    
                
            
        
        if len( ac_counts ) > 0:
            
            counts_cache_changes = [ ( tag_id, 0, pending_delta ) for ( tag_id, pending_delta ) in ac_counts.items() ]
            
            self.modules_mappings_counts_update.ReduceCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, self.modules_services.combined_file_service_id, tag_service_id, counts_cache_changes )
            
        
