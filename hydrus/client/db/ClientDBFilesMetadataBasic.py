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
        
    
    def _GetHasFlag( self, table_name: str, hash_id: int ):
        
        result = self._Execute( f'SELECT hash_id FROM {table_name} WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        return result is not None
        
    
    def _GetFlagHashIds( self, table_name: str, hash_ids_table_name: str ):
        
        hash_ids = self._STS( self._Execute( f'SELECT hash_id FROM {hash_ids_table_name} CROSS JOIN {table_name} USING ( hash_id );' ) )
        
        return hash_ids
        
    
    def _SetHasFlag( self, table_name: str, hash_id: int, has_flag: bool ):
        
        if has_flag:
            
            self._Execute( f'INSERT OR IGNORE INTO {table_name} ( hash_id ) VALUES ( ? );', ( hash_id, ) )
            
        else:
            
            self._Execute( f'DELETE FROM {table_name} WHERE hash_id = ?;', ( hash_id, ) )
            
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        # yo, do you want to collapse these boolean 'has_x' tables into one guy with a status_type column and a ( status_type | hash ) index?
        # in my experience this sort of thing is not as KISS as one dreams and the index column of '80,000 instances each of only five distinct values' tends to perform and store like garbage
        # spammy tables are spammy, but they are fast and KISS
        
        return {
            'main.files_info' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, has_audio INTEGER_BOOLEAN, num_words INTEGER );', 400 ),
            'main.files_info_forced_filetypes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, forced_mime INTEGER );', 556 ),
            'main.has_icc_profile' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 465 ),
            'main.has_exif' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 505 ),
            'main.has_xmp' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 682 ),
            'main.has_iptc' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 682 ),
            'main.has_human_readable_embedded_metadata' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 505 ),
            'main.has_software_source' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 682 ),
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
        
        return self._GetHasFlag( 'has_exif', hash_id )
        
    
    def GetHasEXIFHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        return self._GetFlagHashIds( 'has_exif', hash_ids_table_name )
        
    
    def GetHasHumanReadableEmbeddedMetadata( self, hash_id: int ):
        
        return self._GetHasFlag( 'has_human_readable_embedded_metadata', hash_id )
        
    
    def GetHasHumanReadableEmbeddedMetadataHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        return self._GetFlagHashIds( 'has_human_readable_embedded_metadata', hash_ids_table_name )
        
    
    def GetHashIdsToBlurhashes( self, hash_ids_table_name: str ):
        
        return dict( self._Execute( 'SELECT hash_id, blurhash FROM {} CROSS JOIN blurhashes USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
    
    def GetHashIdsToForcedFiletypes( self, hash_ids_table_name: str ):
        
        return dict( self._Execute( 'SELECT hash_id, forced_mime FROM {} CROSS JOIN files_info_forced_filetypes USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
    
    def GetHasICCProfile( self, hash_id: int ):
        
        return self._GetHasFlag( 'has_icc_profile', hash_id )
        
    
    def GetHasICCProfileHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        return self._GetFlagHashIds( 'has_icc_profile', hash_ids_table_name )
        
    
    def GetHasIPTC( self, hash_id: int ):
        
        return self._GetHasFlag( 'has_iptc', hash_id )
        
    
    def GetHasIPTCHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        return self._GetFlagHashIds( 'has_iptc', hash_ids_table_name )
        
    
    def GetHasSoftwareSource( self, hash_id: int ):
        
        return self._GetHasFlag( 'has_software_source', hash_id )
        
    
    def GetHasSoftwareSourceHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        return self._GetFlagHashIds( 'has_software_source', hash_ids_table_name )
        
    
    def GetHasTransparency( self, hash_id: int ):
        
        return self._GetHasFlag( 'has_transparency', hash_id )
        
    
    def GetHasTransparencyHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        return self._GetFlagHashIds( 'has_transparency', hash_ids_table_name )
        
    
    def GetHasXMP( self, hash_id: int ):
        
        return self._GetHasFlag( 'has_xmp', hash_id )
        
    
    def GetHasXMPHashIds( self, hash_ids_table_name: str ) -> set[ int ]:
        
        return self._GetFlagHashIds( 'has_xmp', hash_ids_table_name )
        
    
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
                ( 'has_xmp', 'hash_id' ),
                ( 'has_iptc', 'hash_id' ),
                ( 'has_human_readable_embedded_metadata', 'hash_id' ),
                ( 'has_software_source', 'hash_id' ),
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
        
        self._SetHasFlag( 'has_exif', hash_id, has_exif )
        
    
    def SetHasHumanReadableEmbeddedMetadata( self, hash_id: int, has_human_readable_embedded_metadata: bool ):
        
        self._SetHasFlag( 'has_human_readable_embedded_metadata', hash_id, has_human_readable_embedded_metadata )
        
    
    def SetHasICCProfile( self, hash_id: int, has_icc_profile: bool ):
        
        self._SetHasFlag( 'has_icc_profile', hash_id, has_icc_profile )
        
    
    def SetHasIPTC( self, hash_id: int, has_iptc: bool ):
        
        self._SetHasFlag( 'has_iptc', hash_id, has_iptc )
        
    
    def SetHasSoftwareSource( self, hash_id: int, has_software_source: bool ):
        
        self._SetHasFlag( 'has_software_source', hash_id, has_software_source )
        
    
    def SetHasTransparency( self, hash_id: int, has_transparency: bool ):
        
        self._SetHasFlag( 'has_transparency', hash_id, has_transparency )
        
    
    def SetHasXMP( self, hash_id: int, has_xmp: bool ):
        
        self._SetHasFlag( 'has_xmp', hash_id, has_xmp )
        
    
    def SetBlurhash( self, hash_id: int, blurhash: str ):
        
        self._Execute('INSERT OR REPLACE INTO blurhashes ( hash_id, blurhash ) VALUES ( ?, ?);', ( hash_id, blurhash ) )
        
    
