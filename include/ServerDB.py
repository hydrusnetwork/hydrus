import collections
import dircache
import hashlib
import httplib
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
import HydrusNATPunch
import HydrusServer
import itertools
import os
import Queue
import random
import ServerConstants as SC
import shutil
import sqlite3
import sys
import threading
import time
import traceback
import yaml
import wx

class FileDB( object ):
    
    def _AddFile( self, c, service_key, account_key, file_dict ):
        
        service_id = self._GetServiceId( c, service_key )
        
        account_id = self._GetAccountId( c, account_key )
        
        hash = file_dict[ 'hash' ]
        
        hash_id = self._GetHashId( c, hash )
        
        now = HC.GetNow()
        
        if c.execute( 'SELECT 1 FROM file_map WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone() is None or c.execute( 'SELECT 1 FROM file_petitions WHERE service_id = ? AND hash_id = ? AND status = ?;', ( service_id, hash_id, HC.DELETED ) ).fetchone() is None:
            
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
            
            options = self._GetOptions( c, service_key )
            
            max_storage = options[ 'max_storage' ]
            
            if max_storage is not None:
                
                # this is wrong! no service_id in files_info. need to cross with file_map or w/e
                ( current_storage, ) = c.execute( 'SELECT SUM( size ) FROM file_map, files_info USING ( hash_id ) WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                if current_storage + size > max_storage: raise HydrusExceptions.ForbiddenException( 'The service is full! It cannot take any more files!' )
                
            
            source_path = file_dict[ 'path' ]
            
            dest_path = SC.GetExpectedPath( 'file', hash )
            
            if not os.path.exists( dest_path ): shutil.move( source_path, dest_path )
            
            if 'thumbnail' in file_dict:
                
                thumbnail_dest_path = SC.GetExpectedPath( 'thumbnail', hash )
                
                if not os.path.exists( thumbnail_dest_path ):
                    
                    thumbnail = file_dict[ 'thumbnail' ]
                    
                    with open( thumbnail_dest_path, 'wb' ) as f: f.write( thumbnail )
                    
                
            
            if c.execute( 'SELECT 1 FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone() is None:
                
                c.execute( 'INSERT OR IGNORE INTO files_info ( hash_id, size, mime, width, height, duration, num_frames, num_words ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ? );', ( hash_id, size, mime, width, height, duration, num_frames, num_words ) )
                
            
            c.execute( 'INSERT OR IGNORE INTO file_map ( service_id, hash_id, account_id, timestamp ) VALUES ( ?, ?, ?, ? );', ( service_id, hash_id, account_id, now ) )
            
            if options[ 'log_uploader_ips' ]:
                
                ip = file_dict[ 'ip' ]
                
                c.execute( 'INSERT INTO ip_addresses ( service_id, hash_id, ip, timestamp ) VALUES ( ?, ?, ?, ? );', ( service_id, hash_id, ip, now ) )
                
            
        
    
    def _AddFilePetition( self, c, service_id, account_id, hash_ids, reason_id ):
        
        self._ApproveOptimisedFilePetition( c, service_id, account_id, hash_ids )
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_map WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) ]
        
        # this clears out any old reasons, if the user wants to overwrite them
        c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND account_id = ? AND hash_id IN ' + HC.SplayListForDB( valid_hash_ids ) + ' AND status = ?;', ( service_id, account_id, HC.PETITIONED ) )
        
        now = HC.GetNow()
        
        c.executemany( 'INSERT OR IGNORE INTO file_petitions ( service_id, account_id, hash_id, reason_id, timestamp, status ) VALUES ( ?, ?, ?, ?, ?, ? );', [ ( service_id, account_id, hash_id, reason_id, now, HC.PETITIONED ) for hash_id in valid_hash_ids ] )
        
    
    def _ApproveFilePetition( self, c, service_id, account_id, hash_ids, reason_id ):
        
        self._ApproveOptimisedFilePetition( c, service_id, account_id, hash_ids )
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_map WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) ]
        
        self._RewardFilePetitioners( c, service_id, valid_hash_ids, 1 )
        
        self._DeleteFiles( c, service_id, account_id, valid_hash_ids, reason_id )
        
    
    def _ApproveOptimisedFilePetition( self, c, service_id, account_id, hash_ids ):
        
        ( biggest_end, ) = c.execute( 'SELECT end FROM update_cache ORDER BY end DESC LIMIT 1;' ).fetchone()
        
        c.execute( 'DELETE FROM file_map WHERE service_id = ? AND account_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND timestamp > ?;', ( service_id, account_id, biggest_end ) )
        
    
    def _DeleteFiles( self, c, service_id, account_id, hash_ids, reason_id ):
        
        splayed_hash_ids = HC.SplayListForDB( hash_ids )
        
        affected_timestamps = [ timestamp for ( timestamp, ) in c.execute( 'SELECT DISTINCT timestamp FROM file_map WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) ) ]
        
        c.execute( 'DELETE FROM file_map WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
        c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
        now = HC.GetNow()
        
        c.executemany( 'INSERT OR IGNORE INTO file_petitions ( service_id, account_id, hash_id, reason_id, timestamp, status ) VALUES ( ?, ?, ?, ?, ?, ? );', ( ( service_id, account_id, hash_id, reason_id, now, HC.DELETED ) for hash_id in hash_ids ) )
        
        self._RefreshUpdateCache( c, service_id, affected_timestamps )
        
    
    def _DenyFilePetition( self, c, service_id, hash_ids ):
        
        self._RewardFilePetitioners( c, service_id, hash_ids, -1 )
        
        c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
    
    def _GenerateFileUpdate( self, c, service_id, begin, end ):
        
        hash_ids = set()
        
        service_data = {}
        content_data = HC.GetEmptyDataDict()
        
        #
        
        files_info = [ ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) for ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in c.execute( 'SELECT hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words FROM file_map, files_info USING ( hash_id ) WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ) ]
        
        hash_ids.update( ( file_info[0] for file_info in files_info ) )
        
        content_data[ HC.CONTENT_DATA_TYPE_FILES ][ HC.CONTENT_UPDATE_ADD ] = files_info
        
        #
        
        deleted_files_info = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_petitions WHERE service_id = ? AND timestamp BETWEEN ? AND ? AND status = ?;', ( service_id, begin, end, HC.DELETED ) ) ]
        
        hash_ids.update( deleted_files_info )
        
        content_data[ HC.CONTENT_DATA_TYPE_FILES ][ HC.CONTENT_UPDATE_DELETE ] = deleted_files_info
        
        #
        
        news = c.execute( 'SELECT news, timestamp FROM news WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ).fetchall()
        
        service_data[ HC.SERVICE_UPDATE_BEGIN_END ] = ( begin, end )
        service_data[ HC.SERVICE_UPDATE_NEWS ] = news
        
        #
        
        hash_ids_to_hashes = self._GetHashIdsToHashes( c, hash_ids )
        
        return HC.ServerToClientUpdate( service_data, content_data, hash_ids_to_hashes )
        
    
    def _GenerateHashIdsEfficiently( self, c, hashes ):
        
        if type( hashes ) != list: hashes = list( hashes )
        
        hashes_not_in_db = set( hashes )
        
        for i in range( 0, len( hashes ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            hashes_subset = hashes[ i : i + 250 ]
            
            hashes_not_in_db.difference_update( [ hash for ( hash, ) in c.execute( 'SELECT hash FROM hashes WHERE hash IN (' + ','.join( '?' * len( hashes_subset ) ) + ');', [ sqlite3.Binary( hash ) for hash in hashes_subset ] ) ] )
            
        
        if len( hashes_not_in_db ) > 0: c.executemany( 'INSERT INTO hashes ( hash ) VALUES( ? );', [ ( sqlite3.Binary( hash ), ) for hash in hashes_not_in_db ] )
        
    
    def _GetFile( self, hash ):
        
        path = SC.GetPath( 'file', hash )
        
        with open( path, 'rb' ) as f: file = f.read()
        
        return file
        
    
    def _GetFilePetition( self, c, service_id ):
        
        result = c.execute( 'SELECT DISTINCT account_id, reason_id FROM file_petitions WHERE service_id = ? AND status = ? ORDER BY RANDOM() LIMIT 1;', ( service_id, HC.PETITIONED ) ).fetchone()
        
        if result is None: raise HydrusExceptions.NotFoundException( 'No petitions!' )
        
        ( account_id, reason_id ) = result
        
        account_key = self._GetAccountKeyFromAccountId( c, account_id )
        
        petitioner_account_identifier = HC.AccountIdentifier( account_key = account_key )
        
        reason = self._GetReason( c, reason_id )
        
        hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_petitions WHERE service_id = ? AND account_id = ? AND reason_id = ? AND status = ?;', ( service_id, account_id, reason_id, HC.PETITIONED ) ) ]
        
        hashes = self._GetHashes( c, hash_ids )
        
        petition_data = hashes
        
        return HC.ServerToClientPetition( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, petitioner_account_identifier, petition_data, reason )
        
    
    def _GetHash( self, c, hash_id ):
        
        result = c.execute( 'SELECT hash FROM hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None: raise Exception( 'File hash error in database' )
        
        ( hash, ) = result
        
        return hash
        
    
    def _GetHashes( self, c, hash_ids ): return [ hash for ( hash, ) in c.execute( 'SELECT hash FROM hashes WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';' ) ]
    
    def _GetHashId( self, c, hash ):
        
        result = c.execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( sqlite3.Binary( hash ), ) )
            
            hash_id = c.lastrowid
            
            return hash_id
            
        else:
            
            ( hash_id, ) = result
            
            return hash_id
            
        
    
    def _GetHashIds( self, c, hashes ):
        
        hash_ids = []
        
        if type( hashes ) == type( set() ): hashes = list( hashes )
        
        for i in range( 0, len( hashes ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            hashes_subset = hashes[ i : i + 250 ]
            
            hash_ids.extend( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM hashes WHERE hash IN (' + ','.join( '?' * len( hashes_subset ) ) + ');', [ sqlite3.Binary( hash ) for hash in hashes_subset ] ) ] )
            
        
        if len( hashes ) > len( hash_ids ):
            
            if len( set( hashes ) ) > len( hash_ids ):
                
                # must be some new hashes the db has not seen before, so let's generate them as appropriate
                
                self._GenerateHashIdsEfficiently( c, hashes )
                
                hash_ids = self._GetHashIds( c, hashes )
                
            
        
        return hash_ids
        
    
    def _GetHashIdsToHashes( self, c, hash_ids ): return { hash_id : hash for ( hash_id, hash ) in c.execute( 'SELECT hash_id, hash FROM hashes WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';' ) }
    
    def _GetIPTimestamp( self, c, service_key, hash ):
        
        service_id = self._GetServiceId( c, service_key )
        
        hash_id = self._GetHashId( c, hash )
        
        result = c.execute( 'SELECT ip, timestamp FROM ip_addresses WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
        
        if result is None: raise HydrusExceptions.ForbiddenException( 'Did not find ip information for that hash.' )
        
        return result
        
    
    def _GetThumbnail( self, hash ):
        
        path = SC.GetPath( 'thumbnail', hash )
        
        with open( path, 'rb' ) as f: thumbnail = f.read()
        
        return thumbnail
        
    
    def _RewardFilePetitioners( self, c, service_id, hash_ids, multiplier ):
        
        scores = [ ( account_id, count * multiplier ) for ( account_id, count ) in c.execute( 'SELECT account_id, COUNT( * ) FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ? GROUP BY account_id;', ( service_id, HC.PETITIONED ) ) ]
        
        self._RewardAccounts( c, service_id, HC.SCORE_PETITION, scores )
        
    
class MessageDB( object ):
    
    def _AddMessage( self, c, contact_key, message ):
        
        try: ( service_id, account_id ) = c.execute( 'SELECT service_id, account_id FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( contact_key ), ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'Did not find that contact key for the message depot!' )
        
        message_key = os.urandom( 32 )
        
        c.execute( 'INSERT OR IGNORE INTO messages ( message_key, service_id, account_id, timestamp ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( message_key ), service_id, account_id, HC.GetNow() ) )
        
        dest_path = SC.GetExpectedPath( 'message', message_key )
        
        with open( dest_path, 'wb' ) as f: f.write( message )
        
    
    def _AddStatuses( self, c, contact_key, statuses ):
        
        try: ( service_id, account_id ) = c.execute( 'SELECT service_id, account_id FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( contact_key ), ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'Did not find that contact key for the message depot!' )
        
        now = HC.GetNow()
        
        c.executemany( 'INSERT OR REPLACE INTO message_statuses ( status_key, service_id, account_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ? );', [ ( sqlite3.Binary( status_key ), service_id, account_id, sqlite3.Binary( status ), now ) for ( status_key, status ) in statuses ] )
        
    
    def _CreateContact( self, c, service_id, account_id, public_key ):
        
        result = c.execute( 'SELECT public_key FROM contacts WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
        
        if result is not None:
            
            ( existing_public_key, ) = result
            
            if existing_public_key != public_key: raise HydrusExceptions.ForbiddenException( 'This account already has a public key!' )
            else: return
            
        
        contact_key = hashlib.sha256( public_key ).digest()
        
        c.execute( 'INSERT INTO contacts ( service_id, account_id, contact_key, public_key ) VALUES ( ?, ?, ?, ? );', ( service_id, account_id, sqlite3.Binary( contact_key ), public_key ) )
        
    
    def _GetMessage( self, c, service_id, account_id, message_key ):
        
        result = c.execute( 'SELECT 1 FROM messages WHERE service_id = ? AND account_id = ? AND message_key = ?;', ( service_id, account_id, sqlite3.Binary( message_key ) ) ).fetchone()
        
        if result is None: raise HydrusExceptions.ForbiddenException( 'Could not find that message key on message depot!' )
        
        path = SC.GetPath( 'message', message_key )
        
        with open( path, 'rb' ) as f: message = f.read()
        
        return message
        
    
    def _GetMessageInfoSince( self, c, service_id, account_id, timestamp ):
        
        message_keys = [ message_key for ( message_key, ) in c.execute( 'SELECT message_key FROM messages WHERE service_id = ? AND account_id = ? AND timestamp > ? ORDER BY timestamp ASC;', ( service_id, account_id, timestamp ) ) ]
        
        statuses = [ status for ( status, ) in c.execute( 'SELECT status FROM message_statuses WHERE service_id = ? AND account_id = ? AND timestamp > ? ORDER BY timestamp ASC;', ( service_id, account_id, timestamp ) ) ]
        
        return ( message_keys, statuses )
        
    
    def _GetPublicKey( self, c, contact_key ):
        
        ( public_key, ) = c.execute( 'SELECT public_key FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( contact_key ), ) ).fetchone()
        
        return public_key
        
    
class TagDB( object ):
    
    def _AddMappings( self, c, service_id, account_id, tag_id, hash_ids, overwrite_deleted ):
        
        if overwrite_deleted:
            
            splayed_hash_ids = HC.SplayListForDB( hash_ids )
            
            affected_timestamps = [ timestamp for ( timestamp, ) in c.execute( 'SELECT DISTINCT timestamp FROM mapping_petitions WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ' AND status = ?;', ( service_id, tag_id, HC.DELETED ) ) ]
            
            c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ' AND status = ?;', ( service_id, tag_id, HC.DELETED ) )
            
            self._RefreshUpdateCache( c, service_id, affected_timestamps )
            
        else:
            
            already_deleted = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mapping_petitions WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ?;', ( service_id, tag_id, HC.DELETED ) ) ]
            
            hash_ids = set( hash_ids ).difference( already_deleted )
            
        
        now = HC.GetNow()
        
        c.executemany( 'INSERT OR IGNORE INTO mappings ( service_id, tag_id, hash_id, account_id, timestamp ) VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, tag_id, hash_id, account_id, now ) for hash_id in hash_ids ] )
        
    
    def _AddMappingPetition( self, c, service_id, account_id, tag_id, hash_ids, reason_id ):
        
        self._ApproveMappingPetitionOptimised( c, service_id, account_id, tag_id, hash_ids )
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, tag_id ) ) ]
        
        c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND account_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( valid_hash_ids ) + ' AND STATUS = ?;', ( service_id, account_id, tag_id, HC.PETITIONED ) )
        
        now = HC.GetNow()
        
        c.executemany( 'INSERT OR IGNORE INTO mapping_petitions ( service_id, account_id, tag_id, hash_id, reason_id, timestamp, status ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', [ ( service_id, account_id, tag_id, hash_id, reason_id, now, HC.PETITIONED ) for hash_id in valid_hash_ids ] )
        
    
    def _AddTagParentPetition( self, c, service_id, account_id, old_tag_id, new_tag_id, reason_id, status ):
        
        result = c.execute( 'SELECT 1 WHERE EXISTS ( SELECT 1 FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ? );', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ).fetchone()
        
        it_already_exists = result is not None
        
        if status == HC.PENDING:
            
            if it_already_exists: return
            
        elif status == HC.PETITIONED:
            
            if not it_already_exists: return
            
        
        c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND account_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, account_id, old_tag_id, new_tag_id, status ) )
        
        now = HC.GetNow()
        
        c.execute( 'INSERT OR IGNORE INTO tag_parents ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, now ) )
        
    
    def _AddTagSiblingPetition( self, c, service_id, account_id, old_tag_id, new_tag_id, reason_id, status ):
        
        result = c.execute( 'SELECT 1 WHERE EXISTS ( SELECT 1 FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ? );', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ).fetchone()
        
        it_already_exists = result is not None
        
        if status == HC.PENDING:
            
            if it_already_exists: return
            
        elif status == HC.PETITIONED:
            
            if not it_already_exists: return
            
        
        c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND account_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, account_id, old_tag_id, new_tag_id, status ) )
        
        now = HC.GetNow()
        
        c.execute( 'INSERT OR IGNORE INTO tag_siblings ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, now ) )
        
    
    def _ApproveMappingPetition( self, c, service_id, account_id, tag_id, hash_ids, reason_id ):
        
        self._ApproveMappingPetitionOptimised( c, service_id, account_id, tag_id, hash_ids )
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, tag_id ) ) ]
        
        self._RewardMappingPetitioners( c, service_id, tag_id, valid_hash_ids, 1 )
        
        self._DeleteMappings( c, service_id, account_id, tag_id, valid_hash_ids, reason_id )
        
    
    def _ApproveMappingPetitionOptimised( self, c, service_id, account_id, tag_id, hash_ids ):
        
        ( biggest_end, ) = c.execute( 'SELECT end FROM update_cache WHERE service_id = ? ORDER BY end DESC LIMIT 1;', ( service_id, ) ).fetchone()
        
        c.execute( 'DELETE FROM mappings WHERE service_id = ? AND account_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND timestamp > ?;', ( service_id, account_id, tag_id, biggest_end ) )
        
    
    def _ApproveTagParentPetition( self, c, service_id, account_id, old_tag_id, new_tag_id, reason_id, status ):
        
        result = c.execute( 'SELECT 1 WHERE EXISTS ( SELECT 1 FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ? );', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ).fetchone()
        
        it_already_exists = result is not None
        
        if status == HC.PENDING:
            
            if it_already_exists: return
            
        elif status == HC.PETITIONED:
            
            if not it_already_exists: return
            
        
        self._RewardTagParentPetitioners( c, service_id, old_tag_id, new_tag_id, 1 )
        
        # get affected timestamps here?
        
        affected_timestamps = [ timestamp for ( timestamp, ) in c.execute( 'SELECT DISTINCT timestamp FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ) ]
        
        c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ?;', ( service_id, old_tag_id, new_tag_id ) )
        
        if status == HC.PENDING: new_status = HC.CURRENT
        elif status == HC.PETITIONED: new_status = HC.DELETED
        
        now = HC.GetNow()
        
        c.execute( 'INSERT OR IGNORE INTO tag_parents ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, old_tag_id, new_tag_id, reason_id, new_status, now ) )
        
        if len( affected_timestamps ) > 0: self._RefreshUpdateCache( c, service_id, affected_timestamps )
        
    
    def _ApproveTagSiblingPetition( self, c, service_id, account_id, old_tag_id, new_tag_id, reason_id, status ):
        
        result = c.execute( 'SELECT 1 WHERE EXISTS ( SELECT 1 FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ? );', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ).fetchone()
        
        it_already_exists = result is not None
        
        if status == HC.PENDING:
            
            if it_already_exists: return
            
        elif status == HC.PETITIONED:
            
            if not it_already_exists: return
            
        
        self._RewardTagSiblingPetitioners( c, service_id, old_tag_id, new_tag_id, 1 )
        
        # get affected timestamps here?
        
        affected_timestamps = [ timestamp for ( timestamp, ) in c.execute( 'SELECT DISTINCT timestamp FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, old_tag_id, new_tag_id, HC.CURRENT ) ) ]
        
        c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ?;', ( service_id, old_tag_id, new_tag_id ) )
        
        if status == HC.PENDING: new_status = HC.CURRENT
        elif status == HC.PETITIONED: new_status = HC.DELETED
        
        now = HC.GetNow()
        
        c.execute( 'INSERT OR IGNORE INTO tag_siblings ( service_id, account_id, old_tag_id, new_tag_id, reason_id, status, timestamp ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, old_tag_id, new_tag_id, reason_id, new_status, now ) )
        
        if len( affected_timestamps ) > 0: self._RefreshUpdateCache( c, service_id, affected_timestamps )
        
    
    def _DeleteMappings( self, c, service_id, account_id, tag_id, hash_ids, reason_id ):
        
        splayed_hash_ids = HC.SplayListForDB( hash_ids )
        
        affected_timestamps = [ timestamp for ( timestamp, ) in c.execute( 'SELECT DISTINCT timestamp FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, tag_id ) ) ]
        
        c.execute( 'DELETE FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, tag_id ) )
        c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ' AND status = ?;', ( service_id, tag_id, HC.PETITIONED ) )
        
        c.executemany( 'INSERT OR IGNORE INTO mapping_petitions ( service_id, tag_id, hash_id, account_id, reason_id, timestamp, status ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( ( service_id, tag_id, hash_id, account_id, reason_id, HC.GetNow(), HC.DELETED ) for hash_id in hash_ids ) )
        
        self._RefreshUpdateCache( c, service_id, affected_timestamps )
        
    
    def _DenyMappingPetition( self, c, service_id, tag_id, hash_ids ):
        
        self._RewardMappingPetitioners( c, service_id, tag_id, hash_ids, -1 )
        
        c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ?;', ( service_id, tag_id, HC.PETITIONED ) )
        
    
    def _DenyTagParentPetition( self, c, service_id, old_tag_id, new_tag_id, action ):
        
        self._RewardTagParentPetitioners( c, service_id, old_tag_id, new_tag_id, -1 )
        
        if action == HC.CONTENT_UPDATE_DENY_PEND: status = HC.PENDING
        elif action == HC.CONTENT_UPDATE_DENY_PETITION: status = HC.PETITIONED
        
        c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, old_tag_id, new_tag_id, status ) )
        
    
    def _DenyTagSiblingPetition( self, c, service_id, old_tag_id, new_tag_id, action ):
        
        self._RewardTagSiblingPetitioners( c, service_id, old_tag_id, new_tag_id, -1 )
        
        if action == HC.CONTENT_UPDATE_DENY_PEND: status = HC.PENDING
        elif action == HC.CONTENT_UPDATE_DENY_PETITION: status = HC.PETITIONED
        
        c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status = ?;', ( service_id, old_tag_id, new_tag_id, status ) )
        
    
    def _GenerateTagUpdate( self, c, service_id, begin, end ):
        
        service_data = {}
        content_data = HC.GetEmptyDataDict()
        
        hash_ids = set()
        
        # mappings
        
        mappings_dict = HC.BuildKeyToListDict( c.execute( 'SELECT tag, hash_id FROM tags, mappings USING ( tag_id ) WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ) )
        
        hash_ids.update( itertools.chain.from_iterable( mappings_dict.values() ) )
        
        mappings = mappings_dict.items()
        
        content_data[ HC.CONTENT_DATA_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_ADD ] = mappings
        
        #
        
        deleted_mappings_dict = HC.BuildKeyToListDict( c.execute( 'SELECT tag, hash_id FROM tags, mapping_petitions USING ( tag_id ) WHERE service_id = ? AND timestamp BETWEEN ? AND ? AND status = ?;', ( service_id, begin, end, HC.DELETED ) ) )
        
        hash_ids.update( itertools.chain.from_iterable( deleted_mappings_dict.values() ) )
        
        deleted_mappings = deleted_mappings_dict.items()
        
        content_data[ HC.CONTENT_DATA_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_DELETE ] = deleted_mappings
        
        # tag siblings
        
        tag_sibling_ids = c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_siblings WHERE service_id = ? AND status = ? AND timestamp BETWEEN ? AND ?;', ( service_id, HC.CURRENT, begin, end ) ).fetchall()
        
        tag_siblings = [ ( self._GetTag( c, old_tag_id ), self._GetTag( c, new_tag_id ) ) for ( old_tag_id, new_tag_id ) in tag_sibling_ids ]
        
        content_data[ HC.CONTENT_DATA_TYPE_TAG_SIBLINGS ][ HC.CONTENT_UPDATE_ADD ] = tag_siblings
        
        #
        
        deleted_tag_sibling_ids = c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_siblings WHERE service_id = ? AND status = ? AND timestamp BETWEEN ? AND ?;', ( service_id, HC.DELETED, begin, end ) ).fetchall()
        
        deleted_tag_siblings = [ ( self._GetTag( c, old_tag_id ), self._GetTag( c, new_tag_id ) ) for ( old_tag_id, new_tag_id ) in deleted_tag_sibling_ids ]
        
        content_data[ HC.CONTENT_DATA_TYPE_TAG_SIBLINGS ][ HC.CONTENT_UPDATE_DELETE ] = deleted_tag_siblings
        
        # tag parents
        
        tag_parent_ids = c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_parents WHERE service_id = ? AND status = ? AND timestamp BETWEEN ? AND ?;', ( service_id, HC.CURRENT, begin, end ) ).fetchall()
        
        tag_parents = [ ( self._GetTag( c, old_tag_id ), self._GetTag( c, new_tag_id ) ) for ( old_tag_id, new_tag_id ) in tag_parent_ids ]
        
        content_data[ HC.CONTENT_DATA_TYPE_TAG_PARENTS ][ HC.CONTENT_UPDATE_ADD ] = tag_parents
        
        #
        
        deleted_tag_parent_ids = c.execute( 'SELECT old_tag_id, new_tag_id FROM tag_parents WHERE service_id = ? AND status = ? AND timestamp BETWEEN ? AND ?;', ( service_id, HC.DELETED, begin, end ) ).fetchall()
        
        deleted_tag_parents = [ ( self._GetTag( c, old_tag_id ), self._GetTag( c, new_tag_id ) ) for ( old_tag_id, new_tag_id ) in deleted_tag_parent_ids ]
        
        content_data[ HC.CONTENT_DATA_TYPE_TAG_PARENTS ][ HC.CONTENT_UPDATE_DELETE ] = deleted_tag_parents
        
        # finish off
        
        hash_ids_to_hashes = self._GetHashIdsToHashes( c, hash_ids )
        
        news_rows = c.execute( 'SELECT news, timestamp FROM news WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ).fetchall()
        
        service_data[ HC.SERVICE_UPDATE_BEGIN_END ] = ( begin, end )
        service_data[ HC.SERVICE_UPDATE_NEWS ] = news_rows
        
        return HC.ServerToClientUpdate( service_data, content_data, hash_ids_to_hashes )
        
    
    def _GenerateTagIdsEfficiently( self, c, tags ):
        
        if type( tags ) != list: tags = list( tags )
        
        tags_not_in_db = set( tags )
        
        for i in range( 0, len( tags ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            tags_subset = tags[ i : i + 250 ]
            
            tags_not_in_db.difference_update( [ tag for ( tag, ) in c.execute( 'SELECT tag FROM tags WHERE tag IN (' + ','.join( '?' * len( tags_subset ) ) + ');', [ tag for tag in tags_subset ] ) ] )
            
        
        if len( tags_not_in_db ) > 0: c.executemany( 'INSERT INTO tags ( tag ) VALUES( ? );', [ ( tag, ) for tag in tags_not_in_db ] )
        
    
    def _GetTag( self, c, tag_id ):
        
        result = c.execute( 'SELECT tag FROM tags WHERE tag_id = ?;', ( tag_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Tag error in database' )
        
        ( tag, ) = result
        
        return tag
        
    
    def _GetTagId( self, c, tag ):
        
        tag = HC.CleanTag( tag )
        
        if tag == '': raise HydrusExceptions.ForbiddenException( 'Tag of zero length!' )
        
        result = c.execute( 'SELECT tag_id FROM tags WHERE tag = ?;', ( tag, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO tags ( tag ) VALUES ( ? );', ( tag, ) )
            
            tag_id = c.lastrowid
            
            return tag_id
            
        else:
            
            ( tag_id, ) = result
            
            return tag_id
            
        
    
    def _GetTagPetition( self, c, service_id ):
        
        petition_types = [ HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_DATA_TYPE_TAG_PARENTS ]
        
        random.shuffle( petition_types )
        
        for petition_type in petition_types:
            
            if petition_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
                
                result = c.execute( 'SELECT DISTINCT account_id, tag_id, reason_id, status FROM mapping_petitions WHERE service_id = ? AND status = ? ORDER BY RANDOM() LIMIT 1;', ( service_id, HC.PETITIONED ) ).fetchone()
                
                if result is None: continue
                
                ( account_id, tag_id, reason_id, status ) = result
                
                action = HC.CONTENT_UPDATE_PETITION
                
                tag = self._GetTag( c, tag_id )
                
                hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mapping_petitions WHERE service_id = ? AND account_id = ? AND tag_id = ? AND reason_id = ? AND status = ?;', ( service_id, account_id, tag_id, reason_id, HC.PETITIONED ) ) ]
                
                hashes = self._GetHashes( c, hash_ids )
                
                petition_data = ( tag, hashes )
                
            elif petition_type in ( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_DATA_TYPE_TAG_PARENTS ):
                
                if petition_type == HC.CONTENT_DATA_TYPE_TAG_SIBLINGS: result = c.execute( 'SELECT account_id, old_tag_id, new_tag_id, reason_id, status FROM tag_siblings WHERE service_id = ? AND status IN ( ?, ? ) ORDER BY RANDOM() LIMIT 1;', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
                elif petition_type == HC.CONTENT_DATA_TYPE_TAG_PARENTS: result = c.execute( 'SELECT account_id, old_tag_id, new_tag_id, reason_id, status FROM tag_parents WHERE service_id = ? AND status IN ( ?, ? ) ORDER BY RANDOM() LIMIT 1;', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
                
                if result is None: continue
                
                ( account_id, old_tag_id, new_tag_id, reason_id, status ) = result
                
                old_tag = self._GetTag( c, old_tag_id )
                
                new_tag = self._GetTag( c, new_tag_id )
                
                petition_data = ( old_tag, new_tag )
                
            
            if status == HC.PENDING: action = HC.CONTENT_UPDATE_PENDING
            elif status == HC.PETITIONED: action = HC.CONTENT_UPDATE_PETITION
            
            account_key = self._GetAccountKeyFromAccountId( c, account_id )
            
            petitioner_account_identifier = HC.AccountIdentifier( account_key = account_key )
            
            reason = self._GetReason( c, reason_id )
            
            return HC.ServerToClientPetition( petition_type, action, petitioner_account_identifier, petition_data, reason )
            
        
        raise HydrusExceptions.NotFoundException( 'No petitions!' )
        
    
    def _RewardMappingPetitioners( self, c, service_id, tag_id, hash_ids, multiplier ):
        
        scores = [ ( account_id, count * multiplier ) for ( account_id, count ) in c.execute( 'SELECT account_id, COUNT( * ) FROM mapping_petitions WHERE service_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ? GROUP BY account_id;', ( service_id, tag_id, HC.PETITIONED ) ) ]
        
        self._RewardAccounts( c, service_id, HC.SCORE_PETITION, scores )
        
    
    def _RewardTagParentPetitioners( self, c, service_id, old_tag_id, new_tag_id, multiplier ):
        
        hash_ids_with_old_tag = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, old_tag_id ) ) }
        hash_ids_with_new_tag = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, new_tag_id ) ) }
        
        score = len( hash_ids_with_old_tag.intersection( hash_ids_with_new_tag ) )
        
        weighted_score = score * multiplier
        
        account_ids = [ account_id for ( account_id, ) in c.execute( 'SELECT account_id FROM tag_parents WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status IN ( ?, ? );', ( service_id, old_tag_id, new_tag_id, HC.PENDING, HC.PETITIONED ) ) ]
        
        scores = [ ( account_id, weighted_score ) for account_id in account_ids ]
        
        self._RewardAccounts( c, service_id, HC.SCORE_PETITION, scores )
        
    
    def _RewardTagSiblingPetitioners( self, c, service_id, old_tag_id, new_tag_id, multiplier ):
        
        hash_ids_with_old_tag = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, old_tag_id ) ) }
        hash_ids_with_new_tag = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND tag_id = ?;', ( service_id, new_tag_id ) ) }
        
        score = len( hash_ids_with_old_tag.intersection( hash_ids_with_new_tag ) )
        
        weighted_score = score * multiplier
        
        account_ids = [ account_id for ( account_id, ) in c.execute( 'SELECT account_id FROM tag_siblings WHERE service_id = ? AND old_tag_id = ? AND new_tag_id = ? AND status IN ( ?, ? );', ( service_id, old_tag_id, new_tag_id, HC.PENDING, HC.PETITIONED ) ) ]
        
        scores = [ ( account_id, weighted_score ) for account_id in account_ids ]
        
        self._RewardAccounts( c, service_id, HC.SCORE_PETITION, scores )
        
    
class RatingDB( object ):
    
    def _GenerateRatingUpdate( self, c, service_id, begin, end ):
        
        ratings_info = c.execute( 'SELECT hash, hash_id, score, count, new_timestamp, current_timestamp FROM aggregate_ratings, hashes USING ( hash_id ) WHERE service_id = ? AND ( new_timestamp BETWEEN ? AND ? OR current_timestamp BETWEEN ? AND ? );', ( service_id, begin, end, begin, end ) ).fetchall()
        
        current_timestamps = { rating_info[5] for rating_info in ratings_info }
        
        hash_ids = [ rating_info[1] for rating_info in ratings_info ]
        
        c.execute( 'UPDATE aggregate_ratings SET current_timestamp = new_timestamp AND new_timestamp = 0 WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
        
        c.executemany( 'UPDATE updates SET dirty = ? WHERE service_id = ? AND ? BETWEEN begin AND end;', [ ( True, service_id, current_timestamp ) for current_timestamp in current_timestamps if current_timestamp != 0 ] )
        
        ratings = [ ( hash, score, count ) for ( hash, hash_id, score, count, new_timestamp, current_timestamp ) in ratings_info ]
        
        news = c.execute( 'SELECT news, timestamp FROM news WHERE service_id = ? AND timestamp BETWEEN ? AND ?;', ( service_id, begin, end ) ).fetchall()
        
        return HC.UpdateServerToClientRatings( ratings, news, begin, end )
        
    
    def _UpdateRatings( self, c, service_id, account_id, ratings ):
        
        hashes = [ rating[0] for rating in ratings ]
        
        hashes_to_hash_ids = self._GetHashesToHashIds( c, hashes )
        
        valued_ratings = [ ( hash, rating ) for ( hash, rating ) in ratings if rating is not None ]
        null_ratings = [ hash for ( hash, rating ) in ratings if rating is None ]
        
        c.executemany( 'REPLACE INTO ratings ( service_id, account_id, hash_id, rating ) VALUES ( ?, ?, ?, ? );', [ ( service_id, account_id, hashes_to_hash_ids[ hash ], rating ) for ( hash, rating ) in valued_ratings ] )
        c.executemany( 'DELETE FROM ratings WHERE service_id = ? AND account_id = ? AND hash_id = ?;', [ ( service_id, account_id, hashes_to_hash_ids[ hash ] ) for hash in null_ratings ] )
        
        hash_ids = set( hashes_to_hash_ids.values() )
        
        aggregates = c.execute( 'SELECT hash_id, SUM( rating ), COUNT( * ) FROM ratings WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' GROUP BY hash_id;' )
        
        missed_aggregate_hash_ids = hash_ids.difference( aggregate[0] for aggregate in aggregates )
        
        aggregates.extend( [ ( hash_id, 0.0, 0 ) for hash_id in missed_aggregate_hash_ids ] )        
        
        hash_ids_to_new_timestamps = { hash_id : new_timestamp for ( hash_id, new_timestamp ) in c.execute( 'SELECT hash_id, new_timestamp FROM aggregate_ratings WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) }
        
        now = HC.GetNow()
        
        for ( hash_id, total_score, count ) in aggregates:
            
            score = float( total_score ) / float( count )
            
            if hash_id not in hash_ids_to_new_timestamps or hash_ids_to_new_timestamps[ hash_id ] == 0:
                
                new_timestamp = now + ( count * HC.UPDATE_DURATION / 10 )
                
            else:
                
                new_timestamp = max( now, hash_ids_to_new_timestamps[ hash_id ] - HC.UPDATE_DURATION )
                
            
            if hash_id not in hash_ids_to_new_timestamps: c.execute( 'INSERT INTO aggregate_ratings ( service_id, hash_id, score, count, new_timestamp, current_timestamp ) VALUES ( ?, ?, ?, ?, ?, ? );', ( service_id, hash_id, score, new_timestamp, 0 ) )
            elif new_timestamp != hash_ids_to_new_timestamps[ hash_id ]: c.execute( 'UPDATE aggregate_ratings SET new_timestamp = ? WHERE service_id = ? AND hash_id = ?;', ( new_timestamp, service_id, hash_id ) )
            
        
    
class ServiceDB( FileDB, MessageDB, TagDB ):
    
    def _AccountTypeExists( self, c, service_id, title ): return c.execute( 'SELECT 1 FROM account_types WHERE service_id = ? AND title = ?;', ( service_id, title ) ).fetchone() is not None
    
    def _AddNews( self, c, service_key, news ):
        
        service_id = self._GetServiceId( c, service_key )
        
        now = HC.GetNow()
        
        c.execute( 'INSERT INTO news ( service_id, news, timestamp ) VALUES ( ?, ?, ? );', ( service_id, news, now ) )
        
    
    def _AddMessagingSession( self, c, service_key, session_key, account_key, name, expires ):
        
        service_id = self._GetServiceId( c, service_key )
        
        account_id = self._GetAccountId( c, account_key )
        
        c.execute( 'INSERT INTO sessions ( service_id, session_key, account_id, identifier, name, expiry ) VALUES ( ?, ?, ?, ?, ?, ? );', ( service_id, sqlite3.Binary( session_key ), account_id, sqlite3.Binary( account_key ), name, expires ) )
        
    
    def _AddSession( self, c, session_key, service_key, account_key, expires ):
        
        service_id = self._GetServiceId( c, service_key )
        
        account_id = self._GetAccountId( c, account_key )
        
        c.execute( 'INSERT INTO sessions ( session_key, service_id, account_id, expiry ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( session_key ), service_id, account_id, expires ) )
        
    
    def _AddToExpires( self, c, account_ids, timespan ): c.execute( 'UPDATE accounts SET expires = expires + ? WHERE account_id IN ' + HC.SplayListForDB( account_ids ) + ';', ( timespan, ) )
    
    def _Ban( self, c, service_id, action, admin_account_id, subject_account_ids, reason_id, expires = None, lifetime = None ):
        
        splayed_subject_account_ids = HC.SplayListForDB( subject_account_ids )
        
        now = HC.GetNow()
        
        if expires is not None: pass
        elif lifetime is not None: expires = now + lifetime
        else: expires = None
        
        c.executemany( 'INSERT OR IGNORE INTO bans ( service_id, account_id, admin_account_id, reason_id, created, expires ) VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, subject_account_id, admin_account_id, reason_id, now, expires ) for subject_account_id in subject_account_ids ] )
        
        c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
        c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
        c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) )
        
        c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) )
        
        if action == HC.SUPERBAN:
            
            hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ';', ( service_id, ) ) ]
            
            if len( hash_ids ) > 0: self._DeleteLocalFiles( c, admin_account_id, hash_ids, reason_id )
            
            mappings_dict = HC.BuildKeyToListDict( c.execute( 'SELECT tag_id, hash_id FROM mappings WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ';', ( service_id, ) ) )
            
            if len( mappings_dict ) > 0:
                
                for ( tag_id, hash_ids ) in mappings_dict.items(): self._DeleteMappings( c, admin_account_id, tag_id, hash_ids, reason_id )
                
            
        
    
    def _ChangeAccountType( self, c, account_ids, account_type_id ): c.execute( 'UPDATE accounts SET account_type_id = ? WHERE account_id IN ' + HC.SplayListForDB( account_ids ) + ';', ( account_type_id, ) )
    
    def _CheckDataUsage( self, c ):
        
        ( version_year, version_month ) = c.execute( 'SELECT year, month FROM version;' ).fetchone()
        
        current_time_struct = time.gmtime()
        
        ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
        
        if version_year != current_year or version_month != current_month:
            
            c.execute( 'UPDATE version SET year = ?, month = ?;', ( current_year, current_month ) )
            
            c.execute( 'UPDATE accounts SET used_bytes = ?, used_requests = ?;', ( 0, 0 ) )
            
            self.pub_after_commit( 'update_all_session_accounts' )
            
        
    
    def _CheckMonthlyData( self, c ):
        
        service_info = self._GetServicesInfo( c )
        
        running_total = 0
        
        self._services_over_monthly_data = set()
        
        for ( service_key, service_type, options ) in service_info:
            
            service_id = self._GetServiceId( c, service_key )
            
            if service_type != HC.SERVER_ADMIN:
                
                ( total_used_bytes, ) = c.execute( 'SELECT SUM( used_bytes ) FROM accounts WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                if total_used_bytes is None: total_used_bytes = 0
                
                running_total += total_used_bytes
                
                if 'max_monthly_data' in options:
                    
                    max_monthly_data = options[ 'max_monthly_data' ]
                    
                    if max_monthly_data is not None and total_used_bytes > max_monthly_data: self._services_over_monthly_data.add( service_key )
                    
                
            
        
        # have to do this after
        
        server_admin_options = self._GetOptions( c, HC.SERVER_ADMIN_KEY )
        
        self._over_monthly_data = False
        
        if 'max_monthly_data' in server_admin_options:
            
            max_monthly_data = server_admin_options[ 'max_monthly_data' ]
            
            if max_monthly_data is not None and running_total > max_monthly_data: self._over_monthly_data = True
            
        
    
    def _CleanUpdate( self, c, service_key, begin, end ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service_type = self._GetServiceType( c, service_id )
        
        if service_type == HC.FILE_REPOSITORY: clean_update = self._GenerateFileUpdate( c, service_id, begin, end )
        elif service_type == HC.TAG_REPOSITORY: clean_update = self._GenerateTagUpdate( c, service_id, begin, end )
        
        path = SC.GetExpectedUpdatePath( service_key, begin )
        
        with open( path, 'wb' ) as f: f.write( yaml.safe_dump( clean_update ) )
        
        c.execute( 'UPDATE update_cache SET dirty = ? WHERE service_id = ? AND begin = ?;', ( False, service_id, begin ) )
        
    
    def _ClearBans( self, c ):
        
        now = HC.GetNow()
        
        c.execute( 'DELETE FROM bans WHERE expires < ?;', ( now, ) )
        
    
    def _CreateUpdate( self, c, service_key, begin, end ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service_type = self._GetServiceType( c, service_id )
        
        if service_type == HC.FILE_REPOSITORY: update = self._GenerateFileUpdate( c, service_id, begin, end )
        elif service_type == HC.TAG_REPOSITORY: update = self._GenerateTagUpdate( c, service_id, begin, end )
        
        path = SC.GetExpectedUpdatePath( service_key, begin )
        
        with open( path, 'wb' ) as f: f.write( yaml.safe_dump( update ) )
        
        c.execute( 'INSERT OR REPLACE INTO update_cache ( service_id, begin, end, dirty ) VALUES ( ?, ?, ?, ? );', ( service_id, begin, end, False ) )
        
    
    def _DeleteOrphans( self, c ):
        
        # files
        
        deletees = [ hash_id for ( hash_id, ) in c.execute( 'SELECT DISTINCT hash_id FROM files_info EXCEPT SELECT DISTINCT hash_id FROM file_map;' ) ]
        
        if len( deletees ) > 0:
            
            deletee_hashes = set( self._GetHashes( c, deletees ) )
            
            local_files_hashes = SC.GetAllHashes( 'file' )
            thumbnails_hashes = SC.GetAllHashes( 'thumbnail' )
            
            for hash in local_files_hashes & deletee_hashes: os.remove( SC.GetPath( 'file', hash ) )
            for hash in thumbnails_hashes & deletee_hashes: os.remove( SC.GetPath( 'thumbnail', hash ) )
            
            c.execute( 'DELETE FROM files_info WHERE hash_id IN ' + HC.SplayListForDB( deletees ) + ';' )
            
        
        # messages
        
        required_message_keys = { message_key for ( message_key, ) in c.execute( 'SELECT DISTINCT message_key FROM messages;' ) }
        
        existing_message_keys = SC.GetAllHashes( 'message' )
        
        deletees = existing_message_keys - required_message_keys
        
        for message_key in deletees: os.remove( SC.GetPath( 'message', message_key ) )
        
    
    def _FlushRequestsMade( self, c, all_requests ):
        
        requests_dict = HC.BuildKeyToListDict( all_requests )
        
        c.executemany( 'UPDATE accounts SET used_bytes = used_bytes + ?, used_requests = used_requests + ? WHERE account_key = ?;', [ ( sum( num_bytes_list ), len( num_bytes_list ), sqlite3.Binary( account_key ) ) for ( account_key, num_bytes_list ) in requests_dict.items() ] )
        
    
    def _GenerateRegistrationKeys( self, c, service_key, num, title, lifetime = None ):
        
        service_id = self._GetServiceId( c, service_key )
        
        account_type_id = self._GetAccountTypeId( c, service_id, title )
        
        now = HC.GetNow()
        
        if lifetime is not None: expires = now + lifetime
        else: expires = None
        
        keys = [ ( os.urandom( HC.HYDRUS_KEY_LENGTH ), os.urandom( HC.HYDRUS_KEY_LENGTH ), os.urandom( HC.HYDRUS_KEY_LENGTH ) ) for i in range( num ) ]
        
        c.executemany( 'INSERT INTO registration_keys ( registration_key, service_id, account_type_id, account_key, access_key, expiry ) VALUES ( ?, ?, ?, ?, ?, ? );', [ ( sqlite3.Binary( hashlib.sha256( registration_key ).digest() ), service_id, account_type_id, sqlite3.Binary( account_key ), sqlite3.Binary( access_key ), expires ) for ( registration_key, account_key, access_key ) in keys ] )
        
        return [ registration_key for ( registration_key, account_key, access_key ) in keys ]
        
    
    def _GetAccessKey( self, c, registration_key ):
        
        # we generate a new access_key every time this is requested so that if the registration_key leaks, no one grab the access_key before the legit user does
        # the reg_key is deleted when the last-requested access_key is used to create a session, which calls getaccountkeyfromaccesskey
        
        try: ( one, ) = c.execute( 'SELECT 1 FROM registration_keys WHERE registration_key = ?;', ( sqlite3.Binary( hashlib.sha256( registration_key ).digest() ), ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'The service could not find that registration key in its database.' )
        
        new_access_key = os.urandom( HC.HYDRUS_KEY_LENGTH )
        
        c.execute( 'UPDATE registration_keys SET access_key = ? WHERE registration_key = ?;', ( sqlite3.Binary( new_access_key ), sqlite3.Binary( hashlib.sha256( registration_key ).digest() ) ) )
        
        return new_access_key
        
    
    def _GetAccount( self, c, account_key ):
        
        ( account_id, service_id, account_key, account_type, created, expires, used_bytes, used_requests ) = c.execute( 'SELECT account_id, service_id, account_key, account_type, created, expires, used_bytes, used_requests FROM accounts, account_types USING ( service_id, account_type_id ) WHERE account_key = ?;', ( sqlite3.Binary( account_key ), ) ).fetchone()
        
        banned_info = c.execute( 'SELECT reason, created, expires FROM bans, reasons USING ( reason_id ) WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
        
        return HC.Account( account_key, account_type, created, expires, used_bytes, used_requests, banned_info = banned_info )
        
    
    def _GetAccountFileInfo( self, c, service_id, account_id ):
        
        ( num_deleted_files, ) = c.execute( 'SELECT COUNT( * ) FROM file_petitions WHERE service_id = ? AND account_id = ? AND status = ?;', ( service_id, account_id, HC.DELETED ) ).fetchone()
        
        ( num_files, num_files_bytes ) = c.execute( 'SELECT COUNT( * ), SUM( size ) FROM file_map, files_info USING ( hash_id ) WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
        
        if num_files_bytes is None: num_files_bytes = 0
        
        result = c.execute( 'SELECT score FROM account_scores WHERE service_id = ? AND account_id = ? AND score_type = ?;', ( service_id, account_id, HC.SCORE_PETITION ) ).fetchone()
        
        if result is None: petition_score = 0
        else: ( petition_score, ) = result
        
        ( num_petitions, ) = c.execute( 'SELECT COUNT( DISTINCT reason_id ) FROM file_petitions WHERE service_id = ? AND account_id = ? AND status = ?;', ( service_id, account_id, HC.PETITIONED ) ).fetchone()
        
        account_info = {}
        
        account_info[ 'num_deleted_files' ] = num_deleted_files
        account_info[ 'num_files' ] = num_files
        account_info[ 'num_files_bytes' ] = num_files_bytes
        account_info[ 'petition_score' ] = petition_score
        account_info[ 'num_petitions' ] = num_petitions
        
        return account_info
        
    
    def _GetAccountKeyFromAccessKey( self, c, service_key, access_key ):
        
        try: ( account_key, ) = c.execute( 'SELECT account_key FROM accounts WHERE hashed_access_key = ?;', ( sqlite3.Binary( hashlib.sha256( access_key ).digest() ), ) ).fetchone()
        except:
            
            # we do not delete the registration_key (and hence the raw unhashed access_key)
            # until the first attempt to create a session to make sure the user
            # has the access_key saved
            
            try: ( account_type_id, account_key, expires ) = c.execute( 'SELECT account_type_id, account_key, expiry FROM registration_keys WHERE access_key = ?;', ( sqlite3.Binary( access_key ), ) ).fetchone()
            except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
            
            c.execute( 'DELETE FROM registration_keys WHERE access_key = ?;', ( sqlite3.Binary( access_key ), ) )
            
            #
            
            now = HC.GetNow()
            
            service_id = self._GetServiceId( c, service_key )
            
            c.execute( 'INSERT INTO accounts ( service_id, account_key, hashed_access_key, account_type_id, created, expires, used_bytes, used_requests ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ? );', ( service_id, sqlite3.Binary( account_key ), sqlite3.Binary( hashlib.sha256( access_key ).digest() ), account_type_id, now, expires, 0, 0 ) )
            
        
        return account_key
        
    
    def _GetAccountKeyFromAccountId( self, c, account_id ):
        
        try: ( account_key, ) = c.execute( 'SELECT account_key FROM accounts WHERE account_id = ?;', ( account_id, ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account_id in its database.' )
        
        return account_key
        
    
    def _GetAccountKeyFromIdentifier( self, c, service_key, account_identifier ):
        
        service_id = self._GetServiceId( c, service_key )
        
        if account_identifier.HasAccountKey():
            
            account_key = account_identifier.GetData()
            
            result = c.execute( 'SELECT 1 FROM accounts WHERE service_id = ? AND account_key = ?;', ( service_id, sqlite3.Binary( account_key ) ) ).fetchone()
            
            if result is None: raise HydrusExceptions.ForbiddenException( 'The service could not find that hash in its database.')
            
        else:
            
            if account_identifier.HasHash():
                
                try:
                    
                    hash = account_identifier.GetData()
                    
                    hash_id = self._GetHashId( c, hash )
                    
                    result = c.execute( 'SELECT account_id FROM file_map WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
                    
                    if result is None: result = c.execute( 'SELECT account_id FROM file_petitions WHERE service_id = ? AND hash_id = ? AND status = ?;', ( service_id, hash_id, HC.DELETED ) ).fetchone()
                    
                    ( account_id, ) = result
                    
                except: raise HydrusExceptions.ForbiddenException( 'The service could not find that hash in its database.' )
                
            elif account_identifier.HasMapping():
                
                try:
                    
                    ( hash, tag ) = account_identifier.GetData()
                    
                    hash_id = self._GetHashId( c, hash )
                    tag_id = self._GetTagId( c, tag )
                    
                    ( account_id, ) = c.execute( 'SELECT account_id FROM mappings WHERE service_id = ? AND tag_id = ? AND hash_id = ?;', ( service_id, tag_id, hash_id ) ).fetchone()
                    
                except: raise HydrusExceptions.ForbiddenException( 'The service could not find that mapping in its database.' )
                
            
            try: ( account_key, ) = c.execute( 'SELECT account_key FROM accounts WHERE account_id = ?;', ( account_id, ) ).fetchone()
            except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
            
        
        return account_key
        
    
    def _GetAccountIdFromContactKey( self, c, service_id, contact_key ):
        
        try:
            
            ( account_id, ) = c.execute( 'SELECT account_id FROM contacts WHERE service_id = ? AND contact_key = ?;', ( service_id, sqlite3.Binary( contact_key ) ) ).fetchone()
            
        except: raise HydrusExceptions.NotFoundException( 'Could not find that contact key!' )
        
        return account_id
        
    
    def _GetAccountId( self, c, account_key ):
        
        result = c.execute( 'SELECT account_id FROM accounts WHERE account_key = ?;', ( sqlite3.Binary( account_key ), ) ).fetchone()
        
        if result is None: raise HydrusExceptions.ForbiddenException( 'The service could not find that account key in its database.' )
        
        ( account_id, ) = result
        
        return account_id
        
    
    def _GetAccountInfo( self, c, service_key, account_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        account = self._GetAccount( c, account_key )
        
        account_id = self._GetAccountId( c, account_key )
        
        service_type = self._GetServiceType( c, service_id )
        
        if service_type == HC.FILE_REPOSITORY: account_info = self._GetAccountFileInfo( c, service_id, account_id )
        elif service_type == HC.TAG_REPOSITORY: account_info = self._GetAccountMappingInfo( c, service_id, account_id )
        else: account_info = {}
        
        account_info[ 'account' ] = account
        
        return account_info
        
    
    def _GetAccountMappingInfo( self, c, service_id, account_id ):
        
        num_deleted_mappings = len( c.execute( 'SELECT COUNT( * ) FROM mapping_petitions WHERE service_id = ? AND account_id = ? AND status = ? LIMIT 5000;', ( service_id, account_id, HC.DELETED ) ).fetchall() )
        
        num_mappings = len( c.execute( 'SELECT 1 FROM mappings WHERE service_id = ? AND account_id = ? LIMIT 5000;', ( service_id, account_id ) ).fetchall() )
        
        result = c.execute( 'SELECT score FROM account_scores WHERE service_id = ? AND account_id = ? AND score_type = ?;', ( service_id, account_id, HC.SCORE_PETITION ) ).fetchone()
        
        if result is None: petition_score = 0
        else: ( petition_score, ) = result
        
        # crazy query here because two distinct columns
        ( num_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT tag_id, reason_id FROM mapping_petitions WHERE service_id = ? AND account_id = ? AND status = ? );', ( service_id, account_id, HC.PETITIONED ) ).fetchone()
        
        account_info = {}
        
        account_info[ 'num_deleted_mappings' ] = num_deleted_mappings
        account_info[ 'num_mappings' ] = num_mappings
        account_info[ 'petition_score' ] = petition_score
        account_info[ 'num_petitions' ] = num_petitions
        
        return account_info
        
    
    def _GetAccountTypeId( self, c, service_id, title ):
        
        result = c.execute( 'SELECT account_type_id FROM account_types WHERE service_id = ? AND title = ?;', ( service_id, title ) ).fetchone()
        
        if result is None: raise HydrusExceptions.NotFoundException( 'Could not find account title ' + HC.u( title ) + ' in db for this service.' )
        
        ( account_type_id, ) = result
        
        return account_type_id
        
    
    def _GetAccountTypes( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        return [ account_type for ( account_type, ) in c.execute( 'SELECT account_type FROM account_types WHERE service_id = ?;', ( service_id, ) ) ]
        
    
    def _GetDirtyUpdates( self, c ):
        
        service_ids_to_tuples = HC.BuildKeyToListDict( [ ( service_id, ( begin, end ) ) for ( service_id, begin, end ) in c.execute( 'SELECT service_id, begin, end FROM update_cache WHERE dirty = ?;', ( True, ) ) ] )
        
        service_keys_to_tuples = {}
        
        for ( service_id, tuples ) in service_ids_to_tuples.items():
            
            service_key = self._GetServiceKey( c, service_id )
            
            service_keys_to_tuples[ service_key ] = tuples
            
        
        return service_keys_to_tuples
        
    
    def _GetMessagingSessions( self, c ):
        
        now = HC.GetNow()
        
        c.execute( 'DELETE FROM messaging_sessions WHERE ? > expiry;', ( now, ) )
        
        existing_session_ids = HC.BuildKeyToListDict( [ ( service_id, ( session_key, account_id, identifier, name, expires ) ) for ( service_id, identifier, name, expires ) in c.execute( 'SELECT service_id, session_key, account_id, identifier, name, expiry FROM messaging_sessions;' ) ] )
        
        existing_sessions = {}
        
        for ( service_id, tuples ) in existing_session_ids.items():
            
            service_key = self._GetServiceKey( c, service_id )
            
            processed_tuples = []
            
            for ( account_id, identifier, name, expires ) in tuples:
                
                account_key = self._GetAccountKeyFromAccountId( c, account_id )
                
                account = self._GetAccount( c, account_key )
                
                processed_tuples.append( ( account, name, expires ) )
                
            
            existing_sessions[ service_key ] = processed_tuples
            
        
        return existing_sessions
        
    
    def _GetNumPetitions( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service_type = self._GetServiceType( c, service_id )
        
        if service_type == HC.FILE_REPOSITORY:
            
            ( num_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT account_id, reason_id FROM file_petitions WHERE service_id = ? AND status = ? );', ( service_id, HC.PETITIONED ) ).fetchone()
            
        elif service_type == HC.TAG_REPOSITORY:
            
            ( num_mapping_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT account_id, tag_id, reason_id FROM mapping_petitions WHERE service_id = ? AND status = ? );', ( service_id, HC.PETITIONED ) ).fetchone()
            
            ( num_tag_sibling_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM tag_siblings WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
            
            ( num_tag_parent_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM tag_parents WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
            
            num_petitions = num_mapping_petitions + num_tag_sibling_petitions + num_tag_parent_petitions
            
        
        return num_petitions
        
    
    def _GetOptions( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        ( options, ) = c.execute( 'SELECT options FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return options
        
    
    def _GetPetition( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service_type = self._GetServiceType( c, service_id )
        
        if service_type == HC.FILE_REPOSITORY: petition = self._GetFilePetition( c, service_id )
        elif service_type == HC.TAG_REPOSITORY: petition = self._GetTagPetition( c, service_id )
        
        return petition
        
    
    def _GetReason( self, c, reason_id ):
        
        result = c.execute( 'SELECT reason FROM reasons WHERE reason_id = ?;', ( reason_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Reason error in database' )
        
        ( reason, ) = result
        
        return reason
        
    
    def _GetReasonId( self, c, reason ):
        
        result = c.execute( 'SELECT reason_id FROM reasons WHERE reason = ?;', ( reason, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO reasons ( reason ) VALUES ( ? );', ( reason, ) )
            
            reason_id = c.lastrowid
            
            return reason_id
            
        else:
            
            ( reason_id, ) = result
            
            return reason_id
            
        
    
    def _GetServiceId( self, c, service_key ):
        
        result = c.execute( 'SELECT service_id FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_id, ) = result
        
        return service_id
        
    
    def _GetServiceIds( self, c, limited_types = HC.ALL_SERVICES ): return [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM services WHERE type IN ' + HC.SplayListForDB( limited_types ) + ';' ) ]
    
    def _GetServiceKey( self, c, service_id ):
        
        ( service_key, ) = c.execute( 'SELECT service_key FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return service_key
        
    
    def _GetServiceKeys( self, c, limited_types = HC.ALL_SERVICES ): return [ service_key for ( service_key, ) in c.execute( 'SELECT service_key FROM services WHERE type IN '+ HC.SplayListForDB( limited_types ) + ';' ) ]
    
    def _GetServiceType( self, c, service_id ):
        
        result = c.execute( 'SELECT type FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_type, ) = result
        
        return service_type
        
    
    def _GetServiceInfo( self, c, service_key ): return c.execute( 'SELECT type, options FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
    
    def _GetServicesInfo( self, c, limited_types = HC.ALL_SERVICES ): return c.execute( 'SELECT service_key, type, options FROM services WHERE type IN '+ HC.SplayListForDB( limited_types ) + ';' ).fetchall()
    
    def _GetSessions( self, c ):
        
        now = HC.GetNow()
        
        c.execute( 'DELETE FROM sessions WHERE ? > expiry;', ( now, ) )
        
        sessions = []
        
        results = c.execute( 'SELECT session_key, service_id, account_id, expiry FROM sessions;' ).fetchall()
        
        service_ids_to_service_keys = {}
        
        account_ids_to_accounts = {}
        
        for ( session_key, service_id, account_id, expires ) in results:
            
            if service_id not in service_ids_to_service_keys: service_ids_to_service_keys[ service_id ] = self._GetServiceKey( c, service_id )
            
            service_key = service_ids_to_service_keys[ service_id ]
            
            if account_id not in account_ids_to_accounts:
                
                account_key = self._GetAccountKeyFromAccountId( c, account_id )
                
                account = self._GetAccount( c, account_key )
                
                account_ids_to_accounts[ account_id ] = account
                
            
            account = account_ids_to_accounts[ account_id ]
            
            sessions.append( ( session_key, service_key, account, expires ) )
            
        
        return sessions
        
    
    def _GetStats( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        stats = {}
        
        ( stats[ 'num_accounts' ], ) = c.execute( 'SELECT COUNT( * ) FROM accounts WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        ( stats[ 'num_banned' ], ) = c.execute( 'SELECT COUNT( * ) FROM bans WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return stats
        
    
    def _GetUpdateEnds( self, c ):
        
        service_ids = self._GetServiceIds( c, HC.REPOSITORIES )
        
        results = {}
        
        for service_id in service_ids:
            
            ( end, ) = c.execute( 'SELECT end FROM update_cache WHERE service_id = ? ORDER BY end DESC LIMIT 1;', ( service_id, ) ).fetchone()
            
            service_key = self._GetServiceKey( c, service_id )
            
            results[ service_key ] = end
            
        
        return results
        
    
    def _InitAdmin( self, c ):
        
        if c.execute( 'SELECT 1 FROM accounts;' ).fetchone() is not None: raise HydrusExceptions.ForbiddenException( 'This server is already initialised!' )
        
        num = 1
        
        title = 'server admin'
        
        ( registration_key, ) = self._GenerateRegistrationKeys( c, HC.SERVER_ADMIN_KEY, num, title )
        
        access_key = self._GetAccessKey( c, registration_key )
        
        return access_key
        
    
    def _ModifyAccount( self, c, service_key, admin_account_key, action, subject_account_keys, kwargs ):
        
        service_id = self._GetServiceId( c, service_key )
        
        admin_account_id = self._GetAccountId( c, admin_account_key )
        
        subject_account_ids = [ self._GetAccountId( c, subject_account_key ) for subject_account_key in subject_account_keys ]
        
        if action in ( HC.BAN, HC.SUPERBAN ):
            
            reason = kwargs[ 'reason' ]
            
            reason_id = self._GetReasonId( c, reason )
            
            if lifetime in request_args: lifetime = kwargs[ 'lifetime' ]
            else: lifetime = None
            
            self._Ban( c, service_id, action, admin_account_id, subject_account_ids, reason_id, lifetime ) # fold ban and superban together, yo
            
        else:
            
            admin_account.CheckPermission( HC.GENERAL_ADMIN ) # special case, don't let manage_users people do these:
            
            if action == HC.CHANGE_ACCOUNT_TYPE:
                
                title = kwargs[ 'title' ]
                
                account_type_id = self._GetAccountTypeId( c, service_id, title )
                
                self._ChangeAccountType( c, subject_account_ids, account_type_id )
                
            elif action == HC.ADD_TO_EXPIRES:
                
                timespan = kwargs[ 'timespan' ]
                
                self._AddToExpires( c, subject_account_ids, timespan )
                
            elif action == HC.SET_EXPIRES:
                
                expires = kwargs[ 'expires' ]
                
                self._SetExpires( c, subject_account_ids, expires )
                
            
        
    
    def _ModifyAccountTypes( self, c, service_key, edit_log ):
        
        service_id = self._GetServiceId( c, service_key )
        
        for ( action, details ) in edit_log:
            
            if action == HC.ADD:
                
                account_type = details
                
                title = account_type.GetTitle()
                
                if self._AccountTypeExists( c, service_id, title ): raise HydrusExceptions.ForbiddenException( 'Already found account type ' + HC.u( title ) + ' in the db for this service, so could not add!' )
                
                c.execute( 'INSERT OR IGNORE INTO account_types ( service_id, title, account_type ) VALUES ( ?, ?, ? );', ( service_id, title, account_type ) )
                
            elif action == HC.DELETE:
                
                ( title, new_title ) = details
                
                account_type_id = self._GetAccountTypeId( c, service_id, title )
                
                new_account_type_id = self._GetAccountTypeId( c, service_id, new_title )
                
                c.execute( 'UPDATE accounts SET account_type_id = ? WHERE account_type_id = ?;', ( new_account_type_id, account_type_id ) )
                c.execute( 'UPDATE registration_keys SET account_type_id = ? WHERE account_type_id = ?;', ( new_account_type_id, account_type_id ) )
                
                c.execute( 'DELETE FROM account_types WHERE account_type_id = ?;', ( account_type_id, ) )
                
            elif action == HC.EDIT:
                
                ( old_title, account_type ) = details
                
                title = account_type.GetTitle()
                
                if old_title != title and self._AccountTypeExists( c, service_id, title ): raise HydrusExceptions.ForbiddenException( 'Already found account type ' + HC.u( title ) + ' in the database, so could not rename ' + HC.u( old_title ) + '!' )
                
                account_type_id = self._GetAccountTypeId( c, service_id, old_title )
                
                c.execute( 'UPDATE account_types SET title = ?, account_type = ? WHERE account_type_id = ?;', ( title, account_type, account_type_id ) )
                
            
        
    
    def _ModifyServices( self, c, account_key, edit_log ):
        
        account_id = self._GetAccountId( c, account_key )
        
        service_keys_to_access_keys = {}
        
        now = HC.GetNow()
        
        for ( action, data ) in edit_log:
            
            if action == HC.ADD:
                
                ( service_key, service_type, options ) = data
                
                c.execute( 'INSERT INTO services ( service_key, type, options ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, options ) )
                
                service_id = c.lastrowid
                
                service_admin_account_type = HC.AccountType( 'service admin', [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN ], ( None, None ) )
                
                c.execute( 'INSERT INTO account_types ( service_id, title, account_type ) VALUES ( ?, ?, ? );', ( service_id, 'service admin', service_admin_account_type ) )
                
                [ registration_key ] = self._GenerateRegistrationKeys( c, service_key, 1, 'service admin', None )
                
                access_key = self._GetAccessKey( c, registration_key )
                
                service_keys_to_access_keys[ service_key ] = access_key
                
                if service_type in HC.REPOSITORIES:
                    
                    begin = 0
                    end = HC.GetNow()
                    
                    self._CreateUpdate( c, service_key, begin, end )
                    
                
                self.pub_after_commit( 'action_service', service_key, 'start' )
                
            elif action == HC.DELETE:
                
                service_key = data
                
                service_id = self._GetServiceId( c, service_key )
                
                c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
                
                self.pub_after_commit( 'action_service', service_key, 'stop' )
                
            elif action == HC.EDIT:
                
                ( service_key, service_type, options ) = data
                
                service_id = self._GetServiceId( c, service_key )
                
                c.execute( 'UPDATE services SET options = ? WHERE service_id = ?;', ( options, service_id ) )
                
                self.pub_after_commit( 'action_service', service_key, 'restart' )
                
            
        
        return service_keys_to_access_keys
        
    
    def _ProcessUpdate( self, c, service_key, account_key, update ):
        
        service_id = self._GetServiceId( c, service_key )
        
        account_id = self._GetAccountId( c, account_key )
        
        account = self._GetAccount( c, account_key )
        
        service_type = self._GetServiceType( c, service_id )
        
        if service_type == HC.FILE_REPOSITORY:
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ) or account.HasPermission( HC.POST_PETITIONS ):
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveFilePetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddFilePetition
                
                for ( hashes, reason ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PETITION ):
                    
                    hash_ids = self._GetHashIds( c, hashes )
                    
                    reason_id = self._GetReasonId( c, reason )
                    
                    petition_method( c, service_id, account_id, hash_ids, reason_id )
                    
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                for hashes in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DENY_PETITION ):
                    
                    hash_ids = self._GetHashIds( c, hashes )
                    
                    self._DenyFilePetition( c, service_id, hash_ids )
                    
                
            
        elif service_type == HC.TAG_REPOSITORY:
            
            tags = update.GetTags()
            
            hashes = update.GetHashes()
            
            self._GenerateTagIdsEfficiently( c, tags )
            
            self._GenerateHashIdsEfficiently( c, hashes )
            
            #
            
            overwrite_deleted = account.HasPermission( HC.RESOLVE_PETITIONS )
            
            for ( tag, hashes ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING ):
                
                tag_id = self._GetTagId( c, tag )
                
                hash_ids = self._GetHashIds( c, hashes )
                
                self._AddMappings( c, service_id, account_id, tag_id, hash_ids, overwrite_deleted )
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ) or account.HasPermission( HC.POST_PETITIONS ):
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveMappingPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddMappingPetition
                
                for ( tag, hashes, reason ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION ):
                    
                    tag_id = self._GetTagId( c, tag )
                    
                    hash_ids = self._GetHashIds( c, hashes )
                    
                    reason_id = self._GetReasonId( c, reason )
                    
                    petition_method( c, service_id, account_id, tag_id, hash_ids, reason_id )
                    
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                for ( tag, hashes ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DENY_PETITION ):
                    
                    tag_id = self._GetTagId( c, tag )
                    
                    hash_ids = self._GetHashIds( c, hashes )
                    
                    self._DenyMappingPetition( c, service_id, tag_id, hash_ids )
                    
                
            
            #
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ) or account.HasPermission( HC.POST_PETITIONS ):
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveTagSiblingPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddTagSiblingPetition
                
                for ( ( old_tag, new_tag ), reason ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PENDING ):
                    
                    old_tag_id = self._GetTagId( c, old_tag )
                    new_tag_id = self._GetTagId( c, new_tag )
                    
                    reason_id = self._GetReasonId( c, reason )
                    
                    petition_method( c, service_id, account_id, old_tag_id, new_tag_id, reason_id, HC.PENDING )
                    
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveTagSiblingPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddTagSiblingPetition
                
                for ( ( old_tag, new_tag ), reason ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION ):
                    
                    old_tag_id = self._GetTagId( c, old_tag )
                    new_tag_id = self._GetTagId( c, new_tag )
                    
                    reason_id = self._GetReasonId( c, reason )
                    
                    petition_method( c, service_id, account_id, old_tag_id, new_tag_id, reason_id, HC.PETITIONED )
                    
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                for ( old_tag, new_tag ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DENY_PEND ):
                    
                    old_tag_id = self._GetTagId( c, old_tag )
                    
                    new_tag_id = self._GetTagId( c, new_tag )
                    
                    self._DenyTagSiblingPetition( c, service_id, old_tag_id, new_tag_id, HC.CONTENT_UPDATE_DENY_PEND )
                    
                
                for ( old_tag, new_tag ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DENY_PETITION ):
                    
                    old_tag_id = self._GetTagId( c, old_tag )
                    
                    new_tag_id = self._GetTagId( c, new_tag )
                    
                    self._DenyTagSiblingPetition( c, service_id, old_tag_id, new_tag_id, HC.CONTENT_UPDATE_DENY_PETITION )
                    
                
            
            #
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ) or account.HasPermission( HC.POST_PETITIONS ):
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveTagParentPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddTagParentPetition
                
                for ( ( old_tag, new_tag ), reason ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PENDING ):
                    
                    old_tag_id = self._GetTagId( c, old_tag )
                    new_tag_id = self._GetTagId( c, new_tag )
                    
                    reason_id = self._GetReasonId( c, reason )
                    
                    petition_method( c, service_id, account_id, old_tag_id, new_tag_id, reason_id, HC.PENDING )
                    
                
                if account.HasPermission( HC.RESOLVE_PETITIONS ): petition_method = self._ApproveTagParentPetition
                elif account.HasPermission( HC.POST_PETITIONS ): petition_method = self._AddTagParentPetition
                
                for ( ( old_tag, new_tag ), reason ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION ):
                    
                    old_tag_id = self._GetTagId( c, old_tag )
                    new_tag_id = self._GetTagId( c, new_tag )
                    
                    reason_id = self._GetReasonId( c, reason )
                    
                    petition_method( c, service_id, account_id, old_tag_id, new_tag_id, reason_id, HC.PETITIONED )
                    
                
            
            if account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                for ( old_tag, new_tag ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DENY_PEND ):
                    
                    old_tag_id = self._GetTagId( c, old_tag )
                    
                    new_tag_id = self._GetTagId( c, new_tag )
                    
                    self._DenyTagParentPetition( c, service_id, old_tag_id, new_tag_id, HC.CONTENT_UPDATE_DENY_PEND )
                    
                
                for ( old_tag, new_tag ) in update.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DENY_PETITION ):
                    
                    old_tag_id = self._GetTagId( c, old_tag )
                    
                    new_tag_id = self._GetTagId( c, new_tag )
                    
                    self._DenyTagParentPetition( c, service_id, old_tag_id, new_tag_id, HC.CONTENT_UPDATE_DENY_PETITION )
                    
                
            
        
    
    def _RefreshUpdateCache( self, c, service_id, affected_timestamps ): c.executemany( 'UPDATE update_cache SET dirty = ? WHERE service_id = ? AND ? BETWEEN begin AND end;', [ ( True, service_id, timestamp ) for timestamp in affected_timestamps ] )
    
    def _RewardAccounts( self, c, service_id, score_type, scores ):
        
        c.executemany( 'INSERT OR IGNORE INTO account_scores ( service_id, account_id, score_type, score ) VALUES ( ?, ?, ?, ? );', [ ( service_id, account_id, score_type, 0 ) for ( account_id, score ) in scores ] )
        
        c.executemany( 'UPDATE account_scores SET score = score + ? WHERE service_id = ? AND account_id = ? and score_type = ?;', [ ( score, service_id, account_id, score_type ) for ( account_id, score ) in scores ] )
        
    
    def _SetExpires( self, c, account_ids, expires ): c.execute( 'UPDATE accounts SET expires = ? WHERE account_id IN ' + HC.SplayListForDB( account_ids ) + ';', ( expires, ) )
    
    def _UnbanKey( self, c, service_id, account_id ): c.execute( 'DELETE FROM bans WHERE service_id = ? AND account_id = ?;', ( account_id, ) )
    
    def _VerifyAccessKey( self, c, service_key, access_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        result = c.execute( 'SELECT 1 FROM accounts WHERE service_id = ? AND hashed_access_key = ?;', ( service_id, sqlite3.Binary( hashlib.sha256( access_key ).digest() ) ) ).fetchone()
        
        if result is None:
            
            result = c.execute( 'SELECT 1 FROM registration_keys WHERE service_id = ? AND access_key = ?;', ( service_id, sqlite3.Binary( access_key ) ) ).fetchone()
            
            if result is None: return False
            
        
        return True
        
    
class DB( ServiceDB ):
    
    def __init__( self ):
        
        self._local_shutdown = False
        self._loop_finished = False
        
        self._db_path = HC.DB_DIR + os.path.sep + 'server.db'
        
        self._jobs = Queue.PriorityQueue()
        self._pubsubs = []
        
        self._over_monthly_data = False
        self._services_over_monthly_data = set()
        
        self._InitDB()
        
        ( db, c ) = self._GetDBCursor()
        
        ( version, ) = c.execute( 'SELECT version FROM version;' ).fetchone()
        
        if version < HC.SOFTWARE_VERSION - 50: raise Exception( 'Your current version of hydrus ' + HC.u( version ) + ' is too old for this version ' + HC.u( HC.SOFTWARE_VERSION ) + ' to update. Please try updating with version ' + HC.u( version + 45 ) + ' or earlier first.' )
        
        while version < HC.SOFTWARE_VERSION:
            
            time.sleep( 1 )
            
            try: c.execute( 'BEGIN IMMEDIATE' )
            except Exception as e: raise HydrusExceptions.DBAccessException( HC.u( e ) )
            
            try:
                
                self._UpdateDB( c, version )
                
                c.execute( 'COMMIT' )
                
            except:
                
                c.execute( 'ROLLBACK' )
                
                raise Exception( 'Updating the server db to version ' + HC.u( version ) + ' caused this error:' + os.linesep + traceback.format_exc() )
                
            
            ( version, ) = c.execute( 'SELECT version FROM version;' ).fetchone()
            
        
        service_keys = self._GetServiceKeys( c )
        
        threading.Thread( target = self.MainLoop, name = 'Database Main Loop' ).start()
        
    
    def _GetDBCursor( self ):
        
        db = sqlite3.connect( self._db_path, timeout=600.0, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        c = db.cursor()
        
        c.execute( 'PRAGMA cache_size = 10000;' )
        c.execute( 'PRAGMA foreign_keys = ON;' )
        c.execute( 'PRAGMA recursive_triggers = ON;' )
        
        return ( db, c )
        
    
    def _InitDB( self ):
        
        if not os.path.exists( self._db_path ):
            
            dirs = ( HC.SERVER_FILES_DIR, HC.SERVER_THUMBNAILS_DIR, HC.SERVER_UPDATES_DIR, HC.SERVER_MESSAGES_DIR )
            
            for dir in dirs:
                
                if not os.path.exists( dir ): os.mkdir( dir )
                
            
            dirs = ( HC.SERVER_FILES_DIR, HC.SERVER_THUMBNAILS_DIR, HC.SERVER_MESSAGES_DIR )
            
            hex_chars = '0123456789abcdef'
            
            for dir in dirs:
                
                for ( one, two ) in itertools.product( hex_chars, hex_chars ):
                    
                    new_dir = dir + os.path.sep + one + two
                    
                    if not os.path.exists( new_dir ): os.mkdir( new_dir )
                    
                
            
            ( db, c ) = self._GetDBCursor()
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            c.execute( 'PRAGMA auto_vacuum = 0;' ) # none
            c.execute( 'PRAGMA journal_mode=WAL;' )
            
            now = HC.GetNow()
            
            c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, type INTEGER, options TEXT_YAML );' )
            
            c.execute( 'CREATE TABLE accounts( account_id INTEGER PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_key BLOB_BYTES, hashed_access_key BLOB_BYTES, account_type_id INTEGER, created INTEGER, expires INTEGER, used_bytes INTEGER, used_requests INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_account_key_index ON accounts ( account_key );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_hashed_access_key_index ON accounts ( hashed_access_key );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_service_id_account_id_index ON accounts ( service_id, account_id );' )
            c.execute( 'CREATE INDEX accounts_service_id_account_type_id_index ON accounts ( service_id, account_type_id );' )
            
            c.execute( 'CREATE TABLE account_scores ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, score_type INTEGER, score INTEGER, PRIMARY KEY( service_id, account_id, score_type ) );' )
            
            c.execute( 'CREATE TABLE account_types ( account_type_id INTEGER PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, title TEXT, account_type TEXT_YAML );' )
            c.execute( 'CREATE UNIQUE INDEX account_types_service_id_account_type_id_index ON account_types ( service_id, account_type_id );' )
            
            c.execute( 'CREATE TABLE bans ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, admin_account_id INTEGER, reason_id INTEGER, created INTEGER, expires INTEGER, PRIMARY KEY( service_id, account_id ) );' )
            c.execute( 'CREATE INDEX bans_expires ON bans ( expires );' )
            
            c.execute( 'CREATE TABLE contacts ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, contact_key BLOB, public_key TEXT, PRIMARY KEY( service_id, account_id ) );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_contact_key_index ON contacts ( contact_key );' )
            
            c.execute( 'CREATE TABLE files_info ( hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, num_words INTEGER );' )
            
            c.execute( 'CREATE TABLE file_map ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, account_id INTEGER, timestamp INTEGER, PRIMARY KEY( service_id, hash_id, account_id ) );' )
            c.execute( 'CREATE INDEX file_map_service_id_account_id_index ON file_map ( service_id, account_id );' )
            c.execute( 'CREATE INDEX file_map_service_id_timestamp_index ON file_map ( service_id, timestamp );' )
            
            c.execute( 'CREATE TABLE file_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY( service_id, account_id, hash_id, status ) );' )
            c.execute( 'CREATE INDEX file_petitions_service_id_account_id_reason_id_index ON file_petitions ( service_id, account_id, reason_id );' )
            c.execute( 'CREATE INDEX file_petitions_service_id_hash_id_index ON file_petitions ( service_id, hash_id );' )
            c.execute( 'CREATE INDEX file_petitions_service_id_status_index ON file_petitions ( service_id, status );' )
            c.execute( 'CREATE INDEX file_petitions_service_id_timestamp_index ON file_petitions ( service_id, timestamp );' )
            
            c.execute( 'CREATE TABLE hashes ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES );' )
            c.execute( 'CREATE UNIQUE INDEX hashes_hash_index ON hashes ( hash );' )
            
            c.execute( 'CREATE TABLE ip_addresses ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, ip TEXT, timestamp INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            
            c.execute( 'CREATE TABLE mapping_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY( service_id, account_id, tag_id, hash_id, status ) );' )
            c.execute( 'CREATE INDEX mapping_petitions_service_id_account_id_reason_id_tag_id_index ON mapping_petitions ( service_id, account_id, reason_id, tag_id );' )
            c.execute( 'CREATE INDEX mapping_petitions_service_id_tag_id_hash_id_index ON mapping_petitions ( service_id, tag_id, hash_id );' )
            c.execute( 'CREATE INDEX mapping_petitions_service_id_status_index ON mapping_petitions ( service_id, status );' )
            c.execute( 'CREATE INDEX mapping_petitions_service_id_timestamp_index ON mapping_petitions ( service_id, timestamp );' )
            
            c.execute( 'CREATE TABLE mappings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, tag_id INTEGER, hash_id INTEGER, account_id INTEGER, timestamp INTEGER, PRIMARY KEY( service_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX mappings_account_id_index ON mappings ( account_id );' )
            c.execute( 'CREATE INDEX mappings_timestamp_index ON mappings ( timestamp );' )
            
            c.execute( 'CREATE TABLE messages ( message_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, timestamp INTEGER );' )
            c.execute( 'CREATE INDEX messages_service_id_account_id_index ON messages ( service_id, account_id );' )
            c.execute( 'CREATE INDEX messages_timestamp_index ON messages ( timestamp );' )
            
            c.execute( 'CREATE TABLE message_statuses ( status_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, status BLOB_BYTES, timestamp INTEGER );' )
            c.execute( 'CREATE INDEX message_statuses_service_id_account_id_index ON message_statuses ( service_id, account_id );' )
            c.execute( 'CREATE INDEX message_statuses_timestamp_index ON message_statuses ( timestamp );' )
            
            c.execute( 'CREATE TABLE messaging_sessions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, session_key BLOB_BYTES, account_id INTEGER, identifier BLOB_BYTES, name TEXT, expiry INTEGER );' )
            
            c.execute( 'CREATE TABLE news ( service_id INTEGER REFERENCES services ON DELETE CASCADE, news TEXT, timestamp INTEGER );' )
            c.execute( 'CREATE INDEX news_timestamp_index ON news ( timestamp );' )
            
            c.execute( 'CREATE TABLE reasons ( reason_id INTEGER PRIMARY KEY, reason TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX reasons_reason_index ON reasons ( reason );' )
            
            c.execute( 'CREATE TABLE registration_keys ( registration_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_type_id INTEGER, account_key BLOB_BYTES, access_key BLOB_BYTES, expiry INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX registration_keys_access_key_index ON registration_keys ( access_key );' )
            
            c.execute( 'CREATE TABLE sessions ( session_key BLOB_BYTES, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, expiry INTEGER );' )
            
            c.execute( 'CREATE TABLE tag_parents ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, old_tag_id INTEGER, new_tag_id INTEGER, timestamp INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, account_id, old_tag_id, new_tag_id, status ) );' )
            c.execute( 'CREATE INDEX tag_parents_service_id_old_tag_id_index ON tag_parents ( service_id, old_tag_id, new_tag_id );' )
            c.execute( 'CREATE INDEX tag_parents_service_id_timestamp_index ON tag_parents ( service_id, timestamp );' )
            c.execute( 'CREATE INDEX tag_parents_service_id_status_index ON tag_parents ( service_id, status );' )
            
            c.execute( 'CREATE TABLE tag_siblings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, old_tag_id INTEGER, new_tag_id INTEGER, timestamp INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, account_id, old_tag_id, status ) );' )
            c.execute( 'CREATE INDEX tag_siblings_service_id_old_tag_id_index ON tag_siblings ( service_id, old_tag_id );' )
            c.execute( 'CREATE INDEX tag_siblings_service_id_timestamp_index ON tag_siblings ( service_id, timestamp );' )
            c.execute( 'CREATE INDEX tag_siblings_service_id_status_index ON tag_siblings ( service_id, status );' )
            
            c.execute( 'CREATE TABLE tags ( tag_id INTEGER PRIMARY KEY, tag TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX tags_tag_index ON tags ( tag );' )
            
            c.execute( 'CREATE TABLE update_cache ( service_id INTEGER REFERENCES services ON DELETE CASCADE, begin INTEGER, end INTEGER, dirty INTEGER_BOOLEAN, PRIMARY KEY( service_id, begin ) );' )
            c.execute( 'CREATE UNIQUE INDEX update_cache_service_id_end_index ON update_cache ( service_id, end );' )
            c.execute( 'CREATE INDEX update_cache_service_id_dirty_index ON update_cache ( service_id, dirty );' )
            
            c.execute( 'CREATE TABLE version ( version INTEGER, year INTEGER, month INTEGER );' )
            
            current_time_struct = time.gmtime()
            
            ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
            
            c.execute( 'INSERT INTO version ( version, year, month ) VALUES ( ?, ?, ? );', ( HC.SOFTWARE_VERSION, current_year, current_month ) )
            
            # set up server admin
            
            service_key = HC.SERVER_ADMIN_KEY
            
            service_type = HC.SERVER_ADMIN
            
            options = HC.DEFAULT_OPTIONS[ HC.SERVER_ADMIN ]
            
            options[ 'port' ] = HC.DEFAULT_SERVER_ADMIN_PORT
            
            c.execute( 'INSERT INTO services ( service_key, type, options ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, options ) )
            
            server_admin_service_id = c.lastrowid
            
            server_admin_account_type = HC.AccountType( 'server admin', [ HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ], ( None, None ) )
            
            c.execute( 'INSERT INTO account_types ( service_id, title, account_type ) VALUES ( ?, ?, ? );', ( server_admin_service_id, 'server admin', server_admin_account_type ) )
            
            c.execute( 'COMMIT' )
            
        
    
    def _MakeBackup( self, c ):
        
        c.execute( 'COMMIT' )
        
        c.execute( 'VACUUM' )
        
        c.execute( 'ANALYZE' )
        
        c.execute( 'BEGIN IMMEDIATE' )
        
        shutil.copy( self._db_path, self._db_path + '.backup' )
        if os.path.exists( self._db_path + '-wal' ): shutil.copy( self._db_path + '-wal', self._db_path + '-wal.backup' )
        
        shutil.rmtree( HC.SERVER_FILES_DIR + '_backup', ignore_errors = True )
        shutil.rmtree( HC.SERVER_THUMBNAILS_DIR + '_backup', ignore_errors = True )
        shutil.rmtree( HC.SERVER_MESSAGES_DIR + '_backup', ignore_errors = True )
        shutil.rmtree( HC.SERVER_UPDATES_DIR + '_backup', ignore_errors = True )
        
        shutil.copytree( HC.SERVER_FILES_DIR, HC.SERVER_FILES_DIR + '_backup' )
        shutil.copytree( HC.SERVER_THUMBNAILS_DIR, HC.SERVER_THUMBNAILS_DIR + '_backup' )
        shutil.copytree( HC.SERVER_MESSAGES_DIR, HC.SERVER_MESSAGES_DIR + '_backup' )
        shutil.copytree( HC.SERVER_UPDATES_DIR, HC.SERVER_UPDATES_DIR + '_backup' )
        
    
    def _UpdateDB( self, c, version ):
        
        if version == 90:
            
            for ( service_id, options ) in c.execute( 'SELECT service_id, options FROM services;' ).fetchall():
                
                options[ 'upnp' ] = None
                
                c.execute( 'UPDATE services SET options = ? WHERE service_id = ?;', ( options, service_id ) )
                
            
        
        if version == 93:
            
            c.execute( 'CREATE TABLE messaging_sessions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, session_key BLOB_BYTES, account_id INTEGER, identifier BLOB_BYTES, name TEXT, expiry INTEGER );' )
            
        
        if version == 108:
            
            data = c.execute( 'SELECT service_id, begin, end FROM update_cache;' ).fetchall()
            
            c.execute( 'DROP TABLE update_cache;' )
            
            c.execute( 'CREATE TABLE update_cache ( service_id INTEGER REFERENCES services ON DELETE CASCADE, begin INTEGER, end INTEGER, dirty INTEGER_BOOLEAN, PRIMARY KEY( service_id, begin ) );' )
            c.execute( 'CREATE UNIQUE INDEX update_cache_service_id_end_index ON update_cache ( service_id, end );' )
            c.execute( 'CREATE INDEX update_cache_service_id_dirty_index ON update_cache ( service_id, dirty );' )
            
            c.executemany( 'INSERT INTO update_cache ( service_id, begin, end, dirty ) VALUES ( ?, ?, ?, ? );', ( ( service_id, begin, end, True ) for ( service_id, begin, end ) in data ) )
            
            stuff_in_updates_dir = dircache.listdir( HC.SERVER_UPDATES_DIR )
            
            for filename in stuff_in_updates_dir:
                
                path = HC.SERVER_UPDATES_DIR + os.path.sep + filename
                
                if os.path.isdir( path ): shutil.rmtree( path )
                else: os.remove( path )
                
            
        
        if version == 128:
            
            c.execute( 'COMMIT' )
            
            c.execute( 'PRAGMA foreign_keys = OFF;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            #
            
            old_account_info = c.execute( 'SELECT * FROM accounts;' ).fetchall()
            
            c.execute( 'DROP TABLE accounts;' )
            
            c.execute( 'CREATE TABLE accounts ( account_id INTEGER PRIMARY KEY, account_key BLOB_BYTES, access_key BLOB_BYTES );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_account_key_index ON accounts ( account_key );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_access_key_index ON accounts ( access_key );' )
            
            for ( account_id, access_key ) in old_account_info:
                
                account_key = os.urandom( 32 )
                
                c.execute( 'INSERT INTO accounts ( account_id, account_key, access_key ) VALUES ( ?, ?, ? );', ( account_id, sqlite3.Binary( account_key ), sqlite3.Binary( access_key ) ) )
                
            
            #
            
            old_r_k_info = c.execute( 'SELECT * FROM registration_keys;' ).fetchall()
            
            c.execute( 'DROP TABLE registration_keys;' )
            
            c.execute( 'CREATE TABLE registration_keys ( registration_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_type_id INTEGER, account_key BLOB_BYTES, access_key BLOB_BYTES, expiry INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX registration_keys_access_key_index ON registration_keys ( access_key );' )
            
            for ( registration_key, service_id, account_type_id, access_key, expires ) in old_r_k_info:
                
                account_key = os.urandom( 32 )
                
                c.execute( 'INSERT INTO registration_keys ( registration_key, service_id, account_type_id, account_key, access_key, expiry ) VALUES ( ?, ?, ?, ?, ?, ? );', ( sqlite3.Binary( registration_key ), service_id, account_type_id, sqlite3.Binary( account_key ), sqlite3.Binary( access_key ), expires ) )
                
            
            #
            
            c.execute( 'COMMIT' )
            
            c.execute( 'PRAGMA foreign_keys = ON;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
        
        if version == 131:
            
            accounts_info = c.execute( 'SELECT * FROM accounts;' ).fetchall()
            account_map_info = c.execute( 'SELECT * FROM account_map;' ).fetchall()
            account_types_info = c.execute( 'SELECT * FROM account_types;' ).fetchall()
            account_type_map_info = c.execute( 'SELECT * FROM account_type_map;' ).fetchall()
            
            accounts_dict = { account_id : ( account_key, hashed_access_key ) for ( account_id, account_key, hashed_access_key ) in accounts_info }
            account_types_dict = { account_type_id : ( title, account_type ) for ( account_type_id, title, account_type ) in account_types_info }
            
            #
            
            c.execute( 'DROP TABLE accounts;' )
            c.execute( 'DROP TABLE account_map;' )
            c.execute( 'DROP TABLE account_types;' )
            c.execute( 'DROP TABLE account_type_map;' )
            
            c.execute( 'CREATE TABLE accounts( account_id INTEGER PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_key BLOB_BYTES, hashed_access_key BLOB_BYTES, account_type_id INTEGER, created INTEGER, expires INTEGER, used_bytes INTEGER, used_requests INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_account_key_index ON accounts ( account_key );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_hashed_access_key_index ON accounts ( hashed_access_key );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_service_id_account_id_index ON accounts ( service_id, account_id );' )
            c.execute( 'CREATE INDEX accounts_service_id_account_type_id_index ON accounts ( service_id, account_type_id );' )
            
            c.execute( 'CREATE TABLE account_types ( account_type_id INTEGER PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, title TEXT, account_type TEXT_YAML );' )
            c.execute( 'CREATE UNIQUE INDEX account_types_service_id_account_type_id_index ON account_types ( service_id, account_type_id );' )
            
            #
            
            account_log_text = ''
            
            existing_account_ids = set()
            existing_account_type_ids = set()
            
            next_account_id = max( accounts_dict.keys() ) + 1
            next_account_type_id = max( account_types_dict.keys() ) + 1
            
            account_tables = [ 'bans', 'contacts', 'file_petitions', 'mapping_petitions', 'mappings', 'messages', 'message_statuses', 'messaging_sessions', 'sessions', 'tag_parents', 'tag_siblings' ]
            account_type_tables = [ 'accounts', 'registration_keys' ]
            
            service_dict = { service_id : options[ 'port' ] for ( service_id, options ) in c.execute( 'SELECT service_id, options FROM services;' ) }
            
            # have to do accounts first because account_types may update it!
            
            for ( service_id, account_id, account_type_id, created, expires, used_bytes, used_requests ) in account_map_info:
                
                ( account_key, hashed_access_key ) = accounts_dict[ account_id ]
                
                if account_id in existing_account_ids:
                    
                    account_key = os.urandom( 32 )
                    access_key = os.urandom( 32 )
                    
                    account_log_text += 'The account at port ' + str( service_dict[ service_id ] ) + ' now uses access key: ' + access_key.encode( 'hex' ) + os.linesep
                    
                    hashed_access_key = hashlib.sha256( access_key ).digest()
                    
                    new_account_id = next_account_id
                    
                    next_account_id += 1
                    
                    for table_name in account_tables:
                        
                        c.execute( 'UPDATE ' + table_name + ' SET account_id = ? WHERE service_id = ? AND account_id = ?;', ( new_account_id, service_id, account_id ) )
                        
                    
                    c.execute( 'UPDATE bans SET admin_account_id = ? WHERE service_id = ? AND admin_account_id = ?;', ( new_account_id, service_id, account_id ) )
                    
                    account_id = new_account_id
                    
                
                existing_account_ids.add( account_id )
                
                c.execute( 'INSERT INTO accounts ( account_id, service_id, account_key, hashed_access_key, account_type_id, created, expires, used_bytes, used_requests ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? );', ( account_id, service_id, sqlite3.Binary( account_key ), sqlite3.Binary( hashed_access_key ), account_type_id, created, expires, used_bytes, used_requests ) )
                
            
            if len( account_log_text ) > 0:
                
                with open( HC.BASE_DIR + os.path.sep + 'update to v132 new access keys.txt', 'wb' ) as f: f.write( account_log_text )
                
            
            for ( service_id, account_type_id ) in account_type_map_info:
                
                ( title, account_type ) = account_types_dict[ account_type_id ]
                
                if account_type_id in existing_account_type_ids:
                    
                    new_account_type_id = next_account_type_id
                    
                    next_account_type_id += 1
                    
                    for table_name in account_type_tables:
                        
                        c.execute( 'UPDATE ' + table_name + ' SET account_type_id = ? WHERE service_id = ? AND account_type_id = ?;', ( new_account_type_id, service_id, account_type_id ) )
                        
                    
                    account_type_id = new_account_type_id
                    
                
                existing_account_type_ids.add( account_type_id )
                
                c.execute( 'INSERT INTO account_types ( account_type_id, service_id, title, account_type ) VALUES ( ?, ?, ?, ? );', ( account_type_id, service_id, title, account_type ) )
                
            
        
        if version == 132:
            
            dirs = ( HC.SERVER_FILES_DIR, HC.SERVER_THUMBNAILS_DIR, HC.SERVER_MESSAGES_DIR )
            
            hex_chars = '0123456789abcdef'
            
            for dir in dirs:
                
                for ( one, two ) in itertools.product( hex_chars, hex_chars ):
                    
                    new_dir = dir + os.path.sep + one + two
                    
                    if not os.path.exists( new_dir ): os.mkdir( new_dir )
                    
                
            
        
        c.execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
    
    def pub_after_commit( self, topic, *args, **kwargs ): self._pubsubs.append( ( topic, args, kwargs ) )
    
    def LoopIsFinished( self ): return self._loop_finished
    
    def MainLoop( self ):
        
        def ProcessJob( c, job ):
            
            def ProcessRead( action, args, kwargs ):
                
                if action == 'access_key': result = self._GetAccessKey( c, *args, **kwargs )
                elif action == 'account': result = self._GetAccount( c, *args, **kwargs )
                elif action == 'account_info': result = self._GetAccountInfo( c, *args, **kwargs )
                elif action == 'account_key_from_access_key': result = self._GetAccountKeyFromAccessKey( c, *args, **kwargs )
                elif action == 'account_key_from_identifier': result = self._GetAccountKeyFromIdentifier( c, *args, **kwargs )
                elif action == 'account_types': result = self._GetAccountTypes( c, *args, **kwargs )
                elif action == 'dirty_updates': result = self._GetDirtyUpdates( c, *args, **kwargs  )
                elif action == 'init': result = self._InitAdmin( c, *args, **kwargs  )
                elif action == 'ip': result = self._GetIPTimestamp( c, *args, **kwargs )
                elif action == 'messaging_sessions': result = self._GetMessagingSessions( c, *args, **kwargs )
                elif action == 'num_petitions': result = self._GetNumPetitions( c, *args, **kwargs )
                elif action == 'petition': result = self._GetPetition( c, *args, **kwargs )
                elif action == 'registration_keys': result = self._GenerateRegistrationKeys( c, *args, **kwargs )
                elif action == 'service_keys': result = self._GetServiceKeys( c, *args, **kwargs )
                elif action == 'service_info': result = self._GetServiceInfo( c, *args, **kwargs )
                elif action == 'services_info': result = self._GetServicesInfo( c, *args, **kwargs )
                elif action == 'sessions': result = self._GetSessions( c, *args, **kwargs )
                elif action == 'stats': result = self._GetStats( c, *args, **kwargs )
                elif action == 'update_ends': result = self._GetUpdateEnds( c, *args, **kwargs )
                elif action == 'verify_access_key': result = self._VerifyAccessKey( c, *args, **kwargs )
                else: raise Exception( 'db received an unknown read command: ' + action )
                
                return result
                
            
            def ProcessWrite( action, args, kwargs ):
                
                if action == 'account': result = self._ModifyAccount( c, *args, **kwargs )
                elif action == 'account_types': result = self._ModifyAccountTypes( c, *args, **kwargs )
                elif action == 'backup': result = self._MakeBackup( c, *args, **kwargs )
                elif action == 'check_data_usage': result = self._CheckDataUsage( c, *args, **kwargs )
                elif action == 'check_monthly_data': result = self._CheckMonthlyData( c, *args, **kwargs )
                elif action == 'clean_update': result = self._CleanUpdate( c, *args, **kwargs )
                elif action == 'clear_bans': result = self._ClearBans( c, *args, **kwargs )
                elif action == 'create_update': result = self._CreateUpdate( c, *args, **kwargs )
                elif action == 'delete_orphans': result = self._DeleteOrphans( c, *args, **kwargs )
                elif action == 'file': result = self._AddFile( c, *args, **kwargs )
                elif action == 'flush_requests_made': result = self._FlushRequestsMade( c, *args, **kwargs )
                elif action == 'messaging_session': result = self._AddMessagingSession( c, *args, **kwargs )
                elif action == 'news': result = self._AddNews( c, *args, **kwargs )
                elif action == 'services': result = self._ModifyServices( c, *args, **kwargs )
                elif action == 'session': result = self._AddSession( c, *args, **kwargs )
                elif action == 'update': result = self._ProcessUpdate( c, *args, **kwargs )
                else: raise Exception( 'db received an unknown write command: ' + action )
                
                return result
                
            
            job_type = job.GetType()
            
            action = job.GetAction()
            
            args = job.GetArgs()
            
            kwargs = job.GetKWArgs()
            
            if job_type in ( 'read', 'read_write' ):
                
                if job_type == 'read': c.execute( 'BEGIN DEFERRED' )
                else: c.execute( 'BEGIN IMMEDIATE' )
                
                try:
                    
                    result = ProcessRead( action, args, kwargs )
                    
                    c.execute( 'COMMIT' )
                    
                    for ( topic, args, kwargs ) in self._pubsubs: HC.pubsub.pub( topic, *args, **kwargs )
                    
                    job.PutResult( result )
                    
                except Exception as e:
                    
                    c.execute( 'ROLLBACK' )
                    
                    ( exception_type, value, tb ) = sys.exc_info()
                    
                    new_e = type( e )( os.linesep.join( traceback.format_exception( exception_type, value, tb ) ) )
                    
                    job.PutResult( new_e )
                    
                
            else:
                
                if job_type == 'write': c.execute( 'BEGIN IMMEDIATE' )
                
                try:
                    
                    result = ProcessWrite( action, args, kwargs )
                    
                    if job_type == 'write': c.execute( 'COMMIT' )
                    
                    for ( topic, args, kwargs ) in self._pubsubs: HC.pubsub.pub( topic, *args, **kwargs )
                    
                    job.PutResult( result )
                    
                except Exception as e:
                    
                    if job_type == 'write': c.execute( 'ROLLBACK' )
                    
                    ( exception_type, value, tb ) = sys.exc_info()
                    
                    new_e = type( e )( os.linesep.join( traceback.format_exception( exception_type, value, tb ) ) )
                    
                    job.PutResult( new_e )
                    
                
            
        
        ( db, c ) = self._GetDBCursor()
        
        while not ( ( self._local_shutdown or HC.shutdown ) and self._jobs.empty() ):
            
            try:
                
                ( priority, job ) = self._jobs.get( timeout = 1 )
                
                self._pubsubs = []
                
                try:
                    
                    ProcessJob( c, job )
                    
                except:
                    
                    self._jobs.put( ( priority, job ) ) # couldn't lock db; put job back on queue
                    
                    time.sleep( 5 )
                    
                
            except: pass # no jobs this second; let's see if we should shutdown
            
        
        c.close()
        db.close()
        
        self._loop_finished = True
        
    
    def Read( self, action, priority, *args, **kwargs ):
        
        job_type = 'read'
        
        synchronous = True
        
        job = HC.JobDatabase( action, job_type, synchronous, *args, **kwargs )
        
        self._jobs.put( ( priority + 1, job ) ) # +1 so all writes of equal priority can clear out first
        
        return job.GetResult()
        
    
    def Shutdown( self ): self._local_shutdown = True
    
    def Write( self, action, priority, *args, **kwargs ):
        
        job_type = 'write'
        
        synchronous = True
        
        job = HC.JobDatabase( action, job_type, synchronous, *args, **kwargs )
        
        self._jobs.put( ( priority, job ) )
        
        return job.GetResult()
        
    
def DAEMONCheckDataUsage(): HC.app.WriteDaemon( 'check_data_usage' )

def DAEMONCheckMonthlyData(): HC.app.WriteDaemon( 'check_monthly_data' )

def DAEMONClearBans(): HC.app.WriteDaemon( 'clear_bans' )

def DAEMONDeleteOrphans(): HC.app.WriteDaemon( 'delete_orphans' )

def DAEMONFlushRequestsMade( all_requests ): HC.app.WriteDaemon( 'flush_requests_made', all_requests )

def DAEMONGenerateUpdates():
    
    dirty_updates = HC.app.ReadDaemon( 'dirty_updates' )
    
    for ( service_key, tuples ) in dirty_updates.items():
        
        for ( begin, end ) in tuples: HC.app.WriteDaemon( 'clean_update', service_key, begin, end )
        
    
    update_ends = HC.app.ReadDaemon( 'update_ends' )
    
    for ( service_key, biggest_end ) in update_ends.items():
        
        now = HC.GetNow()
        
        next_begin = biggest_end + 1
        next_end = biggest_end + HC.UPDATE_DURATION
        
        while next_end < now:
            
            HC.app.WriteDaemon( 'create_update', service_key, next_begin, next_end )
            
            biggest_end = next_end
            
            now = HC.GetNow()
            
            next_begin = biggest_end + 1
            next_end = biggest_end + HC.UPDATE_DURATION
            
        
    
def DAEMONUPnP():
    
    local_ip = HydrusNATPunch.GetLocalIP()
    
    current_mappings = HydrusNATPunch.GetUPnPMappings()
    
    our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) in current_mappings }
    
    services_info = HC.app.ReadDaemon( 'services_info' )
    
    for ( service_key, service_type, options ) in services_info:
        
        internal_port = options[ 'port' ]
        upnp = options[ 'upnp' ]
        
        if ( local_ip, internal_port ) in our_mappings:
            
            current_external_port = our_mappings[ ( local_ip, internal_port ) ]
            
            if current_external_port != upnp: HydrusNATPunch.RemoveUPnPMapping( current_external_port, 'TCP' )
            
        
    
    for ( service_key, service_type, options ) in services_info:
        
        internal_port = options[ 'port' ]
        upnp = options[ 'upnp' ]
        
        if upnp is not None and ( local_ip, internal_port ) not in our_mappings:
            
            external_port = upnp
            
            protocol = 'TCP'
            
            description = HC.service_string_lookup[ service_type ] + ' at ' + local_ip + ':' + str( internal_port )
            
            duration = 3600
            
            HydrusNATPunch.AddUPnPMapping( local_ip, internal_port, external_port, protocol, description, duration = duration )
            
        
    