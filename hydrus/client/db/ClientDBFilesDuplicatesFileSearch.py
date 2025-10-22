import itertools
import random
import sqlite3
import typing

from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesDuplicates
from hydrus.client.db import ClientDBFilesSearch
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBMediaResults
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext

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
        
    
    def GetPotentialDuplicateIdPairsAndDistancesFragmentary( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances:
        
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
                    
                
            
        
        return ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( matching_pairs_and_distances )
        
    
    def GetPotentialDuplicateMediaResultPairsAndDistancesFragmentary( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances, no_more_than = None ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances:
        
        matching_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicates_search_context, relevant_pairs_and_distances )
        
        rows = matching_potential_duplicate_id_pairs_and_distances.GetRows()
        
        if no_more_than is not None:
            
            rows = rows[ : no_more_than ]
            
        
        pairs = [ ( smaller_media_id, larger_media_id ) for ( smaller_media_id, larger_media_id, distance ) in rows ]
        
        all_media_ids = { media_id for pair in pairs for media_id in pair }
        
        media_ids_to_king_hash_ids = { media_id : self.modules_files_duplicates.GetKingHashId( media_id ) for media_id in all_media_ids }
        
        media_results = self.modules_media_results.GetMediaResults( set( media_ids_to_king_hash_ids.values() ) )
        
        hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
        
        matching_potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances(
            [ ( hash_ids_to_media_results[ media_ids_to_king_hash_ids[ smaller_media_id ] ], hash_ids_to_media_results[ media_ids_to_king_hash_ids[ larger_media_id ] ], distance ) for ( smaller_media_id, larger_media_id, distance ) in rows ]
        )
        
        return matching_potential_duplicate_media_result_pairs_and_distances
        
    
    def GetPotentialDuplicatePairHashesForFiltering( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, max_num_pairs: typing.Optional[ int ] = None ):
        
        potential_duplicate_id_pairs_and_distances = self.modules_files_duplicates.GetPotentialDuplicateIdPairsAndDistances( potential_duplicates_search_context.GetFileSearchContext1().GetLocationContext() )
        
        pair_results = []
        
        for block_of_potential_duplicate_id_pairs_and_distances in potential_duplicate_id_pairs_and_distances.IterateBlocks():
            
            potential_duplicate_media_result_pairs_and_distances = self.GetPotentialDuplicateMediaResultPairsAndDistancesFragmentary( potential_duplicates_search_context, block_of_potential_duplicate_id_pairs_and_distances )
            
            potential_duplicate_media_result_pairs_and_distances.Sort( ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE, False )
            
            for ( media_result_1, media_result_2 ) in potential_duplicate_media_result_pairs_and_distances.GetPairs():
                
                pair_results.append( ( media_result_1.GetHash(), media_result_2.GetHash() ) )
                
                if max_num_pairs is not None and len( pair_results ) >= max_num_pairs:
                    
                    return pair_results
                    
                
            
        
        return pair_results
        
    
    def GetPotentialDuplicatesCount( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
        potential_duplicate_id_pairs_and_distances = self.modules_files_duplicates.GetPotentialDuplicateIdPairsAndDistances( potential_duplicates_search_context.GetFileSearchContext1().GetLocationContext() )
        
        count = 0
        
        for block in potential_duplicate_id_pairs_and_distances.IterateBlocks():
            
            count += self.GetPotentialDuplicatesCountFragmentary( potential_duplicates_search_context, block )
            
        
        return count
        
    
    def GetPotentialDuplicatesCountFragmentary( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances ) -> int:
        
        matching_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicates_search_context, relevant_pairs_and_distances )
        
        return len( matching_potential_duplicate_id_pairs_and_distances )
        
    
    def GetRandomPotentialDuplicateGroupHashes( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ) -> list[ bytes ]:
        
        potential_duplicate_id_pairs_and_distances = self.modules_files_duplicates.GetPotentialDuplicateIdPairsAndDistances( potential_duplicates_search_context.GetFileSearchContext1().GetLocationContext() )
        
        potential_duplicate_id_pairs_and_distances.RandomiseForRichEstimate()
        
        master_media_id = None
        
        for block in potential_duplicate_id_pairs_and_distances.IterateBlocks():
            
            matching_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicates_search_context, block )
            
            if len( matching_potential_duplicate_id_pairs_and_distances ) > 0:
                
                rows = matching_potential_duplicate_id_pairs_and_distances.GetRows()
                
                row = random.choice( rows )
                
                master_media_id = row[0]
                
                break
                
            
        
        if master_media_id is None:
            
            return []
            
        
        # ok we have selected a random guy that fits the search. we know there is at least one pair, so let's now get his whole group
        
        # a small wew moment here is that if any link in the group is not present in the search context, we nonetheless deliver the two separate sections of the chain--let's see how often that is an issue
        group_potential_duplicate_id_pairs_and_distances = potential_duplicate_id_pairs_and_distances.FilterWiderPotentialGroup( ( master_media_id, ) )
        
        group_matching_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicates_search_context, group_potential_duplicate_id_pairs_and_distances )
        
        all_media_ids = { media_id for pair in group_matching_potential_duplicate_id_pairs_and_distances.GetPairs() for media_id in pair }
        
        media_ids_to_king_hash_ids = { media_id : self.modules_files_duplicates.GetKingHashId( media_id ) for media_id in all_media_ids }
        
        hashes = self.modules_hashes_local_cache.GetHashes( list( media_ids_to_king_hash_ids.values() ) )
        
        return hashes
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
