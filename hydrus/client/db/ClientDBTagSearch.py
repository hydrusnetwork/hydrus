import itertools
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBTagDisplay
from hydrus.client.metadata import ClientTags

# Sqlite can handle -( 2 ** 63 ) -> ( 2 ** 63 ) - 1
MIN_CACHED_INTEGER = - ( 2 ** 63 )
MAX_CACHED_INTEGER = ( 2 ** 63 ) - 1

def CanCacheInteger( num ):
    
    return MIN_CACHED_INTEGER <= num and num <= MAX_CACHED_INTEGER
    
def ConvertWildcardToSQLiteLikeParameter( wildcard ):
    
    like_param = wildcard.replace( '*', '%' )
    
    return like_param
    
def GenerateCombinedFilesIntegerSubtagsTableName( tag_service_id ):
    
    name = 'combined_files_integer_subtags_cache'
    
    integer_subtags_table_name = 'external_caches.{}_{}'.format( name, tag_service_id )
    
    return integer_subtags_table_name
    
def GenerateCombinedFilesSubtagsFTS4TableName( tag_service_id ):
    
    name = 'combined_files_subtags_fts4_cache'
    
    subtags_fts4_table_name = 'external_caches.{}_{}'.format( name, tag_service_id )
    
    return subtags_fts4_table_name
    
def GenerateCombinedFilesSubtagsSearchableMapTableName( tag_service_id ):
    
    name = 'combined_files_subtags_searchable_map_cache'
    
    subtags_searchable_map_table_name = 'external_caches.{}_{}'.format( name, tag_service_id )
    
    return subtags_searchable_map_table_name
    
def GenerateCombinedFilesTagsTableName( tag_service_id ):
    
    name = 'combined_files_tags_cache'
    
    tags_table_name = 'external_caches.{}_{}'.format( name, tag_service_id )
    
    return tags_table_name
    
def GenerateCombinedTagsTagsTableName( file_service_id ):
    
    name = 'combined_tags_tags_cache'
    
    tags_table_name = 'external_caches.{}_{}'.format( name, file_service_id )
    
    return tags_table_name
    
def GenerateSpecificIntegerSubtagsTableName( file_service_id, tag_service_id ):
    
    name = 'specific_integer_subtags_cache'
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    integer_subtags_table_name = 'external_caches.{}_{}'.format( name, suffix )
    
    return integer_subtags_table_name
    
def GenerateSpecificSubtagsFTS4TableName( file_service_id, tag_service_id ):
    
    name = 'specific_subtags_fts4_cache'
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    subtags_fts4_table_name = 'external_caches.{}_{}'.format( name, suffix )
    
    return subtags_fts4_table_name
    
def GenerateSpecificSubtagsSearchableMapTableName( file_service_id, tag_service_id ):
    
    name = 'specific_subtags_searchable_map_cache'
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    subtags_searchable_map_table_name = 'external_caches.{}_{}'.format( name, suffix )
    
    return subtags_searchable_map_table_name
    
def GenerateSpecificTagsTableName( file_service_id, tag_service_id ):
    
    name = 'specific_tags_cache'
    
    suffix = '{}_{}'.format( file_service_id, tag_service_id )
    
    tags_table_name = 'external_caches.{}_{}'.format( name, suffix )
    
    return tags_table_name
    
def WildcardHasFTS4SearchableCharacters( wildcard: str ):
    
    # fts4 says it can do alphanumeric or unicode with a value >= 128
    
    for c in wildcard:
        
        if c.isalnum() or ord( c ) >= 128 or c == '*':
            
            return True
            
        
    
    return False
    
