import itertools
import sqlite3

from hydrus.core import HydrusTime

from hydrus.client.db import ClientDBFilesDuplicates
from hydrus.client.db import ClientDBFilesDuplicatesAutoResolutionStorage
from hydrus.client.db import ClientDBFilesDuplicatesFileSearch
from hydrus.client.db import ClientDBFilesDuplicatesSetter
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBMediaResults
from hydrus.client.db import ClientDBModule
from hydrus.client.duplicates import ClientDuplicatesAutoResolution

class ClientDBFilesDuplicatesAutoResolutionSearch( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_files_duplicates: ClientDBFilesDuplicates.ClientDBFilesDuplicates,
        modules_files_duplicates_auto_resolution_storage: ClientDBFilesDuplicatesAutoResolutionStorage.ClientDBFilesDuplicatesAutoResolutionStorage,
        modules_media_results: ClientDBMediaResults.ClientDBMediaResults,
        modules_files_duplicates_file_query: ClientDBFilesDuplicatesFileSearch.ClientDBFilesDuplicatesFileSearch,
        modules_files_duplicates_setter: ClientDBFilesDuplicatesSetter.ClientDBFilesDuplicatesSetter
    ):
        
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
            
        
    
    def DoResolutionWork( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, stop_time = None ) -> bool:
        
        work_still_to_do = True
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( rule.GetPotentialDuplicatesSearchContext().GetFileSearchContext1().GetLocationContext() )
        
        def get_row():
            
            return self.modules_files_duplicates_auto_resolution_storage.GetMatchingUntestedPair( rule )
            
        
        current_num_pending_pairs = rule.GetCountsCacheDuplicate()[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION ]
        
        def pending_pairs_full_up():
            
            if rule.GetOperationMode() == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION:
                
                max_pending_pairs = rule.GetMaxPendingPairs()
                
                if max_pending_pairs is not None and current_num_pending_pairs >= max_pending_pairs:
                    
                    return True
                    
                
            
            return False
            
        
        pair_to_work = get_row()
        
        while pair_to_work is not None:
            
            if pending_pairs_full_up():
                
                return False
                
            
            ( smaller_media_id, larger_media_id ) = pair_to_work
            
            smaller_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context = db_location_context )
            larger_hash_id = self.modules_files_duplicates.GetBestKingId( larger_media_id, db_location_context = db_location_context )
            
            if smaller_hash_id is None or larger_hash_id is None:
                
                self.modules_files_duplicates_auto_resolution_storage.SetPairsToSimpleQueue( rule, ( pair_to_work, ), ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST )
                
                pair_to_work = get_row()
                
                continue
                
            
            media_result_1 = self.modules_media_results.GetMediaResult( smaller_hash_id )
            media_result_2 = self.modules_media_results.GetMediaResult( larger_hash_id )
            
            # TODO: now that this can take some CPU time, we should pull this out of the db tbh!
            
            result = rule.TestPair( media_result_1, media_result_2 )
            
            if result is None:
                
                self.modules_files_duplicates_auto_resolution_storage.SetPairsToSimpleQueue( rule, ( pair_to_work, ), ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST )
                
                pair_to_work = get_row()
                
                continue
                
            
            # result is ( action, hash_a, hash_b, content_update_packages )
            
            hash_a = result[1]
            
            if media_result_1.GetHash() == hash_a:
                
                hash_id_a = smaller_hash_id
                hash_id_b = larger_hash_id
                
            else:
                
                hash_id_a = larger_hash_id
                hash_id_b = smaller_hash_id
                
            
            operation_mode = rule.GetOperationMode()
            
            if operation_mode == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION:
                
                current_num_pending_pairs += 1
                
                self.modules_files_duplicates_auto_resolution_storage.SetPairToPendingAction( rule, smaller_media_id, larger_media_id, hash_id_a, hash_id_b )
                
            else:
                
                self.modules_files_duplicates_setter.SetDuplicatePairStatus( [ result ] )
                
                duplicate_type = result[0]
                
                self.modules_files_duplicates_auto_resolution_storage.RecordActionedPair( rule, smaller_media_id, larger_media_id, hash_id_a, hash_id_b, duplicate_type, HydrusTime.GetNowMS() )
                
            
            if stop_time is not None and HydrusTime.TimeHasPassedFloat( stop_time ):
                
                return work_still_to_do
                
            
            old_pair_to_work = pair_to_work
            
            pair_to_work = get_row()
            
            if old_pair_to_work == pair_to_work:
                
                # ruh roh
                
                raise Exception( f'Hey, the duplicates auto-resolution system encountered an error! Your "{rule.GetName()}" rule processed a pair ({pair_to_work}), but that pair did not disappear from the to-be-actioned queue. Something has gone wrong, and the respective rule should have been paused. Please let hydev know the details.' )
                
            
        
        work_still_to_do = False
        
        return work_still_to_do
        
    
    def DoSearchWork( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        we_produced_matching_pairs = False
        
        # there is some overhead for any search. even as we prime with a query_hash_ids, I suspect some searches will be bad.
        # if we dicover that fetching just two rows here every thirty seconds really screws things up, we'll want to batch this to 256 chunks or something
        
        limit = 4096
        
        unsearched_pairs_and_distances = self.modules_files_duplicates_auto_resolution_storage.GetUnsearchedPairsAndDistances( rule, limit = limit )
        
        work_still_to_do = len( unsearched_pairs_and_distances ) == limit
        
        if len( unsearched_pairs_and_distances ) > 0:
            
            potential_duplicates_search_context = rule.GetPotentialDuplicatesSearchContext()
            
            matching_pairs = self.modules_files_duplicates_file_query.GetPotentialDuplicatePairsFragmentary( potential_duplicates_search_context, unsearched_pairs_and_distances )
            
            #
            
            unsearched_pairs = { ( smaller_media_id, larger_media_id ) for ( smaller_media_id, larger_media_id, distance ) in unsearched_pairs_and_distances }
            
            unmatching_pairs = set( unsearched_pairs ).difference( matching_pairs )
            
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
        
    
    def GetPendingActionPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, fetch_limit = None ):
        
        hash_id_pairs = self.modules_files_duplicates_auto_resolution_storage.GetPendingActionPairs( rule, fetch_limit = fetch_limit )
        
        media_result_pairs = self.modules_media_results.GetMediaResultPairs( hash_id_pairs )
        
        return media_result_pairs
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
