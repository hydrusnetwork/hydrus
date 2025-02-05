import sqlite3
import typing

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
        
    
    def DoResolutionWork( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, max_work_time = 0.5 ) -> bool:
        
        work_still_to_do = True
        
        # we probably want some sort of progress reporting for an UI watching this guy
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( rule.GetPotentialDuplicatesSearchContext().GetFileSearchContext1().GetLocationContext() )
        
        time_started = HydrusTime.GetNowFloat()
        
        def get_row():
            
            return self.modules_files_duplicates_auto_resolution_storage.GetMatchingUntestedPair( rule )
            
        
        pair_to_work = get_row()
        
        while pair_to_work is not None:
            
            ( smaller_media_id, larger_media_id ) = pair_to_work
            
            smaller_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context = db_location_context )
            larger_hash_id = self.modules_files_duplicates.GetBestKingId( smaller_media_id, db_location_context = db_location_context )
            
            if smaller_hash_id is None or larger_hash_id is None:
                
                self.modules_files_duplicates_auto_resolution_storage.SetPairsStatus( rule, ( pair_to_work, ), ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST )
                
                pair_to_work = get_row()
                
                continue
                
            
            media_result_1 = self.modules_media_results.GetMediaResult( smaller_hash_id )
            media_result_2 = self.modules_media_results.GetMediaResult( larger_media_id )
            
            result = rule.TestPair( media_result_1, media_result_2 )
            
            if result is None:
                
                self.modules_files_duplicates_auto_resolution_storage.SetPairsStatus( rule, ( pair_to_work, ), ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST )
                
                pair_to_work = get_row()
                
                continue
                
            
            # result is ( action, hash_a, hash_b, content_update_packages )
            self.modules_files_duplicates_setter.SetDuplicatePairStatus(
                ( result, )
            )
            
            self.modules_files_duplicates_auto_resolution_storage.IncrementActionedPairCount( rule )
            
            if max_work_time is not None and HydrusTime.TimeHasPassedFloat( time_started + max_work_time ):
                
                return work_still_to_do
                
            
            old_pair_to_work = pair_to_work
            
            pair_to_work = get_row()
            
            if old_pair_to_work == pair_to_work:
                
                # ruh roh
                
                raise Exception( f'Hey, the duplicates auto-resolution system encountered an error! Your "{rule.GetName()}" rule processed a pair ({pair_to_work}), but that pair did not disappear from the to-be-actioned queue. Something has gone wrong, and the respective rule should have been paused. Please let hydev know the details.' )
                
            
        
        work_still_to_do = False
        
        return work_still_to_do
        
    
    def DoSearchWork( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        # this guy originally wanted to do the search in 256 chunks, but it is actually easier for all concerned if we try to do as much work as we can every time
        
        potential_duplicates_search_context = rule.GetPotentialDuplicatesSearchContext()
        
        unsearched_pairs = self.modules_files_duplicates_auto_resolution_storage.GetUnsearchedPairs( rule )
        
        if len( unsearched_pairs ) > 0:
            
            matching_pairs = self.modules_files_duplicates_file_query.GetPotentialDuplicatePairsForAutoResolution( potential_duplicates_search_context, unsearched_pairs )
            
            #
            
            unmatching_pairs = set( unsearched_pairs ).difference( matching_pairs )
            
            self.modules_files_duplicates_auto_resolution_storage.SetPairsStatus( rule, matching_pairs, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED )
            self.modules_files_duplicates_auto_resolution_storage.SetPairsStatus( rule, unmatching_pairs, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH )
            
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
