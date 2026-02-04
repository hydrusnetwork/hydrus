import collections
import collections.abc
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBFilesDuplicatesStorage
from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBSerialisable
from hydrus.client.db import ClientDBServices
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext

def GenerateResolutionActionedPairsTableName( rule_id: int ) -> str:
    
    return f'duplicate_files_auto_resolution_actioned_{rule_id}'
    

def GenerateResolutionDeniedPairsTableName( rule_id: int ) -> str:
    
    return f'duplicate_files_auto_resolution_declined_{rule_id}'
    

def GenerateResolutionPendingActionsPairsTableName( rule_id: int ) -> str:
    
    return f'duplicate_files_auto_resolution_pending_actions_{rule_id}'
    

def GenerateAutoResolutionQueueTableName( rule_id: int, status: int ):
    
    return GenerateAutoResolutionQueueTableNames( rule_id )[ status ]
    

def GenerateAutoResolutionQueueTableNames( rule_id: int ) -> dict[ int, str ]:
    
    table_core = f'duplicate_files_auto_resolution_pair_decisions_{rule_id}'
    
    results = {}
    
    for status in (
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST
    ):
        
        results[ status ] = f'{table_core}_{status}'
        
    
    results[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DENIED ] = GenerateResolutionDeniedPairsTableName( rule_id )
    
    results[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION ] = GenerateResolutionPendingActionsPairsTableName( rule_id )
    
    return results
    

