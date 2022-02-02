import collections
import distutils.version
import os
import queue
import sqlite3
import traceback
import time

from hydrus.core import HydrusDBBase
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusEncryption
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths

def CheckCanVacuum( db_path, stop_time = None ):
    
    db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
    
    c = db.cursor()
    
    CheckCanVacuumCursor( db_path, c, stop_time = stop_time )
    
def CheckCanVacuumCursor( db_path, c, stop_time = None ):
    
    ( page_size, ) = c.execute( 'PRAGMA page_size;' ).fetchone()
    ( page_count, ) = c.execute( 'PRAGMA page_count;' ).fetchone()
    ( freelist_count, ) = c.execute( 'PRAGMA freelist_count;' ).fetchone()
    
    CheckCanVacuumData( db_path, page_size, page_count, freelist_count, stop_time = stop_time )
    
def CheckCanVacuumData( db_path, page_size, page_count, freelist_count, stop_time = None ):
    
    db_size = ( page_count - freelist_count ) * page_size
    
    if stop_time is not None:
        
        approx_vacuum_duration = GetApproxVacuumDuration( db_size )
        
        time_i_will_have_to_start = stop_time - approx_vacuum_duration
        
        if HydrusData.TimeHasPassed( time_i_will_have_to_start ):
            
            raise Exception( 'I believe you need about ' + HydrusData.TimeDeltaToPrettyTimeDelta( approx_vacuum_duration ) + ' to vacuum, but there is not enough time allotted.' )
            
        
    
    db_dir = os.path.dirname( db_path )
    
    HydrusDBBase.CheckHasSpaceForDBTransaction( db_dir, db_size )
    
def GetApproxVacuumDuration( db_size ):
    
    vacuum_estimate = int( db_size * 1.2 )
    
    approx_vacuum_speed_mb_per_s = 1048576 * 1
    
    approx_vacuum_duration = vacuum_estimate // approx_vacuum_speed_mb_per_s
    
    return approx_vacuum_duration
    
def ReadFromCancellableCursor( cursor, largest_group_size, cancelled_hook = None ):
    
    if cancelled_hook is None:
        
        return cursor.fetchall()
        
    
    NUM_TO_GET = 1
    
    results = []
    
    group_of_results = cursor.fetchmany( NUM_TO_GET )
    
    while len( group_of_results ) > 0:
        
        results.extend( group_of_results )
        
        if cancelled_hook():
            
            break
            
        
        if NUM_TO_GET < largest_group_size:
            
            NUM_TO_GET *= 2
            
        
        group_of_results = cursor.fetchmany( NUM_TO_GET )
        
    
    return results
    
def ReadLargeIdQueryInSeparateChunks( cursor, select_statement, chunk_size ):
    
    table_name = 'tempbigread' + os.urandom( 32 ).hex()
    
    cursor.execute( 'CREATE TEMPORARY TABLE ' + table_name + ' ( job_id INTEGER PRIMARY KEY AUTOINCREMENT, temp_id INTEGER );' )
    
    cursor.execute( 'INSERT INTO ' + table_name + ' ( temp_id ) ' + select_statement ) # given statement should end in semicolon, so we are good
    
    num_to_do = cursor.rowcount
    
    if num_to_do is None or num_to_do == -1:
        
        num_to_do = 0
        
    
    i = 0
    
    while i < num_to_do:
        
        chunk = [ temp_id for ( temp_id, ) in cursor.execute( 'SELECT temp_id FROM ' + table_name + ' WHERE job_id BETWEEN ? AND ?;', ( i, i + chunk_size - 1 ) ) ]
        
        i += len( chunk )
        
        yield ( chunk, i, num_to_do )
        
    
    cursor.execute( 'DROP TABLE ' + table_name + ';' )
    
