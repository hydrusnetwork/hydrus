import collections.abc
import random
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesDuplicatesStorage
from hydrus.client.db import ClientDBFilesInbox
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBFilesTimestamps
from hydrus.client.db import ClientDBFilesViewingStats
from hydrus.client.db import ClientDBMappingsCounts
from hydrus.client.db import ClientDBMappingsStorage
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBNotesMap
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.db import ClientDBTagSearch
from hydrus.client.db import ClientDBTagSiblings
from hydrus.client.db import ClientDBURLMap
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

SHOWN_UNINITIALISED_SEARCH_ERROR = False

def intersection_update_qhi( query_hash_ids: set[ int ] | None, some_hash_ids: collections.abc.Collection[ int ], force_create_new_set = False ) -> set[ int ]:
    
    if query_hash_ids is None:
        
        if not isinstance( some_hash_ids, set ) or force_create_new_set:
            
            some_hash_ids = set( some_hash_ids )
            
        
        return some_hash_ids
        
    else:
        
        query_hash_ids.intersection_update( some_hash_ids )
        
        return query_hash_ids
        
    

class SearchState( object ):
    
    def __init__(
        self,
        done_or_predicates: bool,
        done_files_info_predicates,
        have_cross_referenced_file_locations: bool,
        there_are_tags_to_search: bool,
        there_are_simple_files_info_preds_to_search_for: bool,
        done_tricky_incdec_ratings: bool
    ):
        
        self.done_or_predicates = done_or_predicates
        self.done_files_info_predicates = done_files_info_predicates
        self.have_cross_referenced_file_locations = have_cross_referenced_file_locations
        self.there_are_tags_to_search = there_are_tags_to_search
        self.there_are_simple_files_info_preds_to_search_for = there_are_simple_files_info_preds_to_search_for
        self.done_tricky_incdec_ratings = done_tricky_incdec_ratings
        
    
    def DoOrPredsInFirstRound( self ):
        
        # OR round one--if nothing else will be fast, let's prep query_hash_ids now
        return not self.done_or_predicates and not ( self.there_are_tags_to_search or self.there_are_simple_files_info_preds_to_search_for )
        
    
    def DoOrPredsInSecondRound( self ):
        
        # OR round two--if file preds will not be fast, let's step in to reduce the file domain search space
        return not self.done_or_predicates and not self.there_are_simple_files_info_preds_to_search_for
        
    
    def NotifyDoneOrPreds( self ):
        
        self.done_or_predicates = True
        self.have_cross_referenced_file_locations = True
        
    

def GetFilesInfoPredicates( system_predicates: ClientSearchFileSearchContext.FileSystemPredicates ):
    
    simple_preds = system_predicates.GetSimpleInfo()
    
    files_info_predicates = []
    
    if 'min_size' in simple_preds:
        
        files_info_predicates.append( 'size > ' + str( simple_preds[ 'min_size' ] ) )
        
    if 'size' in simple_preds:
        
        files_info_predicates.append( 'size = ' + str( simple_preds[ 'size' ] ) )
        
    if 'not_size' in simple_preds:
        
        files_info_predicates.append( 'size != ' + str( simple_preds[ 'not_size' ] ) )
        
    if 'max_size' in simple_preds:
        
        files_info_predicates.append( 'size < ' + str( simple_preds[ 'max_size' ] ) )
        
    
    if system_predicates.HasAllowedFiletypes():
        
        # Note, I worked on this way longer than I needed to, vacillating on how to structure this forced data properly and rewriting things four times
        # NOT EXISTS is a blessing, do not try to screw around too much!
        
        mimes = system_predicates.GetAllowedFiletypes()
        
        if len( mimes ) == 1:
            
            ( mime, ) = mimes
            
            files_info_predicates.append( f'( ( mime = {mime} AND NOT EXISTS ( SELECT 1 FROM files_info_forced_filetypes WHERE hash_id = h1 AND forced_mime != {mime} ) ) OR EXISTS ( SELECT 1 FROM files_info_forced_filetypes WHERE hash_id = h1 AND forced_mime = {mime} ) )' )
            
        else:
            
            mimes_splayed = HydrusLists.SplayListForDB( mimes )
            
            files_info_predicates.append( f'( ( mime IN {mimes_splayed} AND NOT EXISTS ( SELECT 1 FROM files_info_forced_filetypes WHERE hash_id = h1 AND forced_mime NOT IN {mimes_splayed} ) ) OR EXISTS ( SELECT 1 FROM files_info_forced_filetypes WHERE hash_id = h1 AND mime IN {mimes_splayed} ) )' )
            
        
    
    if 'has_forced_filetype' in simple_preds:
        
        has_forced_filetype = simple_preds[ 'has_forced_filetype' ]
        
        if has_forced_filetype:
            
            files_info_predicates.append( 'EXISTS ( SELECT 1 FROM files_info_forced_filetypes WHERE hash_id = h1 )' )
            
        else:
            
            files_info_predicates.append( 'NOT EXISTS ( SELECT 1 FROM files_info_forced_filetypes WHERE hash_id = h1 )' )
            
        
    
    if 'has_audio' in simple_preds:
        
        has_audio = simple_preds[ 'has_audio' ]
        
        files_info_predicates.append( 'has_audio = {}'.format( int( has_audio ) ) )
        
    
    if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH in simple_preds:
        
        number_tests: list[ ClientNumberTest.NumberTest ] = simple_preds[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH ]
        
        for number_test in number_tests:
            
            files_info_predicates.extend( number_test.GetSQLitePredicates( 'width' ) )
            
        
    
    if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT in simple_preds:
        
        number_tests: list[ ClientNumberTest.NumberTest ] = simple_preds[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT ]
        
        for number_test in number_tests:
            
            files_info_predicates.extend( number_test.GetSQLitePredicates( 'height' ) )
            
        
    
    if 'min_num_pixels' in simple_preds:
        
        files_info_predicates.append( 'width * height > ' + str( simple_preds[ 'min_num_pixels' ] ) )
        
    if 'num_pixels' in simple_preds:
        
        files_info_predicates.append( 'width * height = ' + str( simple_preds[ 'num_pixels' ] ) )
        
    if 'not_num_pixels' in simple_preds:
        
        files_info_predicates.append( 'width * height != ' + str( simple_preds[ 'not_num_pixels' ] ) )
        
    if 'max_num_pixels' in simple_preds:
        
        files_info_predicates.append( 'width * height < ' + str( simple_preds[ 'max_num_pixels' ] ) )
        
    
    if 'min_ratio' in simple_preds:
        
        ( ratio_width, ratio_height ) = simple_preds[ 'min_ratio' ]
        
        files_info_predicates.append( '( width * 1.0 ) / height > ' + str( float( ratio_width ) ) + ' / ' + str( ratio_height ) )
        
    if 'ratio' in simple_preds:
        
        ( ratio_width, ratio_height ) = simple_preds[ 'ratio' ]
        
        files_info_predicates.append( '( width * 1.0 ) / height = ' + str( float( ratio_width ) ) + ' / ' + str( ratio_height ) )
        
    if 'not_ratio' in simple_preds:
        
        ( ratio_width, ratio_height ) = simple_preds[ 'not_ratio' ]
        
        files_info_predicates.append( '( width * 1.0 ) / height != ' + str( float( ratio_width ) ) + ' / ' + str( ratio_height ) )
        
    if 'max_ratio' in simple_preds:
        
        ( ratio_width, ratio_height ) = simple_preds[ 'max_ratio' ]
        
        files_info_predicates.append( '( width * 1.0 ) / height < ' + str( float( ratio_width ) ) + ' / ' + str( ratio_height ) )
        
    
    if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS in simple_preds:
        
        number_tests: list[ ClientNumberTest.NumberTest ] = simple_preds[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS ]
        
        for number_test in number_tests:
            
            files_info_predicates.extend( number_test.GetSQLitePredicates( 'num_words' ) )
            
        
    
    if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION in simple_preds:
        
        number_tests: list[ ClientNumberTest.NumberTest ] = simple_preds[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION ]
        
        for number_test in number_tests:
            
            files_info_predicates.extend( number_test.GetSQLitePredicates( 'duration' ) )
            
        
    
    if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE in simple_preds:
        
        number_tests: list[ ClientNumberTest.NumberTest ] = simple_preds[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE ]
        
        for number_test in number_tests:
            
            files_info_predicates.extend( number_test.GetSQLitePredicates( '( num_frames * 1.0 ) / ( duration / 1000.0 )' ) )
            
        
    
    if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES in simple_preds:
        
        number_tests: list[ ClientNumberTest.NumberTest ] = simple_preds[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES ]
        
        for number_test in number_tests:
            
            files_info_predicates.extend( number_test.GetSQLitePredicates( 'num_frames' ) )
            
        
    
    return files_info_predicates
    

