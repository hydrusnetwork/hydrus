import collections
import hashlib
import httplib
import HydrusConstants as HC
import HydrusDB
import HydrusEncryption
import HydrusExceptions
import HydrusFileHandling
import HydrusNATPunch
import HydrusNetwork
import HydrusNetworking
import HydrusPaths
import HydrusSerialisable
import itertools
import json
import os
import Queue
import random
import ServerFiles
import shutil
import sqlite3
import stat
import sys
import threading
import time
import traceback
import HydrusData
import HydrusTags
import HydrusGlobals

def GenerateRepositoryMasterMapTableNames( service_id ):
    
    suffix = str( service_id )
    
    hash_id_map_table_name = 'external_master.repository_hash_id_map_' + suffix
    tag_id_map_table_name = 'external_master.repository_tag_id_map_' + suffix
    
    return ( hash_id_map_table_name, tag_id_map_table_name )
    
def GenerateRepositoryFilesTableNames( service_id ):
    
    suffix = str( service_id )
    
    current_files_table_name = 'current_files_' + suffix
    deleted_files_table_name = 'deleted_files_' + suffix
    pending_files_table_name = 'pending_files_' + suffix
    petitioned_files_table_name = 'petitioned_files_' + suffix
    ip_addresses_table_name = 'ip_addresses_' + suffix
    
    return ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name )
    
def GenerateRepositoryMappingsTableNames( service_id ):
    
    suffix = str( service_id )
    
    current_mappings_table_name = 'external_mappings.current_mappings_' + suffix
    deleted_mappings_table_name = 'external_mappings.deleted_mappings_' + suffix
    pending_mappings_table_name = 'external_mappings.pending_mappings_' + suffix
    petitioned_mappings_table_name = 'external_mappings.petitioned_mappings_' + suffix
    
    return ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name )
    
def GenerateRepositoryTagParentsTableNames( service_id ):
    
    suffix = str( service_id )
    
    current_tag_parents_table_name = 'current_tag_parents_' + suffix
    deleted_tag_parents_table_name = 'deleted_tag_parents_' + suffix
    pending_tag_parents_table_name = 'pending_tag_parents_' + suffix
    petitioned_tag_parents_table_name = 'petitioned_tag_parents_' + suffix
    
    return ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name )
    
def GenerateRepositoryTagSiblingsTableNames( service_id ):
    
    suffix = str( service_id )
    
    current_tag_siblings_table_name = 'current_tag_siblings_' + suffix
    deleted_tag_siblings_table_name = 'deleted_tag_siblings_' + suffix
    pending_tag_siblings_table_name = 'pending_tag_siblings_' + suffix
    petitioned_tag_siblings_table_name = 'petitioned_tag_siblings_' + suffix
    
    return ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name )
    
def GenerateRepositoryUpdateTableName( service_id ):
    
    return 'updates_' + str( service_id )
    
