import cProfile
import cStringIO
import distutils.version
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import os
import pstats
import Queue
import random
import sqlite3
import sys
import threading
import traceback
import time

class HydrusDB( object ):
    
    READ_WRITE_ACTIONS = []
    UPDATE_WAIT = 2
    
    def __init__( self, controller, db_dir, db_name, no_wal = False ):
        
        self._controller = controller
        self._db_dir = db_dir
        self._db_name = db_name
        self._no_wal = no_wal
        
        main_db_filename = db_name
        
        if not main_db_filename.endswith( '.db' ):
            
            main_db_filename += '.db'
            
        
        self._db_filenames = {}
        
        self._db_filenames[ 'main' ] = main_db_filename
        
        if distutils.version.LooseVersion( sqlite3.sqlite_version ) < distutils.version.LooseVersion( '3.11.0' ):
            
            self._fast_big_transaction_wal = False
            
        else:
            
            self._fast_big_transaction_wal = True
            
        
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
        
        if version < HC.SOFTWARE_VERSION - 50: raise Exception( 'Your current version of hydrus ' + str( version ) + ' is too old for this version ' + str( HC.SOFTWARE_VERSION ) + ' to update. Please try updating with version ' + str( version + 45 ) + ' or earlier first.' )
        
        while version < HC.SOFTWARE_VERSION:
            
            time.sleep( self.UPDATE_WAIT )
            
            try: self._c.execute( 'BEGIN IMMEDIATE' )
            except Exception as e:
                
                raise HydrusExceptions.DBAccessException( HydrusData.ToUnicode( e ) )
                
            
            try:
                
                self._UpdateDB( version )
                
                self._c.execute( 'COMMIT' )
                
            except:
                
                self._c.execute( 'ROLLBACK' )
                
                raise Exception( 'Updating the ' + self._db_name + ' db to version ' + str( version + 1 ) + ' caused this error:' + os.linesep + traceback.format_exc() )
                
            
            ( version, ) = self._c.execute( 'SELECT version FROM version;' ).fetchone()
            
        
        self._CloseDBCursor()
        
        threading.Thread( target = self.MainLoop, name = 'Database Main Loop' ).start()
        
        while not self._ready_to_serve_requests:
            
            time.sleep( 0.1 )
            
            if self._could_not_initialise:
                
                raise Exception( 'Could not initialise the db! Error written to the log!' )
                
            
        
    
    def _AttachExternalDatabases( self ):
        
        pass
        
    
    def _CleanUpCaches( self ):
        
        pass
        
    
    def _CloseDBCursor( self ):
        
        if self._db is not None:
            
            self._c.close()
            self._db.close()
            
            del self._c
            del self._db
            
            self._db = None
            self._c = None
            
        
    
    def _CreateDB( self ):
        
        raise NotImplementedError()
        
    
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
            
            self._CreateDB()
            
        
    
    def _InitDBCursor( self ):
        
        self._CloseDBCursor()
        
        db_path = os.path.join( self._db_dir, self._db_filenames[ 'main' ] )
        
        db_just_created = not os.path.exists( db_path )
        
        self._db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        self._db.create_function( 'hydrus_hamming', 2, HydrusData.GetHammingDistance )
        
        self._c = self._db.cursor()
        
        self._c.execute( 'PRAGMA cache_size = -150000;' )
        
        if self._no_wal:
            
            self._c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
            
            self._c.execute( 'PRAGMA synchronous = 2;' )
            
            self._c.execute( 'SELECT * FROM sqlite_master;' ).fetchone()
            
        else:
            
            self._c.execute( 'PRAGMA journal_mode = WAL;' )
            
            self._c.execute( 'PRAGMA synchronous = 1;' )
            
            try:
                
                self._c.execute( 'SELECT * FROM sqlite_master;' ).fetchone()
                
            except sqlite3.OperationalError:
                
                traceback.print_exc()
                
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
                    
                    self._c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
                    
                    self._c.execute( 'PRAGMA synchronous = 2;' )
                    
                    self._c.execute( 'SELECT * FROM sqlite_master;' ).fetchone()
                    
                    create_no_wal_file()
                    
                
            
        
        self._c.execute( 'ATTACH ":memory:" AS mem;' )
        
        self._AttachExternalDatabases()
        
    
    def _ManageDBError( self, job, e ):
        
        raise NotImplementedError()
        
    
    def _ProcessJob( self, job ):
        
        job_type = job.GetType()
        
        ( action, args, kwargs ) = job.GetCallableTuple()
        
        in_transaction = False
        
        try:
            
            if job_type == 'read': self._c.execute( 'BEGIN DEFERRED' )
            elif job_type in ( 'read_write', 'write' ): self._c.execute( 'BEGIN IMMEDIATE' )
            
            in_transaction = True
            
            if job_type in ( 'read', 'read_write' ): result = self._Read( action, *args, **kwargs )
            elif job_type in ( 'write' ): result = self._Write( action, *args, **kwargs )
            
            self._c.execute( 'COMMIT' )
            
            for ( topic, args, kwargs ) in self._pubsubs:
                
                self._controller.pub( topic, *args, **kwargs )
                
            
            if job.IsSynchronous():
                
                job.PutResult( result )
                
            
        except Exception as e:
            
            if in_transaction: self._c.execute( 'ROLLBACK' )
            
            self._ManageDBError( job, e )
            
        
    
    def _Read( self, action, *args, **kwargs ):
        
        raise NotImplementedError()
        
    
    def _ReportStatus( self, text ):
        
        HydrusData.Print( text )
        
    
    def _UpdateDB( self, version ):
        
        raise NotImplementedError()
        
    
    def _Write( self, action, *args, **kwargs ):
        
        raise NotImplementedError()
        
    
    def pub_after_commit( self, topic, *args, **kwargs ):
        
        self._pubsubs.append( ( topic, args, kwargs ) )
        
    
    def CurrentlyDoingJob( self ):
        
        return self._currently_doing_job
        
    
    def LoopIsFinished( self ):
        
        return self._loop_finished
        
    
    def JobsQueueEmpty( self ):
        
        return self._jobs.empty()
        
    
    def MainLoop( self ):
        
        try:
            
            self._InitDBCursor() # have to reinitialise because the thread id has changed
            
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
                        
                        HydrusData.ShowText( 'Profiling ' + job.ToString() )
                        
                        HydrusData.Profile( 'self._ProcessJob( job )', globals(), locals() )
                        
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
        
    