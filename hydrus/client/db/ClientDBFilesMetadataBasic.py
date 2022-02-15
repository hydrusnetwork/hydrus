import os
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusDB
from hydrus.core import HydrusExceptions

from hydrus.client.db import ClientDBModule

class ClientDBFilesMetadataBasic( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files metadata', cursor )
        
        self.inbox_hash_ids = set()
        
        self._InitCaches()
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.files_info' ] = [
            ( [ 'size' ], False, 400 ),
            ( [ 'mime' ], False, 400 ),
            ( [ 'width' ], False, 400 ),
            ( [ 'height' ], False, 400 ),
            ( [ 'duration' ], False, 400 ),
            ( [ 'num_frames' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.file_inbox' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 400 ),
            'main.files_info' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, has_audio INTEGER_BOOLEAN, num_words INTEGER );', 400 ),
            'main.has_icc_profile' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 465 )
        }
        
    
    def _InitCaches( self ):
        
        if self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'file_inbox', ) ).fetchone() is not None:
            
            self.inbox_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM file_inbox;' ) )
            
        
    
    def AddFilesInfo( self, rows, overwrite = False ):
        
        if overwrite:
            
            insert_phrase = 'REPLACE INTO'
            
        else:
            
            insert_phrase = 'INSERT OR IGNORE INTO'
            
        
        # hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words
        self._ExecuteMany( insert_phrase + ' files_info ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? );', rows )
        
    
    def ArchiveFiles( self, hash_ids: typing.Collection[ int ] ) -> typing.Set[ int ]:
        
        if not isinstance( hash_ids, set ):
            
            hash_ids = set( hash_ids )
            
        
        archiveable_hash_ids = hash_ids.intersection( self.inbox_hash_ids )
        
        if len( archiveable_hash_ids ) > 0:
            
            self._ExecuteMany( 'DELETE FROM file_inbox WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in archiveable_hash_ids ) )
            
            self.inbox_hash_ids.difference_update( archiveable_hash_ids )
            
        
        return archiveable_hash_ids
        
    
    def GetMime( self, hash_id: int ) -> int:
        
        result = self._Execute( 'SELECT mime FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Did not have mime information for that file!' )
            
        
        ( mime, ) = result
        
        return mime
        
    
    def GetNumViewable( self, hash_ids: typing.Collection[ int ] ) -> int:
        
        if len( hash_ids ) == 1:
            
            ( hash_id, ) = hash_ids
            
            result = self._STL( self._Execute( 'SELECT mime FROM files_info WHERE hash_id = ?;', ( hash_id, ) ) )
            
        else:
            
            with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                result = self._STL( self._Execute( 'SELECT mime FROM {} CROSS JOIN files_info USING ( hash_id );'.format( temp_hash_ids_table_name ) ) )
                
            
        
        return sum( ( 1 for mime in result if mime in HC.SEARCHABLE_MIMES ) )
        
    
    def GetResolution( self, hash_id: int ):
        
        result = self._Execute( 'SELECT width, height FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            return ( None, None )
            
        
        return result
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            return [
                ( 'file_inbox', 'hash_id' ),
                ( 'files_info', 'hash_id' ),
                ( 'has_icc_profile', 'hash_id' )
            ]
            
        
        return []
        
    
    def GetTotalSize( self, hash_ids: typing.Collection[ int ] ) -> int:
        
        if len( hash_ids ) == 1:
            
            ( hash_id, ) = hash_ids
            
            result = self._Execute( 'SELECT size FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
        else:
            
            with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                result = self._Execute( 'SELECT SUM( size ) FROM {} CROSS JOIN files_info USING ( hash_id );'.format( temp_hash_ids_table_name ) ).fetchone()
                
            
        
        if result is None:
            
            return 0
            
        
        ( total_size, ) = result
        
        return total_size
        
    
    def GetHasICCProfile( self, hash_id: int ):
        
        result = self._Execute( 'SELECT hash_id FROM has_icc_profile WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetHasICCProfileHashIds( self, hash_ids: typing.Collection[ int ] ) -> typing.Set[ int ]:
        
        with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            has_icc_profile_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN has_icc_profile USING ( hash_id );'.format( temp_hash_ids_table_name ) ) )
            
        
        return has_icc_profile_hash_ids
        
    
    def InboxFiles( self, hash_ids: typing.Collection[ int ] ) -> typing.Set[ int ]:
        
        if not isinstance( hash_ids, set ):
            
            hash_ids = set( hash_ids )
            
        
        inboxable_hash_ids = hash_ids.difference( self.inbox_hash_ids )
        
        if len( inboxable_hash_ids ) > 0:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO file_inbox VALUES ( ? );', ( ( hash_id, ) for hash_id in inboxable_hash_ids ) )
            
            self.inbox_hash_ids.update( inboxable_hash_ids )
            
        
        return inboxable_hash_ids
        
    
    def SetHasICCProfile( self, hash_id: int, has_icc_profile: bool ):
        
        if has_icc_profile:
            
            self._Execute( 'INSERT OR IGNORE INTO has_icc_profile ( hash_id ) VALUES ( ? );', ( hash_id, ) )
            
        else:
            
            self._Execute( 'DELETE FROM has_icc_profile WHERE hash_id = ?;', ( hash_id, ) )
            
        
    
