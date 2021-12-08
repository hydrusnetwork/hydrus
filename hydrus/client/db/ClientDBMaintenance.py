import os
import random
import sqlite3
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBModule

class ClientDBMaintenance( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, db_dir: str, db_filenames: typing.Collection[ str ] ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client db maintenance', cursor )
        
        self._db_dir = db_dir
        self._db_filenames = db_filenames
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.last_shutdown_work_time' : ( 'CREATE TABLE IF NOT EXISTS {} ( last_shutdown_work_time INTEGER );', 400 ),
            'main.analyze_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( name TEXT, num_rows INTEGER, timestamp INTEGER );', 400 ),
            'main.vacuum_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( name TEXT, timestamp INTEGER );', 400 )
        }
        
    
    def _TableHasAtLeastRowCount( self, name, row_count ):
        
        cursor = self._Execute( 'SELECT 1 FROM {};'.format( name ) )
        
        for i in range( row_count ):
            
            r = cursor.fetchone()
            
            if r is None:
                
                return False
                
            
        
        return True
        
    
    def _TableIsEmpty( self, name ):
        
        result = self._Execute( 'SELECT 1 FROM {};'.format( name ) )
        
        return result is None
        
    
    def AnalyzeDueTables( self, maintenance_mode = HC.MAINTENANCE_FORCED, stop_time = None, force_reanalyze = False ):
        
        names_to_analyze = self.GetTableNamesDueAnalysis( force_reanalyze = force_reanalyze )
        
        if len( names_to_analyze ) > 0:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            try:
                
                job_key.SetStatusTitle( 'database maintenance - analyzing' )
                
                HG.client_controller.pub( 'modal_message', job_key )
                
                random.shuffle( names_to_analyze )
                
                for name in names_to_analyze:
                    
                    HG.client_controller.frame_splash_status.SetText( 'analyzing ' + name )
                    job_key.SetVariable( 'popup_text_1', 'analyzing ' + name )
                    
                    time.sleep( 0.02 )
                    
                    started = HydrusData.GetNowPrecise()
                    
                    self.AnalyzeTable( name )
                    
                    time_took = HydrusData.GetNowPrecise() - started
                    
                    if time_took > 1:
                        
                        HydrusData.Print( 'Analyzed ' + name + ' in ' + HydrusData.TimeDeltaToPrettyTimeDelta( time_took ) )
                        
                    
                    p1 = HG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time )
                    p2 = job_key.IsCancelled()
                    
                    if p1 or p2:
                        
                        break
                        
                    
                
                self._Execute( 'ANALYZE sqlite_master;' ) # this reloads the current stats into the query planner
                
                job_key.SetVariable( 'popup_text_1', 'done!' )
                
                HydrusData.Print( job_key.ToString() )
                
            finally:
                
                job_key.Finish()
                
                job_key.Delete( 10 )
                
            
        
    
    def AnalyzeTable( self, name ):
        
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
        
        self._Execute( 'INSERT OR IGNORE INTO analyze_timestamps ( name, num_rows, timestamp ) VALUES ( ?, ?, ? );', ( name, num_rows, HydrusData.GetNow() ) )
        
    
    def GetLastShutdownWorkTime( self ):
        
        result = self._Execute( 'SELECT last_shutdown_work_time FROM last_shutdown_work_time;' ).fetchone()
        
        if result is None:
            
            return 0
            
        
        ( last_shutdown_work_time, ) = result
        
        return last_shutdown_work_time
        
    
    def GetTableNamesDueAnalysis( self, force_reanalyze = False ):
        
        db_names = [ name for ( index, name, path ) in self._Execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp', 'durable_temp' ) ]
        
        all_names = set()
        
        for db_name in db_names:
            
            all_names.update( ( name for ( name, ) in self._Execute( 'SELECT name FROM {}.sqlite_master WHERE type = ?;'.format( db_name ), ( 'table', ) ) ) )
            
        
        all_names.discard( 'sqlite_stat1' )
        
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
            # anything bigger than 100k rows will now not be analyzed
            
            existing_names_to_info = { name : ( num_rows, timestamp ) for ( name, num_rows, timestamp ) in self._Execute( 'SELECT name, num_rows, timestamp FROM analyze_timestamps;' ) }
            
            names_to_analyze = []
            
            for name in all_names:
                
                if name in existing_names_to_info:
                    
                    ( num_rows, timestamp ) = existing_names_to_info[ name ]
                    
                    for ( row_limit_for_this_boundary, can_analyze_immediately, period ) in boundaries:
                        
                        if num_rows > row_limit_for_this_boundary:
                            
                            continue
                            
                        
                        if not HydrusData.TimeHasPassed( timestamp + period ):
                            
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
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def GetVacuumData( self ):
        
        vacuum_data = {}
        
        for ( name, filename ) in self._db_filenames.items():
            
            path = os.path.join( self._db_dir, filename )
            
            ( page_size, ) = self._Execute( 'PRAGMA {}.page_size;'.format( name ) ).fetchone()
            ( page_count, ) = self._Execute( 'PRAGMA {}.page_count;'.format( name ) ).fetchone()
            ( freelist_count, ) = self._Execute( 'PRAGMA {}.freelist_count;'.format( name ) ).fetchone()
            
            result = self._Execute( 'SELECT timestamp FROM vacuum_timestamps WHERE name = ?;', ( name, ) ).fetchone()
            
            if result is None:
                
                last_vacuumed = None
                
            else:
                
                ( last_vacuumed, ) = result
                
            
            this_vacuum_data = {}
            
            this_vacuum_data[ 'path' ] = path
            this_vacuum_data[ 'page_size' ] = page_size
            this_vacuum_data[ 'page_count' ] = page_count
            this_vacuum_data[ 'freelist_count' ] = freelist_count
            this_vacuum_data[ 'last_vacuumed' ] = last_vacuumed
            
            vacuum_data[ name ] = this_vacuum_data
            
        
        return vacuum_data
        
    
    def RegisterShutdownWork( self ):
        
        self._Execute( 'DELETE from last_shutdown_work_time;' )
        
        self._Execute( 'INSERT INTO last_shutdown_work_time ( last_shutdown_work_time ) VALUES ( ? );', ( HydrusData.GetNow(), ) )
        
    
    def RegisterSuccessfulVacuum( self, name: str ):
        
        self._Execute( 'DELETE FROM vacuum_timestamps WHERE name = ?;', ( name, ) )
        
        self._Execute( 'INSERT OR IGNORE INTO vacuum_timestamps ( name, timestamp ) VALUES ( ?, ? );', ( name, HydrusData.GetNow() ) )
        
    
    def TouchAnalyzeNewTables( self ):
        
        # just a little thing to run after creating and populating tables that will scan any actual new stuff
        
        self.GetTableNamesDueAnalysis()
        