class ClientDBFilesDuplicatesAutoResolutionStorage( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_db_maintenance: ClientDBMaintenance.ClientDBMaintenance,
        modules_serialisable: ClientDBSerialisable.ClientDBSerialisable,
        modules_files_duplicates_storage: ClientDBFilesDuplicatesStorage.ClientDBFilesDuplicatesStorage
    ):
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_services = modules_services
        self.modules_db_maintenance = modules_db_maintenance
        self.modules_serialisable = modules_serialisable
        self.modules_files_duplicates_storage = modules_files_duplicates_storage
        
        super().__init__( 'client duplicates auto-resolution storage', cursor )
        
        self._rule_ids_to_rules: dict[ int, ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] = {}
        
        self._have_initialised_rules = False
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.duplicate_files_auto_resolution_rules' : ( 'CREATE TABLE IF NOT EXISTS {} ( rule_id INTEGER PRIMARY KEY );', 616 ),
            'main.duplicates_files_auto_resolution_rule_count_cache' : ( 'CREATE TABLE IF NOT EXISTS {} ( rule_id INTEGER, status INTEGER, status_count INTEGER, PRIMARY KEY ( rule_id, status ) );', 612 )
        }
        
    
    def _MovePairsAcrossQueues( self, rule_id, source_status, dest_status ):
        
        if dest_status in ( ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED ):
            
            raise Exception( 'Hey, duplicates auto-resolution tried to set a ready-to-action or actioned record in the wrong place! Please tell hydev about this.' )
            
        
        if source_status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED:
            
            raise Exception( 'Hey, duplicates auto-resolution tried to pull from the actioned record in the wrong place! Please tell hydev about this.' )
            
        
        statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
        
        if dest_status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DENIED:
            
            now_ms = HydrusTime.GetNowMS()
            
            self._Execute( f'INSERT OR IGNORE INTO {statuses_to_table_names[ dest_status ]} ( smaller_media_id, larger_media_id, timestamp_ms ) SELECT smaller_media_id, larger_media_id, ? FROM {statuses_to_table_names[ source_status ]};', ( now_ms, ) )
            
        else:
            
            self._Execute( f'INSERT OR IGNORE INTO {statuses_to_table_names[ dest_status ]} ( smaller_media_id, larger_media_id ) SELECT smaller_media_id, larger_media_id FROM {statuses_to_table_names[ source_status ]};' )
            
        
        num_added = self._GetRowCount()
        
        if num_added > 0:
            
            self._UpdateRuleCount( rule_id, dest_status, num_added )
            
        
        self._Execute( f'DELETE FROM {statuses_to_table_names[ source_status ]};' )
        
        self._SetRuleCount( rule_id, source_status, 0 )
        
    
    def _Reinit( self ):
        
        self._rule_ids_to_rules = { rule.GetId() : rule for rule in self.modules_serialisable.GetJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE ) }
        
        # now build out our count cache as needed and attach
        
        rules_to_counters = collections.defaultdict( collections.Counter )
        
        rows = self._Execute( 'SELECT rule_id, status, status_count FROM duplicates_files_auto_resolution_rule_count_cache;' ).fetchall()
        
        for ( rule_id, status, status_count ) in rows:
            
            rule = self._rule_ids_to_rules[ rule_id ]
            
            rules_to_counters[ rule ][ status ] = status_count
            
        
        found_data = { ( rule_id, status ) for ( rule_id, status, status_count ) in rows }
        expected_data = set()
        
        for rule_id in self._rule_ids_to_rules.keys():
            
            expected_data.update(
                [ ( rule_id, status ) for status in [
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DENIED
                ] ]
            )
            
        
        missing_data = expected_data.difference( found_data )
        
        if len( missing_data ) > 0:
            
            insert_rows = []
            
            missing_data_dict = HydrusData.BuildKeyToSetDict( missing_data )
            
            for ( rule_id, statuses ) in missing_data_dict.items():
                
                rule = self._rule_ids_to_rules[ rule_id ]
                
                statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
                
                for status in statuses:
                    
                    if status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED:
                        
                        table_name = GenerateResolutionActionedPairsTableName( rule_id )
                        
                    else:
                        
                        table_name = statuses_to_table_names[ status ]
                        
                    
                    ( status_count, ) = self._Execute( f'SELECT COUNT( * ) FROM {table_name};' ).fetchone()
                    
                    rules_to_counters[ rule ][ status ] = status_count
                    
                    insert_rows.append(
                        ( rule_id, status, status_count )
                    )
                    
                
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO duplicates_files_auto_resolution_rule_count_cache ( rule_id, status, status_count ) VALUES ( ?, ?, ? );', insert_rows )
            
        
        for ( rule, counts ) in rules_to_counters.items():
            
            rule.SetCountsCache( counts )
            
        
        # rules now have counts and we will always update them the same time as the count_cache table, or in extreme delete cases, reinit here
        # count is now synced
        
        self._have_initialised_rules = True
        
    
    def _RemovePairsFromQueues( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, pairs: collections.abc.Collection ):
        
        rule_id = rule.GetId()
        
        statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
        
        for ( status, table_name ) in statuses_to_table_names.items():
            
            self._ExecuteMany(
                f'DELETE FROM {table_name} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                pairs
            )
            
            num_deleted = self._GetRowCount()
            
            if num_deleted > 0:
                
                self._UpdateRuleCount( rule_id, status, - num_deleted )
                
            
        
    
    def _ResetRuleSearchProgress( self, rule_id: int ):
        
        for status in [
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION
        ]:
            
            self._MovePairsAcrossQueues( rule_id, status, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED )
            
        
    
    def _ResetRuleTestProgress( self, rule_id: int ):
        
        for status in [
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION
        ]:
            
            self._MovePairsAcrossQueues( rule_id, status, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED )
            
        
    
    def _ResyncToLocationContext( self, rule_id: int, location_context: ClientLocation.LocationContext, master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ) -> tuple[ int, int ]:
        
        # first we'll remove any from the existing store that shouldn't be there
        
        all_good_pairs_we_have = set()
        
        total_num_deleted = 0
        
        statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
        
        for ( status, table_name ) in statuses_to_table_names.items():
            
            # TODO: do a ReadLargeIdQueryInSeparateChunks for two-column data, or n-coloumn data and do it here
            
            all_pairs_for_this_table = self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {table_name};' ).fetchall()
            
            for group_of_pairs in HydrusLists.SplitListIntoChunks( all_pairs_for_this_table, 10000 ):
                
                valid_pairs = self.modules_files_duplicates_storage.FilterMediaIdPairs( location_context, group_of_pairs )
                
                all_good_pairs_we_have.update( valid_pairs )
                
                if len( valid_pairs ) < len( group_of_pairs ):
                    
                    deletee_pairs = set( group_of_pairs ).difference( valid_pairs )
                    
                    self._ExecuteMany(
                        f'DELETE FROM {table_name} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                        deletee_pairs
                    )
                    
                    num_deleted = self._GetRowCount()
                    
                    if num_deleted > 0:
                        
                        self._UpdateRuleCount( rule_id, status, - num_deleted )
                        
                        total_num_deleted += num_deleted
                        
                    
                
            
        
        # now we'll add stuff that we should have but don't
        
        total_num_added = 0
        
        # TODO: do a ReadLargeIdQueryInSeparateChunks for two-column data, or n-coloumn data and do it here
        
        all_pairs = self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {master_potential_duplicate_pairs_table_name};' ).fetchall()
        
        not_searched_table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]
        
        for group_of_pairs in HydrusLists.SplitListIntoChunks( all_pairs, 10000 ):
            
            pairs_to_add = set( self.modules_files_duplicates_storage.FilterMediaIdPairs( location_context, group_of_pairs ) )
            
            pairs_to_add.difference_update( all_good_pairs_we_have )
            
            if len( pairs_to_add ) == 0:
                
                continue
                
            
            self._ExecuteMany( f'INSERT OR IGNORE INTO {not_searched_table_name} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );', pairs_to_add )
            
            num_added = self._GetRowCount()
            
            if num_added > 0:
                
                self._UpdateRuleCount( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED, num_added )
                
                total_num_added += num_added
                
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
        return ( total_num_deleted, total_num_added )
        
    
    def _SetRuleCount( self, rule_id: int, status: int, count: int ):
        
        self._Execute( 'REPLACE INTO duplicates_files_auto_resolution_rule_count_cache ( rule_id, status, status_count ) VALUES ( ?, ?, ? );', ( rule_id, status, count ) )
        
        rule = self._rule_ids_to_rules[ rule_id ]
        
        rule.SetCount( status, count )
        
    
    def _UpdateRuleCount( self, rule_id: int, status: int, delta: int ):
        
        self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', ( delta, rule_id, status ) )
        
        rule = self._rule_ids_to_rules[ rule_id ]
        
        rule.UpdateCount( status, delta )
        
    
    def DeleteAllPotentialDuplicatePairs( self ):
        
        # either dissolve or merge or manual removal from all potential pairs for a search reset or something
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
            
            statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
            
            for ( status, table_name ) in statuses_to_table_names.items():
                
                self._Execute( f'DELETE FROM {table_name};' )
                
            
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache;' )
        
        self._Reinit()
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def FlipPausePlay( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        try:
            
            existing_rule = self._rule_ids_to_rules[ rule_id ]
            
        except Exception as e:
            
            return
            
        
        existing_rule.SetPaused( not existing_rule.IsPaused() )
        
        self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = existing_rule.GetName() )
        self.modules_serialisable.SetJSONDump( rule )
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def GetActionedPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, fetch_limit = None ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rule_id = rule.GetId()
        
        actioned_table_name = GenerateResolutionActionedPairsTableName( rule_id )
        
        if fetch_limit is None:
            
            hash_id_pairs_with_data = self._Execute( f'SELECT hash_id_a, hash_id_b, duplicate_type, timestamp_ms FROM {actioned_table_name} ORDER BY timestamp_ms DESC;' ).fetchall()
            
        else:
            
            hash_id_pairs_with_data = self._Execute( f'SELECT hash_id_a, hash_id_b, duplicate_type, timestamp_ms FROM {actioned_table_name} ORDER BY timestamp_ms DESC LIMIT ?;', ( fetch_limit, ) ).fetchall()
            
        
        return hash_id_pairs_with_data
        
    
    def GetAllRuleLocationContexts( self ) -> set[ ClientLocation.LocationContext ]:
        
        return { resolution_rule.GetLocationContext() for resolution_rule in self._rule_ids_to_rules.values() }
        
    
    def GetDeniedPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, fetch_limit = None ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rule_id = rule.GetId()
        
        denied_table_name = GenerateResolutionDeniedPairsTableName( rule_id )
        
        if fetch_limit is None:
            
            media_id_pairs_with_data = self._Execute( f'SELECT smaller_media_id, larger_media_id, timestamp_ms FROM {denied_table_name} ORDER BY timestamp_ms DESC;' ).fetchall()
            
        else:
            
            media_id_pairs_with_data = self._Execute( f'SELECT smaller_media_id, larger_media_id, timestamp_ms FROM {denied_table_name} ORDER BY timestamp_ms DESC LIMIT ?;', ( fetch_limit, ) ).fetchall()
            
        
        return media_id_pairs_with_data
        
    
    def GetMatchingUntestedPair( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rule_id = rule.GetId()
        
        if rule_id not in self._rule_ids_to_rules:
            
            return None
            
        
        table_name = GenerateAutoResolutionQueueTableName( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED )
        
        return self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {table_name};' ).fetchone()
        
    
    def GetPendingActionPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, fetch_limit = None ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rule_id = rule.GetId()
        
        pending_actions_table_name = GenerateResolutionPendingActionsPairsTableName( rule_id )
        
        if fetch_limit is None:
            
            hash_id_pairs = self._Execute( f'SELECT hash_id_a, hash_id_b FROM {pending_actions_table_name};' ).fetchall()
            
        else:
            
            hash_id_pairs = self._Execute( f'SELECT hash_id_a, hash_id_b FROM {pending_actions_table_name} LIMIT ?;', ( fetch_limit, ) ).fetchall()
            
        
        return hash_id_pairs
        
    
    def GetRulesWithCounts( self ) -> list[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ]:
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        return list( self._rule_ids_to_rules.values() )
        
    
    def GetUnsearchedPairsAndDistances( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, limit = None ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rule_id = rule.GetId()
        
        if rule_id not in self._rule_ids_to_rules:
            
            return []
            
        
        table_name = GenerateAutoResolutionQueueTableName( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED )
        
        if limit is None:
            
            result = self._Execute( f'SELECT smaller_media_id, larger_media_id, distance FROM {table_name} CROSS JOIN potential_duplicate_pairs USING ( smaller_media_id, larger_media_id );' ).fetchall()
            
        else:
            
            result = self._Execute( f'SELECT smaller_media_id, larger_media_id, distance FROM {table_name} CROSS JOIN potential_duplicate_pairs USING ( smaller_media_id, larger_media_id ) LIMIT ?;', ( limit, ) ).fetchall()
            
        
        return ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( result )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            rule_ids = self._STS( self._Execute( 'SELECT rule_id FROM duplicate_files_auto_resolution_rules;' ) )
            
            for rule_id in rule_ids:
                
                actioned_pairs_table_name = GenerateResolutionActionedPairsTableName( rule_id )
                
                tables_and_columns.extend( [
                    ( actioned_pairs_table_name, 'hash_id_a' ),
                    ( actioned_pairs_table_name, 'hash_id_b' )
                ] )
                
                pending_actions_table_name = GenerateResolutionPendingActionsPairsTableName( rule_id )
                
                tables_and_columns.extend( [
                    ( pending_actions_table_name, 'hash_id_a' ),
                    ( pending_actions_table_name, 'hash_id_b' )
                ] )
                
            
        
        return tables_and_columns
        
    
    def RecordActionedPair( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, smaller_media_id: int, larger_media_id: int, hash_id_a: int, hash_id_b: int, duplicate_type: int, timestamp_ms: int ):
        
        self._RemovePairsFromQueues( rule, [ ( smaller_media_id, larger_media_id ) ] )
        
        rule_id = rule.GetId()
        
        table_name = GenerateResolutionActionedPairsTableName( rule_id )
        
        self._Execute( f'INSERT OR IGNORE INTO {table_name} ( hash_id_a, hash_id_b, duplicate_type, timestamp_ms ) VALUES ( ?, ?, ?, ? );', ( hash_id_a, hash_id_b, duplicate_type, timestamp_ms ) )
        
        num_added = self._GetRowCount()
        
        if num_added > 0:
            
            self._UpdateRuleCount( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED, num_added )
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def MaintenanceFixOrphanPotentialPairs( self, pairs_to_sync_to = None, master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        pairs_stored_in_duplicates_proper = None
        
        if pairs_to_sync_to is None:
            
            pairs_to_sync_to = set( self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {master_potential_duplicate_pairs_table_name};' ) )
            pairs_stored_in_duplicates_proper = set( pairs_to_sync_to )
            
        
        all_were_good = True
        
        with self._MakeTemporaryIntegerTable( pairs_to_sync_to, ( 'smaller_media_id', 'larger_media_id' ) ) as temp_media_ids_table_name:
            
            if pairs_stored_in_duplicates_proper is None:
                
                table_join = f'{temp_media_ids_table_name} CROSS JOIN {master_potential_duplicate_pairs_table_name} USING ( smaller_media_id, larger_media_id )'
                
                pairs_stored_in_duplicates_proper = set( self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {table_join};' ) )
                
            
            for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
                
                statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
                
                statuses_to_pairs_i_have = collections.defaultdict( set )
                
                for ( status, table_name ) in statuses_to_table_names.items():
                    
                    pairs_i_have = set( self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {temp_media_ids_table_name} CROSS JOIN {table_name} USING ( smaller_media_id, larger_media_id );' ) )
                    
                    statuses_to_pairs_i_have[ status ] = pairs_i_have
                    
                
                all_my_pairs = HydrusLists.MassUnion( statuses_to_pairs_i_have.values() )
                
                pairs_we_should_add = pairs_stored_in_duplicates_proper.difference( all_my_pairs )
                
                if len( pairs_we_should_add ) > 0:
                    
                    self._ExecuteMany(
                        f'INSERT OR IGNORE INTO {statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );',
                        pairs_we_should_add
                    )
                    
                    num_added = self._GetRowCount()
                    
                    if num_added > 0:
                        
                        self._UpdateRuleCount( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED, num_added )
                        
                        HydrusData.Print( f'During auto-resolution potential pair-sync, added {HydrusNumbers.ToHumanInt( num_added )} pairs for rule {resolution_rule.GetName()}, ({rule_id}).' )
                        
                        all_were_good = False
                        
                    
                
                for ( status, pairs_i_have ) in statuses_to_pairs_i_have.items():
                    
                    pairs_we_should_remove = pairs_i_have.difference( pairs_stored_in_duplicates_proper )
                    
                    if len( pairs_we_should_remove ) > 0:
                        
                        self._ExecuteMany(
                            f'DELETE FROM {statuses_to_table_names[ status ]} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                            pairs_we_should_remove
                        )
                        
                        num_deleted = self._GetRowCount()
                        
                        if num_deleted > 0:
                            
                            self._UpdateRuleCount( rule_id, status, - num_deleted )
                            
                            HydrusData.Print( f'During auto-resolution potential pair-sync, deleted {HydrusNumbers.ToHumanInt( num_deleted )} pairs for rule {resolution_rule.GetName()} ({rule_id}), status {status} ({ClientDuplicatesAutoResolution.duplicate_status_str_lookup[ status ]}).' )
                            
                            all_were_good = False
                            
                        
                    
                
            
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache;' )
        
        self._Reinit()
        
        if all_were_good:
            
            HydrusData.ShowText( 'All the duplicates auto-resolution potential pairs looked good--no orphans!' )
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def MaintenanceFixOrphanRules( self ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        all_were_good = True
        
        all_serialised_rule_ids = set( self._rule_ids_to_rules.keys() )
        
        defined_rule_ids = self._STS( self._Execute( 'SELECT rule_id FROM duplicate_files_auto_resolution_rules;' ) )
        
        orphaned_on_our_side = defined_rule_ids.difference( all_serialised_rule_ids )
        orphaned_on_object_side = all_serialised_rule_ids.difference( defined_rule_ids )
        
        if len( orphaned_on_our_side ) > 0:
            
            self._ExecuteMany( 'DELETE FROM duplicate_files_auto_resolution_rules WHERE rule_id = ?;', ( ( rule_id, ) for rule_id in orphaned_on_our_side ) )
            
            HydrusData.ShowText( f'Deleted {HydrusNumbers.ToHumanInt( len( orphaned_on_our_side ) )} orphaned auto-resolution rule definitions!' )
            HydrusData.Print( f'Deleted ids: {sorted( orphaned_on_our_side )}')
            
            all_were_good = False
            
        
        if len( orphaned_on_object_side ) > 0:
            
            orphaned_object_names = { self._rule_ids_to_rules[ rule_id ].GetName() for rule_id in orphaned_on_object_side }
            
            for name in orphaned_object_names:
                
                self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = name )
                
            
            HydrusData.ShowText( f'During auto-resolution rule-sync, deleted {HydrusNumbers.ToHumanInt( len( orphaned_on_object_side ) )} orphaned auto-resolution rule objects!' )
            HydrusData.Print( f'Deleted names: {sorted( orphaned_object_names )}')
            
            all_were_good = False
            
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache;' )
        
        self._Reinit()
        
        if all_were_good:
            
            HydrusData.ShowText( 'All the duplicates auto-resolution rules looked good--no orphans!' )
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_duplicates_auto_resolution_new_rules' )
        
    
    def MaintenanceRegenNumbers( self ):
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache;' )
        
        self._Reinit()
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
        HydrusData.ShowText( 'Cached auto-resolution numbers cleared!' )
        
    
    def MaintenanceResyncAllRulesToLocationContexts( self ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusTitle( 'auto-resolution rule file location resync' )
        
        job_status.SetStatusText( 'initialising' )
        
        CG.client_controller.pub( 'message', job_status )
        
        we_had_fixes = False
        
        num_to_do = len( self._rule_ids_to_rules )
        
        for ( num_done, ( rule_id, rule ) ) in enumerate( self._rule_ids_to_rules.items() ):
            
            job_status.SetStatusText( f'{HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}: {rule.GetName()}' )
            job_status.SetGauge( num_done, num_to_do )
            
            ( num_deleted, num_added ) = self._ResyncToLocationContext( rule_id, rule.GetLocationContext() )
            
            if num_deleted > 0 or num_added > 0:
                
                we_had_fixes = True
                
                HydrusData.ShowText( f'During file domain resync, auto-resolution rule "{rule.GetName()}" lost {HydrusNumbers.ToHumanInt(num_deleted)} pairs and added {HydrusNumbers.ToHumanInt(num_added)} rows!' )
                
            
        
        if not we_had_fixes:
            
            HydrusData.ShowText( 'All auto-resolution rules were found to be synced ok!' )
            
        
        job_status.FinishAndDismiss()
        
    
    def NotifyNewPotentialDuplicatePairsAdded( self, pertinent_location_context: ClientLocation.LocationContext, pairs_added ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        # pairs have been added either by being created or because a file has entered our domain
        # the guy above us has responsibility to doing filtering pairs according to the pertinent location context
        # we won't trust that the caller definitely knows they are new--nor indeed that our current storage is totally synced with that understanding--we'll scan ourselves carefully to make sure we don't dupe a pair across our status tables
        
        pairs_added = set( pairs_added )
        
        any_added = False
        
        with self._MakeTemporaryIntegerTable( pairs_added, ( 'smaller_media_id', 'larger_media_id' ) ) as temp_media_ids_table_name:
            
            self._AnalyzeTempTable( temp_media_ids_table_name )
            
            for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
                
                if resolution_rule.GetLocationContext() != pertinent_location_context:
                    
                    continue
                    
                
                statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
                
                pairs_that_already_exist_for_this_rule = set()
                
                for ( status, table_name ) in statuses_to_table_names.items():
                    
                    if status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED:
                        
                        continue
                        
                    
                    pairs_in_this_table = self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {temp_media_ids_table_name} CROSS JOIN {table_name} USING ( smaller_media_id, larger_media_id );' )
                    
                    pairs_that_already_exist_for_this_rule.update( pairs_in_this_table )
                    
                
                pairs_to_add_for_this_rule = pairs_added.difference( pairs_that_already_exist_for_this_rule )
                
                if len( pairs_to_add_for_this_rule ) > 0:
                    
                    self._ExecuteMany(
                        f'INSERT OR IGNORE INTO {statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );',
                        pairs_to_add_for_this_rule
                    )
                    
                    num_added = self._GetRowCount()
                    
                    if num_added > 0:
                        
                        self._UpdateRuleCount( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED, num_added )
                        
                        any_added = True
                        
                    
                
            
        
        if any_added:
            
            self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
            
        
    
    def NotifyExistingPotentialDuplicatePairsRemoved( self, pertinent_location_context: ClientLocation.LocationContext, pairs_removed ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        # maybe these pairs were collapsed by a merge action, broken by a false positive, or simply dissolved. could also be the file left this file domain
        # the guy above us has responsibility to doing filtering pairs according to the pertinent location context
        # whatever the reason, they no longer exist as a pair here, so the respective rules do not need to track them any more
        
        any_removed = False
        
        for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
            
            if resolution_rule.GetLocationContext() != pertinent_location_context:
                
                continue
                
            
            statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
            
            for ( status, table_name ) in statuses_to_table_names.items():
                
                self._ExecuteMany(
                    f'DELETE FROM {table_name} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                    pairs_removed
                )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._UpdateRuleCount( rule_id, status, - num_deleted )
                    
                    any_removed = True
                    
                
            
        
        if any_removed:
            
            self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
            
        
    
    def NotifyMediaIdNoLongerPotential( self, media_id: int ):
        
        # either dissolve or merge or manual removal from all potential pairs for a search reset or something
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        any_removed = False
        
        for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
            
            statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
            
            for ( status, table_name ) in statuses_to_table_names.items():
                
                self._Execute( f'DELETE FROM {table_name} WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._UpdateRuleCount( rule_id, status, - num_deleted )
                    
                    any_removed = True
                    
                
            
        
        if any_removed:
            
            self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
            
        
    
    def ResetRuleDenied( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        self._MovePairsAcrossQueues( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DENIED, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED )
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def ResetRuleSearchProgress( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        self._ResetRuleSearchProgress( rule_id )
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def ResetRuleTestProgress( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        self._ResetRuleTestProgress( rule_id )
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def SetPairToPendingAction( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, smaller_media_id: int, larger_media_id: int, hash_id_a: int, hash_id_b: int ):
        
        self._RemovePairsFromQueues( rule, [ ( smaller_media_id, larger_media_id ) ] )
        
        rule_id = rule.GetId()
        
        table_name = GenerateResolutionPendingActionsPairsTableName( rule_id )
        
        self._Execute( f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id, hash_id_a, hash_id_b ) VALUES ( ?, ?, ?, ? );', ( smaller_media_id, larger_media_id, hash_id_a, hash_id_b ) )
        
        num_added = self._GetRowCount()
        
        if num_added > 0:
            
            self._UpdateRuleCount( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION, num_added )
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def SetPairsToSimpleQueue( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, pairs: collections.abc.Collection, status_to_set: int ):
        
        if status_to_set in ( ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED ):
            
            raise Exception( 'Hey, duplicates auto-resolution tried to set a ready-to-action or actioned record in the wrong place! Please tell hydev about this.' )
            
        
        self._RemovePairsFromQueues( rule, pairs )
        
        rule_id = rule.GetId()
        
        table_name = GenerateAutoResolutionQueueTableName( rule_id, status_to_set )
        
        if status_to_set == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DENIED:
            
            now_ms = HydrusTime.GetNowMS()
            
            self._ExecuteMany(
                f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id, timestamp_ms ) VALUES ( ?, ?, ? );',
                [ ( smaller_media_id, larger_media_id, now_ms ) for ( smaller_media_id, larger_media_id ) in pairs ]
            )
            
        else:
            
            self._ExecuteMany(
                f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );',
                pairs
            )
            
        
        num_added = self._GetRowCount()
        
        if num_added > 0:
            
            self._UpdateRuleCount( rule_id, status_to_set, num_added )
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'duplicates_auto_resolution_rules_properties_have_changed' )
        
    
    def SetRules( self, rules_to_set: collections.abc.Collection[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ], master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rule_ids_to_rules_to_set = { rule.GetId() : rule for rule in rules_to_set }
        
        existing_rule_ids = set( self._rule_ids_to_rules.keys() )
        rule_ids_to_set = { rule.GetId() for rule in rules_to_set }
        
        rule_ids_to_delete = existing_rule_ids.difference( rule_ids_to_set )
        rule_ids_to_update = existing_rule_ids.intersection( rule_ids_to_set )
        
        #
        # we have to hop skip and jump to maneouvre around renames here since we work by id but the serialisable system uses names
        #
        
        # important we do deletes first, before writing any new ones
        for rule_id in rule_ids_to_update:
            
            existing_rule = self._rule_ids_to_rules[ rule_id ]
            
            self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = existing_rule.GetName() )
            
        
        for rule_id in rule_ids_to_delete:
            
            existing_rule = self._rule_ids_to_rules[ rule_id ]
            
            self._Execute( 'DELETE FROM duplicate_files_auto_resolution_rules WHERE rule_id = ?;', ( rule_id, ) )
            self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache WHERE rule_id = ?;', ( rule_id, ) )
            
            statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
            
            for table_name in statuses_to_table_names.values():
                
                self.modules_db_maintenance.DeferredDropTable( table_name )
                
            
            actioned_pairs_table_name = GenerateResolutionActionedPairsTableName( rule_id )
            
            self.modules_db_maintenance.DeferredDropTable( actioned_pairs_table_name )
            
            del self._rule_ids_to_rules[ rule_id ]
            
            self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = existing_rule.GetName() )
            
        
        #
        
        rules_to_add = [ rule for rule in rules_to_set if rule.GetId() < 0 ]
        
        for rule in rules_to_add:
            
            self._Execute( 'INSERT INTO duplicate_files_auto_resolution_rules DEFAULT VALUES;' )
            
            rule_id = self._GetLastRowId()
            
            rule.SetId( rule_id )
            
            self.modules_serialisable.SetJSONDump( rule )
            
            self._rule_ids_to_rules[ rule_id ] = rule
            
            statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
            
            for ( status, table_name ) in statuses_to_table_names.items():
                
                self._Execute( f'DROP TABLE IF EXISTS {table_name};' ) # due to the nature of the rule_id here, just a little safety thing to handle busted dbs
                
                if status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION:
                    
                    self._Execute( f'CREATE TABLE IF NOT EXISTS {table_name} ( smaller_media_id INTEGER, larger_media_id INTEGER, hash_id_a INTEGER, hash_id_b INTEGER, PRIMARY KEY ( smaller_media_id, larger_media_id ) );' )
                    
                    self._CreateIndex( table_name, [ 'hash_id_a' ] )
                    self._CreateIndex( table_name, [ 'hash_id_b' ] )
                    
                elif status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DENIED:
                    
                    self._Execute( f'CREATE TABLE IF NOT EXISTS {table_name} ( smaller_media_id INTEGER, larger_media_id INTEGER, timestamp_ms INTEGER, PRIMARY KEY ( smaller_media_id, larger_media_id ) );' )
                    
                    self._CreateIndex( table_name, [ 'timestamp_ms' ] )
                    
                else:
                    
                    self._Execute( f'CREATE TABLE IF NOT EXISTS {table_name} ( smaller_media_id INTEGER, larger_media_id INTEGER, PRIMARY KEY ( smaller_media_id, larger_media_id ) );' )
                    
                
                self._CreateIndex( table_name, [ 'larger_media_id', 'smaller_media_id' ], unique = True )
                
            
            actioned_pairs_table_name = GenerateResolutionActionedPairsTableName( rule_id )
            
            self._Execute( f'DROP TABLE IF EXISTS {actioned_pairs_table_name};' ) # due to the nature of the rule_id here, just a little safety thing to handle busted dbs
            
            self._Execute( f'CREATE TABLE IF NOT EXISTS {actioned_pairs_table_name} ( hash_id_a INTEGER, hash_id_b INTEGER, duplicate_type INTEGER, timestamp_ms INTEGER );' )
            
            self._CreateIndex( actioned_pairs_table_name, [ 'hash_id_a' ] )
            self._CreateIndex( actioned_pairs_table_name, [ 'hash_id_b' ] )
            self._CreateIndex( actioned_pairs_table_name, [ 'timestamp_ms' ] )
            
            self._ResyncToLocationContext( rule_id, rule.GetLocationContext(), master_potential_duplicate_pairs_table_name = master_potential_duplicate_pairs_table_name )
            
        
        for rule_id in rule_ids_to_update:
            
            rule = rule_ids_to_rules_to_set[ rule_id ]
            
            existing_rule = self._rule_ids_to_rules[ rule_id ]
            
            self.modules_serialisable.SetJSONDump( rule )
            
            self._rule_ids_to_rules[ rule_id ] = rule
            
            if rule.GetOperationMode() == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC and existing_rule.GetOperationMode() == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION:
                
                self._MovePairsAcrossQueues( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED )
                
            
            if rule.GetPairSelector() != existing_rule.GetPairSelector():
                
                self._ResetRuleTestProgress( rule_id )
                
            
            if rule.GetPotentialDuplicatesSearchContext() != existing_rule.GetPotentialDuplicatesSearchContext():
                
                only_location_context_changed = False
                
                if rule.GetLocationContext() != existing_rule.GetLocationContext():
                    
                    self._ResyncToLocationContext( rule_id, rule.GetLocationContext() )
                    
                    existing_potential_search_context_duplicate = existing_rule.GetPotentialDuplicatesSearchContext().Duplicate()
                    
                    existing_potential_search_context_duplicate.GetFileSearchContext1().SetLocationContext( rule.GetLocationContext() )
                    existing_potential_search_context_duplicate.GetFileSearchContext2().SetLocationContext( rule.GetLocationContext() )
                    
                    if rule.GetPotentialDuplicatesSearchContext() == existing_potential_search_context_duplicate:
                        
                        only_location_context_changed = True
                        
                    
                
                if not only_location_context_changed:
                    
                    self._ResetRuleSearchProgress( rule_id )
                    
                
            
        
        # fix up any borked counts that the dialog/caller messed around with
        self._Reinit()
        
        CG.client_controller.pub( 'notify_duplicates_auto_resolution_new_rules' )
        
    
