import itertools
import random
import sqlite3

from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusData
from hydrus.core import HydrusTime

from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesDuplicatesStorage
from hydrus.client.db import ClientDBFilesDuplicatesUpdates
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
        modules_files_duplicates_storage: ClientDBFilesDuplicatesStorage.ClientDBFilesDuplicatesStorage,
        modules_files_duplicates_updates: ClientDBFilesDuplicatesUpdates.ClientDBFilesDuplicatesUpdates,
        modules_files_query: ClientDBFilesSearch.ClientDBFilesQuery,
        modules_media_results: ClientDBMediaResults.ClientDBMediaResults
        ):
        
        super().__init__( 'client file duplicates file search', cursor )
        
        self.modules_files_storage = modules_files_storage
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_similar_files = modules_similar_files
        self.modules_files_duplicates_storage = modules_files_duplicates_storage
        self.modules_files_duplicates_updates = modules_files_duplicates_updates
        self.modules_files_query = modules_files_query
        self.modules_media_results = modules_media_results
        
    
    def _GetAllKingHashIds( self, db_location_context: ClientDBFilesStorage.DBLocationContext ):
        
        if db_location_context.SingleTableIsFast():
            
            files_table_name = db_location_context.GetSingleFilesTableName()
            
            return self._STS( self._Execute( f'SELECT king_hash_id FROM duplicate_files CROSS JOIN {files_table_name} ON ( duplicate_files.king_hash_id = {files_table_name}.hash_id );' ) )
            
        
        return self._STS( self._Execute( 'SELECT king_hash_id FROM duplicate_files;' ) )
        
    
    def GetPotentialDuplicateIdPairsAndDistances( self, potential_duplicate_pairs_fragmentary_search: ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances:
        
        matching_potential_duplicate_id_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( [] )
        
        while not potential_duplicate_pairs_fragmentary_search.SearchDone():
            
            matching_potential_duplicate_id_pairs_and_distances.Merge(
                self.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicate_pairs_fragmentary_search )
            )
            
        
        return matching_potential_duplicate_id_pairs_and_distances
        
    
    def GetPotentialDuplicateIdPairsAndDistancesFragmentary( self, potential_duplicate_pairs_fragmentary_search: ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances:
        
        do_report_mode = HG.potential_duplicates_report_mode
        
        # every single part of the fragementary search goes through this method at some point. it alters the fragmentary search in ways the caller cannot predict but will react to (e.g. just chips away or completes immediately)
        
        # we need to search the mass of potential duplicates using our search context, but we only want results from within the given pairs
        # to achieve this, we need two layers of clever fast filtering:
        # - in the join, we use a table of our given pairs instead of the whole potential_duplicate_pairs table to limit the search space
        # - file queries that prep the join are limited to the media_ids' king_hash_ids
        
        do_file_based_search = False
        
        if potential_duplicate_pairs_fragmentary_search.DoingFileBasedSearchIsOK() and potential_duplicate_pairs_fragmentary_search.ThisAppearsToHaveAHitRateLowerThan( 0.01 ):
            
            # we are confident we have a decent sample on a decent sized search and it is showing a low hitrate
            
            estimated_num_potential_based_rows_remaining = potential_duplicate_pairs_fragmentary_search.EstimatedNumRowsStillToSearch()
            
            estimated_num_file_search_based_hits_total = max( potential_duplicate_pairs_fragmentary_search.EstimatedNumHits(), 1 )
            
            # some quick and dirty profiling gave this very generous number, but it was pretty gonk because it was a small dev machine (15,000 rows) where everything was already in memory
            # often 4-8us per potential row
            # 1-4ms per file hit
            # 
            # OK, here is real world data from rich clients:
            # 20us per uncached potential row
            # 1.5-15ms per file hit
            # this still equals ~500x, so great stuff
            #
            # there are still numerous problems with this since we aren't capturing overhead costs per job and edge case file results will have very large result counts and all that (one dude had 29s per file hit, let's go), but there we go
            how_many_potential_rows_of_work_to_do_one_file_hit = 500
            
            if do_report_mode:
                
                HydrusData.Print( f'This does appear to be a low hit-rate search, and the magic weights are: {estimated_num_file_search_based_hits_total * how_many_potential_rows_of_work_to_do_one_file_hit} versus {estimated_num_potential_based_rows_remaining}')
                
            
            if estimated_num_file_search_based_hits_total * how_many_potential_rows_of_work_to_do_one_file_hit < estimated_num_potential_based_rows_remaining:
                
                do_file_based_search = True
                
            
        
        if do_report_mode:
            
            time_started = HydrusTime.GetNowPrecise()
            
        
        potential_duplicates_search_context = potential_duplicate_pairs_fragmentary_search.GetPotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context = potential_duplicates_search_context.Duplicate()
        
        potential_duplicates_search_context.OptimiseForSearch()
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        dupe_search_type = potential_duplicates_search_context.GetDupeSearchType()
        pixel_dupes_preference = potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = potential_duplicates_search_context.GetMaxHammingDistance()
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( file_search_context_1.GetLocationContext() )
        
        #
        
        with self._MakeTemporaryIntegerTable( [], ( 'smaller_media_id', 'larger_media_id', 'distance' ) ) as temp_media_ids_table_name:
            
            with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_1:
                
                with self._MakeTemporaryIntegerTable( [], 'hash_id' ) as temp_table_name_2:
                    
                    if do_file_based_search:
                        
                        # ▓▓▓▓█▓█▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓█████▓██▓▒▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓██ ▒█▓▓▓▓▓▓▓▓▓░▒█▓▓█
                        # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█  ▓▓▓▓▓▓▓▓▓▓ ░▓▓▓▓
                        # █▓▓▓▓▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓▒░▒▒░ ▒▒ ▒▒▒▒▓▓▓▓▓▓▓██▓█▓▓▓▓█  █▓█▓▓▓▓▓▓▓▒░█▓▓█
                        # █▓▓█▓▓▓█▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒ ▒▒░▒▒▒▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓█░ ▓▓▓▓▓▓▓▓▓▓▒▒▓▓▓█
                        # █▓█▓█▓█▓█▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓░▓▒░▒▓▓▓▓█▓███████████████▓█▓▓▓▓▓█▓▓▓▓█▒ ▓▓█▓█▓█▓▓▓▒ ▓▓▓█
                        # ▓███▓█▓█▓█████▓▓▓▓▓██▓▓▓▓▓▓▒▓▓▓███████▓▓▓██▓▓▓▓███▓█▓█▓███▓▓▓▓▓▓▓█▒ ▓███▓██▓▓▓▒▒▓▓▓█
                        # █▓███▓█████▓███▓█▓█▓▓▓▓▓▓▓▓▓▓████▓▓▓▓▓▓▓▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓ ▓█▓▓▓▓▓▓▓▓▓▓▓▓▓█
                        # ██████████▓▓▓▓▓█▓█▓▓▓▓▓▓▓▓▓▓▒▓██▓▓▓▓▓▓▓▓▒▒░▒▒▒░░ ▓▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓▓█▓▒▒▓▓▓▓▓█▓▓▓▓▓▓
                        # █▓██████▓▓▓▓▓▒▒▓█▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▒  ▒▓▓▓▓▓▓▓▓▓█▒▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▓▓█▓▓▓▓▓
                        # ███████▓▒▒▒▒▒▒▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓█▓▓▓████▓▒▒▓███▓█▓█▓█▓▒▓▓▓▓▓▓▓▓▓██▓▒▒▒▒▒▒▒▓██▓█▓▓
                        # ▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▓███▓█▓▓▓▓▓▓▓▓▒▓█████████████████████████▓▒▓█▓▓▓▓▓▓█▓▓▓▓▒▒▒▒▒▒▓▓██▓█▓
                        # ▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▓▓██▓▓██▓▓▓▓█▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▓███▓▓▓▓▓▓▓▓▓▓▓▒▓▒▒▓█▓█▓▓
                        # █▓▓▓▓▓▓▒▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓█████▓▓▒░░▒▓▒░▒▓▒▒▒▒░░░▓▒░▒▓▒▒▒▒▒▓▓▓▓███▓▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓█▓█▓
                        # ▓▓▓█▓█▓▓▒▓▓▓▓▓██▓▓▓▓▓▓▓▓▓███▓▒░░▒▓▓▒▒▓▒▓▒▓▒▒▒▒▒▓▒▒▓▓▒▓▒▓▒▓▓▓▓███▓▓▓▓▓▓▓███▓▓▓▓▓█▓█▓▓
                        # █████▓▓▓▓▓▓████▓▓▓█▓▓▓▓████▓▒▒▒▒▓▓▒▒▓▓▓▒▒▓▒▒▒▒▒▓▒░▓▓▒▒▒▓▓▒▒▓█████▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▓
                        # ████▓▓▓█████▓▓▓███▓█▓▓▓████▓▒▓▓▓▒▓▒▓▓▒▓▒▒▓▒▒▒▒▒▒▒▒▓▓▒▒▒▒▓▓▒▓██████▓▓▓███▓▓▓▓▓▓▓▓▓▓▓▓
                        # █████▓█████▓▓▓█████▓▓▓█████▓▒▒▒▓▓▒▓▓▓▒▓▒▒▒▓▒▒▓▓▒▓▒▓▓▓▒▓▓▓▓▓▓▓▓███▓█▓█████████▓▓▓▓▓▓▓
                        # ▓▓▓███████▓███████████████▓▒▒▒▓▓▒▒▓▓▒▓▓▓▓▓▓▓▒▒▒▓▓▓▓▓▓▓▒▓▒▓▒▒▒▒██████▓▓▓███████████▓▓
                        # ▓▓███▓███████████▓███████▓▓▒▒▒▓▒▒▓▓▓▓▓▓▒▒▒▒▒▒▒▓▒▓▓▓▓▓▓▒▓▓▒▓▒▒▒▓██████████▓█████████▓
                        # ▓███████████▓███████████▒▓▓▓▒▓▓▒▓▓▓▓▓▓▓▓▒▓▒▓▓▓▒▒▒▓▓▓▓▓▓▓▓▓▓▒▒▒▒▓████████████▓██████▓
                        # █████████▓███████████▓▓▓▒▓▓▒▒▓▓▓▓▓▒▓▓▓▓▓▓▓▓▓▓▓▓▒▓▒▓▓▓▓▓▓▓▓▓▓▓▓▒▓█▓██████████████████
                        # ████████████████████▓▓▓▓▒▓▓▓▓▓▓█▓ ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓▒▓█▓▓███████████▓█████
                        # █▓█████████████████▓▓▓▓▓▓▓▓▓▓▓█▓  ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   ▓██▓▓▓▓▓▓▓▓▓█████████████████
                        # ██████████████████▓▓▓█▓▓▒▓▓▓▓█▓    ▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓    ▒█▓▓▓▓▓▓▓▓▒▓▓██████████████▓
                        # ████████████████▓▓▓▓▓█▓▓▓▓▓▓█▓     ▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ░▒ ▒█▓▓█▓▓▓▓█▓▓▓▓▓████████████▓
                        # ██████████████▓▓▓▒▓▓▓█▓▓▓▓█▓▓▓██▓▓▓██▓▓█▓█▓▓▓█▓▓▓█▓▓██████▓▓██▓▓▓█▓▓▓▓▓▓████████████
                        # ██████████████▓▓█▓▓▓▓█▓▓▓▓█▓███████▓▓████▓███▓█▓▓██▓▓██▓▓▓▓██▓▓▓▓███████▓▓▓▓████████
                        # ███████████▓▓█████████▓▓▓▓▓██▓▓████▓ ▒░ ▓█▓█████▓▓▒▒█████▓▒▓██▓▓▓▓██████▓▓▓▓▓▓██████
                        # █████████▓▓▓▓████████▓▓▓▓▓▓█▓ ▓█▓▓▓▓     ▓▒▒▓██▓▒░  ▓▓▓▓▓ ░▓▓█▓▓▓▓█▓█████▓█▓▓▓▓▓█▓██
                        # ████████▓▓▓▓▓███▓▓▓▓██▓▓▓▓▓▓▓▒ ▓▓▒▓▒░               ░▓▒▓▒░▒▒▒▓▓▓▓▓▓▒▓▓██▓▓██████▓▓▓▓
                        # ████████▓▓▓▓▓██▓▓▒▒▒▓▓▓▓▓█▓▓▓▒▒░▒▒░░░░░             ░░░░▒▒▒░▓▓█▓▓▓█▒▓▓██▓▓█████████▓
                        # ████████▓▓▓▓▓▓▓█▓▒▒▓█▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒░░░░░░ ░ ░░ ░░░░░▒▒▒▒▒▒▒▓██▓▓▓▓▓██▓▓█▓▓▓████████
                        # ███████▓▓▓█▓▓▓███▓▓█▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒░▒░░░░░░░░░░░░░░░▒▒▒▒▒▒▒▓█▓█▓▓▓▓██▓▓▓▓█▓▒▓███████
                        # █████▓▒▓██▓▓▓▓▓█████▓▓▓▓▓▓▓▓█▓▒▒▒▒▒▒▒▒▒▒░░░░ ░ ░░▒░▒▒▒▒▒▒▒▓█▓▓█▓▓▓▓▓▓▓▓▓▓▓██▓▓▓█████
                        # ███▓▓▓███▓▓▓▓▓▓▓███▓▓█▓▓▓▓▓▓██▓▒▒▒▒▒▒▒▒▒▒░░▒▓▓▓▒░▒▒▒▒▒▒▒▒▒▓█▓██▓▓▓▓▓▓▓▓▓▓▓▓████▓████
                        # ██▓▓███▓▓▓▓▓▓█▓▓▓█▓▓▓█▓▓▓▓▓▓▓█▓▓▓▒▒▒▒▒▒▒░▓██████▓▒▒▒▒▒▒░▒▓█▓██▓▓▓▓▓▓▓█▓▓▓▓▓▓▓███████
                        # ██████▓▓▓▓▓▓▓▓▓▓██▓▒██▓▓▓▓▓▓▓██▓▓▒▒▒▒▒▒▒▒▓█▓▓▓▓█▓▒▒▒▒▒▒▓███▓█▓▓█▓▓▓▓▓██▓▓█▓▓▓▓█████▓
                        # █████▓▓▓██▓▓▓▓▓▓██▓▓██▓▓▓▓▓▓▓█▓██▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓████▓█▓▓▓█▓▓▓▓▓███▓▓██▓▓▓██▓▓█
                        # ▓███▓▓███▓▓▓█▓▓▓██▓▓█▓█▓▓▓▓▓██▓▓███▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▓▓████▓▓█▓▓▓█▓▓▓▓▓▓███▓▓▓▓█▓▓▓█▓▓▓
                        # ▓██▓▓█▓▓▓▓▓▓█▓▓███▓▓████▓█▓▓▓██▓▓███▓▓▓▓▓▓▒▒▒▒▒▓▓▓██▓▓▓▓▓█▓▓▓██▓▓▓█▓▓▓█▓▓▓▓▓▓▓▓▓▓█▓▓
                        # ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓▓██▓█▓▓██▓▓█▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓██▓▓▓▓█▓█▓▓▓██▓▓█▓█▓▓▓█▓▓▓▓▓▓▓▓▓▓█▓▓
                        # ▓█▓▓▓▓▓▓▓▓▓▓▓▓██▓█▓▓██▓██▓▓███▓█▓███▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓▓▓█▓▓▓███▓█▓█▓█▓▓▓▓▓▓▓▓▓▓▓▓▓██▓
                        # ██▓▓▓▓▓▓▓▓▓▓▓▓██▓▓█▓█▓█▓██▓▓████▓███▓▓▓▓▓▓▓▓▓▓▓▓███▓▓▓█▓█▓▓▓█▓█▓█▓▓▓█▓▓▓▓▓▓▓▓███████
                        # ██████▓▓▓▓▓▓▓▓▓█▓▓▓█▓█▓▓▓███▓▓████████▓█▓▒▒▓▓███████████▓█▓█▓██▓▓▓▓▓█▓▓▓▓▓▓███▓███▓█
                        # █████▓███▓▓▓▓▓▓██████▓▓██████▓█▓▓▒▓█████▓░ ▒▓█████▓▓▓▓███████▓▓▓█████▓▓▓████▓▓▓███▓▓
                        # ▓▓███▓▓█████▓▓▓▓████████████▒▒▓▓▓░ ░▒▓▓▒▓▓▓▓▓▓▓▓▓▒ ▒▒ ▒▓████████████▓▓▓██▓▓▓▓▓▓████▓
                        #  ▒███▓▓▓▓▓▓▓███████████████▓  ▒▓▓▒░░ ▒█▓ ▒▓▒ ▓█▒ ░░▒▓░▒▒▓█████████████▓█▓▓██▓▓▓████▓
                        # ▓████▓▓▓▓█▓▓▓█▓▓▒▓██▓▓█▓▓█▓▒░░▒▓▒▓▓▓▓▓▓▓▓▒░▓▓▓▓▓▓▒▓▓▓░▓▓▒███▓██████▓▓███▓▓██▓▓▓▓████
                        # █████▓▓▓▓██▓▓▓░░░░▒▓░▓█▓ ░░░▒░▒▓░▒▓▓▓▒░░▓▓▓▓▓░░▒▓▓▓▒░░▓▓░ ▒▒▒█▓▒█▓▒░░▒▓█▓▓▓██▓▓▓████
                        # █████▓▓▓██▓▓▓▒▒▒▒░░░░▓█▓░▒▒▒▒▒▒▓▒▒░▒░▒▒▒░▓█▓░▒▒▒░▒▒▒▒▒▒▒▒▒░░▒█▓▒▒▒▒▒▒░▒▓██▓▓▓██▓▓▓██
                        # ███▓▓▓███▓▓▓█▓▓▓▓▓▓▒▒▓█▓░▒▒▒▒▒▒▓▓▒▒▒▒▒▒▒▒▓█▓▒▒▒▒▒▒▒▒▒▒▓▒▒▒▒▒▒██▒▒▒▒▒▓▓▓▓▓▓█▓▓▓▓█████
                        # ██▓▓██▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▓██▓▓▓▓▒▒▒▓▓▒▒▒▒▒▒▒▒██▓▓▒▒▒▒▒▒▒▒▓▓▒▒▒▒▒▒██▓▓▓▓▓▓▓▓▓▓▓▓████▓▓█▓ 
                        
                        # this is the optimisation for searches with '5 out of 750,000' hitrate. rather than iterating through all 750k, we just do the search and then cull potentials in one go
                        # I could just load all the potential pairs and trust the sqlite query profiler hinges the joint around doing one of the file guys first, but let's be very very specific about what we want to do here
                        # this is a precise optimisation that follows a very specific path
                        
                        relevant_pairs_and_distances = potential_duplicate_pairs_fragmentary_search.PopRemaining()
                        
                        with self._MakeTemporaryIntegerTable( relevant_pairs_and_distances, ( 'smaller_media_id', 'larger_media_id', 'distance' ) ) as temp_media_ids_table_name_for_culling:
                            
                            self._Execute( f'ANALYZE {temp_media_ids_table_name_for_culling};')
                            
                            if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                                
                                results_1 = self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1 )
                                results_2 = self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_2, temp_table_name_2 )
                                
                                if len( results_1 ) < len( results_2 ):
                                    
                                    ( first_table, second_table ) = ( temp_table_name_1, temp_table_name_2 )
                                    
                                else:
                                    
                                    ( first_table, second_table ) = ( temp_table_name_2, temp_table_name_1 )
                                    
                                
                                self._Execute( f'ANALYZE {temp_table_name_1};')
                                self._Execute( f'ANALYZE {temp_table_name_2};')
                                
                                table_join_1 = f'{first_table} CROSS JOIN duplicate_files AS duplicate_files_1 ON ( {first_table}.hash_id = duplicate_files_1.king_hash_id ) '
                                table_join_1 += f'CROSS JOIN {temp_media_ids_table_name_for_culling} ON ( duplicate_files_1.media_id = {temp_media_ids_table_name_for_culling}.smaller_media_id ) '
                                table_join_1 += f'CROSS JOIN duplicate_files AS duplicate_files_2 ON ( {temp_media_ids_table_name_for_culling}.larger_media_id = duplicate_files_2.media_id ) '
                                table_join_1 += f'CROSS JOIN {second_table} ON ( duplicate_files_2.king_hash_id = {second_table}.hash_id )'
                                
                                table_join_2 = f'{first_table} CROSS JOIN duplicate_files AS duplicate_files_1 ON ( {first_table}.hash_id = duplicate_files_1.king_hash_id ) '
                                table_join_2 += f'CROSS JOIN {temp_media_ids_table_name_for_culling} ON ( duplicate_files_1.media_id = {temp_media_ids_table_name_for_culling}.larger_media_id ) '
                                table_join_2 += f'CROSS JOIN duplicate_files AS duplicate_files_2 ON ( {temp_media_ids_table_name_for_culling}.smaller_media_id = duplicate_files_2.media_id ) '
                                table_join_2 += f'CROSS JOIN {second_table} ON ( duplicate_files_2.king_hash_id = {second_table}.hash_id )'
                                
                                select_statements = [
                                    f'SELECT smaller_media_id, larger_media_id, distance FROM {table_join_1}',
                                    f'SELECT smaller_media_id, larger_media_id, distance FROM {table_join_2}'
                                ]
                                
                            else:
                                
                                if ( file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates() ) and db_location_context.SingleTableIsFast():
                                    
                                    # I presume this situation will never happen since what system:everything would deliver a low hitrate, but we'll be good and cover it
                                    # I think the user who has five media groups, each of 500 members (low king incidence), with some similar to each other, might hit this
                                    # or a guy with 99999990 webms and 10 images I guess. we'll see if that becomes a problem
                                    
                                    select_statements = [ f'SELECT smaller_media_id, larger_media_id, distance FROM {temp_media_ids_table_name_for_culling}' ]
                                    
                                else:
                                    
                                    results_1 = self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1 )
                                    
                                    self._Execute( f'ANALYZE {temp_table_name_1};')
                                    
                                    if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
                                        
                                        table_join_1 = f'{temp_table_name_1} as file_results_1 CROSS JOIN duplicate_files AS duplicate_files_1 ON ( file_results_1.hash_id = duplicate_files_1.king_hash_id ) '
                                        table_join_1 += f'CROSS JOIN {temp_media_ids_table_name_for_culling} ON ( duplicate_files_1.media_id = {temp_media_ids_table_name_for_culling}.smaller_media_id ) '
                                        table_join_1 += f'CROSS JOIN duplicate_files AS duplicate_files_2 ON ( {temp_media_ids_table_name_for_culling}.larger_media_id = duplicate_files_2.media_id ) '
                                        table_join_1 += f'CROSS JOIN {temp_table_name_1} AS file_results_2 ON ( duplicate_files_2.king_hash_id = file_results_2.hash_id )'
                                        
                                        table_join_2 = f'{temp_table_name_1} as file_results_1 CROSS JOIN duplicate_files AS duplicate_files_1 ON ( file_results_1.hash_id = duplicate_files_1.king_hash_id ) '
                                        table_join_2 += f'CROSS JOIN {temp_media_ids_table_name_for_culling} ON ( duplicate_files_1.media_id = {temp_media_ids_table_name_for_culling}.larger_media_id ) '
                                        table_join_2 += f'CROSS JOIN duplicate_files AS duplicate_files_2 ON ( {temp_media_ids_table_name_for_culling}.smaller_media_id = duplicate_files_2.media_id ) '
                                        table_join_2 += f'CROSS JOIN {temp_table_name_1} AS file_results_2 ON ( duplicate_files_2.king_hash_id = file_results_2.hash_id )'
                                        
                                        select_statements = [
                                            f'SELECT smaller_media_id, larger_media_id, distance FROM {table_join_1}',
                                            f'SELECT smaller_media_id, larger_media_id, distance FROM {table_join_2}'
                                        ]
                                        
                                    else:
                                        
                                        table_join = f'{temp_table_name_1} CROSS JOIN duplicate_files ON ( {temp_table_name_1}.hash_id = duplicate_files.king_hash_id ) CROSS JOIN {temp_media_ids_table_name_for_culling} ON ( duplicate_files.media_id = {temp_media_ids_table_name_for_culling}.smaller_media_id OR duplicate_files.media_id = {temp_media_ids_table_name_for_culling}.larger_media_id )'
                                        
                                        select_statements = [ f'SELECT smaller_media_id, larger_media_id, distance FROM {table_join}' ]
                                        
                                    
                                
                            
                            for select_statement in select_statements:
                                
                                self._Execute( f'INSERT OR IGNORE INTO {temp_media_ids_table_name} ( smaller_media_id, larger_media_id, distance ) {select_statement};' )
                                
                            
                        
                    else:
                        
                        # OK so the conceit I went with in the end is simply substituting potential_duplicate_pairs table with a temp table of our relevant pairs and letting the query planner's chips fall where they may
                        # I threw in the ANALYZE to help the query planner navigate this. we'll see how it is IRL, fingers-crossed we win with three-row tables giving us insta-search
                        # trying to insert a forced CROSS JOIN in dynamic join calls here is total wewmode, so tread carefully
                        
                        relevant_pairs_and_distances = potential_duplicate_pairs_fragmentary_search.PopBlock()
                        
                        self._ExecuteMany( f'INSERT OR IGNORE INTO {temp_media_ids_table_name} ( smaller_media_id, larger_media_id, distance ) VALUES ( ?, ?, ? );', relevant_pairs_and_distances.GetRows() )
                        
                        if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                            
                            all_media_ids = set( itertools.chain.from_iterable( relevant_pairs_and_distances.GetPairs() ) )
                            
                            required_hash_ids = self.modules_files_duplicates_storage.GetKingHashIds( db_location_context, all_media_ids )
                            
                            self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1, query_hash_ids = required_hash_ids )
                            self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_2, temp_table_name_2, query_hash_ids = required_hash_ids )
                            
                            self._Execute( f'ANALYZE {temp_table_name_1};')
                            self._Execute( f'ANALYZE {temp_table_name_2};')
                            
                        else:
                            
                            if ( file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates() ) and db_location_context.SingleTableIsFast():
                                
                                pass
                                
                            else:
                                
                                all_media_ids = set( itertools.chain.from_iterable( relevant_pairs_and_distances.GetPairs() ) )
                                
                                required_hash_ids = self.modules_files_duplicates_storage.GetKingHashIds( db_location_context, all_media_ids )
                                
                                self.modules_files_query.PopulateSearchIntoTempTable( file_search_context_1, temp_table_name_1, query_hash_ids = required_hash_ids )
                                
                                self._Execute( f'ANALYZE {temp_table_name_1};')
                                
                            
                        
                    
                    self._Execute( f'ANALYZE {temp_media_ids_table_name};')
                    
                    if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                        
                        table_join = self.modules_files_duplicates_storage.GetPotentialDuplicatePairsTableJoinOnSeparateSearchResults( temp_table_name_1, temp_table_name_2, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                        
                    else:
                        
                        if ( file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates() ) and db_location_context.SingleTableIsFast():
                            
                            table_join = self.modules_files_duplicates_storage.GetPotentialDuplicatePairsTableJoinOnEverythingSearchResults( db_location_context, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                            
                        else:
                            
                            if dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH:
                                
                                table_join = self.modules_files_duplicates_storage.GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( temp_table_name_1, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                                
                            else:
                                
                                table_join = self.modules_files_duplicates_storage.GetPotentialDuplicatePairsTableJoinOnSearchResults( db_location_context, temp_table_name_1, pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = temp_media_ids_table_name )
                                
                            
                        
                    
                    # distinct important here for the search results table join
                    matching_pairs_and_distances = self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id, distance FROM {};'.format( table_join ) ).fetchall()
                    
                
            
        
        if do_report_mode:
            
            try:
                
                time_took = HydrusTime.GetNowPrecise() - time_started
                
                if do_file_based_search:
                    
                    # we care about 'time per hit' here
                    num_guys = len( matching_pairs_and_distances )
                    
                    HydrusData.Print( f'Fragmentary potential duplicates search did a file based search, with per-hit speed of: { HydrusTime.TimeDeltaToPrettyTimeDelta( time_took / num_guys ) }' )
                    
                else:
                    
                    # we care about 'time per potential row' here
                    num_guys = len( relevant_pairs_and_distances )
                    
                    HydrusData.Print( f'Fragmentary potential duplicates search did a potentials based search, with per-row speed of: { HydrusTime.TimeDeltaToPrettyTimeDelta( time_took / num_guys ) }' )
                    
                
            except Exception as e:
                
                HydrusData.Print( 'Could not profile the fragmentary duplicates search!' )
                
            
        
        potential_duplicate_pairs_fragmentary_search.AddHits( matching_pairs_and_distances )
        
        return ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( matching_pairs_and_distances )
        
    
    def GetPotentialDuplicateMediaResultPairsAndDistances( self, potential_duplicate_pairs_fragmentary_search: ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances:
        
        matching_potential_duplicate_id_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( [] )
        
        while not potential_duplicate_pairs_fragmentary_search.SearchDone():
            
            matching_potential_duplicate_id_pairs_and_distances.Merge(
                self.GetPotentialDuplicateMediaResultPairsAndDistancesFragmentary( potential_duplicate_pairs_fragmentary_search )
            )
            
        
        return matching_potential_duplicate_id_pairs_and_distances
        
    
    def GetPotentialDuplicateMediaResultPairsAndDistancesFragmentary( self, potential_duplicate_pairs_fragmentary_search: ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch, no_more_than = None ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances:
        
        matching_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicate_pairs_fragmentary_search )
        
        rows = matching_potential_duplicate_id_pairs_and_distances.GetRows()
        
        if no_more_than is not None:
            
            rows = rows[ : no_more_than ]
            
        
        pairs = [ ( smaller_media_id, larger_media_id ) for ( smaller_media_id, larger_media_id, distance ) in rows ]
        
        all_media_ids = { media_id for pair in pairs for media_id in pair }
        
        media_ids_to_king_hash_ids = { media_id : self.modules_files_duplicates_storage.GetKingHashId( media_id ) for media_id in all_media_ids }
        
        media_results = self.modules_media_results.GetMediaResults( set( media_ids_to_king_hash_ids.values() ) )
        
        hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
        
        matching_potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances(
            [ ( hash_ids_to_media_results[ media_ids_to_king_hash_ids[ smaller_media_id ] ], hash_ids_to_media_results[ media_ids_to_king_hash_ids[ larger_media_id ] ], distance ) for ( smaller_media_id, larger_media_id, distance ) in rows ]
        )
        
        return matching_potential_duplicate_media_result_pairs_and_distances
        
    
    def GetPotentialDuplicatesCount( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
        potential_duplicate_id_pairs_and_distances = self.modules_files_duplicates_updates.GetPotentialDuplicateIdPairsAndDistances( potential_duplicates_search_context.GetLocationContext() )
        
        potential_duplicate_pairs_fragmentary_search = ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch( potential_duplicates_search_context, True )
        potential_duplicate_pairs_fragmentary_search.SetSearchSpace( potential_duplicate_id_pairs_and_distances )
        
        count = 0
        
        while not potential_duplicate_pairs_fragmentary_search.SearchDone():
            
            count += self.GetPotentialDuplicatesCountFragmentary( potential_duplicate_pairs_fragmentary_search )
            
        
        return count
        
    
    def GetPotentialDuplicatesCountFragmentary( self, potential_duplicate_pairs_fragmentary_search: ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) -> int:
        
        matching_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicate_pairs_fragmentary_search )
        
        return len( matching_potential_duplicate_id_pairs_and_distances )
        
    
    def GetRandomPotentialDuplicateGroupHashes( self, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ) -> list[ bytes ]:
        
        potential_duplicate_id_pairs_and_distances = self.modules_files_duplicates_updates.GetPotentialDuplicateIdPairsAndDistances( potential_duplicates_search_context.GetLocationContext() )
        
        potential_duplicate_pairs_fragmentary_search = ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch( potential_duplicates_search_context, True )
        potential_duplicate_pairs_fragmentary_search.SetDesiredNumHits( 1 )
        potential_duplicate_pairs_fragmentary_search.SetSearchSpace( potential_duplicate_id_pairs_and_distances )
        
        master_media_id = None
        
        while not potential_duplicate_pairs_fragmentary_search.SearchDone():
            
            matching_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicate_pairs_fragmentary_search )
            
            if len( matching_potential_duplicate_id_pairs_and_distances ) > 0:
                
                rows = matching_potential_duplicate_id_pairs_and_distances.GetRows()
                
                row = random.choice( rows )
                
                master_media_id = row[0]
                
                break
                
            
        
        if master_media_id is None:
            
            return []
            
        
        # ok we have selected a random guy that fits the search. we know there is at least one pair, so let's now get his whole group
        
        # a small wew moment here is that if any link in the group is not present in the search context, we nonetheless deliver the two separate sections of the chain--let's see how often that is an issue
        group_fragmentary_search = potential_duplicate_pairs_fragmentary_search.SpawnMediaIdFilteredSearch( ( master_media_id, ) )
        
        group_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistances( group_fragmentary_search )
        
        all_media_ids = { media_id for pair in group_potential_duplicate_id_pairs_and_distances.GetPairs() for media_id in pair }
        
        media_ids_to_king_hash_ids = { media_id : self.modules_files_duplicates_storage.GetKingHashId( media_id ) for media_id in all_media_ids }
        
        hashes = self.modules_hashes_local_cache.GetHashes( list( media_ids_to_king_hash_ids.values() ) )
        
        return hashes
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
