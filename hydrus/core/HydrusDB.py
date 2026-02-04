import os
import queue
import sqlite3
import threading
import traceback
import time

from hydrus.core import HydrusDBBase
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusEncryption
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusExit
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusProfiling
from hydrus.core import HydrusTime

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
        
        if HydrusTime.TimeHasPassed( time_i_will_have_to_start ):
            
            raise Exception( 'I believe you need about ' + HydrusTime.TimeDeltaToPrettyTimeDelta( approx_vacuum_duration ) + ' to vacuum, but there is not enough time allotted.' )
            
        
    
    db_dir = os.path.dirname( db_path )
    
    HydrusDBBase.CheckHasSpaceForDBTransaction( db_dir, db_size )
    

def CheckCanVacuumInto( db_path, stop_time = None ):
    
    db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
    
    c = db.cursor()
    
    CheckCanVacuumIntoCursor( db_path, c, stop_time = stop_time )
    

def CheckCanVacuumIntoCursor( db_path, c, stop_time = None ):
    
    ( page_size, ) = c.execute( 'PRAGMA page_size;' ).fetchone()
    ( page_count, ) = c.execute( 'PRAGMA page_count;' ).fetchone()
    ( freelist_count, ) = c.execute( 'PRAGMA freelist_count;' ).fetchone()
    
    CheckCanVacuumIntoData( db_path, page_size, page_count, freelist_count, stop_time = stop_time )
    

def CheckCanVacuumIntoData( db_path, page_size, page_count, freelist_count, stop_time = None ):
    
    db_size = ( page_count - freelist_count ) * page_size
    
    if stop_time is not None:
        
        approx_vacuum_duration = GetApproxVacuumIntoDuration( db_size )
        
        time_i_will_have_to_start = stop_time - approx_vacuum_duration
        
        if HydrusTime.TimeHasPassed( time_i_will_have_to_start ):
            
            raise Exception( 'I believe you need about ' + HydrusTime.TimeDeltaToPrettyTimeDelta( approx_vacuum_duration ) + ' to vacuum, but there is not enough time allotted.' )
            
        
    
    db_dir = os.path.dirname( db_path )
    
    HydrusDBBase.CheckHasSpaceForDBTransaction( db_dir, db_size, no_temp_needed = True )
    

def GetApproxVacuumDuration( db_size ):
    
    vacuum_estimate = int( db_size * 1.2 )
    
    approx_vacuum_speed_mb_per_s = 1048576 * 1
    
    approx_vacuum_duration = vacuum_estimate // approx_vacuum_speed_mb_per_s
    
    return approx_vacuum_duration
    

def GetApproxVacuumIntoDuration( db_size ):
    
    # I've seen 200MB/s on a 600MB file in memory
    # I've seen 30MB/s on a 4GB file not in memory
    # I'll presume a real 20GB file is going to trend just a bit lower, but we can adjust this if we get some IRL data
    
    vacuum_estimate = int( db_size * 1.2 )
    
    approx_vacuum_speed_mb_per_s = 1048576 * 10
    
    approx_vacuum_duration = vacuum_estimate // approx_vacuum_speed_mb_per_s
    
    return approx_vacuum_duration
    

def ReadLargeIdQueryInSeparateChunks( cursor, select_statement, chunk_size ):
    
    table_name = 'tempbigread' + os.urandom( 32 ).hex()
    
    cursor.execute( 'CREATE TEMPORARY TABLE ' + table_name + ' ( job_id INTEGER PRIMARY KEY AUTOINCREMENT, temp_id INTEGER );' )
    
    cursor.execute( 'INSERT INTO ' + table_name + ' ( temp_id ) ' + select_statement ) # given statement should end in semicolon, so we are good
    
    num_to_do = cursor.rowcount
    
    if num_to_do is None or num_to_do == -1:
        
        num_to_do = 0
        
    
    i = 0
    num_done = 0
    
    while num_done < num_to_do:
        
        chunk = [ temp_id for ( temp_id, ) in cursor.execute( 'SELECT temp_id FROM ' + table_name + ' WHERE job_id BETWEEN ? AND ?;', ( i, i + ( chunk_size - 1 ) ) ) ]
        
        i += chunk_size
        num_done += len( chunk )
        
        yield ( chunk, num_done, num_to_do )
        
    
    cursor.execute( 'DROP TABLE ' + table_name + ';' )
    

