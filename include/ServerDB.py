import collections
import hashlib
import httplib
import HydrusConstants as HC
import HydrusDB
import HydrusEncryption
import HydrusExceptions
import HydrusFileHandling
import HydrusNATPunch
import HydrusPaths
import HydrusSerialisable
import itertools
import json
import lz4
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
import yaml
import HydrusData
import HydrusTags
import HydrusGlobals
'''
class MessageDB( object ):
    
    def _AddMessage( self, contact_key, message ):
        
        try: ( service_id, account_id ) = self._c.execute( 'SELECT service_id, account_id FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( contact_key ), ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'Did not find that contact key for the message depot!' )
        
        message_key = HydrusData.GenerateKey()
        
        self._c.execute( 'INSERT OR IGNORE INTO messages ( message_key, service_id, account_id, timestamp ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( message_key ), service_id, account_id, HydrusData.GetNow() ) )
        
        dest_path = ServerFiles.GetExpectedPath( 'message', message_key )
        
        with open( dest_path, 'wb' ) as f: f.write( message )
        
    
    def _AddStatuses( self, contact_key, statuses ):
        
        try: ( service_id, account_id ) = self._c.execute( 'SELECT service_id, account_id FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( contact_key ), ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'Did not find that contact key for the message depot!' )
        
        now = HydrusData.GetNow()
        
        self._c.executemany( 'INSERT OR REPLACE INTO message_statuses ( status_key, service_id, account_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ? );', [ ( sqlite3.Binary( status_key ), service_id, account_id, sqlite3.Binary( status ), now ) for ( status_key, status ) in statuses ] )
        
    
    def _CreateContact( self, service_id, account_id, public_key ):
        
        result = self._c.execute( 'SELECT public_key FROM contacts WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
        
        if result is not None:
            
            ( existing_public_key, ) = result
            
            if existing_public_key != public_key: raise HydrusExceptions.ForbiddenException( 'This account already has a public key!' )
            else: return
            
        
        contact_key = hashlib.sha256( public_key ).digest()
        
        self._c.execute( 'INSERT INTO contacts ( service_id, account_id, contact_key, public_key ) VALUES ( ?, ?, ?, ? );', ( service_id, account_id, sqlite3.Binary( contact_key ), public_key ) )
        
    
    def _GetMessage( self, service_id, account_id, message_key ):
        
        result = self._c.execute( 'SELECT 1 FROM messages WHERE service_id = ? AND account_id = ? AND message_key = ?;', ( service_id, account_id, sqlite3.Binary( message_key ) ) ).fetchone()
        
        if result is None: raise HydrusExceptions.ForbiddenException( 'Could not find that message key on message depot!' )
        
        path = ServerFiles.GetPath( 'message', message_key )
        
        with open( path, 'rb' ) as f: message = f.read()
        
        return message
        
    
    def _GetMessageInfoSince( self, service_id, account_id, timestamp ):
        
        message_keys = [ message_key for ( message_key, ) in self._c.execute( 'SELECT message_key FROM messages WHERE service_id = ? AND account_id = ? AND timestamp > ? ORDER BY timestamp ASC;', ( service_id, account_id, timestamp ) ) ]
        
        statuses = [ status for ( status, ) in self._c.execute( 'SELECT status FROM message_statuses WHERE service_id = ? AND account_id = ? AND timestamp > ? ORDER BY timestamp ASC;', ( service_id, account_id, timestamp ) ) ]
        
        return ( message_keys, statuses )
        
    
    def _GetPublicKey( self, contact_key ):
        
        ( public_key, ) = self._c.execute( 'SELECT public_key FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( contact_key ), ) ).fetchone()
        
        return public_key
        
    '''
