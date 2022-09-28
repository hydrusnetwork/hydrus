import re
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

class ClientDBServicePaths( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_texts: ClientDBMaster.ClientDBMasterTexts, modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes ):
        
        self.modules_services = modules_services
        self.modules_texts = modules_texts
        self.modules_hashes_local_cache = modules_hashes_local_cache
        
        ClientDBModule.ClientDBModule.__init__( self, 'client service paths', cursor )
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.service_filenames' ] = [
            ( [ 'hash_id' ], False, 400 )
        ]
        
        index_generation_dict[ 'main.service_directories' ] = [
            ( [ 'directory_id' ], False, 400 )
        ]
        
        index_generation_dict[ 'main.service_directory_file_map' ] = [
            ( [ 'hash_id' ], False, 400 ),
            ( [ 'directory_id' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.service_filenames' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, hash_id INTEGER, filename TEXT, PRIMARY KEY ( service_id, hash_id ) );', 400 ),
            'main.service_directories' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, directory_id INTEGER, num_files INTEGER, total_size INTEGER, note TEXT, PRIMARY KEY ( service_id, directory_id ) );', 400 ),
            'main.service_directory_file_map' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, directory_id INTEGER, hash_id INTEGER, PRIMARY KEY ( service_id, directory_id, hash_id ) );', 400 )
        }
        
    
    def ClearService( self, service_id: int ):
        
        self._Execute( 'DELETE FROM service_filenames WHERE service_id = ?;', ( service_id, ) )
        self._Execute( 'DELETE FROM service_directories WHERE service_id = ?;', ( service_id, ) )
        self._Execute( 'DELETE FROM service_directory_file_map WHERE service_id = ?;', ( service_id, ) )
        
    
    def DeleteServiceDirectory( self, service_id: int, dirname: str ):
        
        directory_id = self.modules_texts.GetTextId( dirname )
        
        self._Execute( 'DELETE FROM service_directories WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) )
        self._Execute( 'DELETE FROM service_directory_file_map WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) )
        
    
    def GetHashIdsToServiceIdsAndFilenames( self, hash_ids_table_name: str ):
        
        query = 'SELECT hash_id, service_id, filename FROM {} CROSS JOIN service_filenames USING ( hash_id );'.format( hash_ids_table_name )
        
        hash_ids_to_service_ids_and_filenames = HydrusData.BuildKeyToListDict( ( ( hash_id, ( service_id, filename ) ) for ( hash_id, service_id, filename ) in self._Execute( query ) ) )
        
        return hash_ids_to_service_ids_and_filenames
        
    
    def GetServiceDirectoryHashes( self, service_key, dirname ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        directory_id = self.modules_texts.GetTextId( dirname )
        
        hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM service_directory_file_map WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) ) )
        
        hashes = self.modules_hashes_local_cache.GetHashes( hash_ids )
        
        return hashes
        
    
    def GetServiceDirectoriesInfo( self, service_key ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        incomplete_info = self._Execute( 'SELECT directory_id, num_files, total_size, note FROM service_directories WHERE service_id = ?;', ( service_id, ) ).fetchall()
        
        info = [ ( self.modules_texts.GetText( directory_id ), num_files, total_size, note ) for ( directory_id, num_files, total_size, note ) in incomplete_info ]
        
        return info
        
    
    def GetServiceFilename( self, service_id, hash_id ):
        
        result = self._Execute( 'SELECT filename FROM service_filenames WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Service filename not found!' )
            
        
        ( filename, ) = result
        
        return filename
        
    
    def GetServiceFilenames( self, service_key: bytes, hashes: typing.Collection[ bytes ] ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        result = sorted( ( filename for ( filename, ) in self._Execute( 'SELECT filename FROM service_filenames WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) ) )
        
        return result
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        # if content type is a domain, then give urls? bleh
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def SetServiceDirectory( self, service_id: int, hash_ids: typing.Collection[ int ], dirname: str, total_size: int, note: str ):
        
        directory_id = self.modules_texts.GetTextId( dirname )
        
        self._Execute( 'DELETE FROM service_directories WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) )
        self._Execute( 'DELETE FROM service_directory_file_map WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) )
        
        num_files = len( hash_ids )
        
        self._Execute( 'INSERT INTO service_directories ( service_id, directory_id, num_files, total_size, note ) VALUES ( ?, ?, ?, ?, ? );', ( service_id, directory_id, num_files, total_size, note ) )
        self._ExecuteMany( 'INSERT INTO service_directory_file_map ( service_id, directory_id, hash_id ) VALUES ( ?, ?, ? );', ( ( service_id, directory_id, hash_id ) for hash_id in hash_ids ) )
        
    
    def SetServiceFilename( self, service_id: int, hash_id: int, filename: str ):
        
        self._Execute( 'REPLACE INTO service_filenames ( service_id, hash_id, filename ) VALUES ( ?, ?, ? );', ( service_id, hash_id, filename ) )
        
    
