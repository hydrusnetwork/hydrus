import collections
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG
from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBSerialisable
from hydrus.client.db import ClientDBServices
from hydrus.client.duplicates import ClientDuplicatesAutoResolution

def GenerateResolutionActionedPairsTableName( rule_id: int ) -> str:
    
    return f'duplicate_files_auto_resolution_actioned_{rule_id}'
    

def GenerateResolutionPendingActionsPairsTableName( rule_id: int ) -> str:
    
    return f'duplicate_files_auto_resolution_pending_actions_{rule_id}'
    

def GenerateAutoResolutionQueueTableNames( rule_id: int ) -> typing.Dict[ int, str ]:
    
    table_core = f'duplicate_files_auto_resolution_pair_decisions_{rule_id}'
    
    results = {}
    
    for status in (
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DECLINED
    ):
        
        results[ status ] = f'{table_core}_{status}'
        
    
    results[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION ] = GenerateResolutionPendingActionsPairsTableName( rule_id )
    
    return results
    

class ClientDBFilesDuplicatesAutoResolutionStorage( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_db_maintenance: ClientDBMaintenance.ClientDBMaintenance,
        modules_serialisable: ClientDBSerialisable.ClientDBSerialisable
    ):
        
        self.modules_services = modules_services
        self.modules_db_maintenance = modules_db_maintenance
        self.modules_serialisable = modules_serialisable
        
        super().__init__( 'client duplicates auto-resolution storage', cursor )
        
        self._rule_ids_to_rules: typing.Dict[ int, ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] = {}
        
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
        
        self._Execute( f'INSERT OR IGNORE INTO {statuses_to_table_names[ dest_status ]} ( smaller_media_id, larger_media_id ) SELECT smaller_media_id, larger_media_id FROM {statuses_to_table_names[ source_status ]};' )
        
        num_added = self._GetRowCount()
        
        if num_added > 0:
            
            self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', ( num_added, rule_id, dest_status ) )
            
        
        self._Execute( f'DELETE FROM {statuses_to_table_names[ source_status ]};' )
        
        self._Execute( 'REPLACE INTO duplicates_files_auto_resolution_rule_count_cache ( rule_id, status, status_count ) VALUES ( ?, ?, ? );', ( rule_id, source_status, 0 ) )
        
    
    def _Reinit( self ):
        
        self._rule_ids_to_rules = { rule.GetId() : rule for rule in self.modules_serialisable.GetJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE ) }
        
        self._have_initialised_rules = True
        
    
    def _RemovePairsFromQueues( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, pairs: typing.Collection ):
        
        rule_id = rule.GetId()
        
        statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
        
        for ( status, table_name ) in statuses_to_table_names.items():
            
            self._ExecuteMany(
                f'DELETE FROM {table_name} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                pairs
            )
            
            num_deleted = self._GetRowCount()
            
            if num_deleted > 0:
                
                self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count - ? WHERE rule_id = ? AND status = ?;', ( num_deleted, rule_id, status ) )
                
            
        
    
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
            
        
    
    def DeleteAllPotentialDuplicatePairs( self ):
        
        # either dissolve or merge or manual removal from all potential pairs for a search reset or something
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
            
            statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
            
            for ( status, table_name ) in statuses_to_table_names.items():
                
                self._Execute( f'DELETE FROM {table_name};' )
                
            
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache;' )
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
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
        
    
    def GetMatchingUntestedPair( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rule_id = rule.GetId()
        
        if rule_id not in self._rule_ids_to_rules:
            
            return None
            
        
        statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
        
        table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED ]
        
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
        
    
    def GetRulesWithCounts( self ) -> typing.List[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ]:
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        result = collections.defaultdict( collections.Counter )
        
        rows = self._Execute( 'SELECT rule_id, status, status_count FROM duplicates_files_auto_resolution_rule_count_cache;' ).fetchall()
        
        for ( rule_id, status, status_count ) in rows:
            
            rule = self._rule_ids_to_rules[ rule_id ]
            
            result[ rule ][ status ] = status_count
            
        
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
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DECLINED
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
                    
                    result[ rule ][ status ] = status_count
                    
                    insert_rows.append(
                        ( rule_id, status, status_count )
                    )
                    
                
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO duplicates_files_auto_resolution_rule_count_cache ( rule_id, status, status_count ) VALUES ( ?, ?, ? );', insert_rows )
            
        
        for ( rule, counts ) in result.items():
            
            rule.SetCountsCache( counts )
            
        
        return list( result.keys() )
        
    
    def GetUnsearchedPairsAndDistances( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, limit = None ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rule_id = rule.GetId()
        
        if rule_id not in self._rule_ids_to_rules:
            
            return []
            
        
        statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
        
        table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]
        
        if limit is None:
            
            return self._Execute( f'SELECT smaller_media_id, larger_media_id, distance FROM {table_name} CROSS JOIN potential_duplicate_pairs USING ( smaller_media_id, larger_media_id );' ).fetchall()
            
        else:
            
            return self._Execute( f'SELECT smaller_media_id, larger_media_id, distance FROM {table_name} CROSS JOIN potential_duplicate_pairs USING ( smaller_media_id, larger_media_id ) LIMIT ?;', ( limit, ) ).fetchall()
            
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
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
            
            self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', ( num_added, rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED ) )
            
        
    
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
                        
                        self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', ( num_added, rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ) )
                        
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
                            
                            self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count - ? WHERE rule_id = ? AND status = ?;', ( num_deleted, rule_id, status ) )
                            
                            HydrusData.Print( f'During auto-resolution potential pair-sync, deleted {HydrusNumbers.ToHumanInt( num_deleted )} pairs for rule {resolution_rule.GetName()} ({rule_id}), status {status} ({ClientDuplicatesAutoResolution.duplicate_status_str_lookup[ status ]}).' )
                            
                            all_were_good = False
                            
                        
                    
                
            
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache;' )
        
        if all_were_good:
            
            HydrusData.ShowText( 'All the duplicates auto-resolution potential pairs looked good--no orphans!' )
            
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
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
        
        if all_were_good:
            
            HydrusData.ShowText( 'All the duplicates auto-resolution rules looked good--no orphans!' )
            
        
        self._Reinit()
        
    
    def NotifyNewPotentialDuplicatePairsAdded( self, pairs_added ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        # new pairs have been discovered and added to the system, so we should schedule them for a search according to our rules
        # we won't trust that the caller definitely knows they are new--nor indeed that our current storage is totally synced with that understanding--we'll scan ourselves carefully to make sure we don't dupe a pair across our status tables
        
        pairs_added = set( pairs_added )
        
        any_added = False
        
        with self._MakeTemporaryIntegerTable( pairs_added, ( 'smaller_media_id', 'larger_media_id' ) ) as temp_media_ids_table_name:
            
            self._AnalyzeTempTable( temp_media_ids_table_name )
            
            for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
                
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
                        
                        self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', ( num_added, rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ) )
                        
                        any_added = True
                        
                    
                
            
        
        if any_added:
            
            CG.client_controller.duplicates_auto_resolution_manager.Wake()
            
        
    
    def NotifyExistingPotentialDuplicatePairsRemoved( self, pairs_removed ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        # maybe these pairs were collapsed by a merge action, broken by a false positive, or simply dissolved
        # whatever the reason, they no longer exist as a pair, so this system does not need to track them any more 
        
        any_removed = False
        
        for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
            
            statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
            
            for ( status, table_name ) in statuses_to_table_names.items():
                
                self._ExecuteMany(
                    f'DELETE FROM {table_name} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                    pairs_removed
                )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count - ? WHERE rule_id = ? AND status = ?;', ( num_deleted, rule_id, status ) )
                    
                    any_removed = True
                    
                
            
        
        if any_removed:
            
            CG.client_controller.duplicates_auto_resolution_manager.Wake()
            
        
    
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
                    
                    self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count - ? WHERE rule_id = ? AND status = ?;', ( num_deleted, rule_id, status ) )
                    
                    any_removed = True
                    
                
            
        
        if any_removed:
            
            CG.client_controller.duplicates_auto_resolution_manager.Wake()
            
        
    
    def ResetRuleDeclined( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        self._MovePairsAcrossQueues( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DECLINED, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED )
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def ResetRuleSearchProgress( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        self._ResetRuleSearchProgress( rule_id )
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def ResetRuleTestProgress( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        self._ResetRuleTestProgress( rule_id )
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def SetPairToPendingAction( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, smaller_media_id: int, larger_media_id: int, hash_id_a: int, hash_id_b: int ):
        
        self._RemovePairsFromQueues( rule, [ ( smaller_media_id, larger_media_id ) ] )
        
        rule_id = rule.GetId()
        
        table_name = GenerateResolutionPendingActionsPairsTableName( rule_id )
        
        self._Execute( f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id, hash_id_a, hash_id_b ) VALUES ( ?, ?, ?, ? );', ( smaller_media_id, larger_media_id, hash_id_a, hash_id_b ) )
        
        num_added = self._GetRowCount()
        
        if num_added > 0:
            
            self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', ( num_added, rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION ) )
            
        
    
    def SetPairsToSimpleQueue( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, pairs: typing.Collection, status_to_set: int ):
        
        if status_to_set in ( ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED ):
            
            raise Exception( 'Hey, duplicates auto-resolution tried to set a ready-to-action or actioned record in the wrong place! Please tell hydev about this.' )
            
        
        self._RemovePairsFromQueues( rule, pairs )
        
        rule_id = rule.GetId()
        
        statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
        
        table_name = statuses_to_table_names[ status_to_set ]
        
        self._ExecuteMany(
            f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );',
            pairs
        )
        
        num_added = self._GetRowCount()
        
        if num_added > 0:
            
            self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', ( num_added, rule_id, status_to_set ) )
            
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def SetRules( self, new_rules: typing.Collection[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ], master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        if not self._have_initialised_rules:
            
            self._Reinit()
            
        
        rules_to_add = [ rule for rule in new_rules if rule.GetId() == -1 ]
        
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
                    
                else:
                    
                    self._Execute( f'CREATE TABLE IF NOT EXISTS {table_name} ( smaller_media_id INTEGER, larger_media_id INTEGER, PRIMARY KEY ( smaller_media_id, larger_media_id ) );' )
                    
                
                self._CreateIndex( table_name, [ 'larger_media_id', 'smaller_media_id' ], unique = True )
                
            
            actioned_pairs_table_name = GenerateResolutionActionedPairsTableName( rule_id )
            
            self._Execute( f'DROP TABLE IF EXISTS {actioned_pairs_table_name};' ) # due to the nature of the rule_id here, just a little safety thing to handle busted dbs
            
            self._Execute( f'CREATE TABLE IF NOT EXISTS {actioned_pairs_table_name} ( hash_id_a INTEGER, hash_id_b INTEGER, duplicate_type INTEGER, timestamp_ms INTEGER );' )
            
            self._CreateIndex( actioned_pairs_table_name, [ 'hash_id_a' ] )
            self._CreateIndex( actioned_pairs_table_name, [ 'hash_id_b' ] )
            self._CreateIndex( actioned_pairs_table_name, [ 'timestamp_ms' ] )
            
            table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]
            
            self._Execute( f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id ) SELECT smaller_media_id, larger_media_id FROM {master_potential_duplicate_pairs_table_name};' )
            
            num_added = self._GetRowCount()
            
            self._Execute( 'REPLACE INTO duplicates_files_auto_resolution_rule_count_cache ( rule_id, status, status_count ) VALUES ( ?, ?, ? );', ( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED, num_added ) )
            
        
        rule_ids_to_new_resolution_rules = { rule.GetId() : rule for rule in new_rules }
        
        existing_rule_ids = set( self._rule_ids_to_rules.keys() )
        new_rule_ids = { rule.GetId() for rule in new_rules }
        
        rule_ids_to_delete = existing_rule_ids.difference( new_rule_ids )
        rule_ids_to_update = new_rule_ids.intersection( existing_rule_ids )
        
        for rule_id in rule_ids_to_delete:
            
            rule = self._rule_ids_to_rules[ rule_id ]
            
            self._Execute( 'DELETE FROM duplicate_files_auto_resolution_rules WHERE rule_id = ?;', ( rule_id, ) )
            
            statuses_to_table_names = GenerateAutoResolutionQueueTableNames( rule_id )
            
            for table_name in statuses_to_table_names.values():
                
                self.modules_db_maintenance.DeferredDropTable( table_name )
                
            
            del self._rule_ids_to_rules[ rule_id ]
            
            self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = rule.GetName() )
            
            self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache WHERE rule_id = ?;', ( rule_id, ) )
            
        
        for rule_id in rule_ids_to_update:
            
            rule = rule_ids_to_new_resolution_rules[ rule_id ]
            
            existing_rule = self._rule_ids_to_rules[ rule_id ]
            
            self.modules_serialisable.SetJSONDump( rule ) # got to save it lol
            
            if rule.GetOperationMode() == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC:
                
                self._MovePairsAcrossQueues( rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED )
                
            
            if rule.GetPairSelector() != existing_rule.GetPairSelector():
                
                self._ResetRuleTestProgress( rule_id )
                
            
            if rule.GetPotentialDuplicatesSearchContext() != existing_rule.GetPotentialDuplicatesSearchContext():
                
                self._ResetRuleSearchProgress( rule_id )
                
            
            self._rule_ids_to_rules[ rule_id ] = rule
            
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