def VacuumDB( db_path ):
    
    db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
    
    c = db.cursor()
    
    fast_big_transaction_wal = not sqlite3.sqlite_version_info < ( 3, 11, 0 )
    
    if HG.db_journal_mode == 'WAL' and not fast_big_transaction_wal:
        
        c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
        
    
    # this used to be 1024 for Linux users, so we do want to check and coerce back to SQLite default, 4096
    
    ( page_size, ) = c.execute( 'PRAGMA page_size;' ).fetchone()
    
    ideal_page_size = 4096
    
    if page_size != ideal_page_size:
        
        c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
        c.execute( 'PRAGMA page_size = ' + str( ideal_page_size ) + ';' )
        
    
    c.execute( 'PRAGMA auto_vacuum = 0;' ) # none
    
    c.execute( 'VACUUM;' )
    
    c.execute( 'PRAGMA journal_mode = {};'.format( HG.db_journal_mode ) )
    

def GetVacuumPaths( db_path: str ):
    
    return ( db_path + '.prevacuum', db_path + '.vacuum' )
    

def VacuumDBInto( db_path: str ):
    
    if os.path.exists( db_path + '-wal' ):
        
        raise Exception( f'Hey, I wanted to vacuum "{db_path}", but it seems like the "WAL" journal file still existed after hydrus disconnected, which suggests another program is connected to the database. It may also mean your version of SQLite does not clean up after itself, in which case I still cannot be sure we are clear. Vacuuming under these conditions can cause malformation, so the job will now be abandoned. Please disconnect your external program cleanly and then try again.' )
        
    
    # I guess I should look for PRAGMA journal_mode here tbh, rather than (or in complement to) looking for the sidecar, but w/e
    # any weird sidecars hanging around the db dir should result in NO VACUUM M8, no matter the journal_mode
    if os.path.exists( db_path + '-journal' ):
        
        raise Exception( f'Hey, I wanted to vacuum "{db_path}", but I see a "TRUNCATE" journal file even after I disconnected. I do not easily know, in TRUNCATE mode, if there are other programs connected to the database. Vacuuming under these conditions can cause malformation, so the job will now be abandoned. Please run the program in WAL journalling mode before trying again. If you have not specifically told hydrus to run in TRUNCATE mode, it probably fell back to this because WAL is not supported on your machine.' )
        
    
    started = HydrusTime.GetNowPrecise()
    
    ( deletee_path, vacuum_path ) = GetVacuumPaths( db_path )
    
    if os.path.exists( vacuum_path ):
        
        raise Exception( f'Hey, I wanted to vacuum "{db_path}", but "{vacuum_path}", which I wanted to use, already existed! Did a recent vacuum attempt fail? Please delete "{vacuum_path}" yourself before you try again.' )
        
    
    if os.path.exists( deletee_path ):
        
        raise Exception( f'Hey, I wanted to vacuum "{db_path}", but "{deletee_path}", which I wanted to use briefly, already existed! Did a recent vacuum attempt fail? Please delete "{deletee_path}" yourself before you try again.' )
        
    
    original_size = os.path.getsize( db_path )
    
    db = sqlite3.connect( db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
    
    c = db.cursor()
    
    c.execute( 'VACUUM INTO ?;', ( vacuum_path, ) )
    
    c.close()
    
    db.close()
    
    del c
    
    del db
    
    try:
        
        os.rename( db_path, deletee_path )
        
    except Exception as e:
        
        message = f'While attempting to vacuum "{db_path}", I could not rename it to "{deletee_path}"! You now have a spare vacuum file in your database directory at "{vacuum_path}", which you should manually delete.'
        
        raise Exception( message ) from e
        
    
    try:
        
        os.rename( vacuum_path, db_path )
        
    except Exception as e:
        
        try:
            
            os.rename( deletee_path, db_path )
            
        except Exception as e2:
            
            HydrusData.PrintException( e )
            HydrusData.PrintException( e2 )
            
            message = f'While attempting to vacuum "{db_path}", I could not rename "{vacuum_path}" to "{db_path}"! This is a bad situation, because now there is no database file in the desired location!'
            message += '\n\n'
            message += f'Also, when I attempted to recover by renaming "{deletee_path}" back to "{db_path}", that also failed, even though I only just renamed it the other way! It is like your hard drive suddenly disconnected!'
            message += '\n\n'
            message += f'Go into your db directory now and review the paths. I recommend renaming the "prevacuum" file back to the original name, since we do not know if this vacuum file is ok. Contact hydev if you need more help. Do not delete the "vacuum" file until you know things are good.'
            message += '\n\n'
            message += f'The program will exit suddenly and rudely after this message is closed.'
            
            HG.controller.BlockingSafeShowCriticalMessage( 'CRITICAL VACUUM ERROR', message )
            
            HydrusExit.CRITICALInitiateImmediateProgramHalt()
            
        
        message = f'The vacuum failed, but I have successfully rolled back to where you started. While attempting to vacuum "{db_path}", I could not rename "{vacuum_path}" to "{db_path}"! This was a very bad situation, but I have recovered by renaming the original, to-be-deleted "{deletee_path}" back to "{db_path}".'
        message += '\n\n'
        message += f'You now have a spare "{vacuum_path}" file in your db dir that you should delete. You should investigate what is wrong with your database folder--could there be a permissions error, or something with free space? Why can I rename the main file but not the new vacuum? Hydev would be interested in anything you learn.'
        
        raise Exception( message ) from e
        
    
    try:
        
        os.remove( deletee_path )
        
    except Exception as e:
        
        HydrusData.ShowText( f'Hey, the vacuum of "{db_path}" went ok, but I could not delete the leftover file "{deletee_path}"! Does hydrus not have delete permission on your db folder? In any case, please delete this file yourself.' )
        HydrusData.ShowException( e )
        
    
    vacuum_size = os.path.getsize( db_path )
    
    time_took = HydrusTime.GetNowPrecise() - started
    
    bytes_per_sec = vacuum_size / time_took
    
    HydrusData.ShowText( f'Vacuumed {db_path} in {HydrusTime.TimeDeltaToPrettyTimeDelta( time_took )} ({HydrusData.ToHumanBytes(bytes_per_sec)}/s). It went from {HydrusData.ToHumanBytes( original_size )} to {HydrusData.ToHumanBytes( vacuum_size )}' )
    

class HydrusDB( HydrusDBBase.DBBase ):
    
    READ_WRITE_ACTIONS = []
    UPDATE_WAIT = 2
    
    def __init__( self, controller: "HG.HydrusController.HydrusController", db_dir, db_name ):
        
        super().__init__()
        
        self._controller = controller
        self._db_dir = db_dir
        self._db_name = db_name
        
        self._read_commands_to_methods = {}
        self._write_commands_to_methods = {}
        
        self._modules = []
        
        HydrusDBBase.TemporaryIntegerTableNameCache()
        
        self._ssl_cert_filename = '{}.crt'.format( self._db_name )
        self._ssl_key_filename = '{}.key'.format( self._db_name )
        
        self._ssl_cert_path = os.path.join( self._db_dir, self._ssl_cert_filename )
        self._ssl_key_path = os.path.join( self._db_dir, self._ssl_key_filename )
        
        self._we_have_connected_to_the_database_at_least_once = False
        
        self._finished_job_event = threading.Event()
        
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
        
        self._cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper | None = None
        
        if os.path.exists( os.path.join( self._db_dir, self._db_filenames[ 'main' ] ) ):
            
            # open and close to clean up in case last session didn't close well
            
            self._InitDB()
            self._CloseDBConnection()
        
        
        ( space_wanted, free_space ) = self.GetSafeTransactionDiskSpaceAndCurrentFreeSpace()
        
        if free_space is not None and free_space < space_wanted:
            
            raise HydrusExceptions.DBAccessException( 'Sorry, it looks like the database drive partition has less than {} free space. It needs this for database transactions, so please free up some space.'.format( HydrusData.ToHumanBytes( space_wanted ) ) )
            
        
        self._InitDB()
        
        ( version, ) = self._Execute( 'SELECT version FROM version;' ).fetchone()
        
        if version > HC.SOFTWARE_VERSION:
            
            self._ReportOverupdatedDB( version )
            
        
        if version < HC.SOFTWARE_VERSION - 50:
            
            raise HydrusExceptions.DBVersionException( 'Your current database version of hydrus ' + str( version ) + ' is too old for this software version ' + str( HC.SOFTWARE_VERSION ) + ' to update. Please try updating with version ' + str( version + 45 ) + ' or earlier first.' )
            
        
        bitrot_rows = [
            ( 'client', 551, 558, 'millisecond timestamp conversion' )
        ]
        
        for ( bitrot_db_name, latest_affected_version, safe_update_version, reason ) in bitrot_rows:
            
            if self._db_name == bitrot_db_name and version <= latest_affected_version:
                
                raise HydrusExceptions.DBVersionException( f'Sorry, due to a bitrot issue ({reason}), you cannot update to this software version (v{HC.SOFTWARE_VERSION}) if your database is on v{latest_affected_version} or earlier (you are on v{version}). Please download and update to v{safe_update_version} first!' )
                
            
        
        if version < ( HC.SOFTWARE_VERSION - 15 ):
            
            self._ReportUnderupdatedDB( version )
            
        
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
                
            except Exception as e:
                
                e = Exception( 'Updating the ' + self._db_name + ' db to version ' + str( version + 1 ) + ' caused this error:' + '\n' + traceback.format_exc() )
                
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
        message += '\n' * 2
        message += text
        
        HydrusData.DebugPrint( message )
        
    
    def _DoAfterJobWork( self ):
        
        self._cursor_transaction_wrapper.DoPubSubs()
        
    
    def _GenerateDBJob( self, job_type, synchronous, action, *args, **kwargs ):
        
        return HydrusDBBase.JobDatabase( job_type, synchronous, action, *args, **kwargs )
        
    
    def _GetPossibleAdditionalDBFilenames( self ):
        
        return [ self._ssl_cert_filename, self._ssl_key_filename ]
        
    
    def _InitCaches( self ):
        
        pass
        
    
    def _InitCommandsToMethods( self ):
        
        self._read_commands_to_methods = {}
        self._write_commands_to_methods = {
            'null'  : lambda: None
        }
        
    
    def _InitDB( self ):
        
        main_db_path = os.path.join( self._db_dir, self._db_filenames[ 'main' ] )
        
        main_database_is_missing = not os.path.exists( main_db_path )
        
        external_db_paths = sorted( [ os.path.join( self._db_dir, self._db_filenames[ db_name ] ) for db_name in self._db_filenames if db_name != 'main' ] )
        
        all_db_paths = [ main_db_path ] + external_db_paths
        
        missing_db_paths = [ db_path for db_path in all_db_paths if not os.path.exists( db_path ) ]
        
        if self._we_have_connected_to_the_database_at_least_once and len( missing_db_paths ) > 0:
            
            missing_paths_summary = '"{}"'.format( '", "'.join( missing_db_paths ) )
            
            message = f'Holy hell, it looks like the database files "{missing_paths_summary}" disappeared while the program was working! Obviously something very bad has happened, and the program will now immediately quit. You will have to investigate this. hydev can help you figure it out.'
            
            self._controller.BlockingSafeShowCriticalMessage( 'recovering from failed vacuum!', message )
            
            HydrusExit.CRITICALInitiateImmediateProgramHalt()
            
        
        none_of_the_database_files_exist = len( missing_db_paths ) == len( all_db_paths )
        
        we_have_damage_from_missing_files = len( missing_db_paths ) > 0 and not none_of_the_database_files_exist
        
        if we_have_damage_from_missing_files:
            
            # failed vacuum recovery
            
            for missing_db_path in missing_db_paths:
                
                ( deletee_path, vacuum_path ) = GetVacuumPaths( missing_db_path )
                
                if os.path.exists( deletee_path ):
                    
                    message = f'The database file "{missing_db_path}" was missing, but I saw a file called "{deletee_path}". It appears you have just had a failed vacuum.'
                    message += '\n\n'
                    message += 'If you ok this message, hydrus will attempt to move this file back to where it belongs, restoring you to where you were before the failed vacuum. This is the best that hydev can do in this situation and it is almost certainly the correct thing to do.'
                    message += '\n\n'
                    message += 'If you do know better and want to check your hard drive for other damage before attempting repairs, kill the hydrus process now.'
                    
                    if os.path.exists( vacuum_path ):
                        
                        message += '\n\n'
                        message += f'There is also a file called "{vacuum_path}". This is the file that should have become your new vacuumed database file. You should not delete this file yet, since we may need it for recovery purposes if "{deletee_path}" is damaged, but it is the product of a failed vacuum operation and cannot be trusted, so you should plan to delete it if everything else goes well.'
                        
                    
                    self._controller.BlockingSafeShowCriticalMessage( 'recovering from failed vacuum!', message )
                    
                    try:
                        
                        os.rename( deletee_path, missing_db_path )
                        
                    except Exception as e:
                        
                        HydrusData.PrintException( e )
                        
                        message = 'I am sorry, the recovery attempt failed because I could not rename the file. It looks like your hard drive is damaged or somehow read-only. Hydrus will now quit; please check out what could be wrong with your drive, and ask hydev for help if you need it!'
                        
                        HG.controller.BlockingSafeShowCriticalMessage( 'REPAIR FAILURE', message )
                        
                        HydrusExit.CRITICALInitiateImmediateProgramHalt()
                        
                    
                    self._InitDB()
                    
                    return
                    
                
            
            # missing unrecoverable file reporting
            
            missing_external_db_paths = [ db_path for db_path in external_db_paths if db_path in missing_db_paths ]
            
            existing_external_paths_summary = '"{}"'.format( '", "'.join( [ db_path for db_path in external_db_paths if db_path not in missing_external_db_paths ] ) )
            missing_external_paths_summary = '"{}"'.format( '", "'.join( missing_external_db_paths ) )
            
            if main_database_is_missing:
                
                if len( missing_external_db_paths ) > 0:
                    
                    message = f'Although the expected external files, {existing_external_paths_summary} do exist, {missing_external_paths_summary} and, most importantly, the main database file, "{main_db_path}", do not!\n\nThe missing main database file makes for an invalid database, and the program will now quit. Please contact hydrus_dev if you do not know how this happened or need help recovering from hard drive failure.'
                    
                else:
                    
                    message = f'Although all the expected external files, {existing_external_paths_summary} do exist, the main database file, "{main_db_path}", does not!\n\nThis makes for an invalid database, and the program will now quit. Please contact hydrus_dev if you do not know how this happened or need help recovering from hard drive failure.'
                    
                
                raise HydrusExceptions.DBAccessException( message )
                
            else:
                
                if len( missing_external_db_paths ) > 0:
                    
                    message = f'While the main database file, "{main_db_path}", exists, the external files {missing_external_paths_summary} do not!\n\nIf this is a surprise to you, you have probably had a hard drive failure. You must close this process immediately and diagnose what has happened. Check the "help my db is broke.txt" document in the install_dir/db directory for additional help.\n\nIf this is not a surprise, then you may continue if you wish, and hydrus will do its best to reconstruct the missing files. You will see more error prompts.'
                    
                    self._controller.BlockingSafeShowCriticalMessage( 'missing database file!', message )
                    
                
            
        
        # ok we've dealt with pre-connection problems, let's go
        
        self._InitDBConnection()
        
        if not self._we_have_connected_to_the_database_at_least_once:
            
            self._we_have_connected_to_the_database_at_least_once = True
            
            if none_of_the_database_files_exist:
                
                self._is_first_start = True
                
                self._CreateDB()
                
                self._cursor_transaction_wrapper.CommitAndBegin()
                
            else:
                
                # I'm not sure, since it is nice to have it hardcoded, but we could migrate this stuff to the normal missing table recovery tech. "version" would indeed be marked as a critical missing table
                # but then again, we want to catch the situation of a failed _CreateDB
                
                result = self._Execute( 'SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?;', ( 'table', 'version' ) ).fetchone()
                
                if result is None:
                    
                    message = f'The "version" table in your "{main_db_path}" database was missing. I cannot recover from this automatically.'
                    message += '\n\n'
                    message += 'If you have used this database many times before, then you have probably had a hard drive failure. Hydrus will now close. Check the "help my db is broke.txt" document in the install_dir/db directory.'
                    message += '\n\n'
                    message += 'If you are trying over and over to get a fresh client or server booting for the first time, I suspect your database is in an odd half-initialised condition. You should fix your hard drive permissions and delete everything and try over again. If it seems complicated, hydev can help you figure it all out, so do not be afraid of contacting him.'
                    
                    raise HydrusExceptions.DBAccessException( 'missing critical database table!', message )
                    
                
            
        
    
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
            
            self._InitCommandsToMethods()
            
            self._Execute( 'ATTACH ":memory:" AS mem;' )
            
        except HydrusExceptions.DBAccessException:
            
            raise
            
        except Exception as e:
            
            raise HydrusExceptions.DBAccessException( 'Could not connect to database! If the answer is not obvious to you, please let hydrus dev know. Error follows:' + '\n' * 2 + str( e ) )
            
        
        HydrusDBBase.TemporaryIntegerTableNameCache.instance().Clear()
        
        # durable_temp is not excluded here
        db_names = [ name for ( index, name, path ) in self._Execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
        
        for db_name in db_names:
            
            # MB -> KB
            cache_size = HG.db_cache_size * 1024
            
            self._Execute( 'PRAGMA {}.cache_size = -{};'.format( db_name, cache_size ) )
            
            self._Execute( 'PRAGMA {}.journal_mode = {};'.format( db_name, HG.db_journal_mode ) )
            
            if HG.db_journal_mode in ( 'PERSIST', 'WAL' ):
                
                # We tried 1GB here, but I have reports of larger ones that don't seem to truncate ever?
                # Not sure what that is about, but I guess the db sometimes doesn't want to (expensively?) recover pages from the journal and just appends more data
                # In any case, this pragma is not a 'don't allow it to grow larger than', it's a 'after commit, truncate back to this', so no need to make it so large
                # default is -1, which means no limit
                
                self._Execute( 'PRAGMA {}.journal_size_limit = {};'.format( db_name, HydrusDBBase.JOURNAL_SIZE_LIMIT ) )
                
            
            self._Execute( 'PRAGMA {}.synchronous = {};'.format( db_name, HG.db_synchronous ) )
            
            try:
                
                self._Execute( 'SELECT * FROM {}.sqlite_master;'.format( db_name ) ).fetchone()
                
            except sqlite3.OperationalError as e:
                
                message = 'The database seemed valid, but hydrus failed to read basic data from it. You may need to run the program in a different journal mode using --db_journal_mode. Full error information:'
                
                message += '\n' * 2
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
        
    
    def _ProcessJob( self, job: HydrusDBBase.JobDatabase ):
        
        job_type = job.GetType()
        
        ( action, args, kwargs ) = job.GetCallableTuple()
        
        try:
            
            if job_type in ( 'read_write', 'write' ):
                
                self._current_status = 'db writing'
                
                self._cursor_transaction_wrapper.NotifyWriteOccuring()
                
            else:
                
                self._current_status = 'db reading'
                
            
            self.publish_status_update()
            
            idle_at_job_start = self._controller.CurrentlyIdle()
            time_job_started = HydrusTime.GetNowPrecise()
            
            result = None
            
            if job_type in ( 'read', 'read_write' ):
                
                result = self._Read( action, *args, **kwargs )
                
            elif job_type in ( 'write' ):
                
                result = self._Write( action, *args, **kwargs )
                
            
            idle_at_job_end = self._controller.CurrentlyIdle()
            
            if not idle_at_job_start or not idle_at_job_end:
                
                time_job_finished = HydrusTime.GetNowPrecise()
                
                time_job_took = time_job_finished - time_job_started
                
                if time_job_took > 15:
                    
                    HydrusData.Print( f'The database job "{job.ToString()}" took {HydrusTime.TimeDeltaToPrettyTimeDelta( time_job_took )}.' )
                    
                
            
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
        
        if action not in self._read_commands_to_methods:
            
            raise Exception( 'db received an unknown read command: ' + action )
            
        
        return self._read_commands_to_methods[ action ]( *args, **kwargs )
        
    
    def _RepairDB( self, version ):
        
        for module in self._modules:
            
            module.Repair( version, self._cursor_transaction_wrapper )
            
        
        if HG.controller.LastShutdownWasBad():
            
            for module in self._modules:
                
                module.DoLastShutdownWasBadWork()
                
            
        
    
    def _ReportOverupdatedDB( self, version ):
        
        pass
        
    
    def _ReportUnderupdatedDB( self, version ):
        
        pass
        
    
    def _ShrinkMemory( self ):
        
        self._Execute( 'PRAGMA shrink_memory;' )
        
    
    def _UnloadModules( self ):
        
        self._modules = []
        
    
    def _UpdateDB( self, version ):
        
        raise NotImplementedError()
        
    
    def _Write( self, action, *args, **kwargs ):
        
        if action not in self._write_commands_to_methods:
            
            raise Exception( 'db received an unknown write command: ' + action )
            
        
        return self._write_commands_to_methods[ action ]( *args, **kwargs )
        
    
    def publish_status_update( self ):
        
        pass
        
    
    def CurrentlyDoingJob( self ):
        
        return self._currently_doing_job
        
    
    def ForceACommit( self ):
        
        if self._cursor_transaction_wrapper is None:
            
            # database is closed (for a vacuum or something), so nothing to commit
            
            return
            
        
        if self._cursor_transaction_wrapper.InTransaction():
            
            self._cursor_transaction_wrapper.DoACommitAsSoonAsPossible()
            
            self.Write( 'null', True )
            
        
    
    def GetApproxTotalFileSize( self ):
        
        total = 0
        
        for filename in self._db_filenames.values():
            
            db_path = os.path.join( self._db_dir, filename )
            
            if os.path.exists( db_path ):
                
                total += os.path.getsize( db_path )
                
            
        
        return total
        
    
    def GetSafeTransactionDiskSpaceAndCurrentFreeSpace( self ):
        
        total_db_size = self.GetApproxTotalFileSize()
        
        space_wanted = min( int( total_db_size * 0.5 ), 5 * 1024 * 1048576 )
        
        space_wanted = max( space_wanted, 64 * 1048576 )
        
        free_space = HydrusPaths.GetFreeSpace( self._db_dir )
        
        return ( space_wanted, free_space )
        
    
    def GetSSLPaths( self ):
        
        # create ssl keys
        
        cert_here = os.path.exists( self._ssl_cert_path )
        key_here = os.path.exists( self._ssl_key_path )
        
        if cert_here ^ key_here:
            
            raise Exception( 'While creating the server database, only one of the paths "{}" and "{}" existed. You can create a db with these files already in place, but please either delete the existing file (to have hydrus generate its own pair) or find the other in the pair (to use your own).'.format( self._ssl_cert_path, self._ssl_key_path ) )
            
        elif not ( cert_here or key_here ):
            
            HydrusData.Print( 'Generating new cert/key files.' )
            
            if not HydrusEncryption.CRYPTO_OK:
                
                raise Exception( 'The database was asked for ssl cert and keys to start either the server or the client api in https. The files do not exist yet, so the database wanted to create new ones, but unfortunately "cryptography" library is not available, so this cannot be done. If you are running from source, please install this module using pip. Or drop in your own client.crt/client.key or server.crt/server.key files in the db directory.' )
                
            
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
            
        except Exception as e:
            
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
                        
                    
                    if HydrusProfiling.IsProfileMode( 'db' ):
                        
                        summary = 'Profiling db job: ' + job.ToString()
                        
                        HydrusProfiling.Profile( summary, HydrusData.Call( self._ProcessJob, job ), min_duration_ms = HG.db_profile_min_job_time_ms )
                        
                    else:
                        
                        self._ProcessJob( job )
                        
                    
                    error_count = 0
                    
                except Exception as e:
                    
                    error_count += 1
                    
                    if error_count > 5:
                        
                        raise
                        
                    
                    self._jobs.put( job ) # couldn't lock db; put job back on queue
                    
                    time.sleep( 5 )
                    
                
                self._current_job_name = ''
                self._currently_doing_job = False
                
                self._finished_job_event.set()
                
            except queue.Empty:
                
                if self._cursor_transaction_wrapper.TimeToCommit():
                    
                    self._current_status = 'db committing'
                    
                    self.publish_status_update()
                    
                    self._cursor_transaction_wrapper.CommitAndBegin()
                    
                
            finally:
                
                self._current_status = ''
                self.publish_status_update()
                
            
            if self._pause_and_disconnect:
                
                self._CloseDBConnection()
                
                self._current_status = 'db locked'
                
                self.publish_status_update()
                
                while self._pause_and_disconnect:
                    
                    if self._local_shutdown or HG.model_shutdown:
                        
                        break
                        
                    
                    time.sleep( 1 )
                    
                
                self._InitDBConnection()
                
                self._current_status = ''
                
            
        
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
        
    
    def WaitUntilFree( self ):
        
        while True:
            
            if HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application shutting down!' )
                
            elif self.JobsQueueEmpty() and not self.CurrentlyDoingJob():
                
                return
                
            else:
                
                self._finished_job_event.wait( 0.5 )
                
                self._finished_job_event.clear()
                
            
        
    
    def Write( self, action, synchronous, *args, **kwargs ):
        
        job_type = 'write'
        
        job = self._GenerateDBJob( job_type, synchronous, action, *args, **kwargs )
        
        if HG.model_shutdown:
            
            raise HydrusExceptions.ShutdownException( 'Application has shut down!' )
            
        
        self._jobs.put( job )
        
        if synchronous: return job.GetResult()
        
    
