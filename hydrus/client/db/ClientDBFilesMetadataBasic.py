import collections.abc
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

from hydrus.client.db import ClientDBModule

class ClientDBFilesMetadataBasic( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        super().__init__( 'client files simple metadata', cursor )
        
    
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
        
        index_generation_dict[ 'main.files_info_forced_filetypes' ] = [
            ( [ 'forced_mime' ], False, 556 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.files_info' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, has_audio INTEGER_BOOLEAN, num_words INTEGER );', 400 ),
            'main.files_info_forced_filetypes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, forced_mime INTEGER );', 556 ),
            'main.has_icc_profile' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 465 ),
            'main.has_exif' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 505 ),
            'main.has_human_readable_embedded_metadata' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 505 ),
            'main.has_transparency' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 552 ),
            'external_master.blurhashes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, blurhash TEXT );', 545 )
        }
        
    
    def AddFilesInfo( self, rows, overwrite = False ):
        
        if overwrite:
            
            insert_phrase = 'REPLACE INTO'
            
        else:
            
            insert_phrase = 'INSERT OR IGNORE INTO'
            
        
        # hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words
        self._ExecuteMany( insert_phrase + ' files_info ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? );', rows )
        
    
    def GetBlurhash( self, hash_id: int ) -> str:
        
        result = self._Execute( 'SELECT blurhash FROM blurhashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Did not have blurhash information for that file!' )
            
        
        ( blurhash, ) = result
        
        return blurhash
        
    
    def GetHasEXIF( self, hash_id: int ):
        
        result = self._Execute( 'SELECT hash_id FROM has_exif WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetHasEXIFHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        has_exif_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN has_exif USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
        return has_exif_hash_ids
        
    
    def GetHasHumanReadableEmbeddedMetadata( self, hash_id: int ):
        
        result = self._Execute( 'SELECT hash_id FROM has_human_readable_embedded_metadata WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetHasHumanReadableEmbeddedMetadataHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        has_human_readable_embedded_metadata_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN has_human_readable_embedded_metadata USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
        return has_human_readable_embedded_metadata_hash_ids
        
    
    def GetHashIdsToBlurhashes( self, hash_ids_table_name: str ):
        
        return dict( self._Execute( 'SELECT hash_id, blurhash FROM {} CROSS JOIN blurhashes USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
    
    def GetHashIdsToForcedFiletypes( self, hash_ids_table_name: str ):
        
        return dict( self._Execute( 'SELECT hash_id, forced_mime FROM {} CROSS JOIN files_info_forced_filetypes USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
    
    def GetHasICCProfile( self, hash_id: int ):
        
        result = self._Execute( 'SELECT hash_id FROM has_icc_profile WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetHasICCProfileHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        has_icc_profile_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN has_icc_profile USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
        return has_icc_profile_hash_ids
        
    
    def GetHasTransparency( self, hash_id: int ):
        
        result = self._Execute( 'SELECT hash_id FROM has_transparency WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def GetHasTransparencyHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        has_transparency_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN has_transparency USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
        return has_transparency_hash_ids
        
    
    def GetMime( self, hash_id: int ) -> int:
        
        result = self._Execute( 'SELECT mime FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Did not have mime information for that file!' )
            
        
        ( mime, ) = result
        
        return mime
        
    
    def GetNumViewable( self, hash_ids: collections.abc.Collection[ int ] ) -> int:
        
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
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            return [
                ( 'files_info', 'hash_id' ),
                ( 'files_info_forced_filetypes', 'hash_id' ),
                ( 'has_exif', 'hash_id' ),
                ( 'has_human_readable_embedded_metadata', 'hash_id' ),
                ( 'has_icc_profile', 'hash_id' ),
                ( 'has_transparency', 'hash_id' ),
                ( 'blurhashes', 'hash_id' )
            ]
            
        
        return []
        
    
    def GetTotalSize( self, hash_ids: collections.abc.Collection[ int ] ) -> int:
        
        if len( hash_ids ) == 1:
            
            ( hash_id, ) = hash_ids
            
            result = self._Execute( 'SELECT size FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
        else:
            
            with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                
                result = self._Execute( 'SELECT SUM( size ) FROM {} CROSS JOIN files_info USING ( hash_id );'.format( temp_hash_ids_table_name ) ).fetchone()
                
            
        
        total_size = self._GetSumResult( result )
        
        return total_size
        
    
    def SetForcedFiletype( self, hash_id: int, forced_mime: int | None ):
        
        self._Execute( 'DELETE FROM files_info_forced_filetypes WHERE hash_id = ?;', ( hash_id, ) )
        
        if forced_mime is not None:
            
            result = self._Execute( 'SELECT mime FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
            if result is not None:
                
                ( original_mime, ) = result
                
                if original_mime == forced_mime:
                    
                    return
                    
                
            
            self._Execute( 'INSERT INTO files_info_forced_filetypes ( hash_id, forced_mime ) VALUES ( ?, ? );', ( hash_id, forced_mime ) )
            
        
    
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
            
        
    
    def SetHasTransparency( self, hash_id: int, has_transparency: bool ):
        
        if has_transparency:
            
            self._Execute( 'INSERT OR IGNORE INTO has_transparency ( hash_id ) VALUES ( ? );', ( hash_id, ) )
            
        else:
            
            self._Execute( 'DELETE FROM has_transparency WHERE hash_id = ?;', ( hash_id, ) )
            
        
    
    def SetBlurhash( self, hash_id: int, blurhash: str ):
        
        self._Execute('INSERT OR REPLACE INTO blurhashes ( hash_id, blurhash ) VALUES ( ?, ?);', ( hash_id, blurhash ) )
        
    
