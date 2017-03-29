import cProfile
import cStringIO
import distutils.version
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusPaths
import os
import psutil
import Queue
import random
import sqlite3
import sys
import tempfile
import threading
import traceback
import time

CONNECTION_REFRESH_TIME = 60 * 30

def CanVacuum( db_path, stop_time = None ):
    
    try:
        
        db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        c = db.cursor()
        
        ( page_size, ) = c.execute( 'PRAGMA page_size;' ).fetchone()
        ( page_count, ) = c.execute( 'PRAGMA page_count;' ).fetchone()
        ( freelist_count, ) = c.execute( 'PRAGMA freelist_count;' ).fetchone()
        
        db_size = ( page_count - freelist_count ) * page_size
        
        if stop_time is not None:
            
            approx_vacuum_speed_mb_per_s = 1048576 * 1
            
            approx_vacuum_duration = db_size / approx_vacuum_speed_mb_per_s
            
            time_i_will_have_to_start = stop_time - approx_vacuum_duration
            
            if HydrusData.TimeHasPassed( time_i_will_have_to_start ):
                
                return False
                
            
        
        ( db_dir, db_filename ) = os.path.split( db_path )
        
        ( has_space, reason ) = HydrusPaths.HasSpaceForDBTransaction( db_dir, db_size )
        
        return has_space
        
    except Exception as e:
        
        HydrusData.Print( 'Could not determine whether to vacuum or not:' )
        
        HydrusData.PrintException( e )
        
        return False
        
    
def SetupDBCreatePragma( c, no_wal = False ):
    
    c.execute( 'PRAGMA auto_vacuum = 0;' ) # none
    
    if HC.PLATFORM_WINDOWS:
        
        c.execute( 'PRAGMA page_size = 4096;' )
        
    
    if not no_wal:
        
        c.execute( 'PRAGMA journal_mode = WAL;' )
        
    
    c.execute( 'PRAGMA synchronous = 1;' )
    
def VacuumDB( db_path ):
    
    db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
    
    c = db.cursor()
    
    ( previous_journal_mode, ) = c.execute( 'PRAGMA journal_mode;' ).fetchone()
    
    fast_big_transaction_wal = not distutils.version.LooseVersion( sqlite3.sqlite_version ) < distutils.version.LooseVersion( '3.11.0' )
    
    if previous_journal_mode == 'wal' and not fast_big_transaction_wal:
        
        c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
        
    
    if HC.PLATFORM_WINDOWS:
        
        ideal_page_size = 4096
        
    else:
        
        ideal_page_size = 1024
        
    
    ( page_size, ) = c.execute( 'PRAGMA page_size;' ).fetchone()
    
    if page_size != ideal_page_size:
        
        c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
        c.execute( 'PRAGMA page_size = ' + str( ideal_page_size ) + ';' )
        
    
    c.execute( 'VACUUM;' )
    
    if previous_journal_mode == 'wal':
        
        c.execute( 'PRAGMA journal_mode = WAL;' )
        
    
