import collections
import sqlite3
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client.db import ClientDBFilesDuplicates
from hydrus.client.db import ClientDBFilesSearch
from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBSerialisable
from hydrus.client.db import ClientDBServices
from hydrus.client.duplicates import ClientDuplicatesAutoResolution

def GenerateResolutionDecisionTableNames( resolution_rule_id ) -> typing.Dict[ int, str ]:
    
    table_core = f'duplicate_files_auto_resolution_pair_decisions_{resolution_rule_id}'
    
    results = {}
    
    for status in (
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH,
        ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST
    ):
        
        results[ status ] = f'{table_core}_{status}'
        
    
    return results
    

class ClientDBFilesDuplicatesAutoResolution( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_db_maintenance: ClientDBMaintenance.ClientDBMaintenance,
        modules_serialisable: ClientDBSerialisable.ClientDBSerialisable,
        modules_files_search: ClientDBFilesSearch.ClientDBFilesQuery,
        modules_files_duplicates: ClientDBFilesDuplicates.ClientDBFilesDuplicates
    ):
        
        self.modules_services = modules_services
        self.modules_db_maintenance = modules_db_maintenance
        self.modules_serialisable = modules_serialisable
        self.modules_files_search = modules_files_search
        self.modules_files_duplicates = modules_files_duplicates
        
        super().__init__( 'client duplicates auto-resolution', cursor )
        
        self._ids_to_resolution_rules: typing.Dict[ int, ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] = {}
        
        self._Reinit()
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.duplicate_files_auto_resolution_rules' : ( 'CREATE TABLE IF NOT EXISTS {} ( resolution_rule_id INTEGER PRIMARY KEY );', 593 )
        }
        
    
    def _Reinit( self ):
        
        self._ids_to_resolution_rules = { rule.GetId() : rule for rule in self.modules_serialisable.GetJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE ) }
        
    
    def AddRule( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        self._Execute( 'INSERT INTO duplicate_files_auto_resolution_rules DEFAULT VALUES;' )
        
        resolution_rule_id = self._GetLastRowId()
        
        rule.SetId( resolution_rule_id )
        
        self.modules_serialisable.SetJSONDump( rule )
        
        self._ids_to_resolution_rules[ resolution_rule_id ] = rule
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
        
        for table_name in statuses_to_table_names.values():
            
            self._Execute( f'CREATE TABLE IF NOT EXISTS {table_name} ( smaller_media_id INTEGER, larger_media_id INTEGER, PRIMARY KEY ( smaller_media_id, larger_media_id ) );' )
            
            self._CreateIndex( table_name, ( 'larger_media_id', 'smaller_media_id' ) )
            
        
        self._ExecuteMany( f'INSERT OR IGNORE INTO {statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]} ( smaller_media_id, larger_media_id ) SELECT smaller_media_id, larger_media_id FROM potential_duplicate_pairs;' )
        
        ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager.instance().Wake()
        
    
    def DeleteRule( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        resolution_rule_id = rule.GetId()
        
        self._Execute( 'DELETE FROM duplicate_files_auto_resolution_rules WHERE resolution_rule_id = ?;' )
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
        
        for table_name in statuses_to_table_names.values():
            
            self.modules_db_maintenance.DeferredDropTable( table_name )
            
        
        del self._ids_to_resolution_rules[ resolution_rule_id ]
        
        self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = rule.GetName() )
        
    
    def DoResolutionWork( self, resolution_rule_id: int, max_work_time = 0.5 ) -> bool:
        
        # we probably want some sort of progress reporting for an UI watching this guy
        
        time_started = HydrusTime.GetNowFloat()
        
        rule = self._ids_to_resolution_rules[ resolution_rule_id ]
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
        
        def get_row():
            
            return self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED ]};' ).fetchone()
            
        
        pair_to_work = get_row()
        
        while pair_to_work is not None:
            
            # fetch the media results for the kings
            # if no kings, say fail
            # test the rule
            # if fail, move row to fail
            # if succeed, action it and delete the row (presumably this delete, and for related collapsed rows, will happen automatically because of notify stuff, but we still have to figure that signal order out)
            pass
            
            if max_work_time is not None and HydrusTime.TimeHasPassedFloat( time_started + max_work_time ):
                
                return True
                
            
            pair_to_work = get_row()
            
        
        return False
        
    
    def DoSearchWork( self, resolution_rule_id: int, max_work_time = 0.5 ):
        
        # we probably want some sort of progress reporting for an UI watching this guy
        
        time_started = HydrusTime.GetNowFloat()
        
        rule = self._ids_to_resolution_rules[ resolution_rule_id ]
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
        
        def get_rows():
            
            return self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]} LIMIT 256;' ).fetchone()
            
        
        pairs_to_work = get_rows()
        
        while len( pairs_to_work ) > 0:
            
            # do our clever duplicates search from the rule using existing duplicates search tech, AND make sure it is limited to these 256 files.
            # we could hack that with system:hash_ids or maybe a careful query_hash_ids somewhere
            # buuuut remember we need to convert from media_ids to king_hash_ids
            # anything we can't find kings for, say fail and carefully discard from the work packet
            # then, given our results, do a difference and assign to does not match and does match but not tested yet
            # TODO: if it makes sense as you finish this up, combine this guy with the DoResolutionWork and skip the database table for 'not tested' entirely
            #   it might not fit with the ideal of doing one row at a time on that end though, so w/e
            # 
            pass
            
            if max_work_time is not None and HydrusTime.TimeHasPassedFloat( time_started + max_work_time ):
                
                return True
                
            
            pairs_to_work = get_rows()
            
        
    
    def GetNumberSummary( self ):
        
        # maybe we'll want a cache here for fast update
        # fetch the stuff like 'rule 3 search matches x pairs, passed y' for UI review
        
        pass
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def MaintenanceFixOrphanRules( self ):
        
        all_serialised_resolution_rule_ids = set( self._ids_to_resolution_rules.keys() )
        
        defined_resolution_rule_ids = self._STS( self._Execute( 'SELECT resolution_rule_id FROM duplicate_files_auto_resolution_rules;' ) )
        
        orphaned_on_our_side = defined_resolution_rule_ids.difference( all_serialised_resolution_rule_ids )
        orphaned_on_object_side = all_serialised_resolution_rule_ids.difference( defined_resolution_rule_ids )
        
        if len( orphaned_on_our_side ) > 0:
            
            self._ExecuteMany( 'DELETE FROM duplicate_files_auto_resolution_rules WHERE resolution_rule_id = ?;', ( ( resolution_rule_id, ) for resolution_rule_id in orphaned_on_our_side ) )
            
            HydrusData.ShowText( f'Deleted {HydrusNumbers.ToHumanInt( len( orphaned_on_our_side ) )} orphaned auto-resolution rule definitions!' )
            HydrusData.Print( f'Deleted ids: {sorted( orphaned_on_our_side )}')
            
        
        if len( orphaned_on_object_side ) > 0:
            
            orphaned_object_names = { self._ids_to_resolution_rules[ resolution_rule_id ].GetName() for resolution_rule_id in orphaned_on_object_side }
            
            for name in orphaned_object_names:
                
                self.modules_serialisable.DeleteJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE, dump_name = name )
                
            
            HydrusData.ShowText( f'Deleted {HydrusNumbers.ToHumanInt( len( orphaned_on_object_side ) )} orphaned auto-resolution rule objects!' )
            HydrusData.Print( f'Deleted names: {sorted( orphaned_object_names )}')
            
        
        self._Reinit()
        
    
    def NotifyAddPairs( self, pairs_to_add ):
        
        # not sure if this is the right way to do it, but w/e
        
        for ( resolution_rule_id, resolution_rule ) in self._ids_to_resolution_rules.items():
            
            statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
            
            self._ExecuteMany(
                f'INSERT OR IGNORE INTO {statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );',
                pairs_to_add
            )
            
        
        ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager.instance().Wake()
        
    
    def NotifyDeletePairs( self, pairs_to_remove ):
        
        # not sure if this is the right way to do it, but w/e
        
        for ( resolution_rule_id, resolution_rule ) in self._ids_to_resolution_rules.items():
            
            statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
            
            for table_name in statuses_to_table_names.values():
                
                self._ExecuteMany(
                    f'DELETE FROM {table_name} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                    pairs_to_remove
                )
                
            
        
        ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager.instance().Wake()
        
    
    def ResearchRule( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        # rule was edited or user wants to run it again (maybe it has num_tags or something in it)
        
        resolution_rule_id = rule.GetId()
        
        self._ids_to_resolution_rules[ resolution_rule_id ] = rule
        
        statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
        
        not_searched_table_name = statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]
        
        for ( status, table_name ) in statuses_to_table_names.items():
            
            if status == ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED:
                
                continue
                
            
            self._Execute( f'INSERT OR IGNORE INTO {not_searched_table_name} ( smaller_media_id, larger_media_id ) SELECT smaller_media_id, larger_media_id FROM {table_name};' )
            
            self._Execute( f'DELETE FROM {table_name};' )
            
        
    
    def SyncPairs( self, pairs_to_sync_to = None ):
        
        if pairs_to_sync_to is None:
            
            pairs_to_sync_to = self._STS( self._Execute( 'SELECT smaller_media_id, larger_media_id FROM potential_duplicate_pairs;' ) )
            
        
        with self._MakeTemporaryIntegerTable( pairs_to_sync_to, ( 'smaller_media_id', 'larger_media_id' ) ) as temp_media_ids_table_name:
            
            my_ids_to_statuses_to_pairs = collections.defaultdict( lambda: collections.defaultdict( set ) )
            
            for ( resolution_rule_id, resolution_rule ) in self._ids_to_resolution_rules.items():
                
                statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
                
                for ( status, table_name ) in statuses_to_table_names:
                    
                    pairs = self._STS( self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {temp_media_ids_table_name} CROSS JOIN {table_name} ON ( {temp_media_ids_table_name}.smaller_media_id = {table_name}.smaller_media_id AND {temp_media_ids_table_name}.larger_media_id = {table_name}.larger_media_id );' ) )
                    
                    my_ids_to_statuses_to_pairs[ resolution_rule_id ][ status ] = pairs
                    
                
            
            pairs_stored_in_duplicates_proper = self.modules_files_duplicates.FilterExistingPotentialDuplicatePairs( temp_media_ids_table_name )
            
        
        for ( resolution_rule_id, statuses_to_pairs ) in my_ids_to_statuses_to_pairs.items():
            
            statuses_to_table_names = GenerateResolutionDecisionTableNames( resolution_rule_id )
            
            all_my_pairs = HydrusLists.MassUnion( statuses_to_pairs.values() )
            
            pairs_we_should_add = pairs_stored_in_duplicates_proper.difference( all_my_pairs )
            
            if len( pairs_we_should_add ) > 0:
                
                self._ExecuteMany(
                    f'INSERT OR IGNORE INTO {statuses_to_table_names[ ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED ]} ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );',
                    pairs_we_should_add
                )
                
            
            for ( status, my_pairs ) in statuses_to_pairs.items():
                
                pairs_we_should_remove = my_pairs.difference( pairs_stored_in_duplicates_proper )
                
                if len( pairs_we_should_remove ) > 0:
                    
                    self._ExecuteMany(
                        f'DELETE FROM {statuses_to_table_names[ status ]} WHERE smaller_media_id = ? AND larger_media_id = ?;',
                        pairs_we_should_remove
                    )
                    
                
            
        
        ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager.instance().Wake()
        
    
