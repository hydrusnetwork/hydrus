import os
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client.db import ClientDBServices
from hydrus.client.metadata import ClientTags

class ClientDBFilesMetadataBasic( HydrusDBModule.HydrusDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        HydrusDBModule.HydrusDBModule.__init__( self, 'client files metadata', cursor )
        
        self.inbox_hash_ids = set()
        
        self._InitCaches()
        
    
    def _GetInitialIndexGenerationTuples( self ):
        
        index_generation_tuples = []
        
        index_generation_tuples.append( ( 'files_info', [ 'size' ], False ) )
        index_generation_tuples.append( ( 'files_info', [ 'mime' ], False ) )
        index_generation_tuples.append( ( 'files_info', [ 'width' ], False ) )
        index_generation_tuples.append( ( 'files_info', [ 'height' ], False ) )
        index_generation_tuples.append( ( 'files_info', [ 'duration' ], False ) )
        index_generation_tuples.append( ( 'files_info', [ 'num_frames' ], False ) )
        
        return index_generation_tuples
        
    
    def _InitCaches( self ):
        
        if self._c.execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'file_inbox', ) ).fetchone() is not None:
            
            self.inbox_hash_ids = self._STS( self._c.execute( 'SELECT hash_id FROM file_inbox;' ) )
            
        
    
    def AddFilesInfo( self, rows, overwrite = False ):
        
        if overwrite:
            
            insert_phrase = 'REPLACE INTO'
            
        else:
            
            insert_phrase = 'INSERT OR IGNORE INTO'
            
        
        # hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words
        self._c.executemany( insert_phrase + ' files_info ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? );', rows )
        
    
    def ArchiveFiles( self, hash_ids: typing.Collection[ int ] ) -> typing.Set[ int ]:
        
        if not isinstance( hash_ids, set ):
            
            hash_ids = set( hash_ids )
            
        
        archiveable_hash_ids = hash_ids.intersection( self.inbox_hash_ids )
        
        if len( archiveable_hash_ids ) > 0:
            
            self._c.executemany( 'DELETE FROM file_inbox WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in archiveable_hash_ids ) )
            
            self.inbox_hash_ids.difference_update( archiveable_hash_ids )
            
        
        return archiveable_hash_ids
        
    
    def CreateInitialTables( self ):
        
        self._c.execute( 'CREATE TABLE file_inbox ( hash_id INTEGER PRIMARY KEY );' )
        self._c.execute( 'CREATE TABLE files_info ( hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, has_audio INTEGER_BOOLEAN, num_words INTEGER );' )
        
    
    def GetExpectedTableNames( self ) -> typing.Collection[ str ]:
        
        expected_table_names = [
            'file_inbox',
            'files_info'
        ]
        
        return expected_table_names
        
    
    def GetMime( self, hash_id: int ) -> int:
        
        result = self._c.execute( 'SELECT mime FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Did not have mime information for that file!' )
            
        
        ( mime, ) = result
        
        return mime
        
    
    def GetNumViewable( self, hash_ids: typing.Collection[ int ] ) -> int:
        
        if len( hash_ids ) == 1:
            
            ( hash_id, ) = hash_ids
            
            result = self._STL( self._c.execute( 'SELECT mime FROM files_info WHERE hash_id = ?;', ( hash_id, ) ) )
            
        else:
            
            with HydrusDB.TemporaryIntegerTable( self._c, hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                result = self._STL( self._c.execute( 'SELECT mime FROM {} CROSS JOIN files_info USING ( hash_id );'.format( temp_hash_ids_table_name ) ) )
                
            
        
        return sum( ( 1 for mime in result if mime in HC.SEARCHABLE_MIMES ) )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        if HC.CONTENT_TYPE_HASH:
            
            return [ ( 'files_info', 'hash_id' ) ]
            
        
        return []
        
    
    def GetTotalSize( self, hash_ids: typing.Collection[ int ] ) -> int:
        
        if len( hash_ids ) == 1:
            
            ( hash_id, ) = hash_ids
            
            result = self._c.execute( 'SELECT size FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
        else:
            
            with HydrusDB.TemporaryIntegerTable( self._c, hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                result = self._c.execute( 'SELECT SUM( size ) FROM {} CROSS JOIN files_info USING ( hash_id );'.format( temp_hash_ids_table_name ) ).fetchone()
                
            
        
        if result is None:
            
            return 0
            
        
        ( total_size, ) = result
        
        return total_size
        
    
    def InboxFiles( self, hash_ids: typing.Collection[ int ] ) -> typing.Set[ int ]:
        
        if not isinstance( hash_ids, set ):
            
            hash_ids = set( hash_ids )
            
        
        inboxable_hash_ids = hash_ids.difference( self.inbox_hash_ids )
        
        if len( inboxable_hash_ids ) > 0:
            
            self._c.executemany( 'INSERT OR IGNORE INTO file_inbox VALUES ( ? );', ( ( hash_id, ) for hash_id in inboxable_hash_ids ) )
            
            self.inbox_hash_ids.update( inboxable_hash_ids )
            
        
        return inboxable_hash_ids
        
    
