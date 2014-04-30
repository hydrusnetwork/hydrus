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

class FileDB():
    
    def _AddFile( self, c, service_identifier, account, file_dict ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        account_id = account.GetAccountId()
        
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
            
            options = self._GetOptions( c, service_identifier )
            
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
        
        petitioner_account_identifier = HC.AccountIdentifier( account_id = account_id )
        
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
    
    def _GetIPTimestamp( self, c, service_identifier, hash ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
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
        
    
class MessageDB():
    
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
        
    
class TagDB():
    
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
            
            petitioner_account_identifier = HC.AccountIdentifier( account_id = account_id )
            
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
        
    
class RatingDB():
    
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
    
    def _AccountTypeExists( self, c, service_id, title ): return c.execute( 'SELECT 1 FROM account_types, account_type_map USING ( account_type_id ) WHERE service_id = ? AND title = ?;', ( service_id, title ) ).fetchone() is not None
    
    def _AddNews( self, c, service_identifier, news ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        now = HC.GetNow()
        
        c.execute( 'INSERT INTO news ( service_id, news, timestamp ) VALUES ( ?, ?, ? );', ( service_id, news, now ) )
        
    
    def _AddMessagingSession( self, c, service_identifier, session_key, account, identifier, name, expiry ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        account_id = account.GetAccountId()
        
        c.execute( 'INSERT INTO sessions ( service_id, session_key, account_id, identifier, name, expiry ) VALUES ( ?, ?, ?, ?, ?, ? );', ( service_id, sqlite3.Binary( session_key ), account_id, sqlite3.Binary( identifier ), name, expiry ) )
        
    
    def _AddSession( self, c, session_key, service_identifier, account, expiry ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        account_id = account.GetAccountId()
        
        c.execute( 'INSERT INTO sessions ( session_key, service_id, account_id, expiry ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( session_key ), service_id, account_id, expiry ) )
        
    
    def _AddToExpiry( self, c, service_id, account_ids, timespan ): c.execute( 'UPDATE account_map SET expires = expires + ? WHERE service_id = ? AND account_id IN ' + HC.SplayListForDB( account_ids ) + ';', ( timespan, service_id ) )
    
    def _Ban( self, c, service_id, action, admin_account_id, subject_account_ids, reason_id, expiry = None, lifetime = None ):
        
        splayed_subject_account_ids = HC.SplayListForDB( subject_account_ids )
        
        now = HC.GetNow()
        
        if expiry is not None: pass
        elif lifetime is not None: expiry = now + lifetime
        else: expiry = None
        
        c.executemany( 'INSERT OR IGNORE INTO bans ( service_id, account_id, admin_account_id, reason_id, created, expires ) VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, subject_account_id, admin_account_id, reason_id, now, expiry ) for subject_account_id in subject_account_ids ] )
        
        c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
        c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status = ?;', ( service_id, HC.PETITIONED ) )
        
        c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) )
        
        c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ' AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) )
        
        if action == HC.SUPERBAN:
            
            hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ? AND account_id IN ' + splayed_subject_account_ids + ';', ( service_id, ) ) ]
            
            if len( hash_ids ) > 0: self._DeleteLocalFiles( c, admin_account_id, hash_ids, reason_id )
            
            mappings_dict = HC.BuildKeyToListDict( c.execute( 'SELECT tag_id, hash_id FROM mappings WHERE service_id = ? AND account_id IN ' + splayed_subject_keys_ids + ';', ( service_id, ) ) )
            
            if len( mappings_dict ) > 0:
                
                for ( tag_id, hash_ids ) in mappings_dict.items(): self._DeleteMappings( c, admin_account_id, tag_id, hash_ids, reason_id )
                
            
        
    
    def _ChangeAccountType( self, c, service_id, account_ids, account_type_id ):
        
        splayed_account_ids = HC.SplayListForDB( account_ids )
        
        c.execute( 'UPDATE account_map SET account_type_id = ? WHERE service_id = ? AND account_id IN ' + splayed_account_ids + ';', ( account_type_id, service_id ) )
        
    
    def _CheckDataUsage( self, c ):
        
        ( version_year, version_month ) = c.execute( 'SELECT year, month FROM version;' ).fetchone()
        
        current_time_struct = time.gmtime()
        
        ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
        
        if version_year != current_year or version_month != current_month:
            
            c.execute( 'UPDATE version SET year = ?, month = ?;', ( current_year, current_month ) )
            
            c.execute( 'UPDATE account_map SET used_bytes = ?, used_requests = ?;', ( 0, 0 ) )
            
            self.pub_after_commit( 'update_all_session_accounts' )
            
        
    
    def _CheckMonthlyData( self, c ):
        
        service_identifiers = self._GetServiceIdentifiers( c )
        
        running_total = 0
        
        self._services_over_monthly_data = set()
        
        for service_identifier in service_identifiers:
            
            service_id = self._GetServiceId( c, service_identifier )
            
            options = self._GetOptions( c, service_identifier )
            
            service_type = service_identifier.GetType()
            
            if service_type != HC.SERVER_ADMIN:
                
                ( total_used_bytes, ) = c.execute( 'SELECT SUM( used_bytes ) FROM account_map WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                if total_used_bytes is None: total_used_bytes = 0
                
                running_total += total_used_bytes
                
                if 'max_monthly_data' in options:
                    
                    max_monthly_data = options[ 'max_monthly_data' ]
                    
                    if max_monthly_data is not None and total_used_bytes > max_monthly_data: self._services_over_monthly_data.add( service_identifier )
                    
                
            
        
        # have to do this after
        
        server_admin_options = self._GetOptions( c, HC.SERVER_ADMIN_IDENTIFIER )
        
        self._over_monthly_data = False
        
        if 'max_monthly_data' in server_admin_options:
            
            max_monthly_data = server_admin_options[ 'max_monthly_data' ]
            
            if max_monthly_data is not None and running_total > max_monthly_data: self._over_monthly_data = True
            
        
    
    def _CleanUpdate( self, c, service_identifier, begin, end ):
        
        service_type = service_identifier.GetType()
        
        service_id = self._GetServiceId( c, service_identifier )
        
        if service_type == HC.FILE_REPOSITORY: clean_update = self._GenerateFileUpdate( c, service_id, begin, end )
        elif service_type == HC.TAG_REPOSITORY: clean_update = self._GenerateTagUpdate( c, service_id, begin, end )
        
        path = SC.GetExpectedUpdatePath( service_identifier, begin )
        
        with open( path, 'wb' ) as f: f.write( yaml.safe_dump( clean_update ) )
        
        c.execute( 'UPDATE update_cache SET dirty = ? WHERE service_id = ? AND begin = ?;', ( False, service_id, begin ) )
        
    
    def _ClearBans( self, c ):
        
        now = HC.GetNow()
        
        c.execute( 'DELETE FROM bans WHERE expires < ?;', ( now, ) )
        
    
    def _CreateUpdate( self, c, service_identifier, begin, end ):
        
        service_type = service_identifier.GetType()
        
        service_id = self._GetServiceId( c, service_identifier )
        
        if service_type == HC.FILE_REPOSITORY: update = self._GenerateFileUpdate( c, service_id, begin, end )
        elif service_type == HC.TAG_REPOSITORY: update = self._GenerateTagUpdate( c, service_id, begin, end )
        
        path = SC.GetExpectedUpdatePath( service_identifier, begin )
        
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
        
    
    def _FlushRequestsMade( self, c, all_services_requests ):
        
        all_services_request_dict = HC.BuildKeyToListDict( [ ( service_identifier, ( account, num_bytes ) ) for ( service_identifier, account, num_bytes ) in all_services_requests ] )
        
        for ( service_identifier, requests ) in all_services_request_dict.items():
            
            service_id = self._GetServiceId( c, service_identifier )
            
            requests_dict = HC.BuildKeyToListDict( requests )
            
            c.executemany( 'UPDATE account_map SET used_bytes = used_bytes + ?, used_requests = used_requests + ? WHERE service_id = ? AND account_id = ?;', [ ( sum( num_bytes_list ), len( num_bytes_list ), service_id, account.GetAccountId() ) for ( account, num_bytes_list ) in requests_dict.items() ] )
            
        
    
    def _GenerateRegistrationKeys( self, c, service_identifier, num, title, lifetime = None ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        account_type_id = self._GetAccountTypeId( c, service_id, title )
        
        now = HC.GetNow()
        
        if lifetime is not None: expiry = now + lifetime
        else: expiry = None
        
        keys = [ ( os.urandom( HC.HYDRUS_KEY_LENGTH ), os.urandom( HC.HYDRUS_KEY_LENGTH ) ) for i in range( num ) ]
        
        c.executemany( 'INSERT INTO registration_keys ( registration_key, service_id, account_type_id, access_key, expiry ) VALUES ( ?, ?, ?, ?, ? );', [ ( sqlite3.Binary( hashlib.sha256( registration_key ).digest() ), service_id, account_type_id, sqlite3.Binary( access_key ), expiry ) for ( registration_key, access_key ) in keys ] )
        
        return [ registration_key for ( registration_key, access_key ) in keys ]
        
    
    def _GetAccessKey( self, c, registration_key ):
        
        try: ( access_key, ) = c.execute( 'SELECT access_key FROM registration_keys WHERE registration_key = ?;', ( sqlite3.Binary( hashlib.sha256( registration_key ).digest() ), ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'The service could not find that registration key in its database.' )
        
        return access_key
        
    
    def _GetAccount( self, c, service_identifier, account_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        if account_identifier.HasAccessKey():
            
            access_key = account_identifier.GetData()
            
            try: ( account_id, account_type, created, expiry, used_bytes, used_requests ) = c.execute( 'SELECT account_id, account_type, created, expires, used_bytes, used_requests FROM account_types, ( accounts, account_map USING ( account_id ) ) USING ( account_type_id ) WHERE service_id = ? AND access_key = ?;', ( service_id, sqlite3.Binary( hashlib.sha256( access_key ).digest() ) ) ).fetchone()
            except:
                
                # we do not delete the registration_key (and hence the raw access_key)
                # until the first attempt to create a session to make sure the user
                # has the access_key saved somewhere
                
                try: ( account_type_id, expiry ) = c.execute( 'SELECT account_type_id, expiry FROM registration_keys WHERE access_key = ?;', ( sqlite3.Binary( access_key ), ) ).fetchone()
                except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
                
                c.execute( 'DELETE FROM registration_keys WHERE access_key = ?;', ( sqlite3.Binary( access_key ), ) )
                
                #
                
                c.execute( 'INSERT INTO accounts ( access_key ) VALUES ( ? );', ( sqlite3.Binary( hashlib.sha256( access_key ).digest() ), ) )
                
                account_id = c.lastrowid
                
                now = HC.GetNow()
                
                c.execute( 'INSERT INTO account_map ( service_id, account_id, account_type_id, created, expires, used_bytes, used_requests ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, account_id, account_type_id, now, expiry, 0, 0 ) )
                
                ( account_id, account_type, created, expiry, used_bytes, used_requests ) = c.execute( 'SELECT account_id, account_type, created, expires, used_bytes, used_requests FROM account_types, ( accounts, account_map USING ( account_id ) ) USING ( account_type_id ) WHERE service_id = ? AND access_key = ?;', ( service_id, sqlite3.Binary( hashlib.sha256( access_key ).digest() ) ) ).fetchone()
                
            
        elif account_identifier.HasAccountId():
            
            account_id = account_identifier.GetData()
            
            try: ( account_id, account_type, created, expiry, used_bytes, used_requests ) = c.execute( 'SELECT account_id, account_type, created, expires, used_bytes, used_requests FROM account_types, account_map USING ( account_type_id ) WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
            except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
            
        elif account_identifier.HasHash():
            
            hash = account_identifier.GetData()
            
            try: hash_id = self._GetHashId( c, hash )
            except: raise HydrusExceptions.ForbiddenException( 'The service could not find that hash in its database.' )
            
            try:
                
                result = c.execute( 'SELECT account_id, account_type, created, expires, used_bytes, used_requests FROM account_types, ( accounts, ( account_map, file_map USING ( service_id, account_id ) ) USING ( account_id ) ) USING ( account_type_id ) WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
                
                if result is None: result = c.execute( 'SELECT account_id, account_type, created, expires, used_bytes, used_requests FROM account_types, ( accounts, ( account_map, file_petitions USING ( service_id, account_id ) ) USING ( account_id ) ) USING ( account_type_id ) WHERE service_id = ? AND hash_id = ? AND status = ?;', ( service_id, hash_id, HC.DELETED ) ).fetchone()
                
                ( account_id, account_type, created, expiry, used_bytes, used_requests ) = result
                
            except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
            
        elif account_identifier.HasMapping():
            
            try:
                
                ( hash, tag ) = account_identifier.GetData()
                
                hash_id = self._GetHashId( c, hash )
                tag_id = self._GetTagId( c, tag )
                
            except: raise HydrusExceptions.ForbiddenException( 'The service could not find that mapping in its database.' )
            
            try: ( account_id, account_type, created, expiry, used_bytes, used_requests ) = c.execute( 'SELECT account_id, account_type, created, expires, used_bytes, used_requests FROM account_types, ( accounts, ( account_map, mappings USING ( service_id, account_id ) ) USING ( account_id ) ) USING ( account_type_id ) WHERE service_id = ? AND tag_id = ? AND hash_id = ?;', ( service_id, tag_id, hash_id ) ).fetchone()
            except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
            
        
        used_data = ( used_bytes, used_requests )
        
        banned_info = c.execute( 'SELECT reason, created, expires FROM bans, reasons USING ( reason_id ) WHERE service_id = ? AND account_id = ?;', ( service_id, account_id ) ).fetchone()
        
        return HC.Account( account_id, account_type, created, expiry, used_data, banned_info = banned_info )
        
    
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
        
    
    def _GetAccountIdentifier( self, c, access_key ):
        
        try: ( account_id, ) = c.execute( 'SELECT account_id FROM accounts WHERE access_key = ?;', ( sqlite3.Binary( hashlib.sha256( access_key ).digest() ), ) ).fetchone()
        except: raise HydrusExceptions.ForbiddenException( 'The service could not find that account in its database.' )
        
        return HC.AccountIdentifier( account_id = account_id )
        
    
    def _GetAccountIdFromContactKey( self, c, service_id, contact_key ):
        
        try:
            
            ( account_id, ) = c.execute( 'SELECT account_id FROM contacts WHERE service_id = ? AND contact_key = ?;', ( service_id, sqlite3.Binary( contact_key ) ) ).fetchone()
            
        except: raise HydrusExceptions.NotFoundException( 'Could not find that contact key!' )
        
        return account_id
        
    
    def _GetAccountIds( self, c, access_keys ):
        
        account_ids = []
        
        if type( access_keys ) == set: access_keys = list( access_keys )
        
        for i in range( 0, len( access_keys ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            access_keys_subset = access_keys[ i : i + 250 ]
            
            account_ids.extend( [ account_id for ( account_id , ) in c.execute( 'SELECT account_id FROM accounts WHERE access_key IN (' + ','.join( '?' * len( access_keys_subset ) ) + ');', [ sqlite3.Binary( hashlib.sha256( access_key ).digest() ) for access_key in access_keys_subset ] ) ] )
            
        
        return account_ids
        
    
    def _GetAccountInfo( self, c, service_identifier, account_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        account = self._GetAccount( c, service_identifier, account_identifier )
        
        account_id = account.GetAccountId()
        
        service_type = service_identifier.GetType()
        
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
        
        result = c.execute( 'SELECT account_type_id FROM account_types, account_type_map USING ( account_type_id ) WHERE service_id = ? AND title = ?;', ( service_id, title ) ).fetchone()
        
        if result is None: raise HydrusExceptions.NotFoundException( 'Could not find account title ' + HC.u( title ) + ' in db for this service.' )
        
        ( account_type_id, ) = result
        
        return account_type_id
        
    
    def _GetAccountTypes( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        return [ account_type for ( account_type, ) in c.execute( 'SELECT account_type FROM account_type_map, account_types USING ( account_type_id ) WHERE service_id = ?;', ( service_id, ) ) ]
        
    
    def _GetDirtyUpdates( self, c ):
        
        service_ids_to_tuples = HC.BuildKeyToListDict( [ ( service_id, ( begin, end ) ) for ( service_id, begin, end ) in c.execute( 'SELECT service_id, begin, end FROM update_cache WHERE dirty = ?;', ( True, ) ) ] )
        
        service_identifiers_to_tuples = {}
        
        for ( service_id, tuples ) in service_ids_to_tuples.items():
            
            service_identifier = self._GetServiceIdentifier( c, service_id )
            
            service_identifiers_to_tuples[ service_identifier ] = tuples
            
        
        return service_identifiers_to_tuples
        
    
    def _GetMessagingSessions( self, c ):
        
        now = HC.GetNow()
        
        c.execute( 'DELETE FROM messaging_sessions WHERE ? > expiry;', ( now, ) )
        
        existing_session_ids = HC.BuildKeyToListDict( [ ( service_id, ( session_key, account_id, identifier, name, expiry ) ) for ( service_id, identifier, name, expiry ) in c.execute( 'SELECT service_id, session_key, account_id, identifier, name, expiry FROM messaging_sessions;' ) ] )
        
        existing_sessions = {}
        
        for ( service_id, tuples ) in existing_session_ids.items():
            
            service_identifier = self._GetServiceIdentifier( c, service_id )
            
            processed_tuples = []
            
            for ( account_id, identifier, name, expiry ) in tuples:
                
                account_identifier = HC.AccountIdentifier( account_id = account_id )
                
                account = self._GetAccount( c, service_identifier, account_identifier )
                
                processed_tuples.append( ( account, identifier, name, expiry ) )
                
            
            existing_sessions[ service_identifier ] = processed_tuples
            
        
        return existing_sessions
        
    
    def _GetNumPetitions( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        service_type = service_identifier.GetType()
        
        if service_type == HC.FILE_REPOSITORY:
            
            ( num_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT account_id, reason_id FROM file_petitions WHERE service_id = ? AND status = ? );', ( service_id, HC.PETITIONED ) ).fetchone()
            
        elif service_type == HC.TAG_REPOSITORY:
            
            ( num_mapping_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT account_id, tag_id, reason_id FROM mapping_petitions WHERE service_id = ? AND status = ? );', ( service_id, HC.PETITIONED ) ).fetchone()
            
            ( num_tag_sibling_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM tag_siblings WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
            
            ( num_tag_parent_petitions, ) = c.execute( 'SELECT COUNT( * ) FROM tag_parents WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.PENDING, HC.PETITIONED ) ).fetchone()
            
            num_petitions = num_mapping_petitions + num_tag_sibling_petitions + num_tag_parent_petitions
            
        
        return num_petitions
        
    
    def _GetOptions( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        ( options, ) = c.execute( 'SELECT options FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return options
        
    
    def _GetPetition( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        service_type = service_identifier.GetType()
        
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
            
        
    
    def _GetServiceId( self, c, service_identifier ):
        
        service_key = service_identifier.GetServiceKey()
        
        result = c.execute( 'SELECT service_id FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_id, ) = result
        
        return service_id
        
    
    def _GetServiceIds( self, c, limited_types = HC.ALL_SERVICES ): return [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM services WHERE type IN ' + HC.SplayListForDB( limited_types ) + ';' ) ]
    
    def _GetServiceIdentifier( self, c, service_id ):
        
        ( service_key, service_type ) = c.execute( 'SELECT service_key, type FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return HC.ServerServiceIdentifier( service_key, service_type )
        
    
    def _GetServiceIdentifiers( self, c, limited_types = HC.ALL_SERVICES ): return [ HC.ServerServiceIdentifier( service_key, service_type ) for ( service_key, service_type ) in c.execute( 'SELECT service_key, type FROM services WHERE type IN '+ HC.SplayListForDB( limited_types ) + ';' ) ]
    
    def _GetServiceType( self, c, service_id ):
        
        result = c.execute( 'SELECT type FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_type, ) = result
        
        return service_type
        
    
    def _GetServicesInfo( self, c, limited_types = HC.ALL_SERVICES ):
        
        service_identifiers = self._GetServiceIdentifiers( c, limited_types )
        
        services_info = [ ( service_identifier, self._GetOptions( c, service_identifier ) ) for service_identifier in service_identifiers ]
        
        return services_info
        
    
    def _GetSessions( self, c ):
        
        now = HC.GetNow()
        
        c.execute( 'DELETE FROM sessions WHERE ? > expiry;', ( now, ) )
        
        sessions = []
        
        results = c.execute( 'SELECT session_key, service_id, account_id, expiry FROM sessions;' ).fetchall()
        
        service_ids_to_service_identifiers = {}
        
        for ( session_key, service_id, account_id, expiry ) in results:
            
            if service_id not in service_ids_to_service_identifiers: service_ids_to_service_identifiers[ service_id ] = self._GetServiceIdentifier( c, service_id )
            
            service_identifier = service_ids_to_service_identifiers[ service_id ]
            
            account_identifier = HC.AccountIdentifier( account_id = account_id )
            
            account = self._GetAccount( c, service_identifier, account_identifier )
            
            sessions.append( ( session_key, service_identifier, account, expiry ) )
            
        
        return sessions
        
    
    def _GetStats( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        stats = {}
        
        ( stats[ 'num_accounts' ], ) = c.execute( 'SELECT COUNT( * ) FROM account_map WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        ( stats[ 'num_banned' ], ) = c.execute( 'SELECT COUNT( * ) FROM bans WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return stats
        
    
    def _GetUpdateEnds( self, c ):
        
        service_ids = self._GetServiceIds( c, HC.REPOSITORIES )
        
        results = {}
        
        for service_id in service_ids:
            
            ( end, ) = c.execute( 'SELECT end FROM update_cache WHERE service_id = ? ORDER BY end DESC LIMIT 1;', ( service_id, ) ).fetchone()
            
            service_identifier = self._GetServiceIdentifier( c, service_id )
            
            results[ service_identifier ] = end
            
        
        return results
        
    
    def _InitAdmin( self, c ):
        
        if c.execute( 'SELECT 1 FROM account_map;' ).fetchone() is not None: raise HydrusExceptions.ForbiddenException( 'This server is already initialised!' )
        
        service_id = self._GetServiceId( c, HC.SERVER_ADMIN_IDENTIFIER )
        
        # this is a little odd, but better to keep it all the same workflow
        
        num = 1
        
        title = 'server admin'
        
        ( registration_key, ) = self._GenerateRegistrationKeys( c, HC.SERVER_ADMIN_IDENTIFIER, num, title )
        
        access_key = self._GetAccessKey( c, registration_key )
        
        return access_key
        
    
    def _ModifyAccount( self, c, service_identifier, admin_account, action, subject_identifiers, kwargs ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        admin_account_id = admin_account.GetAccountId()
        
        subjects = [ self._GetAccount( c, service_identifier, subject_identifier ) for subject_identifier in subject_identifiers ]
        
        subject_account_ids = [ subject.GetAccountId() for subject in subjects ]
        
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
                
                self._ChangeAccountType( c, service_id, subject_account_ids, account_type_id )
                
            elif action == HC.ADD_TO_EXPIRY:
                
                timespan = kwargs[ 'timespan' ]
                
                self._AddToExpiry( c, service_id, subject_account_ids, timespan )
                
            elif action == HC.SET_EXPIRY:
                
                expiry = kwargs[ 'expiry' ]
                
                self._SetExpiry( c, service_id, subject_account_ids, expiry )
                
            
        
    
    def _ModifyAccountTypes( self, c, service_identifier, edit_log ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        for ( action, details ) in edit_log:
            
            if action == HC.ADD:
                
                account_type = details
                
                title = account_type.GetTitle()
                
                if self._AccountTypeExists( c, service_id, title ): raise HydrusExceptions.ForbiddenException( 'Already found account type ' + HC.u( title ) + ' in the db for this service, so could not add!' )
                
                c.execute( 'INSERT OR IGNORE INTO account_types ( title, account_type ) VALUES ( ?, ? );', ( title, account_type ) )
                
                account_type_id = c.lastrowid
                
                c.execute( 'INSERT OR IGNORE INTO account_type_map ( service_id, account_type_id ) VALUES ( ?, ? );', ( service_id, account_type_id ) )
                
            elif action == HC.DELETE:
                
                ( title, new_title ) = details
                
                account_type_id = self._GetAccountTypeId( c, service_id, title )
                
                new_account_type_id = self._GetAccountTypeId( c, service_id, new_title )
                
                c.execute( 'UPDATE account_map SET account_type_id = ? WHERE service_id = ? AND account_type_id = ?;', ( new_account_type_id, service_id, account_type_id ) )
                c.execute( 'UPDATE registration_keys SET account_type_id = ? WHERE service_id = ? AND account_type_id = ?;', ( new_account_type_id, service_id, account_type_id ) )
                
                c.execute( 'DELETE FROM account_types WHERE account_type_id = ?;', ( account_type_id, ) )
                
                c.execute( 'DELETE FROM account_type_map WHERE service_id = ? AND account_type_id = ?;', ( service_id, account_type_id ) )
                
            elif action == HC.EDIT:
                
                ( old_title, account_type ) = details
                
                title = account_type.GetTitle()
                
                if old_title != title and self._AccountTypeExists( c, service_id, title ): raise HydrusExceptions.ForbiddenException( 'Already found account type ' + HC.u( title ) + ' in the database, so could not rename ' + HC.u( old_title ) + '!' )
                
                account_type_id = self._GetAccountTypeId( c, service_id, old_title )
                
                c.execute( 'UPDATE account_types SET title = ?, account_type = ? WHERE account_type_id = ?;', ( title, account_type, account_type_id ) )
                
            
        
    
    def _ModifyServices( self, c, account, edit_log ):
        
        account_id = account.GetAccountId()
        
        service_identifiers_to_access_keys = []
        
        modified_services = {}
        
        now = HC.GetNow()
        
        for ( action, data ) in edit_log:
            
            if action == HC.ADD:
                
                ( service_identifier, options ) = data
                
                service_key = service_identifier.GetServiceKey()
                service_type = service_identifier.GetType()
                
                c.execute( 'INSERT INTO services ( service_key, type, options ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, options ) )
                
                service_id = c.lastrowid
                
                service_admin_account_type = HC.AccountType( 'service admin', [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN ], ( None, None ) )
                
                c.execute( 'INSERT INTO account_types ( title, account_type ) VALUES ( ?, ? );', ( 'service admin', service_admin_account_type ) )
                
                service_admin_account_type_id = c.lastrowid
                
                c.execute( 'INSERT INTO account_type_map ( service_id, account_type_id ) VALUES ( ?, ? );', ( service_id, service_admin_account_type_id ) )
                
                [ registration_key ] = self._GenerateRegistrationKeys( c, service_identifier, 1, 'service admin', None )
                
                access_key = self._GetAccessKey( c, registration_key )
                
                service_identifiers_to_access_keys.append( ( service_identifier, access_key ) )
                
                if service_type in HC.REPOSITORIES:
                    
                    begin = 0
                    end = HC.GetNow()
                    
                    self._CreateUpdate( c, service_identifier, begin, end )
                    
                
                modified_services[ service_identifier ] = options
                
            elif action == HC.DELETE:
                
                service_identifier = data
                
                service_id = self._GetServiceId( c, service_identifier )
                
                c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
                
                modified_services[ service_identifier ] = {}
                
            elif action == HC.EDIT:
                
                ( service_identifier, options ) = data
                
                service_id = self._GetServiceId( c, service_identifier )
                
                c.execute( 'UPDATE services SET options = ? WHERE service_id = ?;', ( options, service_id ) )
                
                modified_services[ service_identifier ] = options
                
            
        
        for ( service_identifier, options ) in modified_services.items(): self.pub_after_commit( 'restart_service', service_identifier, options )
        
        return service_identifiers_to_access_keys
        
    
    def _ProcessUpdate( self, c, service_identifier, account, update ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        account_id = account.GetAccountId()
        
        service_type = service_identifier.GetType()
        
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
        
    
    def _SetExpiry( self, c, service_id, account_ids, expiry ): c.execute( 'UPDATE account_map SET expires = ? WHERE service_id = ? AND account_id IN ' + HC.SplayListForDB( account_ids ) + ';', ( expiry, service_id ) )
    
    def _SetOptions( self, c, service_identifier, options ):
        
        service_id = self._GetServiceIdentifier( c, service_identifier )
        
        c.execute( 'UPDATE services SET options = ? WHERE service_id = ?;', ( options, service_id ) )
        
        self.pub_after_commit( 'restart_service', service_identifier )
        self.pub_after_commit( 'notify_new_options' )
        
    
    def _UnbanKey( self, c, service_id, account_id ): c.execute( 'DELETE FROM bans WHERE service_id = ? AND account_id = ?;', ( account_id, ) )
    
class DB( ServiceDB ):
    
    def __init__( self ):
        
        self._db_path = HC.DB_DIR + os.path.sep + 'server.db'
        
        self._jobs = Queue.PriorityQueue()
        self._pubsubs = []
        
        self._over_monthly_data = False
        self._services_over_monthly_data = set()
        
        self._InitDB()
        
        ( db, c ) = self._GetDBCursor()
        
        ( version, ) = c.execute( 'SELECT version FROM version;' ).fetchone()
        
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
            
        
        service_identifiers = self._GetServiceIdentifiers( c )
        
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
            
            for ( one, two ) in itertools.product( hex_chars, hex_chars ):
                
                new_dir = dir + os.path.sep + one + two
                
                if not os.path.exists( new_dir ): os.mkdir( new_dir )
                
            
            ( db, c ) = self._GetDBCursor()
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            c.execute( 'PRAGMA auto_vacuum = 0;' ) # none
            c.execute( 'PRAGMA journal_mode=WAL;' )
            
            now = HC.GetNow()
            
            c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, type INTEGER, options TEXT_YAML );' )
            
            c.execute( 'CREATE TABLE accounts ( account_id INTEGER PRIMARY KEY, access_key BLOB_BYTES );' )
            c.execute( 'CREATE UNIQUE INDEX accounts_access_key_index ON accounts ( access_key );' )
            
            c.execute( 'CREATE TABLE account_map ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, account_type_id INTEGER, created INTEGER, expires INTEGER, used_bytes INTEGER, used_requests INTEGER, PRIMARY KEY( service_id, account_id ) );' )
            c.execute( 'CREATE INDEX account_map_service_id_account_type_id_index ON account_map ( service_id, account_type_id );' )
            
            c.execute( 'CREATE TABLE account_scores ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, score_type INTEGER, score INTEGER, PRIMARY KEY( service_id, account_id, score_type ) );' )
            
            c.execute( 'CREATE TABLE account_type_map ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_type_id INTEGER, PRIMARY KEY ( service_id, account_type_id ) );' )
            
            c.execute( 'CREATE TABLE account_types ( account_type_id INTEGER PRIMARY KEY, title TEXT, account_type TEXT_YAML );' )
            
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
            
            c.execute( 'CREATE TABLE registration_keys ( registration_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_type_id INTEGER, access_key BLOB_BYTES, expiry INTEGER );' )
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
            
            service_identifier = HC.SERVER_ADMIN_IDENTIFIER
            
            service_key = service_identifier.GetServiceKey()
            
            service_type = service_identifier.GetType()
            
            options = HC.DEFAULT_OPTIONS[ HC.SERVER_ADMIN ]
            
            options[ 'port' ] = HC.DEFAULT_SERVER_ADMIN_PORT
            
            c.execute( 'INSERT INTO services ( service_key, type, options ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, options ) )
            
            server_admin_service_id = c.lastrowid
            
            server_admin_account_type = HC.AccountType( 'server admin', [ HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ], ( None, None ) )
            
            c.execute( 'INSERT INTO account_types ( title, account_type ) VALUES ( ?, ? );', ( 'server admin', server_admin_account_type ) )
            
            server_admin_account_type_id = c.lastrowid
            
            c.execute( 'INSERT INTO account_type_map ( service_id, account_type_id ) VALUES ( ?, ? );', ( server_admin_service_id, server_admin_account_type_id ) )
            
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
        
        self._UpdateDBOld( c, version )
        
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
                
            
        
        c.execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
    
    def _UpdateDBOld( self, c, version ):
        
        if version == 28:
            
            files_db_path = HC.DB_DIR + os.path.sep + 'server_files.db'
            
            c.execute( 'COMMIT' )
            
            # can't do it inside a transaction
            c.execute( 'ATTACH database "' + files_db_path + '" as files_db;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            os.mkdir( HC.SERVER_FILES_DIR )
            
            all_local_files = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files;' ) ]
            
            for i in range( 0, len( all_local_files ), 100 ):
                
                local_files_subset = all_local_files[ i : i + 100 ]
                
                for hash_id in local_files_subset:
                    
                    hash = self._GetHash( c, hash_id )
                    
                    ( file, ) = c.execute( 'SELECT file FROM files WHERE hash_id = ?', ( hash_id, ) ).fetchone()
                    
                    path_to = HC.SERVER_FILES_DIR + os.path.sep + hash.encode( 'hex' )
                    
                    with open( path_to, 'wb' ) as f: f.write( file )
                    
                
                c.execute( 'DELETE FROM files WHERE hash_id IN ' + HC.SplayListForDB( local_files_subset ) + ';' )
                
                c.execute( 'COMMIT' )
                
                # slow truncate happens here!
                
                c.execute( 'BEGIN IMMEDIATE' )
                
            
            c.execute( 'COMMIT' )
            
            # can't do it inside a transaction
            c.execute( 'DETACH DATABASE files_db;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            os.remove( files_db_path )
            
        
        if version == 29:
            
            thumbnails_db_path = HC.DB_DIR + os.path.sep + 'server_thumbnails.db'
            
            c.execute( 'COMMIT' )
            
            # can't do it inside a transaction
            c.execute( 'ATTACH database "' + thumbnails_db_path + '" as thumbnails_db;' )
            
            os.mkdir( HC.SERVER_THUMBNAILS_DIR )
            
            all_thumbnails = c.execute( 'SELECT DISTINCT hash_id, hash FROM thumbnails, hashes USING ( hash_id );' ).fetchall()
            
            for i in range( 0, len( all_thumbnails ), 500 ):
                
                thumbnails_subset = all_thumbnails[ i : i + 500 ]
                
                for ( hash_id, hash ) in thumbnails_subset:
                    
                    ( thumbnail, ) = c.execute( 'SELECT thumbnail FROM thumbnails WHERE hash_id = ?', ( hash_id, ) ).fetchone()
                    
                    path_to = HC.SERVER_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' )
                    
                    with open( path_to, 'wb' ) as f: f.write( thumbnail )
                    
                
            
            # can't do it inside a transaction
            c.execute( 'DETACH DATABASE thumbnails_db;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            os.remove( thumbnails_db_path )
            
        
        if version == 34:
            
            main_db_path = HC.DB_DIR + os.path.sep + 'server_main.db'
            files_info_db_path = HC.DB_DIR + os.path.sep + 'server_files_info.db'
            mappings_db_path = HC.DB_DIR + os.path.sep + 'server_mappings.db'
            updates_db_path = HC.DB_DIR + os.path.sep + 'server_updates.db'
            
            if os.path.exists( main_db_path ):
                
                c.execute( 'COMMIT' )
                
                c.execute( 'ATTACH database "' + main_db_path + '" as main_db;' )
                c.execute( 'ATTACH database "' + files_info_db_path + '" as files_info_db;' )
                c.execute( 'ATTACH database "' + mappings_db_path + '" as mappings_db;' )
                c.execute( 'ATTACH database "' + updates_db_path + '" as updates_db;' )
                
                c.execute( 'BEGIN IMMEDIATE' )
                
                c.execute( 'REPLACE INTO main.services SELECT * FROM main_db.services;' )
                
                all_service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM main.services;' ) ]
                
                c.execute( 'DELETE FROM main_db.account_map WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM main_db.account_scores WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM main_db.account_type_map WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM main_db.bans WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM main_db.news WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                
                c.execute( 'DELETE FROM mappings_db.deleted_mappings WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM mappings_db.mappings WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM mappings_db.mapping_petitions WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                
                c.execute( 'DELETE FROM files_info_db.deleted_files WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM files_info_db.file_map WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM files_info_db.ip_addresses WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                c.execute( 'DELETE FROM files_info_db.file_petitions WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                
                c.execute( 'DELETE FROM updates_db.update_cache WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                
                c.execute( 'REPLACE INTO main.accounts SELECT * FROM main_db.accounts;' )
                c.execute( 'REPLACE INTO main.account_map SELECT * FROM main_db.account_map;' )
                c.execute( 'REPLACE INTO main.account_scores SELECT * FROM main_db.account_scores;' )
                c.execute( 'REPLACE INTO main.account_type_map SELECT * FROM main_db.account_type_map;' )
                c.execute( 'REPLACE INTO main.account_types SELECT * FROM main_db.account_types;' )
                c.execute( 'REPLACE INTO main.bans SELECT * FROM main_db.bans;' )
                c.execute( 'REPLACE INTO main.hashes SELECT * FROM main_db.hashes;' )
                c.execute( 'REPLACE INTO main.news SELECT * FROM main_db.news;' )
                c.execute( 'REPLACE INTO main.reasons SELECT * FROM main_db.reasons;' )
                c.execute( 'REPLACE INTO main.tags SELECT * FROM main_db.tags;' )
                # don't do version, lol
                
                c.execute( 'REPLACE INTO main.deleted_mappings SELECT * FROM mappings_db.deleted_mappings;' )
                c.execute( 'REPLACE INTO main.mappings SELECT * FROM mappings_db.mappings;' )
                c.execute( 'REPLACE INTO main.mapping_petitions SELECT * FROM mappings_db.mapping_petitions;' )
                
                c.execute( 'REPLACE INTO main.deleted_files SELECT * FROM files_info_db.deleted_files;' )
                c.execute( 'REPLACE INTO main.files_info SELECT * FROM files_info_db.files_info;' )
                c.execute( 'REPLACE INTO main.file_map SELECT * FROM files_info_db.file_map;' )
                c.execute( 'REPLACE INTO main.file_petitions SELECT * FROM files_info_db.file_petitions;' )
                c.execute( 'REPLACE INTO main.ip_addresses SELECT * FROM files_info_db.ip_addresses;' )
                
                c.execute( 'REPLACE INTO main.update_cache SELECT * FROM updates_db.update_cache;' )
                
                c.execute( 'COMMIT' )
                
                c.execute( 'DETACH database main_db;' )
                c.execute( 'DETACH database files_info_db;' )
                c.execute( 'DETACH database mappings_db;' )
                c.execute( 'DETACH database updates_db;' )
                
                os.remove( main_db_path )
                os.remove( mappings_db_path )
                os.remove( files_info_db_path )
                os.remove( updates_db_path )
                
                c.execute( 'BEGIN IMMEDIATE' )
                
            
        
        if version == 36:
            
            os.mkdir( HC.SERVER_MESSAGES_DIR )
            
            c.execute( 'CREATE TABLE contacts ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, contact_key BLOB, public_key TEXT, PRIMARY KEY( service_id, account_id ) );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_contact_key_index ON contacts ( contact_key );' )
            
            c.execute( 'CREATE TABLE messages ( message_key BLOB PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, timestamp INTEGER );' )
            c.execute( 'CREATE INDEX messages_service_id_account_id_index ON messages ( service_id, account_id );' )
            c.execute( 'CREATE INDEX messages_timestamp_index ON messages ( timestamp );' )
            
        
        if version == 37:
            
            c.execute( 'COMMIT' )
            c.execute( 'PRAGMA journal_mode=WAL;' ) # possibly didn't work last time, cause of sqlite dll issue
            c.execute( 'BEGIN IMMEDIATE' )
            
            c.execute( 'DROP TABLE messages;' ) # blob instead of blob_bytes!
            
            c.execute( 'CREATE TABLE messages ( message_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, timestamp INTEGER );' )
            c.execute( 'CREATE INDEX messages_service_id_account_id_index ON messages ( service_id, account_id );' )
            c.execute( 'CREATE INDEX messages_timestamp_index ON messages ( timestamp );' )
            
            c.execute( 'CREATE TABLE message_statuses ( status_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, status BLOB_BYTES, timestamp INTEGER );' )
            c.execute( 'CREATE INDEX message_statuses_service_id_account_id_index ON message_statuses ( service_id, account_id );' )
            c.execute( 'CREATE INDEX message_statuses_timestamp_index ON message_statuses ( timestamp );' )
            
        
        if version == 39:
            
            try: c.execute( 'SELECT 1 FROM message_statuses;' ).fetchone() # didn't update dbinit on 38
            except:
                
                c.execute( 'DROP TABLE messages;' ) # blob instead of blob_bytes!
                
                c.execute( 'CREATE TABLE messages ( message_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, timestamp INTEGER );' )
                c.execute( 'CREATE INDEX messages_service_id_account_id_index ON messages ( service_id, account_id );' )
                c.execute( 'CREATE INDEX messages_timestamp_index ON messages ( timestamp );' )
                
                c.execute( 'CREATE TABLE message_statuses ( status_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, status BLOB_BYTES, timestamp INTEGER );' )
                c.execute( 'CREATE INDEX message_statuses_service_id_account_id_index ON message_statuses ( service_id, account_id );' )
                c.execute( 'CREATE INDEX message_statuses_timestamp_index ON message_statuses ( timestamp );' )
                
            
        
        if version == 40:
            
            c.execute( 'CREATE TABLE ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, hash_id INTEGER, rating REAL, PRIMARY KEY( service_id, account_id, hash_id ) );' )
            c.execute( 'CREATE INDEX ratings_hash_id ON ratings ( hash_id );' )
            
            c.execute( 'CREATE TABLE ratings_aggregates ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, score INTEGER, count INTEGER, new_timestamp INTEGER, current_timestamp INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX ratings_aggregates_new_timestamp ON ratings_aggregates ( new_timestamp );' )
            c.execute( 'CREATE INDEX ratings_aggregates_current_timestamp ON ratings_aggregates ( current_timestamp );' )
            
        
        if version == 50:
            
            if not os.path.exists( HC.SERVER_UPDATES_DIR ): os.mkdir( HC.SERVER_UPDATES_DIR )
            
            all_update_data = c.execute( 'SELECT * FROM update_cache;' ).fetchall()
            
            c.execute( 'DROP TABLE update_cache;' )
            
            c.execute( 'CREATE TABLE update_cache ( service_id INTEGER REFERENCES services ON DELETE CASCADE, begin INTEGER, end INTEGER, update_key TEXT, dirty INTEGER_BOOLEAN, PRIMARY KEY( service_id, begin ) );' )
            c.execute( 'CREATE UNIQUE INDEX update_cache_service_id_end_index ON update_cache ( service_id, end );' )
            c.execute( 'CREATE INDEX update_cache_service_id_dirty_index ON update_cache ( service_id, dirty );' )
            
            for ( service_id, begin, end, update, dirty ) in all_update_data:
                
                update_key_bytes = os.urandom( 32 )
                
                update_key = update_key_bytes.encode( 'hex' )
                
                with open( HC.SERVER_UPDATES_DIR + os.path.sep + update_key, 'wb' ) as f: f.write( update )
                
                c.execute( 'INSERT INTO update_cache ( service_id, begin, end, update_key, dirty ) VALUES ( ?, ?, ?, ?, ? );', ( service_id, begin, end, update_key, dirty ) )
                
            
        
        if version == 55:
            
            c.execute( 'DROP INDEX mappings_service_id_account_id_index;' )
            c.execute( 'DROP INDEX mappings_service_id_timestamp_index;' )
            
            c.execute( 'CREATE INDEX mappings_account_id_index ON mappings ( account_id );' )
            c.execute( 'CREATE INDEX mappings_timestamp_index ON mappings ( timestamp );' )
            
        
        if version == 60:
            
            c.execute( 'CREATE TABLE sessions ( session_key BLOB_BYTES, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, expiry INTEGER );' )
            
            c.execute( 'CREATE TABLE registration_keys ( registration_key BLOB_BYTES PRIMARY KEY, service_id INTEGER REFERENCES services ON DELETE CASCADE, account_type_id INTEGER, access_key BLOB_BYTES, expiry INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX registration_keys_access_key_index ON registration_keys ( access_key );' )
            
        
        if version == 67:
            
            dirs = ( HC.SERVER_FILES_DIR, HC.SERVER_THUMBNAILS_DIR, HC.SERVER_UPDATES_DIR, HC.SERVER_MESSAGES_DIR )
            
            hex_chars = '0123456789abcdef'
            
            for dir in dirs:
                
                for ( one, two ) in itertools.product( hex_chars, hex_chars ):
                    
                    new_dir = dir + os.path.sep + one + two
                    
                    if not os.path.exists( new_dir ): os.mkdir( new_dir )
                    
                
                filenames = dircache.listdir( dir )
                
                for filename in filenames:
                    
                    try:
                        
                        source_path = dir + os.path.sep + filename
                        
                        first_two_chars = filename[:2]
                        
                        destination_path = dir + os.path.sep + first_two_chars + os.path.sep + filename
                        
                        shutil.move( source_path, destination_path )
                        
                    except: continue
                    
                
            
        
        if version == 70:
            
            try: c.execute( 'CREATE INDEX mappings_account_id_index ON mappings ( account_id );' )
            except: pass
            
            try: c.execute( 'CREATE INDEX mappings_timestamp_index ON mappings ( timestamp );' )
            except: pass
            
        
        if version == 71:
            
            c.execute( 'ANALYZE' )
            
            #
            
            now = HC.GetNow()
            
            #
            
            petitioned_inserts = [ ( service_id, account_id, hash_id, reason_id, now, HC.PETITIONED ) for ( service_id, account_id, hash_id, reason_id ) in c.execute( 'SELECT service_id, account_id, hash_id, reason_id FROM file_petitions;' ) ]
            deleted_inserts = [ ( service_id, account_id, hash_id, reason_id, timestamp, HC.DELETED ) for ( service_id, account_id, hash_id, reason_id, timestamp ) in c.execute( 'SELECT service_id, admin_account_id, hash_id, reason_id, timestamp FROM deleted_files;' ) ]
            
            c.execute( 'DROP TABLE file_petitions;' )
            c.execute( 'DROP TABLE deleted_files;' )
            
            c.execute( 'CREATE TABLE file_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY( service_id, account_id, hash_id, status ) );' )
            c.execute( 'CREATE INDEX file_petitions_service_id_account_id_reason_id_index ON file_petitions ( service_id, account_id, reason_id );' )
            c.execute( 'CREATE INDEX file_petitions_service_id_hash_id_index ON file_petitions ( service_id, hash_id );' )
            c.execute( 'CREATE INDEX file_petitions_service_id_status_index ON file_petitions ( service_id, status );' )
            c.execute( 'CREATE INDEX file_petitions_service_id_timestamp_index ON file_petitions ( service_id, timestamp );' )
            
            c.executemany( 'INSERT INTO file_petitions VALUES ( ?, ?, ?, ?, ?, ? );', petitioned_inserts )
            c.executemany( 'INSERT INTO file_petitions VALUES ( ?, ?, ?, ?, ?, ? );', deleted_inserts )
            
            #
            
            petitioned_inserts = [ ( service_id, account_id, tag_id, hash_id, reason_id, now, HC.PETITIONED ) for ( service_id, account_id, tag_id, hash_id, reason_id ) in c.execute( 'SELECT service_id, account_id, tag_id, hash_id, reason_id FROM mapping_petitions;' ) ]
            deleted_inserts = [ ( service_id, account_id, tag_id, hash_id, reason_id, timestamp, HC.DELETED ) for ( service_id, account_id, tag_id, hash_id, reason_id, timestamp ) in c.execute( 'SELECT service_id, admin_account_id, tag_id, hash_id, reason_id, timestamp FROM deleted_mappings;' ) ]
            
            c.execute( 'DROP TABLE mapping_petitions;' )
            c.execute( 'DROP TABLE deleted_mappings;' )
            
            c.execute( 'CREATE TABLE mapping_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, timestamp INTEGER, status INTEGER, PRIMARY KEY( service_id, account_id, tag_id, hash_id, status ) );' )
            c.execute( 'CREATE INDEX mapping_petitions_service_id_account_id_reason_id_tag_id_index ON mapping_petitions ( service_id, account_id, reason_id, tag_id );' )
            c.execute( 'CREATE INDEX mapping_petitions_service_id_tag_id_hash_id_index ON mapping_petitions ( service_id, tag_id, hash_id );' )
            c.execute( 'CREATE INDEX mapping_petitions_service_id_status_index ON mapping_petitions ( service_id, status );' )
            c.execute( 'CREATE INDEX mapping_petitions_service_id_timestamp_index ON mapping_petitions ( service_id, timestamp );' )
            
            c.executemany( 'INSERT INTO mapping_petitions VALUES ( ?, ?, ?, ?, ?, ?, ? );', petitioned_inserts )
            c.executemany( 'INSERT INTO mapping_petitions VALUES ( ?, ?, ?, ?, ?, ?, ? );', deleted_inserts )
            
            #
            
            try:
                
                c.execute( 'DROP TABLE tag_siblings;' )
                c.execute( 'DROP TABLE deleted_tag_siblings;' )
                c.execute( 'DROP TABLE pending_tag_siblings;' )
                c.execute( 'DROP TABLE tag_sibling_petitions;' )
                
            except: pass
            
            c.execute( 'CREATE TABLE tag_siblings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, old_tag_id INTEGER, new_tag_id INTEGER, timestamp INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, account_id, old_tag_id, status ) );' )
            c.execute( 'CREATE INDEX tag_siblings_service_id_old_tag_id_index ON tag_siblings ( service_id, old_tag_id );' )
            c.execute( 'CREATE INDEX tag_siblings_service_id_timestamp_index ON tag_siblings ( service_id, timestamp );' )
            c.execute( 'CREATE INDEX tag_siblings_service_id_status_index ON tag_siblings ( service_id, status );' )
            
            #
            
            c.execute( 'CREATE TABLE tag_parents ( service_id INTEGER REFERENCES services ON DELETE CASCADE, account_id INTEGER, old_tag_id INTEGER, new_tag_id INTEGER, timestamp INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, account_id, old_tag_id, new_tag_id, status ) );' )
            c.execute( 'CREATE INDEX tag_parents_service_id_old_tag_id_index ON tag_parents ( service_id, old_tag_id, new_tag_id );' )
            c.execute( 'CREATE INDEX tag_parents_service_id_timestamp_index ON tag_parents ( service_id, timestamp );' )
            c.execute( 'CREATE INDEX tag_parents_service_id_status_index ON tag_parents ( service_id, status );' )
            
            # update objects have changed
            
            results = c.execute( 'SELECT service_id, begin, end FROM update_cache WHERE begin = 0;' ).fetchall()
            
            c.execute( 'DELETE FROM update_cache;' )
            
            update_paths = [ path for path in SC.IterateAllPaths( 'update' ) ]
            
            for path in update_paths: os.remove( path )
            
            for ( service_id, begin, end ) in results: self._CreateUpdate( c, service_id, begin, end )
            
        
        if version == 86:
            
            c.execute( 'COMMIT' )
            
            c.execute( 'PRAGMA foreign_keys = OFF;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            old_service_info = c.execute( 'SELECT * FROM services;' ).fetchall()
            
            c.execute( 'DROP TABLE services;' )
            
            c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, type INTEGER, options TEXT_YAML );' ).fetchall()
            
            for ( service_id, service_type, port, options ) in old_service_info:
                
                if service_type == HC.SERVER_ADMIN: service_key = 'server admin'
                else: service_key = os.urandom( 32 )
                
                options[ 'port' ] = port
                
                c.execute( 'INSERT INTO services ( service_id, service_key, type, options ) VALUES ( ?, ?, ?, ? );', ( service_id, sqlite3.Binary( service_key ), service_type, options ) )
                
            
            c.execute( 'COMMIT' )
            
            c.execute( 'PRAGMA foreign_keys = ON;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
        
        if version == 90:
            
            for ( service_id, options ) in c.execute( 'SELECT service_id, options FROM services;' ).fetchall():
                
                options[ 'upnp' ] = None
                
                c.execute( 'UPDATE services SET options = ? WHERE service_id = ?;', ( options, service_id ) )
                
            
        
    
    def pub_after_commit( self, topic, *args, **kwargs ): self._pubsubs.append( ( topic, args, kwargs ) )
    
    def MainLoop( self ):
        
        def ProcessJob( c, job ):
            
            def ProcessRead( action, args, kwargs ):
                
                if action == 'access_key': result = self._GetAccessKey( c, *args, **kwargs )
                elif action == 'account': result = self._GetAccount( c, *args, **kwargs )
                elif action == 'account_info': result = self._GetAccountInfo( c, *args, **kwargs )
                elif action == 'account_types': result = self._GetAccountTypes( c, *args, **kwargs )
                elif action == 'dirty_updates': result = self._GetDirtyUpdates( c, *args, **kwargs  )
                elif action == 'init': result = self._InitAdmin( c, *args, **kwargs  )
                elif action == 'ip': result = self._GetIPTimestamp( c, *args, **kwargs )
                elif action == 'messaging_sessions': result = self._GetMessagingSessions( c, *args, **kwargs )
                elif action == 'num_petitions': result = self._GetNumPetitions( c, *args, **kwargs )
                elif action == 'petition': result = self._GetPetition( c, *args, **kwargs )
                elif action == 'registration_keys': result = self._GenerateRegistrationKeys( c, *args, **kwargs )
                elif action == 'service_identifiers': result = self._GetServiceIdentifiers( c, *args, **kwargs )
                elif action == 'services': result = self._GetServicesInfo( c, *args, **kwargs )
                elif action == 'sessions': result = self._GetSessions( c, *args, **kwargs )
                elif action == 'stats': result = self._GetStats( c, *args, **kwargs )
                elif action == 'update_ends': result = self._GetUpdateEnds( c, *args, **kwargs )
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
                elif action == 'options': result = self._SetOptions( c, *args, **kwargs )
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
        
        while not HC.shutdown or not self._jobs.empty():
            
            try:
                
                ( priority, job ) = self._jobs.get( timeout = 1 )
                
                self._pubsubs = []
                
                try:
                    
                    ProcessJob( c, job )
                    
                except:
                    
                    self._jobs.put( ( priority, job ) ) # couldn't lock db; put job back on queue
                    
                    time.sleep( 5 )
                    
                
            except: pass # no jobs this second; let's see if we should shutdown
            
        
    
    def Read( self, action, priority, *args, **kwargs ):
        
        job_type = 'read'
        
        synchronous = True
        
        job = HC.JobDatabase( action, job_type, synchronous, *args, **kwargs )
        
        self._jobs.put( ( priority + 1, job ) ) # +1 so all writes of equal priority can clear out first
        
        return job.GetResult()
        
    
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

def DAEMONFlushRequestsMade( all_services_requests ): HC.app.WriteDaemon( 'flush_requests_made', all_services_requests )

def DAEMONGenerateUpdates():
    
    dirty_updates = HC.app.ReadDaemon( 'dirty_updates' )
    
    for ( service_identifier, tuples ) in dirty_updates.items():
        
        for ( begin, end ) in tuples: HC.app.WriteDaemon( 'clean_update', service_identifier, begin, end )
        
    
    update_ends = HC.app.ReadDaemon( 'update_ends' )
    
    for ( service_identifier, biggest_end ) in update_ends.items():
        
        now = HC.GetNow()
        
        next_begin = biggest_end + 1
        next_end = biggest_end + HC.UPDATE_DURATION
        
        while next_end < now:
            
            HC.app.WriteDaemon( 'create_update', service_identifier, next_begin, next_end )
            
            biggest_end = next_end
            
            now = HC.GetNow()
            
            next_begin = biggest_end + 1
            next_end = biggest_end + HC.UPDATE_DURATION
            
        
    
def DAEMONUPnP():
    
    local_ip = HydrusNATPunch.GetLocalIP()
    
    current_mappings = HydrusNATPunch.GetUPnPMappings()
    
    our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) in current_mappings }
    
    service_identifiers = HC.app.ReadDaemon( 'service_identifiers' )
    
    all_options = { service_identifier : HC.app.ReadDaemon( 'options', service_identifier ) for service_identifier in service_identifiers }
    
    for ( service_identifier, options ) in all_options.items():
        
        internal_port = options[ 'port' ]
        upnp = options[ 'upnp' ]
        
        if ( local_ip, internal_port ) in our_mappings:
            
            current_external_port = our_mappings[ ( local_ip, internal_port ) ]
            
            if current_external_port != upnp: HydrusNATPunch.RemoveUPnPMapping( current_external_port, 'TCP' )
            
        
    
    for ( service_identifier, options ) in all_options.items():
        
        internal_port = options[ 'port' ]
        upnp = options[ 'upnp' ]
        
        if ( local_ip, internal_port ) not in our_mappings:
            
            external_port = our_mappings[ ( local_ip, internal_port ) ]
            
            protocol = 'TCP'
            
            description = HC.service_string_lookup[ service_identifier.GetType() ] + ' at ' + local_ip + ':' + str( internal_port )
            
            duration = 3600
            
            HydrusNATPunch.AddUPnPMapping( local_ip, internal_port, external_port, protocol, description, duration = duration )
            
        
    