class ClientDBTagSearch( ClientDBModule.ClientDBModule ):
    
    CAN_REPOPULATE_ALL_MISSING_DATA = True
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_tags: ClientDBMaster.ClientDBMasterTags, modules_tag_display: ClientDBTagDisplay.ClientDBTagDisplay ):
        
        self.modules_services = modules_services
        self.modules_tags = modules_tags
        self.modules_tag_display = modules_tag_display
        
        ClientDBModule.ClientDBModule.__init__( self, 'client tag search', cursor )
        
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
                    
                    searchable_subtag = ClientSearch.ConvertSubtagToSearchable( subtag )
                    
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
        chained_tag_ids = self.modules_tag_display.GetChainsMembers( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, tag_ids )
        
        tag_ids = tag_ids.difference( chained_tag_ids )
        
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
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( tags_table_name ) )
        
        subtags_fts4_table_name = self.GetSubtagsFTS4TableName( file_service_id, tag_service_id )
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( subtags_fts4_table_name ) )
        
        subtags_searchable_map_table_name = self.GetSubtagsSearchableMapTableName( file_service_id, tag_service_id )
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( subtags_searchable_map_table_name ) )
        
        integer_subtags_table_name = self.GetIntegerSubtagsTableName( file_service_id, tag_service_id )
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( integer_subtags_table_name ) )
        
    
    def FilterExistingTagIds( self, file_service_id, tag_service_id, tag_ids_table_name ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        
        return self._STS( self._Execute( 'SELECT tag_id FROM {} CROSS JOIN {} USING ( tag_id );'.format( tag_ids_table_name, tags_table_name ) ) )
        
    
    def Generate( self, file_service_id, tag_service_id ):
        
        table_generation_dict = self._GetServiceTableGenerationDictSingle( file_service_id, tag_service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._Execute( create_query_without_name.format( table_name ) )
            
        
        index_generation_dict = self._GetServiceIndexGenerationDictSingle( file_service_id, tag_service_id )
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
    def GetIntegerSubtagsTableName( self, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            integer_subtags_table_name = GenerateCombinedFilesIntegerSubtagsTableName( tag_service_id )
            
        else:
            
            if self.modules_services.FileServiceIsCoveredByAllLocalFiles( file_service_id ):
                
                file_service_id = self.modules_services.combined_local_file_service_id
                
            
            integer_subtags_table_name = GenerateSpecificIntegerSubtagsTableName( file_service_id, tag_service_id )
            
        
        return integer_subtags_table_name
        
    
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
        
    
    def GetSubtagIdsFromWildcard( self, file_service_id: int, tag_service_id: int, subtag_wildcard, job_key = None ):
        
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
                    cursor = self._Execute( 'SELECT docid FROM {};'.format( subtags_fts4_table_name ) )
                    
                elif ClientSearch.IsComplexWildcard( subtag_wildcard ) or not wildcard_has_fts4_searchable_characters:
                    
                    # FTS4 does not support complex wildcards, so instead we'll search our raw subtags
                    # however, since we want to search 'searchable' text, we use the 'searchable subtags map' to cross between real and searchable
                    
                    like_param = ConvertWildcardToSQLiteLikeParameter( subtag_wildcard )
                    
                    if subtag_wildcard.startswith( '*' ) or not wildcard_has_fts4_searchable_characters:
                        
                        # this is a SCAN, but there we go
                        # a potential optimisation here, in future, is to store fts4 of subtags reversed, then for '*amus', we can just search that reverse cache for 'suma*'
                        # and this would only double the size of the fts4 cache, the largest cache in the whole db! a steal!
                        # it also would not fix '*amu*', but with some cleverness could speed up '*amus ar*'
                        
                        query = 'SELECT docid FROM {} WHERE subtag LIKE ?;'.format( subtags_fts4_table_name )
                        
                        cursor = self._Execute( query, ( like_param, ) )
                        
                    else:
                        
                        # we have an optimisation here--rather than searching all subtags for bl*ah, let's search all the bl* subtags for bl*ah!
                        
                        prefix_fts4_wildcard = subtag_wildcard.split( '*' )[0]
                        
                        prefix_fts4_wildcard_param = '"{}*"'.format( prefix_fts4_wildcard )
                        
                        query = 'SELECT docid FROM {} WHERE subtag MATCH ? AND subtag LIKE ?;'.format( subtags_fts4_table_name )
                        
                        cursor = self._Execute( query, ( prefix_fts4_wildcard_param, like_param ) )
                        
                    
                else:
                    
                    # we want the " " wrapping our search text to keep whitespace words connected and in order
                    # "samus ar*" should not match "around samus"
                    
                    # simple 'sam*' style subtag, so we can search fts4 no prob
                    
                    subtags_fts4_param = '"{}"'.format( subtag_wildcard )
                    
                    cursor = self._Execute( 'SELECT docid FROM {} WHERE subtag MATCH ?;'.format( subtags_fts4_table_name ), ( subtags_fts4_param, ) )
                    
                
                cancelled_hook = None
                
                if job_key is not None:
                    
                    cancelled_hook = job_key.IsCancelled
                    
                
                loop_of_subtag_ids = self._STL( HydrusDB.ReadFromCancellableCursor( cursor, 1024, cancelled_hook = cancelled_hook ) )
                
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
                    
                
            
            if job_key is not None and job_key.IsCancelled():
                
                return set()
                
            
            result_subtag_ids.update( loop_of_subtag_ids )
            
        
        return result_subtag_ids
        
    
    def GetSubtagIdsFromWildcardIntoTable( self, file_service_id: int, tag_service_id: int, subtag_wildcard, subtag_id_table_name, job_key = None ):
        
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
                    cursor = self._Execute( 'SELECT docid FROM {};'.format( subtags_fts4_table_name ) )
                    
                elif ClientSearch.IsComplexWildcard( subtag_wildcard ) or not wildcard_has_fts4_searchable_characters:
                    
                    # FTS4 does not support complex wildcards, so instead we'll search our raw subtags
                    # however, since we want to search 'searchable' text, we use the 'searchable subtags map' to cross between real and searchable
                    
                    like_param = ConvertWildcardToSQLiteLikeParameter( subtag_wildcard )
                    
                    if subtag_wildcard.startswith( '*' ) or not wildcard_has_fts4_searchable_characters:
                        
                        # this is a SCAN, but there we go
                        # a potential optimisation here, in future, is to store fts4 of subtags reversed, then for '*amus', we can just search that reverse cache for 'suma*'
                        # and this would only double the size of the fts4 cache, the largest cache in the whole db! a steal!
                        # it also would not fix '*amu*', but with some cleverness could speed up '*amus ar*'
                        
                        query = 'SELECT docid FROM {} WHERE subtag LIKE ?;'.format( subtags_fts4_table_name )
                        
                        cursor = self._Execute( query, ( like_param, ) )
                        
                    else:
                        
                        # we have an optimisation here--rather than searching all subtags for bl*ah, let's search all the bl* subtags for bl*ah!
                        
                        prefix_fts4_wildcard = subtag_wildcard.split( '*' )[0]
                        
                        prefix_fts4_wildcard_param = '"{}*"'.format( prefix_fts4_wildcard )
                        
                        query = 'SELECT docid FROM {} WHERE subtag MATCH ? AND subtag LIKE ?;'.format( subtags_fts4_table_name )
                        
                        cursor = self._Execute( query, ( prefix_fts4_wildcard_param, like_param ) )
                        
                    
                else:
                    
                    # we want the " " wrapping our search text to keep whitespace words connected and in order
                    # "samus ar*" should not match "around samus"
                    
                    # simple 'sam*' style subtag, so we can search fts4 no prob
                    
                    subtags_fts4_param = '"{}"'.format( subtag_wildcard )
                    
                    cursor = self._Execute( 'SELECT docid FROM {} WHERE subtag MATCH ?;'.format( subtags_fts4_table_name ), ( subtags_fts4_param, ) )
                    
                
                cancelled_hook = None
                
                if job_key is not None:
                    
                    cancelled_hook = job_key.IsCancelled
                    
                
                loop_of_subtag_id_tuples = HydrusDB.ReadFromCancellableCursor( cursor, 1024, cancelled_hook = cancelled_hook )
                
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
                    
                
            
            if job_key is not None and job_key.IsCancelled():
                
                self._Execute( 'DELETE FROM {};'.format( subtag_id_table_name ) )
                
                return
                
            
        
    
    def GetSubtagsFTS4TableName( self, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            subtags_fts4_table_name = GenerateCombinedFilesSubtagsFTS4TableName( tag_service_id )
            
        else:
            
            if self.modules_services.FileServiceIsCoveredByAllLocalFiles( file_service_id ):
                
                file_service_id = self.modules_services.combined_local_file_service_id
                
            
            subtags_fts4_table_name = GenerateSpecificSubtagsFTS4TableName( file_service_id, tag_service_id )
            
        
        return subtags_fts4_table_name
        
    
    def GetSubtagsSearchableMapTableName( self, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            subtags_searchable_map_table_name = GenerateCombinedFilesSubtagsSearchableMapTableName( tag_service_id )
            
        else:
            
            if self.modules_services.FileServiceIsCoveredByAllLocalFiles( file_service_id ):
                
                file_service_id = self.modules_services.combined_local_file_service_id
                
            
            subtags_searchable_map_table_name = GenerateSpecificSubtagsSearchableMapTableName( file_service_id, tag_service_id )
            
        
        return subtags_searchable_map_table_name
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if HC.CONTENT_TYPE_TAG:
            
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
        
    
    def GetTagsTableName( self, file_service_id, tag_service_id ):
        
        if file_service_id == self.modules_services.combined_file_service_id:
            
            tags_table_name = GenerateCombinedFilesTagsTableName( tag_service_id )
            
        else:
            
            if self.modules_services.FileServiceIsCoveredByAllLocalFiles( file_service_id ):
                
                file_service_id = self.modules_services.combined_local_file_service_id
                
            
            tags_table_name = GenerateSpecificTagsTableName( file_service_id, tag_service_id )
            
        
        return tags_table_name
        
    
    def HasTag( self, file_service_id, tag_service_id, tag_id ):
        
        tags_table_name = self.GetTagsTableName( file_service_id, tag_service_id )
        
        result = self._Execute( 'SELECT 1 FROM {} WHERE tag_id = ?;'.format( tags_table_name ), ( tag_id, ) ).fetchone()
        
        return result is not None
        
    
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
                
                searchable_subtag = ClientSearch.ConvertSubtagToSearchable( subtag )
                
                if searchable_subtag != subtag:
                    
                    searchable_subtag_id = self.modules_tags.GetSubtagId( searchable_subtag )
                    
                    self._Execute( 'INSERT OR IGNORE INTO {} ( subtag_id, searchable_subtag_id ) VALUES ( ?, ? );'.format( subtags_searchable_map_table_name ), ( subtag_id, searchable_subtag_id ) )
                    
                
            
            message = HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do )
            
            HG.client_controller.frame_splash_status.SetSubtext( message )
            
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
            
            searchable_subtag = ClientSearch.ConvertSubtagToSearchable( subtag )
            
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
            
            HydrusData.ShowText( 'Repopulated {} missing subtags for {}_{}.'.format( HydrusData.ToHumanInt( len( missing_subtag_ids ) ), file_service_id, tag_service_id ) )
            
        
    
