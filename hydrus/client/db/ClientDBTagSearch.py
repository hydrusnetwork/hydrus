import collections.abc
import sqlite3
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBTagDisplay
from hydrus.client.db import ClientDBTagSiblings
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchAutocomplete
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

# Sqlite can handle -( 2 ** 63 ) -> ( 2 ** 63 ) - 1
MIN_CACHED_INTEGER = - ( 2 ** 63 )
MAX_CACHED_INTEGER = ( 2 ** 63 ) - 1

def CanCacheInteger( num ):
    
    return MIN_CACHED_INTEGER <= num <= MAX_CACHED_INTEGER
    

def ConvertWildcardToSQLiteLikeParameter( wildcard ):
    
    like_param = wildcard.replace( '*', '%' )
    
    return like_param
    

COMBINED_INTEGER_SUBTAGS_PREFIX = 'combined_files_integer_subtags_cache_'
COMBINED_SUBTAGS_FTS4_PREFIX = 'combined_files_subtags_fts4_cache_'
COMBINED_SUBTAGS_SEARCHABLE_MAP_PREFIX = 'combined_files_subtags_searchable_map_cache_'
COMBINED_TAGS_PREFIX = 'combined_files_tags_cache_'

SPECIFIC_INTEGER_SUBTAGS_PREFIX = 'specific_integer_subtags_cache_'
SPECIFIC_SUBTAGS_FTS4_PREFIX = 'specific_subtags_fts4_cache_'
SPECIFIC_SUBTAGS_SEARCHABLE_MAP_PREFIX = 'specific_subtags_searchable_map_cache_'
SPECIFIC_TAGS_PREFIX = 'specific_tags_cache_'

def GenerateCombinedFilesIntegerSubtagsTableName( tag_service_id ):
    
    suffix = tag_service_id
    
    integer_subtags_table_name = f'external_caches.{COMBINED_INTEGER_SUBTAGS_PREFIX}{suffix}'
    
    return integer_subtags_table_name
    

def GenerateCombinedFilesSubtagsFTS4TableName( tag_service_id ):
    
    suffix = tag_service_id
    
    subtags_fts4_table_name = f'external_caches.{COMBINED_SUBTAGS_FTS4_PREFIX}{suffix}'
    
    return subtags_fts4_table_name
    

def GenerateCombinedFilesSubtagsSearchableMapTableName( tag_service_id ):
    
    suffix = tag_service_id
    
    subtags_searchable_map_table_name = f'external_caches.{COMBINED_SUBTAGS_SEARCHABLE_MAP_PREFIX}{suffix}'
    
    return subtags_searchable_map_table_name
    

def GenerateCombinedFilesTagsTableName( tag_service_id ):
    
    suffix = tag_service_id
    
    tags_table_name = f'external_caches.{COMBINED_TAGS_PREFIX}{suffix}'
    
    return tags_table_name
    

def GenerateSpecificIntegerSubtagsTableName( file_service_id, tag_service_id ):
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    integer_subtags_table_name = f'external_caches.{SPECIFIC_INTEGER_SUBTAGS_PREFIX}{suffix}'
    
    return integer_subtags_table_name
    

def GenerateSpecificSubtagsFTS4TableName( file_service_id, tag_service_id ):
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    subtags_fts4_table_name = f'external_caches.{SPECIFIC_SUBTAGS_FTS4_PREFIX}{suffix}'
    
    return subtags_fts4_table_name
    

def GenerateSpecificSubtagsSearchableMapTableName( file_service_id, tag_service_id ):
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    subtags_searchable_map_table_name = f'external_caches.{SPECIFIC_SUBTAGS_SEARCHABLE_MAP_PREFIX}{suffix}'
    
    return subtags_searchable_map_table_name
    

def GenerateSpecificTagsTableName( file_service_id, tag_service_id ):
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    tags_table_name = f'external_caches.{SPECIFIC_TAGS_PREFIX}{suffix}'
    
    return tags_table_name
    

def WildcardHasFTS4SearchableCharacters( wildcard: str ):
    
    # fts4 says it can do alphanumeric or unicode with a value >= 128
    
    for c in wildcard:
        
        if c == '*':
            
            continue
            
        
        if c.isalnum() or ord( c ) >= 128:
            
            return True
            
        
    
    return False
    