class DB( HydrusDB.HydrusDB ):
    
    READ_WRITE_ACTIONS = [ 'access_key', 'immediate_content_update', 'registration_keys' ]
    
    def __init__( self, controller, db_dir, db_name, no_wal = False ):
        
        self._files_dir = os.path.join( db_dir, 'server_files' )
        
        self._ssl_cert_filename = 'server.crt'
        self._ssl_key_filename = 'server.key'
        
        self._ssl_cert_path = os.path.join( db_dir, self._ssl_cert_filename )
        self._ssl_key_path = os.path.join( db_dir, self._ssl_key_filename )
        
        self._account_type_cache = {}
        
        HydrusDB.HydrusDB.__init__( self, controller, db_dir, db_name, no_wal = no_wal )
        
    
    def _AddAccountType( self, service_id, account_type ):
        
        ( account_type_key, title, dictionary ) = account_type.ToDictionaryTuple()
        
        dictionary_string = dictionary.DumpToString()
        
        self._c.execute( 'INSERT INTO account_types ( service_id, account_type_key, title, dictionary_string ) VALUES ( ?, ?, ?, ? );', ( service_id, sqlite3.Binary( account_type_key ), title, dictionary_string ) )
        
        account_type_id = self._c.lastrowid
        
        return account_type_id
        
    
    def _AddFile( self, file_dict ):
        
        hash = file_dict[ 'hash' ]
        
        master_hash_id = self._GetMasterHashId( hash )
        
        result = self._c.execute( 'SELECT 1 FROM files_info WHERE master_hash_id = ?;', ( master_hash_id, ) ).fetchone()
        
        if result is None:
            
            size = file_dict[ 'size' ]
            mime = file_dict[ 'mime' ]
            
            if 'width' in file_dict: width = file_dict[ 'width' ]
            else: width = None
            
            if 'height' in file_dict: height = file_dict[ 'height' ]
            else: height = None
            
            if 'duration' in file_dict: duration = file_dict[ 'duration' ]
            else: duration = None
            
            if 'num_frames' in file_dict: num_frames = file_dict[ 'num_frames' ]
            else: num_frames = None
            
            if 'num_words' in file_dict: num_words = file_dict[ 'num_words' ]
            else: num_words = None
            
            source_path = file_dict[ 'path' ]
            
            dest_path = ServerFiles.GetExpectedFilePath( hash )
            
            HydrusPaths.MirrorFile( source_path, dest_path )
            
            if 'thumbnail' in file_dict:
                
                thumbnail_dest_path = ServerFiles.GetExpectedThumbnailPath( hash )
                
                thumbnail = file_dict[ 'thumbnail' ]
                
                with open( thumbnail_dest_path, 'wb' ) as f:
                    
                    f.write( thumbnail )
                    
                
            
            self._c.execute( 'INSERT OR IGNORE INTO files_info ( master_hash_id, size, mime, width, height, duration, num_frames, num_words ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ? );', ( master_hash_id, size, mime, width, height, duration, num_frames, num_words ) )
            
        
        return master_hash_id
        
    
    def _AddService( self, service ):
        
        ( service_key, service_type, name, port, dictionary ) = service.ToTuple()
        
        dictionary_string = dictionary.DumpToString()
        
        self._c.execute( 'INSERT INTO services ( service_key, service_type, name, port, dictionary_string ) VALUES ( ?, ?, ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, name, port, dictionary_string ) )
        
        service_id = self._c.lastrowid
        
        service_admin_account_type = HydrusNetwork.AccountType.GenerateAdminAccountType( service_type )
        
        service_admin_account_type_id = self._AddAccountType( service_id, service_admin_account_type )
        
        if service_type == HC.SERVER_ADMIN:
            
            force_registration_key = 'init'
            
        else:
            
            force_registration_key = None
            
        
        [ registration_key ] = self._GenerateRegistrationKeys( service_id, 1, service_admin_account_type_id, None, force_registration_key )
        
        access_key = self._GetAccessKey( service_key, registration_key )
        
        if service_type in HC.REPOSITORIES:
            
            self._RepositoryCreate( service_id )
            
        
        return access_key
        
    
    def _AddSession( self, session_key, service_key, account_key, expires ):
        
        service_id = self._GetServiceId( service_key )
        
        account_id = self._GetAccountId( account_key )
        
        self._c.execute( 'INSERT INTO sessions ( session_key, service_id, account_id, expires ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( session_key ), service_id, account_id, expires ) )
        
    
    def _Analyze( self, stop_time ):
        
        stale_time_delta = 30 * 86400
        
        existing_names_to_timestamps = dict( self._c.execute( 'SELECT name, timestamp FROM analyze_timestamps;' ).fetchall() )
        
        db_names = [ name for ( index, name, path ) in self._c.execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
        
        all_names = set()
        
        for db_name in db_names:
            
            all_names.update( ( name for ( name, ) in self._c.execute( 'SELECT name FROM ' + db_name + '.sqlite_master WHERE type = ?;', ( 'table', ) ) ) )
            
        
        all_names.discard( 'sqlite_stat1' )
        
        names_to_analyze = [ name for name in all_names if name not in existing_names_to_timestamps or HydrusData.TimeHasPassed( existing_names_to_timestamps[ name ] + stale_time_delta ) ]
        
        random.shuffle( names_to_analyze )
        
        if len( names_to_analyze ) > 0:
            
            HydrusGlobals.server_busy = True
            
        
        for name in names_to_analyze:
            
            started = HydrusData.GetNowPrecise()
            
            self._c.execute( 'ANALYZE ' + name + ';' )
            
            self._c.execute( 'DELETE FROM analyze_timestamps WHERE name = ?;', ( name, ) )
            
            self._c.execute( 'INSERT OR IGNORE INTO analyze_timestamps ( name, timestamp ) VALUES ( ?, ? );', ( name, HydrusData.GetNow() ) )
            
            time_took = HydrusData.GetNowPrecise() - started
            
            if time_took > 1:
                
                HydrusData.Print( 'Analyzed ' + name + ' in ' + HydrusData.ConvertTimeDeltaToPrettyString( time_took ) )
                
            
            if HydrusData.TimeHasPassed( stop_time ):
                
                break
                
            
        
        self._c.execute( 'ANALYZE sqlite_master;' ) # this reloads the current stats into the query planner
        
        HydrusGlobals.server_busy = False
        
    
    def _Backup( self ):
        
        self._Commit()
        
        self._CloseDBCursor()
        
        HydrusGlobals.server_busy = True
        
        try:
            
            stop_time = HydrusData.GetNow() + 300
            
            for filename in self._db_filenames.values():
                
                db_path = os.path.join( self._db_dir, filename )
                
                if HydrusDB.CanVacuum( db_path, stop_time ):
                    
                    HydrusData.Print( 'backing up: vacuuming ' + filename )
                    
                    HydrusDB.VacuumDB( db_path )
                    
                
            
            backup_path = os.path.join( self._db_dir, 'server_backup' )
            
            HydrusPaths.MakeSureDirectoryExists( backup_path )
            
            for filename in self._db_filenames.values():
                
                HydrusData.Print( 'backing up: copying ' + filename )
                
                source = os.path.join( self._db_dir, filename )
                dest = os.path.join( backup_path, filename )
                
                HydrusPaths.MirrorFile( source, dest )
                
            
            for filename in [ self._ssl_cert_filename, self._ssl_key_filename ]:
                
                HydrusData.Print( 'backing up: copying ' + filename )
                
                source = os.path.join( self._db_dir, filename )
                dest = os.path.join( backup_path, filename )
                
                HydrusPaths.MirrorFile( source, dest )
                
            
            HydrusData.Print( 'backing up: copying files' )
            HydrusPaths.MirrorTree( self._files_dir, os.path.join( backup_path, 'server_files' ) )
            
        finally:
            
            HydrusGlobals.server_busy = False
            
            self._InitDBCursor()
            
            self._BeginImmediate()
            
        
        HydrusData.Print( 'backing up: done!' )
        
    
    def _CreateDB( self ):
        
        HydrusPaths.MakeSureDirectoryExists( self._files_dir )
        
        for prefix in HydrusData.IterateHexPrefixes():
            
            new_dir = os.path.join( self._files_dir, prefix )
            
            HydrusPaths.MakeSureDirectoryExists( new_dir )
            
        
        HydrusDB.SetupDBCreatePragma( self._c, no_wal = self._no_wal )
        
        self._BeginImmediate()
        
        self._c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, service_type INTEGER, name TEXT, port INTEGER, dictionary_string TEXT );' )
        
        self._c.execute( 'CREATE TABLE accounts ( account_id INTEGER PRIMARY KEY, service_id INTEGER, account_key BLOB_BYTES, hashed_access_key BLOB_BYTES, account_type_id INTEGER, created INTEGER, expires INTEGER, dictionary_string TEXT );' )
        self._c.execute( 'CREATE UNIQUE INDEX accounts_account_key_index ON accounts ( account_key );' )
        self._c.execute( 'CREATE UNIQUE INDEX accounts_hashed_access_key_index ON accounts ( hashed_access_key );' )
        
        self._c.execute( 'CREATE TABLE account_scores ( service_id INTEGER, account_id INTEGER, score_type INTEGER, score INTEGER, PRIMARY KEY ( service_id, account_id, score_type ) );' )
        
        self._c.execute( 'CREATE TABLE account_types ( account_type_id INTEGER PRIMARY KEY, service_id INTEGER, account_type_key BLOB_BYTES, title TEXT, dictionary_string TEXT );' )
        
        self._c.execute( 'CREATE TABLE analyze_timestamps ( name TEXT, timestamp INTEGER );' )
        
        self._c.execute( 'CREATE TABLE files_info ( master_hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, num_words INTEGER );' )
        
        self._c.execute( 'CREATE TABLE reasons ( reason_id INTEGER PRIMARY KEY, reason TEXT );' )
        self._c.execute( 'CREATE UNIQUE INDEX reasons_reason_index ON reasons ( reason );' )
        
        self._c.execute( 'CREATE TABLE registration_keys ( registration_key BLOB_BYTES PRIMARY KEY, service_id INTEGER, account_type_id INTEGER, account_key BLOB_BYTES, access_key BLOB_BYTES UNIQUE, expires INTEGER );' )
        
        self._c.execute( 'CREATE TABLE sessions ( session_key BLOB_BYTES, service_id INTEGER, account_id INTEGER, expires INTEGER );' )
        
        self._c.execute( 'CREATE TABLE version ( version INTEGER, year INTEGER, month INTEGER );' )
        
        # master
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.hashes ( master_hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES UNIQUE );' )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.tags ( master_tag_id INTEGER PRIMARY KEY, tag TEXT UNIQUE );' )
        
        # inserts
        
        current_time_struct = time.gmtime()
        
        ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
        
        self._c.execute( 'INSERT INTO version ( version, year, month ) VALUES ( ?, ?, ? );', ( HC.SOFTWARE_VERSION, current_year, current_month ) )
        
        # create ssl keys
        
        HydrusEncryption.GenerateOpenSSLCertAndKeyFile( self._ssl_cert_path, self._ssl_key_path )
        
        # set up server admin
        
        admin_service = HydrusNetwork.GenerateService( HC.SERVER_ADMIN_KEY, HC.SERVER_ADMIN, 'server admin', HC.DEFAULT_SERVER_ADMIN_PORT )
        
        self._AddService( admin_service ) # this sets up the admin account and a registration key by itself
        
        self._Commit()
        
    
    def _DeleteOrphans( self ):
        
        # make a table for files
        # make a table for thumbnails
        
        # populate both tables with what you have in your hdd
        # if the filename isn't even a hash, schedule it for immediate deletion instead
        
        # delete from the tables based on what is in current and pending repo file tables
        # delete from the file tables based on what is in update tables
        
        # delete whatever is left
        
        # might want to split this up into 256 jobs--depends on how fast its bits run
        # might also want to set server_busy, if it isn't already
        
        # also think about how often it runs--maybe only once a month is appropriate
        
        return # return to this to fix it for new system
        
    
    def _DeleteService( self, service_key ):
        
        # assume foreign keys is on here
        
        service_id = self._GetServiceId( service_key )
        service_type = self._GetServiceType( service_id )
        
        service_id = self._GetServiceId( service_key )
        
        self._c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
        
        self._c.execute( 'DELETE FROM accounts WHERE service_id = ?;', ( service_id, ) )
        self._c.execute( 'DELETE FROM account_types WHERE service_id = ?;', ( service_id, ) )
        self._c.execute( 'DELETE FROM account_scores WHERE service_id = ?;', ( service_id, ) )
        self._c.execute( 'DELETE FROM registration_keys WHERE service_id = ?;', ( service_id, ) )
        self._c.execute( 'DELETE FROM sessions WHERE service_id = ?;', ( service_id, ) )
        
        if service_type in HC.REPOSITORIES:
            
            self._RepositoryDrop( service_id )
            
        
    
    def _GenerateRegistrationKeysFromAccount( self, service_key, account, num, account_type_key, expires ):
        
        account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
        
        service_id = self._GetServiceId( service_key )
        
        account_type_id = self._GetAccountTypeId( service_id, account_type_key )
        
        return self._GenerateRegistrationKeys( service_id, num, account_type_id, expires )
        
    
    def _GenerateRegistrationKeys( self, service_id, num, account_type_id, expires, force_registration_key = None ):
        
        if force_registration_key is None:
            
            keys = [ ( os.urandom( HC.HYDRUS_KEY_LENGTH ), os.urandom( HC.HYDRUS_KEY_LENGTH ), os.urandom( HC.HYDRUS_KEY_LENGTH ) ) for i in range( num ) ]
            
        else:
            
            keys = [ ( force_registration_key, os.urandom( HC.HYDRUS_KEY_LENGTH ), os.urandom( HC.HYDRUS_KEY_LENGTH ) ) for i in range( num ) ]
            
        
        self._c.executemany( 'INSERT INTO registration_keys ( registration_key, service_id, account_type_id, account_key, access_key, expires ) VALUES ( ?, ?, ?, ?, ?, ? );', [ ( sqlite3.Binary( hashlib.sha256( registration_key ).digest() ), service_id, account_type_id, sqlite3.Binary( account_key ), sqlite3.Binary( access_key ), expires ) for ( registration_key, account_key, access_key ) in keys ] )
        
        return [ registration_key for ( registration_key, account_key, access_key ) in keys ]
        
    
    def _GetAccessKey( self, service_key, registration_key ):
        
        service_id = self._GetServiceId( service_key )
        
        # we generate a new access_key every time this is requested so that no one with access to the registration key can peek at the access_key before the legit user fetches it for real
        # the reg_key is deleted when the last-requested access_key is used to create a session, which calls getaccountkeyfromaccesskey
        
        registration_key_sha256 = hashlib.sha256( registration_key ).digest()
        
        result = self._c.execute( 'SELECT 1 FROM registration_keys WHERE service_id = ? AND registration_key = ?;', ( service_id, sqlite3.Binary( registration_key_sha256 ) ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.ForbiddenException( 'The service could not find that registration key in its database.' )
            
        
        new_access_key = os.urandom( HC.HYDRUS_KEY_LENGTH )
        
        self._c.execute( 'UPDATE registration_keys SET access_key = ? WHERE service_id = ? AND registration_key = ?;', ( sqlite3.Binary( new_access_key ), service_id, sqlite3.Binary( registration_key_sha256 ) ) )
        
        return new_access_key
        
    
    def _GetAccount( self, service_id, account_id ):
        
        ( account_key, account_type_id, created, expires, dictionary_string ) = self._c.execute( 'SELECT account_key, account_type_id, created, expires, dictionary_string FROM accounts WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
        
        account_type = self._GetAccountTypeFromCache( service_id, account_type_id )
        
        dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
        
        return HydrusNetwork.Account.GenerateAccountFromTuple( ( account_key, account_type, created, expires, dictionary ) )
        
    
    def _GetAccountFromAccountKey( self, service_key, account_key ):
        
        service_id = self._GetServiceId( service_key )
        
        account_id = self._GetAccountId( account_key )
        
        return self._GetAccount( service_id, account_id )
        
    
    def _GetAccountFromAccountKeyAdmin( self, admin_account, service_key, account_key ):
        
        # check admin account
        
        service_id = self._GetServiceId( service_key )
        
        account_id = self._GetAccountId( account_key )
        
        return self._GetAccount( service_id, account_id )
        
    
    def _GetAccountKeyFromAccessKey( self, service_key, access_key ):
        
        service_id = self._GetServiceId( service_key )
        
        result = self._c.execute( 'SELECT account_key FROM accounts WHERE service_id = ? AND hashed_access_key = ?;', ( service_id, sqlite3.Binary( hashlib.sha256( access_key ).digest() ), ) ).fetchone()
        
        if result is None:
            
            # we do not delete the registration_key (and hence the raw unhashed access_key)
            # until the first attempt to create a session to make sure the user
            # has the access_key saved
            
            try:
                
                ( account_type_id, account_key, expires ) = self._c.execute( 'SELECT account_type_id, account_key, expires FROM registration_keys WHERE access_key = ?;', ( sqlite3.Binary( access_key ), ) ).fetchone()
                
            except:
                
                raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
                
            
            self._c.execute( 'DELETE FROM registration_keys WHERE access_key = ?;', ( sqlite3.Binary( access_key ), ) )
            
            #
            
            hashed_account_key = hashlib.sha256( access_key ).digest()
            
            account_type = self._GetAccountTypeFromCache( service_id, account_type_id )
            
            created = HydrusData.GetNow()
            
            account = HydrusNetwork.Account( account_key, account_type, created, expires )
            
            ( account_key, account_type, created, expires, dictionary ) = HydrusNetwork.Account.GenerateTupleFromAccount( account )
            
            dictionary_string = dictionary.DumpToString()
            
            self._c.execute( 'INSERT INTO accounts ( service_id, account_key, hashed_access_key, account_type_id, created, expires, dictionary_string ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, sqlite3.Binary( account_key ), sqlite3.Binary( hashed_account_key ), account_type_id, created, expires, dictionary_string ) )
            
        else:
            
            ( account_key, ) = result
            
        
        return account_key
        
    
    def _GetAccountKeyFromAccountId( self, account_id ):
        
        try: ( account_key, ) = self._c.execute( 'SELECT account_key FROM accounts WHERE account_id = ?;', ( account_id, ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account_id in its database.' )
        
        return account_key
        
    
    def _GetAccountFromContent( self, admin_account, service_key, content ):
        
        # check admin account
        
        service_id = self._GetServiceId( service_key )
        
        content_type = content.GetContentType()
        content_data = content.GetContentData()
        
        if content_type == HC.CONTENT_TYPE_FILES:
            
            hash = content_data[0]
            
            if not self._MasterHashExists( hash ):
                
                raise HydrusExceptions.NotFoundException( 'The service could not find that hash in its database.' )
                
            
            master_hash_id = self._GetMasterHashId( hash )
            
            if not self._RepositoryServiceHashIdExists( service_id, master_hash_id ):
                
                raise HydrusExceptions.NotFoundException( 'The service could not find that service hash in its database.' )
                
            
            service_hash_id = self._RepositoryGetServiceHashId( service_id, master_hash_id )
            
            ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
            
            result = self._c.execute( 'SELECT account_id FROM ' + current_files_table_name + ' WHERE service_hash_id = ?;', ( service_hash_id, ) ).fetchone()
            
            if result is None:
                
                result = self._c.execute( 'SELECT account_id FROM ' + deleted_files_table_name + ' WHERE service_hash_id = ?;', ( service_hash_id, ) ).fetchone()
                
            
            if result is None:
                
                raise HydrusExceptions.NotFoundException( 'The service could not find that hash in its database.' )
                
            
        elif content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = content_data
            
            if not self._MasterHashExists( hash ):
                
                raise HydrusExceptions.NotFoundException( 'The service could not find that hash in its database.' )
                
            
            master_hash_id = self._GetMasterHashId( hash )
            
            if not self._RepositoryServiceHashIdExists( service_id, master_hash_id ):
                
                raise HydrusExceptions.NotFoundException( 'The service could not find that service hash in its database.' )
                
            
            service_hash_id = self._RepositoryGetServiceHashId( service_id, master_hash_id )
            
            if not self._MasterTagExists( tag ):
                
                raise HydrusExceptions.NotFoundException( 'The service could not find that tag in its database.' )
                
            
            master_tag_id = self._GetMasterTagId( tag )
            
            if not self._RepositoryServiceTagIdExists( service_id, master_tag_id ):
                
                raise HydrusExceptions.NotFoundException( 'The service could not find that service tag in its database.' )
                
            
            service_tag_id = self._RepositoryGetServiceTagId( service_id, master_tag_id )
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
            
            result = self._c.execute( 'SELECT account_id FROM ' + current_mappings_table_name + ' WHERE service_tag_id = ? AND service_hash_id = ?;', ( service_tag_id, service_hash_id ) ).fetchone()
            
            if result is None:
                
                result = self._c.execute( 'SELECT account_id FROM ' + deleted_mappings_table_name + ' WHERE service_tag_id = ? AND service_hash_id = ?;', ( service_tag_id, service_hash_id ) ).fetchone()
                
            
            if result is None:
                
                raise HydrusExceptions.NotFoundException( 'The service could not find that mapping in its database.' )
                
            
        else:
            
            raise HydrusExceptions.NotFoundException( 'The service could not understand the submitted content.' )
            
        
        ( account_id, ) = result
        
        account = self._GetAccount( service_id, account_id )
        
        return account
        
    
    def _GetAccountId( self, account_key ):
        
        result = self._c.execute( 'SELECT account_id FROM accounts WHERE account_key = ?;', ( sqlite3.Binary( account_key ), ) ).fetchone()
        
        if result is None: raise HydrusExceptions.ForbiddenException( 'The service could not find that account key in its database.' )
        
        ( account_id, ) = result
        
        return account_id
        
    
    def _GetAccountInfo( self, service_key, account, subject_account ):
        
        account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
        
        service_id = self._GetServiceId( service_key )
        
        subject_account_key = subject_account.GetAccountKey()
        
        subject_account_id = self._GetAccountId( subject_account_key )
        
        service_type = self._GetServiceType( service_id )
        
        if service_type in HC.REPOSITORIES:
            
            account_info = self._RepositoryGetAccountInfo( service_id, subject_account_id )
            
        else:
            
            account_info = {}
            
        
        return account_info
        
    
    def _GetAccountTypeId( self, service_id, account_type_key ):
        
        result = self._c.execute( 'SELECT account_type_id FROM account_types WHERE service_id = ? AND account_type_key = ?;', ( service_id, sqlite3.Binary( account_type_key ) ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that account type in db for this service.' )
            
        
        ( account_type_id, ) = result
        
        return account_type_id
        
    
    def _GetAccountTypes( self, service_key, account ):
        
        account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
        
        service_id = self._GetServiceId( service_key )
        
        return self._GetAccountTypesFromCache( service_id )
        
    
    def _GetAccountTypeFromCache( self, service_id, account_type_id ):
        
        if service_id not in self._account_type_cache:
            
            self._RefreshAccountTypeCache( service_id )
            
        
        return self._account_type_cache[ service_id ][ account_type_id ]
        
    
    def _GetAccountTypesFromCache( self, service_id ):
        
        if service_id not in self._account_type_cache:
            
            self._RefreshAccountTypeCache( service_id )
            
        
        return self._account_type_cache[ service_id ].values()
        
    
    def _GetFile( self, hash ):
        
        path = ServerFiles.GetFilePath( hash )
        
        with open( path, 'rb' ) as f:
            
            data = f.read()
            
        
        return data
        
    
    def _GetHash( self, master_hash_id ):
        
        result = self._c.execute( 'SELECT hash FROM hashes WHERE master_hash_id = ?;', ( master_hash_id, ) ).fetchone()
        
        if result is None:
            
            raise Exception( 'File hash error in database' )
            
        
        ( hash, ) = result
        
        return hash
        
    
    def _GetHashes( self, master_hash_ids ):
        
        select_statement = 'SELECT hash FROM hashes WHERE master_hash_id IN %s;'
        
        return [ hash for ( hash, ) in self._SelectFromList( select_statement, master_hash_ids ) ]
        
    
    def _GetMasterHashId( self, hash ):
        
        result = self._c.execute( 'SELECT master_hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( sqlite3.Binary( hash ), ) )
            
            master_hash_id = self._c.lastrowid
            
            return master_hash_id
            
        else:
            
            ( master_hash_id, ) = result
            
            return master_hash_id
            
        
    
    def _GetMasterHashIds( self, hashes ):
        
        master_hash_ids = set()
        hashes_not_in_db = set()
        
        for hash in hashes:
            
            if hash is None:
                
                continue
                
            
            result = self._c.execute( 'SELECT master_hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
            
            if result is None:
                
                hashes_not_in_db.add( hash )
                
            else:
                
                ( master_hash_id, ) = result
                
                master_hash_ids.add( master_hash_id )
                
            
        
        if len( hashes_not_in_db ) > 0:
            
            self._c.executemany( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( ( sqlite3.Binary( hash ), ) for hash in hashes_not_in_db ) )
            
            for hash in hashes_not_in_db:
                
                ( master_hash_id, ) = self._c.execute( 'SELECT master_hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
                
                master_hash_ids.add( master_hash_id )
                
            
        
        return master_hash_ids
        
    
    def _GetMasterTagId( self, tag ):
        
        tag = HydrusTags.CleanTag( tag )
        
        HydrusTags.CheckTagNotEmpty( tag )
        
        result = self._c.execute( 'SELECT master_tag_id FROM tags WHERE tag = ?;', ( tag, ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO tags ( tag ) VALUES ( ? );', ( tag, ) )
            
            master_tag_id = self._c.lastrowid
            
            return master_tag_id
            
        else:
            
            ( master_tag_id, ) = result
            
            return master_tag_id
            
        
    
    def _GetOptions( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        ( options, ) = self._c.execute( 'SELECT options FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return options
        
    
    def _GetReason( self, reason_id ):
        
        result = self._c.execute( 'SELECT reason FROM reasons WHERE reason_id = ?;', ( reason_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Reason error in database' )
        
        ( reason, ) = result
        
        return reason
        
    
    def _GetReasonId( self, reason ):
        
        result = self._c.execute( 'SELECT reason_id FROM reasons WHERE reason = ?;', ( reason, ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO reasons ( reason ) VALUES ( ? );', ( reason, ) )
            
            reason_id = self._c.lastrowid
            
            return reason_id
            
        else:
            
            ( reason_id, ) = result
            
            return reason_id
            
        
    
    def _GetServiceId( self, service_key ):
        
        result = self._c.execute( 'SELECT service_id FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Service id error in database' )
            
        
        ( service_id, ) = result
        
        return service_id
        
    
    def _GetServiceIds( self, limited_types = HC.ALL_SERVICES ):
        
        return [ service_id for ( service_id, ) in self._c.execute( 'SELECT service_id FROM services WHERE service_type IN ' + HydrusData.SplayListForDB( limited_types ) + ';' ) ]
        
    
    def _GetServiceKey( self, service_id ):
        
        ( service_key, ) = self._c.execute( 'SELECT service_key FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return service_key
        
    
    def _GetServiceKeys( self, limited_types = HC.ALL_SERVICES ):
        
        return [ service_key for ( service_key, ) in self._c.execute( 'SELECT service_key FROM services WHERE service_type IN '+ HydrusData.SplayListForDB( limited_types ) + ';' ) ]
        
    
    def _GetServiceType( self, service_id ):
        
        result = self._c.execute( 'SELECT service_type FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_type, ) = result
        
        return service_type
        
    
    def _GetServiceInfo( self, service_key ): return self._c.execute( 'SELECT type, options FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
    
    def _GetServices( self, limited_types = HC.ALL_SERVICES ):
        
        services = []
        
        service_info = self._c.execute( 'SELECT service_key, service_type, name, port, dictionary_string FROM services WHERE service_type IN ' + HydrusData.SplayListForDB( limited_types ) + ';' ).fetchall()
        
        for ( service_key, service_type, name, port, dictionary_string ) in service_info:
            
            dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
            
            service = HydrusNetwork.GenerateService( service_key, service_type, name, port, dictionary )
            
            services.append( service )
            
        
        return services
        
    
    def _GetServicesFromAccount( self, account ):
        
        account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_OVERRULE )
        
        return self._GetServices()
        
    
    def _GetSessions( self, service_key = None ):
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'DELETE FROM sessions WHERE ? > expires;', ( now, ) )
        
        sessions = []
        
        if service_key is None:
            
            results = self._c.execute( 'SELECT session_key, service_id, account_id, expires FROM sessions;' ).fetchall()
            
        else:
            
            service_id = self._GetServiceId( service_key)
            
            results = self._c.execute( 'SELECT session_key, service_id, account_id, expires FROM sessions WHERE service_id = ?;', ( service_id, ) ).fetchall()
            
        
        service_ids_to_service_keys = {}
        
        account_ids_to_accounts = {}
        
        for ( session_key, service_id, account_id, expires ) in results:
            
            if service_id not in service_ids_to_service_keys:
                
                service_ids_to_service_keys[ service_id ] = self._GetServiceKey( service_id )
                
            
            service_key = service_ids_to_service_keys[ service_id ]
            
            if account_id not in account_ids_to_accounts:
                
                account = self._GetAccount( service_id, account_id )
                
                account_ids_to_accounts[ account_id ] = account
                
            
            account = account_ids_to_accounts[ account_id ]
            
            sessions.append( ( session_key, service_key, account, expires ) )
            
        
        return sessions
        
    
    def _GetTag( self, master_tag_id ):
        
        result = self._c.execute( 'SELECT tag FROM tags WHERE master_tag_id = ?;', ( master_tag_id, ) ).fetchone()
        
        if result is None:
            
            raise Exception( 'Tag error in database' )
            
        
        ( tag, ) = result
        
        return tag
        
    
    def _GetThumbnail( self, hash ):
        
        path = ServerFiles.GetThumbnailPath( hash )
        
        with open( path, 'rb' ) as f: thumbnail = f.read()
        
        return thumbnail
        
    
    def _InitCaches( self ):
        
        self._over_monthly_data = False
        self._services_over_monthly_data = set()
        
    
    def _InitExternalDatabases( self ):
        
        self._db_filenames[ 'external_mappings' ] = 'server.mappings.db'
        self._db_filenames[ 'external_master' ] = 'server.master.db'
        
    
    def _ManageDBError( self, job, e ):
        
        if isinstance( e, HydrusExceptions.NetworkException ):
            
            job.PutResult( e )
            
        else:
            
            ( exception_type, value, tb ) = sys.exc_info()
            
            new_e = type( e )( os.linesep.join( traceback.format_exception( exception_type, value, tb ) ) )
            
            job.PutResult( new_e )
            
        
    
    def _MasterHashExists( self, hash ):
        
        result = self._c.execute( 'SELECT master_hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def _MasterTagExists( self, tag ):
        
        result = self._c.execute( 'SELECT master_tag_id FROM tags WHERE tag = ?;', ( tag, ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def _DeleteAllAccountContributions( self, service_key, account, subject_accounts, superban ):
        
        account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
        
        service_id = self._GetServiceId( service_key )
        
        subject_account_keys = [ subject_account.GetAccountKey() for subject_account in subject_accounts ]
        
        subject_account_ids = [ self._GetAccountId( subject_account_key ) for subject_account_key in subject_account_keys ]
        
        self._RepositoryBan( service_id, subject_account_ids )
        
        if superban:
            
            account_key = account.GetAccountKey()
            
            account_id = self._GetAccountId( account_key )
            
            self._RepositorySuperBan( service_id, account_id, subject_account_ids )
            
        
    
    def _ModifyAccounts( self, service_key, account, subject_accounts ):
        
        account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
        
        service_id = self._GetServiceId( service_key )
        
        self._SaveAccounts( service_id, subject_accounts )
        
        subject_account_keys = [ subject_account.GetAccountKey() for subject_account in subject_accounts ]
        
        HydrusGlobals.server_controller.pub( 'update_session_accounts', service_key, subject_account_keys )
        
    
    def _ModifyAccountTypes( self, service_key, account, account_types, deletee_account_type_keys_to_new_account_type_keys ):
        
        account.CheckPermission( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_OVERRULE )
        
        service_id = self._GetServiceId( service_key )
        
        current_account_type_keys = { account_type_key for ( account_type_key, ) in self._c.execute( 'SELECT account_type_key FROM account_types WHERE service_id = ?;', ( service_id, ) ) }
        
        future_account_type_keys = { account_type.GetAccountTypeKey() for account_type in account_types }
        
        for account_type in account_types:
            
            account_type_key = account_type.GetAccountTypeKey()
            
            if account_type_key not in current_account_type_keys:
                
                self._AddAccountType( service_id, account_type )
                
            else:
                
                ( account_type_key, title, dictionary ) = account_type.ToDictionaryTuple()
                
                dictionary_string = dictionary.DumpToString()
                
                account_type_id = self._GetAccountTypeId( service_id, account_type_key )
                
                self._c.execute( 'UPDATE account_types SET title = ?, dictionary_string = ? WHERE service_id = ? AND account_type_id = ?;', ( title, dictionary_string, service_id, account_type_id ) )
                
            
        
        for account_type_key in current_account_type_keys:
            
            if account_type_key not in future_account_type_keys:
                
                account_type_id = self._GetAccountTypeId( service_id, account_type_key )
                
                if account_type_key not in deletee_account_type_keys_to_new_account_type_keys:
                    
                    raise HydrusExceptions.NotFoundException( 'Was missing a replacement account_type_key.' )
                    
                
                new_account_type_key = deletee_account_type_keys_to_new_account_type_keys[ account_type_key ]
                
                new_account_type_id = self._GetAccountTypeId( service_id, new_account_type_key )
                
                self._c.execute( 'UPDATE accounts SET account_type_id = ? WHERE service_id = ? AND account_type_id = ?;', ( new_account_type_id, service_id, account_type_id ) )
                self._c.execute( 'UPDATE registration_keys SET account_type_id = ? WHERE service_id = ? AND account_type_id = ?;', ( new_account_type_id, service_id, account_type_id ) )
                
                self._c.execute( 'DELETE FROM account_types WHERE service_id = ? AND account_type_id = ?;', ( service_id, account_type_id ) )
                
            
        
        self._RefreshAccountTypeCache( service_id )
        
        HydrusGlobals.server_controller.pub( 'update_all_session_accounts', service_key )
        
    
    def _ModifyServices( self, account, services ):
        
        account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_OVERRULE )
        
        self._Commit()
        
        if not self._fast_big_transaction_wal:
            
            self._c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
            
        
        self._c.execute( 'PRAGMA foreign_keys = ON;' )
        
        self._BeginImmediate()
        
        current_service_keys = { service_key for ( service_key, ) in self._c.execute( 'SELECT service_key FROM services;' ) }
        
        future_service_keys = { service.GetServiceKey() for service in services }
        
        for service_key in current_service_keys:
            
            if service_key not in future_service_keys:
                
                self._DeleteService( service_key )
                
            
        
        service_keys_to_access_keys = {}
        
        for service in services:
            
            service_key = service.GetServiceKey()
            
            if service_key in current_service_keys:
                
                ( service_key, service_type, name, port, dictionary ) = service.ToTuple()
                
                service_id = self._GetServiceId( service_key )
                
                dictionary_string = dictionary.DumpToString()
                
                self._c.execute( 'UPDATE services SET name = ?, port = ?, dictionary_string = ? WHERE service_id = ?;', ( name, port, dictionary_string, service_id ) )
                
            else:
                
                access_key = self._AddService( service )
                
                service_keys_to_access_keys[ service_key ] = access_key
                
            
        
        self._Commit()
        
        self._InitDBCursor()
        
        self._BeginImmediate()
        
        return service_keys_to_access_keys
        
    
    def _Read( self, action, *args, **kwargs ):
        
        if action == 'access_key': result = self._GetAccessKey( *args, **kwargs )
        elif action == 'account': result = self._GetAccountFromAccountKey( *args, **kwargs )
        elif action == 'account_info': result = self._GetAccountInfo( *args, **kwargs )
        elif action == 'account_key_from_access_key': result = self._GetAccountKeyFromAccessKey( *args, **kwargs )
        elif action == 'account_types': result = self._GetAccountTypes( *args, **kwargs )
        elif action == 'immediate_update': result = self._RepositoryGenerateImmediateUpdate( *args, **kwargs )
        elif action == 'ip': result = self._RepositoryGetIPTimestamp( *args, **kwargs )
        elif action == 'num_petitions': result = self._RepositoryGetNumPetitions( *args, **kwargs )
        elif action == 'petition': result = self._RepositoryGetPetition( *args, **kwargs )
        elif action == 'registration_keys': result = self._GenerateRegistrationKeysFromAccount( *args, **kwargs )
        elif action == 'service_has_file': result = self._RepositoryHasFile( *args, **kwargs )
        elif action == 'service_info': result = self._GetServiceInfo( *args, **kwargs )
        elif action == 'service_keys': result = self._GetServiceKeys( *args, **kwargs )
        elif action == 'services': result = self._GetServices( *args, **kwargs )
        elif action == 'services_from_account': result = self._GetServicesFromAccount( *args, **kwargs )
        elif action == 'sessions': result = self._GetSessions( *args, **kwargs )
        elif action == 'verify_access_key': result = self._VerifyAccessKey( *args, **kwargs )
        else: raise Exception( 'db received an unknown read command: ' + action )
        
        return result
        
    
    def _RefreshAccountTypeCache( self, service_id ):
        
        self._account_type_cache[ service_id ] = {}
        
        account_type_tuples = self._c.execute( 'SELECT account_type_id, account_type_key, title, dictionary_string FROM account_types WHERE service_id = ?;', ( service_id, ) ).fetchall()
        
        for ( account_type_id, account_type_key, title, dictionary_string ) in account_type_tuples:
            
            dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
            
            account_type = HydrusNetwork.AccountType( account_type_key, title, dictionary )
            
            self._account_type_cache[ service_id ][ account_type_id ] = account_type
            
        
    
    def _RepositoryAddFile( self, service_id, account_id, file_dict, overwrite_deleted ):
        
        master_hash_id = self._AddFile( file_dict )
        
        service_hash_id = self._RepositoryGetServiceHashId( service_id, master_hash_id )
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        now = HydrusData.GetNow()
        
        if 'ip' in file_dict:
            
            ip = file_dict[ 'ip' ]
            
            self._c.execute( 'INSERT INTO ' + ip_addresses_table_name + ' ( master_hash_id, ip, ip_timestamp ) VALUES ( ?, ?, ? );', ( master_hash_id, ip, now ) )
            
        
        result = self._c.execute( 'SELECT 1 FROM ' + current_files_table_name + ' WHERE service_hash_id = ?;', ( service_hash_id, ) ).fetchone()
        
        if result is not None:
            
            return
            
        
        if overwrite_deleted:
            
            #self._RepositoryRewardFilePenders( service_id, service_hash_id, 1 )
            
            #self._c.execute( 'DELETE FROM ' + pending_files_table_name + ' WHERE service_hash_id = ?;', ( service_hash_id, ) )
            self._c.execute( 'DELETE FROM ' + deleted_files_table_name + ' WHERE service_hash_id = ?;', ( service_hash_id, ) )
            
        else:
            
            result = self._c.execute( 'SELECT 1 FROM ' + deleted_files_table_name + ' WHERE service_hash_id = ?;', ( service_hash_id, ) ).fetchone()
            
            if result is not None:
                
                return
                
            
        
        self._c.execute( 'INSERT INTO ' + current_files_table_name + ' ( service_hash_id, account_id, file_timestamp ) VALUES ( ?, ?, ? );', ( service_hash_id, account_id, now ) )
        
    
    def _RepositoryAddMappings( self, service_id, account_id, master_tag_id, master_hash_ids, overwrite_deleted ):
        
        service_tag_id = self._RepositoryGetServiceTagId( service_id, master_tag_id )
        service_hash_ids = self._RepositoryGetServiceHashIds( service_id, master_hash_ids )
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        if overwrite_deleted:
            
            #self._RepositoryRewardMappingPenders( service_id, service_tag_id, service_hash_ids, 1 )
            
            #self._c.executemany( 'DELETE FROM ' + pending_mappings_table_name + ' WHERE master_tag_id = ? AND master_hash_id = ?;', ( ( master_tag_id, master_hash_id ) for master_hash_id in master_hash_ids ) )
            self._c.executemany( 'DELETE FROM ' + deleted_mappings_table_name + ' WHERE service_tag_id = ? AND service_hash_id = ?;', ( ( service_tag_id, service_hash_id ) for service_hash_id in service_hash_ids ) )
            
        else:
            
            select_statement = 'SELECT service_hash_id FROM ' + deleted_mappings_table_name + ' WHERE service_tag_id = ' + str( service_tag_id ) + ' AND service_hash_id IN %s;'
            
            deleted_service_hash_ids = self._STI( self._SelectFromList( select_statement, service_hash_ids ) )
            
            service_hash_ids = set( service_hash_ids ).difference( deleted_service_hash_ids )
            
        
        # in future, delete from pending with the master ids here
        
        now = HydrusData.GetNow()
        
        self._c.executemany( 'INSERT OR IGNORE INTO ' + current_mappings_table_name + ' ( service_tag_id, service_hash_id, account_id, mapping_timestamp ) VALUES ( ?, ?, ?, ? );', [ ( service_tag_id, service_hash_id, account_id, now ) for service_hash_id in service_hash_ids ] )
        
    
    def _RepositoryAddTagParent( self, service_id, account_id, child_master_tag_id, parent_master_tag_id, overwrite_deleted ):
        
        child_service_tag_id = self._RepositoryGetServiceTagId( service_id, child_master_tag_id )
        parent_service_tag_id = self._RepositoryGetServiceTagId( service_id, parent_master_tag_id )
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        if overwrite_deleted:
            
            self._RepositoryRewardTagParentPenders( service_id, child_master_tag_id, parent_master_tag_id, 1 )
            
            self._c.execute( 'DELETE FROM ' + pending_tag_parents_table_name + ' WHERE child_master_tag_id = ? AND parent_master_tag_id = ?;', ( child_master_tag_id, parent_master_tag_id ) )
            self._c.execute( 'DELETE FROM ' + deleted_tag_parents_table_name + ' WHERE child_service_tag_id = ? AND parent_service_tag_id = ?;', ( child_service_tag_id, parent_service_tag_id ) )
            
        else:
            
            result = self._c.execute( 'SELECT 1 FROM ' + deleted_tag_parents_table_name + ' WHERE child_service_tag_id = ? AND parent_service_tag_id = ?;', ( child_service_tag_id, parent_service_tag_id ) ).fetchone()
            
            if result is not None:
                
                return
                
            
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT OR IGNORE INTO ' + current_tag_parents_table_name + ' ( child_service_tag_id, parent_service_tag_id, account_id, parent_timestamp ) VALUES ( ?, ?, ?, ? );', ( child_service_tag_id, parent_service_tag_id, account_id, now ) )
        
        child_master_hash_ids = self._RepositoryGetCurrentMappingsMasterHashIds( service_id, child_service_tag_id )
        
        self._RepositoryAddMappings( service_id, account_id, parent_master_tag_id, child_master_hash_ids, False )
        
    
    def _RepositoryAddTagSibling( self, service_id, account_id, bad_master_tag_id, good_master_tag_id, overwrite_deleted ):
        
        bad_service_tag_id = self._RepositoryGetServiceTagId( service_id, bad_master_tag_id )
        good_service_tag_id = self._RepositoryGetServiceTagId( service_id, good_master_tag_id )
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        if overwrite_deleted:
            
            self._RepositoryRewardTagSiblingPenders( service_id, bad_master_tag_id, good_master_tag_id, 1 )
            
            self._c.execute( 'DELETE FROM ' + pending_tag_siblings_table_name + ' WHERE bad_master_tag_id = ? AND good_master_tag_id = ?;', ( bad_master_tag_id, good_master_tag_id ) )
            self._c.execute( 'DELETE FROM ' + deleted_tag_siblings_table_name + ' WHERE bad_service_tag_id = ? AND good_service_tag_id = ?;', ( bad_service_tag_id, good_service_tag_id ) )
            
        else:
            
            result = self._c.execute( 'SELECT 1 FROM ' + deleted_tag_siblings_table_name + ' WHERE bad_service_tag_id = ? AND good_service_tag_id = ?;', ( bad_service_tag_id, good_service_tag_id ) ).fetchone()
            
            if result is not None:
                
                return
                
            
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT OR IGNORE INTO ' + current_tag_siblings_table_name + ' ( bad_service_tag_id, good_service_tag_id, account_id, sibling_timestamp ) VALUES ( ?, ?, ?, ? );', ( bad_service_tag_id, good_service_tag_id, account_id, now ) )
        
    
    def _RepositoryBan( self, service_id, subject_account_ids ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        self._c.executemany( 'DELETE FROM ' + pending_files_table_name + ' WHERE account_id = ?;', ( ( subject_account_id, ) for subject_account_id in subject_account_ids ) )
        self._c.executemany( 'DELETE FROM ' + petitioned_files_table_name + ' WHERE account_id = ?;', ( ( subject_account_id, ) for subject_account_id in subject_account_ids ) )
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        self._c.executemany( 'DELETE FROM ' + pending_mappings_table_name + ' WHERE account_id = ?;', ( ( subject_account_id, ) for subject_account_id in subject_account_ids ) )
        self._c.executemany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE account_id = ?;', ( ( subject_account_id, ) for subject_account_id in subject_account_ids ) )
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        self._c.executemany( 'DELETE FROM ' + pending_tag_parents_table_name + ' WHERE account_id = ?;', ( ( subject_account_id, ) for subject_account_id in subject_account_ids ) )
        self._c.executemany( 'DELETE FROM ' + petitioned_tag_parents_table_name + ' WHERE account_id = ?;', ( ( subject_account_id, ) for subject_account_id in subject_account_ids ) )
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        self._c.executemany( 'DELETE FROM ' + pending_tag_siblings_table_name + ' WHERE account_id = ?;', ( ( subject_account_id, ) for subject_account_id in subject_account_ids ) )
        self._c.executemany( 'DELETE FROM ' + petitioned_tag_siblings_table_name + ' WHERE account_id = ?;', ( ( subject_account_id, ) for subject_account_id in subject_account_ids ) )
        
    
    def _RepositoryCreate( self, service_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        self._c.execute( 'CREATE TABLE ' + hash_id_map_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, master_hash_id INTEGER UNIQUE, hash_id_timestamp INTEGER );' )
        self._CreateIndex( hash_id_map_table_name, [ 'hash_id_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + tag_id_map_table_name + ' ( service_tag_id INTEGER PRIMARY KEY, master_tag_id INTEGER UNIQUE, tag_id_timestamp INTEGER );' )
        self._CreateIndex( tag_id_map_table_name, [ 'tag_id_timestamp' ] )
        
        #
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        self._c.execute( 'CREATE TABLE ' + current_files_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, account_id INTEGER, file_timestamp INTEGER );' )
        self._CreateIndex( current_files_table_name, [ 'account_id' ] )
        self._CreateIndex( current_files_table_name, [ 'file_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + deleted_files_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, account_id INTEGER, file_timestamp INTEGER );' )
        self._CreateIndex( deleted_files_table_name, [ 'account_id' ] )
        self._CreateIndex( deleted_files_table_name, [ 'file_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + pending_files_table_name + ' ( master_hash_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( master_hash_id, account_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( pending_files_table_name, [ 'account_id', 'reason_id' ] )
        
        self._c.execute( 'CREATE TABLE ' + petitioned_files_table_name + ' ( service_hash_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( service_hash_id, account_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( petitioned_files_table_name, [ 'account_id', 'reason_id' ] )
        
        self._c.execute( 'CREATE TABLE ' + ip_addresses_table_name + ' ( master_hash_id INTEGER, ip TEXT, ip_timestamp INTEGER );' )
        
        #
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        self._c.execute( 'CREATE TABLE ' + current_mappings_table_name + ' ( service_tag_id INTEGER, service_hash_id INTEGER, account_id INTEGER, mapping_timestamp INTEGER, PRIMARY KEY ( service_tag_id, service_hash_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( current_mappings_table_name, [ 'account_id' ] )
        self._CreateIndex( current_mappings_table_name, [ 'mapping_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + deleted_mappings_table_name + ' ( service_tag_id INTEGER, service_hash_id INTEGER, account_id INTEGER, mapping_timestamp INTEGER, PRIMARY KEY ( service_tag_id, service_hash_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( deleted_mappings_table_name, [ 'account_id' ] )
        self._CreateIndex( deleted_mappings_table_name, [ 'mapping_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + pending_mappings_table_name + ' ( master_tag_id INTEGER, master_hash_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( master_tag_id, master_hash_id, account_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( pending_mappings_table_name, [ 'account_id', 'reason_id' ] )
        
        self._c.execute( 'CREATE TABLE ' + petitioned_mappings_table_name + ' ( service_tag_id INTEGER, service_hash_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( service_tag_id, service_hash_id, account_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( petitioned_mappings_table_name, [ 'account_id', 'reason_id' ] )
        
        #
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        self._c.execute( 'CREATE TABLE ' + current_tag_parents_table_name + ' ( child_service_tag_id INTEGER, parent_service_tag_id INTEGER, account_id INTEGER, parent_timestamp INTEGER, PRIMARY KEY ( child_service_tag_id, parent_service_tag_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( current_tag_parents_table_name, [ 'account_id' ] )
        self._CreateIndex( current_tag_parents_table_name, [ 'parent_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + deleted_tag_parents_table_name + ' ( child_service_tag_id INTEGER, parent_service_tag_id INTEGER, account_id INTEGER, parent_timestamp INTEGER, PRIMARY KEY ( child_service_tag_id, parent_service_tag_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( deleted_tag_parents_table_name, [ 'account_id' ] )
        self._CreateIndex( deleted_tag_parents_table_name, [ 'parent_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + pending_tag_parents_table_name + ' ( child_master_tag_id INTEGER, parent_master_tag_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( child_master_tag_id, parent_master_tag_id, account_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( pending_tag_parents_table_name, [ 'account_id', 'reason_id' ] )
        
        self._c.execute( 'CREATE TABLE ' + petitioned_tag_parents_table_name + ' ( child_service_tag_id INTEGER, parent_service_tag_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( child_service_tag_id, parent_service_tag_id, account_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( petitioned_tag_parents_table_name, [ 'account_id', 'reason_id' ] )
        
        #
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        self._c.execute( 'CREATE TABLE ' + current_tag_siblings_table_name + ' ( bad_service_tag_id INTEGER PRIMARY KEY, good_service_tag_id INTEGER, account_id INTEGER, sibling_timestamp INTEGER );' )
        self._CreateIndex( current_tag_siblings_table_name, [ 'account_id' ] )
        self._CreateIndex( current_tag_siblings_table_name, [ 'sibling_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + deleted_tag_siblings_table_name + ' ( bad_service_tag_id INTEGER PRIMARY KEY, good_service_tag_id INTEGER, account_id INTEGER, sibling_timestamp INTEGER );' )
        self._CreateIndex( deleted_tag_siblings_table_name, [ 'account_id' ] )
        self._CreateIndex( deleted_tag_siblings_table_name, [ 'sibling_timestamp' ] )
        
        self._c.execute( 'CREATE TABLE ' + pending_tag_siblings_table_name + ' ( bad_master_tag_id INTEGER, good_master_tag_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( bad_master_tag_id, account_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( pending_tag_siblings_table_name, [ 'account_id', 'reason_id' ] )
        
        self._c.execute( 'CREATE TABLE ' + petitioned_tag_siblings_table_name + ' ( bad_service_tag_id INTEGER, good_service_tag_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( bad_service_tag_id, account_id ) ) WITHOUT ROWID;' )
        self._CreateIndex( petitioned_tag_siblings_table_name, [ 'account_id', 'reason_id' ] )
        
        #
        
        ( update_table_name ) = GenerateRepositoryUpdateTableName( service_id )
        
        self._c.execute( 'CREATE TABLE ' + update_table_name + ' ( master_hash_id INTEGER PRIMARY KEY );' )
        
    
    def _RepositoryCreateUpdate( self, service_key, begin, end ):
        
        service_id = self._GetServiceId( service_key )
        
        ( name, ) = self._c.execute( 'SELECT name FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        HydrusData.Print( 'Creating update for ' + repr( name ) + ' from ' + HydrusData.ConvertTimestampToPrettyTime( begin ) + ' to ' + HydrusData.ConvertTimestampToPrettyTime( end ) )
        
        updates = self._RepositoryGenerateUpdates( service_id, begin, end )
        
        update_hashes = []
        
        total_definition_rows = 0
        total_content_rows = 0
        
        if len( updates ) > 0:
            
            for update in updates:
                
                num_rows = update.GetNumRows()
                
                if isinstance( update, HydrusNetwork.DefinitionsUpdate ):
                    
                    total_definition_rows += num_rows
                    
                elif isinstance( update, HydrusNetwork.ContentUpdate ):
                    
                    total_content_rows += num_rows
                    
                
                update_bytes = update.DumpToNetworkString()
                
                update_hash = hashlib.sha256( update_bytes ).digest()
                
                dest_path = ServerFiles.GetExpectedFilePath( update_hash )
                
                with open( dest_path, 'wb' ) as f:
                    
                    f.write( update_bytes )
                    
                
                update_hashes.append( update_hash )
                
            
            ( update_table_name ) = GenerateRepositoryUpdateTableName( service_id )
            
            master_hash_ids = self._GetMasterHashIds( update_hashes )
            
            self._c.executemany( 'INSERT OR IGNORE INTO ' + update_table_name + ' ( master_hash_id ) VALUES ( ? );', ( ( master_hash_id, ) for master_hash_id in master_hash_ids ) )
            
        
        HydrusData.Print( 'Update OK. ' + HydrusData.ConvertIntToPrettyString( total_definition_rows ) + ' definition rows and ' + HydrusData.ConvertIntToPrettyString( total_content_rows ) + ' content rows in ' + HydrusData.ConvertIntToPrettyString( len( updates ) ) + ' update files.' )
        
        return update_hashes
        
    
    def _RepositoryDeleteFiles( self, service_id, account_id, service_hash_ids ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        select_statement = 'SELECT service_hash_id FROM ' + current_files_table_name + ' WHERE service_hash_id IN %s;'
        
        valid_service_hash_ids = self._STL( self._SelectFromList( select_statement, service_hash_ids ) )
        
        self._RepositoryRewardFilePetitioners( service_id, valid_service_hash_ids, 1 )
        
        self._c.executemany( 'DELETE FROM ' + current_files_table_name + ' WHERE service_hash_id = ?', ( ( service_hash_id, ) for service_hash_id in valid_service_hash_ids ) )
        self._c.executemany( 'DELETE FROM ' + petitioned_files_table_name + ' WHERE service_hash_id = ?', ( ( service_hash_id, ) for service_hash_id in valid_service_hash_ids ) )
        
        now = HydrusData.GetNow()
        
        self._c.executemany( 'INSERT OR IGNORE INTO ' + deleted_files_table_name + ' ( service_hash_id, account_id, file_timestamp ) VALUES ( ?, ?, ? );', ( ( service_hash_id, account_id, now ) for service_hash_id in valid_service_hash_ids ) )
        
    
    def _RepositoryDeleteMappings( self, service_id, account_id, service_tag_id, service_hash_ids ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        select_statement = 'SELECT service_hash_id FROM ' + current_mappings_table_name + ' WHERE service_tag_id = ' + str( service_tag_id ) + ' AND service_hash_id IN %s;'
        
        valid_service_hash_ids = self._STL( self._SelectFromList( select_statement, service_hash_ids ) )
        
        self._RepositoryRewardMappingPetitioners( service_id, service_tag_id, valid_service_hash_ids, 1 )
        
        self._c.executemany( 'DELETE FROM ' + current_mappings_table_name + ' WHERE service_tag_id = ? AND service_hash_id = ?;', ( ( service_tag_id, service_hash_id ) for service_hash_id in valid_service_hash_ids ) )
        self._c.executemany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE service_tag_id = ? AND service_hash_id = ?;', ( ( service_tag_id, service_hash_id ) for service_hash_id in valid_service_hash_ids ) )
        
        now = HydrusData.GetNow()
        
        self._c.executemany( 'INSERT OR IGNORE INTO ' + deleted_mappings_table_name + ' ( service_tag_id, service_hash_id, account_id, mapping_timestamp ) VALUES ( ?, ?, ?, ? );', ( ( service_tag_id, service_hash_id, account_id, now ) for service_hash_id in valid_service_hash_ids ) )
        
    
    def _RepositoryDeleteTagParent( self, service_id, account_id, child_service_tag_id, parent_service_tag_id ):
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        self._RepositoryRewardTagParentPetitioners( service_id, child_service_tag_id, parent_service_tag_id, 1 )
        
        self._c.execute( 'DELETE FROM ' + current_tag_parents_table_name + ' WHERE child_service_tag_id = ? AND parent_service_tag_id = ?;', ( child_service_tag_id, parent_service_tag_id ) )
        self._c.execute( 'DELETE FROM ' + petitioned_tag_parents_table_name + ' WHERE child_service_tag_id = ? AND parent_service_tag_id = ?;', ( child_service_tag_id, parent_service_tag_id ) )
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT OR IGNORE INTO ' + deleted_tag_parents_table_name + ' ( child_service_tag_id, parent_service_tag_id, account_id, parent_timestamp ) VALUES ( ?, ?, ?, ? );', ( child_service_tag_id, parent_service_tag_id, account_id, now ) )
        
    
    def _RepositoryDeleteTagSibling( self, service_id, account_id, bad_service_tag_id, good_service_tag_id ):
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        self._RepositoryRewardTagSiblingPetitioners( service_id, bad_service_tag_id, good_service_tag_id, 1 )
        
        self._c.execute( 'DELETE FROM ' + current_tag_siblings_table_name + ' WHERE bad_service_tag_id = ? AND good_service_tag_id = ?;', ( bad_service_tag_id, good_service_tag_id ) )
        self._c.execute( 'DELETE FROM ' + petitioned_tag_siblings_table_name + ' WHERE bad_service_tag_id = ? AND good_service_tag_id = ?;', ( bad_service_tag_id, good_service_tag_id ) )
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT OR IGNORE INTO ' + deleted_tag_siblings_table_name + ' ( bad_service_tag_id, good_service_tag_id, account_id, sibling_timestamp ) VALUES ( ?, ?, ?, ? );', ( bad_service_tag_id, good_service_tag_id, account_id, now ) )
        
    
    def _RepositoryDenyFilePetition( self, service_id, service_hash_ids ):
        
        self._RepositoryRewardFilePetitioners( service_id, service_hash_ids, -1 )
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        self._c.executemany( 'DELETE FROM ' + petitioned_files_table_name + ' WHERE service_hash_id = ?;', ( ( service_hash_id, ) for service_hash_id in service_hash_ids ) )
        
    
    def _RepositoryDenyMappingPetition( self, service_id, service_tag_id, service_hash_ids ):
        
        self._RepositoryRewardMappingPetitioners( service_id, service_tag_id, service_hash_ids, -1 )
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        self._c.executemany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE service_tag_id = ? AND service_hash_id = ?;', ( ( service_tag_id, service_hash_id ) for service_hash_id in service_hash_ids ) )
        
    
    def _RepositoryDenyTagParentPend( self, service_id, child_master_tag_id, parent_master_tag_id ):
        
        self._RepositoryRewardTagParentPenders( service_id, child_master_tag_id, parent_master_tag_id, -1 )
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        self._c.execute( 'DELETE FROM ' + pending_tag_parents_table_name + ' WHERE child_master_tag_id = ? AND parent_master_tag_id = ?;', ( child_master_tag_id, parent_master_tag_id ) )
        
    
    def _RepositoryDenyTagParentPetition( self, service_id, child_service_tag_id, parent_service_tag_id ):
        
        self._RepositoryRewardTagParentPetitioners( service_id, child_service_tag_id, parent_service_tag_id, -1 )
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        self._c.execute( 'DELETE FROM ' + petitioned_tag_parents_table_name + ' WHERE child_service_tag_id = ? AND parent_service_tag_id = ?;', ( child_service_tag_id, parent_service_tag_id ) )
        
    
    def _RepositoryDenyTagSiblingPend( self, service_id, bad_master_tag_id, good_master_tag_id ):
        
        self._RepositoryRewardTagSiblingPenders( service_id, bad_master_tag_id, good_master_tag_id, -1 )
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        self._c.execute( 'DELETE FROM ' + pending_tag_siblings_table_name + ' WHERE bad_master_tag_id = ? AND good_master_tag_id = ?;', ( bad_master_tag_id, good_master_tag_id ) )
        
    
    def _RepositoryDenyTagSiblingPetition( self, service_id, bad_service_tag_id, good_service_tag_id ):
        
        self._RepositoryRewardTagSiblingPetitioners( service_id, bad_service_tag_id, good_service_tag_id, -1 )
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        self._c.execute( 'DELETE FROM ' + petitioned_tag_siblings_table_name + ' WHERE bad_service_tag_id = ? AND good_service_tag_id = ?;', ( bad_service_tag_id, good_service_tag_id ) )
        
    
    def _RepositoryDrop( self, service_id ):
        
        table_names = []
        
        table_names.extend( GenerateRepositoryMasterMapTableNames( service_id ) )
        
        table_names.extend( GenerateRepositoryFilesTableNames( service_id ) )
        
        table_names.extend( GenerateRepositoryMappingsTableNames( service_id ) )
        
        table_names.extend( GenerateRepositoryTagParentsTableNames( service_id ) )
        
        table_names.extend( GenerateRepositoryTagSiblingsTableNames( service_id ) )
        
        table_names.append( GenerateRepositoryUpdateTableName( service_id ) )
        
        for table_name in table_names:
            
            self._c.execute( 'DROP TABLE ' + table_name + ';' )
            
        
    
    def _RepositoryGenerateImmediateUpdate( self, service_key, account, begin, end ):
        
        if True not in ( account.HasPermission( content_type, HC.PERMISSION_ACTION_OVERRULE ) for content_type in HC.REPOSITORY_CONTENT_TYPES ):
            
            raise HydrusExceptions.PermissionException( 'You do not have permission to generate an immediate update!' )
            
        
        service_id = self._GetServiceId( service_key )
        
        updates = self._RepositoryGenerateUpdates( service_id, begin, end )
        
        return updates
        
    
    def _RepositoryGenerateUpdates( self, service_id, begin, end ):
        
        MAX_DEFINITIONS_ROWS = 50000
        MAX_CONTENT_ROWS = 250000
        
        MAX_CONTENT_CHUNK = 25000
        
        updates = []
        
        definitions_update_builder = HydrusNetwork.UpdateBuilder( HydrusNetwork.DefinitionsUpdate, MAX_DEFINITIONS_ROWS )
        content_update_builder = HydrusNetwork.UpdateBuilder( HydrusNetwork.ContentUpdate, MAX_CONTENT_ROWS )
        
        ( service_hash_ids_table_name, service_tag_ids_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        for ( service_hash_id, hash ) in self._c.execute( 'SELECT service_hash_id, hash FROM ' + service_hash_ids_table_name + ' NATURAL JOIN hashes WHERE hash_id_timestamp BETWEEN ? AND ?;', ( begin, end ) ):
            
            row = ( HC.DEFINITIONS_TYPE_HASHES, service_hash_id, hash )
            
            definitions_update_builder.AddRow( row )
            
        
        for ( service_tag_id, tag ) in self._c.execute( 'SELECT service_tag_id, tag FROM ' + service_tag_ids_table_name + ' NATURAL JOIN tags WHERE tag_id_timestamp BETWEEN ? AND ?;', ( begin, end ) ):
            
            row = ( HC.DEFINITIONS_TYPE_TAGS, service_tag_id, tag )
            
            definitions_update_builder.AddRow( row )
            
        
        definitions_update_builder.Finish()
        
        updates.extend( definitions_update_builder.GetUpdates() )
        
        #
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        table_join = self._RepositoryGetFilesInfoFilesTableJoin( service_id, HC.CONTENT_STATUS_CURRENT )
        
        for ( service_hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in self._c.execute( 'SELECT service_hash_id, size, mime, file_timestamp, width, height, duration, num_frames, num_words FROM ' + table_join + ' WHERE file_timestamp BETWEEN ? AND ?;', ( begin, end ) ):
            
            file_row = ( service_hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words )
            
            content_update_builder.AddRow( ( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, file_row ) )
            
        
        service_hash_ids = [ service_hash_id for ( service_hash_id, ) in self._c.execute( 'SELECT service_hash_id FROM ' + deleted_files_table_name + ' WHERE file_timestamp BETWEEN ? AND ?;', ( begin, end ) ) ]
        
        for service_hash_id in service_hash_ids:
            
            content_update_builder.AddRow( ( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, service_hash_id ) )
            
        
        #
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        service_tag_ids_to_service_hash_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT service_tag_id, service_hash_id FROM ' + current_mappings_table_name + ' WHERE mapping_timestamp BETWEEN ? AND ?;', ( begin, end ) ) )
        
        for ( service_tag_id, service_hash_ids ) in service_tag_ids_to_service_hash_ids.items():
            
            for block_of_service_hash_ids in HydrusData.SplitListIntoChunks( service_hash_ids, MAX_CONTENT_CHUNK ):
                
                row_weight = len( block_of_service_hash_ids )
                
                content_update_builder.AddRow( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( service_tag_id, block_of_service_hash_ids ) ), row_weight )
                
            
        
        service_tag_ids_to_service_hash_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT service_tag_id, service_hash_id FROM ' + deleted_mappings_table_name + ' WHERE mapping_timestamp BETWEEN ? AND ?;', ( begin, end ) ) )
        
        for ( service_tag_id, service_hash_ids ) in service_tag_ids_to_service_hash_ids.items():
            
            for block_of_service_hash_ids in HydrusData.SplitListIntoChunks( service_hash_ids, MAX_CONTENT_CHUNK ):
                
                row_weight = len( block_of_service_hash_ids )
                
                content_update_builder.AddRow( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( service_tag_id, block_of_service_hash_ids ) ), row_weight )
                
            
        
        #
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        pairs = self._c.execute( 'SELECT child_service_tag_id, parent_service_tag_id FROM ' + current_tag_parents_table_name + ' WHERE parent_timestamp BETWEEN ? AND ?;', ( begin, end ) ).fetchall()
        
        for pair in pairs:
            
            content_update_builder.AddRow( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD, pair ) )
            
        
        pairs = self._c.execute( 'SELECT child_service_tag_id, parent_service_tag_id FROM ' + deleted_tag_parents_table_name + ' WHERE parent_timestamp BETWEEN ? AND ?;', ( begin, end ) ).fetchall()
        
        for pair in pairs:
            
            content_update_builder.AddRow( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DELETE, pair ) )
            
        
        #
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        pairs = self._c.execute( 'SELECT bad_service_tag_id, good_service_tag_id FROM ' + current_tag_siblings_table_name + ' WHERE sibling_timestamp BETWEEN ? AND ?;', ( begin, end ) ).fetchall()
        
        for pair in pairs:
            
            content_update_builder.AddRow( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, pair ) )
            
        
        pairs = self._c.execute( 'SELECT bad_service_tag_id, good_service_tag_id FROM ' + deleted_tag_siblings_table_name + ' WHERE sibling_timestamp BETWEEN ? AND ?;', ( begin, end ) ).fetchall()
        
        for pair in pairs:
            
            content_update_builder.AddRow( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, pair ) )
            
        
        #
        
        content_update_builder.Finish()
        
        updates.extend( content_update_builder.GetUpdates() )
        
        return updates
        
    
    def _RepositoryGetAccountInfo( self, service_id, account_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        table_join = 'file_info NATURAL JOIN ' + hash_id_map_table_name + ' NATURAL JOIN ' + current_files_table_name
        
        ( num_files, num_files_bytes ) = self._c.execute( 'SELECT COUNT( * ), SUM( size ) FROM ' + table_join + ' WHERE account_id = ?;', ( account_id, ) ).fetchone()
        
        if num_files_bytes is None:
            
            num_files_bytes = 0
            
        
        account_info = {}
        
        account_info[ 'num_files' ] = num_files
        account_info[ 'num_files_bytes' ] = num_files_bytes
        
        #
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        num_mappings = len( self._c.execute( 'SELECT 1 FROM ' + current_mappings_table_name + ' WHERE account_id = ? LIMIT 5000;', ( account_id, ) ).fetchall() )
        
        account_info[ 'num_mappings' ] = num_mappings
        
        #
        
        result = self._c.execute( 'SELECT score FROM account_scores WHERE service_id = ? AND account_id = ? AND score_type = ?;', ( service_id, account_id, HC.SCORE_PETITION ) ).fetchone()
        
        if result is None: petition_score = 0
        else: ( petition_score, ) = result
        
        account_info[ 'petition_score' ] = petition_score
        
        return account_info
        
    
    def _RepositoryGetCurrentMappingsCount( self, service_id, service_tag_id ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        ( count, ) = self._c.execute( 'SELECT COUNT( * ) FROM ' + current_mappings_table_name + ' WHERE service_tag_id = ?;', ( service_tag_id, ) ).fetchone()
        
        return count
        
    
    def _RepositoryGetCurrentMappingsMasterHashIds( self, service_id, service_tag_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        master_hash_ids = [ master_hash_id for ( master_hash_id, ) in self._c.execute( 'SELECT master_hash_id FROM ' + hash_id_map_table_name + ' NATURAL JOIN ' + current_mappings_table_name + ' WHERE service_tag_id = ?;', ( service_tag_id, ) ) ]
        
        return master_hash_ids
        
    
    def _RepositoryGetFilesInfoFilesTableJoin( self, service_id, content_status ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        if content_status == HC.CONTENT_STATUS_CURRENT:
            
            return 'files_info NATURAL JOIN ' + hash_id_map_table_name + ' NATURAL JOIN ' + current_files_table_name
            
        elif content_status == HC.CONTENT_STATUS_DELETED:
            
            return 'files_info NATURAL JOIN ' + hash_id_map_table_name + ' NATURAL JOIN ' + deleted_files_table_name
            
        elif content_status == HC.CONTENT_STATUS_PENDING:
            
            return 'files_info NATURAL JOIN ' + hash_id_map_table_name + ' NATURAL JOIN ' + pending_files_table_name
            
        elif content_status == HC.CONTENT_STATUS_PETITIONED:
            
            return 'files_info NATURAL JOIN ' + hash_id_map_table_name + ' NATURAL JOIN ' + petitioned_files_table_name
            
        
    
    def _RepositoryGetFilePetition( self, service_id ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        result = self._c.execute( 'SELECT account_id, reason_id FROM ' + petitioned_files_table_name + ' ORDER BY RANDOM() LIMIT 1;' ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'No petitions!' )
            
        
        ( petitioner_account_id, reason_id ) = result
        
        action = HC.CONTENT_UPDATE_PETITION
        
        petitioner_account = self._GetAccount( service_id, petitioner_account_id )
        
        reason = self._GetReason( reason_id )
        
        service_hash_ids = [ service_hash_id for ( service_hash_id, ) in self._c.execute( 'SELECT service_hash_id FROM ' + petitioned_files_table_name + ' WHERE account_id = ? AND reason_id = ?;', ( petitioner_account_id, reason_id ) ) ]
        
        master_hash_ids = self._RepositoryGetMasterHashIds( service_id, service_hash_ids )
        
        hashes = self._GetHashes( master_hash_ids )
        
        content_type = HC.CONTENT_TYPE_FILES
        
        contents = [ HydrusNetwork.Content( content_type, hashes ) ]
        
        return HydrusNetwork.Petition( action, petitioner_account, reason, contents )
        
    
    def _RepositoryGetIPTimestamp( self, service_key, account, hash ):
        
        account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
        
        service_id = self._GetServiceId( service_key )
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        master_hash_id = self._GetMasterHashId( hash )
        
        result = self._c.execute( 'SELECT ip, ip_timestamp FROM ' + ip_addresses_table_name + ' WHERE master_hash_id = ?;', ( master_hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.ForbiddenException( 'Did not find ip information for that hash.' )
            
        
        return result
        
    
    def _RepositoryGetNumPetitions( self, service_key, account ):
        
        service_id = self._GetServiceId( service_key )
        
        petition_count_info = []
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        if account.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_OVERRULE ):
            
            ( num_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT account_id, reason_id FROM ' + petitioned_files_table_name + ' );' ).fetchone()
            
            petition_count_info.append( ( HC.CONTENT_TYPE_FILES, HC.CONTENT_STATUS_PETITIONED, num_petitions ) )
            
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        if account.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_OVERRULE ):
            
            ( num_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT service_tag_id, account_id, reason_id FROM ' + petitioned_mappings_table_name + ' );' ).fetchone()
            
            petition_count_info.append( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED, num_petitions ) )
            
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        if account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_OVERRULE ):
            
            ( num_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ' + pending_tag_parents_table_name + ';' ).fetchone()
            
            petition_count_info.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING, num_petitions ) )
            
            ( num_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ' + petitioned_tag_parents_table_name + ';' ).fetchone()
            
            petition_count_info.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PETITIONED, num_petitions ) )
            
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        if account.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_OVERRULE ):
            
            ( num_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ' + pending_tag_siblings_table_name + ';' ).fetchone()
            
            petition_count_info.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PENDING, num_petitions ) )
            
            ( num_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ' + petitioned_tag_siblings_table_name + ';' ).fetchone()
            
            petition_count_info.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PETITIONED, num_petitions ) )
            
        
        return petition_count_info
        
    
    def _RepositoryGetMappingPetition( self, service_id ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        result = self._c.execute( 'SELECT account_id, reason_id FROM ' + petitioned_mappings_table_name + ' ORDER BY RANDOM() LIMIT 1;' ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'No petitions!' )
            
        
        ( petitioner_account_id, reason_id ) = result
        
        action = HC.CONTENT_UPDATE_PETITION
        
        petitioner_account = self._GetAccount( service_id, petitioner_account_id )
        
        reason = self._GetReason( reason_id )
        
        tag_ids_to_hash_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT service_tag_id, service_hash_id FROM ' + petitioned_mappings_table_name + ' WHERE account_id = ? AND reason_id = ?;', ( petitioner_account_id, reason_id ) ) )
        
        contents = []
        
        for ( service_tag_id, service_hash_ids ) in tag_ids_to_hash_ids.items():
            
            master_tag_id = self._RepositoryGetMasterTagId( service_id, service_tag_id )
            master_hash_ids = self._RepositoryGetMasterHashIds( service_id, service_hash_ids )
            
            tag = self._GetTag( master_tag_id )
            
            hashes = self._GetHashes( master_hash_ids )
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag, hashes ) )
            
            contents.append( content )
            
        
        return HydrusNetwork.Petition( action, petitioner_account, reason, contents )
        
        
    
    def _RepositoryGetMasterHashIds( self, service_id, service_hash_ids ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        select_statement = 'SELECT master_hash_id FROM ' + hash_id_map_table_name + ' WHERE service_hash_id IN %s;'
        
        master_hash_ids = [ master_hash_id for ( master_hash_id, ) in self._SelectFromList( select_statement, service_hash_ids ) ]
        
        if len( service_hash_ids ) != len( master_hash_ids ):
            
            raise HydrusExceptions.DataMissing( 'Missing master_hash_id map error!' )
            
        
        return master_hash_ids
        
    
    def _RepositoryGetMasterTagId( self, service_id, service_tag_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        result = self._c.execute( 'SELECT master_tag_id FROM ' + tag_id_map_table_name + ' WHERE service_tag_id = ?;', ( service_tag_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Missing master_tag_id map error!' )
            
        
        ( master_tag_id, ) = result
        
        return master_tag_id
        
    
    def _RepositoryGetPetition( self, service_key, account, content_type, status ):
        
        service_id = self._GetServiceId( service_key )
        
        account.CheckPermission( content_type, HC.PERMISSION_ACTION_OVERRULE )
        
        if content_type == HC.CONTENT_TYPE_FILES:
            
            petition = self._RepositoryGetFilePetition( service_id )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            petition = self._RepositoryGetMappingPetition( service_id )
            
        elif content_type == HC.CONTENT_TYPE_TAG_PARENTS:
            
            if status == HC.CONTENT_STATUS_PENDING:
                
                petition = self._RepositoryGetTagParentPend( service_id )
                
            else:
                
                petition = self._RepositoryGetTagParentPetition( service_id )
                
            
        elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
            
            if status == HC.CONTENT_STATUS_PENDING:
                
                petition = self._RepositoryGetTagSiblingPend( service_id )
                
            else:
                
                petition = self._RepositoryGetTagSiblingPetition( service_id )
                
            
        
        return petition
        
    
    def _RepositoryGetServiceHashId( self, service_id, master_hash_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        result = self._c.execute( 'SELECT service_hash_id FROM ' + hash_id_map_table_name + ' WHERE master_hash_id = ?;', ( master_hash_id, ) ).fetchone()
        
        if result is None:
            
            now = HydrusData.GetNow()
            
            self._c.execute( 'INSERT INTO ' + hash_id_map_table_name + ' ( master_hash_id, hash_id_timestamp ) VALUES ( ?, ? );', ( master_hash_id, now ) )
            
            service_hash_id = self._c.lastrowid
            
            return service_hash_id
            
        else:
            
            ( service_hash_id, ) = result
            
            return service_hash_id
            
        
    
    def _RepositoryGetServiceHashIds( self, service_id, master_hash_ids ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        service_hash_ids = set()
        master_hash_ids_not_in_table = set()
        
        for master_hash_id in master_hash_ids:
            
            result = self._c.execute( 'SELECT service_hash_id FROM ' + hash_id_map_table_name + ' WHERE master_hash_id = ?;', ( master_hash_id, ) ).fetchone()
            
            if result is None:
                
                master_hash_ids_not_in_table.add( master_hash_id )
                
            else:
                
                ( service_hash_id, ) = result
                
                service_hash_ids.add( service_hash_id )
                
            
        
        if len( master_hash_ids_not_in_table ) > 0:
            
            now = HydrusData.GetNow()
            
            self._c.executemany( 'INSERT INTO ' + hash_id_map_table_name + ' ( master_hash_id, hash_id_timestamp ) VALUES ( ?, ? );', ( ( master_hash_id, now ) for master_hash_id in master_hash_ids_not_in_table ) )
            
            for master_hash_id in master_hash_ids_not_in_table:
                
                ( service_hash_id, ) = self._c.execute( 'SELECT service_hash_id FROM ' + hash_id_map_table_name + ' WHERE master_hash_id = ?;', ( master_hash_id, ) ).fetchone()
                
                service_hash_ids.add( service_hash_id )
                
            
        
        return service_hash_ids
        
    
    def _RepositoryGetServiceTagId( self, service_id, master_tag_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        result = self._c.execute( 'SELECT service_tag_id FROM ' + tag_id_map_table_name + ' WHERE master_tag_id = ?;', ( master_tag_id, ) ).fetchone()
        
        if result is None:
            
            now = HydrusData.GetNow()
            
            self._c.execute( 'INSERT INTO ' + tag_id_map_table_name + ' ( master_tag_id, tag_id_timestamp ) VALUES ( ?, ? );', ( master_tag_id, now ) )
            
            service_tag_id = self._c.lastrowid
            
            return service_tag_id
            
        else:
            
            ( service_tag_id, ) = result
            
            return service_tag_id
            
        
    
    def _RepositoryGetTagParentPend( self, service_id ):
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        result = self._c.execute( 'SELECT account_id, reason_id FROM ' + pending_tag_parents_table_name + ' ORDER BY RANDOM() LIMIT 1;' ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'No petitions!' )
            
        
        ( petitioner_account_id, reason_id ) = result
        
        action = HC.CONTENT_UPDATE_PEND
        
        petitioner_account = self._GetAccount( service_id, petitioner_account_id )
        
        reason = self._GetReason( reason_id )
        
        pairs = self._c.execute( 'SELECT child_master_tag_id, parent_master_tag_id FROM ' + pending_tag_parents_table_name + ' WHERE account_id = ? AND reason_id = ?;', ( petitioner_account_id, reason_id ) ).fetchall()
        
        contents = []
        
        for ( child_master_tag_id, parent_master_tag_id ) in pairs:
            
            child_tag = self._GetTag( child_master_tag_id )
            parent_tag = self._GetTag( parent_master_tag_id )
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag, parent_tag ) )
            
            contents.append( content )
            
        
        return HydrusNetwork.Petition( action, petitioner_account, reason, contents )
        
    
    def _RepositoryGetTagParentPetition( self, service_id ):
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        result = self._c.execute( 'SELECT account_id, reason_id FROM ' + petitioned_tag_parents_table_name + ' ORDER BY RANDOM() LIMIT 1;' ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'No petitions!' )
            
        
        ( petitioner_account_id, reason_id ) = result
        
        action = HC.CONTENT_UPDATE_PETITION
        
        petitioner_account = self._GetAccount( service_id, petitioner_account_id )
        
        reason = self._GetReason( reason_id )
        
        pairs = self._c.execute( 'SELECT child_service_tag_id, parent_service_tag_id FROM ' + petitioned_tag_parents_table_name + ' WHERE account_id = ? AND reason_id = ?;', ( petitioner_account_id, reason_id ) ).fetchall()
        
        contents = []
        
        for ( child_service_tag_id, parent_service_tag_id ) in pairs:
            
            child_master_tag_id = self._RepositoryGetMasterTagId( service_id, child_service_tag_id )
            parent_master_tag_id = self._RepositoryGetMasterTagId( service_id, parent_service_tag_id )
            
            child_tag = self._GetTag( child_master_tag_id )
            parent_tag = self._GetTag( parent_master_tag_id )
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag, parent_tag ) )
            
            contents.append( content )
            
        
        return HydrusNetwork.Petition( action, petitioner_account, reason, contents )
        
    
    def _RepositoryGetTagSiblingPend( self, service_id ):
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        result = self._c.execute( 'SELECT account_id, reason_id FROM ' + pending_tag_siblings_table_name + ' ORDER BY RANDOM() LIMIT 1;' ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'No petitions!' )
            
        
        ( petitioner_account_id, reason_id ) = result
        
        action = HC.CONTENT_UPDATE_PEND
        
        petitioner_account = self._GetAccount( service_id, petitioner_account_id )
        
        reason = self._GetReason( reason_id )
        
        pairs = self._c.execute( 'SELECT bad_master_tag_id, good_master_tag_id FROM ' + pending_tag_siblings_table_name + ' WHERE account_id = ? AND reason_id = ?;', ( petitioner_account_id, reason_id ) ).fetchall()
        
        contents = []
        
        for ( bad_master_tag_id, good_master_tag_id ) in pairs:
            
            bad_tag = self._GetTag( bad_master_tag_id )
            good_tag = self._GetTag( good_master_tag_id )
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag, good_tag ) )
            
            contents.append( content )
            
        
        return HydrusNetwork.Petition( action, petitioner_account, reason, contents )
        
    
    def _RepositoryGetTagSiblingPetition( self, service_id ):
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        result = self._c.execute( 'SELECT account_id, reason_id FROM ' + petitioned_tag_siblings_table_name + ' ORDER BY RANDOM() LIMIT 1;' ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'No petitions!' )
            
        
        ( petitioner_account_id, reason_id ) = result
        
        action = HC.CONTENT_UPDATE_PETITION
        
        petitioner_account = self._GetAccount( service_id, petitioner_account_id )
        
        reason = self._GetReason( reason_id )
        
        pairs = self._c.execute( 'SELECT bad_service_tag_id, good_service_tag_id FROM ' + petitioned_tag_siblings_table_name + ' WHERE account_id = ? AND reason_id = ?;', ( petitioner_account_id, reason_id ) ).fetchall()
        
        contents = []
        
        for ( bad_service_tag_id, good_service_tag_id ) in pairs:
            
            bad_master_tag_id = self._RepositoryGetMasterTagId( service_id, bad_service_tag_id )
            good_master_tag_id = self._RepositoryGetMasterTagId( service_id, good_service_tag_id )
            
            bad_tag = self._GetTag( bad_master_tag_id )
            good_tag = self._GetTag( good_master_tag_id )
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag, good_tag ) )
            
            contents.append( content )
            
        
        return HydrusNetwork.Petition( action, petitioner_account, reason, contents )
        
    
    def _RepositoryHasFile( self, service_key, hash ):
        
        if not self._MasterHashExists( hash ):
            
            return ( False, None )
            
        
        service_id = self._GetServiceId( service_key )
        
        master_hash_id = self._GetMasterHashId( hash )
        
        table_join = self._RepositoryGetFilesInfoFilesTableJoin( service_id, HC.CONTENT_STATUS_CURRENT )
        
        result = self._c.execute( 'SELECT mime FROM ' + table_join + ' WHERE master_hash_id = ?;', ( master_hash_id, ) ).fetchone()
        
        if result is None:
            
            return ( False, None )
            
        
        ( mime, ) = result
        
        return ( True, mime )
        
    
    def _RepositoryPendTagParent( self, service_id, account_id, child_master_tag_id, parent_master_tag_id, reason_id ):
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        child_exists = self._RepositoryServiceTagIdExists( service_id, child_master_tag_id )
        parent_exists = self._RepositoryServiceTagIdExists( service_id, parent_master_tag_id )
        
        if child_exists and parent_exists:
            
            child_service_tag_id = self._RepositoryGetServiceTagId( service_id, child_master_tag_id )
            parent_service_tag_id = self._RepositoryGetServiceTagId( service_id, parent_master_tag_id )
            
            result = self._c.execute( 'SELECT 1 FROM ' + current_tag_parents_table_name + ' WHERE child_service_tag_id = ? AND parent_service_tag_id = ?;', ( child_service_tag_id, parent_service_tag_id ) ).fetchone()
            
            if result is not None:
                
                return
                
            
        
        self._c.execute( 'REPLACE INTO ' + pending_tag_parents_table_name + ' ( child_master_tag_id, parent_master_tag_id, account_id, reason_id ) VALUES ( ?, ?, ?, ? );', ( child_master_tag_id, parent_master_tag_id, account_id, reason_id ) )
        
    
    def _RepositoryPendTagSibling( self, service_id, account_id, bad_master_tag_id, good_master_tag_id, reason_id ):
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        bad_exists = self._RepositoryServiceTagIdExists( service_id, bad_master_tag_id )
        good_exists = self._RepositoryServiceTagIdExists( service_id, good_master_tag_id )
        
        if bad_exists and good_exists:
            
            bad_service_tag_id = self._RepositoryGetServiceTagId( service_id, bad_master_tag_id )
            good_service_tag_id = self._RepositoryGetServiceTagId( service_id, good_master_tag_id )
            
            result = self._c.execute( 'SELECT 1 FROM ' + current_tag_siblings_table_name + ' WHERE bad_service_tag_id = ? AND good_service_tag_id = ?;', ( bad_service_tag_id, good_service_tag_id ) ).fetchone()
            
            if result is not None:
                
                return
                
            
        
        self._c.execute( 'REPLACE INTO ' + pending_tag_siblings_table_name + ' ( bad_master_tag_id, good_master_tag_id, account_id, reason_id ) VALUES ( ?, ?, ?, ? );', ( bad_master_tag_id, good_master_tag_id, account_id, reason_id ) )
        
    
    def _RepositoryPetitionFiles( self, service_id, account_id, service_hash_ids, reason_id ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        select_statement = 'SELECT service_hash_id FROM ' + current_files_table_name + ' WHERE service_hash_id IN %s;'
        
        valid_service_hash_ids = [ service_hash_id for ( service_hash_id, ) in self._SelectFromList( select_statement, service_hash_ids ) ]
        
        now = HydrusData.GetNow()
        
        self._c.executemany( 'REPLACE INTO ' + petitioned_files_table_name + ' ( service_hash_id, account_id, reason_id ) VALUES ( ?, ?, ? );', ( ( service_hash_id, account_id, reason_id ) for service_hash_id in valid_service_hash_ids ) )
        
    
    def _RepositoryPetitionMappings( self, service_id, account_id, service_tag_id, service_hash_ids, reason_id ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        select_statement = 'SELECT service_hash_id FROM ' + current_mappings_table_name + ' WHERE service_tag_id = ' + str( service_tag_id ) + ' AND service_hash_id IN %s;'
        
        valid_service_hash_ids = [ service_hash_id for ( service_hash_id, ) in self._SelectFromList( select_statement, service_hash_ids ) ]
        
        self._c.executemany( 'REPLACE INTO ' + petitioned_mappings_table_name + ' ( service_tag_id, service_hash_id, account_id, reason_id ) VALUES ( ?, ?, ?, ? );', [ ( service_tag_id, service_hash_id, account_id, reason_id ) for service_hash_id in valid_service_hash_ids ] )
        
    
    def _RepositoryPetitionTagParent( self, service_id, account_id, child_service_tag_id, parent_service_tag_id, reason_id ):
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        result = self._c.execute( 'SELECT 1 FROM ' + current_tag_parents_table_name + ' WHERE child_service_tag_id = ? AND parent_service_tag_id = ?;', ( child_service_tag_id, parent_service_tag_id ) ).fetchone()
        
        if result is None:
            
            return
            
        
        self._c.execute( 'REPLACE INTO ' + petitioned_tag_parents_table_name + ' ( child_service_tag_id, parent_service_tag_id, account_id, reason_id ) VALUES ( ?, ?, ?, ? );', ( child_service_tag_id, parent_service_tag_id, account_id, reason_id ) )
        
    
    def _RepositoryPetitionTagSibling( self, service_id, account_id, bad_service_tag_id, good_service_tag_id, reason_id ):
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        result = self._c.execute( 'SELECT 1 FROM ' + current_tag_siblings_table_name + ' WHERE bad_service_tag_id = ? AND good_service_tag_id = ?;', ( bad_service_tag_id, good_service_tag_id ) ).fetchone()
        
        if result is None:
            
            return
            
        
        self._c.execute( 'REPLACE INTO ' + petitioned_tag_siblings_table_name + ' ( bad_service_tag_id, good_service_tag_id, account_id, reason_id ) VALUES ( ?, ?, ?, ? );', ( bad_service_tag_id, good_service_tag_id, account_id, reason_id ) )
        
    
    def _RepositoryProcessAddFile( self, service, account, file_dict ):
        
        service_key = service.GetServiceKey()
        
        service_id = self._GetServiceId( service_key )
        
        account_key = account.GetAccountKey()
        
        account_id = self._GetAccountId( account_key )
        
        can_petition_files = account.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_PETITION )
        can_create_files = account.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_CREATE )
        can_overrule_files = account.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_OVERRULE )
        
        # later add pend file here however that is neat
        
        if can_create_files or can_overrule_files:
            
            if not can_overrule_files:
                
                max_storage = service.GetMaxStorage()
                
                if max_storage is not None:
                    
                    ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
                    
                    table_join = self._RepositoryGetFilesInfoFilesTableJoin( service_id, HC.CONTENT_STATUS_CURRENT )
                    
                    ( total_current_storage, ) = self._c.execute( 'SELECT SUM( size ) FROM ' + table_join + ';' ).fetchone()
                    
                    if total_current_storage is None:
                        
                        total_current_storage = 0
                        
                    
                    table_join = self._RepositoryGetFilesInfoFilesTableJoin( service_id, HC.CONTENT_STATUS_PENDING )
                    
                    ( total_pending_storage, ) = self._c.execute( 'SELECT SUM( size ) FROM ' + table_join + ';' ).fetchone()
                    
                    if total_pending_storage is None:
                        
                        total_pending_storage = 0
                        
                    
                    if total_current_storage + total_pending_storage + file_dict[ 'size' ] > max_storage:
                        
                        raise HydrusExceptions.PermissionException( 'This repository is full up and cannot take any more files!' )
                        
                    
                
            
            overwrite_deleted = can_overrule_files
            
            self._RepositoryAddFile( service_id, account_id, file_dict, overwrite_deleted )
            
        
    
    def _RepositoryProcessClientToServerUpdate( self, service_key, account, client_to_server_update ):
        
        service_id = self._GetServiceId( service_key )
        
        account_key = account.GetAccountKey()
        
        account_id = self._GetAccountId( account_key )
        
        can_petition_files = account.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_PETITION )
        can_overrule_files = account.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_OVERRULE )
        
        can_petition_mappings = account.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_PETITION )
        can_create_mappings = account.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_CREATE )
        can_overrule_mappings = account.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_OVERRULE )
        
        can_petition_tag_parents = account.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_PETITION )
        can_create_tag_parents = account.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_CREATE )
        can_overrule_tag_parents = account.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_OVERRULE )
        
        can_petition_tag_siblings = account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION )
        can_create_tag_siblings = account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_CREATE )
        can_overrule_tag_siblings = account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_OVERRULE )
        
        if can_overrule_files or can_petition_files:
            
            for ( hashes, reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION ):
                
                master_hash_ids = self._GetMasterHashIds( hashes )
                
                service_hash_ids = self._RepositoryGetServiceHashIds( service_id, master_hash_ids )
                
                if can_overrule_files:
                    
                    self._RepositoryDeleteFiles( service_id, account_id, service_hash_ids )
                    
                elif can_petition_files:
                    
                    reason_id = self._GetReasonId( reason )
                    
                    self._RepositoryPetitionFiles( service_id, account_id, service_hash_ids, reason_id )
                    
                
            
        
        if can_overrule_files:
            
            for ( hashes, reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DENY_PETITION ):
                
                master_hash_ids = self._GetMasterHashIds( hashes )
                
                service_hash_ids = self._RepositoryGetServiceHashIds( service_id, master_hash_ids )
                
                self._RepositoryDenyFilePetition( service_id, service_hash_ids )
                
            
        
        #
        
        # later add pend mappings here however that is neat
        
        if can_create_mappings or can_overrule_mappings:
            
            for ( ( tag, hashes ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND ):
                
                master_tag_id = self._GetMasterTagId( tag )
                
                master_hash_ids = self._GetMasterHashIds( hashes )
                
                overwrite_deleted = can_overrule_mappings
                
                self._RepositoryAddMappings( service_id, account_id, master_tag_id, master_hash_ids, overwrite_deleted )
                
            
        
        if can_overrule_mappings or can_petition_mappings:
            
            for ( ( tag, hashes ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION ):
                
                master_tag_id = self._GetMasterTagId( tag )
                
                service_tag_id = self._RepositoryGetServiceTagId( service_id, master_tag_id )
                
                master_hash_ids = self._GetMasterHashIds( hashes )
                
                service_hash_ids = self._RepositoryGetServiceHashIds( service_id, master_hash_ids )
                
                if can_overrule_mappings:
                    
                    self._RepositoryDeleteMappings( service_id, account_id, service_tag_id, service_hash_ids )
                    
                elif can_petition_mappings:
                    
                    reason_id = self._GetReasonId( reason )
                    
                    self._RepositoryPetitionMappings( service_id, account_id, service_tag_id, service_hash_ids, reason_id )
                    
                
            
        
        if can_overrule_mappings:
            
            for ( ( tag, hashes ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DENY_PETITION ):
                
                master_tag_id = self._GetMasterTagId( tag )
                
                service_tag_id = self._RepositoryGetServiceTagId( service_id, master_tag_id )
                
                master_hash_ids = self._GetMasterHashIds( hashes )
                
                service_hash_ids = self._RepositoryGetServiceHashIds( service_id, master_hash_ids )
                
                self._RepositoryDenyMappingPetition( service_id, service_tag_id, service_hash_ids )
                
            
        
        #
        
        if can_create_tag_parents or can_overrule_tag_parents or can_petition_tag_parents:
            
            for ( ( child_tag, parent_tag ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PEND ):
                
                child_master_tag_id = self._GetMasterTagId( child_tag )
                parent_master_tag_id = self._GetMasterTagId( parent_tag )
                
                if can_create_tag_parents or can_overrule_tag_parents:
                    
                    overwrite_deleted = can_overrule_tag_parents
                    
                    self._RepositoryAddTagParent( service_id, account_id, child_master_tag_id, parent_master_tag_id, overwrite_deleted )
                    
                elif can_petition_tag_parents:
                    
                    reason_id = self._GetReasonId( reason )
                    
                    self._RepositoryPendTagParent( service_id, account_id, child_master_tag_id, parent_master_tag_id, reason_id )
                    
                
            
            for ( ( child_tag, parent_tag ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION ):
                
                child_master_tag_id = self._GetMasterTagId( child_tag )
                parent_master_tag_id = self._GetMasterTagId( parent_tag )
                
                child_service_tag_id = self._RepositoryGetServiceTagId( service_id, child_master_tag_id )
                parent_service_tag_id = self._RepositoryGetServiceTagId( service_id, parent_master_tag_id )
                
                if can_overrule_tag_parents:
                    
                    self._RepositoryDeleteTagParent( service_id, account_id, child_service_tag_id, parent_service_tag_id )
                    
                elif can_petition_tag_parents:
                    
                    reason_id = self._GetReasonId( reason )
                    
                    self._RepositoryPetitionTagParent( service_id, account_id, child_service_tag_id, parent_service_tag_id, reason_id )
                    
                
            
        
        if can_overrule_tag_parents:
            
            for ( ( child_tag, parent_tag ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DENY_PEND ):
                
                child_master_tag_id = self._GetMasterTagId( child_tag )
                parent_master_tag_id = self._GetMasterTagId( parent_tag )
                
                self._RepositoryDenyTagParentPend( service_id, child_master_tag_id, parent_master_tag_id )
                
            
            for ( ( child_tag, parent_tag ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DENY_PETITION ):
                
                child_master_tag_id = self._GetMasterTagId( child_tag )
                parent_master_tag_id = self._GetMasterTagId( parent_tag )
                
                child_service_tag_id = self._RepositoryGetServiceTagId( service_id, child_master_tag_id )
                parent_service_tag_id = self._RepositoryGetServiceTagId( service_id, parent_master_tag_id )
                
                self._RepositoryDenyTagParentPetition( service_id, child_service_tag_id, parent_service_tag_id )
                
            
        
        #
        
        if can_create_tag_siblings or can_overrule_tag_siblings or can_petition_tag_siblings:
            
            for ( ( bad_tag, good_tag ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PEND ):
                
                bad_master_tag_id = self._GetMasterTagId( bad_tag )
                good_master_tag_id = self._GetMasterTagId( good_tag )
                
                if can_create_tag_siblings or can_overrule_tag_siblings:
                    
                    overwrite_deleted = can_overrule_tag_siblings
                    
                    self._RepositoryAddTagSibling( service_id, account_id, bad_master_tag_id, good_master_tag_id, overwrite_deleted )
                    
                elif can_petition_tag_siblings:
                    
                    reason_id = self._GetReasonId( reason )
                    
                    self._RepositoryPendTagSibling( service_id, account_id, bad_master_tag_id, good_master_tag_id, reason_id )
                    
                
            
            for ( ( bad_tag, good_tag ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION ):
                
                bad_master_tag_id = self._GetMasterTagId( bad_tag )
                good_master_tag_id = self._GetMasterTagId( good_tag )
                
                bad_service_tag_id = self._RepositoryGetServiceTagId( service_id, bad_master_tag_id )
                good_service_tag_id = self._RepositoryGetServiceTagId( service_id, good_master_tag_id )
                
                if can_overrule_tag_siblings:
                    
                    self._RepositoryDeleteTagSibling( service_id, account_id, bad_service_tag_id, good_service_tag_id )
                    
                elif can_petition_tag_siblings:
                    
                    reason_id = self._GetReasonId( reason )
                    
                    self._RepositoryPetitionTagSibling( service_id, account_id, bad_service_tag_id, good_service_tag_id, reason_id )
                    
                
            
        
        if can_overrule_tag_siblings:
            
            for ( ( bad_tag, good_tag ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DENY_PEND ):
                
                bad_master_tag_id = self._GetMasterTagId( bad_tag )
                good_master_tag_id = self._GetMasterTagId( good_tag )
                
                self._RepositoryDenyTagSiblingPend( service_id, bad_master_tag_id, good_master_tag_id )
                
            
            for ( ( bad_tag, good_tag ), reason ) in client_to_server_update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DENY_PETITION ):
                
                bad_master_tag_id = self._GetMasterTagId( bad_tag )
                good_master_tag_id = self._GetMasterTagId( good_tag )
                
                bad_service_tag_id = self._RepositoryGetServiceTagId( service_id, bad_master_tag_id )
                good_service_tag_id = self._RepositoryGetServiceTagId( service_id, good_master_tag_id )
                
                self._RepositoryDenyTagSiblingPetition( service_id, bad_service_tag_id, good_service_tag_id )
                
            
        
    
    def _RepositoryRewardFilePetitioners( self, service_id, service_hash_ids, multiplier ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        select_statement = 'SELECT account_id, COUNT( * ) FROM ' + petitioned_files_table_name + ' WHERE service_hash_id IN %s GROUP BY account_id;'
        
        scores = [ ( account_id, count * multiplier ) for ( account_id, count ) in self._SelectFromList( select_statement, service_hash_ids ) ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RepositoryRewardMappingPetitioners( self, service_id, service_tag_id, service_hash_ids, multiplier ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        select_statement = 'SELECT account_id, COUNT( * ) FROM ' + petitioned_mappings_table_name + ' WHERE service_tag_id = ' + str( service_tag_id ) + ' AND service_hash_id IN %s GROUP BY account_id;'
        
        scores = [ ( account_id, count * multiplier ) for ( account_id, count ) in self._SelectFromList( select_statement, service_hash_ids ) ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RepositoryRewardTagParentPenders( self, service_id, child_master_tag_id, parent_master_tag_id, multiplier ):
        
        child_service_tag_id = self._RepositoryGetServiceTagId( service_id, child_master_tag_id )
        
        score = self._RepositoryGetCurrentMappingsCount( service_id, child_service_tag_id )
        
        score = max( score, 1 )
        
        weighted_score = score * multiplier
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        account_ids = [ account_id for ( account_id, ) in self._c.execute( 'SELECT account_id FROM ' + pending_tag_parents_table_name + ' WHERE child_master_tag_id = ? AND parent_master_tag_id = ?;', ( child_master_tag_id, parent_master_tag_id ) ) ]
        
        scores = [ ( account_id, weighted_score ) for account_id in account_ids ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RepositoryRewardTagParentPetitioners( self, service_id, child_service_tag_id, parent_service_tag_id, multiplier ):
        
        score = self._RepositoryGetCurrentMappingsCount( service_id, child_service_tag_id )
        
        score = max( score, 1 )
        
        weighted_score = score * multiplier
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        account_ids = [ account_id for ( account_id, ) in self._c.execute( 'SELECT account_id FROM ' + petitioned_tag_parents_table_name + ' WHERE child_service_tag_id = ? AND parent_service_tag_id = ?;', ( child_service_tag_id, parent_service_tag_id ) ) ]
        
        scores = [ ( account_id, weighted_score ) for account_id in account_ids ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RepositoryRewardTagSiblingPenders( self, service_id, bad_master_tag_id, good_master_tag_id, multiplier ):
        
        bad_service_tag_id = self._RepositoryGetServiceTagId( service_id, bad_master_tag_id )
        
        score = self._RepositoryGetCurrentMappingsCount( service_id, bad_service_tag_id )
        
        score = max( score, 1 )
        
        weighted_score = score * multiplier
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        account_ids = [ account_id for ( account_id, ) in self._c.execute( 'SELECT account_id FROM ' + pending_tag_siblings_table_name + ' WHERE bad_master_tag_id = ? AND good_master_tag_id = ?;', ( bad_master_tag_id, good_master_tag_id ) ) ]
        
        scores = [ ( account_id, weighted_score ) for account_id in account_ids ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RepositoryRewardTagSiblingPetitioners( self, service_id, bad_service_tag_id, good_service_tag_id, multiplier ):
        
        score = self._RepositoryGetCurrentMappingsCount( service_id, bad_service_tag_id )
        
        score = max( score, 1 )
        
        weighted_score = score * multiplier
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        account_ids = [ account_id for ( account_id, ) in self._c.execute( 'SELECT account_id FROM ' + petitioned_tag_siblings_table_name + ' WHERE bad_service_tag_id = ? AND good_service_tag_id = ?;', ( bad_service_tag_id, good_service_tag_id ) ) ]
        
        scores = [ ( account_id, weighted_score ) for account_id in account_ids ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RepositoryServiceHashIdExists( self, service_id, master_hash_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        result = self._c.execute( 'SELECT 1 FROM ' + hash_id_map_table_name + ' WHERE master_hash_id = ?;', ( master_hash_id, ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def _RepositoryServiceTagIdExists( self, service_id, master_tag_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
        
        result = self._c.execute( 'SELECT 1 FROM ' + tag_id_map_table_name + ' WHERE master_tag_id = ?;', ( master_tag_id, ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def _RepositorySuperBan( self, service_id, admin_account_id, subject_account_ids ):
        
        ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
        
        select_statement = 'SELECT service_hash_id FROM ' + current_files_table_name + ' WHERE account_id IN %s;'
        
        service_hash_ids = [ service_hash_id for ( service_hash_id, ) in self._SelectFromList( select_statement, subject_account_ids ) ]
        
        if len( service_hash_ids ) > 0:
            
            self._RepositoryDeleteFiles( service_id, admin_account_id, service_hash_ids )
            
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
        
        select_statement = 'SELECT service_tag_id, service_hash_id FROM ' + current_mappings_table_name + ' WHERE account_id IN %s;'
        
        mappings_dict = HydrusData.BuildKeyToListDict( self._SelectFromList( select_statement, subject_account_ids ) )
        
        if len( mappings_dict ) > 0:
            
            for ( service_tag_id, service_hash_ids ) in mappings_dict.items():
                
                self._RepositoryDeleteMappings( service_id, admin_account_id, service_tag_id, service_hash_ids )
                
            
        
        ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
        
        select_statement = 'SELECT child_service_tag_id, parent_service_tag_id FROM ' + current_tag_parents_table_name + ' WHERE account_id IN %s;'
        
        pairs = self._SelectFromListFetchAll( select_statement, subject_account_ids )
        
        if len( pairs ) > 0:
            
            for ( child_service_tag_id, parent_service_tag_id ) in pairs:
                
                self._RepositoryDeleteTagParent( service_id, admin_account_id, child_service_tag_id, parent_service_tag_id )
                
            
        
        ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
        
        select_statement = 'SELECT bad_service_tag_id, good_service_tag_id FROM ' + current_tag_siblings_table_name + ' WHERE account_id IN %s;'
        
        pairs = self._SelectFromListFetchAll( select_statement, subject_account_ids )
        
        if len( pairs ) > 0:
            
            for ( bad_service_tag_id, good_service_tag_id ) in pairs:
                
                self._RepositoryDeleteTagSibling( service_id, admin_account_id, bad_service_tag_id, good_service_tag_id )
                
            
        
    
    def _RewardAccounts( self, service_id, score_type, scores ):
        
        self._c.executemany( 'INSERT OR IGNORE INTO account_scores ( service_id, account_id, score_type, score ) VALUES ( ?, ?, ?, ? );', [ ( service_id, account_id, score_type, 0 ) for ( account_id, score ) in scores ] )
        
        self._c.executemany( 'UPDATE account_scores SET score = score + ? WHERE service_id = ? AND account_id = ? and score_type = ?;', [ ( score, service_id, account_id, score_type ) for ( account_id, score ) in scores ] )
        
    
    def _SaveAccounts( self, service_id, accounts ):
        
        for account in accounts:
            
            ( account_key, account_type, created, expires, dictionary ) = HydrusNetwork.Account.GenerateTupleFromAccount( account )
            
            account_type_key = account_type.GetAccountTypeKey()
            
            account_type_id = self._GetAccountTypeId( service_id, account_type_key )
            
            dictionary_string = dictionary.DumpToString()
            
            self._c.execute( 'UPDATE accounts SET account_type_id = ?, expires = ?, dictionary_string = ? WHERE account_key = ?;', ( account_type_id, expires, dictionary_string, sqlite3.Binary( account_key ) ) )
            
            account.SetClean()
            
        
    
    def _SaveDirtyAccounts( self, service_keys_to_dirty_accounts ):
        
        for ( service_key, dirty_accounts ) in service_keys_to_dirty_accounts.items():
            
            service_id = self._GetServiceId( service_key )
            
            self._SaveAccounts( service_id, dirty_accounts )
            
        
    
    def _SaveDirtyServices( self, dirty_services ):
        
        self._SaveServices( dirty_services )
        
    
    def _SaveServices( self, services ):
        
        for service in services:
            
            ( service_key, service_type, name, port, dictionary ) = service.ToTuple()
            
            dictionary_string = dictionary.DumpToString()
            
            self._c.execute( 'UPDATE services SET dictionary_string = ? WHERE service_key = ?;', ( dictionary_string, sqlite3.Binary( service_key ) ) )
            
            service.SetClean()
            
        
    
    def _UnbanKey( self, service_key, account_key ):
        
        service_id = self._GetServiceId( service_key )
        
        account_id = self._GetAccountId( account_key )
        
        account = self._GetAccount( service_id, account_id )
        
        account.Unban()
        
        self._SaveAccounts( service_id, [ account ] )
        
    
    def _UpdateDB( self, version ):
        
        HydrusData.Print( 'The server is updating to version ' + str( version + 1 ) )
        
        if version == 198:
            
            HydrusData.Print( 'exporting mappings to external db' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mappings ( service_id INTEGER, tag_id INTEGER, hash_id INTEGER, account_id INTEGER, timestamp INTEGER, PRIMARY KEY ( service_id, tag_id, hash_id ) );' )
            
            self._c.execute( 'INSERT INTO external_mappings.mappings SELECT * FROM main.mappings;' )
            
            self._c.execute( 'DROP TABLE main.mappings;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mapping_petitions ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY ( service_id, account_id, tag_id, hash_id, status ) );' )
            
            self._c.execute( 'INSERT INTO external_mappings.mapping_petitions SELECT * FROM main.mapping_petitions;' )
            
            self._c.execute( 'DROP TABLE main.mapping_petitions;' )
            
        
        if version == 200:
            
            HydrusData.Print( 'exporting hashes to external db' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.hashes ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES UNIQUE );' )
            
            self._c.execute( 'INSERT INTO external_master.hashes SELECT * FROM main.hashes;' )
            
            self._c.execute( 'DROP TABLE main.hashes;' )
            
            HydrusData.Print( 'exporting tags to external db' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.tags ( tag_id INTEGER PRIMARY KEY, tag TEXT UNIQUE );' )
            
            self._c.execute( 'INSERT INTO external_master.tags SELECT * FROM main.tags;' )
            
            self._c.execute( 'DROP TABLE main.tags;' )
            
            #
            
            HydrusData.Print( 'compacting mappings tables' )
            
            self._c.execute( 'DROP INDEX mapping_petitions_service_id_account_id_reason_id_tag_id_index;' )
            self._c.execute( 'DROP INDEX mapping_petitions_service_id_tag_id_hash_id_index;' )
            self._c.execute( 'DROP INDEX mapping_petitions_service_id_status_index;' )
            self._c.execute( 'DROP INDEX mapping_petitions_service_id_timestamp_index;' )
            
            self._c.execute( 'DROP INDEX mappings_account_id_index;' )
            self._c.execute( 'DROP INDEX mappings_timestamp_index;' )
            
            self._c.execute( 'ALTER TABLE mapping_petitions RENAME TO mapping_petitions_old;' )
            self._c.execute( 'ALTER TABLE mappings RENAME TO mappings_old;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mapping_petitions ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY ( service_id, account_id, tag_id, hash_id, status ) ) WITHOUT ROWID;' )
            
            self._c.execute( 'INSERT INTO mapping_petitions SELECT * FROM mapping_petitions_old;' )
            
            self._c.execute( 'DROP TABLE mapping_petitions_old;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mappings ( service_id INTEGER, tag_id INTEGER, hash_id INTEGER, account_id INTEGER, timestamp INTEGER, PRIMARY KEY ( service_id, tag_id, hash_id ) ) WITHOUT ROWID;' )
            
            self._c.execute( 'INSERT INTO mappings SELECT * FROM mappings_old;' )
            
            self._c.execute( 'DROP TABLE mappings_old;' )
            
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mapping_petitions_service_id_account_id_reason_id_tag_id_index ON mapping_petitions ( service_id, account_id, reason_id, tag_id );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mapping_petitions_service_id_tag_id_hash_id_index ON mapping_petitions ( service_id, tag_id, hash_id );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mapping_petitions_service_id_status_index ON mapping_petitions ( service_id, status );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mapping_petitions_service_id_timestamp_index ON mapping_petitions ( service_id, timestamp );' )
            
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mappings_account_id_index ON mappings ( account_id );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mappings_timestamp_index ON mappings ( timestamp );' )
            
            #
            
            self._Commit()
            
            self._CloseDBCursor()
            
            try:
                
                for filename in self._db_filenames.values():
                    
                    HydrusData.Print( 'vacuuming ' + filename )
                    
                    db_path = os.path.join( self._db_dir, filename )
                    
                    if HydrusDB.CanVacuum( db_path ):
                        
                        HydrusDB.VacuumDB( db_path )
                        
                    
                
            finally:
                
                self._InitDBCursor()
                
                self._BeginImmediate()
                
            
        
        if version == 202:
            
            self._c.execute( 'DELETE FROM analyze_timestamps;' )
            
        
        if version == 207:
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.petitioned_mappings ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, tag_id, hash_id, account_id ) ) WITHOUT ROWID;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.deleted_mappings ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, PRIMARY KEY ( service_id, tag_id, hash_id ) ) WITHOUT ROWID;' )
            
            #
            
            self._c.execute( 'INSERT INTO petitioned_mappings ( service_id, account_id, tag_id, hash_id, reason_id ) SELECT service_id, account_id, tag_id, hash_id, reason_id FROM mapping_petitions WHERE status = ?;', ( HC.CONTENT_STATUS_PETITIONED, ) )
            self._c.execute( 'INSERT INTO deleted_mappings ( service_id, account_id, tag_id, hash_id, reason_id, timestamp ) SELECT service_id, account_id, tag_id, hash_id, reason_id, timestamp FROM mapping_petitions WHERE status = ?;', ( HC.CONTENT_STATUS_DELETED, ) )
            
            #
            
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.petitioned_mappings_service_id_account_id_reason_id_tag_id_index ON petitioned_mappings ( service_id, account_id, reason_id, tag_id );' )
            
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.deleted_mappings_service_id_account_id_index ON deleted_mappings ( service_id, account_id );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.deleted_mappings_service_id_timestamp_index ON deleted_mappings ( service_id, timestamp );' )
            
            #
            
            self._c.execute( 'DROP TABLE mapping_petitions;' )
            
        
        if version == 208:
            
            old_thumbnail_dir = os.path.join( self._db_dir, 'server_thumbnails' )
            
            for prefix in HydrusData.IterateHexPrefixes():
                
                HydrusData.Print( 'moving thumbnails: ' + prefix )
                
                source_dir = os.path.join( old_thumbnail_dir, prefix )
                dest_dir = os.path.join( self._files_dir, prefix )
                
                source_filenames = os.listdir( source_dir )
                
                for source_filename in source_filenames:
                    
                    source_path = os.path.join( source_dir, source_filename )
                    
                    dest_filename = source_filename + '.thumbnail'
                    
                    dest_path = os.path.join( dest_dir, dest_filename )
                    
                    try:
                        
                        HydrusPaths.MergeFile( source_path, dest_path )
                        
                    except:
                        
                        HydrusData.Print( 'Problem moving thumbnail from ' + source_path + ' to ' + dest_path + '.' )
                        HydrusData.Print( 'Abandoning thumbnail transfer for ' + source_dir + '.' )
                        
                        break
                        
                    
                
            
            try:
                
                HydrusPaths.DeletePath( old_thumbnail_dir )
                
            except:
                
                HydrusData.Print( 'Could not delete old thumbnail directory at ' + old_thumbnail_dir )
                
            
        
        if version == 212:
            
            for prefix in HydrusData.IterateHexPrefixes():
                
                dir = os.path.join( self._files_dir, prefix )
                
                for filename in os.listdir( dir ):
                    
                    if not filename.endswith( '.thumbnail' ):
                        
                        try:
                            
                            file_path = os.path.join( dir, filename )
                            thumbnail_path = file_path + '.thumbnail'
                            
                            if HydrusFileHandling.GetMime( file_path ) in ( HC.IMAGE_PNG, HC.IMAGE_GIF ):
                                
                                if os.path.exists( thumbnail_path ):
                                    
                                    os.remove( thumbnail_path )
                                    
                                
                                thumbnail = HydrusFileHandling.GenerateThumbnail( file_path )
                                
                                with open( thumbnail_path, 'wb' ) as f:
                                    
                                    f.write( thumbnail )
                                    
                                
                            
                        except Exception as e:
                            
                            HydrusData.Print( 'Failed to regen thumbnail for ' + file_path + '! Error was:' )
                            HydrusData.PrintException( e )
                            
                        
                    
                
            
        
        if version == 238:
            
            HydrusData.Print( 'Generating SSL cert and key' )
            
            HydrusEncryption.GenerateOpenSSLCertAndKeyFile( self._ssl_cert_path, self._ssl_key_path )
            
        
        if version == 239:
            
            os.chmod( self._ssl_cert_path, stat.S_IREAD )
            os.chmod( self._ssl_key_path, stat.S_IREAD )
            
        
        if version == 244:
            
            ( foreign_keys_on, ) = self._c.execute( 'PRAGMA foreign_keys;' ).fetchone()
            
            if foreign_keys_on:
                
                self._Commit()
                
                self._c.execute( 'PRAGMA foreign_keys = ?;', ( False, ) )
                
                self._BeginImmediate()
                
            
            HydrusData.Print( 'updating services' )
            
            old_service_info = self._c.execute( 'SELECT * FROM services;' ).fetchall()
            
            self._c.execute( 'DROP TABLE services;' )
            
            self._c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, service_type INTEGER, name TEXT, port INTEGER, dictionary_string TEXT );' )
            
            for ( service_id, service_key, service_type, options ) in old_service_info:
                
                if service_type not in [ HC.SERVER_ADMIN, HC.FILE_REPOSITORY, HC.TAG_REPOSITORY ]:
                    
                    continue
                    
                
                dictionary = HydrusNetwork.GenerateDefaultServiceDictionary( service_type )
                
                if service_type in HC.REPOSITORIES:
                    
                    first_end = min( ( end for ( end, ) in self._c.execute( 'SELECT end FROM update_cache WHERE service_id = ?;', ( service_id, ) ) ) )
                    
                    metadata = HydrusNetwork.Metadata()
                    
                    now = HydrusData.GetNow()
                    
                    update_hashes = []
                    begin = 0
                    end = first_end
                    next_update_due = now
                    
                    metadata.AppendUpdate( update_hashes, begin, end, next_update_due )
                    
                    dictionary[ 'metadata' ] = metadata
                    
                
                port = options[ 'port' ]
                
                name = HC.service_string_lookup[ service_type ] + '@' + str( port )
                
                dictionary_string = dictionary.DumpToString()
                
                self._c.execute( 'INSERT INTO services ( service_id, service_key, service_type, name, port, dictionary_string ) VALUES ( ?, ?, ?, ?, ?, ? );', ( service_id, sqlite3.Binary( service_key ), service_type, name, port, dictionary_string ) )
                
            
            #
            
            HydrusData.Print( 'updating account types' )
            
            old_account_type_info = self._c.execute( 'SELECT * FROM account_types;' ).fetchall()
            
            self._c.execute( 'DROP TABLE account_types;' )
            
            self._c.execute( 'CREATE TABLE account_types ( account_type_id INTEGER PRIMARY KEY, service_id INTEGER, account_type_key BLOB_BYTES, title TEXT, dictionary_string TEXT );' )
            
            for ( account_type_id, service_id, title, account_type_yaml ) in old_account_type_info:
                
                result = self._c.execute( 'SELECT service_type FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                if result is None:
                    
                    continue
                    
                
                ( service_type, ) = result
                
                old_permissions = account_type_yaml._permissions
                
                permissions = {}
                
                if service_type == HC.FILE_REPOSITORY:
                    
                    if HC.RESOLVE_PETITIONS in old_permissions:
                        
                        permissions[ HC.CONTENT_TYPE_FILES ] = HC.PERMISSION_ACTION_OVERRULE
                        
                    elif HC.POST_DATA in old_permissions:
                        
                        permissions[ HC.CONTENT_TYPE_FILES ] = HC.PERMISSION_ACTION_CREATE
                        
                    elif HC.POST_PETITIONS in old_permissions:
                        
                        permissions[ HC.CONTENT_TYPE_FILES ] = HC.PERMISSION_ACTION_PETITION
                        
                    
                elif service_type == HC.TAG_REPOSITORY:
                    
                    mapping_permissions = []
                    tag_pair_permissions = []
                    
                    if HC.RESOLVE_PETITIONS in old_permissions:
                        
                        permissions[ HC.CONTENT_TYPE_MAPPINGS ] = HC.PERMISSION_ACTION_OVERRULE
                        permissions[ HC.CONTENT_TYPE_TAG_PARENTS ] = HC.PERMISSION_ACTION_OVERRULE
                        permissions[ HC.CONTENT_TYPE_TAG_SIBLINGS ] = HC.PERMISSION_ACTION_OVERRULE
                        
                    elif HC.POST_DATA in old_permissions:
                        
                        permissions[ HC.CONTENT_TYPE_MAPPINGS ] = HC.PERMISSION_ACTION_CREATE
                        permissions[ HC.CONTENT_TYPE_TAG_PARENTS ] = HC.PERMISSION_ACTION_PETITION
                        permissions[ HC.CONTENT_TYPE_TAG_SIBLINGS ] = HC.PERMISSION_ACTION_PETITION
                        
                    
                elif service_type == HC.SERVER_ADMIN:
                    
                    if HC.EDIT_SERVICES in old_permissions:
                        
                        permissions[ HC.CONTENT_TYPE_SERVICES ] = HC.PERMISSION_ACTION_OVERRULE
                        
                    
                
                if HC.MANAGE_USERS in old_permissions:
                    
                    permissions[ HC.CONTENT_TYPE_ACCOUNTS ] = HC.PERMISSION_ACTION_OVERRULE
                    permissions[ HC.CONTENT_TYPE_ACCOUNT_TYPES ] = HC.PERMISSION_ACTION_OVERRULE
                    
                
                bandwidth_rules = HydrusNetworking.BandwidthRules()
                
                ( max_monthly_bytes, max_monthly_requests ) = account_type_yaml._max_monthly_data
                
                if max_monthly_bytes is not None:
                    
                    bandwidth_rules.AddRule( HC.BANDWIDTH_TYPE_DATA, None, max_monthly_bytes )
                    
                
                if max_monthly_requests is not None:
                    
                    bandwidth_rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, None, max_monthly_requests )
                    
                
                account_type = HydrusNetwork.AccountType.GenerateNewAccountTypeFromParameters( title, permissions, bandwidth_rules )
                
                ( account_type_key, title, dictionary ) = account_type.ToDictionaryTuple()
                
                dictionary_string = dictionary.DumpToString()
                
                self._c.execute( 'INSERT INTO account_types ( account_type_id, service_id, account_type_key, title, dictionary_string ) VALUES ( ?, ?, ?, ?, ? );', ( account_type_id, service_id, sqlite3.Binary( account_type_key ), title, dictionary_string ) )
                
            
            
            HydrusData.Print( 'updating accounts' )
            
            old_accounts = self._c.execute( 'SELECT * FROM accounts;' ).fetchall()
            
            self._c.execute( 'DROP TABLE accounts;' )
            
            self._c.execute( 'CREATE TABLE accounts ( account_id INTEGER PRIMARY KEY, service_id INTEGER, account_key BLOB_BYTES, hashed_access_key BLOB_BYTES, account_type_id INTEGER, created INTEGER, expires INTEGER, dictionary_string TEXT );' )
            self._c.execute( 'CREATE UNIQUE INDEX accounts_account_key_index ON accounts ( account_key );' )
            self._c.execute( 'CREATE UNIQUE INDEX accounts_hashed_access_key_index ON accounts ( hashed_access_key );' )
            
            for ( account_id, service_id, account_key, hashed_access_key, account_type_id, created, expires, used_bytes, used_requests ) in old_accounts:
                
                result = self._c.execute( 'SELECT 1 FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                if result is None:
                    
                    continue
                    
                
                dictionary = HydrusSerialisable.SerialisableDictionary()
                
                result = self._c.execute( 'SELECT reason, created, expires FROM reasons NATURAL JOIN bans WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
                
                if result is None:
                    
                    dictionary[ 'banned_info' ] = None
                    
                else:
                    
                    ( reason, created, expires ) = result
                    
                    dictionary[ 'banned_info' ] = ( reason, created, expires )
                    
                
                dictionary[ 'bandwidth_tracker' ] = HydrusNetworking.BandwidthTracker()
                
                dictionary_string = dictionary.DumpToString()
                
                self._c.execute( 'INSERT INTO accounts ( account_id, service_id, account_key, hashed_access_key, account_type_id, created, expires, dictionary_string ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ? );', ( account_id, service_id, sqlite3.Binary( account_key ), sqlite3.Binary( hashed_access_key ), account_type_id, created, expires, dictionary_string ) )
                
            
            HydrusData.Print( 'removing misc old tables' )
            
            self._c.execute( 'DROP TABLE news;' )
            self._c.execute( 'DROP TABLE IF EXISTS contacts;' )
            self._c.execute( 'DROP TABLE IF EXISTS messages;' )
            self._c.execute( 'DROP TABLE IF EXISTS message_statuses;' )
            self._c.execute( 'DROP TABLE IF EXISTS messaging_sessions;' )
            self._c.execute( 'DROP TABLE IF EXISTS ratings;' )
            self._c.execute( 'DROP TABLE bans;' )
            
            HydrusData.Print( 'removing some foreign keys' )
            
            #
            
            self._c.execute( 'ALTER TABLE account_scores RENAME TO old_table;' )
            
            self._c.execute( 'CREATE TABLE account_scores ( service_id INTEGER, account_id INTEGER, score_type INTEGER, score INTEGER, PRIMARY KEY ( service_id, account_id, score_type ) );' )
            
            self._c.execute( 'INSERT INTO account_scores SELECT * FROM old_table;' )
            
            self._c.execute( 'DROP TABLE old_table;' )
            
            #
            
            self._c.execute( 'ALTER TABLE registration_keys RENAME TO old_table;' )
            
            self._c.execute( 'DROP INDEX IF EXISTS registration_keys_access_key_index;' )
            
            self._c.execute( 'CREATE TABLE registration_keys ( registration_key BLOB_BYTES PRIMARY KEY, service_id INTEGER, account_type_id INTEGER, account_key BLOB_BYTES, access_key BLOB_BYTES UNIQUE, expires INTEGER );' )
            
            self._c.execute( 'INSERT INTO registration_keys SELECT * FROM old_table;' )
            
            self._c.execute( 'DROP TABLE old_table;' )
            
            #
            
            self._c.execute( 'ALTER TABLE sessions RENAME TO old_table;' )
            
            self._c.execute( 'CREATE TABLE sessions ( session_key BLOB_BYTES, service_id INTEGER, account_id INTEGER, expires INTEGER );' )
            
            self._c.execute( 'INSERT INTO sessions SELECT * FROM old_table;' )
            
            self._c.execute( 'DROP TABLE old_table;' )
            
            #
            
            HydrusData.Print( 'updating hashes table' )
            
            self._c.execute( 'ALTER TABLE hashes RENAME TO old_table;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.hashes ( master_hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES UNIQUE );' )
            
            self._c.execute( 'INSERT INTO hashes SELECT * FROM old_table;' )
            
            self._c.execute( 'DROP TABLE old_table;' )
            
            #
            
            HydrusData.Print( 'updating tags table' )
            
            self._c.execute( 'ALTER TABLE tags RENAME TO old_table;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.tags ( master_tag_id INTEGER PRIMARY KEY, tag TEXT UNIQUE );' )
            
            self._c.execute( 'INSERT INTO tags SELECT * FROM old_table;' )
            
            self._c.execute( 'DROP TABLE old_table;' )
            
            #
            
            HydrusData.Print( 'cleaning invalid tags' )
            
            unclean_tags = []
            invalid_tags = []
            
            for ( master_tag_id, tag ) in self._c.execute( 'SELECT master_tag_id, tag FROM tags;' ):
                
                clean_tag = HydrusTags.CleanTag( tag )
                
                try:
                    
                    HydrusTags.CheckTagNotEmpty( clean_tag )
                    
                except HydrusExceptions.SizeException:
                    
                    invalid_tags.append( ( master_tag_id, tag ) )
                    
                    continue
                    
                
                if clean_tag != tag:
                    
                    unclean_tags.append( ( master_tag_id, tag, clean_tag ) )
                    
                
            
            for ( master_tag_id, tag, clean_tag ) in unclean_tags:
                
                result = self._c.execute( 'SELECT master_tag_id FROM tags WHERE tag = ?;', ( clean_tag, ) ).fetchone()
                
                if result is None:
                    
                    self._c.execute( 'UPDATE tags SET tag = ? WHERE master_tag_id = ?;', ( clean_tag, master_tag_id ) )
                    
                else:
                    
                    invalid_tags.append( ( master_tag_id, tag ) )
                    
                
            
            for ( master_tag_id, tag ) in invalid_tags:
                
                replacee = 'hydrus invalid tag:"' + tag + '"'
                
                self._c.execute( 'UPDATE tags SET tag = ? WHERE master_tag_id = ?;', ( replacee, master_tag_id ) )
                
            
            #
            
            HydrusData.Print( 'updating files_info table' )
            
            self._c.execute( 'ALTER TABLE files_info RENAME TO old_table;' )
            
            self._c.execute( 'CREATE TABLE files_info ( master_hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, num_words INTEGER );' )
            
            self._c.execute( 'INSERT INTO files_info SELECT * FROM old_table;' )
            
            self._c.execute( 'DROP TABLE old_table;' )
            
            #
            
            repository_service_ids = [ service_id for ( service_id, ) in self._c.execute( 'SELECT service_id FROM services WHERE service_type IN ( ?, ? );', ( HC.FILE_REPOSITORY, HC.TAG_REPOSITORY ) ) ]
            
            for service_id in repository_service_ids:
                
                HydrusData.Print( '---updating service ' + str( service_id ) + '---' )
                
                ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterMapTableNames( service_id )
                
                self._c.execute( 'CREATE TABLE ' + hash_id_map_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, master_hash_id INTEGER UNIQUE, hash_id_timestamp INTEGER );' )
                
                self._c.execute( 'CREATE TABLE ' + tag_id_map_table_name + ' ( service_tag_id INTEGER PRIMARY KEY, master_tag_id INTEGER UNIQUE, tag_id_timestamp INTEGER );' )
                
                HydrusData.Print( 'compiling minimum timestamps' )
                
                self._c.execute( 'CREATE TABLE mem.hash_timestamps ( hash_id INTEGER, timestamp INTEGER );' )
                self._c.execute( 'CREATE TABLE mem.tag_timestamps ( tag_id INTEGER, timestamp INTEGER );' )
                
                self._c.execute ( 'INSERT INTO hash_timestamps SELECT hash_id, MIN( timestamp ) FROM file_map WHERE service_id = ? GROUP BY hash_id;', ( service_id, ) )
                self._c.execute ( 'INSERT INTO hash_timestamps SELECT hash_id, MIN( timestamp ) FROM file_petitions WHERE service_id = ? GROUP BY hash_id;', ( service_id, ) )
                
                self._c.execute ( 'INSERT INTO hash_timestamps SELECT hash_id, MIN( timestamp ) FROM mappings WHERE service_id = ? GROUP BY hash_id;', ( service_id, ) )
                self._c.execute ( 'INSERT INTO tag_timestamps SELECT tag_id, MIN( timestamp ) FROM mappings WHERE service_id = ? GROUP BY tag_id;', ( service_id, ) )
                self._c.execute ( 'INSERT INTO hash_timestamps SELECT hash_id, MIN( timestamp ) FROM deleted_mappings WHERE service_id = ? GROUP BY hash_id;', ( service_id, ) )
                self._c.execute ( 'INSERT INTO tag_timestamps SELECT tag_id, MIN( timestamp ) FROM deleted_mappings WHERE service_id = ? GROUP BY tag_id;', ( service_id, ) )
                
                self._c.execute ( 'INSERT INTO tag_timestamps SELECT old_tag_id, MIN( timestamp ) FROM tag_parents WHERE service_id = ? GROUP BY old_tag_id;', ( service_id, ) )
                self._c.execute ( 'INSERT INTO tag_timestamps SELECT new_tag_id, MIN( timestamp ) FROM tag_parents WHERE service_id = ? GROUP BY new_tag_id;', ( service_id, ) )
                
                self._c.execute ( 'INSERT INTO tag_timestamps SELECT old_tag_id, MIN( timestamp ) FROM tag_siblings WHERE service_id = ? GROUP BY old_tag_id;', ( service_id, ) )
                self._c.execute ( 'INSERT INTO tag_timestamps SELECT new_tag_id, MIN( timestamp ) FROM tag_siblings WHERE service_id = ? GROUP BY new_tag_id;', ( service_id, ) )
                
                HydrusData.Print( 'saving timestamps and creating new service-specific ids' )
                
                self._c.execute( 'INSERT INTO ' + hash_id_map_table_name + ' ( master_hash_id, hash_id_timestamp ) SELECT hash_id, MIN( timestamp ) FROM hash_timestamps GROUP BY hash_id;' )
                self._c.execute( 'INSERT INTO ' + tag_id_map_table_name + ' ( master_tag_id, tag_id_timestamp ) SELECT tag_id, MIN( timestamp ) FROM tag_timestamps GROUP BY tag_id;' )
                
                self._c.execute( 'DROP TABLE hash_timestamps;' )
                self._c.execute( 'DROP TABLE tag_timestamps;' )
                
                HydrusData.Print( 'creating service master indices' )
                
                self._CreateIndex( hash_id_map_table_name, [ 'hash_id_timestamp' ] )
                self._CreateIndex( tag_id_map_table_name, [ 'tag_id_timestamp' ] )
                
                #
                
                HydrusData.Print( 'compacting current files' )
                
                ( current_files_table_name, deleted_files_table_name, pending_files_table_name, petitioned_files_table_name, ip_addresses_table_name ) = GenerateRepositoryFilesTableNames( service_id )
                
                self._c.execute( 'CREATE TABLE ' + current_files_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, account_id INTEGER, file_timestamp INTEGER );' )
                
                self._c.execute( 'INSERT INTO ' + current_files_table_name + ' SELECT service_hash_id, account_id, file_map.timestamp FROM file_map, ' + hash_id_map_table_name + ' ON ( file_map.hash_id = ' + hash_id_map_table_name + '.master_hash_id ) WHERE service_id = ?;', ( service_id, ) )
                
                self._CreateIndex( current_files_table_name, [ 'account_id' ] )
                self._CreateIndex( current_files_table_name, [ 'file_timestamp' ] )
                
                HydrusData.Print( 'compacting non-current files' )
                
                self._c.execute( 'CREATE TABLE ' + deleted_files_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, account_id INTEGER, file_timestamp INTEGER );' )
                
                self._c.execute( 'INSERT INTO ' + deleted_files_table_name + ' SELECT service_hash_id, account_id, file_petitions.timestamp FROM file_petitions, ' + hash_id_map_table_name + ' ON ( file_petitions.hash_id = ' + hash_id_map_table_name + '.master_hash_id ) WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_DELETED ) )
                
                self._CreateIndex( deleted_files_table_name, [ 'account_id' ] )
                self._CreateIndex( deleted_files_table_name, [ 'file_timestamp' ] )
                
                self._c.execute( 'CREATE TABLE ' + pending_files_table_name + ' ( master_hash_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( master_hash_id, account_id ) ) WITHOUT ROWID;' )
                self._CreateIndex( pending_files_table_name, [ 'account_id', 'reason_id' ] )
                
                self._c.execute( 'CREATE TABLE ' + petitioned_files_table_name + ' ( service_hash_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( service_hash_id, account_id ) ) WITHOUT ROWID;' )
                
                self._c.execute( 'INSERT INTO ' + petitioned_files_table_name + ' SELECT service_hash_id, account_id, reason_id FROM file_petitions, ' + hash_id_map_table_name + ' ON ( file_petitions.hash_id = ' + hash_id_map_table_name + '.master_hash_id ) WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) )
                
                self._CreateIndex( petitioned_files_table_name, [ 'account_id', 'reason_id' ] )
                
                self._c.execute( 'CREATE TABLE ' + ip_addresses_table_name + ' ( master_hash_id INTEGER, ip TEXT, ip_timestamp INTEGER );' )
                
                self._c.execute( 'INSERT INTO ' + ip_addresses_table_name + ' SELECT hash_id, ip, timestamp FROM ip_addresses WHERE service_id = ?;', ( service_id, ) )
                
                #
                
                HydrusData.Print( 'compacting current mappings' )
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateRepositoryMappingsTableNames( service_id )
                
                self._c.execute( 'CREATE TABLE ' + current_mappings_table_name + ' ( service_tag_id INTEGER, service_hash_id INTEGER, account_id INTEGER, mapping_timestamp INTEGER, PRIMARY KEY ( service_tag_id, service_hash_id ) ) WITHOUT ROWID;' )
                
                table_join = hash_id_map_table_name + ', ' + tag_id_map_table_name + ', mappings ON ( ' + tag_id_map_table_name + '.master_tag_id = mappings.tag_id AND ' + hash_id_map_table_name + '.master_hash_id = mappings.hash_id )'
                
                self._c.execute( 'INSERT INTO ' + current_mappings_table_name + ' SELECT service_tag_id, service_hash_id, account_id, mappings.timestamp FROM ' + table_join + ' WHERE service_id = ?;', ( service_id, ) )
                
                HydrusData.Print( 'creating current mapping indices' )
                
                self._CreateIndex( current_mappings_table_name, [ 'account_id' ] )
                self._CreateIndex( current_mappings_table_name, [ 'mapping_timestamp' ] )
                
                HydrusData.Print( 'compacting non-current mappings' )
                
                self._c.execute( 'CREATE TABLE ' + deleted_mappings_table_name + ' ( service_tag_id INTEGER, service_hash_id INTEGER, account_id INTEGER, mapping_timestamp INTEGER, PRIMARY KEY ( service_tag_id, service_hash_id ) ) WITHOUT ROWID;' )
                
                table_join = hash_id_map_table_name + ', ' + tag_id_map_table_name + ', deleted_mappings ON ( ' + tag_id_map_table_name + '.master_tag_id = deleted_mappings.tag_id AND ' + hash_id_map_table_name + '.master_hash_id = deleted_mappings.hash_id )'
                
                self._c.execute( 'INSERT INTO ' + deleted_mappings_table_name + ' SELECT service_tag_id, service_hash_id, account_id, deleted_mappings.timestamp FROM ' + table_join + ' WHERE service_id = ?;', ( service_id, ) )
                
                self._CreateIndex( deleted_mappings_table_name, [ 'account_id' ] )
                self._CreateIndex( deleted_mappings_table_name, [ 'mapping_timestamp' ] )
                
                self._c.execute( 'CREATE TABLE ' + pending_mappings_table_name + ' ( master_tag_id INTEGER, master_hash_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( master_tag_id, master_hash_id, account_id ) ) WITHOUT ROWID;' )
                self._CreateIndex( pending_mappings_table_name, [ 'account_id', 'reason_id' ] )
                
                self._c.execute( 'CREATE TABLE ' + petitioned_mappings_table_name + ' ( service_tag_id INTEGER, service_hash_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( service_tag_id, service_hash_id, account_id ) ) WITHOUT ROWID;' )
                
                table_join = hash_id_map_table_name + ', ' + tag_id_map_table_name + ', petitioned_mappings ON ( ' + tag_id_map_table_name + '.master_tag_id = petitioned_mappings.tag_id AND ' + hash_id_map_table_name + '.master_hash_id = petitioned_mappings.hash_id )'
                
                self._c.execute( 'INSERT INTO ' + petitioned_mappings_table_name + ' SELECT service_tag_id, service_hash_id, account_id, reason_id FROM ' + table_join + ' WHERE service_id = ?;', ( service_id, ) )
                
                self._CreateIndex( petitioned_mappings_table_name, [ 'account_id', 'reason_id' ] )
                
                #
                
                def ConvertTagPairs( rows ):
                    
                    results = []
                    
                    for ( master_tag_id_1, master_tag_id_2, gumpf_1, gumpf_2 ) in rows:
                        
                        ( service_tag_id_1, ) = self._c.execute( 'SELECT service_tag_id FROM ' + tag_id_map_table_name + ' WHERE master_tag_id = ?;', ( master_tag_id_1, ) ).fetchone()
                        ( service_tag_id_2, ) = self._c.execute( 'SELECT service_tag_id FROM ' + tag_id_map_table_name + ' WHERE master_tag_id = ?;', ( master_tag_id_2, ) ).fetchone()
                        
                        results.append( ( service_tag_id_1, service_tag_id_2, gumpf_1, gumpf_2 ) )
                        
                    
                    return results
                    
                
                #
                
                HydrusData.Print( 'compacting tag parents' )
                
                ( current_tag_parents_table_name, deleted_tag_parents_table_name, pending_tag_parents_table_name, petitioned_tag_parents_table_name ) = GenerateRepositoryTagParentsTableNames( service_id )
                
                self._c.execute( 'CREATE TABLE ' + current_tag_parents_table_name + ' ( child_service_tag_id INTEGER, parent_service_tag_id INTEGER, account_id INTEGER, parent_timestamp INTEGER, PRIMARY KEY ( child_service_tag_id, parent_service_tag_id ) ) WITHOUT ROWID;' )
                
                old_data = self._c.execute( 'SELECT old_tag_id, new_tag_id, account_id, timestamp FROM tag_parents WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_CURRENT ) ).fetchall()
                
                inserts = ConvertTagPairs( old_data )
                
                self._c.executemany( 'INSERT INTO ' + current_tag_parents_table_name + ' VALUES ( ?, ?, ?, ? );', inserts )
                
                self._CreateIndex( current_tag_parents_table_name, [ 'account_id' ] )
                self._CreateIndex( current_tag_parents_table_name, [ 'parent_timestamp' ] )
                
                self._c.execute( 'CREATE TABLE ' + deleted_tag_parents_table_name + ' ( child_service_tag_id INTEGER, parent_service_tag_id INTEGER, account_id INTEGER, parent_timestamp INTEGER, PRIMARY KEY ( child_service_tag_id, parent_service_tag_id ) ) WITHOUT ROWID;' )
                
                old_data = self._c.execute( 'SELECT old_tag_id, new_tag_id, account_id, timestamp FROM tag_parents WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_DELETED ) ).fetchall()
                
                inserts = ConvertTagPairs( old_data )
                
                self._c.executemany( 'INSERT INTO ' + deleted_tag_parents_table_name + ' VALUES ( ?, ?, ?, ? );', inserts )
                
                self._CreateIndex( deleted_tag_parents_table_name, [ 'account_id' ] )
                self._CreateIndex( deleted_tag_parents_table_name, [ 'parent_timestamp' ] )
                
                self._c.execute( 'CREATE TABLE ' + pending_tag_parents_table_name + ' ( child_master_tag_id INTEGER, parent_master_tag_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( child_master_tag_id, parent_master_tag_id, account_id ) ) WITHOUT ROWID;' )
                
                self._c.execute( 'INSERT INTO ' + pending_tag_parents_table_name + ' SELECT old_tag_id, new_tag_id, account_id, reason_id FROM tag_parents WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PENDING ) )
                
                self._CreateIndex( pending_tag_parents_table_name, [ 'account_id', 'reason_id' ] )
                
                self._c.execute( 'CREATE TABLE ' + petitioned_tag_parents_table_name + ' ( child_service_tag_id INTEGER, parent_service_tag_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( child_service_tag_id, parent_service_tag_id, account_id ) ) WITHOUT ROWID;' )
                
                old_data = self._c.execute( 'SELECT old_tag_id, new_tag_id, account_id, reason_id FROM tag_parents WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) ).fetchall()
                
                inserts = ConvertTagPairs( old_data )
                
                self._c.executemany( 'INSERT INTO ' + petitioned_tag_parents_table_name + ' VALUES ( ?, ?, ?, ? );', inserts )
                
                self._CreateIndex( petitioned_tag_parents_table_name, [ 'account_id', 'reason_id' ] )
                
                #
                
                HydrusData.Print( 'compacting tag siblings' )
                
                ( current_tag_siblings_table_name, deleted_tag_siblings_table_name, pending_tag_siblings_table_name, petitioned_tag_siblings_table_name ) = GenerateRepositoryTagSiblingsTableNames( service_id )
                
                self._c.execute( 'CREATE TABLE ' + current_tag_siblings_table_name + ' ( bad_service_tag_id INTEGER PRIMARY KEY, good_service_tag_id INTEGER, account_id INTEGER, sibling_timestamp INTEGER );' )
                
                old_data = self._c.execute( 'SELECT old_tag_id, new_tag_id, account_id, timestamp FROM tag_siblings WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_CURRENT ) ).fetchall()
                
                inserts = ConvertTagPairs( old_data )
                
                self._c.executemany( 'INSERT INTO ' + current_tag_siblings_table_name + ' VALUES ( ?, ?, ?, ? );', inserts )
                
                self._CreateIndex( current_tag_siblings_table_name, [ 'account_id' ] )
                self._CreateIndex( current_tag_siblings_table_name, [ 'sibling_timestamp' ] )
                
                self._c.execute( 'CREATE TABLE ' + deleted_tag_siblings_table_name + ' ( bad_service_tag_id INTEGER PRIMARY KEY, good_service_tag_id INTEGER, account_id INTEGER, sibling_timestamp INTEGER );' )
                
                old_data = self._c.execute( 'SELECT old_tag_id, new_tag_id, account_id, timestamp FROM tag_siblings WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_DELETED ) ).fetchall()
                
                inserts = ConvertTagPairs( old_data )
                
                self._c.executemany( 'INSERT INTO ' + deleted_tag_siblings_table_name + ' VALUES ( ?, ?, ?, ? );', inserts )
                
                self._CreateIndex( deleted_tag_siblings_table_name, [ 'account_id' ] )
                self._CreateIndex( deleted_tag_siblings_table_name, [ 'sibling_timestamp' ] )
                
                self._c.execute( 'CREATE TABLE ' + pending_tag_siblings_table_name + ' ( bad_master_tag_id INTEGER, good_master_tag_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( bad_master_tag_id, account_id ) ) WITHOUT ROWID;' )
                
                self._c.execute( 'INSERT INTO ' + pending_tag_siblings_table_name + ' SELECT old_tag_id, new_tag_id, account_id, reason_id FROM tag_siblings WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PENDING ) )
                
                self._CreateIndex( pending_tag_siblings_table_name, [ 'account_id', 'reason_id' ] )
                
                self._c.execute( 'CREATE TABLE ' + petitioned_tag_siblings_table_name + ' ( bad_service_tag_id INTEGER, good_service_tag_id INTEGER, account_id INTEGER, reason_id INTEGER, PRIMARY KEY ( bad_service_tag_id, account_id ) ) WITHOUT ROWID;' )
                
                old_data = self._c.execute( 'SELECT old_tag_id, new_tag_id, account_id, reason_id FROM tag_siblings WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) ).fetchall()
                
                inserts = ConvertTagPairs( old_data )
                
                self._c.executemany( 'INSERT INTO ' + petitioned_tag_siblings_table_name + ' VALUES ( ?, ?, ?, ? );', inserts )
                
                self._CreateIndex( petitioned_tag_siblings_table_name, [ 'account_id', 'reason_id' ] )
                
                #
                
                ( update_table_name ) = GenerateRepositoryUpdateTableName( service_id )
                
                self._c.execute( 'CREATE TABLE ' + update_table_name + ' ( master_hash_id INTEGER PRIMARY KEY );' )
                
            
            self._c.execute( 'DROP TABLE file_map;' )
            self._c.execute( 'DROP TABLE file_petitions;' )
            
            self._c.execute( 'DROP TABLE mappings;' )
            self._c.execute( 'DROP TABLE petitioned_mappings;' )
            self._c.execute( 'DROP TABLE deleted_mappings;' )
            
            self._c.execute( 'DROP TABLE tag_parents;' )
            
            self._c.execute( 'DROP TABLE tag_siblings;' )
            
            self._c.execute( 'DROP TABLE ip_addresses;' )
            
            self._c.execute( 'DROP TABLE update_cache;' )
            
            
            HydrusData.Print( 'committing to disk' )
            
            self._Commit()
            
            self._CloseDBCursor()
            
            try:
                
                for filename in [ 'server.mappings.db', 'server.master.db', 'server.db' ]:
                    
                    HydrusData.Print( 'vacuuming ' + filename )
                    
                    db_path = os.path.join( self._db_dir, filename )
                    
                    try:
                        
                        if HydrusDB.CanVacuum( db_path ):
                            
                            HydrusDB.VacuumDB( db_path )
                            
                        
                    except Exception as e:
                        
                        HydrusData.Print( 'Vacuum failed!' )
                        HydrusData.PrintException( e )
                        
                    
                
            finally:
                
                self._InitDBCursor()
                
                self._BeginImmediate()
                
            
            
            for schema in [ 'main', 'external_master', 'external_mappings' ]:
                
                HydrusData.Print( 'analyzing ' + schema )
                
                try:
                    
                    self._c.execute( 'ANALYZE ' + schema + ';' )
                    
                except:
                    
                    HydrusData.Print( 'While updating to v245, ANALYZE ' + schema + ' failed!' )
                    
                
            
            HydrusData.Print( 'deleting old update directory' )
            
            updates_dir = os.path.join( self._db_dir, 'server_updates' )
            
            HydrusPaths.DeletePath( updates_dir )
            
        
        
        HydrusData.Print( 'The server has updated to version ' + str( version + 1 ) )
        
        self._c.execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
    
    def _VerifyAccessKey( self, service_key, access_key ):
        
        service_id = self._GetServiceId( service_key )
        
        result = self._c.execute( 'SELECT 1 FROM accounts WHERE service_id = ? AND hashed_access_key = ?;', ( service_id, sqlite3.Binary( hashlib.sha256( access_key ).digest() ) ) ).fetchone()
        
        if result is None:
            
            result = self._c.execute( 'SELECT 1 FROM registration_keys WHERE service_id = ? AND access_key = ?;', ( service_id, sqlite3.Binary( access_key ) ) ).fetchone()
            
            if result is None:
                
                return False
                
            
        
        return True
        
    
    def _Write( self, action, *args, **kwargs ):
        
        if action == 'accounts': result = self._ModifyAccounts( *args, **kwargs )
        elif action == 'account_types': result = self._ModifyAccountTypes( *args, **kwargs )
        elif action == 'analyze': result = self._Analyze( *args, **kwargs )
        elif action == 'backup': result = self._Backup( *args, **kwargs )
        elif action == 'create_update': result = self._RepositoryCreateUpdate( *args, **kwargs )
        elif action == 'delete_orphans': result = self._DeleteOrphans( *args, **kwargs )
        elif action == 'dirty_accounts': result = self._SaveDirtyAccounts( *args, **kwargs )
        elif action == 'dirty_services': result = self._SaveDirtyServices( *args, **kwargs )
        elif action == 'file': result = self._RepositoryProcessAddFile( *args, **kwargs )
        elif action == 'services': result = self._ModifyServices( *args, **kwargs )
        elif action == 'session': result = self._AddSession( *args, **kwargs )
        elif action == 'update': result = self._RepositoryProcessClientToServerUpdate( *args, **kwargs )
        else: raise Exception( 'db received an unknown write command: ' + action )
        
        return result
        
    
    def GetFilesDir( self ):
        
        return self._files_dir
        
    
    def GetSSLPaths( self ):
        
        return ( self._ssl_cert_path, self._ssl_key_path )
        
    
