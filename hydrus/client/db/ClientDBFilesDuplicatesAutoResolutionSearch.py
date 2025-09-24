import itertools
import sqlite3
import typing

from hydrus.core import HydrusTime

from hydrus.client.db import ClientDBFilesDuplicates
from hydrus.client.db import ClientDBFilesDuplicatesAutoResolutionStorage
from hydrus.client.db import ClientDBFilesDuplicatesFileSearch
from hydrus.client.db import ClientDBFilesDuplicatesSetter
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBMediaResults
from hydrus.client.db import ClientDBModule
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.media import ClientMediaResult

class ClientDBFilesDuplicatesAutoResolutionSearch( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_local_hashes_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_files_duplicates: ClientDBFilesDuplicates.ClientDBFilesDuplicates,
        modules_files_duplicates_auto_resolution_storage: ClientDBFilesDuplicatesAutoResolutionStorage.ClientDBFilesDuplicatesAutoResolutionStorage,
        modules_media_results: ClientDBMediaResults.ClientDBMediaResults,
        modules_files_duplicates_file_query: ClientDBFilesDuplicatesFileSearch.ClientDBFilesDuplicatesFileSearch,
        modules_files_duplicates_setter: ClientDBFilesDuplicatesSetter.ClientDBFilesDuplicatesSetter
    ):
        
        self.modules_local_hashes_cache = modules_local_hashes_cache
        self.modules_files_storage = modules_files_storage
        self.modules_files_duplicates = modules_files_duplicates
        self.modules_files_duplicates_auto_resolution_storage = modules_files_duplicates_auto_resolution_storage
        self.modules_media_results = modules_media_results
        self.modules_files_duplicates_file_query = modules_files_duplicates_file_query
        self.modules_files_duplicates_setter = modules_files_duplicates_setter
        
        super().__init__( 'client duplicates auto-resolution search', cursor )
        
    
    def ApprovePendingPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, pairs ):
        
        for ( media_result_a, media_result_b ) in pairs:
            
            hash_id_a = media_result_a.GetHashId()
            hash_id_b = media_result_b.GetHashId()
            
            media_id_a = self.modules_files_duplicates.GetMediaId( hash_id_a )
            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
            
            if media_id_a == media_id_b: # ok a previous approve in this run already merged these guys; nothing to do
                
                continue
                
            
            result = rule.GetDuplicateActionResult( media_result_a, media_result_b )
            
            self.modules_files_duplicates_setter.SetDuplicatePairStatus( [ result ] )
            
            smaller_media_id = min( media_id_a, media_id_b )
            larger_media_id = max( media_id_a, media_id_b )
            
            duplicate_type = result[0]
            
            self.modules_files_duplicates_auto_resolution_storage.RecordActionedPair( rule, smaller_media_id, larger_media_id, hash_id_a, hash_id_b, duplicate_type, HydrusTime.GetNowMS() )
            
        
    
    def CommitResolutionPairFailed( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, media_result_pair: tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult ] ):
        
        ( media_result_1, media_result_2 ) = media_result_pair
        
        hash_id_1 = media_result_1.GetHashId()
        hash_id_2 = media_result_2.GetHashId()
        
        media_id_1 = self.modules_files_duplicates.GetMediaId( hash_id_1 )
        media_id_2 = self.modules_files_duplicates.GetMediaId( hash_id_2 )
        
        smaller_media_id = min( media_id_1, media_id_2 )
        larger_media_id = max( media_id_1, media_id_2 )
        
        self.modules_files_duplicates_auto_resolution_storage.SetPairsToSimpleQueue( rule, ( ( smaller_media_id, larger_media_id), ), ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST )
        
    
    def CommitResolutionPairPassed( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, result ):
        
        # result is ( action, hash_a, hash_b, content_update_packages )
        
        hash_a = result[1]
        hash_b = result[2]
        
        hash_id_a = self.modules_local_hashes_cache.GetHashId( hash_a )
        hash_id_b = self.modules_local_hashes_cache.GetHashId( hash_b )
        
        media_id_a = self.modules_files_duplicates.GetMediaId( hash_id_a )
        media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
        
        smaller_media_id = min( media_id_a, media_id_b )
        larger_media_id = max( media_id_a, media_id_b )
        
        operation_mode = rule.GetOperationMode()
        
        if operation_mode == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION:
            
            self.modules_files_duplicates_auto_resolution_storage.SetPairToPendingAction( rule, smaller_media_id, larger_media_id, hash_id_a, hash_id_b )
            
        else:
            
            self.modules_files_duplicates_setter.SetDuplicatePairStatus( [ result ] )
            
            duplicate_type = result[0]
            
            self.modules_files_duplicates_auto_resolution_storage.RecordActionedPair( rule, smaller_media_id, larger_media_id, hash_id_a, hash_id_b, duplicate_type, HydrusTime.GetNowMS() )
            
        
    
    def DenyPendingPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, pairs ):
        
        for ( media_result_a, media_result_b ) in pairs:
            
            hash_id_a = media_result_a.GetHashId()
            hash_id_b = media_result_b.GetHashId()
            
            media_id_a = self.modules_files_duplicates.GetMediaId( hash_id_a )
            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
            
            smaller_media_id = min( media_id_a, media_id_b )
            larger_media_id = max( media_id_a, media_id_b )
            
            pair = ( smaller_media_id, larger_media_id )
            
            self.modules_files_duplicates_auto_resolution_storage.SetPairsToSimpleQueue( rule, ( pair, ), ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DECLINED )
            
        
    
    def GetResolutionPair( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ) -> typing.Optional[ tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult ] ]:
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( rule.GetPotentialDuplicatesSearchContext().GetFileSearchContext1().GetLocationContext() )
        
        def get_row():
            
            # were it convenient, I think it might be nice to sort this to reduce the incidence of visual duplicates false negatives
            # I am thinking that if you have 90%, 80%, 60% quality, the 80/60 is more likely to match than the 90/60, so if we do 80/60 first, i.e. smallest max filesize, we'd be able to collapse more
            # however I think we'd violate KISS generally.  we'd be fetching 15 pairs for every single pair fetch or rewangling the pair queue storage to track size of king blah blah blah, so no worries
            # also, an odd thought: typically, every decision will raise the average filesize
            
            return self.modules_files_duplicates_auto_resolution_storage.GetMatchingUntestedPair( rule )
            
        
        pair_to_work = get_row()
        
        while pair_to_work is not None:
            
            ( smaller_media_id, larger_media_id ) = pair_to_work
            
            smaller_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context = db_location_context )
            larger_hash_id = self.modules_files_duplicates.GetBestKingId( larger_media_id, db_location_context = db_location_context )
            
            if smaller_hash_id is None or larger_hash_id is None:
                
                self.modules_files_duplicates_auto_resolution_storage.SetPairsToSimpleQueue( rule, ( pair_to_work, ), ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST )
                
                pair_to_work = get_row()
                
                continue
                
            
            media_result_1 = self.modules_media_results.GetMediaResult( smaller_hash_id )
            media_result_2 = self.modules_media_results.GetMediaResult( larger_hash_id )
            
            return ( media_result_1, media_result_2 )
            
        
        return None
        
    
    def DoSearchWork( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        we_produced_matching_pairs = False
        
        # there is some overhead for any search. even as we prime with a query_hash_ids, I suspect some searches will be bad.
        # if we dicover that fetching just two rows here every thirty seconds really screws things up, we'll want to batch this to 256 chunks or something
        
        limit = 4096
        
        unsearched_pairs_and_distances = self.modules_files_duplicates_auto_resolution_storage.GetUnsearchedPairsAndDistances( rule, limit = limit )
        
        work_still_to_do = len( unsearched_pairs_and_distances ) == limit
        
        if len( unsearched_pairs_and_distances ) > 0:
            
            potential_duplicates_search_context = rule.GetPotentialDuplicatesSearchContext()
            
            matching_potential_duplicate_id_pairs_and_distances = self.modules_files_duplicates_file_query.GetPotentialDuplicateIdPairsAndDistancesFragmentary( potential_duplicates_search_context, unsearched_pairs_and_distances )
            
            #
            
            unsearched_pairs = set( unsearched_pairs_and_distances.GetPairs() )
            
            matching_pairs = set( matching_potential_duplicate_id_pairs_and_distances.GetPairs() )
            
            unmatching_pairs = unsearched_pairs.difference( matching_pairs )
            
            self.modules_files_duplicates_auto_resolution_storage.SetPairsToSimpleQueue( rule, matching_pairs, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED )
            self.modules_files_duplicates_auto_resolution_storage.SetPairsToSimpleQueue( rule, unmatching_pairs, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH )
            
            we_produced_matching_pairs = len( matching_pairs ) > 0
            
        
        return ( work_still_to_do, we_produced_matching_pairs )
        
    
    def GetActionedPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, fetch_limit = None ):
        
        hash_id_pairs_with_data = self.modules_files_duplicates_auto_resolution_storage.GetActionedPairs( rule, fetch_limit = fetch_limit )
        
        all_hash_ids = set( itertools.chain.from_iterable( ( ( hash_id_a, hash_id_b ) for ( hash_id_a, hash_id_b, duplicate_type, timestamp_ms ) in hash_id_pairs_with_data ) ) )
        
        media_results = self.modules_media_results.GetMediaResults( all_hash_ids )
        
        hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
        
        media_result_pairs_with_data = [
            ( hash_ids_to_media_results[ hash_id_a ], hash_ids_to_media_results[ hash_id_b ], duplicate_type, timestamp_ms )
            for ( hash_id_a, hash_id_b, duplicate_type, timestamp_ms )
            in hash_id_pairs_with_data
        ]
        
        return media_result_pairs_with_data
        
    
    def GetDeclinedPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, fetch_limit = None ):
        
        media_id_pairs_with_data = self.modules_files_duplicates_auto_resolution_storage.GetDeclinedPairs( rule, fetch_limit = fetch_limit )
        
        pairs = [ ( smaller_media_id, larger_media_id ) for ( smaller_media_id, larger_media_id, timestamp ) in media_id_pairs_with_data ]
        
        all_media_ids = { media_id for pair in pairs for media_id in pair }
        
        media_ids_to_king_hash_ids = { media_id : self.modules_files_duplicates.GetKingHashId( media_id ) for media_id in all_media_ids }
        
        all_hash_ids = set( media_ids_to_king_hash_ids.values() )
        
        media_results = self.modules_media_results.GetMediaResults( all_hash_ids )
        
        hash_ids_to_media_results = { media_result.GetHashId() : media_result for media_result in media_results }
        
        media_result_pairs_with_data = [
            ( hash_ids_to_media_results[ media_ids_to_king_hash_ids[ smaller_media_id ] ], hash_ids_to_media_results[ media_ids_to_king_hash_ids[ larger_media_id ] ], timestamp_ms )
            for ( smaller_media_id, larger_media_id, timestamp_ms )
            in media_id_pairs_with_data
        ]
        
        return media_result_pairs_with_data
        
    
    def GetPendingActionPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, fetch_limit = None ):
        
        hash_id_pairs = self.modules_files_duplicates_auto_resolution_storage.GetPendingActionPairs( rule, fetch_limit = fetch_limit )
        
        media_result_pairs = self.modules_media_results.GetMediaResultPairs( hash_id_pairs )
        
        return media_result_pairs
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def RescindDeclinedPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, media_result_pairs ):
        
        for ( media_result_a, media_result_b ) in media_result_pairs:
            
            hash_id_a = media_result_a.GetHashId()
            hash_id_b = media_result_b.GetHashId()
            
            media_id_a = self.modules_files_duplicates.GetMediaId( hash_id_a )
            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
            
            smaller_media_id = min( media_id_a, media_id_b )
            larger_media_id = max( media_id_a, media_id_b )
            
            pair = ( smaller_media_id, larger_media_id )
            
            self.modules_files_duplicates_auto_resolution_storage.SetPairsToSimpleQueue( rule, ( pair, ), ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED )
            
        
    
