import itertools
import random
import sqlite3
import typing

from hydrus.core import HydrusData

from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesDuplicates
from hydrus.client.db import ClientDBFilesSearch
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBMediaResults
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext

from hydrus.client.media import ClientMediaResult

class ClientDBFilesDuplicatesFileSearch( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles,
        modules_files_duplicates: ClientDBFilesDuplicates.ClientDBFilesDuplicates,
        modules_files_query: ClientDBFilesSearch.ClientDBFilesQuery,
        modules_media_results: ClientDBMediaResults.ClientDBMediaResults
        ):
        
        super().__init__( 'client file duplicates file search', cursor )
        
        self.modules_files_storage = modules_files_storage
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_similar_files = modules_similar_files
        self.modules_files_duplicates = modules_files_duplicates
        self.modules_files_query = modules_files_query
        self.modules_media_results = modules_media_results
        
    
    def _GetAllKingHashIds( self, db_location_context: ClientDBFilesStorage.DBLocationContext ):
        
        if db_location_context.SingleTableIsFast():
            
            files_table_name = db_location_context.GetSingleFilesTableName()
            
            return self._STS( self._Execute( f'SELECT king_hash_id FROM duplicate_files CROSS JOIN {files_table_name} ON ( duplicate_files.king_hash_id = {files_table_name}.hash_id );' ) )
            
        
        return self._STS( self._Execute( 'SELECT king_hash_id FROM duplicate_files;' ) )
        
    
    def GetPotentialDuplicatePairsAndDistancesFragmentary( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsAndDistances ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsAndDistances:
        
        # we need to search the mass of potential duplicates using our search context, but we only want results from within the given pairs
        # to achieve this, we need two layers of clever fast filtering:
        # - in the join, we use a table of our given pairs instead of the whole potential_duplicate_pairs table to limit the search space
        # - file queries that prep the join are limited to the media_ids' king_hash_ids
        
        potential_duplicates_search_context = potential_duplicates_search_context.Duplicate()
        
        potential_duplicates_search_context.OptimiseForSearch()
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        dupe_search_type = potential_duplicates_search_context.GetDupeSearchType()
        pixel_dupes_preference = potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = potential_duplicates_search_context.GetMaxHammingDistance()
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( file_search_context_1.GetLocationContext() )
        
        #
        
        # OK so the conceit I went with in the end is simply substituting potential_duplicate_pairs with a temp table of our relevant pairs and letting the query planner's chips fall where they may
        # I threw in the ANALYZE to help the query planner navigate this. we'll see how it is IRL, fingers-crossed we win with three-row tables giving us insta-search
        # trying to insert a forced CROSS JOIN in dynamic join calls here is total wewmode, so tread carefully
        
        with self._MakeTemporaryIntegerTable( relevant_pairs_and_distances.GetRows(), ( 'smaller_media_id', 'larger_media_id', 'distance' ) ) as temp_media_ids_table_name:
            
            self._Execute( f'ANALYZE {temp_media_ids_table_name};')
            
            # TODO: If I am feeling clever I can break the following into a separate method and call that with the master potential pairs table and like all_media_ids = None and merge the GetPotentialDuplicatesCount monolithic call in, if we want it
            # if we want it! maybe it is only unit tests that care, and we should do something else
            
            with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_1:
                
                with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_2:
                    
                    if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                        
                        all_media_ids = set( itertools.chain.from_iterable( relevant_pairs_and_distances.GetPairs() ) )
                        
                        required_hash_ids = self.modules_files_duplicates.GetKingHashIds( db_location_context, all_media_ids )
                        
                        self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1, query_hash_ids = required_hash_ids )
                        self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_2, temp_table_name_2, query_hash_ids = required_hash_ids )
                        
                        self._Execute( f'ANALYZE {temp_table_name_1};')
                        self._Execute( f'ANALYZE {temp_table_name_2};')
                        
                        table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSeparateSearchResults( temp_table_name_1, temp_table_name_2, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                        
                    else:
                        
                        if ( file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates() ) and db_location_context.SingleTableIsFast():
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnEverythingSearchResults( db_location_context, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                            
                        else:
                            
                            all_media_ids = set( itertools.chain.from_iterable( relevant_pairs_and_distances.GetPairs() ) )
                            
                            required_hash_ids = self.modules_files_duplicates.GetKingHashIds( db_location_context, all_media_ids )
                            
                            self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1, query_hash_ids = required_hash_ids )
                            
                            self._Execute( f'ANALYZE {temp_table_name_1};')
                            
                            if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
                                
                                table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( temp_table_name_1, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                                
                            else:
                                
                                table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResults( db_location_context, temp_table_name_1, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                                
                            
                        
                    
                    # distinct important here for the search results table join
                    matching_pairs_and_distances = self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id, distance FROM {};'.format( table_join ) ).fetchall()
                    
                
            
        
        return ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsAndDistances( matching_pairs_and_distances )
        
    
    def GetPotentialDuplicatePairsFragmentaryMediaResults( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsAndDistances, duplicate_pair_sort_type: int, sort_asc: bool ):
        
        matching_potential_duplicate_pairs_and_distances = self.GetPotentialDuplicatePairsAndDistancesFragmentary( potential_duplicates_search_context, relevant_pairs_and_distances )
        
        all_media_ids = { media_id for pair in matching_potential_duplicate_pairs_and_distances.GetPairs() for media_id in pair }
        
        media_ids_to_king_hash_ids = { media_id : self.modules_files_duplicates.GetKingHashId( media_id ) for media_id in all_media_ids }
        
        handle_invalid = lambda i: 1 if i is None or i == 0 else i
        
        if duplicate_pair_sort_type == ClientDuplicates.DUPE_PAIR_SORT_SIMILARITY:
            
            def sort_key( pair: tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult ] ):
                
                ( m_r_1, m_r_2 ) = pair
                
                m_r_1_size = handle_invalid( m_r_1.GetSize() )
                m_r_2_size = handle_invalid( m_r_2.GetSize() )
                
                return max( m_r_1_size, m_r_2_size ) / min( m_r_1_size, m_r_2_size )
                
            
            lists_of_potential_duplicate_pairs = matching_potential_duplicate_pairs_and_distances.GetPairListsBySmallestDistanceFirst()
            
            lists_of_media_result_pairs = []
            
            for potential_duplicate_pairs in lists_of_potential_duplicate_pairs:
                
                pairs_of_hash_ids = [ ( media_ids_to_king_hash_ids[ smaller_media_id ], media_ids_to_king_hash_ids[ larger_media_id ] ) for ( smaller_media_id, larger_media_id ) in potential_duplicate_pairs ]
                
                media_result_pairs = sorted( self.modules_media_results.GetMediaResultPairs( pairs_of_hash_ids ), key = sort_key )
                
                lists_of_media_result_pairs.append( media_result_pairs )
                
            
            final_list_of_media_result_pairs = [ media_result_pair for media_result_pairs in lists_of_media_result_pairs for media_result_pair in media_result_pairs ]
            
        else:
            
            if duplicate_pair_sort_type == ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE:
                
                def sort_key( pair: tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult ] ):
                    
                    ( m_r_1, m_r_2 ) = pair
                    
                    m_r_1_size = handle_invalid( m_r_1.GetSize() )
                    m_r_2_size = handle_invalid( m_r_2.GetSize() )
                    
                    return ( max( m_r_1_size, m_r_2_size ), min( m_r_1_size, m_r_2_size ) )
                    
                
            elif duplicate_pair_sort_type == ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE:
                
                # what I would like auto-resolution to hook into
                
                def sort_key( pair: tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult ] ):
                    
                    ( m_r_1, m_r_2 ) = pair
                    
                    m_r_1_size = handle_invalid( m_r_1.GetSize() )
                    m_r_2_size = handle_invalid( m_r_2.GetSize() )
                    
                    return ( min( m_r_1_size, m_r_2_size ), max( m_r_1_size, m_r_2_size ) )
                    
                
            else:
                
                raise NotImplementedError( 'Did not understand that duplicate sort!' )
                
            
            matching_potential_duplicate_pairs = matching_potential_duplicate_pairs_and_distances.GetPairs()
            
            pairs_of_hash_ids = [ ( media_ids_to_king_hash_ids[ smaller_media_id ], media_ids_to_king_hash_ids[ larger_media_id ] ) for ( smaller_media_id, larger_media_id ) in matching_potential_duplicate_pairs ]
            
            final_list_of_media_result_pairs = sorted( self.modules_media_results.GetMediaResultPairs( pairs_of_hash_ids ), key = sort_key )
            
        
        if not sort_asc:
            
            final_list_of_media_result_pairs.reverse()
            
        
        return final_list_of_media_result_pairs
        
    
    def GetPotentialDuplicatePairHashesForFiltering( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, max_num_pairs: typing.Optional[ int ] = None ):
        
        all_potential_duplicate_pairs_and_distances = self.modules_files_duplicates.GetAllPotentialDuplicatePairsAndDistances()
        
        pair_results = []
        
        for block_of_potential_duplicate_paris_and_distances in all_potential_duplicate_pairs_and_distances.IterateBlocks():
            
            block_of_matching_media_results = self.GetPotentialDuplicatePairsFragmentaryMediaResults( potential_duplicates_search_context, block_of_potential_duplicate_paris_and_distances, ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE, False )
            
            for ( media_result_1, media_result_2 ) in block_of_matching_media_results:
                
                pair_results.append( ( media_result_1.GetHash(), media_result_2.GetHash() ) )
                
                if max_num_pairs is not None and len( pair_results ) >= max_num_pairs:
                    
                    return pair_results
                    
                
            
        
        return pair_results
        
    
    def GetPotentialDuplicatesCount( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
        all_potential_duplicate_pairs_and_distances = self.modules_files_duplicates.GetAllPotentialDuplicatePairsAndDistances()
        
        count = 0
        
        for block in all_potential_duplicate_pairs_and_distances.IterateBlocks():
            
            count += self.GetPotentialDuplicatesCountFragmentary( potential_duplicates_search_context, block )
            
        
        return count
        
    
    def GetPotentialDuplicatesCountFragmentary( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsAndDistances ) -> int:
        
        matching_potential_duplicate_pairs_and_distances = self.GetPotentialDuplicatePairsAndDistancesFragmentary( potential_duplicates_search_context, relevant_pairs_and_distances )
        
        return len( matching_potential_duplicate_pairs_and_distances )
        
    
    def GetRandomPotentialDuplicateHashes( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ) -> list[ bytes ]:
        
        # TODO: This guy feels ripe for a fragmentary update to reduce latency
        # however the later logic is crazy/old. maybe KISS wipe is the solution, or maybe we need a clever little hook after a fragmentary fetch loop
        
        potential_duplicates_search_context = potential_duplicates_search_context.Duplicate()
        
        potential_duplicates_search_context.OptimiseForSearch()
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        dupe_search_type = potential_duplicates_search_context.GetDupeSearchType()
        pixel_dupes_preference = potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = potential_duplicates_search_context.GetMaxHammingDistance()
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( file_search_context_1.GetLocationContext() )
        
        chosen_allowed_hash_ids = None
        chosen_preferred_hash_ids = None
        comparison_allowed_hash_ids = None
        comparison_preferred_hash_ids = None
        
        # first we get a sample of current potential pairs in the db, given our limiting search context
        
        with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_1:
            
            with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_2:
                
                if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                    
                    all_possible_king_hash_ids = self._GetAllKingHashIds( db_location_context )
                    
                    query_hash_ids_1 = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1, query_hash_ids = all_possible_king_hash_ids ) )
                    query_hash_ids_2 = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_2, temp_table_name_2, query_hash_ids = all_possible_king_hash_ids ) )
                    
                    self._Execute( f'ANALYZE {temp_table_name_1};')
                    self._Execute( f'ANALYZE {temp_table_name_2};')
                    
                    # we are going to say our 'master' king for the pair(s) returned here is always from search 1
                    chosen_allowed_hash_ids = query_hash_ids_1
                    comparison_allowed_hash_ids = query_hash_ids_2
                    
                    table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSeparateSearchResults( temp_table_name_1, temp_table_name_2, pixel_dupes_preference, max_hamming_distance )
                    
                else:
                    
                    if ( file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates() ) and db_location_context.SingleTableIsFast():
                        
                        table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnEverythingSearchResults( db_location_context, pixel_dupes_preference, max_hamming_distance )
                        
                    else:
                        
                        all_possible_king_hash_ids = self._GetAllKingHashIds( db_location_context )
                        
                        query_hash_ids = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1, query_hash_ids = all_possible_king_hash_ids ) )
                        
                        self._Execute( f'ANALYZE {temp_table_name_1};')
                        
                        if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
                            
                            chosen_allowed_hash_ids = query_hash_ids
                            comparison_allowed_hash_ids = query_hash_ids
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        else:
                            
                            # the master will always be one that matches the search, the comparison can be whatever
                            chosen_allowed_hash_ids = query_hash_ids
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResults( db_location_context, temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        
                    
                
                # ok let's not use a set here, since that un-weights medias that appear a lot, and we want to see common stuff more often
                potential_media_ids = []
                
                # distinct important here for the search results table join
                for ( smaller_media_id, larger_media_id ) in self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id FROM {};'.format( table_join ) ):
                    
                    potential_media_ids.append( smaller_media_id )
                    potential_media_ids.append( larger_media_id )
                    
                    if len( potential_media_ids ) >= 1000:
                        
                        break
                        
                    
                
                # now let's randomly select a file in these medias
                
                random.shuffle( potential_media_ids )
                
                chosen_media_id = None
                chosen_hash_id = None
                
                for potential_media_id in HydrusData.IterateListRandomlyAndFast( potential_media_ids ):
                    
                    best_king_hash_id = self.modules_files_duplicates.GetBestKingId( potential_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                    
                    if best_king_hash_id is not None:
                        
                        chosen_media_id = potential_media_id
                        chosen_hash_id = best_king_hash_id
                        
                        break
                        
                    
                
                if chosen_hash_id is None:
                    
                    return []
                    
                
                # I used to do self.modules_files_duplicates.GetFileHashesByDuplicateType here, but that gets _all_ potentials in the db context, even with allowed_hash_ids doing work it won't capture pixel hashes or duplicate distance that we searched above
                # so, let's search and make the list manually!
                
                comparison_hash_ids = []
                
                # distinct important here for the search results table join
                matching_pairs = self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id FROM {} AND ( smaller_media_id = ? OR larger_media_id = ? );'.format( table_join ), ( chosen_media_id, chosen_media_id ) ).fetchall()
                
                for ( smaller_media_id, larger_media_id ) in matching_pairs:
                    
                    if smaller_media_id == chosen_media_id:
                        
                        potential_media_id = larger_media_id
                        
                    else:
                        
                        potential_media_id = smaller_media_id
                        
                    
                    best_king_hash_id = self.modules_files_duplicates.GetBestKingId( potential_media_id, db_location_context, allowed_hash_ids = comparison_allowed_hash_ids, preferred_hash_ids = comparison_preferred_hash_ids )
                    
                    if best_king_hash_id is not None:
                        
                        comparison_hash_ids.append( best_king_hash_id )
                        
                    
                
                # might as well have some kind of order
                comparison_hash_ids.sort()
                
                results_hash_ids = [ chosen_hash_id ] + comparison_hash_ids
                
                return self.modules_hashes_local_cache.GetHashes( results_hash_ids )
                
            
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
