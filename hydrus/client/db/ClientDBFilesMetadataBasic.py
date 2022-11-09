import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client import ClientTime
from hydrus.client.db import ClientDBModule

class ClientDBFilesMetadataBasic( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files simple metadata', cursor )
        
    
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
        
        index_generation_dict[ 'main.file_domain_modified_timestamps' ] = [
            ( [ 'file_modified_timestamp' ], False, 476 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.files_info' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, has_audio INTEGER_BOOLEAN, num_words INTEGER );', 400 ),
            'main.has_icc_profile' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 465 ),
            'main.has_exif' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 505 ),
            'main.has_human_readable_embedded_metadata' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 505 ),
            'main.file_domain_modified_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, domain_id INTEGER, file_modified_timestamp INTEGER, PRIMARY KEY ( hash_id, domain_id ) );', 476 )
        }
        
    
    def AddFilesInfo( self, rows, overwrite = False ):
        
        if overwrite:
            
            insert_phrase = 'REPLACE INTO'
            
        else:
            
            insert_phrase = 'INSERT OR IGNORE INTO'
            
        
        # hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words
        self._ExecuteMany( insert_phrase + ' files_info ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? );', rows )
        
    
    def ClearDomainModifiedTimestamp( self, hash_id: int, domain_id: int ):
        
        self._Execute( 'DELETE FROM file_domain_modified_timestamps WHERE hash_id = ? AND domain_id = ?;', ( hash_id, domain_id ) )
        
    
    def GetDomainModifiedTimestamp( self, hash_id: int, domain_id: int ) -> typing.Optional[ int ]:
        
        result = self._Execute( 'SELECT file_modified_timestamp FROM file_domain_modified_timestamps WHERE hash_id = ? AND domain_id = ?;', ( hash_id, domain_id ) ).fetchone()
        
        if result is None:
            
            return None
            
        
        ( timestamp, ) = result
        
        return timestamp
        
    
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
                ( 'files_info', 'hash_id' ),
                ( 'has_exif', 'hash_id' ),
                ( 'has_human_readable_embedded_metadata', 'hash_id' ),
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
        
    
    def GetHasEXIF( self, hash_id: int ):
        
        result = self._Execute( 'SELECT hash_id FROM has_exif WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetHasEXIFHashIds( self, hash_ids_table_name: str ) -> typing.Set[ int ]:
        
        has_exif_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN has_exif USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
        return has_exif_hash_ids
        
    
    def GetHasHumanReadableEmbeddedMetadata( self, hash_id: int ):
        
        result = self._Execute( 'SELECT hash_id FROM has_human_readable_embedded_metadata WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetHasHumanReadableEmbeddedMetadataHashIds( self, hash_ids_table_name: str ) -> typing.Set[ int ]:
        
        has_human_readable_embedded_metadata_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN has_human_readable_embedded_metadata USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
        return has_human_readable_embedded_metadata_hash_ids
        
    
    def GetHasICCProfile( self, hash_id: int ):
        
        result = self._Execute( 'SELECT hash_id FROM has_icc_profile WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetHasICCProfileHashIds( self, hash_ids_table_name: str ) -> typing.Set[ int ]:
        
        has_icc_profile_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN has_icc_profile USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
        return has_icc_profile_hash_ids
        
    
    def SetDomainModifiedTimestamp( self, hash_id: int, domain_id: int, timestamp: int ):
        
        self._Execute( 'REPLACE INTO file_domain_modified_timestamps ( hash_id, domain_id, file_modified_timestamp ) VALUES ( ?, ?, ? );', ( hash_id, domain_id, timestamp ) )
        
    
    def SetHasEXIF( self, hash_id: int, has_exif: bool ):
        
        if has_exif:
            
            self._Execute( 'INSERT OR IGNORE INTO has_exif ( hash_id ) VALUES ( ? );', ( hash_id, ) )
            
        else:
            
            self._Execute( 'DELETE FROM has_exif WHERE hash_id = ?;', ( hash_id, ) )
            
        
    
    def SetHasHumanReadableEmbeddedMetadata( self, hash_id: int, has_human_readable_embedded_metadata: bool ):
        
        if has_human_readable_embedded_metadata:
            
            self._Execute( 'INSERT OR IGNORE INTO has_human_readable_embedded_metadata ( hash_id ) VALUES ( ? );', ( hash_id, ) )
            
        else:
            
            self._Execute( 'DELETE FROM has_human_readable_embedded_metadata WHERE hash_id = ?;', ( hash_id, ) )
            
        
    
    def SetHasICCProfile( self, hash_id: int, has_icc_profile: bool ):
        
        if has_icc_profile:
            
            self._Execute( 'INSERT OR IGNORE INTO has_icc_profile ( hash_id ) VALUES ( ? );', ( hash_id, ) )
            
        else:
            
            self._Execute( 'DELETE FROM has_icc_profile WHERE hash_id = ?;', ( hash_id, ) )
            
        
    
    def UpdateDomainModifiedTimestamp( self, hash_id: int, domain_id: int, timestamp: int ):
        
        should_update = True
        
        existing_timestamp = self.GetDomainModifiedTimestamp( hash_id, domain_id )
        
        if existing_timestamp is not None:
            
            should_update = ClientTime.ShouldUpdateDomainModifiedTime( existing_timestamp, timestamp )
            
        
        if should_update:
            
            self.SetDomainModifiedTimestamp( hash_id, domain_id, timestamp )
            
        
    
