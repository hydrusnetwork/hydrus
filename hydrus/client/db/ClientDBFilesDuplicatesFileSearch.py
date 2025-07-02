import collections
import collections.abc
import itertools
import random
import sqlite3
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusLists

from hydrus.client import ClientGlobals as CG
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
        
    
    def GetPotentialDuplicatePairsFragmentary( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: collections.abc.Collection[ tuple[ int, int, int ] ] ):
        
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
        
        all_media_ids = set( itertools.chain.from_iterable( ( ( smaller_media_id, larger_media_id ) for ( smaller_media_id, larger_media_id, distance ) in relevant_pairs_and_distances ) ) )
        
        #
        
        # OK so the conceit I went with in the end is simply substituting potential_duplicate_pairs with a temp table of our relevant pairs and letting the query planner's chips fall where they may
        # I threw in the ANALYZE to help the query planner navigate this. we'll see how it is IRL, fingers-crossed we win with three-row tables giving us insta-search
        # trying to insert a forced CROSS JOIN in dynamic join calls here is total wewmode, so tread carefully
        
        with self._MakeTemporaryIntegerTable( relevant_pairs_and_distances, ( 'smaller_media_id', 'larger_media_id', 'distance' ) ) as temp_media_ids_table_name:
            
            self._Execute( f'ANALYZE {temp_media_ids_table_name};')
            
            # TODO: If I am feeling clever I can break the following into a separate method and call that with the master potential pairs table and like all_media_ids = None and merge the GetPotentialDuplicatesCount monolithic call in, if we want it
            # if we want it! maybe it is only unit tests that care, and we should do something else
            
            with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_1:
                
                with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_2:
                    
                    if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                        
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
                            
                            required_hash_ids = self.modules_files_duplicates.GetKingHashIds( db_location_context, all_media_ids )
                            
                            self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1, query_hash_ids = required_hash_ids )
                            
                            self._Execute( f'ANALYZE {temp_table_name_1};')
                            
                            if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
                                
                                table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( temp_table_name_1, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                                
                            else:
                                
                                table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResults( db_location_context, temp_table_name_1, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                                
                            
                        
                    
                    # distinct important here for the search results table join
                    matching_pairs = self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id FROM {};'.format( table_join ) ).fetchall()
                    
                
            
        
        return matching_pairs
        
    
    def GetPotentialDuplicatePairsFragmentaryMediaResults( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: collections.abc.Collection[ tuple[ int, int, int ] ] ):
        
        pairs_of_media_ids = self.GetPotentialDuplicatePairsFragmentary( potential_duplicates_search_context, relevant_pairs_and_distances )
        
        all_media_ids = set()
        
        for ( smaller_media_id, larger_media_id ) in pairs_of_media_ids:
            
            all_media_ids.add( smaller_media_id )
            all_media_ids.add( larger_media_id )
            
        
        media_ids_to_king_hash_ids = { media_id : self.modules_files_duplicates.GetKingHashId( media_id ) for media_id in all_media_ids }
        
        pairs_of_hash_ids = [ ( media_ids_to_king_hash_ids[ smaller_media_id ], media_ids_to_king_hash_ids[ larger_media_id ] ) for ( smaller_media_id, larger_media_id ) in pairs_of_media_ids ]
        
        return self.modules_media_results.GetMediaResultPairs( pairs_of_hash_ids )
        
    
    def GetPotentialDuplicatePairsForFiltering( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, max_num_pairs: typing.Optional[ int ] = None ):
        
        # TODO: This guy feels ripe for a fragmentary update to reduce latency
        # however the later logic is crazy/old. maybe KISS wipe is the solution, or maybe we need a clever little hook after a fragmentary fetch loop
        
        if max_num_pairs is None:
            
            max_num_pairs = CG.client_controller.new_options.GetInteger( 'duplicate_filter_max_batch_size' )
            
        
        potential_duplicates_search_context = potential_duplicates_search_context.Duplicate()
        
        potential_duplicates_search_context.OptimiseForSearch()
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        dupe_search_type = potential_duplicates_search_context.GetDupeSearchType()
        pixel_dupes_preference = potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = potential_duplicates_search_context.GetMaxHammingDistance()
        
        # we need to batch non-intersecting decisions here to keep it simple at the gui-level
        # we also want to maximise per-decision value
        
        # now we will fetch some unknown pairs
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( file_search_context_1.GetLocationContext() )
        
        chosen_allowed_hash_ids = None
        chosen_preferred_hash_ids = None
        comparison_allowed_hash_ids = None
        comparison_preferred_hash_ids = None
        
        with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_1:
            
            with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_2:
                
                if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                    
                    all_possible_king_hash_ids = self._GetAllKingHashIds( db_location_context )
                    
                    query_hash_ids_1 = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1, query_hash_ids = all_possible_king_hash_ids ) )
                    query_hash_ids_2 = set( self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_2, temp_table_name_2, query_hash_ids = all_possible_king_hash_ids ) )
                    
                    self._Execute( f'ANALYZE {temp_table_name_1};')
                    self._Execute( f'ANALYZE {temp_table_name_2};')
                    
                    # we always want pairs where one is in one and the other is in the other, we don't want king-selection-trickery giving us a jpeg vs a jpeg
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
                            
                            # both chosen and comparison must be in the search, no king selection nonsense allowed
                            chosen_allowed_hash_ids = query_hash_ids
                            comparison_allowed_hash_ids = query_hash_ids
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        else:
                            
                            # one file matches the search
                            chosen_allowed_hash_ids = query_hash_ids
                            
                            table_join = self.modules_files_duplicates.GetPotentialDuplicatePairsTableJoinOnSearchResults( db_location_context, temp_table_name_1, pixel_dupes_preference, max_hamming_distance )
                            
                        
                    
                
                # distinct important here for the search results table join
                result = self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id, distance FROM {} LIMIT 2500;'.format( table_join ) ).fetchall()
                
            
        
        batch_of_pairs_of_media_ids = []
        seen_media_ids = set()
        
        distances_to_pairs = HydrusData.BuildKeyToListDict( ( ( distance, ( smaller_media_id, larger_media_id ) ) for ( smaller_media_id, larger_media_id, distance ) in result ) )
        
        distances = sorted( distances_to_pairs.keys() )
        
        # we want to preference pairs that have the smallest distance between them. deciding on more similar files first helps merge dupes before dealing with alts so reduces potentials more quickly
        for distance in distances:
            
            result_pairs_for_this_distance = distances_to_pairs[ distance ]
            
            # convert them into possible groups per each possible 'master hash_id', and value them
            
            master_media_ids_to_groups = collections.defaultdict( list )
            
            for pair in result_pairs_for_this_distance:
                
                ( smaller_media_id, larger_media_id ) = pair
                
                master_media_ids_to_groups[ smaller_media_id ].append( pair )
                master_media_ids_to_groups[ larger_media_id ].append( pair )
                
            
            master_hash_ids_to_values = collections.Counter()
            
            for ( media_id, pairs ) in master_media_ids_to_groups.items():
                
                # negative so we later serve up smallest groups first
                # we shall say for now that smaller groups are more useful to front-load because it lets us solve simple problems first
                master_hash_ids_to_values[ media_id ] = - len( pairs )
                
            
            # now let's add decision groups to our batch
            # we exclude hashes we have seen before in each batch so we aren't treading over ground that was implicitly solved by a previous decision in the batch
            
            for ( master_media_id, count ) in master_hash_ids_to_values.most_common():
                
                if master_media_id in seen_media_ids:
                    
                    continue
                    
                
                seen_media_ids_for_this_master_media_id = set()
                
                for pair in master_media_ids_to_groups[ master_media_id ]:
                    
                    ( smaller_media_id, larger_media_id ) = pair
                    
                    if smaller_media_id in seen_media_ids or larger_media_id in seen_media_ids:
                        
                        continue
                        
                    
                    seen_media_ids_for_this_master_media_id.add( smaller_media_id )
                    seen_media_ids_for_this_master_media_id.add( larger_media_id )
                    
                    batch_of_pairs_of_media_ids.append( pair )
                    
                    if len( batch_of_pairs_of_media_ids ) >= max_num_pairs:
                        
                        break
                        
                    
                
                seen_media_ids.update( seen_media_ids_for_this_master_media_id )
                
                if len( batch_of_pairs_of_media_ids ) >= max_num_pairs:
                    
                    break
                    
                
            
            if len( batch_of_pairs_of_media_ids ) >= max_num_pairs:
                
                break
                
            
        
        seen_hash_ids = set()
        
        batch_of_pairs_of_hash_ids = []
        
        if chosen_allowed_hash_ids == comparison_allowed_hash_ids and chosen_preferred_hash_ids == comparison_preferred_hash_ids:
            
            # which file was 'chosen' vs 'comparison' is irrelevant. the user is expecting to see a mix, so we want the best kings possible. this is probably 'system:everything' or similar
            
            for ( smaller_media_id, larger_media_id ) in batch_of_pairs_of_media_ids:
                
                best_smaller_king_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                best_larger_king_hash_id = self.modules_files_duplicates.GetBestKingId( larger_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                
                if best_smaller_king_hash_id is not None and best_larger_king_hash_id is not None:
                    
                    batch_of_pairs_of_hash_ids.append( ( best_smaller_king_hash_id, best_larger_king_hash_id ) )
                    
                    seen_hash_ids.update( ( best_smaller_king_hash_id, best_larger_king_hash_id ) )
                    
                
            
        else:
            
            # we want to enforce that our pairs seem human. if the user said 'A is in search 1 and B is in search 2', we don't want king selection going funny and giving us two from 1
            # previously, we did this on media_ids on their own, but we have to do it in pairs. we choose the 'chosen' and 'comparison' of our pair and filter accordingly
            
            for ( smaller_media_id, larger_media_id ) in batch_of_pairs_of_media_ids:
                
                best_smaller_king_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                best_larger_king_hash_id = self.modules_files_duplicates.GetBestKingId( larger_media_id, db_location_context, allowed_hash_ids = comparison_allowed_hash_ids, preferred_hash_ids = comparison_preferred_hash_ids )
                
                if best_smaller_king_hash_id is None or best_larger_king_hash_id is None:
                    
                    # ok smaller was probably the comparison, let's see if that produces a better king hash
                    
                    best_smaller_king_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context, allowed_hash_ids = comparison_allowed_hash_ids, preferred_hash_ids = comparison_preferred_hash_ids )
                    best_larger_king_hash_id = self.modules_files_duplicates.GetBestKingId( larger_media_id, db_location_context, allowed_hash_ids = chosen_allowed_hash_ids, preferred_hash_ids = chosen_preferred_hash_ids )
                    
                
                if best_smaller_king_hash_id is not None and best_larger_king_hash_id is not None:
                    
                    batch_of_pairs_of_hash_ids.append( ( best_smaller_king_hash_id, best_larger_king_hash_id ) )
                    
                    seen_hash_ids.update( ( best_smaller_king_hash_id, best_larger_king_hash_id ) )
                    
                
            
        
        media_results = self.modules_media_results.GetMediaResults( seen_hash_ids )
        
        hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
        
        batch_of_pairs_of_media_results = [ ( hash_ids_to_media_results[ hash_id_a ], hash_ids_to_media_results[ hash_id_b ] ) for ( hash_id_a, hash_id_b ) in batch_of_pairs_of_hash_ids ]
        
        return batch_of_pairs_of_media_results
        
    
    def GetPotentialDuplicatesCount( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
        all_potential_duplicate_pairs_and_distances = self.modules_files_duplicates.GetAllPotentialDuplicatePairsAndDistances()
        
        count = 0
        
        for block in HydrusLists.SplitListIntoChunks( all_potential_duplicate_pairs_and_distances, 4096 ):
            
            count += self.GetPotentialDuplicatesCountFragmentary( potential_duplicates_search_context, block )
            
        
        return count
        
    
    def GetPotentialDuplicatesCountFragmentary( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, relevant_pairs_and_distances: collections.abc.Collection[ tuple[ int, int, int ] ] ):
        
        pairs_of_media_ids = self.GetPotentialDuplicatePairsFragmentary( potential_duplicates_search_context, relevant_pairs_and_distances )
        
        return len( pairs_of_media_ids )
        
    
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
        
    
