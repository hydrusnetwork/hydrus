import os
import sqlite3
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBModule

class ClientDBMaintenance( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, db_dir: str, db_filenames: dict[ str, str ], cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper, modules: list[ HydrusDBModule.HydrusDBModule ] ):
        
        super().__init__( 'client db maintenance', cursor )
        
        self._db_dir = db_dir
        self._db_filenames = db_filenames
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self._modules = modules
        
    
    def _DropTable( self, deletee_table_name: str ):
        
        self._Execute( f'DROP TABLE {deletee_table_name};' )
        
        self._Execute( 'DELETE FROM deferred_delete_tables WHERE name = ?;', ( deletee_table_name, ) )
        
        HydrusData.Print( f'Deferred delete table {deletee_table_name} successfully dropped.' )
        
    
    def _GetDeferredDeleteTableName( self ) -> tuple[ str | None, int | None ]:
        
        result = self._Execute( 'SELECT name, num_rows FROM deferred_delete_tables WHERE num_rows IS NOT NULL ORDER BY num_rows ASC;' ).fetchone()
        
        if result is None:
            
            result = self._Execute( 'SELECT name, num_rows FROM deferred_delete_tables;' ).fetchone()
            
        
        if result is None:
            
            return ( None, None )
            
        else:
            
            ( table_name, num_rows ) = result
            
            return ( table_name, num_rows )
            
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.last_shutdown_work_time' : ( 'CREATE TABLE IF NOT EXISTS {} ( last_shutdown_work_time INTEGER );', 400 ),
            'main.analyze_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( name TEXT, num_rows INTEGER, timestamp_ms INTEGER );', 400 ),
            'main.vacuum_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( name TEXT, timestamp_ms INTEGER );', 400 ),
            'main.deferred_delete_tables' : ( 'CREATE TABLE IF NOT EXISTS {} ( name TEXT, num_rows INTEGER );', 567 )
        }
        
    
    def _GetMagicDeferredDeleteQuery( self, table_name, pk_column_names, n ) -> str:
        
        #                                                                                               
        #         ░░       ▒                                                                            
        #          ▓░      ▒                                                                            
        #          ▒▒     ░▓░                                                                           
        #         ░▓▓  ░   █▓▒                                                                          
        #         ██  ░▓▓  ▒██▒                                                                         
        #       ░▓██ ░▓▓▓█  ▓███▒                         ░▒▒▒░                                         
        #     ░▒██▒░░ ▒███▒▒░ ▓███▓                      ▓██████▒                                       
        #    ▒█▓█▓  █▒░▓█▓▓▓▓  ███░                     ▓█▒  ░▒██                                       
        #     ███▓ ▒▒░▒▓▓▓░░▒▓ ▓██                     ▓█▓ ▒▒▒░▓█▓                                      
        #     ░██▓▒▓ ▒░▓▓▓ ▒ ▓▒▓██                     ████▒░█▓▓██                                      
        #      ▓██▓▒▒░ ▒██  ▒▓▓██░                     ██   ▒░▒▒██                                      
        #       ████▓▓▓▓████████▒                ░░▒▒░ ██  ▓█  ▒██▒                                     
        #        ▒██████▓▓████▓                    ░▓▓▓██  ▒▓▒▒███▓░                                    
        #           ░░▓█▓▓█▒                          ▓███▒░▒█████▒░░                                   
        #              ▒██▒                       ▒▒░ ░██████████▒  ░                                   
        #              ████░                ░▓  ░▒▓▓▓▓▒██▓▓███████▓▒░                                   
        #             ▓▓▒███▒                ▓█▒▒▒▓▒▒▒██▓▓▓█▓▒████▓▓▓▓▒                                 
        #              ████▒                 ▓▓░░▒█▒░▒█▒▒██░  ████▓▒▒▒▓░                                
        #               ███              ░▓▓███▒▒█▒░█▓▓▒▒▒▒░ ▒███▓░▒  ░█                                
        #               ▓█▓                ░░▓▒░▓█▓███▓▒▒▒▒█░▓█▓██▓▓▓▓▓█▒                               
        #               ░█▓                  ▒░▓███▓▓▓▓▒▒▒▓▓▓██▓▓██▓▓▓▓▒▓▒                              
        #                ██                ░▓▒▓██▓▓▓▒▒▒▒▓▒▓▓▓▓▓█████▓▓██░░                              
        #                ██              ▓▓▓▓▓██▓▒▓▒  ▓▓▓▓▒░▓▓▓▓█████▒▓█                                
        #                ██            ▓███▓▓▓██▓▓█░ ▒▓██▒  ▓▓▓█████▓▒▓█                                
        #                ▓█           ███▓▓██▓██████▓░░▒▒▒▒▓█████▓ ██▓▒▓                                
        #                ▓█░        ░░░░▓▓██▒▓██████▓  ▓▒ ▓█████▓  ████▓                                
        #                ▒█░    ░▒▓▓▒▒█████▓▒░███████▓░▒░▒██████   ████▓                                
        #                ░█▒ ▒▓▓██▓▓███▓▒░    ██▓▒▓███▓ ▒███████   ▓████░                               
        #                ░█▓░░▓█▓▓▓▓▓         ███░▒█▓▓█▓▓█▓█▓▓██▓  ░██▓▓█▒                              
        #               ▒█▓▒▓▓▓▓▓▓▓█▓         ██▓▒▒█▓▓▓▓▓▓▓██▓▓███▒ ██▓▒▓█                              
        #               ▒▓██░██▓▓▓▓▓▓         ██▓▓▓█▓▓▓▓▓▓▓█▓▓▓▓▓██  ██▒▒█                              
        #               ░▒▓▓ ▓█▓▓▓▓█▓         ██▓▓▓█▓▓▓█▓█▓▓▓██▓▒▓██  █▓ █░                             
        #                 ██ ▓█▓▓▓▓█▓         █▓▓████▓▓▓▓▒▓▓████▓▒███ ▒█▒▓▒                             
        #                 ▓█ ▓█▓▓▓▓█▓         █▓▓█████▓▒▓▓██████▓▓ ▒▒░ █▓▒▓                             
        #                 ▒█ ▓█▓▓▓▓█▓         █▓▓▓▓█▓██▓▓██▓▓▓██▓█ ░▓░▒ █▒█░                            
        #                 ▒█ ▓█▓▓▓▓█▓         █▓▓██▓▓█▓▓▓███▓▓▓██▓▓▓██▓ █▒▓▓                            
        #                 ░█░▓█▓▓▓▓█▓         █▓▓█▓▓▓██▓▓████▓▓▓▓▓▓▓██▓ █▓▒█░                           
        #                  █▒▓█▓▓▓▓█▓         █▓▓█▓▓████▓███▒ ░▓▓▓▓▓▓█▓ ▓█░▒▓                           
        #                  █▒▒█▓▓▓▓█▓         ██▓█▓▓███▓▓██▓   █▓▒▓▓▓█▓ ░██▓█░                          
        #                  █▓▒█▓▓▓▓█▓         ▓██▓▓████▓▓██▒░░ █▒▒▓▓▓██  ░██▓▒                          
        #                  ██▓█▓▓▓▓█▓         ▓██▓▓████████░░░ ▓▒▒▓▓███  ██▒                            
        #                  ▓█▓█▓▓▓▓█▓         ▓██▓▓███████▓░░░ ▒▒▓█▓███  ▒░                             
        #                  ▓█▓█▓▓▓▓█▓         ▓▓█▓▓███████▓░░░ ░▓██▓███                                 
        #                  ▒███▓▓▓▓█▓         ▓▓██▓███████▓░ ░ ░▓█▓▓███                                 
        #                  ░████▓▓▓▓▓         ▓▓█▓▓██▓████▓ ░░░ ▓█▓▓███                                 
        #                   ████▓▓▓▓▓         ▓▓▓▓▓██▓▓███▓ ░ ░ ▒█▓▓███                                 
        #                   ████▓▓█▓▓         ▓▓▓▓▓██▓▓███▒ ░░░ ▒██████                                 
        #                   █████████░        ▓▓▓▓▓██▓▓█▓█▒ ░░░░░▓██▓██                                 
        #                   ████▓▓███▒        ▓▓▓▓▒██▓▓███▒ ░░░░▒▒█████                                 
        #                   ▓███▓ ████        ▓▓▓ ▒██▓▒███▒  ░░▒▒▓█████                                 
        #                   ▓████  ███▒      ▒█▓▓ ▓██▓▒███▓ ░░▒▒▒██████                                 
        #                   ▒████   ▓██      █▓█▓ ▓██▓▒███▓ ░▒▒▓▓██████                                 
        #                   ░████    ░██   ░████  ▓███▓███▒ ░▒▓▒▓██████                                 
        #                    ████      ▓██████▓░  ▓█████▓█▓ ░▒▒▒▓██████                                 
        #                    ████         ▒▓▒░    ▓█████▓██░░▒▒▒▓▓█████                                 
        #                    ████                 ▓█████▓██▒░▒ ░▒▓█████                                 
        #                    ███▓                 ▓█████▓██░   ▒▓██████                                 
        #                    ███▓                 ▓█████▓██░ ░▒▓▓██████                                 
        #                    ███▓                 ▒█████▓██▓▓▒▓▓▓▓█████                                 
        #                    ███▓                 ▒████▓▓███▓▒▓▓▓██████░                                
        #                    ███▓                 ▒████▓▓██▓▓ ▓▓▓██████▒                                
        #                    ███▓                 ▓████▓▓██▒▒▒▓▓▓███▓██▓                                
        #                    ▓██▓                 ▓████▓▓██▒▓▒▓▓████▓███                                
        #                    ▓██                  ▓████▓▓██▓▒▒▓▓████▓███                                
        #                    ▓█▓                  ██████▓███▒▒▓▓████▓███▒                               
        #                     ██                 ░█████▓▓▓██▒▒▓▓████▓████                               
        #                     ██                 ▒█████▒▒▓██▒▒▓█████▓▓███▒                              
        #                     ▓█                 ▓█████▒░▓██▒▒▓█████▓▓████                              
        #                     ▒█░                ██████▒░▓█▓▒▒▓██████▓█████                             
        #                     ░█░                █▓████▓▓██▓░▓▓██████▓██████                            
        #                     ░█▓               ▒██████████ ░▓███████▓▓██████░▒▒▒▒▒▒▒░░                 
        #                      █▓               █▓████▓▓▓█▓▒▓▓██▓█▓▓██▓███████▓▓▓▓▓█▓███▓▓▓▒            
        #                      █▓         ▒▒▓▓▓██▓███▓▓▓██▒░██████▓▓▓▓▓████████▓▓▓▓▓▓▓▓▓▓▓███▓          
        #                     ▒▓█░       ▓██████▓▓▓▓▓▓▓▓▓█░░▓███▓▓▓▓▓▓▓███████████████▓▓▓█▓█▓▒          
        #                     ▓▒█▓   ▓▓▓███▓▓▓██▓▓▓▓▓▓▓▓▓▓░▒▓██▓▓▓▓▓▓▓▓▓██████████▓▓███████░            
        #                     ▒██▓ ▒██▓▓▓▓▓▓▓██▓▓▓▓▓▓▓▓▓▓▓▒▓██▓  ░▒▓▓▓▓▓████████▓█▓▓▓▓▓▓▓███▓░          
        #                      ██▒▓█▓▓▓▓▓▒▓██████▓▓▒▒░░  ▓▒▓██▓ ░▒▓▓▓▓█████████████▓██▓▓▓▓█▒            
        #                      ██  ▓████████▓▓▓▒        ▒▒▒▓██▓█████▓▒░▓████████▓██▓▓▓▓█▓▒▒             
        #                      ▒█▓▓██▓██▓▓▒░            ▒ ░▓████▓▒░    ░█████▓▓▓▓▓▓▓██▓█▒               
        #                             ░                 ▒███▓░          ▓█▓▓▓▓▓█████▓░                  
        #                                                ▓░               ▒▓█▓ ░▒░▒▒                    
        #                                                                   ▒▓                          
        #                                                                                               
        #                                                                                               
        #                          𝑫𝒂𝒓𝒆 𝒚𝒐𝒖 𝒆𝒏𝒕𝒆𝒓 𝒕𝒉𝒆 𝑽𝒂𝒍𝒆 𝒐𝒇 𝑻𝒆𝒎𝒑𝒕𝒂𝒕𝒊𝒐𝒏, 𝒕𝒓𝒂𝒗𝒆𝒍𝒍𝒆𝒓?                   
        #                                                                                               
        
        # UPDATE: This works on a giganto table with two PKs, but imperfectly. It doesn't do a full SCAN (although reorienting the query can force that), but it is doing some kind of slow lookup, I'm guessing it can skip half of the PK. The EXPLAIN QUERY PLAN is unusual
        # Therefore, we are scrapping this and moving to a simple two-stage select/delete system that we can rely on not going bananas because the SQLite query planner won't do what we want
        # The KISS approach works superfast, who would have guessed. This was 1.5s minimum overhead on a 30m row table, screwing with the autothrottle, and the other one does 20k row/s easy
        # I'm leaving this here because it was neat anyway and a good reminder of hubris
        
        # this mess is predicated on 'DELETE FROM blah LIMIT n;' not being supported by default compile time options in SQLite wew lad
        # so instead we set up the valid delete range with WITH
        # then we say 'delete from the table where there's a corresponding PK row in the temp table'. this should stay a fast SEARCH lookup even on multiple column pks
        # example query:
        # WITH magic_delete (tag_id,hash_id) AS ( SELECT tag_id,hash_id FROM deferred_delete_current_mappings_86_ac27467bdc0598d56d6fb64f1fc7826b LIMIT 25 )
        #   DELETE FROM deferred_delete_current_mappings_86_ac27467bdc0598d56d6fb64f1fc7826b WHERE EXISTS
        #     (SELECT 1 FROM magic_delete WHERE magic_delete.tag_id = deferred_delete_current_mappings_86_ac27467bdc0598d56d6fb64f1fc7826b.tag_id AND magic_delete.hash_id = deferred_delete_current_mappings_86_ac27467bdc0598d56d6fb64f1fc7826b.hash_id);

        
        pk_column_names_comma = ','.join( pk_column_names )
        
        with_phrase = f'WITH magic_delete ({pk_column_names_comma}) AS ( SELECT {pk_column_names_comma} FROM {table_name} LIMIT {n} )'
        
        pk_magic_join_predicates = [ f'magic_delete.{pk_column_name} = {table_name}.{pk_column_name}' for pk_column_name in pk_column_names ]
        
        pk_magic_join_str = ' AND '.join( pk_magic_join_predicates )
        
        exists_subquery = f'SELECT 1 FROM magic_delete WHERE {pk_magic_join_str}'
        
        delete_phrase = f'DELETE FROM {table_name} WHERE EXISTS ({exists_subquery})'
        
        return f'{with_phrase} {delete_phrase};'
        
    
    def _GetSimpleDeferredDeleteQueries( self, table_name, pk_column_names, n ):
        
        pk_column_names_comma = ','.join( pk_column_names )
        
        select_query = f'SELECT {pk_column_names_comma} FROM {table_name} LIMIT {n};'
        
        pk_predicates = [ f'{pk_column_name} = ?' for pk_column_name in pk_column_names ]
        
        pk_predicate_str = ' AND '.join( pk_predicates )
        
        delete_query = f'DELETE FROM {table_name} WHERE {pk_predicate_str};'
        
        return ( select_query, delete_query )
        
    
    def _GetTablePKColumnNames( self, table_name: str ):
        
        results = self._Execute( f'PRAGMA table_info( {table_name} );' ).fetchall()
        
        pk_column_names = [ name for ( cid, name, column_type, nullability, default_value, pk ) in results if pk > 0 ]
        
        if len( pk_column_names ) == 0:
            
            results = self._Execute( f'PRAGMA table_xinfo( {table_name} );' ).fetchall()
            
            if 'docid' in [ name for ( cid, name, column_type, nullability, default_value, pk, hidden ) in results ]:
                
                pk_column_names = [ 'docid' ]
                
            
        
        return pk_column_names
        
    
    def _TableHasAtLeastRowCount( self, name, minimum_row_count ):
        
        num_rows_found = 0
        BLOCK_SIZE = max( 1, min( 10000, int( minimum_row_count / 10 ) ) )
        
        cursor = self._Execute( 'SELECT 1 FROM {};'.format( name ) )
        
        while num_rows_found < minimum_row_count:
            
            result = cursor.fetchmany( BLOCK_SIZE )
            
            num_rows_this_loop = len( result )
            
            if num_rows_this_loop == 0:
                
                return False
                
            
            num_rows_found += num_rows_this_loop
            
        
        return True
        
    
    def _TableIsEmpty( self, name ):
        
        result = self._Execute( 'SELECT 1 FROM {};'.format( name ) ).fetchone()
        
        return result is None
        
    
    def AnalyzeDueTables( self, maintenance_mode = HC.MAINTENANCE_FORCED, stop_time = None, force_reanalyze = False ):
        
        names_to_analyze = self.GetTableNamesDueAnalysis( force_reanalyze = force_reanalyze )
        
        if len( names_to_analyze ) > 0:
            
            job_status = ClientThreading.JobStatus( maintenance_mode = maintenance_mode, cancellable = True )
            
            try:
                
                job_status.SetStatusTitle( 'database maintenance - analyzing' )
                
                CG.client_controller.pub( 'modal_message', job_status )
                
                for name in HydrusLists.IterateListRandomlyAndFast( names_to_analyze ):
                    
                    CG.client_controller.frame_splash_status.SetText( 'analyzing ' + name )
                    job_status.SetStatusText( 'analyzing ' + name )
                    
                    time.sleep( 0.02 )
                    
                    started = HydrusTime.GetNowPrecise()
                    
                    self.AnalyzeTable( name )
                    
                    time_took = HydrusTime.GetNowPrecise() - started
                    
                    if time_took > 1:
                        
                        HydrusData.Print( 'Analyzed ' + name + ' in ' + HydrusTime.TimeDeltaToPrettyTimeDelta( time_took ) )
                        
                    
                    p1 = CG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time )
                    p2 = job_status.IsCancelled()
                    
                    if p1 or p2:
                        
                        break
                        
                    
                
                self._Execute( 'ANALYZE sqlite_master;' ) # this reloads the current stats into the query planner
                
                job_status.SetStatusText( 'done!' )
                
                HydrusData.Print( job_status.ToString() )
                
            finally:
                
                job_status.FinishAndDismiss( 10 )
                
            
        
    
    def AnalyzeTable( self, name ):
        
        num_rows = 0
        
        do_it = True
        
        result = self._Execute( 'SELECT num_rows FROM analyze_timestamps WHERE name = ?;', ( name, ) ).fetchone()
        
        if result is not None:
            
            ( num_rows, ) = result
            
            # if we have previously analyzed a table with some data but the table is now empty, we do not want a new analyze
            if num_rows > 0 and self._TableIsEmpty( name ):
                
                do_it = False
                
            
        
        if do_it:
            
            self._Execute( 'ANALYZE ' + name + ';' )
            
            ( num_rows, ) = self._Execute( 'SELECT COUNT( * ) FROM ' + name + ';' ).fetchone()
            
        
        self._Execute( 'DELETE FROM analyze_timestamps WHERE name = ?;', ( name, ) )
        
        self._Execute( 'INSERT OR IGNORE INTO analyze_timestamps ( name, num_rows, timestamp_ms ) VALUES ( ?, ?, ? );', ( name, num_rows, HydrusTime.GetNowMS() ) )
        
    
    def ClearOrphanTables( self ):
        
        all_table_names = set()
        
        db_names = [ name for ( index, name, path ) in self._Execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp', 'durable_temp' ) ]
        
        for db_name in db_names:
            
            table_names = self._STS( self._Execute( 'SELECT name FROM {}.sqlite_master WHERE type = ?;'.format( db_name ), ( 'table', ) ) )
            
            table_names = { f'{db_name}.{table_name}' for table_name in table_names }
            
            all_table_names.update( table_names )
            
        
        all_surplus_table_names = set()
        
        for module in self._modules:
            
            surplus_table_names = module.GetSurplusServiceTableNames( all_table_names )
            
            all_surplus_table_names.update( surplus_table_names )
            
        
        if len( all_surplus_table_names ) == 0:
            
            HydrusData.ShowText( 'No orphan tables!' )
            
        
        for table_name in all_surplus_table_names:
            
            HydrusData.ShowText( f'Cleared orphan table "{table_name}"' )
            
            self.DeferredDropTable( table_name )
            
        
    
    def DeferredDropTable( self, table_name: str ):
        
        if not self._TableExists( table_name ):
            
            return
            
        
        table_name_without_schema = table_name
        
        if '.' in table_name:
            
            ( schema, table_name_without_schema ) = table_name.split( '.', 1 )
            
        
        new_table_name = 'deferred_delete_{}_{}'.format( table_name_without_schema, os.urandom( 16 ).hex() )
        
        self._Execute( f'ALTER TABLE {table_name} RENAME TO {new_table_name};' )
        
        result = self._Execute( 'SELECT num_rows FROM analyze_timestamps WHERE name = ?;', ( table_name_without_schema, ) ).fetchone()
        
        if result is None:
            
            num_rows = None
            
        else:
            
            ( num_rows, ) = result
            
        
        self._Execute( 'INSERT INTO deferred_delete_tables ( name, num_rows ) VALUES ( ?, ? );', ( new_table_name, num_rows ) )
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_deferred_delete_database_maintenance_new_work' )
        
    
    def DoDeferredDeleteTablesWork( self, time_to_stop: float ):
        
        # OK, so what I wanted to do was 'DELETE FROM {table_name} LIMIT {num_we_want_to_delete}' here and autothrottle that, but hey what do you know default sqlite doesn't come compiled with this very useful feature, hooray
        # Therefore we have to go ring around the rosies and PRAGMA ourselves a nonsense solution that is less efficient but does do the arbitrary-length chunking we want
        
        # just a side note here, we cannot trust num_rows_still_to_delete. it comes from an ANALYZE call from potentially years ago and caps out at like 100 million
        ( deletee_table_name, num_rows_still_to_delete ) = self._GetDeferredDeleteTableName()
        
        still_work_to_do = True
        
        if deletee_table_name is None:
            
            still_work_to_do = False
            
            return still_work_to_do
            
        
        if not self._TableExists( deletee_table_name ):
            
            # weird situation, let's bail out now
            self._Execute( 'DELETE FROM deferred_delete_tables WHERE name = ?;', ( deletee_table_name, ) )
            
            return still_work_to_do
            
        
        pk_column_names = self._GetTablePKColumnNames( deletee_table_name )
        
        if len( pk_column_names ) == 0:
            
            # weird situation, let's burn CPU time as needed and bail out now
            self._Execute( f'DROP TABLE {deletee_table_name};' )
            
            self._Execute( 'DELETE FROM deferred_delete_tables WHERE name = ?;', ( deletee_table_name, ) )
            
            return still_work_to_do
            
        
        num_we_want_to_delete = 10
        
        while not HydrusTime.TimeHasPassedFloat( time_to_stop ):
            
            time_started = HydrusTime.GetNowPrecise()
            
            ( select_query, delete_query ) = self._GetSimpleDeferredDeleteQueries( deletee_table_name, pk_column_names, num_we_want_to_delete )
            
            deletee_rows = self._Execute( select_query ).fetchall()
            
            if len( deletee_rows ) == 0:
                
                self._DropTable( deletee_table_name )
                
                return still_work_to_do
                
            else:
                
                self._ExecuteMany( delete_query, deletee_rows )
                
                if num_rows_still_to_delete is not None:
                    
                    num_rows_still_to_delete -= num_we_want_to_delete
                    
                    # ok the ANALYZE num_rows is out of date or was capped by a giganto table. let's set to unknown since we just don't know
                    if num_rows_still_to_delete < 0:
                        
                        num_rows_still_to_delete = None
                        
                    
                    self._Execute( 'UPDATE deferred_delete_tables SET num_rows = ? WHERE name = ?;', ( num_rows_still_to_delete, deletee_table_name ) )
                    
                
                time_this_cycle_took = HydrusTime.GetNowPrecise() - time_started
                
                n_per_second = num_we_want_to_delete / time_this_cycle_took
                
                remaining_time = time_to_stop - HydrusTime.GetNowFloat()
                
                if remaining_time > 0:
                    
                    # now we go for a very cautious autothrottle
                    
                    ideal_hyperspeed = remaining_time * n_per_second
                    
                    ideal_acceleration = ideal_hyperspeed - num_we_want_to_delete
                    
                    cautious_acceleration = ideal_acceleration // 5
                    
                    num_we_want_to_delete += cautious_acceleration
                    
                    num_we_want_to_delete = max( 10, num_we_want_to_delete )
                    num_we_want_to_delete = min( 100000, num_we_want_to_delete ) # in my test situation, we could ramp up to 1.7m pretty quick wew
                    
                
            
        
        return still_work_to_do
        
    
    def GetDeferredDeleteTableData( self ):
        
        data = self._Execute( 'SELECT name, num_rows FROM deferred_delete_tables;' ).fetchall()
        
        return data
        
    
    def GetLastShutdownWorkTime( self ):
        
        result = self._Execute( 'SELECT last_shutdown_work_time FROM last_shutdown_work_time;' ).fetchone()
        
        if result is None:
            
            return 0
            
        
        ( last_shutdown_work_time, ) = result
        
        return last_shutdown_work_time
        
    
    def GetTableNamesDueAnalysis( self, force_reanalyze = False ) -> list:
        
        db_names = [ name for ( index, name, path ) in self._Execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp', 'durable_temp' ) ]
        
        all_names = set()
        
        for db_name in db_names:
            
            all_names.update( ( name for ( name, ) in self._Execute( 'SELECT name FROM {}.sqlite_master WHERE type = ?;'.format( db_name ), ( 'table', ) ) ) )
            
        
        all_names.discard( 'sqlite_stat1' )
        
        all_names = { name for name in all_names if not name.startswith( 'deferred_delete_' ) }
        
        if force_reanalyze:
            
            names_to_analyze = list( all_names )
            
        else:
            
            # Some tables get huge real fast (usually after syncing to big repo)
            # If they have only ever been analyzed with incomplete or empty data, they work slow
            # Analyze on a small table takes ~1ms, so let's instead do smaller tables more frequently and try to catch them as they grow
            
            boundaries = []
            
            boundaries.append( ( 100, True, 6 * 3600 ) )
            boundaries.append( ( 10000, True, 3 * 86400 ) )
            boundaries.append( ( 100000, False, 3 * 30 * 86400 ) )
            boundaries.append( ( 10000000, False, 12 * 30 * 86400 ) )
            # anything bigger than 10M rows will now not be analyzed
            
            existing_names_to_info = { name : ( num_rows, HydrusTime.SecondiseMS( timestamp_ms ) ) for ( name, num_rows, timestamp_ms ) in self._Execute( 'SELECT name, num_rows, timestamp_ms FROM analyze_timestamps;' ) }
            
            names_to_analyze = []
            
            for name in all_names:
                
                if name in existing_names_to_info:
                    
                    ( num_rows, timestamp ) = existing_names_to_info[ name ]
                    
                    for ( row_limit_for_this_boundary, can_analyze_immediately, period ) in boundaries:
                        
                        if num_rows > row_limit_for_this_boundary:
                            
                            continue
                            
                        
                        if not HydrusTime.TimeHasPassed( timestamp + period ):
                            
                            continue
                            
                        
                        if can_analyze_immediately:
                            
                            # if it has grown, send up to user, as it could be huge. else do it now
                            if self._TableHasAtLeastRowCount( name, row_limit_for_this_boundary ):
                                
                                names_to_analyze.append( name )
                                
                            else:
                                
                                self.AnalyzeTable( name )
                                
                            
                        else:
                            
                            names_to_analyze.append( name )
                            
                        
                    
                else:
                    
                    names_to_analyze.append( name )
                    
                
            
        
        return names_to_analyze
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def GetVacuumData( self ):
        
        vacuum_data = {}
        
        for ( name, filename ) in self._db_filenames.items():
            
            path = os.path.join( self._db_dir, filename )
            
            ( page_size, ) = self._Execute( 'PRAGMA {}.page_size;'.format( name ) ).fetchone()
            ( page_count, ) = self._Execute( 'PRAGMA {}.page_count;'.format( name ) ).fetchone()
            ( freelist_count, ) = self._Execute( 'PRAGMA {}.freelist_count;'.format( name ) ).fetchone()
            
            result = self._Execute( 'SELECT timestamp_ms FROM vacuum_timestamps WHERE name = ?;', ( name, ) ).fetchone()
            
            if result is None:
                
                last_vacuumed_ms = None
                
            else:
                
                ( last_vacuumed_ms, ) = result
                
            
            this_vacuum_data = {}
            
            this_vacuum_data[ 'path' ] = path
            this_vacuum_data[ 'page_size' ] = page_size
            this_vacuum_data[ 'page_count' ] = page_count
            this_vacuum_data[ 'freelist_count' ] = freelist_count
            this_vacuum_data[ 'last_vacuumed_ms' ] = last_vacuumed_ms
            
            vacuum_data[ name ] = this_vacuum_data
            
        
        return vacuum_data
        
    
    def RegisterShutdownWork( self ):
        
        self._Execute( 'DELETE FROM last_shutdown_work_time;' )
        
        self._Execute( 'INSERT INTO last_shutdown_work_time ( last_shutdown_work_time ) VALUES ( ? );', ( HydrusTime.GetNow(), ) )
        
    
    def RegisterSuccessfulVacuum( self, name: str ):
        
        self._Execute( 'DELETE FROM vacuum_timestamps WHERE name = ?;', ( name, ) )
        
        self._Execute( 'INSERT OR IGNORE INTO vacuum_timestamps ( name, timestamp_ms ) VALUES ( ?, ? );', ( name, HydrusTime.GetNowMS() ) )
        
    
    def TouchAnalyzeNewTables( self ):
        
        # just a little thing to run after creating and populating tables that will scan any actual new stuff
        
        # TODO: Actually lmao, this didn't do what I wanted and often caused megalag
        pass
        
        # self.GetTableNamesDueAnalysis()
        