class ClientDBFilesSearchTags( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_tags: ClientDBMaster.ClientDBMasterTags,
        modules_tag_siblings: ClientDBTagSiblings.ClientDBTagSiblings,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts,
        modules_tag_search: ClientDBTagSearch.ClientDBTagSearch
    ):
        
        self.modules_services = modules_services
        self.modules_tags = modules_tags
        self.modules_tag_siblings = modules_tag_siblings
        self.modules_files_storage = modules_files_storage
        self.modules_mappings_counts = modules_mappings_counts
        self.modules_tag_search = modules_tag_search
        
        super().__init__( 'client file search using tags', cursor )
        
    
    def GetHashIdsAndNonZeroTagCounts( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearchTagContext.TagContext, hash_ids, namespace_wildcard = '*', job_status = None ):
        
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
            
            cancelled_hook = None
            
            if job_status is not None:
                
                cancelled_hook = job_status.IsCancelled
                
            
            for group_of_hash_ids in HydrusLists.SplitIteratorIntoChunks( hash_ids, BLOCK_SIZE ):
                
                with self._MakeTemporaryIntegerTable( group_of_hash_ids, 'hash_id' ) as hash_ids_table_name:
                    
                    if namespace_wildcard == '*':
                        
                        # temp hashes to mappings
                        select_statements = [ 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id )'.format( hash_ids_table_name, mappings_table_name ) for ( mappings_table_name, tags_table_name ) in mapping_and_tag_table_names ]
                        
                    else:
                        
                        # temp hashes to mappings to tags to namespaces
                        select_statements = [ 'SELECT hash_id, tag_id FROM {} CROSS JOIN {} USING ( hash_id ) CROSS JOIN {} USING ( tag_id ) CROSS JOIN {} USING ( namespace_id )'.format( hash_ids_table_name, mappings_table_name, tags_table_name, temp_namespace_ids_table_name ) for ( mappings_table_name, tags_table_name ) in mapping_and_tag_table_names ]
                        
                    
                    unions = '( {} )'.format( ' UNION '.join( select_statements ) )
                    
                    query = 'SELECT hash_id, COUNT( tag_id ) FROM {} GROUP BY hash_id;'.format( unions )
                    
                    loop_of_results = self._ExecuteCancellable( query, (), cancelled_hook )
                    
                    if job_status is not None and job_status.IsCancelled():
                        
                        return results
                        
                    
                    results.extend( loop_of_results )
                    
                
            
            return results
            
        
    
    def GetHashIdsFromNamespaceIdsSubtagIds( self, tag_display_type: int, file_service_key, tag_context: ClientSearchTagContext.TagContext, namespace_ids, subtag_ids, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        tag_ids = self.modules_tag_search.GetTagIdsFromNamespaceIdsSubtagIds( file_service_id, tag_service_id, namespace_ids, subtag_ids, job_status = job_status )
        
        return self.GetHashIdsFromTagIds( tag_display_type, file_service_key, tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
        
    
    def GetHashIdsFromNamespaceIdsSubtagIdsTables( self, tag_display_type: int, file_service_key, tag_context: ClientSearchTagContext.TagContext, namespace_ids_table_name, subtag_ids_table_name, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        tag_ids = self.modules_tag_search.GetTagIdsFromNamespaceIdsSubtagIdsTables( file_service_id, tag_service_id, namespace_ids_table_name, subtag_ids_table_name, job_status = job_status )
        
        return self.GetHashIdsFromTagIds( tag_display_type, file_service_key, tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
        
    
    def GetHashIdsFromSubtagIds( self, tag_display_type: int, file_service_key, tag_context: ClientSearchTagContext.TagContext, subtag_ids, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        tag_ids = self.modules_tag_search.GetTagIdsFromSubtagIds( file_service_id, tag_service_id, subtag_ids, job_status = job_status )
        
        return self.GetHashIdsFromTagIds( tag_display_type, file_service_key, tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
        
    
    def GetHashIdsFromSubtagIdsTable( self, tag_display_type: int, file_service_key, tag_context: ClientSearchTagContext.TagContext, subtag_ids_table_name, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
        file_service_id = self.modules_services.GetServiceId( file_service_key )
        tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
        
        tag_ids = self.modules_tag_search.GetTagIdsFromSubtagIdsTable( file_service_id, tag_service_id, subtag_ids_table_name, job_status = job_status )
        
        return self.GetHashIdsFromTagIds( tag_display_type, file_service_key, tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
        
    
    def GetHashIdsFromTag( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearchTagContext.TagContext, tag, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
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
        
        tag_id = self.modules_tags.GetTagId( tag )
        
        for search_tag_service_id in search_tag_service_ids:
            
            search_tag_service_key = service_ids_to_service_keys[ search_tag_service_id ]
            
            search_tag_context = ClientSearchTagContext.TagContext( service_key = search_tag_service_key, include_current_tags = tag_context.include_current_tags, include_pending_tags = tag_context.include_pending_tags, display_service_key = search_tag_service_key )
            
            ideal_tag_id = self.modules_tag_siblings.GetIdealTagId( tag_display_type, search_tag_service_id, tag_id )
            
            for file_service_key in file_service_keys:
                
                # just as a legacy note, this is where we used to do the "'samus aran' gets 'character:samus aran'" code. now, that stuff works through wildcards if user explicitly enters '*:samus aran'
                
                tag_ids = ( ideal_tag_id, )
                
                some_results = self.GetHashIdsFromTagIds( tag_display_type, file_service_key, search_tag_context, tag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
                
                if len( results ) == 0:
                    
                    results = some_results
                    
                else:
                    
                    results.update( some_results )
                    
                
            
        
        if not file_location_is_cross_referenced:
            
            results = self.modules_files_storage.FilterHashIds( location_context, results )
            
        
        return results
        
    
    def GetHashIdsFromTagAdvanced( self, tag: str, tag_display_type: int, statuses: collections.abc.Collection[ int ], tag_service_keys: collections.abc.Collection[ bytes ], location_context: ClientLocation.LocationContext, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
        # This search routine and its predicate caller were brought to you by: cheap booze and hololive 6th fes. ~Color Rise Harmony~ STAGE 3
        
        # TODO: This code is actually not bad compared to the other search gubbins in this module
        # We could integrate the other features of the other methods and crunch it all into one advanced search routine that we optimise on its own rather than having similar search code in ten different places
        # and/or split the clever stuff in here that does the mappings_table storage->display wangle etc... into a new method that other guys call with current/pending
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        ( file_service_keys, file_location_is_cross_referenced ) = location_context.GetCoveringCurrentFileServiceKeys()
        
        if not file_location_is_cross_referenced and hash_ids_table_name is not None:
            
            file_location_is_cross_referenced = True
            
        
        file_service_ids = [ self.modules_services.GetServiceId( file_service_key ) for file_service_key in file_service_keys ]
        tag_service_ids = [ self.modules_services.GetServiceId( tag_service_key ) for tag_service_key in tag_service_keys ]
        
        result_hash_ids = set()
        
        tag_id = self.modules_tags.GetTagId( tag )
        
        for file_service_id in file_service_ids:
            
            for tag_service_id in tag_service_ids:
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = ClientDBMappingsStorage.GenerateMappingsTableNames( tag_service_id )
                
                if file_service_id == self.modules_services.combined_file_service_id:
                    
                    statuses_to_table_names = {
                        HC.CONTENT_STATUS_CURRENT : ( current_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE ),
                        HC.CONTENT_STATUS_DELETED : ( deleted_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE ),
                        HC.CONTENT_STATUS_PENDING : ( pending_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE ),
                        HC.CONTENT_STATUS_PETITIONED : ( petitioned_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE )
                    }
                    
                else:
                    
                    ( cache_current_mappings_table_name, cache_deleted_mappings_table_name, cache_pending_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
                    
                    if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE:
                        
                        statuses_to_table_names = {
                            HC.CONTENT_STATUS_CURRENT : ( cache_current_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE ),
                            HC.CONTENT_STATUS_DELETED : ( cache_deleted_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE ),
                            HC.CONTENT_STATUS_PENDING : ( cache_pending_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE ),
                            HC.CONTENT_STATUS_PETITIONED : ( petitioned_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE )
                        }
                        
                    elif tag_display_type == ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL:
                        
                        ( cache_current_display_mappings_table_name, cache_pending_display_mappings_table_name ) = ClientDBMappingsStorage.GenerateSpecificDisplayMappingsCacheTableNames( file_service_id, tag_service_id )
                        
                        statuses_to_table_names = {
                            HC.CONTENT_STATUS_CURRENT : ( cache_current_display_mappings_table_name, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ),
                            HC.CONTENT_STATUS_DELETED : ( cache_pending_display_mappings_table_name, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ),
                            HC.CONTENT_STATUS_PENDING : ( cache_pending_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE ),
                            HC.CONTENT_STATUS_PETITIONED : ( petitioned_mappings_table_name, ClientTags.TAG_DISPLAY_STORAGE )
                        }
                        
                    else:
                        
                        statuses_to_table_names = {}
                        
                    
                
                for status in statuses:
                    
                    if status not in statuses_to_table_names:
                        
                        continue
                        
                    
                    ( mappings_table_name, table_tag_display_type ) = statuses_to_table_names[ status ]
                    
                    if tag_display_type == ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL:
                        
                        ideal_tag_id = self.modules_tag_siblings.GetIdealTagId( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, tag_id )
                        
                        if table_tag_display_type == ClientTags.TAG_DISPLAY_STORAGE:
                            
                            search_tag_ids = self.modules_tag_siblings.GetChainMembersFromIdeal( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, ideal_tag_id )
                            
                        else:
                            
                            search_tag_ids = ( ideal_tag_id, )
                            
                        
                    else:
                        
                        search_tag_ids = ( tag_id, )
                        
                    
                    if len( search_tag_ids ) == 1:
                        
                        ( search_tag_id, ) = search_tag_ids
                        
                        if hash_ids is not None and hash_ids_table_name is not None:
                            
                            # temp hashes to mappings
                            query = f'SELECT hash_id FROM {hash_ids_table_name} CROSS JOIN {mappings_table_name} USING ( hash_id ) WHERE tag_id = ?'
                            
                        else:
                            
                            query = f'SELECT hash_id FROM {mappings_table_name} WHERE tag_id = ?;'
                            
                        
                        result_hash_ids.update( self._STI( self._ExecuteCancellable( query, ( search_tag_id, ), cancelled_hook ) ) )
                        
                    else:
                        
                        with self._MakeTemporaryIntegerTable( search_tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
                            
                            if hash_ids is not None and hash_ids_table_name is not None:
                                
                                # temp hashes to mappings to temp tags
                                # old method, does not do EXISTS efficiently, it makes a list instead and checks that
                                # queries = [ 'SELECT hash_id FROM {} WHERE EXISTS ( SELECT 1 FROM {} CROSS JOIN {} USING ( tag_id ) WHERE {}.hash_id = {}.hash_id );'.format( hash_ids_table_name, table_name, temp_tag_ids_table_name, table_name, hash_ids_table_name ) for table_name in table_names ]
                                # new method, this seems to actually do the correlated scalar subquery, although it does seem to be sqlite voodoo
                                query = f'SELECT hash_id FROM {hash_ids_table_name} WHERE EXISTS ( SELECT 1 FROM {mappings_table_name} WHERE {mappings_table_name}.hash_id = {hash_ids_table_name}.hash_id AND EXISTS ( SELECT 1 FROM {temp_tag_ids_table_name} WHERE {mappings_table_name}.tag_id = {temp_tag_ids_table_name}.tag_id ) );'
                                
                            else:
                                
                                # temp tags to mappings
                                query = f'SELECT hash_id FROM {temp_tag_ids_table_name} CROSS JOIN {mappings_table_name} USING ( tag_id );'
                                
                            
                            result_hash_ids.update( self._STI( self._ExecuteCancellable( query, (), cancelled_hook ) ) )
                            
                        
                    
                
            
        
        if not file_location_is_cross_referenced:
            
            result_hash_ids = self.modules_files_storage.FilterHashIds( location_context, result_hash_ids )
            
        
        return result_hash_ids
        
    
    def GetHashIdsFromTagIds( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearchTagContext.TagContext, tag_ids: collections.abc.Collection[ int ], hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
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
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        if len( tag_ids ) == 1:
            
            ( tag_id, ) = tag_ids
            
            if do_hash_table_join:
                
                # temp hashes to mappings
                queries = [ 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id ) WHERE tag_id = ?'.format( hash_ids_table_name, table_name ) for table_name in table_names ]
                
            else:
                
                queries = [ 'SELECT hash_id FROM {} WHERE tag_id = ?;'.format( table_name ) for table_name in table_names ]
                
            
            for query in queries:
                
                result_hash_ids.update( self._STI( self._ExecuteCancellable( query, ( tag_id, ), cancelled_hook ) ) )
                
            
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
                    
                    result_hash_ids.update( self._STI( self._ExecuteCancellable( query, (), cancelled_hook ) ) )
                    
                
            
        
        return result_hash_ids
        
    
    def GetHashIdsFromTagIdsTables( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearchTagContext.TagContext, tag_ids: collections.abc.Collection[ int ], hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
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
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        if len( tag_ids ) == 1:
            
            ( tag_id, ) = tag_ids
            
            if do_hash_table_join:
                
                # temp hashes to mappings
                queries = [ 'SELECT hash_id FROM {} CROSS JOIN {} USING ( hash_id ) WHERE tag_id = ?'.format( hash_ids_table_name, table_name ) for table_name in table_names ]
                
            else:
                
                queries = [ 'SELECT hash_id FROM {} WHERE tag_id = ?;'.format( table_name ) for table_name in table_names ]
                
            
            for query in queries:
                
                result_hash_ids.update( self._STI( self._ExecuteCancellable( query, ( tag_id, ), cancelled_hook ) ) )
                
            
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
                    
                    result_hash_ids.update( self._STI( self._ExecuteCancellable( query, (), cancelled_hook ) ) )
                    
                
            
        
        return result_hash_ids
        
    
    def GetHashIdsFromWildcardComplexLocation( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearchTagContext.TagContext, wildcard, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
        ( namespace_wildcard, subtag_wildcard ) = HydrusTags.SplitTag( wildcard )
        
        if subtag_wildcard == '*':
            
            return self.GetHashIdsThatHaveTagsComplexLocation( tag_display_type, location_context, tag_context, namespace_wildcard = namespace_wildcard, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
            
        
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
                
                some_results = self.GetHashIdsFromWildcardSimpleLocation( tag_display_type, file_service_key, tag_context, subtag_wildcard, namespace_ids_table_name = namespace_ids_table_name, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
                
                if len( results ) == 0:
                    
                    results = some_results
                    
                else:
                    
                    results.update( some_results )
                    
                
            
        
        if not file_location_is_cross_referenced:
            
            results = self.modules_files_storage.FilterHashIds( location_context, results )
            
        
        return results
        
    
    def GetHashIdsFromWildcardSimpleLocation( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearchTagContext.TagContext, subtag_wildcard, namespace_ids_table_name = None, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
        with self._MakeTemporaryIntegerTable( [], 'subtag_id' ) as temp_subtag_ids_table_name:
            
            file_service_id = self.modules_services.GetServiceId( file_service_key )
            tag_service_id = self.modules_services.GetServiceId( tag_context.service_key )
            
            self.modules_tag_search.GetSubtagIdsFromWildcardIntoTable( file_service_id, tag_service_id, subtag_wildcard, temp_subtag_ids_table_name, job_status = job_status )
            
            if namespace_ids_table_name is None:
                
                return self.GetHashIdsFromSubtagIdsTable( tag_display_type, file_service_key, tag_context, temp_subtag_ids_table_name, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
                
            else:
                
                return self.GetHashIdsFromNamespaceIdsSubtagIdsTables( tag_display_type, file_service_key, tag_context, namespace_ids_table_name, temp_subtag_ids_table_name, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
                
            
        
    
    def GetHashIdsThatHaveTagAsNumComplexLocation( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearchTagContext.TagContext, namespace_wildcard, num, operator, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
        if location_context.IsEmpty():
            
            return set()
            
        
        ( file_service_keys, file_location_is_cross_referenced ) = location_context.GetCoveringCurrentFileServiceKeys()
        
        if not file_location_is_cross_referenced and hash_ids_table_name is not None:
            
            file_location_is_cross_referenced = True
            
        
        results = set()
        
        for file_service_key in file_service_keys:
            
            some_results = self.GetHashIdsThatHaveTagAsNumSimpleLocation( tag_display_type, file_service_key, tag_context, namespace_wildcard, num, operator, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
            
            if len( results ) == 0:
                
                results = some_results
                
            else:
                
                results.update( some_results )
                
            
        
        if not file_location_is_cross_referenced:
            
            results = self.modules_files_storage.FilterHashIds( location_context, results )
            
        
        return results
        
    
    def GetHashIdsThatHaveTagAsNumSimpleLocation( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearchTagContext.TagContext, namespace_wildcard, num, operator, hash_ids = None, hash_ids_table_name = None, job_status = None ):
        
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
            
            return self.GetHashIdsFromSubtagIds( tag_display_type, file_service_key, tag_context, possible_subtag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
            
        else:
            
            possible_namespace_ids = self.modules_tag_search.GetNamespaceIdsFromWildcard( namespace_wildcard )
            
            return self.GetHashIdsFromNamespaceIdsSubtagIds( tag_display_type, file_service_key, tag_context, possible_namespace_ids, possible_subtag_ids, hash_ids = hash_ids, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
            
        
    
    def GetHashIdsThatHaveTagsComplexLocation( self, tag_display_type: int, location_context: ClientLocation.LocationContext, tag_context: ClientSearchTagContext.TagContext, namespace_wildcard = '*', hash_ids_table_name = None, job_status = None ):
        
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
                
                some_results = self.GetHashIdsThatHaveTagsSimpleLocation( tag_display_type, file_service_key, tag_context, namespace_ids_table_name = namespace_ids_table_name, hash_ids_table_name = hash_ids_table_name, job_status = job_status )
                
                if len( results ) == 0:
                    
                    results = some_results
                    
                else:
                    
                    results.update( some_results )
                    
                
            
        
        if not file_location_is_cross_referenced:
            
            results = self.modules_files_storage.FilterHashIds( location_context, results )
            
        
        return results
        
    
    def GetHashIdsThatHaveTagsSimpleLocation( self, tag_display_type: int, file_service_key: bytes, tag_context: ClientSearchTagContext.TagContext, namespace_ids_table_name = None, hash_ids_table_name = None, job_status = None ):
        
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
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        nonzero_tag_hash_ids = set()
        
        for query in queries:
            
            nonzero_tag_hash_ids.update( self._STI( self._ExecuteCancellable( query, (), cancelled_hook ) ) )
            
            if job_status is not None and job_status.IsCancelled():
                
                return set()
                
            
        
        return nonzero_tag_hash_ids
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    


class ClientDBFilesQuery( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_hashes: ClientDBMaster.ClientDBMasterHashes,
        modules_tags: ClientDBMaster.ClientDBMasterTags,
        modules_files_metadata_basic: ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic,
        modules_files_timestamps: ClientDBFilesTimestamps.ClientDBFilesTimestamps,
        modules_files_viewing_stats: ClientDBFilesViewingStats.ClientDBFilesViewingStats,
        modules_url_map: ClientDBURLMap.ClientDBURLMap,
        modules_notes_map: ClientDBNotesMap.ClientDBNotesMap,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_files_inbox: ClientDBFilesInbox.ClientDBFilesInbox,
        modules_mappings_counts: ClientDBMappingsCounts.ClientDBMappingsCounts,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_tag_search: ClientDBTagSearch.ClientDBTagSearch,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles,
        modules_files_duplicates_storage: ClientDBFilesDuplicatesStorage.ClientDBFilesDuplicatesStorage,
        modules_files_search_tags: ClientDBFilesSearchTags
    ):
        
        # this is obviously a monster, so the solution is going to be to merge the sub-modules into 'search' modules like the 'tags' one above. this guy doesn't have to do search, it can farm that work out
        
        self.modules_services = modules_services
        self.modules_hashes = modules_hashes
        self.modules_tags = modules_tags
        self.modules_files_metadata_basic = modules_files_metadata_basic
        self.modules_files_timestamps = modules_files_timestamps
        self.modules_files_viewing_stats = modules_files_viewing_stats
        self.modules_url_map = modules_url_map
        self.modules_notes_map = modules_notes_map
        self.modules_files_storage = modules_files_storage
        self.modules_files_inbox = modules_files_inbox
        self.modules_mappings_counts = modules_mappings_counts
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_tag_search = modules_tag_search
        self.modules_similar_files = modules_similar_files
        self.modules_files_duplicates_storage = modules_files_duplicates_storage
        self.modules_files_search_tags = modules_files_search_tags
        
        super().__init__( 'client file query', cursor )
        
    
    def _Do1PreInclusiveTagPreds( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, job_status: ClientThreading.JobStatus, query_hash_ids: set[ int ] | None, db_location_context: ClientDBFilesStorage.DBLocationContext, search_state: SearchState ) -> set[ int ] | None:
        
        # ok these should ideally all be nice and fast without query_hash_ids
        
        system_predicates = file_search_context.GetSystemPredicates()
        simple_preds = system_predicates.GetSimpleInfo()
        
        if 'hashes' in simple_preds:
            
            for ( search_hashes, search_hash_type, inclusive ) in simple_preds[ 'hashes' ]:
                
                if inclusive:
                    
                    if search_hash_type == 'sha256':
                        
                        matching_sha256_hashes = [ search_hash for search_hash in search_hashes if self.modules_hashes.HasHash( search_hash ) ]
                        
                    else:
                        
                        source_to_desired = self.modules_hashes.GetFileHashes( search_hashes, search_hash_type, 'sha256' )
                        
                        matching_sha256_hashes = list( source_to_desired.values() )
                        
                    
                    specific_hash_ids = self.modules_hashes_local_cache.GetHashIds( matching_sha256_hashes )
                    
                    query_hash_ids = intersection_update_qhi( query_hash_ids, specific_hash_ids )
                    
                
            
        
        #

        query_hash_ids = self._DoTimestampPreds( file_search_context, query_hash_ids, search_state, job_status = job_status )
        
        query_hash_ids = self._DoSimpleRatingPreds( file_search_context, query_hash_ids, job_status = job_status )
        
        for predicate in system_predicates.GetAdvancedRatingsPredicates():
            
            query_hash_ids = self._DoAdvancedRatingPredicateInclusiveOnly( predicate, query_hash_ids, job_status = job_status )
            
        
        #
        
        for ( view_type, desired_canvas_types, operator, viewing_value ) in system_predicates.GetFileViewingStatsPredicates():
            
            only_do_zero = ( operator in ( '=', HC.UNICODE_APPROX_EQUAL ) and viewing_value == 0 ) or ( operator == '<' and viewing_value == 1 )
            include_zero = operator == '<'
            
            if only_do_zero:
                
                continue
                
            elif include_zero:
                
                continue
                
            else:
                
                viewing_hash_ids = self.modules_files_viewing_stats.GetHashIdsFromFileViewingStatistics( view_type, desired_canvas_types, operator, viewing_value )
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, viewing_hash_ids )
                
            
        
        for ( operator, num_relationships, dupe_type ) in system_predicates.GetDuplicateRelationshipCountPredicates():
            
            only_do_zero = ( operator in ( '=', HC.UNICODE_APPROX_EQUAL ) and num_relationships == 0 ) or ( operator == '<' and num_relationships == 1 )
            include_zero = operator == '<'
            
            if only_do_zero:
                
                continue
                
            elif include_zero:
                
                continue
                
            else:
                
                dupe_hash_ids = self.modules_files_duplicates_storage.GetHashIdsFromDuplicateCountPredicate( db_location_context, operator, num_relationships, dupe_type )
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, dupe_hash_ids )
                
                search_state.have_cross_referenced_file_locations = True
                
            
        
        if system_predicates.HasSimilarToData():
            
            ( pixel_hashes, perceptual_hashes, max_hamming ) = system_predicates.GetSimilarToData()
            
            all_similar_hash_ids = set()
            
            pixel_hash_ids = set()
            
            for pixel_hash in pixel_hashes:
                
                if self.modules_hashes.HasHash( pixel_hash ):
                    
                    pixel_hash_id = self.modules_hashes_local_cache.GetHashId( pixel_hash )
                    
                    pixel_hash_ids.add( pixel_hash_id )
                    
                
            
            if len( pixel_hash_ids ) > 0:
                
                similar_hash_ids_and_distances = self.modules_similar_files.SearchPixelHashes( pixel_hash_ids )
                
                similar_hash_ids = [ similar_hash_id for ( similar_hash_id, distance ) in similar_hash_ids_and_distances ]
                
                all_similar_hash_ids.update( similar_hash_ids )
                
            
            if len( perceptual_hashes ) > 0:
                
                similar_hash_ids_and_distances = self.modules_similar_files.SearchPerceptualHashes( perceptual_hashes, max_hamming )
                
                similar_hash_ids = [ similar_hash_id for ( similar_hash_id, distance ) in similar_hash_ids_and_distances ]
                
                all_similar_hash_ids.update( similar_hash_ids )
                
            
            query_hash_ids = intersection_update_qhi( query_hash_ids, all_similar_hash_ids )
            
        
        if system_predicates.HasSimilarToFiles():
            
            ( similar_to_hashes, max_hamming ) = system_predicates.GetSimilarToFiles()
            
            all_similar_hash_ids = set()
            
            for similar_to_hash in similar_to_hashes:
                
                hash_id = self.modules_hashes_local_cache.GetHashId( similar_to_hash )
                
                similar_hash_ids_and_distances = self.modules_similar_files.SearchFile( hash_id, max_hamming )
                
                similar_hash_ids = [ similar_hash_id for ( similar_hash_id, distance ) in similar_hash_ids_and_distances ]
                
                all_similar_hash_ids.update( similar_hash_ids )
                
            
            query_hash_ids = intersection_update_qhi( query_hash_ids, all_similar_hash_ids )
            
        
        is_inbox = system_predicates.MustBeInbox()
        
        if is_inbox:
            
            query_hash_ids = intersection_update_qhi( query_hash_ids, self.modules_files_inbox.inbox_hash_ids, force_create_new_set = True )
            
        
        #
        
        # last shot before tags and stuff to try to do these. we can only do them if query hash ids has stuff in
        if query_hash_ids is not None and not search_state.done_tricky_incdec_ratings:
            
            for ( operator, value, rating_service_key ) in system_predicates.GetRatingsPredicates():
                
                if isinstance( value, int ):
                    
                    service_id = self.modules_services.GetServiceId( rating_service_key )
                    
                    service = CG.client_controller.services_manager.GetService( rating_service_key )
                    
                    service_type = service.GetServiceType()
                    
                    if service_type == HC.LOCAL_RATING_INCDEC:
                        
                        if operator == '<' or ( operator == '=' and value == 0 ):
                            
                            rated_hash_ids = self._STI( self._Execute( 'SELECT hash_id FROM local_incdec_ratings WHERE service_id = ?;', ( service_id, ) ) )
                            
                            not_rated_hash_ids = query_hash_ids.difference( rated_hash_ids )
                            
                            # 'no rating' for incdec = 0
                            
                            rating_hash_ids = not_rated_hash_ids
                            
                            if operator == '<' and value > 1:
                                
                                less_than_rating_hash_ids = self._STI( self._Execute( 'SELECT hash_id FROM local_incdec_ratings WHERE service_id = ? AND rating < ?;', ( service_id, value ) ) )
                                
                                rating_hash_ids.update( less_than_rating_hash_ids )
                                
                            
                            query_hash_ids = intersection_update_qhi( query_hash_ids, rating_hash_ids )
                            
                        
                    
                
            
            search_state.done_tricky_incdec_ratings = True
            
        
        return query_hash_ids
        
    
    def _Do2InclusiveTagPreds( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, job_status: ClientThreading.JobStatus, query_hash_ids: set[ int ] | None, search_state: SearchState ) -> set[ int ] | None:
        
        location_context = file_search_context.GetLocationContext()
        tag_context = file_search_context.GetTagContext()
        
        system_predicates = file_search_context.GetSystemPredicates()
        
        tags_to_include = file_search_context.GetTagsToInclude()
        
        namespaces_to_include = file_search_context.GetNamespacesToInclude()
        
        wildcards_to_include = file_search_context.GetWildcardsToInclude()
        
        is_inbox = system_predicates.MustBeInbox()
        
        if search_state.there_are_tags_to_search:
            
            def sort_longest_tag_first_key( s ):
                
                return ( 1 if HydrusTags.IsUnnamespaced( s ) else 0, -len( s ) )
                
            
            tags_to_include = list( tags_to_include )
            
            tags_to_include.sort( key = sort_longest_tag_first_key )
            
            for tag in tags_to_include:
                
                if query_hash_ids is None:
                    
                    tag_query_hash_ids = self.modules_files_search_tags.GetHashIdsFromTag( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, tag, job_status = job_status )
                    
                elif is_inbox and len( query_hash_ids ) == len( self.modules_files_inbox.inbox_hash_ids ):
                    
                    tag_query_hash_ids = self.modules_files_search_tags.GetHashIdsFromTag( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, tag, hash_ids = self.modules_files_inbox.inbox_hash_ids, hash_ids_table_name = 'file_inbox', job_status = job_status )
                    
                else:
                    
                    with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                        
                        tag_query_hash_ids = self.modules_files_search_tags.GetHashIdsFromTag( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, tag, hash_ids = query_hash_ids, hash_ids_table_name = temp_table_name, job_status = job_status )
                        
                    
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, tag_query_hash_ids )
                
                search_state.have_cross_referenced_file_locations = True
                
                if len( query_hash_ids ) == 0:
                    
                    return set()
                    
                
            
            namespaces_to_include = list( namespaces_to_include )
            
            namespaces_to_include.sort( key = lambda n: -len( n ) )
            
            for namespace in namespaces_to_include:
                
                if query_hash_ids is None or ( is_inbox and len( query_hash_ids ) == len( self.modules_files_inbox.inbox_hash_ids ) ):
                    
                    namespace_query_hash_ids = self.modules_files_search_tags.GetHashIdsThatHaveTagsComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, namespace_wildcard = namespace, job_status = job_status )
                    
                else:
                    
                    with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                        
                        self._AnalyzeTempTable( temp_table_name )
                        
                        namespace_query_hash_ids = self.modules_files_search_tags.GetHashIdsThatHaveTagsComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, namespace_wildcard = namespace, hash_ids_table_name = temp_table_name, job_status = job_status )
                        
                    
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, namespace_query_hash_ids )
                
                search_state.have_cross_referenced_file_locations = True
                
                if len( query_hash_ids ) == 0:
                    
                    return set()
                    
                
            
            wildcards_to_include = list( wildcards_to_include )
            
            wildcards_to_include.sort( key = lambda w: -len( w ) )
            
            for wildcard in wildcards_to_include:
                
                if query_hash_ids is None:
                    
                    wildcard_query_hash_ids = self.modules_files_search_tags.GetHashIdsFromWildcardComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, wildcard, job_status = job_status )
                    
                else:
                    
                    with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                        
                        self._AnalyzeTempTable( temp_table_name )
                        
                        wildcard_query_hash_ids = self.modules_files_search_tags.GetHashIdsFromWildcardComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, wildcard, hash_ids = query_hash_ids, hash_ids_table_name = temp_table_name, job_status = job_status )
                        
                    
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, wildcard_query_hash_ids )
                
                search_state.have_cross_referenced_file_locations = True
                
                if len( query_hash_ids ) == 0:
                    
                    return set()
                    
                
            
        
        #
        
        # ok let's do inclusive advanced tags. no great place to put these, but expensive search is already bought in here so there we go
        
        for pred in system_predicates.GetAdvancedTagPredicates():
            
            if pred.IsInclusive():
                
                pred_query_hash_ids = self._DoAdvancedTagPredicate( file_search_context, job_status, pred, query_hash_ids )
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, pred_query_hash_ids )
                
            
        
        return query_hash_ids
        
    
    def _Do3FileInfoPreds( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, job_status: ClientThreading.JobStatus, query_hash_ids: set[ int ] | None, db_location_context: ClientDBFilesStorage.DBLocationContext, search_state: SearchState ) -> set[ int ]:
        
        system_predicates = file_search_context.GetSystemPredicates()
        
        is_inbox = system_predicates.MustBeInbox()
        
        location_context = file_search_context.GetLocationContext()
        tag_context = file_search_context.GetTagContext()
        
        not_all_known_files = not location_context.IsAllKnownFiles()
        
        we_need_some_results = query_hash_ids is None
        we_need_to_cross_reference = not_all_known_files and not search_state.have_cross_referenced_file_locations
        
        files_info_predicates = GetFilesInfoPredicates( system_predicates )
        
        if we_need_some_results or we_need_to_cross_reference:
            
            if location_context.IsAllKnownFiles():
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, self.modules_files_search_tags.GetHashIdsThatHaveTagsComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, job_status = job_status ) )
                
            else:
                
                if len( files_info_predicates ) == 0:
                    
                    files_info_predicates.insert( 0, '1=1' )
                    include_files_info = False
                    
                else:
                    
                    include_files_info = True
                    
                
                file_info_query_hash_ids = set()
                
                for files_table_name in db_location_context.GetMultipleFilesTableNames():
                    
                    if include_files_info:
                        
                        # if a file is missing a files_info row, we can't search it with a file system pred. it is just unknown
                        files_table_name = '{} NATURAL JOIN files_info'.format( files_table_name )
                        
                    
                    if query_hash_ids is None:
                        
                        loop_query_hash_ids = self._STS( self._Execute( 'SELECT hash_id AS h1 FROM {} WHERE {};'.format( files_table_name, ' AND '.join( files_info_predicates ) ) ) )
                        
                    else:
                        
                        if is_inbox and len( query_hash_ids ) == len( self.modules_files_inbox.inbox_hash_ids ):
                            
                            loop_query_hash_ids = self._STS( self._Execute( 'SELECT hash_id AS h1 FROM {} NATURAL JOIN {} WHERE {};'.format( 'file_inbox', files_table_name, ' AND '.join( files_info_predicates ) ) ) )
                            
                        else:
                            
                            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                                
                                self._AnalyzeTempTable( temp_table_name )
                                
                                loop_query_hash_ids = self._STS( self._Execute( 'SELECT hash_id AS h1 FROM {} NATURAL JOIN {} WHERE {};'.format( temp_table_name, files_table_name, ' AND '.join( files_info_predicates ) ) ) )
                                
                            
                        
                    
                    file_info_query_hash_ids.update( loop_query_hash_ids )
                    
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, file_info_query_hash_ids )
                
                search_state.have_cross_referenced_file_locations = True
                search_state.done_files_info_predicates = True
                
            
        
        # query_hash_ids now definitely has something in it
        
        # don't be hasty to ever remove this
        if query_hash_ids is None:
            
            global SHOWN_UNINITIALISED_SEARCH_ERROR
            
            if not SHOWN_UNINITIALISED_SEARCH_ERROR:
                
                HydrusData.ShowText( 'Hey, the search you just performed came up with zero results in part because it failed to initialise properly. Please contact hydev with any details you have.\n\nTo stop spam, this message will only show one time per program boot. The error may happen again, silently.' )
                
                SHOWN_UNINITIALISED_SEARCH_ERROR = True
                
            
            query_hash_ids = set()
            
        
        query_hash_ids = typing.cast( set[ int ], query_hash_ids )
        
        # this was bodged in here during a rewrite; there is probably a nicer 'if cross-referenced already, do above, else this', but this is fine for now
        if search_state.there_are_simple_files_info_preds_to_search_for and not search_state.done_files_info_predicates:
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                
                self._AnalyzeTempTable( temp_table_name )
                
                predicate_string = ' AND '.join( files_info_predicates )
                
                select = 'SELECT hash_id AS h1 FROM {} NATURAL JOIN files_info WHERE {};'.format( temp_table_name, predicate_string )
                
                files_info_hash_ids = self._STI( self._Execute( select ) )
                
                query_hash_ids.intersection_update( files_info_hash_ids )
                
            
            search_state.done_files_info_predicates = True
            
        
        return query_hash_ids
        
    
    def _Do4InexpensivePostFileCrossReferencePreds( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, job_status: ClientThreading.JobStatus, query_hash_ids: set[ int ], search_state: SearchState ):
        
        # I have not rigorously tested that these are truly inexpensive, they just percolated like this in older code
        
        system_predicates = file_search_context.GetSystemPredicates()
        
        simple_preds = system_predicates.GetSimpleInfo()
        
        king_filter = system_predicates.GetKingFilter()
        
        #
        
        # hide update files
        
        if file_search_context.GetLocationContext().IsHydrusLocalFileStorage():
            
            repo_update_hash_ids = set( self.modules_files_storage.GetCurrentHashIdsList( self.modules_services.local_update_service_id ) )
            
            query_hash_ids.difference_update( repo_update_hash_ids )
            
        
        #
        
        ( required_file_service_statuses, excluded_file_service_statuses ) = system_predicates.GetFileServiceStatuses()
        
        for ( service_key, statuses ) in required_file_service_statuses.items():
            
            service_id = self.modules_services.GetServiceId( service_key )
            
            for status in statuses:
                
                required_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( service_id, query_hash_ids, status )
                
                query_hash_ids.intersection_update( required_hash_ids )
                
            
        
        for ( service_key, statuses ) in excluded_file_service_statuses.items():
            
            service_id = self.modules_services.GetServiceId( service_key )
            
            for status in statuses:
                
                excluded_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( service_id, query_hash_ids, status )
                
                query_hash_ids.difference_update( excluded_hash_ids )
                
            
        
        #
        
        # if we couldn't do them earlier, now we can
        if not search_state.done_tricky_incdec_ratings:
            
            search_state.done_tricky_incdec_ratings = True
            
            for ( operator, value, rating_service_key ) in system_predicates.GetRatingsPredicates():
                
                if isinstance( value, int ):
                    
                    service_id = self.modules_services.GetServiceId( rating_service_key )
                    
                    service = CG.client_controller.services_manager.GetService( rating_service_key )
                    
                    service_type = service.GetServiceType()
                    
                    if service_type == HC.LOCAL_RATING_INCDEC:
                        
                        if operator == '<' or ( operator == '=' and value == 0 ):
                            
                            rated_hash_ids = self._STI( self._Execute( 'SELECT hash_id FROM local_incdec_ratings WHERE service_id = ?;', ( service_id, ) ) )
                            
                            not_rated_hash_ids = query_hash_ids.difference( rated_hash_ids )
                            
                            # 'no rating' for incdec = 0
                            
                            rating_hash_ids = not_rated_hash_ids
                            
                            if operator == '<' and value > 1:
                                
                                less_than_rating_hash_ids = self._STI( self._Execute( 'SELECT hash_id FROM local_incdec_ratings WHERE service_id = ? AND rating < ?;', ( service_id, value ) ) )
                                
                                rating_hash_ids.update( less_than_rating_hash_ids )
                                
                            
                            query_hash_ids.intersection_update( rating_hash_ids )
                            
                        
                    
                
            
        
        for pred in system_predicates.GetAdvancedTagPredicates():
            
            if not pred.IsInclusive():
                
                pred_query_hash_ids = self._DoAdvancedTagPredicate( file_search_context, job_status, pred, query_hash_ids )
                
                query_hash_ids.difference_update( pred_query_hash_ids )
                
            
        
        if 'hashes' in simple_preds:
            
            for ( search_hashes, search_hash_type, inclusive ) in simple_preds[ 'hashes' ]:
                
                if not inclusive:
                    
                    if search_hash_type == 'sha256':
                        
                        matching_sha256_hashes = [ search_hash for search_hash in search_hashes if self.modules_hashes.HasHash( search_hash ) ]
                        
                    else:
                        
                        source_to_desired = self.modules_hashes.GetFileHashes( search_hashes, search_hash_type, 'sha256' )
                        
                        matching_sha256_hashes = list( source_to_desired.values() )
                        
                    
                    specific_hash_ids = self.modules_hashes_local_cache.GetHashIds( matching_sha256_hashes )
                    
                    query_hash_ids.difference_update( specific_hash_ids )
                    
                
            
        
        if 'has_exif' in simple_preds:
            
            has_exif = simple_preds[ 'has_exif' ]
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                has_exif_hash_ids = self.modules_files_metadata_basic.GetHasEXIFHashIds( temp_hash_ids_table_name )
                
            
            if has_exif:
                
                query_hash_ids.intersection_update( has_exif_hash_ids )
                
            else:
                
                query_hash_ids.difference_update( has_exif_hash_ids )
                
            
        
        if 'has_human_readable_embedded_metadata' in simple_preds:
            
            has_human_readable_embedded_metadata = simple_preds[ 'has_human_readable_embedded_metadata' ]
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                has_human_readable_embedded_metadata_hash_ids = self.modules_files_metadata_basic.GetHasHumanReadableEmbeddedMetadataHashIds( temp_hash_ids_table_name )
                
            
            if has_human_readable_embedded_metadata:
                
                query_hash_ids.intersection_update( has_human_readable_embedded_metadata_hash_ids )
                
            else:
                
                query_hash_ids.difference_update( has_human_readable_embedded_metadata_hash_ids )
                
            
        
        if 'has_icc_profile' in simple_preds:
            
            has_icc_profile = simple_preds[ 'has_icc_profile' ]
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                has_icc_profile_hash_ids = self.modules_files_metadata_basic.GetHasICCProfileHashIds( temp_hash_ids_table_name )
                
            
            if has_icc_profile:
                
                query_hash_ids.intersection_update( has_icc_profile_hash_ids )
                
            else:
                
                query_hash_ids.difference_update( has_icc_profile_hash_ids )
                
            
        
        if 'has_transparency' in simple_preds:
            
            has_transparency = simple_preds[ 'has_transparency' ]
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                has_transparency_hash_ids = self.modules_files_metadata_basic.GetHasTransparencyHashIds( temp_hash_ids_table_name )
                
            
            if has_transparency:
                
                query_hash_ids.intersection_update( has_transparency_hash_ids )
                
            else:
                
                query_hash_ids.difference_update( has_transparency_hash_ids )
                
            
        
        if system_predicates.MustBeArchive():
            
            query_hash_ids.difference_update( self.modules_files_inbox.inbox_hash_ids )
            
        
        if king_filter is not None and king_filter:
            
            king_hash_ids = self.modules_files_duplicates_storage.FilterKingHashIds( query_hash_ids )
            
            query_hash_ids.intersection_update( king_hash_ids )
            
        
        return query_hash_ids
        
    
    def _Do5ExpensivePostFileCrossReferencePreds( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, job_status: ClientThreading.JobStatus, query_hash_ids: set[ int ] | None, db_location_context: ClientDBFilesStorage.DBLocationContext, search_state: SearchState ) -> set[ int ]:
        
        # I have not rigorously tested that these are truly inexpensive, they just percolated like this in older code
        
        location_context = file_search_context.GetLocationContext()
        tag_context = file_search_context.GetTagContext()
        
        system_predicates = file_search_context.GetSystemPredicates()
        
        simple_preds = system_predicates.GetSimpleInfo()
        
        king_filter = system_predicates.GetKingFilter()
        
        #
        
        tags_to_exclude = file_search_context.GetTagsToExclude()
        
        namespaces_to_exclude = file_search_context.GetNamespacesToExclude()
        
        wildcards_to_exclude = file_search_context.GetWildcardsToExclude()
        
        if len( tags_to_exclude ) + len( namespaces_to_exclude ) + len( wildcards_to_exclude ) > 0:
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                
                self._AnalyzeTempTable( temp_table_name )
                
                for tag in tags_to_exclude:
                    
                    unwanted_hash_ids = self.modules_files_search_tags.GetHashIdsFromTag( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, tag, hash_ids = query_hash_ids, hash_ids_table_name = temp_table_name, job_status = job_status )
                    
                    query_hash_ids.difference_update( unwanted_hash_ids )
                    
                    if len( query_hash_ids ) == 0:
                        
                        return set()
                        
                    
                    self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( temp_table_name ), ( ( hash_id, ) for hash_id in unwanted_hash_ids ) )
                    
                
                for namespace in namespaces_to_exclude:
                    
                    unwanted_hash_ids = self.modules_files_search_tags.GetHashIdsThatHaveTagsComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, namespace_wildcard = namespace, hash_ids_table_name = temp_table_name, job_status = job_status )
                    
                    query_hash_ids.difference_update( unwanted_hash_ids )
                    
                    if len( query_hash_ids ) == 0:
                        
                        return set()
                        
                    
                    self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( temp_table_name ), ( ( hash_id, ) for hash_id in unwanted_hash_ids ) )
                    
                
                for wildcard in wildcards_to_exclude:
                    
                    unwanted_hash_ids = self.modules_files_search_tags.GetHashIdsFromWildcardComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, wildcard, hash_ids = query_hash_ids, hash_ids_table_name = temp_table_name, job_status = job_status )
                    
                    query_hash_ids.difference_update( unwanted_hash_ids )
                    
                    if len( query_hash_ids ) == 0:
                        
                        return set()
                        
                    
                    self._ExecuteMany( 'DELETE FROM {} WHERE hash_id = ?;'.format( temp_table_name ), ( ( hash_id, ) for hash_id in unwanted_hash_ids ) )
                    
                
            
        
        #
        
        # ( query_exclude_ratings, query_args ) = self._BuildExcludeQueryRatings( file_search_context )
        
        # if query_exclude_ratings:
            
        #     query_hash_ids.difference_update( self._STI( self._Execute( query_exclude_ratings, query_args ) ) )
            
        
        #original exclude way follows
        #here is the original code for simpleratings
        for ( operator, value, service_key ) in system_predicates.GetRatingsPredicates():
            
            service_id = self.modules_services.GetServiceId( service_key )
            
            if value == 'not rated':
                
                query_hash_ids.difference_update( self._STI( self._Execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ?;', ( service_id, ) ) ) )
                
            
        
        # note the new code for advancedratings. if this code executes, any simpleratings excludes are redundant, because all will be excluded
        
        for predicate in system_predicates.GetAdvancedRatingsPredicates():
            
            query_hash_ids = self._DoAdvancedRatingPredicateExclusiveOnly( predicate, query_hash_ids, job_status = job_status )
            
        
        if king_filter is not None and not king_filter:
            
            king_hash_ids = self.modules_files_duplicates_storage.FilterKingHashIds( query_hash_ids )
            
            query_hash_ids.difference_update( king_hash_ids )
            
        
        for ( operator, num_relationships, dupe_type ) in system_predicates.GetDuplicateRelationshipCountPredicates():
            
            only_do_zero = ( operator in ( '=', HC.UNICODE_APPROX_EQUAL ) and num_relationships == 0 ) or ( operator == '<' and num_relationships == 1 )
            include_zero = operator == '<'
            
            if only_do_zero:
                
                nonzero_hash_ids = self.modules_files_duplicates_storage.GetHashIdsFromDuplicateCountPredicate( db_location_context, '>', 0, dupe_type )
                
                query_hash_ids.difference_update( nonzero_hash_ids )
                
            elif include_zero:
                
                nonzero_hash_ids = self.modules_files_duplicates_storage.GetHashIdsFromDuplicateCountPredicate( db_location_context, '>', 0, dupe_type )
                
                zero_hash_ids = query_hash_ids.difference( nonzero_hash_ids )
                
                accurate_except_zero_hash_ids = self.modules_files_duplicates_storage.GetHashIdsFromDuplicateCountPredicate( db_location_context, operator, num_relationships, dupe_type )
                
                hash_ids = zero_hash_ids.union( accurate_except_zero_hash_ids )
                
                query_hash_ids.intersection_update( hash_ids )
                
            
        
        query_hash_ids = self._DoNotePreds( system_predicates, query_hash_ids, job_status = job_status )
        
        for ( view_type, desired_canvas_types, operator, viewing_value ) in system_predicates.GetFileViewingStatsPredicates():
            
            only_do_zero = ( operator in ( '=', HC.UNICODE_APPROX_EQUAL ) and viewing_value == 0 ) or ( operator == '<' and viewing_value == 1 )
            include_zero = operator == '<'
            
            if only_do_zero:
                
                nonzero_hash_ids = self.modules_files_viewing_stats.GetHashIdsFromFileViewingStatistics( view_type, desired_canvas_types, '>', 0 )
                
                query_hash_ids.difference_update( nonzero_hash_ids )
                
            elif include_zero:
                
                nonzero_hash_ids = self.modules_files_viewing_stats.GetHashIdsFromFileViewingStatistics( view_type, desired_canvas_types, '>', 0 )
                
                zero_hash_ids = query_hash_ids.difference( nonzero_hash_ids )
                
                accurate_except_zero_hash_ids = self.modules_files_viewing_stats.GetHashIdsFromFileViewingStatistics( view_type, desired_canvas_types, operator, viewing_value )
                
                hash_ids = zero_hash_ids.union( accurate_except_zero_hash_ids )
                
                query_hash_ids.intersection_update( hash_ids )
                
            
        
        if job_status.IsCancelled():
            
            return set()
            
        
        #
        
        file_location_is_all_local = self.modules_services.LocationContextIsCoveredByHydrusLocalFileStorage( location_context )
        file_location_is_all_hydrus_local_file_storages_deleted = location_context.IsOneDomain() and CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in location_context.deleted_service_keys
        
        must_be_local = system_predicates.MustBeLocal() or system_predicates.MustBeArchive()
        must_not_be_local = system_predicates.MustNotBeLocal()
        
        if file_location_is_all_local:
            
            # if must be all local, we are great already
            
            if must_not_be_local:
                
                query_hash_ids = set()
                
            
        elif file_location_is_all_hydrus_local_file_storages_deleted:
            
            if must_be_local:
                
                query_hash_ids = set()
                
            
        elif must_be_local or must_not_be_local:
            
            if must_be_local:
                
                query_hash_ids = self.modules_files_storage.FilterHashIdsToStatus( self.modules_services.hydrus_local_file_storage_service_id, query_hash_ids, HC.CONTENT_STATUS_CURRENT )
                
            elif must_not_be_local:
                
                local_hash_ids = self.modules_files_storage.GetCurrentHashIdsList( self.modules_services.hydrus_local_file_storage_service_id )
                
                query_hash_ids.difference_update( local_hash_ids )
                
            
        
        #
        
        num_urls_tests = simple_preds.get( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, [] )
        
        if len( num_urls_tests ) > 0:
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                
                url_hash_ids = self.modules_url_map.GetHashIdsFromCountTests( num_urls_tests, query_hash_ids, temp_table_name )
                
            
            query_hash_ids.intersection_update( url_hash_ids )
            
        
        allowed_job_types = [
            'exact_match',
            'domain',
            'url_class',
            'url_match'
        ]
        
        query_hash_ids = self._DoSpecificKnownURLPreds( file_search_context, query_hash_ids, allowed_job_types )
        
        #
        
        namespaces_to_tests = system_predicates.GetNumTagsNumberTests()
        
        for ( namespace, number_tests ) in namespaces_to_tests.items():
            
            namespace_wildcard = namespace
            
            if namespace_wildcard is None:
                
                namespace_wildcard = '*'
                
            
            specific_number_tests = [ number_test for number_test in number_tests if not ( number_test.IsZero() or number_test.IsAnythingButZero() ) ]
            
            megalambda = ClientNumberTest.NumberTest.STATICCreateMegaLambda( specific_number_tests )
            
            is_zero = True in ( number_test.IsZero() for number_test in number_tests )
            is_anything_but_zero = True in ( number_test.IsAnythingButZero() for number_test in number_tests )
            wants_zero = True in ( number_test.WantsZero() for number_test in number_tests )
            
            nonzero_tag_query_hash_ids = set()
            
            if is_zero or is_anything_but_zero or wants_zero:
                
                with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                    
                    self._AnalyzeTempTable( temp_table_name )
                    
                    nonzero_tag_query_hash_ids = self.modules_files_search_tags.GetHashIdsThatHaveTagsComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, hash_ids_table_name = temp_table_name, namespace_wildcard = namespace_wildcard, job_status = job_status )
                    
                    if is_zero:
                        
                        query_hash_ids.difference_update( nonzero_tag_query_hash_ids )
                        
                    
                    if is_anything_but_zero:
                        
                        query_hash_ids.intersection_update( nonzero_tag_query_hash_ids )
                        
                    
                
            
            if len( specific_number_tests ) > 0:
                
                hash_id_tag_counts = self.modules_files_search_tags.GetHashIdsAndNonZeroTagCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, query_hash_ids, namespace_wildcard = namespace_wildcard, job_status = job_status )
                
                good_tag_count_hash_ids = { hash_id for ( hash_id, count ) in hash_id_tag_counts if megalambda( count ) }
                
                if megalambda( 0 ): # files with zero count are needed
                    
                    zero_hash_ids = query_hash_ids.difference( nonzero_tag_query_hash_ids )
                    
                    good_tag_count_hash_ids.update( zero_hash_ids )
                    
                
                query_hash_ids.intersection_update( good_tag_count_hash_ids )
                
            
        
        if job_status.IsCancelled():
            
            return set()
            
        
        #
        
        if 'min_tag_as_number' in simple_preds:
            
            ( namespace_wildcard, num ) = simple_preds[ 'min_tag_as_number' ]
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                
                self._AnalyzeTempTable( temp_table_name )
                
                good_hash_ids = self.modules_files_search_tags.GetHashIdsThatHaveTagAsNumComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, namespace_wildcard, num, '>', hash_ids = query_hash_ids, hash_ids_table_name = temp_table_name, job_status = job_status )
                
            
            query_hash_ids.intersection_update( good_hash_ids )
            
        
        if 'max_tag_as_number' in simple_preds:
            
            ( namespace_wildcard, num ) = simple_preds[ 'max_tag_as_number' ]
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                
                self._AnalyzeTempTable( temp_table_name )
                
                good_hash_ids = self.modules_files_search_tags.GetHashIdsThatHaveTagAsNumComplexLocation( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, location_context, tag_context, namespace_wildcard, num, '<', hash_ids = query_hash_ids, hash_ids_table_name = temp_table_name, job_status = job_status )
                
            
            query_hash_ids.intersection_update( good_hash_ids )
            
        
        if job_status.IsCancelled():
            
            return set()
            
        
        #
        
        allowed_job_types = [ 'regex' ]
        
        query_hash_ids = self._DoSpecificKnownURLPreds( file_search_context, query_hash_ids, allowed_job_types )
        
        #
        
        return query_hash_ids
        
    
    def _DoAdvancedTagPredicate(
        self,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        job_status: ClientThreading.JobStatus,
        pred: ClientSearchPredicate.Predicate,
        query_hash_ids: set[ int ] | None
    ):
        
        ( service_key_or_none, tag_display_type, statuses, tag ) = pred.GetValue()
        
        if service_key_or_none is None:
            
            prime_search_tag_service_key = file_search_context.GetTagContext().service_key
            
        else:
            
            prime_search_tag_service_key = service_key_or_none
            
        
        if prime_search_tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            services = self.modules_services.GetServices( HC.REAL_TAG_SERVICES )
            
            search_tag_service_keys = [ service.GetServiceKey() for service in services ]
            
        else:
            
            search_tag_service_keys = ( prime_search_tag_service_key, )
            
        
        location_context = file_search_context.GetLocationContext()
        
        if query_hash_ids is None:
            
            result = self.modules_files_search_tags.GetHashIdsFromTagAdvanced(
                tag,
                tag_display_type,
                statuses,
                search_tag_service_keys,
                location_context,
                job_status = job_status
            )
            
        else:
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                
                self._AnalyzeTempTable( temp_table_name )
                
                result = self.modules_files_search_tags.GetHashIdsFromTagAdvanced(
                    tag,
                    tag_display_type,
                    statuses,
                    search_tag_service_keys,
                    location_context,
                    hash_ids = query_hash_ids,
                    hash_ids_table_name = temp_table_name,
                    job_status = job_status
                )
                
            
        
        return result
        
    
    def _DoAdvancedRatingPredicate( self, predicate: ClientSearchPredicate.Predicate, query_hash_ids: set[ int ] | None, job_status: ClientThreading.JobStatus | None = None ) -> set[ int ] | None:
        
        ( logical_operator, service_specifier_primary, service_specifier_secondary, rated ) = predicate.GetValue()
        
        if logical_operator == HC.LOGICAL_OPERATOR_ONLY:
            
            service_keys_primary = service_specifier_primary.GetSpecificKeys()
            
            service_keys_secondary = service_specifier_secondary.GetSpecificKeys().difference( service_keys_primary )
            
            # if rated, we are saying: ALL of PRIMARY have, NONE of remainder SECONDARY have
            # if not rated, we are saying: NONE of PRIMARY have, ALL of remainder SECONDARY have
            
            predicate_primary = ClientSearchPredicate.Predicate(
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING_ADVANCED,
                (
                    HC.LOGICAL_OPERATOR_ALL,
                    ClientServices.ServiceSpecifier( service_keys = service_keys_primary ),
                    ClientServices.ServiceSpecifier(),
                    rated
                )
            )
            
            predicate_secondary = ClientSearchPredicate.Predicate(
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING_ADVANCED,
                (
                    HC.LOGICAL_OPERATOR_ALL,
                    ClientServices.ServiceSpecifier( service_keys = service_keys_secondary ),
                    ClientServices.ServiceSpecifier(),
                    not rated
                )
            )
            
            # we have to do the 'rated' one first to establish query_hash_ids as a real thing (if it is currently None)
            if rated:
                
                ( first_predicate, second_predicate ) = ( predicate_primary, predicate_secondary )
                
            else:
                
                ( first_predicate, second_predicate ) = ( predicate_secondary, predicate_primary )
                
            
            query_hash_ids = self._DoAdvancedRatingPredicate( first_predicate, query_hash_ids, job_status = job_status )
            
            if job_status is not None and job_status.IsCancelled():
                
                return set()
                
            
            query_hash_ids = self._DoAdvancedRatingPredicate( second_predicate, query_hash_ids, job_status = job_status )
            
        else:
            
            if not rated and query_hash_ids is None:
                
                return set()
                
            
            cancelled_hook = None
            
            if job_status is not None:
                
                cancelled_hook = job_status.IsCancelled
                
            
            # could mount the query_hash_ids to a temp table here if we want, but most of the time I think this'll be fast
            
            service_types_to_ids = self.modules_services.GetServiceTypesToServiceIds( service_specifier_primary )
            
            star_service_ids = []
            star_service_ids.extend( service_types_to_ids.get( HC.LOCAL_RATING_LIKE, [] ) )
            star_service_ids.extend( service_types_to_ids.get( HC.LOCAL_RATING_NUMERICAL, [] ) )
            
            incdec_service_ids = service_types_to_ids.get( HC.LOCAL_RATING_INCDEC, [] )
            
            if logical_operator == HC.LOGICAL_OPERATOR_ANY:
                
                if rated:
                    
                    # the files that are rated anywhere, simple union
                    
                    result_hash_ids = set()
                    
                    if len( star_service_ids ) > 0:
                        
                        query = f'SELECT DISTINCT hash_id FROM local_ratings WHERE service_id IN {HydrusLists.SplayListForDB( star_service_ids )};'
                        
                        result_hash_ids.update( self._STI( self._ExecuteCancellable( query, (), cancelled_hook ) ) )
                        
                    
                    if len( incdec_service_ids ) > 0:
                        
                        query = f'SELECT DISTINCT hash_id FROM local_incdec_ratings WHERE service_id IN {HydrusLists.SplayListForDB( incdec_service_ids )} AND rating > 0;'
                        
                        result_hash_ids.update( self._STI( self._ExecuteCancellable( query, (), cancelled_hook ) ) )
                        
                    
                    query_hash_ids = intersection_update_qhi( query_hash_ids, result_hash_ids )
                    
                else:
                    
                    # the files that are not-rated anywhere, aka anything not rated everywhere
                    
                    predicate_exclusive = ClientSearchPredicate.Predicate(
                        ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING_ADVANCED,
                        (
                            HC.LOGICAL_OPERATOR_ALL,
                            service_specifier_primary,
                            service_specifier_secondary,
                            True
                        )
                    )
                    
                    undesired_hash_ids = self._DoAdvancedRatingPredicate( predicate_exclusive, set( query_hash_ids ), job_status = job_status )
                    
                    query_hash_ids.difference_update( undesired_hash_ids )
                    
                
            elif logical_operator == HC.LOGICAL_OPERATOR_ALL:
                
                if rated:
                    
                    # the files are rated everywhere, simple intersection
                    
                    result_hash_ids = None
                    
                    for service_id in star_service_ids:
                        
                        query = 'SELECT hash_id FROM local_ratings WHERE service_id = ?;'
                        
                        this_service_hash_ids = self._STS( self._ExecuteCancellable( query, ( service_id, ), cancelled_hook ) )
                        
                        if result_hash_ids is None:
                            
                            result_hash_ids = this_service_hash_ids
                            
                        else:
                            
                            result_hash_ids.intersection_update( this_service_hash_ids )
                            
                        
                    
                    for service_id in incdec_service_ids:
                        
                        query = 'SELECT hash_id FROM local_incdec_ratings WHERE service_id = ? AND rating > 0;'
                        
                        this_service_hash_ids = self._STS( self._ExecuteCancellable( query, ( service_id, ), cancelled_hook ) )
                        
                        if result_hash_ids is None:
                            
                            result_hash_ids = this_service_hash_ids
                            
                        else:
                            
                            result_hash_ids.intersection_update( this_service_hash_ids )
                            
                        
                    
                    if result_hash_ids is None:
                        
                        result_hash_ids = set()
                        
                    
                    query_hash_ids = intersection_update_qhi( query_hash_ids, result_hash_ids )
                    
                else:
                    
                    # the files are not-rated everywhere, i.e. anything not rated anywhere
                    
                    predicate_exclusive = ClientSearchPredicate.Predicate(
                        ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING_ADVANCED,
                        (
                            HC.LOGICAL_OPERATOR_ANY,
                            service_specifier_primary,
                            service_specifier_secondary,
                            True
                        )
                    )
                    
                    undesired_hash_ids = self._DoAdvancedRatingPredicate( predicate_exclusive, set( query_hash_ids ), job_status = job_status )
                    
                    query_hash_ids.difference_update( undesired_hash_ids )
                    
                
            
        
        return query_hash_ids
        
    
    def _DoAdvancedRatingPredicateExclusiveOnly( self, predicate: ClientSearchPredicate.Predicate, query_hash_ids: set[ int ], job_status: ClientThreading.JobStatus | None = None ) -> set[ int ]:
        
        ( logical_operator, service_specifier_primary, service_specifier_secondary, rated ) = predicate.GetValue()
        
        if not rated and logical_operator != HC.LOGICAL_OPERATOR_ONLY:
            
            query_hash_ids = self._DoAdvancedRatingPredicate( predicate, query_hash_ids, job_status = job_status )
            
        
        return query_hash_ids
        
    
    def _DoAdvancedRatingPredicateInclusiveOnly( self, predicate: ClientSearchPredicate.Predicate, query_hash_ids: set[ int ] | None, job_status: ClientThreading.JobStatus | None = None ) -> set[ int ] | None:
        
        ( logical_operator, service_specifier_primary, service_specifier_secondary, rated ) = predicate.GetValue()
        
        if rated or logical_operator == HC.LOGICAL_OPERATOR_ONLY:
            
            query_hash_ids = self._DoAdvancedRatingPredicate( predicate, query_hash_ids, job_status = job_status )
            
        
        return query_hash_ids
        
    
    def _DoNotePreds( self, system_predicates: ClientSearchFileSearchContext.FileSystemPredicates, query_hash_ids: set[ int ] | None, job_status: ClientThreading.JobStatus | None = None ) -> set[ int ] | None:
        
        simple_preds = system_predicates.GetSimpleInfo()
        
        number_tests = simple_preds.get( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_NOTES, [] )
        
        if len( number_tests ) > 0:
            
            with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                
                self._AnalyzeTempTable( temp_table_name )
                
                num_notes_hash_ids = self.modules_notes_map.GetHashIdsFromNumNotes( number_tests, query_hash_ids, temp_table_name, job_status = job_status )
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, num_notes_hash_ids )
                
            
        
        if 'has_note_names' in simple_preds:
            
            inclusive_note_names = simple_preds[ 'has_note_names' ]
            
            for note_name in inclusive_note_names:
                
                with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                    
                    self._AnalyzeTempTable( temp_table_name )
                    
                    notes_hash_ids = self.modules_notes_map.GetHashIdsFromNoteName( note_name, temp_table_name, job_status = job_status )
                    
                    query_hash_ids = intersection_update_qhi( query_hash_ids, notes_hash_ids )
                    
                
            
        
        if 'not_has_note_names' in simple_preds:
            
            exclusive_note_names = simple_preds[ 'not_has_note_names' ]
            
            for note_name in exclusive_note_names:
                
                with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                    
                    self._AnalyzeTempTable( temp_table_name )
                    
                    notes_hash_ids = self.modules_notes_map.GetHashIdsFromNoteName( note_name, temp_table_name, job_status = job_status )
                    
                    query_hash_ids.difference_update( notes_hash_ids )
                    
                
            
        
        return query_hash_ids
        
    
    def _DoOrPreds(
        self,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        job_status: ClientThreading.JobStatus | None,
        or_predicates: collections.abc.Collection[ ClientSearchPredicate.Predicate ],
        query_hash_ids: set[ int ] | None
    ) -> set[ int ] | None:
            
            # better typically to sort by fewest num of preds first, establishing query_hash_ids for longer chains
            def or_sort_key( p ):
                
                return len( p.GetValue() )
                
            
            or_predicates = sorted( or_predicates, key = or_sort_key )
            
            for or_predicate in or_predicates:
                
                # blue eyes OR green eyes
                
                or_query_hash_ids = set()
                
                or_subpredicates = or_predicate.GetValue()
                
                # [ blue eyes, green eyes ]
                
                for or_subpredicate in or_subpredicates:
                    
                    # blue eyes
                    
                    or_search_context = file_search_context.Duplicate()
                    
                    or_search_context.SetPredicates( [ or_subpredicate ] )
                    
                    # I pass query_hash_ids here to make these inefficient sub-searches (like -tag) potentially much faster
                    or_query_hash_ids.update( self.GetHashIdsFromQuery( or_search_context, job_status, query_hash_ids = query_hash_ids, apply_implicit_limit = False, sort_by = None, limit_sort_by = None ) )
                    
                    if job_status.IsCancelled():
                        
                        return set()
                        
                    
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, or_query_hash_ids )
                
            
            return query_hash_ids
            
        
    
    def _DoSimpleRatingPreds( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, query_hash_ids: set[ int ] | None, job_status: ClientThreading.JobStatus | None = None ) -> set[ int ] | None:
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        system_predicates = file_search_context.GetSystemPredicates()
        
        for ( operator, value, rating_service_key ) in system_predicates.GetRatingsPredicates():
            
            service_id = self.modules_services.GetServiceId( rating_service_key )
            
            if value == 'not rated':
                
                continue
                
            
            if value == 'rated':
                
                rating_hash_ids = self._STI( self._ExecuteCancellable( 'SELECT hash_id FROM local_ratings WHERE service_id = ?;', ( service_id, ), cancelled_hook ) )
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, rating_hash_ids )
                
            else:
                
                service = CG.client_controller.services_manager.GetService( rating_service_key )
                
                service_type = service.GetServiceType()
                
                if service_type in HC.STAR_RATINGS_SERVICES:
                    
                    if service.GetServiceType() == HC.LOCAL_RATING_LIKE:
                        
                        half_a_star_value = 0.5
                        
                    else:
                        
                        one_star_value = service.GetOneStarValue()
                        
                        half_a_star_value = one_star_value / 2
                        
                    
                    if isinstance( value, str ):
                        
                        value = float( value )
                        
                    
                    # floats are a pain! as is storing rating as 0.0-1.0 and then allowing number of stars to change!
                    
                    if operator == HC.UNICODE_APPROX_EQUAL:
                        
                        predicate = str( ( value - half_a_star_value ) * 0.8 ) + ' < rating AND rating < ' + str( ( value + half_a_star_value ) * 1.2 )
                        
                    elif operator == '<':
                        
                        predicate = 'rating <= ' + str( value - half_a_star_value )
                        
                    elif operator == '>':
                        
                        predicate = 'rating > ' + str( value + half_a_star_value )
                        
                    elif operator == '=':
                        
                        predicate = str( value - half_a_star_value ) + ' < rating AND rating <= ' + str( value + half_a_star_value )
                        
                    else:
                        
                        continue
                        
                    
                    query = f'SELECT hash_id FROM local_ratings WHERE service_id = ? AND {predicate};'
                    
                    rating_hash_ids = self._STI( self._ExecuteCancellable( query, ( service_id, ), cancelled_hook ) )
                    
                    query_hash_ids = intersection_update_qhi( query_hash_ids, rating_hash_ids )
                    
                elif service_type == HC.LOCAL_RATING_INCDEC:
                    
                    if operator == '<' or ( operator == '=' and value == 0 ):
                        
                        continue
                        
                    else:
                        
                        if operator == HC.UNICODE_APPROX_EQUAL:
                            
                            min_value = max( value - 1, int( value * 0.8 ) )
                            max_value = min( value + 1, int( value * 1.2 ) )
                            
                            predicate = '{} < rating AND rating < {}'.format( min_value, max_value )
                            
                        else:
                            
                            predicate = 'rating {} {}'.format( operator, value )
                            
                        
                        query = f'SELECT hash_id FROM local_incdec_ratings WHERE service_id = ? AND {predicate};'
                        
                        rating_hash_ids = self._STI( self._ExecuteCancellable( query, ( service_id, ), cancelled_hook ) )
                        
                        query_hash_ids = intersection_update_qhi( query_hash_ids, rating_hash_ids )
                        
                    
                
            
        
        return query_hash_ids
        
    
    def _DoSpecificKnownURLPreds( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, query_hash_ids: set[ int ] | None, allowed_rule_types: collections.abc.Collection[ str ] ) -> set[ int ] | None:
        
        system_predicates = file_search_context.GetSystemPredicates()
        
        is_inbox = system_predicates.MustBeInbox()
        
        simple_preds = system_predicates.GetSimpleInfo()
        
        if 'known_url_rules' in simple_preds:
            
            known_url_rules = list( simple_preds[ 'known_url_rules' ] )
            
            magic_sort_list = [
                'exact_match',
                'domain',
                'url_class',
                'url_match',
                'regex'
            ]
            
            def url_rules_key( row ):
                
                rule_type = row[1]
                
                if rule_type in magic_sort_list:
                    
                    return magic_sort_list.index( rule_type )
                    
                else:
                    
                    return 10
                    
                
            
            known_url_rules.sort( key = url_rules_key )
            
            for ( operator, rule_type, rule ) in known_url_rules:
                
                if rule_type not in allowed_rule_types:
                    
                    continue
                    
                
                if rule_type == 'exact_match' or ( is_inbox and len( query_hash_ids ) == len( self.modules_files_inbox.inbox_hash_ids ) ):
                    
                    url_hash_ids = self.modules_url_map.GetHashIdsFromURLRule( rule_type, rule )
                    
                else:
                    
                    with self._MakeTemporaryIntegerTable( query_hash_ids, 'hash_id' ) as temp_table_name:
                        
                        self._AnalyzeTempTable( temp_table_name )
                        
                        url_hash_ids = self.modules_url_map.GetHashIdsFromURLRule( rule_type, rule, hash_ids = query_hash_ids, hash_ids_table_name = temp_table_name )
                        
                    
                
                if operator: # inclusive
                    
                    query_hash_ids = intersection_update_qhi( query_hash_ids, url_hash_ids )
                    
                else:
                    
                    query_hash_ids.difference_update( url_hash_ids )
                    
                
            
        
        return query_hash_ids
        
    
    def _DoTimestampPreds( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, query_hash_ids: set[ int ] | None, search_state: SearchState, job_status: ClientThreading.JobStatus | None = None ) -> set[ int ] | None:
        
        system_predicates = file_search_context.GetSystemPredicates()
        
        location_context = file_search_context.GetLocationContext()
        not_all_known_files = not location_context.IsAllKnownFiles()
        
        system_pred_type_to_timestamp_ranges_ms = system_predicates.GetTimestampRangesMS()
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        if not_all_known_files:
            
            # in future we will hang an explicit locationcontext off this predicate
            # for now we'll check current domain
            # if domain is deleted, we search deletion time
            
            if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME in system_pred_type_to_timestamp_ranges_ms:
                
                import_timestamp_predicates = []
                
                timestamp_ranges_ms = system_pred_type_to_timestamp_ranges_ms[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME ]
                
                if '>' in timestamp_ranges_ms:
                    
                    import_timestamp_predicates.append( 'timestamp_ms >= {}'.format( timestamp_ranges_ms[ '>' ] ) )
                    
                
                if '<' in timestamp_ranges_ms:
                    
                    import_timestamp_predicates.append( 'timestamp_ms <= {}'.format( timestamp_ranges_ms[ '<' ] ) )
                    
                
                if len( import_timestamp_predicates ) > 0:
                    
                    pred_string = ' AND '.join( import_timestamp_predicates )
                    
                    table_names = []
                    
                    table_names.extend( ( ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.GetServiceId( service_key ), HC.CONTENT_STATUS_CURRENT ) for service_key in location_context.current_service_keys ) )
                    table_names.extend( ( ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.GetServiceId( service_key ), HC.CONTENT_STATUS_DELETED ) for service_key in location_context.deleted_service_keys ) )
                    
                    import_timestamp_hash_ids = set()
                    
                    for table_name in table_names:
                        
                        import_timestamp_hash_ids.update( self._STS( self._ExecuteCancellable( 'SELECT hash_id FROM {} WHERE {};'.format( table_name, pred_string ), (), cancelled_hook ) ) )
                        
                    
                    query_hash_ids = intersection_update_qhi( query_hash_ids, import_timestamp_hash_ids )
                    
                    search_state.have_cross_referenced_file_locations = True
                    
                
            
        
        if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME in system_pred_type_to_timestamp_ranges_ms:
            
            timestamp_ranges_ms = system_pred_type_to_timestamp_ranges_ms[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME ]
            
            if len( timestamp_ranges_ms ) > 0:
                
                modified_timestamp_hash_ids = self.modules_files_timestamps.GetHashIdsInRange( HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE, timestamp_ranges_ms, job_status = job_status )
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, modified_timestamp_hash_ids )
                
            
        
        if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME in system_pred_type_to_timestamp_ranges_ms:
            
            timestamp_ranges_ms = system_pred_type_to_timestamp_ranges_ms[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME ]
            
            if len( timestamp_ranges_ms ) > 0:
                
                archived_timestamp_hash_ids = self.modules_files_timestamps.GetHashIdsInRange( HC.TIMESTAMP_TYPE_ARCHIVED, timestamp_ranges_ms, job_status = job_status )
                
                query_hash_ids = intersection_update_qhi( query_hash_ids, archived_timestamp_hash_ids )
                
            
        
        if ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME in system_pred_type_to_timestamp_ranges_ms:
            
            timestamp_ranges_ms = system_pred_type_to_timestamp_ranges_ms[ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME ]
            
            min_last_viewed_timestamp_ms = timestamp_ranges_ms.get( '>', None )
            max_last_viewed_timestamp_ms = timestamp_ranges_ms.get( '<', None )
            
            last_viewed_time_hash_ids = self.modules_files_viewing_stats.GetHashIdsFromLastViewed( min_last_viewed_timestamp_ms = min_last_viewed_timestamp_ms, max_last_viewed_timestamp_ms = max_last_viewed_timestamp_ms, job_status = job_status )
            
            query_hash_ids = intersection_update_qhi( query_hash_ids, last_viewed_time_hash_ids )
            
        
        return query_hash_ids
        
    
    def GetHashIdsFromQuery(
        self,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        job_status: ClientThreading.JobStatus | None = None,
        query_hash_ids: set[ int ] | None = None,
        apply_implicit_limit: bool = True,
        sort_by: ClientMedia.MediaSort | None = None,
        limit_sort_by: ClientMedia.MediaSort | None = None
    ) -> list[ int ]:
        
        if job_status is None:
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
        
        if query_hash_ids is not None:
            
            query_hash_ids = set( query_hash_ids )
            
        
        system_predicates = file_search_context.GetSystemPredicates()
        
        system_limit = system_predicates.GetLimit( apply_implicit_limit = apply_implicit_limit )
        
        if system_limit == 0:
            
            return []
            
        
        location_context = file_search_context.GetLocationContext()
        tag_context = file_search_context.GetTagContext()
        
        tag_service_key = tag_context.service_key
        
        if location_context.IsEmpty():
            
            return []
            
        
        current_file_service_ids = set()
        
        for current_service_key in location_context.current_service_keys:
            
            try:
                
                current_file_service_id = self.modules_services.GetServiceId( current_service_key )
                
            except HydrusExceptions.DataMissing:
                
                HydrusData.ShowText( 'A file search query was run for a file service that does not exist! If you just removed a service, you might want to try checking the search and/or restarting the client.' )
                
                return []
                
            
            current_file_service_ids.add( current_file_service_id )
            
        
        deleted_file_service_ids = set()
        
        for deleted_service_key in location_context.deleted_service_keys:
            
            try:
                
                deleted_file_service_id = self.modules_services.GetServiceId( deleted_service_key )
                
            except HydrusExceptions.DataMissing:
                
                HydrusData.ShowText( 'A file search query was run for a file service that does not exist! If you just removed a service, you might want to try checking the search and/or restarting the client.' )
                
                return []
                
            
            deleted_file_service_ids.add( deleted_file_service_id )
            
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
        
        try:
            
            tag_service_id = self.modules_services.GetServiceId( tag_service_key )
            
        except HydrusExceptions.DataMissing:
            
            HydrusData.ShowText( 'A file search query was run for a tag service that does not exist! If you just removed a service, you might want to check the search and/or restart the client.' )
            
            return []
            
        
        tags_to_include = file_search_context.GetTagsToInclude()
        
        namespaces_to_include = file_search_context.GetNamespacesToInclude()
        
        wildcards_to_include = file_search_context.GetWildcardsToInclude()
        
        there_are_tags_to_search = len( tags_to_include ) > 0 or len( namespaces_to_include ) > 0 or len( wildcards_to_include ) > 0
        
        # ok, let's set up the big list of simple search preds
        
        or_predicates = file_search_context.GetORPredicates()
        
        done_or_predicates = len( or_predicates ) == 0
        
        done_files_info_predicates = False
        
        have_cross_referenced_file_locations = False
        
        files_info_predicates = GetFilesInfoPredicates( system_predicates )
        
        there_are_simple_files_info_preds_to_search_for = len( files_info_predicates ) > 0
        
        done_tricky_incdec_ratings = False
        
        search_state = SearchState(
            done_or_predicates,
            done_files_info_predicates,
            have_cross_referenced_file_locations,
            there_are_tags_to_search,
            there_are_simple_files_info_preds_to_search_for,
            done_tricky_incdec_ratings
        )
        
        # And now the search proper
        
        if search_state.DoOrPredsInFirstRound():
            
            query_hash_ids = self._DoOrPreds( file_search_context, job_status, or_predicates, query_hash_ids )
            
            search_state.NotifyDoneOrPreds()
            
            if job_status.IsCancelled():
                
                return []
                
            
        
        #
        
        query_hash_ids = self._Do1PreInclusiveTagPreds( file_search_context, job_status, query_hash_ids, db_location_context, search_state )
        
        if job_status.IsCancelled():
            
            return []
            
        
        # 
        
        query_hash_ids = self._Do2InclusiveTagPreds( file_search_context, job_status, query_hash_ids, search_state )
        
        if job_status.IsCancelled():
            
            return []
            
        
        #
        
        if search_state.DoOrPredsInSecondRound():
            
            query_hash_ids = self._DoOrPreds( file_search_context, job_status, or_predicates, query_hash_ids )
            
            search_state.NotifyDoneOrPreds()
            
            if job_status.IsCancelled():
                
                return []
                
            
        
        # now the simple preds and desperate last shot to populate query_hash_ids
        
        query_hash_ids = self._Do3FileInfoPreds( file_search_context, job_status, query_hash_ids, db_location_context, search_state )
        
        # at this point, query_hash_ids has something in it
        
        query_hash_ids = self._Do4InexpensivePostFileCrossReferencePreds( file_search_context, job_status, query_hash_ids, search_state )
        
        #
        
        if job_status.IsCancelled():
            
            return []
            
        
        #
        
        # OR round three--final chance to kick in, and the preferred one. query_hash_ids is now set, so this shouldn't be super slow for most scenarios
        if not search_state.done_or_predicates:
            
            query_hash_ids = self._DoOrPreds( file_search_context, job_status, or_predicates, query_hash_ids )
            
            search_state.NotifyDoneOrPreds()
            
            if job_status.IsCancelled():
                
                return []
                
            
        
        #
        
        query_hash_ids = self._Do5ExpensivePostFileCrossReferencePreds( file_search_context, job_status, query_hash_ids, db_location_context, search_state )
        
        if job_status.IsCancelled():
            
            return []
            
        
        #
        
        query_hash_ids = list( query_hash_ids )
        
        #
        
        we_are_applying_limit = system_limit is not None and system_limit < len( query_hash_ids )
        
        if we_are_applying_limit and limit_sort_by is not None and sort_by is None:
            
            sort_by = limit_sort_by
            
        
        did_sort = False
        
        if sort_by is not None and sort_by.CanSortAtDBLevel( location_context ):
            
            ( did_sort, query_hash_ids ) = self.TryToSortHashIds( location_context, query_hash_ids, sort_by )
            
        
        #
        
        if we_are_applying_limit:
            
            if not did_sort:
                
                query_hash_ids = random.sample( query_hash_ids, system_limit )
                
            else:
                
                query_hash_ids = query_hash_ids[:system_limit]
                
            
        
        return query_hash_ids
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def PopulateSearchIntoTempTable( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, temp_table_name: str, query_hash_ids = None ) -> list[ int ]:
        
        query_hash_ids = self.GetHashIdsFromQuery( file_search_context, apply_implicit_limit = False, query_hash_ids = query_hash_ids )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( hash_id ) VALUES ( ? );'.format( temp_table_name ), ( ( hash_id, ) for hash_id in query_hash_ids ) )
        
        self._AnalyzeTempTable( temp_table_name )
        
        return query_hash_ids
        
    
    def TryToSortHashIds( self, location_context: ClientLocation.LocationContext, hash_ids, sort_by: ClientMedia.MediaSort ):
        
        did_sort = False
        
        if not sort_by.CanSortAtDBLevel( location_context ):
            
            return ( did_sort, hash_ids )
            
        
        ( sort_metadata, sort_data ) = sort_by.sort_type
        sort_order = sort_by.sort_order
        
        query = None
        key = lambda x: 1
        reverse = False
        
        if sort_metadata == 'system':
            
            simple_sorts = [
                CC.SORT_FILES_BY_IMPORT_TIME,
                CC.SORT_FILES_BY_FILESIZE,
                CC.SORT_FILES_BY_DURATION,
                CC.SORT_FILES_BY_FRAMERATE,
                CC.SORT_FILES_BY_NUM_FRAMES,
                CC.SORT_FILES_BY_WIDTH,
                CC.SORT_FILES_BY_HEIGHT,
                CC.SORT_FILES_BY_RATIO,
                CC.SORT_FILES_BY_NUM_PIXELS,
                CC.SORT_FILES_BY_MEDIA_VIEWS,
                CC.SORT_FILES_BY_MEDIA_VIEWTIME,
                CC.SORT_FILES_BY_APPROX_BITRATE,
                CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP,
                CC.SORT_FILES_BY_LAST_VIEWED_TIME,
                CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP
            ]
            
            if sort_data in simple_sorts:
                
                if sort_data == CC.SORT_FILES_BY_IMPORT_TIME:
                    
                    if location_context.IsOneDomain() and location_context.IncludesCurrent():
                        
                        file_service_key = list( location_context.current_service_keys )[0]
                        
                    else:
                        
                        file_service_key = CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY
                        
                    
                    file_service_id = self.modules_services.GetServiceId( file_service_key )
                    
                    current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( file_service_id, HC.CONTENT_STATUS_CURRENT )
                    
                    query = 'SELECT hash_id, timestamp_ms FROM {temp_table} CROSS JOIN {current_files_table} USING ( hash_id );'.format( temp_table = '{temp_table}', current_files_table = current_files_table_name )
                    
                elif sort_data == CC.SORT_FILES_BY_FILESIZE:
                    
                    query = 'SELECT hash_id, size FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                    
                elif sort_data == CC.SORT_FILES_BY_DURATION:
                    
                    query = 'SELECT hash_id, duration FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                    
                elif sort_data == CC.SORT_FILES_BY_FRAMERATE:
                    
                    query = 'SELECT hash_id, num_frames, duration FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                    
                elif sort_data == CC.SORT_FILES_BY_NUM_FRAMES:
                    
                    query = 'SELECT hash_id, num_frames FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                    
                elif sort_data == CC.SORT_FILES_BY_WIDTH:
                    
                    query = 'SELECT hash_id, width FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                    
                elif sort_data == CC.SORT_FILES_BY_HEIGHT:
                    
                    query = 'SELECT hash_id, height FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                    
                elif sort_data == CC.SORT_FILES_BY_RATIO:
                    
                    query = 'SELECT hash_id, width, height FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                        
                elif sort_data == CC.SORT_FILES_BY_NUM_PIXELS:
                    
                    query = 'SELECT hash_id, width, height FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                    
                elif sort_data in ( CC.SORT_FILES_BY_MEDIA_VIEWS, CC.SORT_FILES_BY_MEDIA_VIEWTIME ):
                    
                    desired_canvas_types = CG.client_controller.new_options.GetIntegerList( 'file_viewing_stats_interesting_canvas_types' )
                    
                    desired_canvas_types_splayed = HydrusLists.SplayListForDB( desired_canvas_types )
                    
                    if sort_data == CC.SORT_FILES_BY_MEDIA_VIEWS:
                        
                        query = 'SELECT hash_id, views FROM {temp_table} CROSS JOIN file_viewing_stats USING ( hash_id ) WHERE canvas_type IN {desired_canvas_types_splayed};'.format( temp_table = '{temp_table}', desired_canvas_types_splayed = desired_canvas_types_splayed )
                        
                    else:
                        
                        query = 'SELECT hash_id, viewtime_ms FROM {temp_table} CROSS JOIN file_viewing_stats USING ( hash_id ) WHERE canvas_type IN {desired_canvas_types_splayed};'.format( temp_table = '{temp_table}', desired_canvas_types_splayed = desired_canvas_types_splayed )
                        
                    
                elif sort_data == CC.SORT_FILES_BY_APPROX_BITRATE:
                    
                    query = 'SELECT hash_id, duration, num_frames, size, width, height FROM {temp_table} CROSS JOIN files_info USING ( hash_id );'
                    
                elif sort_data == CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP:
                    
                    q1 = 'SELECT hash_id, file_modified_timestamp_ms FROM {temp_table} CROSS JOIN file_modified_timestamps USING ( hash_id )'
                    q2 = 'SELECT hash_id, file_modified_timestamp_ms FROM {temp_table} CROSS JOIN file_domain_modified_timestamps USING ( hash_id )'
                    
                    query = 'SELECT hash_id, MIN( file_modified_timestamp_ms ) FROM ( {} UNION {} ) GROUP BY hash_id;'.format( q1, q2 )
                    
                elif sort_data == CC.SORT_FILES_BY_LAST_VIEWED_TIME:
                    
                    query = 'SELECT hash_id, last_viewed_timestamp_ms FROM {temp_table} CROSS JOIN file_viewing_stats USING ( hash_id ) WHERE canvas_type = {canvas_type};'.format( temp_table = '{temp_table}', canvas_type = CC.CANVAS_MEDIA_VIEWER )
                    
                elif sort_data == CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP:
                    
                    query = 'SELECT hash_id, archived_timestamp_ms FROM {temp_table} CROSS JOIN archive_timestamps USING ( hash_id );'
                    
                
                if sort_data == CC.SORT_FILES_BY_IMPORT_TIME:
                    
                    def deal_with_none( x ):
                        
                        if x is None: return -1
                        else: return x
                        
                    
                    def key( row ):
                        
                        hash_id = row[0]
                        timestamp = row[1]
                        
                        # hash_id to differentiate files imported in the same second
                        
                        return ( deal_with_none( timestamp ), hash_id )
                        
                    
                elif sort_data == CC.SORT_FILES_BY_RATIO:
                    
                    def key( row ):
                        
                        width = row[1]
                        height = row[2]
                        
                        if width is None or height is None or width == 0 or height == 0:
                            
                            return -1
                            
                        else:
                            
                            return width / height
                            
                        
                    
                elif sort_data == CC.SORT_FILES_BY_FRAMERATE:
                    
                    def key( row ):
                        
                        num_frames = row[1]
                        duration_ms = row[2]
                        
                        if num_frames is None or duration_ms is None or num_frames <= 0 or duration_ms <= 0:
                            
                            return -1
                            
                        else:
                            
                            return num_frames / duration_ms
                            
                        
                    
                elif sort_data == CC.SORT_FILES_BY_NUM_PIXELS:
                    
                    def key( row ):
                        
                        width = row[1]
                        height = row[2]
                        
                        if width is None or height is None or width == 0 or height == 0:
                            
                            return -1
                            
                        else:
                            
                            return width * height
                            
                        
                    
                elif sort_data == CC.SORT_FILES_BY_APPROX_BITRATE:
                    
                    def key( row ):
                        
                        duration_ms = row[1]
                        num_frames = row[2]
                        size = row[3]
                        width = row[4]
                        height = row[5]
                        
                        if duration_ms is None or duration_ms == 0:
                            
                            if size is None or size == 0:
                                
                                duration_bitrate = -1
                                frame_bitrate = -1
                                
                            else:
                                
                                duration_bitrate = 0
                                
                                if width is None or height is None:
                                    
                                    frame_bitrate = 0
                                    
                                else:
                                    
                                    if size is None or size == 0 or width is None or width == 0 or height is None or height == 0:
                                        
                                        frame_bitrate = -1
                                        
                                    else:
                                        
                                        num_pixels = width * height
                                        
                                        frame_bitrate = size / num_pixels
                                        
                                    
                                
                            
                        else:
                            
                            if size is None or size == 0:
                                
                                duration_bitrate = -1
                                frame_bitrate = -1
                                
                            else:
                                
                                duration_bitrate = size / duration_ms
                                
                                if num_frames is None or num_frames == 0:
                                    
                                    frame_bitrate = 0
                                    
                                else:
                                    
                                    frame_bitrate = duration_bitrate / num_frames
                                    
                                
                            
                        
                        return ( duration_bitrate, frame_bitrate )
                        
                    
                else:
                    
                    key = lambda row: -1 if row[1] is None else row[1]
                    
                
                reverse = sort_order == CC.SORT_DESC
                
            elif sort_data == CC.SORT_FILES_BY_RANDOM:
                
                hash_ids = list( hash_ids )
                
                random.shuffle( hash_ids )
                
                did_sort = True
                
            elif sort_data == CC.SORT_FILES_BY_HASH:
                
                hash_ids_to_hashes = self.modules_hashes_local_cache.GetHashIdsToHashes( hash_ids = hash_ids )
                
                reverse = sort_order == CC.SORT_DESC
                
                hash_ids = sorted( hash_ids, key = lambda hash_id: hash_ids_to_hashes[ hash_id ], reverse = reverse )
                
                did_sort = True
                
            elif sort_data == CC.SORT_FILES_BY_PIXEL_HASH:
                
                with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                    
                    hash_ids_to_pixel_hashes = self.modules_similar_files.GetHashIdsToPixelHashes( temp_hash_ids_table_name )
                    
                
                hash_ids_to_pixel_hashes = { hash_id : pixel_hash for ( hash_id, pixel_hash ) in hash_ids_to_pixel_hashes.items() if pixel_hash is not None }
                
                missed_hash_ids = [ hash_id for hash_id in hash_ids if hash_id not in hash_ids_to_pixel_hashes ]
                
                reverse = sort_order == CC.SORT_DESC
                
                hash_ids = sorted( list( hash_ids_to_pixel_hashes.keys() ), key = lambda hash_id: hash_ids_to_pixel_hashes[ hash_id ], reverse = reverse )
                
                hash_ids.extend( missed_hash_ids )
                
                did_sort = True
                
            elif sort_data == CC.SORT_FILES_BY_BLURHASH:
                
                with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                    
                    hash_ids_to_blurhashes = self.modules_files_metadata_basic.GetHashIdsToBlurhashes( temp_hash_ids_table_name )
                    
                
                hash_ids_to_blurhashes = { hash_id : blurhash for ( hash_id, blurhash ) in hash_ids_to_blurhashes.items() if blurhash is not None }
                
                missed_hash_ids = [ hash_id for hash_id in hash_ids if hash_id not in hash_ids_to_blurhashes ]
                
                reverse = sort_order == CC.SORT_DESC
                
                hash_ids = sorted( list( hash_ids_to_blurhashes.keys() ), key = lambda hash_id: hash_ids_to_blurhashes[ hash_id ], reverse = reverse )
                
                hash_ids.extend( missed_hash_ids )
                
                did_sort = True
                
            elif sort_data in CC.AVERAGE_COLOUR_FILE_SORTS:
                
                with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                    
                    hash_ids_to_blurhashes = self.modules_files_metadata_basic.GetHashIdsToBlurhashes( temp_hash_ids_table_name )
                    
                
                hash_ids_to_blurhashes = { hash_id : blurhash for ( hash_id, blurhash ) in hash_ids_to_blurhashes.items() if blurhash is not None }
                
                missed_hash_ids = [ hash_id for hash_id in hash_ids if hash_id not in hash_ids_to_blurhashes ]
                
                reverse = sort_order == CC.SORT_DESC
                
                blurhash_converter = ClientMedia.GetBlurhashToSortableCall( sort_data )
                
                hash_ids = sorted( list( hash_ids_to_blurhashes.keys() ), key = lambda hash_id: blurhash_converter( hash_ids_to_blurhashes[ hash_id ], reverse ), reverse = reverse )
                
                hash_ids.extend( missed_hash_ids )
                
                did_sort = True
                
            
        
        if query is not None:
            
            with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                hash_ids_and_other_data = sorted( self._Execute( query.format( temp_table = temp_hash_ids_table_name ) ), key = key, reverse = reverse )
                
            
            original_hash_ids = set( hash_ids )
            
            hash_ids = [ row[0] for row in hash_ids_and_other_data ]
            
            # some stuff like media views won't have rows
            missing_hash_ids = original_hash_ids.difference( hash_ids )
            
            hash_ids.extend( missing_hash_ids )
            
            did_sort = True
            
        
        return ( did_sort, hash_ids )
        
    