class ClientDBTagSearch( ClientDBModule.ClientDBModule ):
    
    CAN_REPOPULATE_ALL_MISSING_DATA = True
    
    def __init__( self, cursor: sqlite3.Cursor, modules_db_maintenance: ClientDBMaintenance.ClientDBMaintenance, modules_services: ClientDBServices.ClientDBMasterServices, modules_tags: ClientDBMaster.ClientDBMasterTags, modules_tag_display: ClientDBTagDisplay.ClientDBTagDisplay, modules_tag_siblings: ClientDBTagSiblings.ClientDBTagSiblings, modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts ):
        
        self.modules_db_maintenance = modules_db_maintenance
        self.modules_services = modules_services
        self.modules_tags = modules_tags
        self.modules_tag_display = modules_tag_display
        self.modules_tag_siblings = modules_tag_siblings
        self.modules_mappings_counts = modules_mappings_counts
        
        super().__init__( 'client tag search', cursor )
        
        self._missing_tag_search_service_pairs = set()
        
    
    def _GetServiceIndexGenerationDictSingle( self, file_service_id, tag_service_id ) -> dict:
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
        subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, tag_service_id )
        integer_subtags_table_name = self.GetIntegerSubtagsTableName( file_service_id, tag_service_id )
        
        index_generation_dict = {}
        
        index_generation_dict[ tags_table_name ] = [
            ( [ 'namespace_id', 'subtag_id' ], True, 465 ),
            ( [ 'subtag_id' ], False, 465 )
        ]
        
        index_generation_dict[ subtags_searchable_map_table_name ] = [
            ( [ 'searchable_subtag_id' ], False, 465 )
        ]
        
        index_generation_dict[ integer_subtags_table_name ] = [
            ( [ 'integer_subtag' ], False, 465 )
        ]
        
        return index_generation_dict
        
    
    def _GetServiceIndexGenerationDict( self, service_id ) -> dict:
        
        tag_service_id = service_id
        
        index_generation_dict = {}
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ) )
        file_service_ids.append( self.modules_services.combined_file_service_id )
        
        for file_service_id in file_service_ids:
            
            single_index_dict = self._GetServiceIndexGenerationDictSingle( file_service_id, tag_service_id )
            
            index_generation_dict.update( single_index_dict )
            
        
        return index_generation_dict
        
    
    def _GetServiceTableGenerationDictSingle( self, file_service_id, tag_service_id ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
        subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, tag_service_id )
        integer_subtags_table_name = self.GetIntegerSubtagsTableName( file_service_id, tag_service_id )
        
        table_dict = {
            tags_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER PRIMARY KEY, namespace_id INTEGER, subtag_id INTEGER );', 465 ),
            subtags_fts4_table_name : ( 'CREATE VIRTUAL TABLE IF NOT EXISTS {} USING fts4( subtag );', 465 ),
            subtags_searchable_map_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( subtag_id INTEGER PRIMARY KEY, searchable_subtag_id INTEGER );', 465 ),
            integer_subtags_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( subtag_id INTEGER PRIMARY KEY, integer_subtag INTEGER );', 465 )
        }
        
        return table_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        tag_service_id = service_id
        
        table_dict = {}
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ) )
        file_service_ids.append( self.modules_services.combined_file_service_id )
        
        for file_service_id in file_service_ids:
            
            single_table_dict = self._GetServiceTableGenerationDictSingle( file_service_id, tag_service_id )
            
            table_dict.update( single_table_dict )
            
        
        return table_dict
        
    
    def _GetServiceTablePrefixes( self ):
        
        # do not add the fts4 guys to this, since that already uses a bunch of different suffixes for its own virtual sub-tables and it all gets wrapped up false-positive in our tests!
        return {
            COMBINED_TAGS_PREFIX,
            COMBINED_SUBTAGS_SEARCHABLE_MAP_PREFIX,
            COMBINED_INTEGER_SUBTAGS_PREFIX,
            SPECIFIC_TAGS_PREFIX,
            SPECIFIC_SUBTAGS_SEARCHABLE_MAP_PREFIX,
            SPECIFIC_INTEGER_SUBTAGS_PREFIX
        }
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        
    
    def _RepairRepopulateTables( self, table_names, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES ) )
        file_service_ids.append( self.modules_services.combined_file_service_id )
        
        tag_service_ids = list( self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES ) )
        
        for tag_service_id in tag_service_ids:
            
            for file_service_id in file_service_ids:
                
                table_dict_for_this = self._GetServiceTableGenerationDictSingle( file_service_id, tag_service_id )
                
                table_names_for_this = set( table_dict_for_this.keys() )
                
                if not table_names_for_this.isdisjoint( table_names ):
                    
                    self._missing_tag_search_service_pairs.add( ( file_service_id, tag_service_id ) )
                    
                
            
        
    
    def AddTags( self, file_service_id, tag_service_id, tag_ids ):
        
        if len( tag_ids ) == 0:
            
            return
            
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        
        actually_new_tag_ids = set()
        
        for tag_id in tag_ids:
            
            self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id, namespace_id, subtag_id ) SELECT tag_id, namespace_id, subtag_id FROM tags WHERE tag_id = ?;'.format( tags_table_name ), ( tag_id, ) )
            
            if self._GetRowCount() > 0:
                
                actually_new_tag_ids.add( tag_id )
                
            
        
        if len( actually_new_tag_ids ) > 0:
            
            if file_service_id == self.modules_services.combined_file_service_id:
                
                self._Execute( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( len( actually_new_tag_ids ), tag_service_id, HC.SERVICE_INFO_NUM_TAGS ) )
                
            
            with self._MakeTemporaryIntegerTable( actually_new_tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
                
                # temp tags to fast tag definitions to subtags
                subtag_ids_and_subtags = self._Execute( 'SELECT subtag_id, subtag FROM {} CROSS JOIN {} USING ( tag_id ) CROSS JOIN subtags USING ( subtag_id );'.format( temp_tag_ids_table_name, tags_table_name ) ).fetchall()
                
                subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
                subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, tag_service_id )
                integer_subtags_table_name = self.GetIntegerSubtagsTableName( file_service_id, tag_service_id )
                
                for ( subtag_id, subtag ) in subtag_ids_and_subtags:
                    
                    searchable_subtag = ClientSearchTagContext.ConvertSubtagToSearchable( subtag )
                    
                    if searchable_subtag != subtag:
                        
                        searchable_subtag_id = self.modules_tags.GetSubtagId( searchable_subtag )
                        
                        self._Execute( 'INSERT OR IGNORE INTO {} ( subtag_id, searchable_subtag_id ) VALUES ( ?, ? );'.format( subtags_searchable_map_table_name ), ( subtag_id, searchable_subtag_id ) )
                        
                    
                    #
                    
                    self._Execute( 'INSERT OR IGNORE INTO {} ( docid, subtag ) VALUES ( ?, ? );'.format( subtags_fts4_table_name ), ( subtag_id, searchable_subtag ) )
                    
                    if subtag.isdecimal():
                        
                        try:
                            
                            integer_subtag = int( subtag )
                            
                            if CanCacheInteger( integer_subtag ):
                                
                                self._Execute( 'INSERT OR IGNORE INTO {} ( subtag_id, integer_subtag ) VALUES ( ?, ? );'.format( integer_subtags_table_name ), ( subtag_id, integer_subtag ) )
                                
                            
                        except ValueError:
                            
                            pass
                            
                        
                    
                
            
        
    
    def DeleteTags( self, file_service_id, tag_service_id, tag_ids ):
        
        if len( tag_ids ) == 0:
            
            return
            
        
        if not isinstance( tag_ids, set ):
            
            tag_ids = set( tag_ids )
            
        
        #
        
        # we always include all chained guys regardless of count
        chained_tag_ids = self.modules_tag_display.FilterChained( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, tag_ids )
        
        tag_ids = tag_ids.difference( chained_tag_ids )
        
        if len( tag_ids ) == 0:
            
            return
            
        
        #
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
        subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, tag_service_id )
        integer_subtags_table_name = self.GetIntegerSubtagsTableName( file_service_id, tag_service_id )
        
        with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
            
            # temp tag ids to tag definitions
            subtag_ids = self._STS( self._Execute( 'SELECT subtag_id FROM {} CROSS JOIN {} USING ( tag_id );'.format( temp_tag_ids_table_name, tags_table_name ) ) )
            
            #
            
            self._ExecuteMany( 'DELETE FROM {} WHERE tag_id = ?;'.format( tags_table_name ), ( ( tag_id, ) for tag_id in tag_ids ) )
            
            num_deleted = self._GetRowCount()
            
            if num_deleted > 0:
                
                if file_service_id == self.modules_services.combined_file_service_id:
                    
                    self._Execute( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', ( num_deleted, tag_service_id, HC.SERVICE_INFO_NUM_TAGS ) )
                    
                
                #
                
                # subtags may exist under other namespaces, so exclude those that do
                
                with self._MakeTemporaryIntegerTable( subtag_ids, 'subtag_id' ) as temp_subtag_ids_table_name:
                    
                    still_existing_subtag_ids = self._STS( self._Execute( 'SELECT subtag_id FROM {} CROSS JOIN {} USING ( subtag_id );'.format( temp_subtag_ids_table_name, tags_table_name ) ) )
                    
                
                deletee_subtag_ids = subtag_ids.difference( still_existing_subtag_ids )
                
                self._ExecuteMany( 'DELETE FROM {} WHERE docid = ?;'.format( subtags_fts4_table_name ), ( ( subtag_id, ) for subtag_id in deletee_subtag_ids ) )
                self._ExecuteMany( 'DELETE FROM {} WHERE subtag_id = ?;'.format( subtags_searchable_map_table_name ), ( ( subtag_id, ) for subtag_id in deletee_subtag_ids ) )
                self._ExecuteMany( 'DELETE FROM {} WHERE subtag_id = ?;'.format( integer_subtags_table_name ), ( ( subtag_id, ) for subtag_id in deletee_subtag_ids ) )
                
            
        
    
    def Drop( self, file_service_id, tag_service_id ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        
        self.modules_db_maintenance.DeferredDropTable( tags_table_name )
        
        subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
        
        self.modules_db_maintenance.DeferredDropTable( subtags_fts4_table_name )
        
        subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, tag_service_id )
        
        self.modules_db_maintenance.DeferredDropTable( subtags_searchable_map_table_name )
        
        integer_subtags_table_name = self.GetIntegerSubtagsTableName( file_service_id, tag_service_id )
        
        self.modules_db_maintenance.DeferredDropTable( integer_subtags_table_name )
        
    
    def FilterExistingTagIds( self, file_service_id, tag_service_id, tag_ids_table_name ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        
        return self._STS( self._Execute( 'SELECT tag_id FROM {} CROSS JOIN {} USING ( tag_id );'.format( tag_ids_table_name, tags_table_name ) ) )
        
    
    def Generate( self, file_service_id, tag_service_id ):
        
        table_generation_dict = self._GetServiceTableGenerationDictSingle( file_service_id, tag_service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._CreateTable( create_query_without_name, table_name )
            
        
        index_generation_dict = self._GetServiceIndexGenerationDictSingle( file_service_id, tag_service_id )
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
    def GetAllTagIds( self, leaf: ClientDBServices.FileSearchContextLeaf, job_status = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        query = '{};'.format( self.GetQueryPhraseForTagIds( leaf.file_service_id, leaf.tag_service_id ) )
        
        tag_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
        
        return tag_ids
        
    
    def GetAutocompletePredicates(
        self,
        tag_display_type: int,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        search_text: str = '',
        exact_match = False,
        search_namespaces_into_full_tags = False,
        zero_count_ok = False,
        job_status = None
    ):
        
        # TODO: So I think I should interleave this, perhaps with the SearchLeaf object, or just as GetHashIdsFromTag now does, for each tag service. don't throw 'all known tags' down to lower methods
        # _Then_, you do the GeneratePredicatesFromTagIdsAndCounts for each tag service in turn (don't worry, it is quick since servces won't share tags much), and then you can do some clever sibling counting
        # For instance, if we search for A on a domain where one tag service has A->B, we return the B results. Well, let's increment the A (x) count according to that, based on each service!
        # and then obviously a nice big merge at the end
        
        if HG.autocomplete_delay_mode and not exact_match:
            
            time_to_stop = HydrusTime.GetNowFloat() + 3.0
            
            while not HydrusTime.TimeHasPassedFloat( time_to_stop ):
                
                time.sleep( 0.1 )
                
                if job_status is not None and job_status.IsCancelled():
                    
                    return []
                    
                
            
        
        location_context = file_search_context.GetLocationContext()
        tag_context = file_search_context.GetTagContext()
        
        display_tag_service_id = self.modules_services.GetServiceId( tag_context.display_service_key )
        
        if tag_context.IsAllKnownTags() and location_context.IsAllKnownFiles():
            
            return []
            
        
        include_current = tag_context.include_current_tags
        include_pending = tag_context.include_pending_tags
        
        all_predicates = []
        
        file_search_context_branch = self.modules_services.GetFileSearchContextBranch( file_search_context )
        
        for leaf in file_search_context_branch.IterateLeaves():
            
            tag_ids = self.GetAutocompleteTagIds( tag_display_type, leaf, search_text, exact_match, job_status = job_status )
            
            if ':' not in search_text and search_namespaces_into_full_tags and not exact_match:
                
                # 'char' -> 'character:samus aran'
                
                special_search_text = '{}*:*'.format( search_text )
                
                tag_ids.update( self.GetAutocompleteTagIds( tag_display_type, leaf, special_search_text, exact_match, job_status = job_status ) )
                
            
            if job_status is not None and job_status.IsCancelled():
                
                return []
                
            
            domain_is_cross_referenced = leaf.file_service_id != self.modules_services.combined_deleted_file_service_id
            
            for group_of_tag_ids in HydrusLists.SplitIteratorIntoChunks( tag_ids, 1000 ):
                
                if job_status is not None and job_status.IsCancelled():
                    
                    return []
                    
                
                ids_to_count = self.modules_mappings_counts.GetCounts( tag_display_type, leaf.tag_service_id, leaf.file_service_id, group_of_tag_ids, include_current, include_pending, domain_is_cross_referenced = domain_is_cross_referenced, zero_count_ok = zero_count_ok, job_status = job_status )
                
                if len( ids_to_count ) == 0:
                    
                    continue
                    
                
                #
                
                predicates = self.modules_tag_display.GeneratePredicatesFromTagIdsAndCounts( tag_display_type, display_tag_service_id, ids_to_count, job_status = job_status )
                
                all_predicates.extend( predicates )
                
            
            if job_status is not None and job_status.IsCancelled():
                
                return []
                
            
        
        predicates = ClientSearchPredicate.MergePredicates( all_predicates )
        
        return predicates
        
    
    def GetAutocompleteTagIds( self, tag_display_type: int, leaf: ClientDBServices.FileSearchContextLeaf, search_text, exact_match, job_status = None ):
        
        if search_text == '':
            
            return set()
            
        
        ( namespace, half_complete_searchable_subtag ) = HydrusTags.SplitTag( search_text )
        
        if half_complete_searchable_subtag == '':
            
            return set()
            
        
        if exact_match:
            
            if '*' in namespace or '*' in half_complete_searchable_subtag:
                
                return []
                
            
        
        if '*' in namespace:
            
            namespace_ids = self.GetNamespaceIdsFromWildcard( namespace )
            
        else:
            
            if not self.modules_tags.NamespaceExists( namespace ):
                
                return set()
                
            
            namespace_ids = ( self.modules_tags.GetNamespaceId( namespace ), )
            
        
        if half_complete_searchable_subtag == '*':
            
            if namespace == '':
                
                # hellmode 'get all tags' search
                
                tag_ids = self.GetAllTagIds( leaf, job_status = job_status )
                
            else:
                
                tag_ids = self.GetTagIdsFromNamespaceIds( leaf, namespace_ids, job_status = job_status )
                
            
        else:
            
            tag_ids = set()
            
            with self._MakeTemporaryIntegerTable( [], 'subtag_id' ) as temp_subtag_ids_table_name:
                
                self.GetSubtagIdsFromWildcardIntoTable( leaf.file_service_id, leaf.tag_service_id, half_complete_searchable_subtag, temp_subtag_ids_table_name, job_status = job_status )
                
                if namespace == '':
                    
                    loop_of_tag_ids = self.GetTagIdsFromSubtagIdsTable( leaf.file_service_id, leaf.tag_service_id, temp_subtag_ids_table_name, job_status = job_status )
                    
                else:
                    
                    with self._MakeTemporaryIntegerTable( namespace_ids, 'namespace_id' ) as temp_namespace_ids_table_name:
                        
                        loop_of_tag_ids = self.GetTagIdsFromNamespaceIdsSubtagIdsTables( leaf.file_service_id, leaf.tag_service_id, temp_namespace_ids_table_name, temp_subtag_ids_table_name, job_status = job_status )
                        
                    
                
                tag_ids.update( loop_of_tag_ids )
                
            
        
        # now fetch siblings, add to set
        
        if not isinstance( tag_ids, set ):
            
            tag_ids = set( tag_ids )
            
        
        # for now, this thing can fetch an absolute ton of stuff. you type in '1 female', you are getting a lot of tags, often with no count
        # not a very nice simple way to clear the chaff since in smaller cases those related siblings are useful, including those with no count, so no worries
        
        tag_ids_without_siblings = list( tag_ids )
        
        for ( num_done, num_to_do, batch_of_tag_ids ) in HydrusLists.SplitListIntoChunksRich( tag_ids_without_siblings, 10240 ):
            
            with self._MakeTemporaryIntegerTable( batch_of_tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
                
                if job_status is not None and job_status.IsCancelled():
                    
                    return set()
                    
                
                with self._MakeTemporaryIntegerTable( [], 'ideal_tag_id' ) as temp_ideal_tag_ids_table_name:
                    
                    self.modules_tag_siblings.FilterChainedIdealsIntoTable( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, leaf.tag_service_id, temp_tag_ids_table_name, temp_ideal_tag_ids_table_name )
                    
                    with self._MakeTemporaryIntegerTable( [], 'tag_id' ) as temp_chained_tag_ids_table_name:
                        
                        self.modules_tag_siblings.GetChainsMembersFromIdealsTables( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, leaf.tag_service_id, temp_ideal_tag_ids_table_name, temp_chained_tag_ids_table_name )
                        
                        tag_ids.update( self._STI( self._Execute( 'SELECT tag_id FROM {};'.format( temp_chained_tag_ids_table_name ) ) ) )
                        
                    
                
            
        
        return tag_ids
        
    
    def GetIntegerSubtagsTableName( self, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            integer_subtags_table_name = GenerateCombinedFilesIntegerSubtagsTableName( tag_service_id )
            
        else:
            
            if self.modules_services.FileServiceIsCoveredByHydrusLocalFileStorage( file_service_id ):
                
                file_service_id = self.modules_services.hydrus_local_file_storage_service_id
                
            
            integer_subtags_table_name = GenerateSpecificIntegerSubtagsTableName( file_service_id, tag_service_id )
            
        
        return integer_subtags_table_name
        
    
    def GetMappingTables( self, tag_display_type, file_service_key: bytes, tag_context: ClientSearchTagContext.TagContext ):
        
        mapping_and_tag_table_names = self.GetMappingAndTagTables( tag_display_type, file_service_key, tag_context )
        
        mapping_table_names = [ mapping_table_name for ( mapping_table_name, tag_table_name ) in mapping_and_tag_table_names ]
        
        return mapping_table_names
        
    
    def GetMappingAndTagTables( self, tag_display_type, file_service_key: bytes, tag_context: ClientSearchTagContext.TagContext ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_key = tag_context.service_key
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            tag_service_ids = [ self.modules_services.GetServiceId( tag_service_key ) ]
            
        
        current_tables = []
        pending_tables = []
        
        for tag_service_id in tag_service_ids:
            
            tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
            
            if file_service_id == self.modules_services.combined_file_service_id:
                
                # yo this does not support ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL--big tricky problem
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
                
                current_tables.append( ( current_mappings_table_name, tags_table_name ) )
                pending_tables.append( ( pending_mappings_table_name, tags_table_name ) )
                
            else:
                
                if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE:
                    
                    ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
                    
                    current_tables.append( ( cache_current_mappings_table_name, tags_table_name ) )
                    pending_tables.append( ( cache_pending_mappings_table_name, tags_table_name ) )
                    
                elif tag_display_type == ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL:
                    
                    ( cache_current_display_mappings_table_name, cache_pending_display_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
                    
                    current_tables.append( ( cache_current_display_mappings_table_name, tags_table_name ) )
                    pending_tables.append( ( cache_pending_display_mappings_table_name, tags_table_name ) )
                    
                
            
        
        table_names = []
        
        if tag_context.include_current_tags:
            
            table_names.extend( current_tables )
            
        
        if tag_context.include_pending_tags:
            
            table_names.extend( pending_tables )
            
        
        return table_names
        
    
    def GetMissingTagSearchServicePairs( self ):
        
        return self._missing_tag_search_service_pairs
        
    
    def GetNamespaceIdsFromWildcard( self, namespace_wildcard ):
        
        if namespace_wildcard == '*':
            
            return self._STL( self._Execute( 'SELECT namespace_id FROM namespaces;' ) )
            
        elif '*' in namespace_wildcard:
            
            like_param = ConvertWildcardToSQLiteLikeParameter( namespace_wildcard )
            
            return self._STL( self._Execute( 'SELECT namespace_id FROM namespaces WHERE namespace LIKE ?;', ( like_param, ) ) )
            
        else:
            
            if self.modules_tags.NamespaceExists( namespace_wildcard ):
                
                namespace_id = self.modules_tags.GetNamespaceId( namespace_wildcard )
                
                return [ namespace_id ]
                
            else:
                
                return []
                
            
        
    
    def GetQueryPhraseForTagIds( self, file_service_id, tag_service_id ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        
        return 'SELECT tag_id FROM {}'.format( tags_table_name )
        
    
    def GetSubtagIdsFromWildcard( self, file_service_id: int, tag_service_id: int, subtag_wildcard, job_status = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        if tag_service_id == self.modules_services.combined_tag_service_id:
            
            search_tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = ( tag_service_id, )
            
        
        result_subtag_ids = set()
        
        for search_tag_service_id in search_tag_service_ids:
            
            if '*' in subtag_wildcard:
                
                subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, search_tag_service_id )
                
                wildcard_has_fts4_searchable_characters = WildcardHasFTS4SearchableCharacters( subtag_wildcard )
                
                if subtag_wildcard == '*':
                    
                    # hellmode, but shouldn't be called normally
                    query = 'SELECT docid FROM {};'.format( subtags_fts4_table_name )
                    query_args = ()
                    
                elif ClientSearchAutocomplete.IsComplexWildcard( subtag_wildcard ) or not wildcard_has_fts4_searchable_characters:
                    
                    # FTS4 does not support complex wildcards, so instead we'll search our raw subtags
                    # however, since we want to search 'searchable' text, we use the 'searchable subtags map' to cross between real and searchable
                    
                    like_param = ConvertWildcardToSQLiteLikeParameter( subtag_wildcard )
                    
                    if subtag_wildcard.startswith( '*' ) or not wildcard_has_fts4_searchable_characters:
                        
                        # this is a SCAN, but there we go
                        # a potential optimisation here, in future, is to store fts4 of subtags reversed, then for '*amus', we can just search that reverse cache for 'suma*'
                        # and this would only double the size of the fts4 cache, the largest cache in the whole db! a steal!
                        # it also would not fix '*amu*', but with some cleverness could speed up '*amus ar*'
                        
                        query = 'SELECT docid FROM {} WHERE subtag LIKE ?;'.format( subtags_fts4_table_name )
                        query_args = ( like_param, )
                        
                    else:
                        
                        # we have an optimisation here--rather than searching all subtags for bl*ah, let's search all the bl* subtags for bl*ah!
                        
                        prefix_fts4_wildcard = subtag_wildcard.split( '*' )[0]
                        
                        prefix_fts4_wildcard_param = '"{}*"'.format( prefix_fts4_wildcard )
                        
                        query = 'SELECT docid FROM {} WHERE subtag MATCH ? AND subtag LIKE ?;'.format( subtags_fts4_table_name )
                        query_args = ( prefix_fts4_wildcard_param, like_param )
                        
                    
                else:
                    
                    # we want the " " wrapping our search text to keep whitespace words connected and in order
                    # "samus ar*" should not match "around samus"
                    
                    # simple 'sam*' style subtag, so we can search fts4 no prob
                    
                    subtags_fts4_param = '"{}"'.format( subtag_wildcard )
                    
                    query = 'SELECT docid FROM {} WHERE subtag MATCH ?;'.format( subtags_fts4_table_name )
                    query_args = ( subtags_fts4_param, )
                    
                
                loop_of_subtag_ids = self._STL( self._ExecuteCancellable( query, query_args, cancelled_hook ) )
                
            else:
                
                # old notes from before we had searchable subtag map. I deleted that map once, albeit in an older and less efficient form. *don't delete it again, it has use*
                #
                # NOTE: doing a subtag = 'blah' lookup on subtags_fts4 tables is ultra slow, lmao!
                # attempts to match '/a/' to 'a' with clever FTS4 MATCHing (i.e. a MATCH on a*\b, then an '= a') proved not super successful
                # in testing, it was still a bit slow. my guess is it is still iterating through all the nodes for ^a*, the \b just makes it a bit more efficient sometimes
                # in tests '^a\b' was about twice as fast as 'a*', so the \b might not even be helping at all
                # so, I decided to move back to a lean and upgraded searchable subtag map, and here we are
                
                subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, search_tag_service_id )
                
                searchable_subtag = subtag_wildcard
                
                if self.modules_tags.SubtagExists( searchable_subtag ):
                    
                    searchable_subtag_id = self.modules_tags.GetSubtagId( searchable_subtag )
                    
                    loop_of_subtag_ids = self._STS( self._Execute( 'SELECT subtag_id FROM {} WHERE searchable_subtag_id = ?;'.format( subtags_searchable_map_table_name ), ( searchable_subtag_id, ) ) )
                    
                    loop_of_subtag_ids.add( searchable_subtag_id )
                    
                else:
                    
                    loop_of_subtag_ids = set()
                    
                
            
            if job_status is not None and job_status.IsCancelled():
                
                return set()
                
            
            result_subtag_ids.update( loop_of_subtag_ids )
            
        
        return result_subtag_ids
        
    
    def GetSubtagIdsFromWildcardIntoTable( self, file_service_id: int, tag_service_id: int, subtag_wildcard, subtag_id_table_name, job_status = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        if tag_service_id == self.modules_services.combined_tag_service_id:
            
            search_tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = ( tag_service_id, )
            
        
        for search_tag_service_id in search_tag_service_ids:
            
            if '*' in subtag_wildcard:
                
                subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, search_tag_service_id )
                
                wildcard_has_fts4_searchable_characters = WildcardHasFTS4SearchableCharacters( subtag_wildcard )
                
                if subtag_wildcard == '*':
                    
                    # hellmode, but shouldn't be called normally
                    query = self._Execute( 'SELECT docid FROM {};'.format( subtags_fts4_table_name ) )
                    query_args = ()
                    
                elif ClientSearchAutocomplete.IsComplexWildcard( subtag_wildcard ) or not wildcard_has_fts4_searchable_characters:
                    
                    # FTS4 does not support complex wildcards, so instead we'll search our raw subtags
                    # however, since we want to search 'searchable' text, we use the 'searchable subtags map' to cross between real and searchable
                    
                    like_param = ConvertWildcardToSQLiteLikeParameter( subtag_wildcard )
                    
                    if subtag_wildcard.startswith( '*' ) or not wildcard_has_fts4_searchable_characters:
                        
                        # this is a SCAN, but there we go
                        # a potential optimisation here, in future, is to store fts4 of subtags reversed, then for '*amus', we can just search that reverse cache for 'suma*'
                        # and this would only double the size of the fts4 cache, the largest cache in the whole db! a steal!
                        # it also would not fix '*amu*', but with some cleverness could speed up '*amus ar*'
                        
                        query = 'SELECT docid FROM {} WHERE subtag LIKE ?;'.format( subtags_fts4_table_name )
                        query_args = ( like_param, )
                        
                    else:
                        
                        # we have an optimisation here--rather than searching all subtags for bl*ah, let's search all the bl* subtags for bl*ah!
                        
                        prefix_fts4_wildcard = subtag_wildcard.split( '*' )[0]
                        
                        prefix_fts4_wildcard_param = '"{}*"'.format( prefix_fts4_wildcard )
                        
                        query = 'SELECT docid FROM {} WHERE subtag MATCH ? AND subtag LIKE ?;'.format( subtags_fts4_table_name )
                        
                        query_args = ( prefix_fts4_wildcard_param, like_param )
                        
                    
                else:
                    
                    # we want the " " wrapping our search text to keep whitespace words connected and in order
                    # "samus ar*" should not match "around samus"
                    
                    # simple 'sam*' style subtag, so we can search fts4 no prob
                    
                    subtags_fts4_param = '"{}"'.format( subtag_wildcard )
                    
                    query = 'SELECT docid FROM {} WHERE subtag MATCH ?;'.format( subtags_fts4_table_name )
                    query_args = ( subtags_fts4_param, )
                    
                
                loop_of_subtag_id_tuples = self._ExecuteCancellable( query, query_args, cancelled_hook )
                
                self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( subtag_id ) VALUES ( ? );'.format( subtag_id_table_name ), loop_of_subtag_id_tuples )
                
            else:
                
                # old notes from before we had searchable subtag map. I deleted that map once, albeit in an older and less efficient form. *don't delete it again, it has use*
                #
                # NOTE: doing a subtag = 'blah' lookup on subtags_fts4 tables is ultra slow, lmao!
                # attempts to match '/a/' to 'a' with clever FTS4 MATCHing (i.e. a MATCH on a*\b, then an '= a') proved not super successful
                # in testing, it was still a bit slow. my guess is it is still iterating through all the nodes for ^a*, the \b just makes it a bit more efficient sometimes
                # in tests '^a\b' was about twice as fast as 'a*', so the \b might not even be helping at all
                # so, I decided to move back to a lean and upgraded searchable subtag map, and here we are
                
                searchable_subtag = subtag_wildcard
                
                if self.modules_tags.SubtagExists( searchable_subtag ):
                    
                    searchable_subtag_id = self.modules_tags.GetSubtagId( searchable_subtag )
                    
                    self._Execute( 'INSERT OR IGNORE INTO {} ( subtag_id ) VALUES ( ? );'.format( subtag_id_table_name ), ( searchable_subtag_id, ) )
                    
                    subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, search_tag_service_id )
                    
                    self._Execute( 'INSERT OR IGNORE INTO {} ( subtag_id ) SELECT subtag_id FROM {} WHERE searchable_subtag_id = ?;'.format( subtag_id_table_name, subtags_searchable_map_table_name ), ( searchable_subtag_id, ) )
                    
                
            
            if job_status is not None and job_status.IsCancelled():
                
                self._Execute( 'DELETE FROM {};'.format( subtag_id_table_name ) )
                
                return
                
            
        
    
    def GetSubtagsFTS4TableName( self, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            subtags_fts4_table_name = GenerateCombinedFilesSubtagsFTS4TableName( tag_service_id )
            
        else:
            
            if self.modules_services.FileServiceIsCoveredByHydrusLocalFileStorage( file_service_id ):
                
                file_service_id = self.modules_services.hydrus_local_file_storage_service_id
                
            
            subtags_fts4_table_name = GenerateSpecificSubtagsFTS4TableName( file_service_id, tag_service_id )
            
        
        return subtags_fts4_table_name
        
    
    def GetSubtagsSearchableMapTableName( self, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            subtags_searchable_map_table_name = GenerateCombinedFilesSubtagsSearchableMapTableName( tag_service_id )
            
        else:
            
            if self.modules_services.FileServiceIsCoveredByHydrusLocalFileStorage( file_service_id ):
                
                file_service_id = self.modules_services.hydrus_local_file_storage_service_id
                
            
            subtags_searchable_map_table_name = GenerateSpecificSubtagsSearchableMapTableName( file_service_id, tag_service_id )
            
        
        return subtags_searchable_map_table_name
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_TAG:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
            for tag_service_id in tag_service_ids:
                
                table_dict = {}
                
                file_service_ids = list( self.modules_services.GetServiceIds( HC.FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES ) )
                file_service_ids.append( self.modules_services.combined_file_service_id )
                
                for file_service_id in file_service_ids:
                    
                    tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
                    subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
                    
                    tables_and_columns.append( ( tags_table_name, 'tag_id' ) )
                    tables_and_columns.append( ( subtags_fts4_table_name, 'docid' ) )
                    
                
            
        
        return tables_and_columns
        
    
    def GetTagAsNumSubtagIds( self, file_service_id, tag_service_id, operator, num ):
        
        integer_subtags_table_name = self.GetIntegerSubtagsTableName( file_service_id, tag_service_id )
        
        return self._STS( self._Execute( 'SELECT subtag_id FROM {} WHERE integer_subtag {} {};'.format( integer_subtags_table_name, operator, num ) ) )
        
    
    def GetTagCount( self, file_service_id, tag_service_id ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        
        ( count, ) = self._Execute( 'SELECT COUNT( * ) FROM {};'.format( tags_table_name ) ).fetchone()
        
        return count
        
    
    def GetTagIdsFromNamespaceIds( self, leaf: ClientDBServices.FileSearchContextLeaf, namespace_ids: collections.abc.Collection[ int ], job_status = None ):
        
        if len( namespace_ids ) == 0:
            
            return set()
            
        
        final_result_tag_ids = set()
        
        with self._MakeTemporaryIntegerTable( namespace_ids, 'namespace_id' ) as temp_namespace_ids_table_name:
            
            tags_table_name = self.GetTagsTableName( leaf.file_service_id, leaf.tag_service_id )
            
            if len( namespace_ids ) == 1:
                
                ( namespace_id, ) = namespace_ids
                
                query = 'SELECT tag_id FROM {} WHERE namespace_id = ?;'.format( tags_table_name )
                query_args = ( namespace_id, )
                
            else:
                
                # temp namespaces to tags
                query = 'SELECT tag_id FROM {} CROSS JOIN {} USING ( namespace_id );'.format( temp_namespace_ids_table_name, tags_table_name )
                query_args = ()
                
            
            cancelled_hook = None
            
            if job_status is not None:
                
                cancelled_hook = job_status.IsCancelled
                
            
            result_tag_ids = self._STS( self._ExecuteCancellable( query, query_args, cancelled_hook ) )
            
            if job_status is not None:
                
                if job_status.IsCancelled():
                    
                    return set()
                    
                
            
            final_result_tag_ids.update( result_tag_ids )
            
        
        return final_result_tag_ids
        
    
    def GetTagIdsFromNamespaceIdsSubtagIds( self, file_service_id: int, tag_service_id: int, namespace_ids: collections.abc.Collection[ int ], subtag_ids: collections.abc.Collection[ int ], job_status = None ):
        
        if len( namespace_ids ) == 0 or len( subtag_ids ) == 0:
            
            return set()
            
        
        with self._MakeTemporaryIntegerTable( subtag_ids, 'subtag_id' ) as temp_subtag_ids_table_name:
            
            with self._MakeTemporaryIntegerTable( namespace_ids, 'namespace_id' ) as temp_namespace_ids_table_name:
                
                return self.GetTagIdsFromNamespaceIdsSubtagIdsTables( file_service_id, tag_service_id, temp_namespace_ids_table_name, temp_subtag_ids_table_name, job_status = job_status )
                
            
        
    
    def GetTagIdsFromNamespaceIdsSubtagIdsTables( self, file_service_id: int, tag_service_id: int, namespace_ids_table_name: str, subtag_ids_table_name: str, job_status = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        final_result_tag_ids = set()
        
        if tag_service_id == self.modules_services.combined_tag_service_id:
            
            search_tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = ( tag_service_id, )
            
        
        for search_tag_service_id in search_tag_service_ids:
            
            tags_table_name = self.GetTagsTableName( file_service_id, search_tag_service_id )
            
            # temp subtags to tags to temp namespaces
            query = 'SELECT tag_id FROM {} CROSS JOIN {} USING ( subtag_id ) CROSS JOIN {} USING ( namespace_id );'.format( subtag_ids_table_name, tags_table_name, namespace_ids_table_name )
            
            result_tag_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
            
            if job_status is not None:
                
                if job_status.IsCancelled():
                    
                    return set()
                    
                
            
            final_result_tag_ids.update( result_tag_ids )
            
        
        return final_result_tag_ids
        
    
    def GetTagIdsFromSubtagIds( self, file_service_id: int, tag_service_id: int, subtag_ids: collections.abc.Collection[ int ], job_status = None ):
        
        if len( subtag_ids ) == 0:
            
            return set()
            
        
        with self._MakeTemporaryIntegerTable( subtag_ids, 'subtag_id' ) as temp_subtag_ids_table_name:
            
            return self.GetTagIdsFromSubtagIdsTable( file_service_id, tag_service_id, temp_subtag_ids_table_name, job_status = job_status )
            
        
    
    def GetTagIdsFromSubtagIdsTable( self, file_service_id: int, tag_service_id: int, subtag_ids_table_name: str, job_status = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        final_result_tag_ids = set()
        
        if tag_service_id == self.modules_services.combined_tag_service_id:
            
            search_tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = ( tag_service_id, )
            
        
        for search_tag_service_id in search_tag_service_ids:
            
            tags_table_name = self.GetTagsTableName( file_service_id, search_tag_service_id )
            
            # temp subtags to tags
            query = 'SELECT tag_id FROM {} CROSS JOIN {} USING ( subtag_id );'.format( subtag_ids_table_name, tags_table_name )
            
            result_tag_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
            
            if job_status is not None:
                
                if job_status.IsCancelled():
                    
                    return set()
                    
                
            
            final_result_tag_ids.update( result_tag_ids )
            
        
        return final_result_tag_ids
        
    
    def GetTagIdPredicates(
        self,
        tag_display_type: int,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        tag_ids: collections.abc.Collection[ int ],
        zero_count_ok = False,
        job_status = None
    ):
        
        all_predicates = []
        
        tag_context = file_search_context.GetTagContext()
        
        display_tag_service_id = self.modules_services.GetServiceId( tag_context.display_service_key )
        
        include_current = tag_context.include_current_tags
        include_pending = tag_context.include_pending_tags
        
        file_search_context_branch = self.modules_services.GetFileSearchContextBranch( file_search_context )
        
        for leaf in file_search_context_branch.IterateLeaves():
            
            domain_is_cross_referenced = leaf.file_service_id != self.modules_services.combined_deleted_file_service_id
            
            for group_of_tag_ids in HydrusLists.SplitIteratorIntoChunks( tag_ids, 1000 ):
                
                if job_status is not None and job_status.IsCancelled():
                    
                    return []
                    
                
                ids_to_count = self.modules_mappings_counts.GetCounts( tag_display_type, leaf.tag_service_id, leaf.file_service_id, group_of_tag_ids, include_current, include_pending, domain_is_cross_referenced = domain_is_cross_referenced, zero_count_ok = zero_count_ok, job_status = job_status )
                
                if len( ids_to_count ) == 0:
                    
                    continue
                    
                
                #
                
                predicates = self.modules_tag_display.GeneratePredicatesFromTagIdsAndCounts( tag_display_type, display_tag_service_id, ids_to_count, job_status = job_status )
                
                all_predicates.extend( predicates )
                
            
            if job_status is not None and job_status.IsCancelled():
                
                return []
                
            
        
        predicates = ClientSearchPredicate.MergePredicates( all_predicates )
        
        return predicates
        
    
    def GetTagPredicates(
        self,
        tag_display_type: int,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        tags: collections.abc.Collection[ str ],
        zero_count_ok = False,
        job_status = None
    ):
        
        tag_ids = set( self.modules_tags.GetTagIdsToTags( tags = tags ).keys() )
        
        return self.GetTagIdPredicates(
            tag_display_type,
            file_search_context,
            tag_ids,
            zero_count_ok = zero_count_ok,
            job_status = job_status )
        
    
    def GetTagsTableName( self, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            tags_table_name = GenerateCombinedFilesTagsTableName( tag_service_id )
            
        else:
            
            if self.modules_services.FileServiceIsCoveredByHydrusLocalFileStorage( file_service_id ):
                
                file_service_id = self.modules_services.hydrus_local_file_storage_service_id
                
            
            tags_table_name = GenerateSpecificTagsTableName( file_service_id, tag_service_id )
            
        
        return tags_table_name
        
    
    def HasTag( self, file_service_id, tag_service_id, tag_id ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        
        result = self._Execute( 'SELECT 1 FROM {} WHERE tag_id = ?;'.format( tags_table_name ), ( tag_id, ) ).fetchone()
        
        return result is not None
        
    
    def PopulateTableFromTagFilter( self, file_service_id: int, tag_service_id: int, tag_filter: HydrusTags.TagFilter, temp_tag_ids_table_name: str, my_search_includes_deleted_tags: bool ):
        
        if my_search_includes_deleted_tags:
            
            tags_table_name = 'tags' # lol
            
        else:
            
            tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
            
        
        if tag_filter.AllowsEverything():
            
            self._Execute( f'INSERT OR IGNORE INTO {temp_tag_ids_table_name} ( tag_id ) SELECT tag_id FROM {tags_table_name};' )
            
        else:
            
            tag_slices_to_rules = tag_filter.GetTagSlicesToRules()
            
            # KISS: do 'alls', then namespaces, then tags
            
            include_all_unnamespaced = '' not in tag_slices_to_rules or ( '' in tag_slices_to_rules and tag_slices_to_rules[ '' ] == HC.FILTER_WHITELIST )
            
            if include_all_unnamespaced:
                
                self._Execute( f'INSERT OR IGNORE INTO {temp_tag_ids_table_name} ( tag_id ) SELECT tag_id FROM {tags_table_name} WHERE namespace_id = ?;', ( self.modules_tags.null_namespace_id, ) )
                
            
            include_all_namespaced = ':' not in tag_slices_to_rules or ( ':' in tag_slices_to_rules and tag_slices_to_rules[ ':' ] == HC.FILTER_WHITELIST )
            
            if include_all_namespaced:
                
                self._Execute( f'INSERT OR IGNORE INTO {temp_tag_ids_table_name} ( tag_id ) SELECT tag_id FROM {tags_table_name} WHERE namespace_id != ?;', ( self.modules_tags.null_namespace_id, ) )
                
            
            #
            
            for ( tag_slice, rule ) in tag_slices_to_rules.items():
                
                if tag_slice in ( '', ':' ):
                    
                    continue
                    
                
                if HydrusTags.IsNamespaceTagSlice( tag_slice ):
                    
                    namespace = tag_slice[:-1]
                    
                    namespace_id = self.modules_tags.GetNamespaceId( namespace )
                    
                    if rule == HC.FILTER_WHITELIST:
                        
                        self._Execute( f'INSERT OR IGNORE INTO {temp_tag_ids_table_name} ( tag_id ) SELECT tag_id FROM {tags_table_name} WHERE namespace_id = ?;', ( namespace_id, ) )
                        
                    else:
                        
                        self._Execute( f'DELETE FROM {temp_tag_ids_table_name} WHERE tag_id IN ( SELECT tag_id FROM {tags_table_name} WHERE namespace_id = ? );', ( namespace_id, ) )
                        
                    
                
            
            #
            
            tag_ids_to_add = []
            tag_ids_to_delete = []
            
            for ( tag_slice, rule ) in tag_slices_to_rules.items():
                
                if tag_slice in ( '', ':' ):
                    
                    continue
                    
                
                if not HydrusTags.IsNamespaceTagSlice( tag_slice ):
                    
                    tag_id = self.modules_tags.GetTagId( tag_slice )
                    
                    if rule == HC.FILTER_WHITELIST:
                        
                        tag_ids_to_add.append( tag_id )
                        
                    else:
                        
                        tag_ids_to_delete.append( tag_id )
                        
                    
                
            
            if len( tag_ids_to_add ) > 0:
                
                self._ExecuteMany( f'INSERT OR IGNORE INTO {temp_tag_ids_table_name} ( tag_id ) VALUES ( ? );', ( ( tag_id, ) for tag_id in tag_ids_to_add ) )
                
            
            if len( tag_ids_to_delete ) > 0:
                
                self._ExecuteMany( f'DELETE FROM {temp_tag_ids_table_name} WHERE tag_id = ?;', ( ( tag_id, ) for tag_id in tag_ids_to_add ) )
                
            
        
    
    def RegenerateSearchableSubtagMap( self, file_service_id, tag_service_id, status_hook = None ):
        
        subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
        subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, tag_service_id )
        
        self._Execute( 'DELETE FROM {};'.format( subtags_searchable_map_table_name ) )
        
        query = 'SELECT docid FROM {};'.format( subtags_fts4_table_name )
        
        BLOCK_SIZE = 10000
        
        for ( group_of_subtag_ids, num_done, num_to_do ) in HydrusDB.ReadLargeIdQueryInSeparateChunks( self._c, query, BLOCK_SIZE ):
            
            for subtag_id in group_of_subtag_ids:
                
                result = self._Execute( 'SELECT subtag FROM subtags WHERE subtag_id = ?;', ( subtag_id, ) ).fetchone()
                
                if result is None:
                    
                    continue
                    
                
                ( subtag, ) = result
                
                searchable_subtag = ClientSearchTagContext.ConvertSubtagToSearchable( subtag )
                
                if searchable_subtag != subtag:
                    
                    searchable_subtag_id = self.modules_tags.GetSubtagId( searchable_subtag )
                    
                    self._Execute( 'INSERT OR IGNORE INTO {} ( subtag_id, searchable_subtag_id ) VALUES ( ?, ? );'.format( subtags_searchable_map_table_name ), ( subtag_id, searchable_subtag_id ) )
                    
                
            
            message = HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )
            
            CG.client_controller.frame_splash_status.SetSubtext( message )
            
            if status_hook is not None:
                
                status_hook( message )
                
            
        
    
    def RepopulateMissingSubtags( self, file_service_id, tag_service_id ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
        subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, tag_service_id )
        integer_subtags_table_name = self.GetIntegerSubtagsTableName( file_service_id, tag_service_id )
        
        missing_subtag_ids = self._STS( self._Execute( 'SELECT subtag_id FROM {} EXCEPT SELECT docid FROM {};'.format( tags_table_name, subtags_fts4_table_name ) ) )
        
        for subtag_id in missing_subtag_ids:
            
            result = self._Execute( 'SELECT subtag FROM subtags WHERE subtag_id = ?;', ( subtag_id, ) ).fetchone()
            
            if result is None:
                
                continue
                
            
            ( subtag, ) = result
            
            searchable_subtag = ClientSearchTagContext.ConvertSubtagToSearchable( subtag )
            
            if searchable_subtag != subtag:
                
                searchable_subtag_id = self.modules_tags.GetSubtagId( searchable_subtag )
                
                self._Execute( 'INSERT OR IGNORE INTO {} ( subtag_id, searchable_subtag_id ) VALUES ( ?, ? );'.format( subtags_searchable_map_table_name ), ( subtag_id, searchable_subtag_id ) )
                
            
            #
            
            self._Execute( 'INSERT OR IGNORE INTO {} ( docid, subtag ) VALUES ( ?, ? );'.format( subtags_fts4_table_name ), ( subtag_id, searchable_subtag ) )
            
            if subtag.isdecimal():
                
                try:
                    
                    integer_subtag = int( subtag )
                    
                    if CanCacheInteger( integer_subtag ):
                        
                        self._Execute( 'INSERT OR IGNORE INTO {} ( subtag_id, integer_subtag ) VALUES ( ?, ? );'.format( integer_subtags_table_name ), ( subtag_id, integer_subtag ) )
                        
                    
                except ValueError:
                    
                    pass
                    
                
            
        
        if len( missing_subtag_ids ) > 0:
            
            HydrusData.ShowText( 'Repopulated {} missing subtags for {}_{}.'.format( HydrusNumbers.ToHumanInt( len( missing_subtag_ids ) ), file_service_id, tag_service_id ) )
            
        
    