def VacuumDB( db_path ):
    
    db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
    
    c = db.cursor()
    
    fast_big_transaction_wal = not distutils.version.LooseVersion( sqlite3.sqlite_version ) < distutils.version.LooseVersion( '3.11.0' )
    
    if HG.db_journal_mode == 'WAL' and not fast_big_transaction_wal:
        
        c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
        
    
    if HC.PLATFORM_WINDOWS:
        
        ideal_page_size = 4096
        
    else:
        
        ideal_page_size = 1024
        
    
    ( page_size, ) = c.execute( 'PRAGMA page_size;' ).fetchone()
    
    if page_size != ideal_page_size:
        
        c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
        c.execute( 'PRAGMA page_size = ' + str( ideal_page_size ) + ';' )
        
    
    c.execute( 'PRAGMA auto_vacuum = 0;' ) # none
    
    c.execute( 'VACUUM;' )
    
    c.execute( 'PRAGMA journal_mode = {};'.format( HG.db_journal_mode ) )
    
class HydrusDB( HydrusDBBase.DBBase ):
    
    READ_WRITE_ACTIONS = []
    UPDATE_WAIT = 2
    
    def __init__( self, controller, db_dir, db_name ):
        
        if HydrusPaths.GetFreeSpace( db_dir ) < 500 * 1048576:
            
            raise Exception( 'Sorry, it looks like the db partition has less than 500MB, please free up some space.' )
            
        
        HydrusDBBase.DBBase.__init__( self )
        
        self._controller = controller
        self._db_dir = db_dir
        self._db_name = db_name
        
        self._modules = []
        
        HydrusDBBase.TemporaryIntegerTableNameCache()
        
        self._ssl_cert_filename = '{}.crt'.format( self._db_name )
        self._ssl_key_filename = '{}.key'.format( self._db_name )
        
        self._ssl_cert_path = os.path.join( self._db_dir, self._ssl_cert_filename )
        self._ssl_key_path = os.path.join( self._db_dir, self._ssl_key_filename )
        
        main_db_filename = db_name
        
        if not main_db_filename.endswith( '.db' ):
            
            main_db_filename += '.db'
            
        
        self._db_filenames = {}
        
        self._db_filenames[ 'main' ] = main_db_filename
        
        self._durable_temp_db_filename = db_name + '.temp.db'
        
        durable_temp_db_path = os.path.join( self._db_dir, self._durable_temp_db_filename )
        
        if os.path.exists( durable_temp_db_path ):
            
            HydrusPaths.DeletePath( durable_temp_db_path )
            
            wal_lad = durable_temp_db_path + '-wal'
            
            if os.path.exists( wal_lad ):
                
                HydrusPaths.DeletePath( wal_lad )
                
            
            shm_lad = durable_temp_db_path + '-shm'
            
            if os.path.exists( shm_lad ):
                
                HydrusPaths.DeletePath( shm_lad )
                
            
            HydrusData.Print( 'Found and deleted the durable temporary database on boot. The last exit was probably not clean.' )
            
        
        self._InitExternalDatabases()
        
        self._is_first_start = False
        self._is_db_updated = False
        self._local_shutdown = False
        self._pause_and_disconnect = False
        self._loop_finished = False
        self._ready_to_serve_requests = False
        self._could_not_initialise = False
        
        self._jobs = queue.Queue()
        
        self._currently_doing_job = False
        self._current_status = ''
        self._current_job_name = ''
        
        self._db = None
        self._is_connected = False
        
        self._cursor_transaction_wrapper = None
        
        if os.path.exists( os.path.join( self._db_dir, self._db_filenames[ 'main' ] ) ):
            
            # open and close to clean up in case last session didn't close well
            
            self._InitDB()
            self._CloseDBConnection()
            
        
        self._InitDB()
        
        ( version, ) = self._Execute( 'SELECT version FROM version;' ).fetchone()
        
        if version > HC.SOFTWARE_VERSION:
            
            self._ReportOverupdatedDB( version )
            
        
        if version < ( HC.SOFTWARE_VERSION - 15 ):
            
            self._ReportUnderupdatedDB( version )
            
        
        if version < HC.SOFTWARE_VERSION - 50:
            
            raise Exception( 'Your current database version of hydrus ' + str( version ) + ' is too old for this software version ' + str( HC.SOFTWARE_VERSION ) + ' to update. Please try updating with version ' + str( version + 45 ) + ' or earlier first.' )
            
        
        self._RepairDB( version )
        
        while version < HC.SOFTWARE_VERSION:
            
            time.sleep( self.UPDATE_WAIT )
            
            try:
                
                self._cursor_transaction_wrapper.BeginImmediate()
                
            except Exception as e:
                
                raise HydrusExceptions.DBAccessException( str( e ) )
                
            
            try:
                
                self._UpdateDB( version )
                
                self._cursor_transaction_wrapper.Commit()
                
                self._is_db_updated = True
                
            except:
                
                e = Exception( 'Updating the ' + self._db_name + ' db to version ' + str( version + 1 ) + ' caused this error:' + os.linesep + traceback.format_exc() )
                
                try:
                    
                    self._cursor_transaction_wrapper.Rollback()
                    
                except Exception as rollback_e:
                    
                    HydrusData.Print( 'When the update failed, attempting to rollback the database failed.' )
                    
                    HydrusData.PrintException( rollback_e )
                    
                
                raise e
                
            
            ( version, ) = self._Execute( 'SELECT version FROM version;' ).fetchone()
            
        
        self._CloseDBConnection()
        
        self._controller.CallToThreadLongRunning( self.MainLoop )
        
        while not self._ready_to_serve_requests:
            
            time.sleep( 0.1 )
            
            if self._could_not_initialise:
                
                raise Exception( 'Could not initialise the db! Error written to the log!' )
                
            
        
    
    def _AnalyzeTempTable( self, temp_table_name ):
        
        # this is useful to do after populating a temp table so the query planner can decide which index to use in a big join that uses it
        
        self._Execute( 'ANALYZE {};'.format( temp_table_name ) )
        self._Execute( 'ANALYZE mem.sqlite_master;' ) # this reloads the current stats into the query planner, may no longer be needed
        
    
    def _AttachExternalDatabases( self ):
        
        for ( name, filename ) in self._db_filenames.items():
            
            if name == 'main':
                
                continue
                
            
            db_path = os.path.join( self._db_dir, filename )
            
            if os.path.exists( db_path ) and not HydrusPaths.FileisWriteable( db_path ):
                
                raise HydrusExceptions.DBAccessException( '"{}" seems to be read-only!'.format( db_path ) )
                
            
            self._Execute( 'ATTACH ? AS ' + name + ';', ( db_path, ) )
            
        
        db_path = os.path.join( self._db_dir, self._durable_temp_db_filename )
        
        self._Execute( 'ATTACH ? AS durable_temp;', ( db_path, ) )
        
    
    def _CleanAfterJobWork( self ):
        
        self._cursor_transaction_wrapper.CleanPubSubs()
        
    
    def _CloseDBConnection( self ):
        
        HydrusDBBase.TemporaryIntegerTableNameCache.instance().Clear()
        
        if self._db is not None:
            
            if self._cursor_transaction_wrapper.InTransaction():
                
                self._cursor_transaction_wrapper.Commit()
                
            
            self._CloseCursor()
            
            self._db.close()
            
            del self._db
            
            self._db = None
            
            self._is_connected = False
            
            self._cursor_transaction_wrapper = None
            
            self._UnloadModules()
            
        
    
    def _CreateDB( self ):
        
        raise NotImplementedError()
        
    
    def _DisplayCatastrophicError( self, text ):
        
        message = 'The db encountered a serious error! This is going to be written to the log as well, but here it is for a screenshot:'
        message += os.linesep * 2
        message += text
        
        HydrusData.DebugPrint( message )
        
    
    def _DoAfterJobWork( self ):
        
        self._cursor_transaction_wrapper.DoPubSubs()
        
    
    def _GenerateDBJob( self, job_type, synchronous, action, *args, **kwargs ):
        
        return HydrusData.JobDatabase( job_type, synchronous, action, *args, **kwargs )
        
    
    def _GetPossibleAdditionalDBFilenames( self ):
        
        return [ self._ssl_cert_filename, self._ssl_key_filename ]
        
    
    def _InitCaches( self ):
        
        pass
        
    
    def _InitDB( self ):
        
        create_db = False
        
        db_path = os.path.join( self._db_dir, self._db_filenames[ 'main' ] )
        
        if not os.path.exists( db_path ):
            
            create_db = True
            
            external_db_paths = [ os.path.join( self._db_dir, self._db_filenames[ db_name ] ) for db_name in self._db_filenames if db_name != 'main' ]
            
            existing_external_db_paths = [ external_db_path for external_db_path in external_db_paths if os.path.exists( external_db_path ) ]
            
            if len( existing_external_db_paths ) > 0:
                
                message = 'Although the external files, "{}" do exist, the main database file, "{}", does not! This makes for an invalid database, and the program will now quit. Please contact hydrus_dev if you do not know how this happened or need help recovering from hard drive failure.'
                
                message = message.format( ', '.join( existing_external_db_paths ), db_path )
                
                raise HydrusExceptions.DBAccessException( message )
                
            
        
        self._InitDBConnection()
        
        result = self._Execute( 'SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?;', ( 'table', 'version' ) ).fetchone()
        
        if result is None:
            
            create_db = True
            
        
        if create_db:
            
            self._is_first_start = True
            
            self._CreateDB()
            
            self._cursor_transaction_wrapper.CommitAndBegin()
            
        
    
    def _InitDBConnection( self ):
        
        self._CloseDBConnection()
        
        db_path = os.path.join( self._db_dir, self._db_filenames[ 'main' ] )
        
        try:
            
            if os.path.exists( db_path ) and not HydrusPaths.FileisWriteable( db_path ):
                
                raise HydrusExceptions.DBAccessException( '"{}" seems to be read-only!'.format( db_path ) )
                
            
            self._db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
            
            c = self._db.cursor()
            
            self._SetCursor( c )
            
            self._is_connected = True
            
            self._cursor_transaction_wrapper = HydrusDBBase.DBCursorTransactionWrapper( self._c, HG.db_transaction_commit_period )
            
            if HG.no_db_temp_files:
                
                self._Execute( 'PRAGMA temp_store = 2;' ) # use memory for temp store exclusively
                
            
            self._AttachExternalDatabases()
            
            self._LoadModules()
            
            self._Execute( 'ATTACH ":memory:" AS mem;' )
            
        except HydrusExceptions.DBAccessException as e:
            
            raise
            
        except Exception as e:
            
            raise HydrusExceptions.DBAccessException( 'Could not connect to database! If the answer is not obvious to you, please let hydrus dev know. Error follows:' + os.linesep * 2 + str( e ) )
            
        
        HydrusDBBase.TemporaryIntegerTableNameCache.instance().Clear()
        
        # durable_temp is not excluded here
        db_names = [ name for ( index, name, path ) in self._Execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
        
        for db_name in db_names:
            
            # MB -> KB
            cache_size = HG.db_cache_size * 1024
            
            self._Execute( 'PRAGMA {}.cache_size = -{};'.format( db_name, cache_size ) )
            
            self._Execute( 'PRAGMA {}.journal_mode = {};'.format( db_name, HG.db_journal_mode ) )
            
            if HG.db_journal_mode in ( 'PERSIST', 'WAL' ):
                
                self._Execute( 'PRAGMA {}.journal_size_limit = {};'.format( db_name, 1024 ** 3 ) ) # 1GB for now
                
            
            self._Execute( 'PRAGMA {}.synchronous = {};'.format( db_name, HG.db_synchronous ) )
            
            try:
                
                self._Execute( 'SELECT * FROM {}.sqlite_master;'.format( db_name ) ).fetchone()
                
            except sqlite3.OperationalError as e:
                
                message = 'The database seemed valid, but hydrus failed to read basic data from it. You may need to run the program in a different journal mode using --db_journal_mode. Full error information:'
                
                message += os.linesep * 2
                message += str( e )
                
                HydrusData.DebugPrint( message )
                
                raise HydrusExceptions.DBAccessException( message )
                
            
        
        try:
            
            self._cursor_transaction_wrapper.BeginImmediate()
            
        except Exception as e:
            
            if 'locked' in str( e ):
                
                raise HydrusExceptions.DBAccessException( 'Database appeared to be locked. Please ensure there is not another client already running on this database, and then try restarting the client.' )
                
            
            raise HydrusExceptions.DBAccessException( str( e ) )
            
        
    
    def _InitExternalDatabases( self ):
        
        pass
        
    
    def _LoadModules( self ):
        
        pass
        
    
    def _ManageDBError( self, job, e ):
        
        raise NotImplementedError()
        
    
    def _ProcessJob( self, job ):
        
        job_type = job.GetType()
        
        ( action, args, kwargs ) = job.GetCallableTuple()
        
        try:
            
            if job_type in ( 'read_write', 'write' ):
                
                self._current_status = 'db write locked'
                
                self._cursor_transaction_wrapper.NotifyWriteOccuring()
                
            else:
                
                self._current_status = 'db read locked'
                
            
            self.publish_status_update()
            
            if job_type in ( 'read', 'read_write' ):
                
                result = self._Read( action, *args, **kwargs )
                
            elif job_type in ( 'write' ):
                
                result = self._Write( action, *args, **kwargs )
                
            
            if job.IsSynchronous():
                
                job.PutResult( result )
                
            
            self._cursor_transaction_wrapper.Save()
            
            if self._cursor_transaction_wrapper.TimeToCommit():
                
                self._current_status = 'db committing'
                
                self.publish_status_update()
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            
            self._DoAfterJobWork()
            
        except Exception as e:
            
            self._ManageDBError( job, e )
            
            try:
                
                self._cursor_transaction_wrapper.Rollback()
                
            except Exception as rollback_e:
                
                HydrusData.Print( 'When the transaction failed, attempting to rollback the database failed. Please restart the client as soon as is convenient.' )
                
                self._CloseDBConnection()
                
                self._InitDBConnection()
                
                HydrusData.PrintException( rollback_e )
                
            
        finally:
            
            self._CleanAfterJobWork()
            
            self._current_status = ''
            
            self.publish_status_update()
            
        
    
    def _Read( self, action, *args, **kwargs ):
        
        raise NotImplementedError()
        
    
    def _RepairDB( self, version ):
        
        for module in self._modules:
            
            module.Repair( version, self._cursor_transaction_wrapper )
            
        
    
    def _ReportOverupdatedDB( self, version ):
        
        pass
        
    
    def _ReportUnderupdatedDB( self, version ):
        
        pass
        
    
    def _ReportStatus( self, text ):
        
        HydrusData.Print( text )
        
    
    def _ShrinkMemory( self ):
        
        self._Execute( 'PRAGMA shrink_memory;' )
        
    
    def _UnloadModules( self ):
        
        pass
        
    
    def _UpdateDB( self, version ):
        
        raise NotImplementedError()
        
    
    def _Write( self, action, *args, **kwargs ):
        
        raise NotImplementedError()
        
    
    def publish_status_update( self ):
        
        pass
        
    
    def CurrentlyDoingJob( self ):
        
        return self._currently_doing_job
        
    
    def GetApproxTotalFileSize( self ):
        
        total = 0
        
        for filename in self._db_filenames.values():
            
            path = os.path.join( self._db_dir, filename )
            
            total += os.path.getsize( path )
            
        
        return total
        
    
    def GetSSLPaths( self ):
        
        # create ssl keys
        
        cert_here = os.path.exists( self._ssl_cert_path )
        key_here = os.path.exists( self._ssl_key_path )
        
        if cert_here ^ key_here:
            
            raise Exception( 'While creating the server database, only one of the paths "{}" and "{}" existed. You can create a db with these files already in place, but please either delete the existing file (to have hydrus generate its own pair) or find the other in the pair (to use your own).'.format( self._ssl_cert_path, self._ssl_key_path ) )
            
        elif not ( cert_here or key_here ):
            
            HydrusData.Print( 'Generating new cert/key files.' )
            
            if not HydrusEncryption.OPENSSL_OK:
                
                raise Exception( 'The database was asked for ssl cert and keys to start either the server or the client api in https. The files do not exist yet, so the database wanted to create new ones, but unfortunately PyOpenSSL is not available, so this cannot be done. If you are running from source, please install this module using pip. Or drop in your own client.crt/client.key or server.crt/server.key files in the db directory.' )
                
            
            HydrusEncryption.GenerateOpenSSLCertAndKeyFile( self._ssl_cert_path, self._ssl_key_path )
            
        
        return ( self._ssl_cert_path, self._ssl_key_path )
        
    
    def GetStatus( self ):
        
        return ( self._current_status, self._current_job_name )
        
    
    def IsConnected( self ):
        
        return self._is_connected
        
    
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
            
            self._InitDBConnection() # have to reinitialise because the thread id has changed
            
            self._InitCaches()
            
        except:
            
            self._DisplayCatastrophicError( traceback.format_exc() )
            
            self._could_not_initialise = True
            
            return
            
        
        self._ready_to_serve_requests = True
        
        error_count = 0
        
        while not ( ( self._local_shutdown or HG.model_shutdown ) and self._jobs.empty() ):
            
            try:
                
                job = self._jobs.get( timeout = 1 )
                
                self._currently_doing_job = True
                self._current_job_name = job.ToString()
                
                self.publish_status_update()
                
                try:
                    
                    if HG.db_report_mode:
                        
                        summary = 'Running db job: ' + job.ToString()
                        
                        HydrusData.ShowText( summary )
                        
                    
                    if HG.profile_mode:
                        
                        summary = 'Profiling db job: ' + job.ToString()
                        
                        HydrusData.Profile( summary, 'self._ProcessJob( job )', globals(), locals(), min_duration_ms = HG.db_profile_min_job_time_ms )
                        
                    else:
                        
                        self._ProcessJob( job )
                        
                    
                    error_count = 0
                    
                except:
                    
                    error_count += 1
                    
                    if error_count > 5:
                        
                        raise
                        
                    
                    self._jobs.put( job ) # couldn't lock db; put job back on queue
                    
                    time.sleep( 5 )
                    
                
                self._currently_doing_job = False
                self._current_job_name = ''
                
                self.publish_status_update()
                
            except queue.Empty:
                
                if self._cursor_transaction_wrapper.TimeToCommit():
                    
                    self._cursor_transaction_wrapper.CommitAndBegin()
                    
                
            
            if self._pause_and_disconnect:
                
                self._CloseDBConnection()
                
                while self._pause_and_disconnect:
                    
                    if self._local_shutdown or HG.model_shutdown:
                        
                        break
                        
                    
                    time.sleep( 1 )
                    
                
                self._InitDBConnection()
                
            
        
        self._CloseDBConnection()
        
        temp_path = os.path.join( self._db_dir, self._durable_temp_db_filename )
        
        HydrusPaths.DeletePath( temp_path )
        
        self._loop_finished = True
        
    
    def PauseAndDisconnect( self, pause_and_disconnect ):
        
        self._pause_and_disconnect = pause_and_disconnect
        
    
    def Read( self, action, *args, **kwargs ):
        
        if action in self.READ_WRITE_ACTIONS:
            
            job_type = 'read_write'
            
        else:
            
            job_type = 'read'
            
        
        synchronous = True
        
        job = self._GenerateDBJob( job_type, synchronous, action, *args, **kwargs )
        
        if HG.model_shutdown:
            
            raise HydrusExceptions.ShutdownException( 'Application has shut down!' )
            
        
        self._jobs.put( job )
        
        return job.GetResult()
        
    
    def ReadyToServeRequests( self ):
        
        return self._ready_to_serve_requests
        
    
    def Shutdown( self ):
        
        self._local_shutdown = True
        
    
    def Write( self, action, synchronous, *args, **kwargs ):
        
        job_type = 'write'
        
        job = self._GenerateDBJob( job_type, synchronous, action, *args, **kwargs )
        
        if HG.model_shutdown:
            
            raise HydrusExceptions.ShutdownException( 'Application has shut down!' )
            
        
        self._jobs.put( job )
        
        if synchronous: return job.GetResult()
        
    
