import collections
import sqlite3
import typing

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

def GenerateResolutionDecisionTableNames( rule_id ) -> typing.Dict[ int, str ]:
    
    table_core = f'duplicate_files_auto_resolution_pair_decisions_{rule_id}'
    
    results = {}
    
    for status in (
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST
    ):
        
        results[ status ] = f'{table_core}_{status}'
        
    
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
        
        self._Reinit()
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.duplicate_files_auto_resolution_rules' : ( 'CREATE TABLE IF NOT EXISTS {} ( rule_id INTEGER PRIMARY KEY, actioned_pair_count INTEGER DEFAULT 0 );', 606 ),
            'main.duplicates_files_auto_resolution_rule_count_cache' : ( 'CREATE TABLE IF NOT EXISTS {} ( rule_id INTEGER, status INTEGER, status_count INTEGER, PRIMARY KEY ( rule_id, status ) ) )', 606 )
        }
        
    
    def _Reinit( self ):
        
        self._rule_ids_to_rules = { rule.GetId() : rule for rule in self.modules_serialisable.GetJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE ) }
        
    
    def GetRules( self ) -> typing.List[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ]:
        
        return [ rule for ( rule_id, rule ) in sorted( self._rule_ids_to_rules.items() ) ]
        
    
    def SetRules( self, new_rules: typing.Collection[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ], master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        rule_ids_to_new_resolution_rules = { rule.GetId() : rule for rule in new_rules }
        
        existing_rule_ids = set( self._rule_ids_to_rules.keys() )
        new_rule_ids = set( self._rule_ids_to_rules.keys() )
        
        rule_ids_to_add = new_rule_ids.difference( existing_rule_ids )
        rule_ids_to_delete = existing_rule_ids.difference( new_rule_ids )
        rule_ids_to_update = new_rule_ids.intersection( existing_rule_ids )
        
        for rule_id in rule_ids_to_add:
            
            rule = rule_ids_to_new_resolution_rules[ rule_id ]
            
            self._Execute( 'INSERT INTO duplicate_files_auto_resolution_rules DEFAULT VALUES;' )
            
            rule_id = self._GetLastRowId()
            
            rule.SetId( rule_id )
            
            self.modules_serialisable.SetJSONDump( rule )
            
            self._rule_ids_to_rules[ rule_id ] = rule
            
            statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
            
            for table_name in statuses_to_table_names.values():
                
                self._Execute( f'DROP TABLE IF EXISTS {table_name};' ) # due to the nature of the rule_id here, just a little safety thing to handle busted dbs
                
                self._Execute( f'CREATE TABLE IF NOT EXISTS {table_name} ( smaller_media_id INTEGER, larger_media_id INTEGER, PRIMARY KEY ( smaller_media_id, larger_media_id ) );' )
                
                self._CreateIndex( table_name, ( 'larger_media_id', 'smaller_media_id' ) )
                
            
            table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]
            
            self._Execute( f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id ) SELECT smaller_media_id, larger_media_id FROM {master_potential_duplicate_pairs_table_name};' )
            
            num_added = self._GetRowCount()
            
            self._Execute( 'REPLACE INTO duplicates_files_auto_resolution_rule_count_cache ( rule_id, status, status_count ) VALUES ( ?, ?, ? );', rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED, num_added )
            
        
        for rule_id in rule_ids_to_delete:
            
            rule = self._rule_ids_to_rules[ rule_id ]
            
            self._Execute( 'DELETE FROM duplicate_files_auto_resolution_rules WHERE rule_id = ?;' )
            
            statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
            
            for table_name in statuses_to_table_names.values():
                
                self.modules_db_maintenance.DeferredDropTable( table_name )
                
            
            del self._rule_ids_to_rules[ rule_id ]
            
            self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = rule.GetName() )
            
            self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache WHERE rule_id = ?;', ( rule_id, ) )
            
        
        for rule_id in rule_ids_to_update:
            
            rule = rule_ids_to_new_resolution_rules[ rule_id ]
            
            existing_rule = self._rule_ids_to_rules[ rule_id ]
            
            if rule.GetPotentialDuplicatesSearchContext() != existing_rule.GetPotentialDuplicatesSearchContext():
                
                statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
                
                for ( status, table_name ) in statuses_to_table_names.items():
                    
                    if status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED:
                        
                        self._Execute( f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id ) SELECT smaller_media_id, larger_media_id FROM {master_potential_duplicate_pairs_table_name};' )
                        
                        num_added = self._GetRowCount()
                        
                        if num_added > 0:
                            
                            self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', num_added, rule_id, status )
                            
                        
                    else:
                        
                        self._Execute( f'DELETE FROM {table_name};' )
                        
                        self._Execute( 'REPLACE INTO duplicates_files_auto_resolution_rule_count_cache ( rule_id, status, status_count ) VALUES ( ?, ?, ? );', rule_id, status, 0 )
                        
                    
                
            
            self._rule_ids_to_rules[ rule_id ] = rule
            
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def GetMatchingUntestedPair( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        if rule_id not in self._rule_ids_to_rules:
            
            return None
            
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
        
        table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED ]
        
        return self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {table_name};' ).fetchone()
        
    
    def GetNumberSummary( self ):
        
        result = collections.defaultdict( dict )
        
        rows = self._Execute( 'SELECT rule_id, status, status_count FROM duplicates_files_auto_resolution_rule_count_cache;' ).fetchall()
        
        for ( rule_id, status, status_count ) in rows:
            
            result[ rule_id ][ status ] = status_count
            
        
        found_data = { ( rule_id, status ) for ( rule_id, status, status_count ) in rows }
        expected_data = set()
        
        for rule_id in self._rule_ids_to_rules.keys():
            
            expected_data.update(
                [ ( rule_id, status ) for status in [
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH,
                    ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST
                ] ]
            )
            
        
        missing_data = expected_data.difference( found_data )
        
        if len( missing_data ) > 0:
            
            insert_rows = []
            
            missing_data_dict = HydrusData.BuildKeyToSetDict( missing_data )
            
            for ( rule_id, statuses ) in missing_data_dict:
                
                statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
                
                for status in statuses:
                    
                    table_name = statuses_to_table_names[ status ]
                    
                    ( status_count, ) = self._Execute( f'SELECT COUNT( * ) FROM {table_name};' ).fetchone()
                    
                    result[ rule_id ][ status ] = status_count
                    
                    insert_rows.append(
                        ( rule_id, status, status_count )
                    )
                    
                
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO duplicates_files_auto_resolution_rule_count_cache ( rule_id, status, status_count ) VALUES ( ?, ?, ? );', insert_rows )
            
        
        for ( rule_id, actioned_pair_count ) in self._Execute( 'SELECT rule_id, actioned_pair_count FROM duplicate_files_auto_resolution_rules;' ):
            
            result[ rule_id ][ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST ] = actioned_pair_count
            
        
        return result
        
    
    def GetUnsearchedPairs( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        if rule_id not in self._rule_ids_to_rules:
            
            return []
            
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
        
        table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]
        
        return self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {table_name};' ).fetchall()
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def IncrementActionedPairCount( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        self._Execute( 'UPDATE duplicate_files_auto_resolution_rules SET actioned_pair_count = actioned_pair_count + 1 WHERE rule_id = ?;', ( rule_id, ) )
        
    
    def MaintenanceFixOrphanPairs( self, pairs_to_sync_to = None, master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        pairs_stored_in_duplicates_proper = None
        
        if pairs_to_sync_to is None:
            
            pairs_to_sync_to = self._STS( self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {master_potential_duplicate_pairs_table_name};' ) )
            pairs_stored_in_duplicates_proper = set( pairs_to_sync_to )
            
        
        with self._MakeTemporaryIntegerTable( pairs_to_sync_to, ( 'smaller_media_id', 'larger_media_id' ) ) as temp_media_ids_table_name:
            
            if pairs_stored_in_duplicates_proper is None:
                
                table_join = f'{temp_media_ids_table_name} CROSS JOIN {master_potential_duplicate_pairs_table_name} ON ( {temp_media_ids_table_name}.smaller_media_id = {master_potential_duplicate_pairs_table_name}.smaller_media_id AND {temp_media_ids_table_name}.larger_media_id = {master_potential_duplicate_pairs_table_name}.larger_media_id )'
                
                pairs_stored_in_duplicates_proper = self._STS( self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {table_join};' ) )
                
            
            for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
                
                statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
                statuses_to_pairs_i_have = collections.defaultdict( set )
                
                for ( status, table_name ) in statuses_to_table_names:
                    
                    pairs_i_have = self._STS( self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {temp_media_ids_table_name} CROSS JOIN {table_name} ON ( {temp_media_ids_table_name}.smaller_media_id = {table_name}.smaller_media_id AND {temp_media_ids_table_name}.larger_media_id = {table_name}.larger_media_id );' ) )
                    
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
                        
                        self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', num_added, rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED )
                        
                    
                
                for ( status, pairs_i_have ) in statuses_to_pairs_i_have.items():
                    
                    pairs_we_should_remove = pairs_i_have.difference( pairs_stored_in_duplicates_proper )
                    
                    if len( pairs_we_should_remove ) > 0:
                        
                        self._ExecuteMany(
                            f'DELETE FROM {statuses_to_table_names[ status ]} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                            pairs_we_should_remove
                        )
                        
                        num_deleted = self._GetRowCount()
                        
                        if num_deleted > 0:
                            
                            self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count - ? WHERE rule_id = ? AND status = ?;', num_deleted, rule_id, status )
                            
                        
                    
                
            
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache;' )
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def MaintenanceFixOrphanRules( self ):
        
        all_serialised_rule_ids = set( self._rule_ids_to_rules.keys() )
        
        defined_rule_ids = self._STS( self._Execute( 'SELECT rule_id FROM duplicate_files_auto_resolution_rules;' ) )
        
        orphaned_on_our_side = defined_rule_ids.difference( all_serialised_rule_ids )
        orphaned_on_object_side = all_serialised_rule_ids.difference( defined_rule_ids )
        
        if len( orphaned_on_our_side ) > 0:
            
            self._ExecuteMany( 'DELETE FROM duplicate_files_auto_resolution_rules WHERE rule_id = ?;', ( ( rule_id, ) for rule_id in orphaned_on_our_side ) )
            
            HydrusData.ShowText( f'Deleted {HydrusNumbers.ToHumanInt( len( orphaned_on_our_side ) )} orphaned auto-resolution rule definitions!' )
            HydrusData.Print( f'Deleted ids: {sorted( orphaned_on_our_side )}')
            
        
        if len( orphaned_on_object_side ) > 0:
            
            orphaned_object_names = { self._rule_ids_to_rules[ rule_id ].GetName() for rule_id in orphaned_on_object_side }
            
            for name in orphaned_object_names:
                
                self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = name )
                
            
            HydrusData.ShowText( f'Deleted {HydrusNumbers.ToHumanInt( len( orphaned_on_object_side ) )} orphaned auto-resolution rule objects!' )
            HydrusData.Print( f'Deleted names: {sorted( orphaned_object_names )}')
            
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache;' )
        
        self._Reinit()
        
    
    def NotifyNewPotentialDuplicatePairsAdded( self, pairs_added ):
        
        # new pairs have been discovered and added to the system, so we should schedule them for a search according to our rules
        
        for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
            
            statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
            
            self._ExecuteMany(
                f'INSERT OR IGNORE INTO {statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );',
                pairs_added
            )
            
            num_added = self._GetRowCount()
            
            if num_added > 0:
                
                self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', num_added, rule_id, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED )
                
            
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def NotifyExistingPotentialDuplicatePairsRemoved( self, pairs_removed ):
        
        # maybe these pairs were collapsed by a merge action, broken by a false positive, or simply dissolved
        # whatever the reason, they no longer exist as a pair, so this system does not need to track them any more 
        
        for ( rule_id, resolution_rule ) in self._rule_ids_to_rules.items():
            
            statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
            
            for ( status, table_name ) in statuses_to_table_names.items():
                
                self._ExecuteMany(
                    f'DELETE FROM {table_name} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                    pairs_removed
                )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count - ? WHERE rule_id = ? AND status = ?;', num_deleted, rule_id, status )
                    
                
            
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def ResetRuleSearchProgress( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        rule_id = rule.GetId()
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
        
        not_searched_table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]
        
        for ( status, table_name ) in statuses_to_table_names.items():
            
            if status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED:
                
                continue
                
            
            self._Execute( f'INSERT OR IGNORE INTO {not_searched_table_name} ( smaller_media_id, larger_media_id ) SELECT smaller_media_id, larger_media_id FROM {table_name};' )
            
            self._Execute( f'DELETE FROM {table_name};' )
            
        
        self._Execute( 'DELETE FROM duplicates_files_auto_resolution_rule_count_cache WHERE rule_id = ?;', ( rule_id, ) )
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    
    def SetPairsStatus( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, pairs: typing.Collection, status_to_set: int ):
        
        rule_id = rule.GetId()
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( rule_id )
        
        for ( status, table_name ) in statuses_to_table_names.items():
            
            if status == status_to_set:
                
                self._ExecuteMany(
                    f'INSERT OR IGNORE INTO {table_name} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );',
                    pairs
                )
                
                num_added = self._GetRowCount()
                
                if num_added > 0:
                    
                    self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count + ? WHERE rule_id = ? AND status = ?;', num_added, rule_id, status )
                    
                
            else:
                
                self._ExecuteMany(
                    f'DELETE FROM {table_name} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                    pairs
                )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._Execute( 'UPDATE duplicates_files_auto_resolution_rule_count_cache SET status_count = status_count - ? WHERE rule_id = ? AND status = ?;', num_deleted, rule_id, status )
                    
                
            
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