class HydrusDB( object ):
    
    READ_WRITE_ACTIONS = []
    UPDATE_WAIT = 2
    
    def __init__( self, controller, db_dir, db_name, no_wal = False ):
        
        self._controller = controller
        self._db_dir = db_dir
        self._db_name = db_name
        self._no_wal = no_wal
        
        self._in_transaction = False
        
        self._connection_timestamp = 0
        
        main_db_filename = db_name
        
        if not main_db_filename.endswith( '.db' ):
            
            main_db_filename += '.db'
            
        
        self._db_filenames = {}
        
        self._db_filenames[ 'main' ] = main_db_filename
        
        self._InitExternalDatabases()
        
        if distutils.version.LooseVersion( sqlite3.sqlite_version ) < distutils.version.LooseVersion( '3.11.0' ):
            
            self._fast_big_transaction_wal = False
            
        else:
            
            self._fast_big_transaction_wal = True
            
        
        self._is_first_start = False
        self._is_db_updated = False
        self._local_shutdown = False
        self._loop_finished = False
        self._ready_to_serve_requests = False
        self._could_not_initialise = False
        
        self._jobs = Queue.PriorityQueue()
        self._pubsubs = []
        
        self._currently_doing_job = False
        
        self._db = None
        self._c = None
        
        if os.path.exists( os.path.join( self._db_dir, self._db_filenames[ 'main' ] ) ):
            
            # open and close to clean up in case last session didn't close well
            
            self._InitDB()
            self._CloseDBCursor()
            
        
        self._InitDB()
        
        ( version, ) = self._c.execute( 'SELECT version FROM version;' ).fetchone()
        
        if version < HC.SOFTWARE_VERSION - 50:
            
            raise Exception( 'Your current database version of hydrus ' + str( version ) + ' is too old for this software version ' + str( HC.SOFTWARE_VERSION ) + ' to update. Please try updating with version ' + str( version + 45 ) + ' or earlier first.' )
            
        
        if version < 238:
            
            raise Exception( 'Unfortunately, this software cannot update your database. Please try installing version 238 first.' )
            
        
        while version < HC.SOFTWARE_VERSION:
            
            time.sleep( self.UPDATE_WAIT )
            
            try:
                
                self._BeginImmediate()
                
            except Exception as e:
                
                raise HydrusExceptions.DBAccessException( HydrusData.ToUnicode( e ) )
                
            
            try:
                
                self._UpdateDB( version )
                
                self._Commit()
                
                self._is_db_updated = True
                
            except:
                
                e = Exception( 'Updating the ' + self._db_name + ' db to version ' + str( version + 1 ) + ' caused this error:' + os.linesep + traceback.format_exc() )
                
                try:
                    
                    self._Rollback()
                    
                except Exception as rollback_e:
                    
                    HydrusData.Print( 'When the update failed, attempting to rollback the database failed.' )
                    
                    HydrusData.PrintException( rollback_e )
                    
                
                raise e
                
            
            ( version, ) = self._c.execute( 'SELECT version FROM version;' ).fetchone()
            
        
        self._CloseDBCursor()
        
        threading.Thread( target = self.MainLoop, name = 'Database Main Loop' ).start()
        
        while not self._ready_to_serve_requests:
            
            time.sleep( 0.1 )
            
            if self._could_not_initialise:
                
                raise Exception( 'Could not initialise the db! Error written to the log!' )
                
            
        
    
    def _AttachExternalDatabases( self ):
        
        for ( name, filename ) in self._db_filenames.items():
            
            if name == 'main':
                
                continue
                
            
            db_path = os.path.join( self._db_dir, self._db_filenames[ name ] )
            
            if not os.path.exists( db_path ):
                
                db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
                
                c = db.cursor()
                
                SetupDBCreatePragma( c, no_wal = self._no_wal )
                
                del c
                del db
                
            
            self._c.execute( 'ATTACH ? AS ' + name + ';', ( db_path, ) )
            
        
    
    def _BeginImmediate( self ):
        
        if self._in_transaction:
            
            HydrusData.Print( 'Received a call to begin, but was already in a transaction!' )
            
        else:
            
            self._c.execute( 'BEGIN IMMEDIATE;' )
            
            self._in_transaction = True
            
        
    
    def _CleanUpCaches( self ):
        
        pass
        
    
    def _CloseDBCursor( self ):
        
        if self._db is not None:
            
            if self._in_transaction:
                
                self._Commit()
                
            
            self._c.close()
            self._db.close()
            
            del self._c
            del self._db
            
            self._db = None
            self._c = None
            
        
    
    def _Commit( self ):
        
        if self._in_transaction:
            
            self._c.execute( 'COMMIT;' )
            
            self._in_transaction = False
            
        else:
            
            HydrusData.Print( 'Received a call to commit, but was not in a transaction!' )
            
        
    
    def _CreateDB( self ):
        
        raise NotImplementedError()
        
    
    def _CreateIndex( self, table_name, columns, unique = False ):
        
        if '.' in table_name:
            
            table_name_simple = table_name.split( '.' )[1]
            
        else:
            
            table_name_simple = table_name
            
        
        index_name = table_name + '_' + '_'.join( columns ) + '_index'
        
        if unique:
            
            create_phrase = 'CREATE UNIQUE INDEX IF NOT EXISTS '
            
        else:
            
            create_phrase = 'CREATE INDEX IF NOT EXISTS '
            
        
        on_phrase = ' ON ' + table_name_simple + ' (' + ', '.join( columns ) + ');'
        
        statement = create_phrase + index_name + on_phrase
        
        self._c.execute( statement )
        
    
    def _GetRowCount( self ):
        
        row_count = self._c.rowcount
        
        if row_count == -1: return 0
        else: return row_count
        
    
    def _InitCaches( self ):
        
        pass
        
    
    def _InitDB( self ):
        
        create_db = False
        
        db_path = os.path.join( self._db_dir, self._db_filenames[ 'main' ] )
        
        if not os.path.exists( db_path ):
            
            create_db = True
            
        
        self._InitDBCursor()
        
        result = self._c.execute( 'SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?;', ( 'table', 'version' ) ).fetchone()
        
        if result is None:
            
            create_db = True
            
        
        if create_db:
            
            self._is_first_start = True
            
            self._CreateDB()
            
        
    
    def _InitDBCursor( self ):
        
        self._CloseDBCursor()
        
        db_path = os.path.join( self._db_dir, self._db_filenames[ 'main' ] )
        
        db_just_created = not os.path.exists( db_path )
        
        self._db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        self._connection_timestamp = HydrusData.GetNow()
        
        self._c = self._db.cursor()
        
        self._c.execute( 'PRAGMA main.cache_size = -10000;' )
        
        self._c.execute( 'ATTACH ":memory:" AS mem;' )
        
        self._AttachExternalDatabases()
        
        db_names = [ name for ( index, name, path ) in self._c.execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
        
        for db_name in db_names:
            
            self._c.execute( 'PRAGMA ' + db_name + '.cache_size = -10000;' )
            
            if self._no_wal:
                
                self._c.execute( 'PRAGMA ' + db_name + '.journal_mode = TRUNCATE;' )
                
                self._c.execute( 'PRAGMA ' + db_name + '.synchronous = 2;' )
                
                self._c.execute( 'SELECT * FROM ' + db_name + '.sqlite_master;' ).fetchone()
                
            else:
                
                self._c.execute( 'PRAGMA ' + db_name + '.journal_mode = WAL;' )
                
                self._c.execute( 'PRAGMA ' + db_name + '.synchronous = 1;' )
                
                try:
                    
                    self._c.execute( 'SELECT * FROM ' + db_name + '.sqlite_master;' ).fetchone()
                    
                except sqlite3.OperationalError:
                    
                    HydrusData.DebugPrint( traceback.format_exc() )
                    
                    def create_no_wal_file():
                        
                        HydrusGlobals.controller.CreateNoWALFile()
                        
                        self._no_wal = True
                        
                    
                    if db_just_created:
                        
                        del self._c
                        del self._db
                        
                        os.remove( db_path )
                        
                        create_no_wal_file()
                        
                        self._InitDBCursor()
                        
                    else:
                        
                        self._c.execute( 'PRAGMA ' + db_name + '.journal_mode = TRUNCATE;' )
                        
                        self._c.execute( 'PRAGMA ' + db_name + '.synchronous = 2;' )
                        
                        self._c.execute( 'SELECT * FROM ' + db_name + '.sqlite_master;' ).fetchone()
                        
                        create_no_wal_file()
                        
                    
                
            
        
    
    def _InitDiskCache( self ):
        
        pass
        
    
    def _InitExternalDatabases( self ):
        
        pass
        
    
    def _ManageDBError( self, job, e ):
        
        raise NotImplementedError()
        
    
    def _ProcessJob( self, job ):
        
        job_type = job.GetType()
        
        ( action, args, kwargs ) = job.GetCallableTuple()
        
        try:
            
            if job_type in ( 'read_write', 'write' ):
                
                self._BeginImmediate()
                
            
            if job_type in ( 'read', 'read_write' ): result = self._Read( action, *args, **kwargs )
            elif job_type in ( 'write' ): result = self._Write( action, *args, **kwargs )
            
            if self._in_transaction:
                
                self._Commit()
                
            
            for ( topic, args, kwargs ) in self._pubsubs:
                
                self._controller.pub( topic, *args, **kwargs )
                
            
            if job.IsSynchronous():
                
                job.PutResult( result )
                
            
        except Exception as e:
            
            if self._in_transaction:
                
                try:
                    
                    self._Rollback()
                    
                except Exception as rollback_e:
                    
                    HydrusData.Print( 'When the transaction failed, attempting to rollback the database failed.' )
                    
                    HydrusData.PrintException( rollback_e )
                    
                
            
            self._ManageDBError( job, e )
            
        
    
    def _Read( self, action, *args, **kwargs ):
        
        raise NotImplementedError()
        
    
    def _ReportStatus( self, text ):
        
        HydrusData.Print( text )
        
    
    def _Rollback( self ):
        
        if self._in_transaction:
            
            self._c.execute( 'ROLLBACK;' )
            
            self._in_transaction = False
            
        else:
            
            HydrusData.Print( 'Received a call to rollback, but was not in a transaction!' )
            
        
    
    def _SelectFromList( self, select_statement, xs ):
        
        # issue here is that doing a simple blah_id = ? is real quick and cacheable but doing a lot of fetchone()s is slow
        # blah_id IN ( 1, 2, 3 ) is fast to execute but not cacheable and doing the str() list splay takes time so there is initial lag
        # doing the temporaryintegertable trick works well for gigantic lists you refer to frequently but it is super laggy when you sometimes are only selecting four things
        # blah_id IN ( ?, ?, ? ) is fast and cacheable but there's a small limit (1024 is too many) to the number of params sql can handle
        # so lets do the latter but break it into 256-strong chunks to get a good medium
        
        # this will take a select statement with %s like so:
        # SELECT blah_id, blah FROM blahs WHERE blah_id IN %s;
        
        MAX_CHUNK_SIZE = 256
        
        # do this just so we aren't always reproducing this long string for gigantic lists
        # and also so we aren't overmaking it when this gets spammed with a lot of len() == 1 calls
        if len( xs ) >= MAX_CHUNK_SIZE:
            
            max_statement = select_statement % ( '(' + ','.join( '?' * MAX_CHUNK_SIZE ) + ')' )
            
        
        for chunk in HydrusData.SplitListIntoChunks( xs, MAX_CHUNK_SIZE ):
            
            if len( chunk ) == MAX_CHUNK_SIZE:
                
                chunk_statement = max_statement
                
            else:
                
                chunk_statement = select_statement % ( '(' + ','.join( '?' * len( chunk ) ) + ')' )
                
            
            for row in self._c.execute( chunk_statement, chunk ):
                
                yield row
                
            
        
    
    def _SelectFromListFetchAll( self, select_statement, xs ):
        
        return [ row for row in self._SelectFromList( select_statement, xs ) ]
        
    
    def _STI( self, iterable_cursor ):
        
        # strip singleton tuples to an iterator
        
        return ( item for ( item, ) in iterable_cursor )
        
    
    def _STL( self, iterable_cursor ):
        
        # strip singleton tuples to a list
        
        return [ item for ( item, ) in iterable_cursor ]
        
    
    def _STS( self, iterable_cursor ):
        
        # strip singleton tuples to a set
        
        return { item for ( item, ) in iterable_cursor }
        
    
    def _UpdateDB( self, version ):
        
        raise NotImplementedError()
        
    
    def _Write( self, action, *args, **kwargs ):
        
        raise NotImplementedError()
        
    
    def pub_after_commit( self, topic, *args, **kwargs ):
        
        self._pubsubs.append( ( topic, args, kwargs ) )
        
    
    def CurrentlyDoingJob( self ):
        
        return self._currently_doing_job
        
    
    def IsDBUpdated( self ):
        
        return self._is_db_updated
        
    
    def IsFirstStart( self ):
        
        return self._is_first_start
        
    
    def LoopIsFinished( self ):
        
        return self._loop_finished
        
    
    def JobsQueueEmpty( self ):
        
        return self._jobs.empty()
        
    
    def MainLoop( self ):
        
        try:
            
            self._InitDBCursor() # have to reinitialise because the thread id has changed
            
            self._InitDiskCache()
            
            self._InitCaches()
            
        except:
            
            HydrusData.Print( traceback.format_exc() )
            
            self._could_not_initialise = True
            
            return
            
        
        self._ready_to_serve_requests = True
        
        error_count = 0
        
        while not ( ( self._local_shutdown or self._controller.ModelIsShutdown() ) and self._jobs.empty() ):
            
            try:
                
                ( priority, job ) = self._jobs.get( timeout = 0.5 )
                
                self._currently_doing_job = True
                
                self._controller.pub( 'refresh_status' )
                
                self._pubsubs = []
                
                try:
                    
                    if HydrusGlobals.db_profile_mode:
                        
                        summary = 'Profiling ' + job.ToString()
                        
                        HydrusData.ShowText( summary )
                        
                        HydrusData.Profile( summary, 'self._ProcessJob( job )', globals(), locals() )
                        
                    else:
                        
                        self._ProcessJob( job )
                        
                    
                    error_count = 0
                    
                except:
                    
                    error_count += 1
                    
                    if error_count > 5: raise
                    
                    self._jobs.put( ( priority, job ) ) # couldn't lock db; put job back on queue
                    
                    time.sleep( 5 )
                    
                
                self._currently_doing_job = False
                
                self._controller.pub( 'refresh_status' )
                
            except Queue.Empty:
                
                pass # no jobs in the past little while; let's just check if we should shutdown
                
            
            if HydrusData.TimeHasPassed( self._connection_timestamp + CONNECTION_REFRESH_TIME ): # just to clear out the journal files
                
                self._InitDBCursor()
                
            
        
        self._CleanUpCaches()
        
        self._CloseDBCursor()
        
        self._loop_finished = True
        
    
    def Read( self, action, priority, *args, **kwargs ):
        
        if action in self.READ_WRITE_ACTIONS: job_type = 'read_write'
        else: job_type = 'read'
        
        synchronous = True
        
        job = HydrusData.JobDatabase( job_type, synchronous, action, *args, **kwargs )
        
        if self._controller.ModelIsShutdown():
            
            raise HydrusExceptions.ShutdownException( 'Application has shut down!' )
            
        
        self._jobs.put( ( priority + 1, job ) ) # +1 so all writes of equal priority can clear out first
        
        return job.GetResult()
        
    
    def ReadyToServeRequests( self ):
        
        return self._ready_to_serve_requests
        
    
    def Shutdown( self ):
        
        self._local_shutdown = True
        
    
    def SimpleRead( self, action, *args, **kwargs ):
        
        return self.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
    
    def SimpleWrite( self, action, *args, **kwargs ):
        
        return self.Write( action, HC.HIGH_PRIORITY, False, *args, **kwargs )
        
    
    def SimpleWriteSynchronous( self, action, *args, **kwargs ):
        
        return self.Write( action, HC.LOW_PRIORITY, True, *args, **kwargs )
        
    
    def Write( self, action, priority, synchronous, *args, **kwargs ):
        
        job_type = 'write'
        
        job = HydrusData.JobDatabase( job_type, synchronous, action, *args, **kwargs )
        
        if self._controller.ModelIsShutdown():
            
            raise HydrusExceptions.ShutdownException( 'Application has shut down!' )
            
        
        self._jobs.put( ( priority, job ) )
        
        if synchronous: return job.GetResult()
        
    
class TemporaryIntegerTable( object ):
    
    def __init__( self, cursor, integer_iterable, column_name ):
        
        self._cursor = cursor
        self._integer_iterable = integer_iterable
        self._column_name = column_name
        
        self._table_name = 'mem.tempint' + os.urandom( 32 ).encode( 'hex' )
        
    
    def __enter__( self ):
        
        self._cursor.execute( 'CREATE TABLE ' + self._table_name + ' ( ' + self._column_name + ' INTEGER PRIMARY KEY );' )
        
        self._cursor.executemany( 'INSERT INTO ' + self._table_name + ' ( ' + self._column_name + ' ) VALUES ( ? );', ( ( i, ) for i in self._integer_iterable ) )
        
        return self._table_name
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self._cursor.execute( 'DROP TABLE ' + self._table_name + ';' )
        
        return False
        
    
