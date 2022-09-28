import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBTagSearch

class ClientDBFilesSearch( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_tags: ClientDBMaster.ClientDBMasterTags,
        modules_files_storage: ClientDBFilesStorage,
        modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts,
        modules_tag_search: ClientDBTagSearch.ClientDBTagSearch
    ):
        
        self.modules_services = modules_services
        self.modules_tags = modules_tags
        self.modules_files_storage = modules_files_storage
        self.modules_mappings_counts = modules_mappings_counts
        self.modules_tag_search = modules_tag_search
        
        # expand this with more modules to cover all search situations and eventually gethashidsfromquery
        # might also want to split into submodules if we overload things and it makes sense
        
        ClientDBModule.ClientDBModule.__init__( self, 'client file search', cursor )
        
    
    def GetHashIdsAndNonZeroTagCounts( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearch.TagContext, hash_ids, namespace_wildcard = '*', job_key = None ):
        
        if namespace_wildcard == '*':
            
            namespace_ids = []
            
        else:
            
            namespace_ids = self.modules_tag_search.GetNamespaceIdsFromWildcard( namespace_wildcard )
            
        
        with self._MakeTemporaryIntegerTable( namespace_ids, 'namespace_id' ) as temp_namespace_ids_table_name:
            
            ( file_service_keys, file_location_is_cross_referenced ) = location_context.GetCoveringCurrentFileServiceKeys()
            
            mapping_and_tag_table_names = set()
            
            for file_service_key in file_service_keys:
                
                mapping_and_tag_table_names.update( self.modules_tag_search.GetMappingAndTagTables( tag_display_type, file_service_key, tag_context ) )
                
            
            # reason why I (JOIN each table) rather than (join the UNION) is based on previous hell with having query planner figure out a "( a UNION b UNION c ) NATURAL JOIN stuff" situation
            # although the following sometimes makes certifiable 2KB ( 6 UNION * 4-table ) queries, it actually works fast
            
            # OK, a new problem is mass UNION leads to terrible cancelability because the first row cannot be fetched until the first n - 1 union queries are done
            # I tried some gubbins to try to do a pseudo table-union rather than query union and do 'get files->distinct tag count for this union of tables, and fetch hash_ids first on the union', but did not have luck
            
            # so NOW we are just going to do it in bits of files mate. this also reduces memory use from the distinct-making UNION with large numbers of hash_ids
            
            results = []
            
            BLOCK_SIZE = max( 64, int( len( hash_ids ) ** 0.5 ) ) # go for square root for now
            
            for group_of_hash_ids in HydrusData.SplitIteratorIntoChunks( hash_ids, BLOCK_SIZE ):
                
                with self._MakeTemporaryIntegerTable( group_of_hash_ids, 'hash_id' ) as hash_ids_table_name:
                    
                    if namespace_wildcard == '*':
                        
                        # temp hashes to mappings
                        select_statements = [ 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id )'.format( hash_ids_table_name, mappings_table_name ) for ( mappings_table_name, tags_table_name ) in mapping_and_tag_table_names ]
                        
                    else:
                        
                        # temp hashes to mappings to tags to namespaces
                        select_statements = [ 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id ) CROSS JOIN {} USING ( tag_id ) CROSS JOIN {} USING ( namespace_id )'.format( hash_ids_table_name, mappings_table_name, tags_table_name, temp_namespace_ids_table_name ) for ( mappings_table_name, tags_table_name ) in mapping_and_tag_table_names ]
                        
                    
                    unions = '( {} )'.format( ' UNION '.join( select_statements ) )
                    
                    query = 'SELECT hash_id, COUNT( tag_id ) FROM {} GROUP BY hash_id;'.format( unions )
                    
                    cursor = self._Execute( query )
                    
                    cancelled_hook = None
                    
                    if job_key is not None:
                        
                        cancelled_hook = job_key.IsCancelled
                        
                    
                    loop_of_results = HydrusDB.ReadFromCancellableCursor( cursor, 64, cancelled_hook = cancelled_hook )
                    
                    if job_key is not None and job_key.IsCancelled():
                        
                        return results
                        
                    
                    results.extend( loop_of_results )
                    
                
            
            return results
            
        
    
    def GetHashIdsFromNamespaceIdsSubtagIds( self, tag_display_type: int, file_service_key, tag_context: ClientSearch.TagContext, namespace_ids, subtag_ids, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        tag_ids = self.modules_tag_search.GetTagIdsFromNamespaceIdsSubtagIds( file_service_id, tag_service_id, namespace_ids, subtag_ids, job_key = job_key )
        
        return self.GetHashIdsFromTagIds( tag_display_type, file_service_key, tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
        
    
    def GetHashIdsFromNamespaceIdsSubtagIdsTables( self, tag_display_type: int, file_service_key, tag_context: ClientSearch.TagContext, namespace_ids_table_name, subtag_ids_table_name, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        tag_ids = self.modules_tag_search.GetTagIdsFromNamespaceIdsSubtagIdsTables( file_service_id, tag_service_id, namespace_ids_table_name, subtag_ids_table_name, job_key = job_key )
        
        return self.GetHashIdsFromTagIds( tag_display_type, file_service_key, tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
        
    
    def GetHashIdsFromSubtagIds( self, tag_display_type: int, file_service_key, tag_context: ClientSearch.TagContext, subtag_ids, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        tag_ids = self.modules_tag_search.GetTagIdsFromSubtagIds( file_service_id, tag_service_id, subtag_ids, job_key = job_key )
        
        return self.GetHashIdsFromTagIds( tag_display_type, file_service_key, tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
        
    
    def GetHashIdsFromSubtagIdsTable( self, tag_display_type: int, file_service_key, tag_context: ClientSearch.TagContext, subtag_ids_table_name, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        tag_ids = self.modules_tag_search.GetTagIdsFromSubtagIdsTable( file_service_id, tag_service_id, subtag_ids_table_name, job_key = job_key )
        
        return self.GetHashIdsFromTagIds( tag_display_type, file_service_key, tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
        
    
    def GetHashIdsFromTag( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearch.TagContext, tag, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        ( file_service_keys, file_location_is_cross_referenced ) = location_context.GetCoveringCurrentFileServiceKeys()
        
        if not file_location_is_cross_referenced and hash_ids_table_name is not None:
            
            file_location_is_cross_referenced = True
            
        
        if not self.modules_tags.TagExists( tag ):
            
            return set()
            
        
        results = set()
        
        if tag_context.service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            search_tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = ( self.modules_services.GetServiceId( tag_context.service_key ), )
            
        
        service_ids_to_service_keys = self.modules_services.GetServiceIdsToServiceKeys()
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        subtag_id = self.modules_tags.GetSubtagId( subtag )
        tag_id = self.modules_tags.GetTagId( tag )
        
        for search_tag_service_id in search_tag_service_ids:
            
            search_tag_service_key = service_ids_to_service_keys[ search_tag_service_id ]
            
            search_tag_context = ClientSearch.TagContext( service_key = search_tag_service_key, include_current_tags = tag_context.include_current_tags, include_pending_tags = tag_context.include_pending_tags, display_service_key = search_tag_service_key )
            
            ideal_tag_id = self.modules_tag_search.modules_tag_siblings.GetIdealTagId( tag_display_type, search_tag_service_id, tag_id )
            
            for file_service_key in file_service_keys:
                
                # just as a legacy note, this is where we used to do the "'samus aran' gets 'character:samus aran'" code. now, that stuff works through wildcards if user explicitly enters '*:samus aran'
                
                tag_ids = ( ideal_tag_id, )
                
                some_results = self.GetHashIdsFromTagIds( tag_display_type, file_service_key, search_tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
                
                if len( results ) == 0:
                    
                    results = some_results
                    
                else:
                    
                    results.update( some_results )
                    
                
            
        
        if not file_location_is_cross_referenced:
            
            results = self.modules_files_storage.FilterHashIds( location_context, results )
            
        
        return results
        
    
    def GetHashIdsFromTagIds( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearch.TagContext, tag_ids: typing.Collection[ int ], hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        do_hash_table_join = False
        
        if hash_ids_table_name is not None and hash_ids is not None:
            
            tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
            file_service_id = self.modules_services.GetServiceId( file_service_key )
            
            estimated_count = self.modules_mappings_counts.GetAutocompleteCountEstimate( tag_display_type, tag_service_id, file_service_id, tag_ids, tag_context.include_current_tags, tag_context.include_pending_tags )
            
            if ClientDBMappingsStorage.DoingAFileJoinTagSearchIsFaster( len( hash_ids ), estimated_count ):
                
                do_hash_table_join = True
                
            
        
        result_hash_ids = set()
        
        table_names = self.modules_tag_search.GetMappingTables( tag_display_type, file_service_key, tag_context )
        
        cancelled_hook = None
        
        if job_key is not None:
            
            cancelled_hook = job_key.IsCancelled
            
        
        if len( tag_ids ) == 1:
            
            ( tag_id, ) = tag_ids
            
            if do_hash_table_join:
                
                # temp hashes to mappings
                queries = [ 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id ) WHERE tag_id = ?'.format( hash_ids_table_name, table_name ) for table_name in table_names ]
                
            else:
                
                queries = [ 'SELECT hash_id FROM {} WHERE tag_id = ?;'.format( table_name ) for table_name in table_names ]
                
            
            for query in queries:
                
                cursor = self._Execute( query, ( tag_id, ) )
                
                result_hash_ids.update( self._STI( HydrusDB.ReadFromCancellableCursor( cursor, 1024, cancelled_hook ) ) )
                
            
        else:
            
            with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
                
                if do_hash_table_join:
                    
                    # temp hashes to mappings to temp tags
                    # old method, does not do EXISTS efficiently, it makes a list instead and checks that
                    # queries = [ 'SELECT hash_id FROM {} WHERE EXISTS ( SELECT 1 FROM {} CROSS JOIN {} USING ( tag_id ) WHERE {}.hash_id = {}.hash_id );'.format( hash_ids_table_name, table_name, temp_tag_ids_table_name, table_name, hash_ids_table_name ) for table_name in table_names ]
                    # new method, this seems to actually do the correlated scalar subquery, although it does seem to be sqlite voodoo
                    queries = [ 'SELECT hash_id FROM {} WHERE EXISTS ( SELECT 1 FROM {} WHERE {}.hash_id = {}.hash_id AND EXISTS ( SELECT 1 FROM {} WHERE {}.tag_id = {}.tag_id ) );'.format( hash_ids_table_name, table_name, table_name, hash_ids_table_name, temp_tag_ids_table_name, table_name, temp_tag_ids_table_name ) for table_name in table_names ]
                    
                else:
                    
                    # temp tags to mappings
                    queries = [ 'SELECT hash_id FROM {} CROSS JOIN {} USING ( tag_id );'.format( temp_tag_ids_table_name, table_name ) for table_name in table_names ]
                    
                
                for query in queries:
                    
                    cursor = self._Execute( query )
                    
                    result_hash_ids.update( self._STI( HydrusDB.ReadFromCancellableCursor( cursor, 1024, cancelled_hook ) ) )
                    
                
            
        
        return result_hash_ids
        
    
    def GetHashIdsFromWildcardComplexLocation( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearch.TagContext, wildcard, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        ( namespace_wildcard, subtag_wildcard ) = HydrusTags.SplitTag( wildcard )
        
        if subtag_wildcard == '*':
            
            return self.GetHashIdsThatHaveTagsComplexLocation( tag_display_type, location_context, tag_context, namespace_wildcard = namespace_wildcard, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
            
        
        results = set()
        
        ( file_service_keys, file_location_is_cross_referenced ) = location_context.GetCoveringCurrentFileServiceKeys()
        
        if not file_location_is_cross_referenced and hash_ids_table_name is not None:
            
            file_location_is_cross_referenced = True
            
        
        if namespace_wildcard == '*':
            
            possible_namespace_ids = []
            
        else:
            
            possible_namespace_ids = self.modules_tag_search.GetNamespaceIdsFromWildcard( namespace_wildcard )
            
            if len( possible_namespace_ids ) == 0:
                
                return set()
                
            
        
        with self._MakeTemporaryIntegerTable( possible_namespace_ids, 'namespace_id' ) as temp_namespace_ids_table_name:
            
            if namespace_wildcard == '*':
                
                namespace_ids_table_name = None
                
            else:
                
                namespace_ids_table_name = temp_namespace_ids_table_name
                
            
            for file_service_key in file_service_keys:
                
                some_results = self.GetHashIdsFromWildcardSimpleLocation( tag_display_type, file_service_key, tag_context, subtag_wildcard, namespace_ids_table_name = namespace_ids_table_name, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
                
                if len( results ) == 0:
                    
                    results = some_results
                    
                else:
                    
                    results.update( some_results )
                    
                
            
        
        if not file_location_is_cross_referenced:
            
            results = self.modules_files_storage.FilterHashIds( location_context, results )
            
        
        return results
        
    
    def GetHashIdsFromWildcardSimpleLocation( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearch.TagContext, subtag_wildcard, namespace_ids_table_name = None, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        with self._MakeTemporaryIntegerTable( [], 'subtag_id' ) as temp_subtag_ids_table_name:
            
            file_service_id = self.modules_services.GetServiceId( file_service_key )
            tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
            
            self.modules_tag_search.GetSubtagIdsFromWildcardIntoTable( file_service_id, tag_service_id, subtag_wildcard, temp_subtag_ids_table_name, job_key = job_key )
            
            if namespace_ids_table_name is None:
                
                return self.GetHashIdsFromSubtagIdsTable( tag_display_type, file_service_key, tag_context, temp_subtag_ids_table_name, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
                
            else:
                
                return self.GetHashIdsFromNamespaceIdsSubtagIdsTables( tag_display_type, file_service_key, tag_context, namespace_ids_table_name, temp_subtag_ids_table_name, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
                
            
        
    
    def GetHashIdsThatHaveTagAsNumComplexLocation( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearch.TagContext, namespace_wildcard, num, operator, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        if location_context.IsEmpty():
            
            return set()
            
        
        ( file_service_keys, file_location_is_cross_referenced ) = location_context.GetCoveringCurrentFileServiceKeys()
        
        if not file_location_is_cross_referenced and hash_ids_table_name is not None:
            
            file_location_is_cross_referenced = True
            
        
        results = set()
        
        for file_service_key in file_service_keys:
            
            some_results = self.GetHashIdsThatHaveTagAsNumSimpleLocation( tag_display_type, file_service_key, tag_context, namespace_wildcard, num, operator, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
            
            if len( results ) == 0:
                
                results = some_results
                
            else:
                
                results.update( some_results )
                
            
        
        if not file_location_is_cross_referenced:
            
            results = self.modules_files_storage.FilterHashIds( location_context, results )
            
        
        return results
        
    
    def GetHashIdsThatHaveTagAsNumSimpleLocation( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearch.TagContext, namespace_wildcard, num, operator, hash_ids = None, hash_ids_table_name = None, job_key = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        if tag_service_id == self.modules_services.combined_tag_service_id:
            
            search_tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = ( tag_service_id, )
            
        
        possible_subtag_ids = set()
        
        for search_tag_service_id in search_tag_service_ids:
            
            some_possible_subtag_ids = self.modules_tag_search.GetTagAsNumSubtagIds( file_service_id, search_tag_service_id, operator, num )
            
            possible_subtag_ids.update( some_possible_subtag_ids )
            
        
        if namespace_wildcard == '*':
            
            return self.GetHashIdsFromSubtagIds( tag_display_type, file_service_key, tag_context, possible_subtag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
            
        else:
            
            possible_namespace_ids = self.modules_tag_search.GetNamespaceIdsFromWildcard( namespace_wildcard )
            
            return self.GetHashIdsFromNamespaceIdsSubtagIds( tag_display_type, file_service_key, tag_context, possible_namespace_ids, possible_subtag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
            
        
    
    def GetHashIdsThatHaveTagsComplexLocation( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearch.TagContext, namespace_wildcard = '*', hash_ids_table_name = None, job_key = None ):
        
        if location_context.IsEmpty():
            
            return set()
            
        
        if namespace_wildcard == '*':
            
            possible_namespace_ids = []
            
        else:
            
            possible_namespace_ids = self.modules_tag_search.GetNamespaceIdsFromWildcard( namespace_wildcard )
            
            if len( possible_namespace_ids ) == 0:
                
                return set()
                
            
        
        results = set()
        
        with self._MakeTemporaryIntegerTable( possible_namespace_ids, 'namespace_id' ) as temp_namespace_ids_table_name:
            
            if namespace_wildcard == '*':
                
                namespace_ids_table_name = None
                
            else:
                
                namespace_ids_table_name = temp_namespace_ids_table_name
                
            
            ( file_service_keys, file_location_is_cross_referenced ) = location_context.GetCoveringCurrentFileServiceKeys()
            
            if not file_location_is_cross_referenced and hash_ids_table_name is not None:
                
                file_location_is_cross_referenced = True
                
            
            for file_service_key in file_service_keys:
                
                some_results = self.GetHashIdsThatHaveTagsSimpleLocation( tag_display_type, file_service_key, tag_context, namespace_ids_table_name = namespace_ids_table_name, hash_ids_table_name = hash_ids_table_name, job_key = job_key )
                
                if len( results ) == 0:
                    
                    results = some_results
                    
                else:
                    
                    results.update( some_results )
                    
                
            
        
        if not file_location_is_cross_referenced:
            
            results = self.modules_files_storage.FilterHashIds( location_context, results )
            
        
        return results
        
    
    def GetHashIdsThatHaveTagsSimpleLocation( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearch.TagContext, namespace_ids_table_name = None, hash_ids_table_name = None, job_key = None ):
        
        mapping_and_tag_table_names = self.modules_tag_search.GetMappingAndTagTables( tag_display_type, file_service_key, tag_context )
        
        if hash_ids_table_name is None:
            
            if namespace_ids_table_name is None:
                
                # hellmode
                queries = [ 'SELECT DISTINCT hash_id FROM {};'.format( mappings_table_name ) for ( mappings_table_name, tags_table_name ) in mapping_and_tag_table_names ]
                
            else:
                
                # temp namespaces to tags to mappings
                queries = [ 'SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( namespace_id ) CROSS JOIN {} USING ( tag_id );'.format( namespace_ids_table_name, tags_table_name, mappings_table_name ) for ( mappings_table_name, tags_table_name ) in mapping_and_tag_table_names ]
                
            
        else:
            
            if namespace_ids_table_name is None:
                
                queries = [ 'SELECT hash_id FROM {} WHERE EXISTS ( SELECT 1 FROM {} WHERE {}.hash_id = {}.hash_id );'.format( hash_ids_table_name, mappings_table_name, mappings_table_name, hash_ids_table_name ) for ( mappings_table_name, tags_table_name ) in mapping_and_tag_table_names ]
                
            else:
                
                # temp hashes to mappings to tags to temp namespaces
                # this was originally a 'WHERE EXISTS' thing, but doing that on a three way cross join is too complex for that to work well
                # let's hope DISTINCT can save time too
                queries = [ 'SELECT DISTINCT hash_id FROM {} CROSS JOIN {} USING ( hash_id ) CROSS JOIN {} USING ( tag_id ) CROSS JOIN {} USING ( namespace_id );'.format( hash_ids_table_name, mappings_table_name, tags_table_name, namespace_ids_table_name ) for ( mappings_table_name, tags_table_name ) in mapping_and_tag_table_names ]
                
            
        
        cancelled_hook = None
        
        if job_key is not None:
            
            cancelled_hook = job_key.IsCancelled
            
        
        nonzero_tag_hash_ids = set()
        
        for query in queries:
            
            cursor = self._Execute( query )
            
            nonzero_tag_hash_ids.update( self._STI( HydrusDB.ReadFromCancellableCursor( cursor, 10240, cancelled_hook ) ) )
            
            if job_key is not None and job_key.IsCancelled():
                
                return set()
                
            
        
        return nonzero_tag_hash_ids
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