class DB( HydrusDB.HydrusDB ):
    
    READ_WRITE_ACTIONS = [ 'access_key', 'immediate_content_update', 'init', 'registration_keys' ]
    
    def __init__( self, controller, db_dir, db_name, no_wal = False ):
        
        self._files_dir = os.path.join( db_dir, 'server_files' )
        self._updates_dir = os.path.join( db_dir, 'server_updates' )
        
        self._ssl_cert_filename = 'server.crt'
        self._ssl_key_filename = 'server.key'
        
        self._ssl_cert_path = os.path.join( db_dir, self._ssl_cert_filename )
        self._ssl_key_path = os.path.join( db_dir, self._ssl_key_filename )
        
        HydrusDB.HydrusDB.__init__( self, controller, db_dir, db_name, no_wal = no_wal )
        
    
    def _AccountTypeExists( self, service_id, title ): return self._c.execute( 'SELECT 1 FROM account_types WHERE service_id = ? AND title = ?;', ( service_id, title ) ).fetchone() is not None
    
    def _AddFile( self, service_key, account_key, file_dict ):
        
        service_id = self._GetServiceId( service_key )
        
        account_id = self._GetAccountId( account_key )
        
        hash = file_dict[ 'hash' ]
        
        hash_id = self._GetHashId( hash )
        
        now = HydrusData.GetNow()
        
        if self._c.execute( 'SELECT 1 FROM file_map WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone() is None or self._c.execute( 'SELECT 1 FROM file_petitions WHERE service_id = ? AND hash_id = ? AND status = ?;', ( service_id, hash_id, HC.DELETED ) ).fetchone() is None:
            
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
            
            options = self._GetOptions( service_key )
            
            max_storage = options[ 'max_storage' ]
            
            if max_storage is not None:
                
                # this is wrong! no service_id in files_info. need to cross with file_map or w/e
                ( current_storage, ) = self._c.execute( 'SELECT SUM( size ) FROM file_map, files_info USING ( hash_id ) WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                if current_storage + size > max_storage: raise HydrusExceptions.ForbiddenException( 'The service is full! It cannot take any more files!' )
                
            
            source_path = file_dict[ 'path' ]
            
            dest_path = ServerFiles.GetExpectedFilePath( hash )
            
            HydrusPaths.MirrorFile( source_path, dest_path )
            
            if 'thumbnail' in file_dict:
                
                thumbnail_dest_path = ServerFiles.GetExpectedThumbnailPath( hash )
                
                thumbnail = file_dict[ 'thumbnail' ]
                
                with open( thumbnail_dest_path, 'wb' ) as f:
                    
                    f.write( thumbnail )
                    
                
            
            if self._c.execute( 'SELECT 1 FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone() is None:
                
                self._c.execute( 'INSERT OR IGNORE INTO files_info ( hash_id, size, mime, width, height, duration, num_frames, num_words ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ? );', ( hash_id, size, mime, width, height, duration, num_frames, num_words ) )
                
            
            self._c.execute( 'INSERT OR IGNORE INTO file_map ( service_id, hash_id, account_id, timestamp ) VALUES ( ?, ?, ?, ? );', ( service_id, hash_id, account_id, now ) )
            
            if options[ 'log_uploader_ips' ]:
                
                ip = file_dict[ 'ip' ]
                
                self._c.execute( 'INSERT INTO ip_addresses ( service_id, hash_id, ip, timestamp ) VALUES ( ?, ?, ?, ? );', ( service_id, hash_id, ip, now ) )
                
            
        
    
    def _AddFilePetition( self, service_id, account_id, hash_ids, reason_id ):
        
        self._ApproveFilePetitionOptimised( service_id, account_id, hash_ids )
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM file_map WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) ]
        
        # this clears out any old reasons, if the user wants to overwrite them
        self._c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND account_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( valid_hash_ids ) + ' AND status = ?;', ( service_id, account_id, HC.PETITIONED ) )
        
        now = HydrusData.GetNow()
        
        self._c.executemany( 'INSERT OR IGNORE INTO file_petitions ( service_id, account_id, hash_id, reason_id, timestamp, status ) VALUES ( ?, ?, ?, ?, ?, ? );', [ ( service_id, account_id, hash_id, reason_id, now, HC.PETITIONED ) for hash_id in valid_hash_ids ] )
        
    
    def _AddNews( self, service_key, news ):
        
        service_id = self._GetServiceId( service_key )
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT INTO news ( service_id, news, timestamp ) VALUES ( ?, ?, ? );', ( service_id, news, now ) )
        
    
    def _AddMappings( self, service_id, account_id, tag_id, hash_ids, overwrite_deleted ):
        
        if overwrite_deleted:
            
            splayed_hash_ids = HydrusData.SplayListForDB( hash_ids )
            
            self._c.execute( 'DELETE FROM deleted_mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, tag_id ) )
            
        else:
            
            already_deleted = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM deleted_mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, tag_id ) ) ]
            
            hash_ids = set( hash_ids ).difference( already_deleted )
            
        
        now = HydrusData.GetNow()
        
        self._c.executemany( 'INSERT OR IGNORE INTO mappings ( service_id, tag_id, hash_id, account_id, timestamp ) VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, tag_id, hash_id, account_id, now ) for hash_id in hash_ids ] )
        
    
    def _AddMappingPetition( self, service_id, account_id, tag_id, hash_ids, reason_id ):
        
        self._ApproveMappingPetitionOptimised( service_id, account_id, tag_id, hash_ids )
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, tag_id ) ) ]
        
        self._c.execute( 'DELETE FROM petitioned_mappings WHERE service_id = ? AND account_id = ? AND tag_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( valid_hash_ids ) + ';', ( service_id, account_id, tag_id ) )
        
        self._c.executemany( 'INSERT OR IGNORE INTO petitioned_mappings ( service_id, account_id, tag_id, hash_id, reason_id ) VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, account_id, tag_id, hash_id, reason_id ) for hash_id in valid_hash_ids ] )
        
    
    def _AddMessagingSession( self, service_key, session_key, account_key, name, expires ):
        
        service_id = self._GetServiceId( service_key )
        
        account_id = self._GetAccountId( account_key )
        
        self._c.execute( 'INSERT INTO sessions ( service_id, session_key, account_id, identifier, name, expiry ) VALUES ( ?, ?, ?, ?, ?, ? );', ( service_id, sqlite3.Binary( session_key ), account_id, sqlite3.Binary( account_key ), name, expires ) )
        
    
    def _AddSession( self, session_key, service_key, account_key, expires ):
        
        service_id = self._GetServiceId( service_key )
        
        account_id = self._GetAccountId( account_key )
        
        self._c.execute( 'INSERT INTO sessions ( session_key, service_id, account_id, expiry ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( session_key ), service_id, account_id, expires ) )
        
    
    def _AddTagParentPetition( self, service_id, account_id, old_tag_id, new_tag_id, reason_id, status ):
        
        result = self._c.execute( 'SELECT 1 WHERE EXISTS ( SELECT 1 FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ? );', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ).fetchone()
        
        it_already_exists = result is not None
        
        if status == HC.PENDING:
            
            if it_already_exists: return
            
        elif status == HC.PETITIONED:
            
            if not it_already_exists: return
            
        
        self._c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND account_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, account_id, old_tag_id, new_tag_id, status ) )
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT OR IGNORE INTO tag_parents ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, now ) )
        
    
    def _AddTagSiblingPetition( self, service_id, account_id, old_tag_id, new_tag_id, reason_id, status ):
        
        result = self._c.execute( 'SELECT 1 WHERE EXISTS ( SELECT 1 FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ? );', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ).fetchone()
        
        it_already_exists = result is not None
        
        if status == HC.PENDING:
            
            if it_already_exists: return
            
        elif status == HC.PETITIONED:
            
            if not it_already_exists: return
            
        
        self._c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND account_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, account_id, old_tag_id, new_tag_id, status ) )
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT OR IGNORE INTO tag_siblings ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, now ) )
        
    
    def _AddToExpires( self, account_ids, timespan ): self._c.execute( 'UPDATE accounts SET expires = expires + ? WHERE account_id IN ' + HydrusData.SplayListForDB( account_ids ) + ';', ( timespan, ) )
    
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
        
    
    def _ApproveFilePetition( self, service_id, account_id, hash_ids, reason_id ):
        
        self._ApproveFilePetitionOptimised( service_id, account_id, hash_ids )
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM file_map WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) ]
        
        self._RewardFilePetitioners( service_id, valid_hash_ids, 1 )
        
        self._DeleteFiles( service_id, account_id, valid_hash_ids, reason_id )
        
    
    def _ApproveFilePetitionOptimised( self, service_id, account_id, hash_ids ):
        
        ( biggest_end, ) = self._c.execute( 'SELECT end FROM update_cache WHERE service_id = ? ORDER BY end DESC LIMIT 1;', ( service_id, ) ).fetchone()
        
        self._c.execute( 'DELETE FROM file_map WHERE service_id = ? AND account_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ' AND timestamp > ?;', ( service_id, account_id, biggest_end ) )
        
    
    def _ApproveMappingPetition( self, service_id, account_id, tag_id, hash_ids, reason_id ):
        
        self._ApproveMappingPetitionOptimised( service_id, account_id, tag_id, hash_ids )
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, tag_id ) ) ]
        
        self._RewardMappingPetitioners( service_id, tag_id, valid_hash_ids, 1 )
        
        self._DeleteMappings( service_id, account_id, tag_id, valid_hash_ids, reason_id )
        
    
    def _ApproveMappingPetitionOptimised( self, service_id, account_id, tag_id, hash_ids ):
        
        ( biggest_end, ) = self._c.execute( 'SELECT end FROM update_cache WHERE service_id = ? ORDER BY end DESC LIMIT 1;', ( service_id, ) ).fetchone()
        
        self._c.execute( 'DELETE FROM mappings WHERE service_id = ? AND account_id = ? AND tag_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ' AND timestamp > ?;', ( service_id, account_id, tag_id, biggest_end ) )
        
    
    def _ApproveTagParentPetition( self, service_id, account_id, old_tag_id, new_tag_id, reason_id, status ):
        
        result = self._c.execute( 'SELECT 1 WHERE EXISTS ( SELECT 1 FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ? );', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ).fetchone()
        
        it_already_exists = result is not None
        
        if status == HC.PENDING:
            
            if it_already_exists: return
            
        elif status == HC.PETITIONED:
            
            if not it_already_exists: return
            
        
        self._RewardTagParentPetitioners( service_id, old_tag_id, new_tag_id, 1 )
        
        self._c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ?;', ( service_id, old_tag_id, new_tag_id ) )
        
        if status == HC.PENDING: new_status = HC.CURRENT
        elif status == HC.PETITIONED: new_status = HC.DELETED
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT OR IGNORE INTO tag_parents ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, old_tag_id, new_tag_id, reason_id, new_status, now ) )
        
        if new_status == HC.CURRENT:
            
            child_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, old_tag_id ) ) ]
            
            self._AddMappings( service_id, account_id, new_tag_id, child_hash_ids, True )
            
        
    
    def _ApproveTagSiblingPetition( self, service_id, account_id, old_tag_id, new_tag_id, reason_id, status ):
        
        result = self._c.execute( 'SELECT 1 WHERE EXISTS ( SELECT 1 FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ? );', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ).fetchone()
        
        it_already_exists = result is not None
        
        if status == HC.PENDING:
            
            if it_already_exists: return
            
        elif status == HC.PETITIONED:
            
            if not it_already_exists: return
            
        
        self._RewardTagSiblingPetitioners( service_id, old_tag_id, new_tag_id, 1 )
        
        self._c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ?;', ( service_id, old_tag_id, new_tag_id ) )
        
        if status == HC.PENDING: new_status = HC.CURRENT
        elif status == HC.PETITIONED: new_status = HC.DELETED
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'INSERT OR IGNORE INTO tag_siblings ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, old_tag_id, new_tag_id, reason_id, new_status, now ) )
        
    
    def _Backup( self ):
        
        self._c.execute( 'COMMIT;' )
        
        self._CloseDBCursor()
        
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
            
            HydrusData.Print( 'backing up: copying updates' )
            HydrusPaths.MirrorTree( self._updates_dir, os.path.join( backup_path, 'server_updates' ) )
            
        finally:
            
            self._InitDBCursor()
            
            self._c.execute( 'BEGIN IMMEDIATE;' )
            
        
        HydrusData.Print( 'backing up: done!' )
        
    
    def _Ban( self, service_id, action, admin_account_id, subject_account_ids, reason_id, expires = None, lifetime = None ):
        
        splayed_subject_account_ids = HydrusData.SplayListForDB( subject_account_ids )
        
        now = HydrusData.GetNow()
        
        if expires is not None: pass
        elif lifetime is not None: expires = now + lifetime
        else: expires = None
        
        self._c.executemany( 'INSERT OR IGNORE INTO bans ( service_id, account_id, admin_account_id, reason_id, created, expires ) VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, subject_account_id, admin_account_id, reason_id, now, expires ) for subject_account_id in subject_account_ids ] )
        
        self._c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
        self._c.execute( 'DELETE FROM petitioned_mappings WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ';', ( service_id, ) )
        
        self._c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) )
        
        self._c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) )
        
        if action == HC.SUPERBAN:
            
            hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ';', ( service_id, ) ) ]
            
            if len( hash_ids ) > 0: self._DeleteFiles( service_id, admin_account_id, hash_ids, reason_id )
            
            mappings_dict = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT tag_id, hash_id FROM mappings WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ';', ( service_id, ) ) )
            
            if len( mappings_dict ) > 0:
                
                for ( tag_id, hash_ids ) in mappings_dict.items(): self._DeleteMappings( service_id, admin_account_id, tag_id, hash_ids, reason_id )
                
            
        
    
    def _ChangeAccountType( self, account_ids, account_type_id ): self._c.execute( 'UPDATE accounts SET account_type_id = ? WHERE account_id IN ' + HydrusData.SplayListForDB( account_ids ) + ';', ( account_type_id, ) )
    
    def _CheckDataUsage( self ):
        
        ( version_year, version_month ) = self._c.execute( 'SELECT year, month FROM version;' ).fetchone()
        
        current_time_struct = time.gmtime()
        
        ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
        
        if version_year != current_year or version_month != current_month:
            
            self._c.execute( 'UPDATE version SET year = ?, month = ?;', ( current_year, current_month ) )
            
            self._c.execute( 'UPDATE accounts SET used_bytes = ?, used_requests = ?;', ( 0, 0 ) )
            
            self.pub_after_commit( 'update_all_session_accounts' )
            
        
    
    def _CheckMonthlyData( self ):
        
        service_info = self._GetServicesInfo()
        
        running_total = 0
        
        self._services_over_monthly_data = set()
        
        for ( service_key, service_type, options ) in service_info:
            
            service_id = self._GetServiceId( service_key )
            
            if service_type != HC.SERVER_ADMIN:
                
                ( total_used_bytes, ) = self._c.execute( 'SELECT SUM( used_bytes ) FROM accounts WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                if total_used_bytes is None: total_used_bytes = 0
                
                running_total += total_used_bytes
                
                if 'max_monthly_data' in options:
                    
                    max_monthly_data = options[ 'max_monthly_data' ]
                    
                    if max_monthly_data is not None and total_used_bytes > max_monthly_data: self._services_over_monthly_data.add( service_key )
                    
                
            
        
        # have to do this after
        
        server_admin_options = self._GetOptions( HC.SERVER_ADMIN_KEY )
        
        self._over_monthly_data = False
        
        if 'max_monthly_data' in server_admin_options:
            
            max_monthly_data = server_admin_options[ 'max_monthly_data' ]
            
            if max_monthly_data is not None and running_total > max_monthly_data: self._over_monthly_data = True
            
        
    
    def _ClearBans( self ):
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'DELETE FROM bans WHERE expires < ?;', ( now, ) )
        
    
    def _CreateDB( self ):
        
        dirs = ( self._files_dir, self._updates_dir )
        
        for dir in dirs:
            
            HydrusPaths.MakeSureDirectoryExists( dir )
            
        
        dirs = ( self._files_dir, )
        
        for dir in dirs:
            
            for prefix in HydrusData.IterateHexPrefixes():
                
                new_dir = os.path.join( dir, prefix )
                
                HydrusPaths.MakeSureDirectoryExists( new_dir )
                
            
        
        HydrusDB.SetupDBCreatePragma( self._c, no_wal = self._no_wal )
        
        self._c.execute( 'BEGIN IMMEDIATE' )
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, type INTEGER, options TEXT_YAML );' )
        
        self._c.execute( 'CREATE TABLE accounts( account_id INTEGER PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_key BLOB_BYTES, hashed_access_key BLOB_BYTES, account_type_id INTEGER, created INTEGER, expires INTEGER, used_bytes INTEGER, used_requests INTEGER );' )
        self._c.execute( 'CREATE UNIQUE INDEX accounts_account_key_index ON accounts ( account_key );' )
        self._c.execute( 'CREATE UNIQUE INDEX accounts_hashed_access_key_index ON accounts ( hashed_access_key );' )
        self._c.execute( 'CREATE UNIQUE INDEX accounts_service_id_account_id_index ON accounts ( service_id, account_id );' )
        self._c.execute( 'CREATE INDEX accounts_service_id_account_type_id_index ON accounts ( service_id, account_type_id );' )
        
        self._c.execute( 'CREATE TABLE account_scores ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, score_type INTEGER, score INTEGER, PRIMARY KEY( service_id, account_id, score_type ) );' )
        
        self._c.execute( 'CREATE TABLE account_types ( account_type_id INTEGER PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, title TEXT, account_type TEXT_YAML );' )
        self._c.execute( 'CREATE UNIQUE INDEX account_types_service_id_account_type_id_index ON account_types ( service_id, account_type_id );' )
        
        self._c.execute( 'CREATE TABLE analyze_timestamps ( name TEXT, timestamp INTEGER );' )
        
        self._c.execute( 'CREATE TABLE bans ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, admin_account_id INTEGER, reason_id INTEGER, created INTEGER, expires INTEGER, PRIMARY KEY( service_id, account_id ) );' )
        self._c.execute( 'CREATE INDEX bans_expires ON bans ( expires );' )
        
        self._c.execute( 'CREATE TABLE contacts ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, contact_key BLOB, public_key TEXT, PRIMARY KEY( service_id, account_id ) );' )
        self._c.execute( 'CREATE UNIQUE INDEX contacts_contact_key_index ON contacts ( contact_key );' )
        
        self._c.execute( 'CREATE TABLE files_info ( hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, num_words INTEGER );' )
        
        self._c.execute( 'CREATE TABLE file_map ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, account_id INTEGER, timestamp INTEGER, PRIMARY KEY( service_id, hash_id, account_id ) );' )
        self._c.execute( 'CREATE INDEX file_map_service_id_account_id_index ON file_map ( service_id, account_id );' )
        self._c.execute( 'CREATE INDEX file_map_service_id_timestamp_index ON file_map ( service_id, timestamp );' )
        
        self._c.execute( 'CREATE TABLE file_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY( service_id, account_id, hash_id, status ) );' )
        self._c.execute( 'CREATE INDEX file_petitions_service_id_account_id_reason_id_index ON file_petitions ( service_id, account_id, reason_id );' )
        self._c.execute( 'CREATE INDEX file_petitions_service_id_hash_id_index ON file_petitions ( service_id, hash_id );' )
        self._c.execute( 'CREATE INDEX file_petitions_service_id_status_index ON file_petitions ( service_id, status );' )
        self._c.execute( 'CREATE INDEX file_petitions_service_id_timestamp_index ON file_petitions ( service_id, timestamp );' )
        
        self._c.execute( 'CREATE TABLE ip_addresses ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, ip TEXT, timestamp INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
        
        self._c.execute( 'CREATE TABLE messages ( message_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, timestamp INTEGER );' )
        self._c.execute( 'CREATE INDEX messages_service_id_account_id_index ON messages ( service_id, account_id );' )
        self._c.execute( 'CREATE INDEX messages_timestamp_index ON messages ( timestamp );' )
        
        self._c.execute( 'CREATE TABLE message_statuses ( status_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, status BLOB_BYTES, timestamp INTEGER );' )
        self._c.execute( 'CREATE INDEX message_statuses_service_id_account_id_index ON message_statuses ( service_id, account_id );' )
        self._c.execute( 'CREATE INDEX message_statuses_timestamp_index ON message_statuses ( timestamp );' )
        
        self._c.execute( 'CREATE TABLE messaging_sessions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, session_key BLOB_BYTES, account_id INTEGER, identifier BLOB_BYTES, name TEXT, expiry INTEGER );' )
        
        self._c.execute( 'CREATE TABLE news ( service_id INTEGER REFERENCES services ON DELETE CASCADE, news TEXT, timestamp INTEGER );' )
        self._c.execute( 'CREATE INDEX news_timestamp_index ON news ( timestamp );' )
        
        self._c.execute( 'CREATE TABLE reasons ( reason_id INTEGER PRIMARY KEY, reason TEXT );' )
        self._c.execute( 'CREATE UNIQUE INDEX reasons_reason_index ON reasons ( reason );' )
        
        self._c.execute( 'CREATE TABLE registration_keys ( registration_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_type_id INTEGER, account_key BLOB_BYTES, access_key BLOB_BYTES, expiry INTEGER );' )
        self._c.execute( 'CREATE UNIQUE INDEX registration_keys_access_key_index ON registration_keys ( access_key );' )
        
        self._c.execute( 'CREATE TABLE sessions ( session_key BLOB_BYTES, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, expiry INTEGER );' )
        
        self._c.execute( 'CREATE TABLE tag_parents ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, old_tag_id INTEGER, new_tag_id INTEGER, timestamp INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, account_id, old_tag_id, new_tag_id, status ) );' )
        self._c.execute( 'CREATE INDEX tag_parents_service_id_old_tag_id_index ON tag_parents ( service_id, old_tag_id, new_tag_id );' )
        self._c.execute( 'CREATE INDEX tag_parents_service_id_timestamp_index ON tag_parents ( service_id, timestamp );' )
        self._c.execute( 'CREATE INDEX tag_parents_service_id_status_index ON tag_parents ( service_id, status );' )
        
        self._c.execute( 'CREATE TABLE tag_siblings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, old_tag_id INTEGER, new_tag_id INTEGER, timestamp INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, account_id, old_tag_id, status ) );' )
        self._c.execute( 'CREATE INDEX tag_siblings_service_id_old_tag_id_index ON tag_siblings ( service_id, old_tag_id );' )
        self._c.execute( 'CREATE INDEX tag_siblings_service_id_timestamp_index ON tag_siblings ( service_id, timestamp );' )
        self._c.execute( 'CREATE INDEX tag_siblings_service_id_status_index ON tag_siblings ( service_id, status );' )
        
        self._c.execute( 'CREATE TABLE update_cache ( service_id INTEGER REFERENCES services ON DELETE CASCADE, begin INTEGER, end INTEGER, dirty INTEGER_BOOLEAN, PRIMARY KEY( service_id, begin ) );' )
        self._c.execute( 'CREATE UNIQUE INDEX update_cache_service_id_end_index ON update_cache ( service_id, end );' )
        self._c.execute( 'CREATE INDEX update_cache_service_id_dirty_index ON update_cache ( service_id, dirty );' )
        
        self._c.execute( 'CREATE TABLE version ( version INTEGER, year INTEGER, month INTEGER );' )
        
        # mappings
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.petitioned_mappings ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY( service_id, tag_id, hash_id, account_id ) ) WITHOUT ROWID;' )
        self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.petitioned_mappings_service_id_account_id_reason_id_tag_id_index ON petitioned_mappings ( service_id, account_id, reason_id, tag_id );' )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.deleted_mappings ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, PRIMARY KEY( service_id, tag_id, hash_id ) ) WITHOUT ROWID;' )
        self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.deleted_mappings_service_id_account_id_index ON deleted_mappings ( service_id, account_id );' )
        self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.deleted_mappings_service_id_timestamp_index ON deleted_mappings ( service_id, timestamp );' )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mappings ( service_id INTEGER, tag_id INTEGER, hash_id INTEGER, account_id INTEGER, timestamp INTEGER, PRIMARY KEY( service_id, tag_id, hash_id ) ) WITHOUT ROWID;' )
        self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mappings_account_id_index ON mappings ( account_id );' )
        self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mappings_timestamp_index ON mappings ( timestamp );' )
        
        # master
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.hashes ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES UNIQUE );' )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.tags ( tag_id INTEGER PRIMARY KEY, tag TEXT UNIQUE );' )
        
        # inserts
        
        current_time_struct = time.gmtime()
        
        ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
        
        self._c.execute( 'INSERT INTO version ( version, year, month ) VALUES ( ?, ?, ? );', ( HC.SOFTWARE_VERSION, current_year, current_month ) )
        
        # create ssl keys
        
        HydrusEncryption.GenerateOpenSSLCertAndKeyFile( self._ssl_cert_path, self._ssl_key_path )
        
        # set up server admin
        
        service_key = HC.SERVER_ADMIN_KEY
        
        service_type = HC.SERVER_ADMIN
        
        options = HC.DEFAULT_OPTIONS[ HC.SERVER_ADMIN ]
        
        options[ 'port' ] = HC.DEFAULT_SERVER_ADMIN_PORT
        
        self._c.execute( 'INSERT INTO services ( service_key, type, options ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, options ) )
        
        server_admin_service_id = self._c.lastrowid
        
        server_admin_account_type = HydrusData.AccountType( 'server admin', [ HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ], ( None, None ) )
        
        self._c.execute( 'INSERT INTO account_types ( service_id, title, account_type ) VALUES ( ?, ?, ? );', ( server_admin_service_id, 'server admin', server_admin_account_type ) )
        
        self._c.execute( 'COMMIT' )
        
    
    def _CreateUpdate( self, service_key, begin, end ):
        
        self._GenerateUpdate( service_key, begin, end )
        
        service_id = self._GetServiceId( service_key )
        
        self._c.execute( 'INSERT OR REPLACE INTO update_cache ( service_id, begin, end, dirty ) VALUES ( ?, ?, ?, ? );', ( service_id, begin, end, False ) )
        
    
    def _DeleteFiles( self, service_id, account_id, hash_ids, reason_id ):
        
        splayed_hash_ids = HydrusData.SplayListForDB( hash_ids )
        
        self._c.execute( 'DELETE FROM file_map WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
        self._c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
        now = HydrusData.GetNow()
        
        self._c.executemany( 'INSERT OR IGNORE INTO file_petitions ( service_id, account_id, hash_id, reason_id, timestamp, status ) VALUES ( ?, ?, ?, ?, ?, ? );', ( ( service_id, account_id, hash_id, reason_id, now, HC.DELETED ) for hash_id in hash_ids ) )
        
    
    def _DeleteMappings( self, service_id, account_id, tag_id, hash_ids, reason_id ):
        
        splayed_hash_ids = HydrusData.SplayListForDB( hash_ids )
        
        self._c.execute( 'DELETE FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, tag_id ) )
        self._c.execute( 'DELETE FROM petitioned_mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, tag_id ) )
        
        self._c.executemany( 'INSERT OR IGNORE INTO deleted_mappings ( service_id, tag_id, hash_id, account_id, reason_id, timestamp ) VALUES ( ?, ?, ?, ?, ?, ? );', ( ( service_id, tag_id, hash_id, account_id, reason_id, HydrusData.GetNow() ) for hash_id in hash_ids ) )
        
    
    def _DeleteOrphans( self ):
        
        # files
        
        deletees = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT DISTINCT hash_id FROM files_info EXCEPT SELECT DISTINCT hash_id FROM file_map;' ) ]
        
        if len( deletees ) > 0:
            
            deletee_hashes = set( self._GetHashes( deletees ) )
            
            for hash in deletee_hashes:
                
                path = ServerFiles.GetExpectedFilePath( hash )
                
                if os.path.exists( path ):
                    
                    HydrusPaths.RecyclePath( path )
                    
                
                path = ServerFiles.GetExpectedThumbnailPath( hash )
                
                if os.path.exists( path ):
                    
                    HydrusPaths.RecyclePath( path )
                    
                
            
            self._c.execute( 'DELETE FROM files_info WHERE hash_id IN ' + HydrusData.SplayListForDB( deletees ) + ';' )
            
        
    
    def _DenyFilePetition( self, service_id, hash_ids ):
        
        self._RewardFilePetitioners( service_id, hash_ids, -1 )
        
        self._c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
    
    def _DenyMappingPetition( self, service_id, tag_id, hash_ids ):
        
        self._RewardMappingPetitioners( service_id, tag_id, hash_ids, -1 )
        
        self._c.execute( 'DELETE FROM petitioned_mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, tag_id ) )
        
    
    def _DenyTagParentPetition( self, service_id, old_tag_id, new_tag_id, action ):
        
        self._RewardTagParentPetitioners( service_id, old_tag_id, new_tag_id, -1 )
        
        if action == HC.CONTENT_UPDATE_DENY_PEND: status = HC.PENDING
        elif action == HC.CONTENT_UPDATE_DENY_PETITION: status = HC.PETITIONED
        
        self._c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, old_tag_id, new_tag_id, status ) )
        
    
    def _DenyTagSiblingPetition( self, service_id, old_tag_id, new_tag_id, action ):
        
        self._RewardTagSiblingPetitioners( service_id, old_tag_id, new_tag_id, -1 )
        
        if action == HC.CONTENT_UPDATE_DENY_PEND: status = HC.PENDING
        elif action == HC.CONTENT_UPDATE_DENY_PETITION: status = HC.PETITIONED
        
        self._c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, old_tag_id, new_tag_id, status ) )
        
    
    def _FlushRequestsMade( self, all_requests ):
        
        requests_dict = HydrusData.BuildKeyToListDict( all_requests )
        
        self._c.executemany( 'UPDATE accounts SET used_bytes = used_bytes + ?, used_requests = used_requests + ? WHERE account_key = ?;', [ ( sum( num_bytes_list ), len( num_bytes_list ), sqlite3.Binary( account_key ) ) for ( account_key, num_bytes_list ) in requests_dict.items() ] )
        
    
    def _GenerateRegistrationKeys( self, service_key, num, title, lifetime = None ):
        
        service_id = self._GetServiceId( service_key )
        
        account_type_id = self._GetAccountTypeId( service_id, title )
        
        now = HydrusData.GetNow()
        
        if lifetime is not None: expires = now + lifetime
        else: expires = None
        
        keys = [ ( os.urandom( HC.HYDRUS_KEY_LENGTH ), os.urandom( HC.HYDRUS_KEY_LENGTH ), os.urandom( HC.HYDRUS_KEY_LENGTH ) ) for i in range( num ) ]
        
        self._c.executemany( 'INSERT INTO registration_keys ( registration_key, service_id, account_type_id, account_key, access_key, expiry ) VALUES ( ?, ?, ?, ?, ?, ? );', [ ( sqlite3.Binary( hashlib.sha256( registration_key ).digest() ), service_id, account_type_id, sqlite3.Binary( account_key ), sqlite3.Binary( access_key ), expires ) for ( registration_key, account_key, access_key ) in keys ] )
        
        return [ registration_key for ( registration_key, account_key, access_key ) in keys ]
        
    
    def _GenerateImmediateContentUpdate( self, service_key ):
        
        update_ends = self._GetUpdateEnds()
        
        latest_end = update_ends[ service_key ]
        
        begin = latest_end + 1
        
        end = HydrusData.GetNow()
        
        service_id = self._GetServiceId( service_key )
        
        service_type = self._GetServiceType( service_id )
        
        if service_type == HC.FILE_REPOSITORY:
            
            iterator = self._IterateFileUpdateContentData
            
        elif service_type == HC.TAG_REPOSITORY:
            
            iterator = self._IterateTagUpdateContentData
            
        
        subindex = 0
        weight = 0
        
        content_update_package = HydrusData.ServerToClientContentUpdatePackage()
        
        smaller_time_step = max( 10, ( end - begin ) / 100 )
        
        sub_begin = begin
        
        while sub_begin <= end:
            
            sub_end = min( ( sub_begin + smaller_time_step ) - 1, end )
            
            for ( data_type, action, rows, hash_ids_to_hashes, rows_weight ) in iterator( service_id, sub_begin, sub_end ):
                
                content_update_package.AddContentData( data_type, action, rows, hash_ids_to_hashes )
                
            
            sub_begin += smaller_time_step
            
        
        return content_update_package
        
    
    def _GenerateUpdate( self, service_key, begin, end ):
        
        service_id = self._GetServiceId( service_key )
        
        service_type = self._GetServiceType( service_id )
        
        if service_type == HC.FILE_REPOSITORY:
            
            iterator = self._IterateFileUpdateContentData
            
        elif service_type == HC.TAG_REPOSITORY:
            
            iterator = self._IterateTagUpdateContentData
            
        
        subindex = 0
        weight = 0
        
        content_update_package = HydrusData.ServerToClientContentUpdatePackage()
        
        smaller_time_step = ( end - begin ) / 100
        
        sub_begin = begin
        
        while sub_begin <= end:
            
            sub_end = min( ( sub_begin + smaller_time_step ) - 1, end )
            
            for ( data_type, action, rows, hash_ids_to_hashes, rows_weight ) in iterator( service_id, sub_begin, sub_end ):
                
                content_update_package.AddContentData( data_type, action, rows, hash_ids_to_hashes )
                
                weight += rows_weight
                
                if weight >= 100000:
                    
                    path = ServerFiles.GetExpectedContentUpdatePackagePath( service_key, begin, subindex )
                    
                    network_string = content_update_package.DumpToNetworkString()
                    
                    with open( path, 'wb' ) as f:
                        
                        f.write( network_string )
                        
                    
                    subindex += 1
                    weight = 0
                    
                    content_update_package = HydrusData.ServerToClientContentUpdatePackage()
                    
                
            
            sub_begin += smaller_time_step
            
        
        if weight > 0:
            
            path = ServerFiles.GetExpectedContentUpdatePackagePath( service_key, begin, subindex )
            
            network_string = content_update_package.DumpToNetworkString()
            
            with open( path, 'wb' ) as f:
                
                f.write( network_string )
                
            
            subindex += 1
            
        
        subindex_count = subindex
        
        service_update_package = HydrusData.ServerToClientServiceUpdatePackage()
        
        service_update_package.SetBeginEnd( begin, end )
        service_update_package.SetSubindexCount( subindex_count )
        
        news_rows = self._c.execute( 'SELECT news, timestamp FROM news WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ).fetchall()
        
        service_update_package.SetNews( news_rows )
        
        path = ServerFiles.GetExpectedServiceUpdatePackagePath( service_key, begin )
        
        network_string = service_update_package.DumpToNetworkString()
        
        with open( path, 'wb' ) as f:
            
            f.write( network_string )
            
        
    
    def _GetAccessKey( self, registration_key ):
        
        # we generate a new access_key every time this is requested so that if the registration_key leaks, no one grab the access_key before the legit user does
        # the reg_key is deleted when the last-requested access_key is used to create a session, which calls getaccountkeyfromaccesskey
        
        try: ( one, ) = self._c.execute( 'SELECT 1 FROM registration_keys WHERE registration_key = ?;', ( sqlite3.Binary( hashlib.sha256( registration_key ).digest() ), ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'The service could not find that registration key in its database.' )
        
        new_access_key = os.urandom( HC.HYDRUS_KEY_LENGTH )
        
        self._c.execute( 'UPDATE registration_keys SET access_key = ? WHERE registration_key = ?;', ( sqlite3.Binary( new_access_key ), sqlite3.Binary( hashlib.sha256( registration_key ).digest() ) ) )
        
        return new_access_key
        
    
    def _GetAccount( self, account_key ):
        
        ( account_id, service_id, account_key, account_type, created, expires, used_bytes, used_requests ) = self._c.execute( 'SELECT account_id, service_id, account_key, account_type, created, expires, used_bytes, used_requests FROM accounts, account_types USING ( service_id, account_type_id ) WHERE account_key = ?;', ( sqlite3.Binary( account_key ), ) ).fetchone()
        
        banned_info = self._c.execute( 'SELECT reason, created, expires FROM bans, reasons USING ( reason_id ) WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
        
        return HydrusData.Account( account_key, account_type, created, expires, used_bytes, used_requests, banned_info = banned_info )
        
    
    def _GetAccountFileInfo( self, service_id, account_id ):
        
        ( num_files, num_files_bytes ) = self._c.execute( 'SELECT COUNT( * ), SUM( size ) FROM file_map, files_info USING ( hash_id ) WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
        
        if num_files_bytes is None: num_files_bytes = 0
        
        result = self._c.execute( 'SELECT score FROM account_scores WHERE service_id = ? AND account_id = ? AND score_type = ?;', ( service_id, account_id, HC.SCORE_PETITION ) ).fetchone()
        
        if result is None: petition_score = 0
        else: ( petition_score, ) = result
        
        ( num_petitions, ) = self._c.execute( 'SELECT COUNT( DISTINCT reason_id ) FROM file_petitions WHERE service_id = ? AND account_id = ? AND status = ?;', ( service_id, account_id, HC.PETITIONED ) ).fetchone()
        
        account_info = {}
        
        account_info[ 'num_files' ] = num_files
        account_info[ 'num_files_bytes' ] = num_files_bytes
        account_info[ 'petition_score' ] = petition_score
        account_info[ 'num_petitions' ] = num_petitions
        
        return account_info
        
    
    def _GetAccountKeyFromAccessKey( self, service_key, access_key ):
        
        service_id = self._GetServiceId( service_key )
        
        try:
            
            ( account_key, ) = self._c.execute( 'SELECT account_key FROM accounts WHERE service_id = ? AND hashed_access_key = ?;', ( service_id, sqlite3.Binary( hashlib.sha256( access_key ).digest() ), ) ).fetchone()
            
        except:
            
            # we do not delete the registration_key (and hence the raw unhashed access_key)
            # until the first attempt to create a session to make sure the user
            # has the access_key saved
            
            try:
                
                ( account_type_id, account_key, expires ) = self._c.execute( 'SELECT account_type_id, account_key, expiry FROM registration_keys WHERE access_key = ?;', ( sqlite3.Binary( access_key ), ) ).fetchone()
                
            except:
                
                raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
                
            
            self._c.execute( 'DELETE FROM registration_keys WHERE access_key = ?;', ( sqlite3.Binary( access_key ), ) )
            
            #
            
            now = HydrusData.GetNow()
            
            self._c.execute( 'INSERT INTO accounts ( service_id, account_key, hashed_access_key, account_type_id, created, expires, used_bytes, used_requests ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ? );', ( service_id, sqlite3.Binary( account_key ), sqlite3.Binary( hashlib.sha256( access_key ).digest() ), account_type_id, now, expires, 0, 0 ) )
            
        
        return account_key
        
    
    def _GetAccountKeyFromAccountId( self, account_id ):
        
        try: ( account_key, ) = self._c.execute( 'SELECT account_key FROM accounts WHERE account_id = ?;', ( account_id, ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account_id in its database.' )
        
        return account_key
        
    
    def _GetAccountKeyFromIdentifier( self, service_key, account_identifier ):
        
        service_id = self._GetServiceId( service_key )
        
        if account_identifier.HasAccountKey():
            
            account_key = account_identifier.GetData()
            
            result = self._c.execute( 'SELECT 1 FROM accounts WHERE service_id = ? AND account_key = ?;', ( service_id, sqlite3.Binary( account_key ) ) ).fetchone()
            
            if result is None: raise HydrusExceptions.ForbiddenException( 'The service could not find that hash in its database.')
            
        elif account_identifier.HasContent():
            
            content = account_identifier.GetData()
            
            content_type = content.GetContentType()
            content_data = content.GetContent()
            
            if content_type == HC.CONTENT_TYPE_FILES:
                
                try:
                    
                    hash = content_data[0]
                    
                    hash_id = self._GetHashId( hash )
                    
                    result = self._c.execute( 'SELECT account_id FROM file_map WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
                    
                    if result is None: result = self._c.execute( 'SELECT account_id FROM file_petitions WHERE service_id = ? AND hash_id = ? AND status = ?;', ( service_id, hash_id, HC.DELETED ) ).fetchone()
                    
                    ( account_id, ) = result
                    
                except: raise HydrusExceptions.ForbiddenException( 'The service could not find that hash in its database.' )
                
            elif content_type == HC.CONTENT_TYPE_MAPPING:
                
                try:
                    
                    ( tag, hash ) = content_data
                    
                    hash_id = self._GetHashId( hash )
                    tag_id = self._GetTagId( tag )
                    
                    ( account_id, ) = self._c.execute( 'SELECT account_id FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id = ?;', ( service_id, tag_id, hash_id ) ).fetchone()
                    
                except: raise HydrusExceptions.ForbiddenException( 'The service could not find that mapping in its database.' )
                
            
            try: ( account_key, ) = self._c.execute( 'SELECT account_key FROM accounts WHERE account_id = ?;', ( account_id, ) ).fetchone()
            except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
            
        
        return account_key
        
    
    def _GetAccountIdFromContactKey( self, service_id, contact_key ):
        
        try:
            
            ( account_id, ) = self._c.execute( 'SELECT account_id FROM contacts WHERE service_id = ? AND contact_key = ?;', ( service_id, sqlite3.Binary( contact_key ) ) ).fetchone()
            
        except:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that contact key!' )
            
        
        return account_id
        
    
    def _GetAccountId( self, account_key ):
        
        result = self._c.execute( 'SELECT account_id FROM accounts WHERE account_key = ?;', ( sqlite3.Binary( account_key ), ) ).fetchone()
        
        if result is None: raise HydrusExceptions.ForbiddenException( 'The service could not find that account key in its database.' )
        
        ( account_id, ) = result
        
        return account_id
        
    
    def _GetAccountInfo( self, service_key, account_key ):
        
        service_id = self._GetServiceId( service_key )
        
        account = self._GetAccount( account_key )
        
        account_id = self._GetAccountId( account_key )
        
        service_type = self._GetServiceType( service_id )
        
        if service_type == HC.FILE_REPOSITORY: account_info = self._GetAccountFileInfo( service_id, account_id )
        elif service_type == HC.TAG_REPOSITORY: account_info = self._GetAccountMappingInfo( service_id, account_id )
        else: account_info = {}
        
        account_info[ 'account' ] = account
        
        return account_info
        
    
    def _GetAccountMappingInfo( self, service_id, account_id ):
        
        num_mappings = len( self._c.execute( 'SELECT 1 FROM mappings WHERE service_id = ? AND account_id = ? LIMIT 5000;', ( service_id, account_id ) ).fetchall() )
        
        result = self._c.execute( 'SELECT score FROM account_scores WHERE service_id = ? AND account_id = ? AND score_type = ?;', ( service_id, account_id, HC.SCORE_PETITION ) ).fetchone()
        
        if result is None: petition_score = 0
        else: ( petition_score, ) = result
        
        # crazy query here because two distinct columns
        ( num_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT tag_id, reason_id FROM petitioned_mappings WHERE service_id = ? AND account_id = ? );', ( service_id, account_id ) ).fetchone()
        
        account_info = {}
        
        account_info[ 'num_mappings' ] = num_mappings
        account_info[ 'petition_score' ] = petition_score
        account_info[ 'num_petitions' ] = num_petitions
        
        return account_info
        
    
    def _GetAccountTypeId( self, service_id, title ):
        
        result = self._c.execute( 'SELECT account_type_id FROM account_types WHERE service_id = ? AND title = ?;', ( service_id, title ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'Could not find account title ' + HydrusData.ToUnicode( title ) + ' in db for this service.' )
            
        
        ( account_type_id, ) = result
        
        return account_type_id
        
    
    def _GetAccountTypes( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        return [ account_type for ( account_type, ) in self._c.execute( 'SELECT account_type FROM account_types WHERE service_id = ?;', ( service_id, ) ) ]
        
    
    def _GetFile( self, hash ):
        
        path = ServerFiles.GetFilePath( hash )
        
        with open( path, 'rb' ) as f: file = f.read()
        
        return file
        
    
    def _GetFilePetition( self, service_id ):
        
        data_type = HC.CONTENT_TYPE_FILES
        status = HC.PETITIONED
        action = HC.CONTENT_UPDATE_PETITION
        
        result = self._c.execute( 'SELECT DISTINCT account_id, reason_id FROM file_petitions WHERE service_id = ? AND status = ? ORDER BY RANDOM() LIMIT 1;', ( service_id, status ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.NotFoundException( 'No petitions!' )
            
        
        ( account_id, reason_id ) = result
        
        account_key = self._GetAccountKeyFromAccountId( account_id )
        
        petitioner_account_identifier = HydrusData.AccountIdentifier( account_key = account_key )
        
        reason = self._GetReason( reason_id )
        
        hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM file_petitions WHERE service_id = ? AND account_id = ? AND reason_id = ? AND status = ?;', ( service_id, account_id, reason_id, status ) ) ]
        
        hashes = self._GetHashes( hash_ids )
        
        contents = [ HydrusData.Content( data_type, hashes ) ]
        
        return HydrusData.ServerToClientPetition( action, petitioner_account_identifier, reason, contents )
        
    
    def _GetHash( self, hash_id ):
        
        result = self._c.execute( 'SELECT hash FROM hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None: raise Exception( 'File hash error in database' )
        
        ( hash, ) = result
        
        return hash
        
    
    def _GetHashes( self, hash_ids ): return [ hash for ( hash, ) in self._c.execute( 'SELECT hash FROM hashes WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ) ]
    
    def _GetHashId( self, hash ):
        
        result = self._c.execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( sqlite3.Binary( hash ), ) )
            
            hash_id = self._c.lastrowid
            
            return hash_id
            
        else:
            
            ( hash_id, ) = result
            
            return hash_id
            
        
    
    def _GetHashIds( self, hashes ):
        
        hash_ids = set()
        hashes_not_in_db = set()
        
        for hash in hashes:
            
            result = self._c.execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
            
            if result is None: hashes_not_in_db.add( hash )
            else:
                
                ( hash_id, ) = result
                
                hash_ids.add( hash_id )
                
            
        
        if len( hashes_not_in_db ) > 0:
            
            self._c.executemany( 'INSERT INTO hashes ( hash ) VALUES( ? );', ( ( sqlite3.Binary( hash ), ) for hash in hashes_not_in_db ) )
            
            hash_ids.update( self._GetHashIds( hashes ) )
            
        
        return hash_ids
        
    
    def _GetHashIdsToHashes( self, hash_ids ): return { hash_id : hash for ( hash_id, hash ) in self._c.execute( 'SELECT hash_id, hash FROM hashes WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ) }
    
    def _GetIPTimestamp( self, service_key, hash ):
        
        service_id = self._GetServiceId( service_key )
        
        hash_id = self._GetHashId( hash )
        
        result = self._c.execute( 'SELECT ip, timestamp FROM ip_addresses WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
        
        if result is None: raise HydrusExceptions.ForbiddenException( 'Did not find ip information for that hash.' )
        
        return result
        
    
    def _GetMessagingSessions( self ):
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'DELETE FROM messaging_sessions WHERE ? > expiry;', ( now, ) )
        
        existing_session_ids = HydrusData.BuildKeyToListDict( [ ( service_id, ( session_key, account_id, identifier, name, expires ) ) for ( service_id, session_key, account_id, identifier, name, expires ) in self._c.execute( 'SELECT service_id, session_key, account_id, identifier, name, expiry FROM messaging_sessions;' ) ] )
        
        existing_sessions = {}
        
        for ( service_id, tuples ) in existing_session_ids.items():
            
            service_key = self._GetServiceKey( service_id )
            
            processed_tuples = []
            
            for ( account_id, identifier, name, expires ) in tuples:
                
                account_key = self._GetAccountKeyFromAccountId( account_id )
                
                account = self._GetAccount( account_key )
                
                processed_tuples.append( ( account, name, expires ) )
                
            
            existing_sessions[ service_key ] = processed_tuples
            
        
        return existing_sessions
        
    
    def _GetNumPetitions( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        service_type = self._GetServiceType( service_id )
        
        if service_type == HC.FILE_REPOSITORY:
            
            ( num_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT account_id, reason_id FROM file_petitions WHERE service_id = ? AND status = ? );', ( service_id, HC.PETITIONED ) ).fetchone()
            
        elif service_type == HC.TAG_REPOSITORY:
            
            ( num_mapping_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT account_id, tag_id, reason_id FROM petitioned_mappings WHERE service_id = ? );', ( service_id, ) ).fetchone()
            
            ( num_tag_sibling_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM tag_siblings WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
            
            ( num_tag_parent_petitions, ) = self._c.execute( 'SELECT COUNT( * ) FROM tag_parents WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
            
            num_petitions = num_mapping_petitions + num_tag_sibling_petitions + num_tag_parent_petitions
            
        
        return num_petitions
        
    
    def _GetOptions( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        ( options, ) = self._c.execute( 'SELECT options FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return options
        
    
    def _GetPetition( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        service_type = self._GetServiceType( service_id )
        
        if service_type == HC.FILE_REPOSITORY: petition = self._GetFilePetition( service_id )
        elif service_type == HC.TAG_REPOSITORY: petition = self._GetTagPetition( service_id )
        
        return petition
        
    
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
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_id, ) = result
        
        return service_id
        
    
    def _GetServiceIds( self, limited_types = HC.ALL_SERVICES ): return [ service_id for ( service_id, ) in self._c.execute( 'SELECT service_id FROM services WHERE type IN ' + HydrusData.SplayListForDB( limited_types ) + ';' ) ]
    
    def _GetServiceKey( self, service_id ):
        
        ( service_key, ) = self._c.execute( 'SELECT service_key FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return service_key
        
    
    def _GetServiceKeys( self, limited_types = HC.ALL_SERVICES ): return [ service_key for ( service_key, ) in self._c.execute( 'SELECT service_key FROM services WHERE type IN '+ HydrusData.SplayListForDB( limited_types ) + ';' ) ]
    
    def _GetServiceType( self, service_id ):
        
        result = self._c.execute( 'SELECT type FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_type, ) = result
        
        return service_type
        
    
    def _GetServiceInfo( self, service_key ): return self._c.execute( 'SELECT type, options FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
    
    def _GetServicesInfo( self, limited_types = HC.ALL_SERVICES ): return self._c.execute( 'SELECT service_key, type, options FROM services WHERE type IN '+ HydrusData.SplayListForDB( limited_types ) + ';' ).fetchall()
    
    def _GetSessions( self ):
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'DELETE FROM sessions WHERE ? > expiry;', ( now, ) )
        
        sessions = []
        
        results = self._c.execute( 'SELECT session_key, service_id, account_id, expiry FROM sessions;' ).fetchall()
        
        service_ids_to_service_keys = {}
        
        account_ids_to_accounts = {}
        
        for ( session_key, service_id, account_id, expires ) in results:
            
            if service_id not in service_ids_to_service_keys: service_ids_to_service_keys[ service_id ] = self._GetServiceKey( service_id )
            
            service_key = service_ids_to_service_keys[ service_id ]
            
            if account_id not in account_ids_to_accounts:
                
                account_key = self._GetAccountKeyFromAccountId( account_id )
                
                account = self._GetAccount( account_key )
                
                account_ids_to_accounts[ account_id ] = account
                
            
            account = account_ids_to_accounts[ account_id ]
            
            sessions.append( ( session_key, service_key, account, expires ) )
            
        
        return sessions
        
    
    def _GetStats( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        stats = {}
        
        ( stats[ 'num_accounts' ], ) = self._c.execute( 'SELECT COUNT( * ) FROM accounts WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        ( stats[ 'num_banned' ], ) = self._c.execute( 'SELECT COUNT( * ) FROM bans WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return stats
        
    
    def _GetTag( self, tag_id ):
        
        result = self._c.execute( 'SELECT tag FROM tags WHERE tag_id = ?;', ( tag_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Tag error in database' )
        
        ( tag, ) = result
        
        return tag
        
    
    def _GetTagId( self, tag ):
        
        tag = HydrusTags.CleanTag( tag )
        
        HydrusTags.CheckTagNotEmpty( tag )
        
        result = self._c.execute( 'SELECT tag_id FROM tags WHERE tag = ?;', ( tag, ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO tags ( tag ) VALUES ( ? );', ( tag, ) )
            
            tag_id = self._c.lastrowid
            
            return tag_id
            
        else:
            
            ( tag_id, ) = result
            
            return tag_id
            
        
    
    def _GetTagPetition( self, service_id ):
        
        content_types = [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ]
        
        random.shuffle( content_types )
        
        for content_type in content_types:
            
            contents = []
            
            if content_type == HC.CONTENT_TYPE_MAPPINGS:
                
                action = HC.CONTENT_UPDATE_PETITION
                
                result = self._c.execute( 'SELECT account_id, reason_id FROM petitioned_mappings WHERE service_id = ? ORDER BY RANDOM() LIMIT 1;', ( service_id, ) ).fetchone()
                
                if result is None: continue
                
                ( account_id, reason_id ) = result
                
                tag_ids_to_hash_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT tag_id, hash_id FROM petitioned_mappings WHERE service_id = ? AND account_id = ? AND reason_id = ?;', ( service_id, account_id, reason_id ) ) )
                
                for ( tag_id, hash_ids ) in tag_ids_to_hash_ids.items():
                    
                    tag = self._GetTag( tag_id )
                    
                    hashes = self._GetHashes( hash_ids )
                    
                    content = HydrusData.Content( content_type, ( tag, hashes ) )
                    
                    contents.append( content )
                    
                
            elif content_type in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                if content_type == HC.CONTENT_TYPE_TAG_SIBLINGS: result = self._c.execute( 'SELECT account_id, reason_id, status FROM tag_siblings WHERE service_id = ? AND status IN ( ?, ? ) ORDER BY RANDOM() LIMIT 1;', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
                elif content_type == HC.CONTENT_TYPE_TAG_PARENTS: result = self._c.execute( 'SELECT account_id, reason_id, status FROM tag_parents WHERE service_id = ? AND status IN ( ?, ? ) ORDER BY RANDOM() LIMIT 1;', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
                
                if result is None: continue
                
                ( account_id, reason_id, status ) = result
                
                if status == HC.PENDING: action = HC.CONTENT_UPDATE_PEND
                elif status == HC.PETITIONED: action = HC.CONTENT_UPDATE_PETITION
                
                if content_type == HC.CONTENT_TYPE_TAG_SIBLINGS: tag_pairs = self._c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_siblings WHERE service_id = ? AND account_id = ? AND reason_id = ? AND status = ?;', ( service_id, account_id, reason_id, status ) ).fetchall()
                elif content_type == HC.CONTENT_TYPE_TAG_PARENTS: tag_pairs = self._c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_parents WHERE service_id = ? AND account_id = ? AND reason_id = ? AND status = ?;', ( service_id, account_id, reason_id, status ) ).fetchall()
                
                for ( old_tag_id, new_tag_id ) in tag_pairs:
                    
                    old_tag = self._GetTag( old_tag_id )
                    
                    new_tag = self._GetTag( new_tag_id )
                    
                    content = HydrusData.Content( content_type, ( old_tag, new_tag ) )
                    
                    contents.append( content )
                    
                
            
            account_key = self._GetAccountKeyFromAccountId( account_id )
            
            petitioner_account_identifier = HydrusData.AccountIdentifier( account_key = account_key )
            
            reason = self._GetReason( reason_id )
            
            return HydrusData.ServerToClientPetition( action, petitioner_account_identifier, reason, contents )
            
        
        raise HydrusExceptions.NotFoundException( 'No petitions!' )
        
    
    def _GetThumbnail( self, hash ):
        
        path = ServerFiles.GetThumbnailPath( hash )
        
        with open( path, 'rb' ) as f: thumbnail = f.read()
        
        return thumbnail
        
    
    def _GetUpdateEnds( self ):
        
        service_ids = self._GetServiceIds( HC.REPOSITORIES )
        
        results = {}
        
        for service_id in service_ids:
            
            ( end, ) = self._c.execute( 'SELECT end FROM update_cache WHERE service_id = ? ORDER BY end DESC LIMIT 1;', ( service_id, ) ).fetchone()
            
            service_key = self._GetServiceKey( service_id )
            
            results[ service_key ] = end
            
        
        return results
        
    
    def _InitAdmin( self ):
        
        if self._c.execute( 'SELECT 1 FROM accounts;' ).fetchone() is not None: raise HydrusExceptions.ForbiddenException( 'This server is already initialised!' )
        
        num = 1
        
        title = 'server admin'
        
        ( registration_key, ) = self._GenerateRegistrationKeys( HC.SERVER_ADMIN_KEY, num, title )
        
        access_key = self._GetAccessKey( registration_key )
        
        return access_key
        
    
    def _InitCaches( self ):
        
        self._over_monthly_data = False
        self._services_over_monthly_data = set()
        
    
    def _InitExternalDatabases( self ):
        
        self._db_filenames[ 'external_mappings' ] = 'server.mappings.db'
        self._db_filenames[ 'external_master' ] = 'server.master.db'
        
    
    def _IterateFileUpdateContentData( self, service_id, begin, end ):
        
        #
        
        files_info = [ ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) for ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in self._c.execute( 'SELECT hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words FROM file_map, files_info USING ( hash_id ) WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ) ]
        
        for block_of_files_info in HydrusData.SplitListIntoChunks( files_info, 10000 ):
            
            hash_ids = { file_info[0] for file_info in block_of_files_info }
            
            hash_ids_to_hashes = self._GetHashIdsToHashes( hash_ids )
            
            yield ( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, block_of_files_info, hash_ids_to_hashes, len( hash_ids ) )
            
        
        #
        
        deleted_files_info = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM file_petitions WHERE service_id = ? AND timestamp BETWEEN ? AND ? AND status = ?;', ( service_id, begin, end, HC.DELETED ) ) ]
        
        for block_of_deleted_files_info in HydrusData.SplitListIntoChunks( deleted_files_info, 10000 ):
            
            hash_ids = block_of_deleted_files_info
            
            hash_ids_to_hashes = self._GetHashIdsToHashes( hash_ids )
            
            yield ( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, block_of_deleted_files_info, hash_ids_to_hashes, len( hash_ids ) )
            
        
    
    def _IterateTagUpdateContentData( self, service_id, begin, end ):
        
        # mappings
        
        mappings_dict = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT tag, hash_id FROM tags, mappings USING ( tag_id ) WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ) )
        
        for ( tag, hash_ids ) in mappings_dict.items():
            
            for block_of_hash_ids in HydrusData.SplitListIntoChunks( hash_ids, 10000 ):
                
                hash_ids_to_hashes = self._GetHashIdsToHashes( block_of_hash_ids )
                
                yield ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, [ ( tag, block_of_hash_ids ) ], hash_ids_to_hashes, len( block_of_hash_ids ) )
                
            
        
        #
        
        deleted_mappings_dict = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT tag, hash_id FROM tags, deleted_mappings USING ( tag_id ) WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ) )
        
        for ( tag, hash_ids ) in deleted_mappings_dict.items():
            
            for block_of_hash_ids in HydrusData.SplitListIntoChunks( hash_ids, 10000 ):
                
                hash_ids_to_hashes = self._GetHashIdsToHashes( block_of_hash_ids )
                
                yield ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, [ ( tag, block_of_hash_ids ) ], hash_ids_to_hashes, len( block_of_hash_ids ) )
                
            
        
        # tag siblings
        
        tag_sibling_ids = self._c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_siblings WHERE service_id = ? AND status = ? AND timestamp BETWEEN ? AND ?;', ( service_id, HC.CURRENT, begin, end ) ).fetchall()
        
        for block_of_tag_sibling_ids in HydrusData.SplitListIntoChunks( tag_sibling_ids, 10000 ):
            
            tag_siblings = [ ( self._GetTag( old_tag_id ), self._GetTag( new_tag_id ) ) for ( old_tag_id, new_tag_id ) in block_of_tag_sibling_ids ]
            
            hash_ids_to_hashes = {}
            
            yield ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, tag_siblings, hash_ids_to_hashes, len( tag_siblings ) )
            
        
        #
        
        deleted_tag_sibling_ids = self._c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_siblings WHERE service_id = ? AND status = ? AND timestamp BETWEEN ? AND ?;', ( service_id, HC.DELETED, begin, end ) ).fetchall()
        
        for block_of_deleted_tag_sibling_ids in HydrusData.SplitListIntoChunks( deleted_tag_sibling_ids, 10000 ):
            
            deleted_tag_siblings = [ ( self._GetTag( old_tag_id ), self._GetTag( new_tag_id ) ) for ( old_tag_id, new_tag_id ) in block_of_deleted_tag_sibling_ids ]
            
            hash_ids_to_hashes = {}
            
            yield ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, deleted_tag_siblings, hash_ids_to_hashes, len( deleted_tag_siblings ) )
            
        
        # tag parents
        
        tag_parent_ids = self._c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_parents WHERE service_id = ? AND status = ? AND timestamp BETWEEN ? AND ?;', ( service_id, HC.CURRENT, begin, end ) ).fetchall()
        
        for block_of_tag_parent_ids in HydrusData.SplitListIntoChunks( tag_parent_ids, 10000 ):
            
            tag_parents = [ ( self._GetTag( old_tag_id ), self._GetTag( new_tag_id ) ) for ( old_tag_id, new_tag_id ) in block_of_tag_parent_ids ]
            
            hash_ids_to_hashes = {}
            
            yield ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD, tag_parents, hash_ids_to_hashes, len( tag_parents ) )
            
        
        #
        
        deleted_tag_parent_ids = self._c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_parents WHERE service_id = ? AND status = ? AND timestamp BETWEEN ? AND ?;', ( service_id, HC.DELETED, begin, end ) ).fetchall()
        
        for block_of_deleted_tag_parent_ids in HydrusData.SplitListIntoChunks( deleted_tag_parent_ids, 10000 ):
            
            deleted_tag_parents = [ ( self._GetTag( old_tag_id ), self._GetTag( new_tag_id ) ) for ( old_tag_id, new_tag_id ) in block_of_deleted_tag_parent_ids ]
            
            hash_ids_to_hashes = {}
            
            yield ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DELETE, deleted_tag_parents, hash_ids_to_hashes, len( deleted_tag_parents ) )
            
        
    
    def _ManageDBError( self, job, e ):
        
        ( exception_type, value, tb ) = sys.exc_info()
        
        new_e = type( e )( os.linesep.join( traceback.format_exception( exception_type, value, tb ) ) )
        
        job.PutResult( new_e )
        
    
    def _ModifyAccount( self, service_key, admin_account_key, action, subject_account_keys, kwargs ):
        
        service_id = self._GetServiceId( service_key )
        
        admin_account_id = self._GetAccountId( admin_account_key )
        
        subject_account_ids = [ self._GetAccountId( subject_account_key ) for subject_account_key in subject_account_keys ]
        
        if action in ( HC.BAN, HC.SUPERBAN ):
            
            reason = kwargs[ 'reason' ]
            
            reason_id = self._GetReasonId( reason )
            
            if 'lifetime' in kwargs: lifetime = kwargs[ 'lifetime' ]
            else: lifetime = None
            
            self._Ban( service_id, action, admin_account_id, subject_account_ids, reason_id, lifetime ) # fold ban and superban together, yo
            
        else:
            
            admin_account = self._GetAccount( admin_account_key )
            
            admin_account.CheckPermission( HC.GENERAL_ADMIN ) # special case, don't let manage_users people do these:
            
            if action == HC.CHANGE_ACCOUNT_TYPE:
                
                title = kwargs[ 'title' ]
                
                account_type_id = self._GetAccountTypeId( service_id, title )
                
                self._ChangeAccountType( subject_account_ids, account_type_id )
                
            elif action == HC.ADD_TO_EXPIRES:
                
                timespan = kwargs[ 'timespan' ]
                
                self._AddToExpires( subject_account_ids, timespan )
                
            elif action == HC.SET_EXPIRES:
                
                expires = kwargs[ 'expires' ]
                
                self._SetExpires( subject_account_ids, expires )
                
            
        
    
    def _ModifyAccountTypes( self, service_key, edit_log ):
        
        service_id = self._GetServiceId( service_key )
        
        for ( action, details ) in edit_log:
            
            if action == HC.ADD:
                
                account_type = details
                
                title = account_type.GetTitle()
                
                if self._AccountTypeExists( service_id, title ): raise HydrusExceptions.ForbiddenException( 'Already found account type ' + HydrusData.ToUnicode( title ) + ' in the db for this service, so could not add!' )
                
                self._c.execute( 'INSERT OR IGNORE INTO account_types ( service_id, title, account_type ) VALUES ( ?, ?, ? );', ( service_id, title, account_type ) )
                
            elif action == HC.DELETE:
                
                ( title, new_title ) = details
                
                account_type_id = self._GetAccountTypeId( service_id, title )
                
                new_account_type_id = self._GetAccountTypeId( service_id, new_title )
                
                self._c.execute( 'UPDATE accounts SET account_type_id = ? WHERE account_type_id = ?;', ( new_account_type_id, account_type_id ) )
                self._c.execute( 'UPDATE registration_keys SET account_type_id = ? WHERE account_type_id = ?;', ( new_account_type_id, account_type_id ) )
                
                self._c.execute( 'DELETE FROM account_types WHERE account_type_id = ?;', ( account_type_id, ) )
                
            elif action == HC.EDIT:
                
                ( old_title, account_type ) = details
                
                title = account_type.GetTitle()
                
                if old_title != title and self._AccountTypeExists( service_id, title ): raise HydrusExceptions.ForbiddenException( 'Already found account type ' + HydrusData.ToUnicode( title ) + ' in the database, so could not rename ' + HydrusData.ToUnicode( old_title ) + '!' )
                
                account_type_id = self._GetAccountTypeId( service_id, old_title )
                
                self._c.execute( 'UPDATE account_types SET title = ?, account_type = ? WHERE account_type_id = ?;', ( title, account_type, account_type_id ) )
                
            
        
    
    def _ModifyServices( self, account_key, edit_log ):
        
        self._c.execute( 'COMMIT;' )
        
        if not self._fast_big_transaction_wal:
            
            self._c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
            
        
        self._c.execute( 'PRAGMA foreign_keys = ON;' )
        
        self._c.execute( 'BEGIN IMMEDIATE;' )
        
        account_id = self._GetAccountId( account_key )
        
        service_keys_to_access_keys = {}
        
        now = HydrusData.GetNow()
        
        for ( action, data ) in edit_log:
            
            if action == HC.ADD:
                
                ( service_key, service_type, options ) = data
                
                self._c.execute( 'INSERT INTO services ( service_key, type, options ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, options ) )
                
                service_id = self._c.lastrowid
                
                service_admin_account_type = HydrusData.AccountType( 'service admin', [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN ], ( None, None ) )
                
                self._c.execute( 'INSERT INTO account_types ( service_id, title, account_type ) VALUES ( ?, ?, ? );', ( service_id, 'service admin', service_admin_account_type ) )
                
                [ registration_key ] = self._GenerateRegistrationKeys( service_key, 1, 'service admin', None )
                
                access_key = self._GetAccessKey( registration_key )
                
                service_keys_to_access_keys[ service_key ] = access_key
                
                if service_type in HC.REPOSITORIES:
                    
                    update_dir = ServerFiles.GetExpectedUpdateDir( service_key )
                    
                    HydrusPaths.MakeSureDirectoryExists( update_dir )
                    
                    begin = 0
                    end = HydrusData.GetNow()
                    
                    self._CreateUpdate( service_key, begin, end )
                    
                
                self.pub_after_commit( 'action_service', service_key, 'start' )
                
            elif action == HC.DELETE:
                
                service_key = data
                
                service_id = self._GetServiceId( service_key )
                
                self._c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
                self._c.execute( 'DELETE FROM mappings WHERE service_id = ?;', ( service_id, ) )
                self._c.execute( 'DELETE FROM petitioned_mappings WHERE service_id = ?;', ( service_id, ) )
                self._c.execute( 'DELETE FROM deleted_mappings WHERE service_id = ?;', ( service_id, ) )
                
                update_dir = ServerFiles.GetExpectedUpdateDir( service_key )
                
                if os.path.exists( update_dir ):
                    
                    HydrusPaths.DeletePath( update_dir )
                    
                
                self.pub_after_commit( 'action_service', service_key, 'stop' )
                
            elif action == HC.EDIT:
                
                ( service_key, service_type, options ) = data
                
                service_id = self._GetServiceId( service_key )
                
                self._c.execute( 'UPDATE services SET options = ? WHERE service_id = ?;', ( options, service_id ) )
                
                self.pub_after_commit( 'action_service', service_key, 'restart' )
                
            
        
        self._c.execute( 'COMMIT;' )
        
        self._InitDBCursor()
        
        self._c.execute( 'BEGIN IMMEDIATE;' )
        
        return service_keys_to_access_keys
        
    
    def _ProcessUpdate( self, service_key, account_key, update ):
        
        service_id = self._GetServiceId( service_key )
        
        account_id = self._GetAccountId( account_key )
        
        account = self._GetAccount( account_key )
        
        service_type = self._GetServiceType( service_id )
        
        if service_type == HC.FILE_REPOSITORY:
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ) or account.HasPermission( HC.POST_PETITIONS ):
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveFilePetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddFilePetition
                
                for ( hashes, reason ) in update.GetContentDataIterator( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION ):
                    
                    hash_ids = self._GetHashIds( hashes )
                    
                    reason_id = self._GetReasonId( reason )
                    
                    petition_method( service_id, account_id, hash_ids, reason_id )
                    
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                for hashes in update.GetContentDataIterator( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DENY_PETITION ):
                    
                    hash_ids = self._GetHashIds( hashes )
                    
                    self._DenyFilePetition( service_id, hash_ids )
                    
                
            
        elif service_type == HC.TAG_REPOSITORY:
            
            tags = update.GetTags()
            
            hashes = update.GetHashes()
            
            #
            
            overwrite_deleted = account.HasPermission( HC.RESOLVE_PETITIONS )
            
            for ( tag, hashes ) in update.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND ):
                
                tag_id = self._GetTagId( tag )
                
                hash_ids = self._GetHashIds( hashes )
                
                self._AddMappings( service_id, account_id, tag_id, hash_ids, overwrite_deleted )
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ) or account.HasPermission( HC.POST_PETITIONS ):
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveMappingPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddMappingPetition
                
                for ( tag, hashes, reason ) in update.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION ):
                    
                    tag_id = self._GetTagId( tag )
                    
                    hash_ids = self._GetHashIds( hashes )
                    
                    reason_id = self._GetReasonId( reason )
                    
                    petition_method( service_id, account_id, tag_id, hash_ids, reason_id )
                    
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                for ( tag, hashes ) in update.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DENY_PETITION ):
                    
                    tag_id = self._GetTagId( tag )
                    
                    hash_ids = self._GetHashIds( hashes )
                    
                    self._DenyMappingPetition( service_id, tag_id, hash_ids )
                    
                
            
            #
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ) or account.HasPermission( HC.POST_PETITIONS ):
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveTagSiblingPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddTagSiblingPetition
                
                for ( ( old_tag, new_tag ), reason ) in update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PEND ):
                    
                    old_tag_id = self._GetTagId( old_tag )
                    new_tag_id = self._GetTagId( new_tag )
                    
                    reason_id = self._GetReasonId( reason )
                    
                    petition_method( service_id, account_id, old_tag_id, new_tag_id, reason_id, HC.PENDING )
                    
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveTagSiblingPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddTagSiblingPetition
                
                for ( ( old_tag, new_tag ), reason ) in update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION ):
                    
                    old_tag_id = self._GetTagId( old_tag )
                    new_tag_id = self._GetTagId( new_tag )
                    
                    reason_id = self._GetReasonId( reason )
                    
                    petition_method( service_id, account_id, old_tag_id, new_tag_id, reason_id, HC.PETITIONED )
                    
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                for ( old_tag, new_tag ) in update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DENY_PEND ):
                    
                    old_tag_id = self._GetTagId( old_tag )
                    
                    new_tag_id = self._GetTagId( new_tag )
                    
                    self._DenyTagSiblingPetition( service_id, old_tag_id, new_tag_id, HC.CONTENT_UPDATE_DENY_PEND )
                    
                
                for ( old_tag, new_tag ) in update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DENY_PETITION ):
                    
                    old_tag_id = self._GetTagId( old_tag )
                    
                    new_tag_id = self._GetTagId( new_tag )
                    
                    self._DenyTagSiblingPetition( service_id, old_tag_id, new_tag_id, HC.CONTENT_UPDATE_DENY_PETITION )
                    
                
            
            #
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ) or account.HasPermission( HC.POST_PETITIONS ):
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveTagParentPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddTagParentPetition
                
                for ( ( old_tag, new_tag ), reason ) in update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PEND ):
                    
                    old_tag_id = self._GetTagId( old_tag )
                    new_tag_id = self._GetTagId( new_tag )
                    
                    reason_id = self._GetReasonId( reason )
                    
                    petition_method( service_id, account_id, old_tag_id, new_tag_id, reason_id, HC.PENDING )
                    
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveTagParentPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddTagParentPetition
                
                for ( ( old_tag, new_tag ), reason ) in update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION ):
                    
                    old_tag_id = self._GetTagId( old_tag )
                    new_tag_id = self._GetTagId( new_tag )
                    
                    reason_id = self._GetReasonId( reason )
                    
                    petition_method( service_id, account_id, old_tag_id, new_tag_id, reason_id, HC.PETITIONED )
                    
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                for ( old_tag, new_tag ) in update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DENY_PEND ):
                    
                    old_tag_id = self._GetTagId( old_tag )
                    
                    new_tag_id = self._GetTagId( new_tag )
                    
                    self._DenyTagParentPetition( service_id, old_tag_id, new_tag_id, HC.CONTENT_UPDATE_DENY_PEND )
                    
                
                for ( old_tag, new_tag ) in update.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DENY_PETITION ):
                    
                    old_tag_id = self._GetTagId( old_tag )
                    
                    new_tag_id = self._GetTagId( new_tag )
                    
                    self._DenyTagParentPetition( service_id, old_tag_id, new_tag_id, HC.CONTENT_UPDATE_DENY_PETITION )
                    
                
            
        
    
    def _Read( self, action, *args, **kwargs ):
        
        if action == 'access_key': result = self._GetAccessKey( *args, **kwargs )
        elif action == 'account': result = self._GetAccount( *args, **kwargs )
        elif action == 'account_info': result = self._GetAccountInfo( *args, **kwargs )
        elif action == 'account_key_from_access_key': result = self._GetAccountKeyFromAccessKey( *args, **kwargs )
        elif action == 'account_key_from_identifier': result = self._GetAccountKeyFromIdentifier( *args, **kwargs )
        elif action == 'account_types': result = self._GetAccountTypes( *args, **kwargs )
        elif action == 'immediate_content_update': result = self._GenerateImmediateContentUpdate( *args, **kwargs )
        elif action == 'init': result = self._InitAdmin( *args, **kwargs  )
        elif action == 'ip': result = self._GetIPTimestamp( *args, **kwargs )
        elif action == 'messaging_sessions': result = self._GetMessagingSessions( *args, **kwargs )
        elif action == 'num_petitions': result = self._GetNumPetitions( *args, **kwargs )
        elif action == 'petition': result = self._GetPetition( *args, **kwargs )
        elif action == 'registration_keys': result = self._GenerateRegistrationKeys( *args, **kwargs )
        elif action == 'service_keys': result = self._GetServiceKeys( *args, **kwargs )
        elif action == 'service_info': result = self._GetServiceInfo( *args, **kwargs )
        elif action == 'services_info': result = self._GetServicesInfo( *args, **kwargs )
        elif action == 'sessions': result = self._GetSessions( *args, **kwargs )
        elif action == 'stats': result = self._GetStats( *args, **kwargs )
        elif action == 'update_ends': result = self._GetUpdateEnds( *args, **kwargs )
        elif action == 'verify_access_key': result = self._VerifyAccessKey( *args, **kwargs )
        else: raise Exception( 'db received an unknown read command: ' + action )
        
        return result
        
    
    def _RewardAccounts( self, service_id, score_type, scores ):
        
        self._c.executemany( 'INSERT OR IGNORE INTO account_scores ( service_id, account_id, score_type, score ) VALUES ( ?, ?, ?, ? );', [ ( service_id, account_id, score_type, 0 ) for ( account_id, score ) in scores ] )
        
        self._c.executemany( 'UPDATE account_scores SET score = score + ? WHERE service_id = ? AND account_id = ? and score_type = ?;', [ ( score, service_id, account_id, score_type ) for ( account_id, score ) in scores ] )
        
    
    def _RewardFilePetitioners( self, service_id, hash_ids, multiplier ):
        
        scores = [ ( account_id, count * multiplier ) for ( account_id, count ) in self._c.execute( 'SELECT account_id, COUNT( * ) FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ' AND status = ? GROUP BY account_id;', ( service_id, HC.PETITIONED ) ) ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RewardMappingPetitioners( self, service_id, tag_id, hash_ids, multiplier ):
        
        scores = [ ( account_id, count * multiplier ) for ( account_id, count ) in self._c.execute( 'SELECT account_id, COUNT( * ) FROM petitioned_mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ' GROUP BY account_id;', ( service_id, tag_id ) ) ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RewardTagParentPetitioners( self, service_id, old_tag_id, new_tag_id, multiplier ):
        
        hash_ids_with_old_tag = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, old_tag_id ) ) }
        hash_ids_with_new_tag = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, new_tag_id ) ) }
        
        score = len( hash_ids_with_old_tag.intersection( hash_ids_with_new_tag ) )
        
        weighted_score = score * multiplier
        
        account_ids = [ account_id for ( account_id, ) in self._c.execute( 'SELECT account_id FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status IN ( ?, ? );', ( service_id, old_tag_id, new_tag_id, HC.PENDING, HC.PETITIONED ) ) ]
        
        scores = [ ( account_id, weighted_score ) for account_id in account_ids ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _RewardTagSiblingPetitioners( self, service_id, old_tag_id, new_tag_id, multiplier ):
        
        hash_ids_with_old_tag = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, old_tag_id ) ) }
        hash_ids_with_new_tag = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, new_tag_id ) ) }
        
        score = len( hash_ids_with_old_tag.intersection( hash_ids_with_new_tag ) )
        
        weighted_score = score * multiplier
        
        account_ids = [ account_id for ( account_id, ) in self._c.execute( 'SELECT account_id FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status IN ( ?, ? );', ( service_id, old_tag_id, new_tag_id, HC.PENDING, HC.PETITIONED ) ) ]
        
        scores = [ ( account_id, weighted_score ) for account_id in account_ids ]
        
        self._RewardAccounts( service_id, HC.SCORE_PETITION, scores )
        
    
    def _SetExpires( self, account_ids, expires ): self._c.execute( 'UPDATE accounts SET expires = ? WHERE account_id IN ' + HydrusData.SplayListForDB( account_ids ) + ';', ( expires, ) )
    
    def _UnbanKey( self, service_id, account_id ): self._c.execute( 'DELETE FROM bans WHERE service_id = ? AND account_id = ?;', ( account_id, ) )
    
    def _UpdateDB( self, version ):
        
        HydrusData.Print( 'The server is updating to version ' + str( version + 1 ) )
        
        if version == 198:
            
            HydrusData.Print( 'exporting mappings to external db' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mappings ( service_id INTEGER, tag_id INTEGER, hash_id INTEGER, account_id INTEGER, timestamp INTEGER, PRIMARY KEY( service_id, tag_id, hash_id ) );' )
            
            self._c.execute( 'INSERT INTO external_mappings.mappings SELECT * FROM main.mappings;' )
            
            self._c.execute( 'DROP TABLE main.mappings;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mapping_petitions ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY( service_id, account_id, tag_id, hash_id, status ) );' )
            
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
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mapping_petitions ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY( service_id, account_id, tag_id, hash_id, status ) ) WITHOUT ROWID;' )
            
            self._c.execute( 'INSERT INTO mapping_petitions SELECT * FROM mapping_petitions_old;' )
            
            self._c.execute( 'DROP TABLE mapping_petitions_old;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.mappings ( service_id INTEGER, tag_id INTEGER, hash_id INTEGER, account_id INTEGER, timestamp INTEGER, PRIMARY KEY( service_id, tag_id, hash_id ) ) WITHOUT ROWID;' )
            
            self._c.execute( 'INSERT INTO mappings SELECT * FROM mappings_old;' )
            
            self._c.execute( 'DROP TABLE mappings_old;' )
            
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mapping_petitions_service_id_account_id_reason_id_tag_id_index ON mapping_petitions ( service_id, account_id, reason_id, tag_id );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mapping_petitions_service_id_tag_id_hash_id_index ON mapping_petitions ( service_id, tag_id, hash_id );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mapping_petitions_service_id_status_index ON mapping_petitions ( service_id, status );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mapping_petitions_service_id_timestamp_index ON mapping_petitions ( service_id, timestamp );' )
            
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mappings_account_id_index ON mappings ( account_id );' )
            self._c.execute( 'CREATE INDEX IF NOT EXISTS external_mappings.mappings_timestamp_index ON mappings ( timestamp );' )
            
            #
            
            self._c.execute( 'COMMIT;' )
            
            self._CloseDBCursor()
            
            try:
                
                for filename in self._db_filenames.values():
                    
                    HydrusData.Print( 'vacuuming ' + filename )
                    
                    db_path = os.path.join( self._db_dir, filename )
                    
                    if HydrusDB.CanVacuum( db_path ):
                        
                        HydrusDB.VacuumDB( db_path )
                        
                    
                
            finally:
                
                self._InitDBCursor()
                
                self._c.execute( 'BEGIN IMMEDIATE;' )
                
            
        
        if version == 202:
            
            self._c.execute( 'DELETE FROM analyze_timestamps;' )
            
        
        if version == 207:
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.petitioned_mappings ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY( service_id, tag_id, hash_id, account_id ) ) WITHOUT ROWID;' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_mappings.deleted_mappings ( service_id INTEGER, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, PRIMARY KEY( service_id, tag_id, hash_id ) ) WITHOUT ROWID;' )
            
            #
            
            self._c.execute( 'INSERT INTO petitioned_mappings ( service_id, account_id, tag_id, hash_id, reason_id ) SELECT service_id, account_id, tag_id, hash_id, reason_id FROM mapping_petitions WHERE status = ?;', ( HC.PETITIONED, ) )
            self._c.execute( 'INSERT INTO deleted_mappings ( service_id, account_id, tag_id, hash_id, reason_id, timestamp ) SELECT service_id, account_id, tag_id, hash_id, reason_id, timestamp FROM mapping_petitions WHERE status = ?;', ( HC.DELETED, ) )
            
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
            
        
        HydrusData.Print( 'The server has updated to version ' + str( version + 1 ) )
        
        self._c.execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
    
    def _VerifyAccessKey( self, service_key, access_key ):
        
        service_id = self._GetServiceId( service_key )
        
        result = self._c.execute( 'SELECT 1 FROM accounts WHERE service_id = ? AND hashed_access_key = ?;', ( service_id, sqlite3.Binary( hashlib.sha256( access_key ).digest() ) ) ).fetchone()
        
        if result is None:
            
            result = self._c.execute( 'SELECT 1 FROM registration_keys WHERE service_id = ? AND access_key = ?;', ( service_id, sqlite3.Binary( access_key ) ) ).fetchone()
            
            if result is None: return False
            
        
        return True
        
    
    def _Write( self, action, *args, **kwargs ):
        
        if action == 'account': result = self._ModifyAccount( *args, **kwargs )
        elif action == 'account_types': result = self._ModifyAccountTypes( *args, **kwargs )
        elif action == 'analyze': result = self._Analyze( *args, **kwargs )
        elif action == 'backup': result = self._Backup( *args, **kwargs )
        elif action == 'check_data_usage': result = self._CheckDataUsage( *args, **kwargs )
        elif action == 'check_monthly_data': result = self._CheckMonthlyData( *args, **kwargs )
        elif action == 'clear_bans': result = self._ClearBans( *args, **kwargs )
        elif action == 'create_update': result = self._CreateUpdate( *args, **kwargs )
        elif action == 'delete_orphans': result = self._DeleteOrphans( *args, **kwargs )
        elif action == 'file': result = self._AddFile( *args, **kwargs )
        elif action == 'flush_requests_made': result = self._FlushRequestsMade( *args, **kwargs )
        elif action == 'messaging_session': result = self._AddMessagingSession( *args, **kwargs )
        elif action == 'news': result = self._AddNews( *args, **kwargs )
        elif action == 'services': result = self._ModifyServices( *args, **kwargs )
        elif action == 'session': result = self._AddSession( *args, **kwargs )
        elif action == 'update': result = self._ProcessUpdate( *args, **kwargs )
        else: raise Exception( 'db received an unknown write command: ' + action )
        
        return result
        
    
    def GetFilesDir( self ):
        
        return self._files_dir
        
    
    def GetSSLPaths( self ):
        
        return ( self._ssl_cert_path, self._ssl_key_path )
        
    
    def GetUpdatesDir( self ):
        
        return self._updates_dir
        
    
