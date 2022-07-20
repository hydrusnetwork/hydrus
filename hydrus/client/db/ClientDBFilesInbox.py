import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBModule

class ClientDBFilesInbox( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage
    ):
        
        self.modules_files_storage = modules_files_storage
        
        self.inbox_hash_ids = set()
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files inbox', cursor )
        
        self._InitCaches()
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.archive_timestamps' ] = [
            ( [ 'archived_timestamp' ], False, 474 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.archive_timestamps' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY, archived_timestamp INTEGER );', 474 ),
            'main.file_inbox' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER PRIMARY KEY );', 400 )
        }
        
    
    def _InitCaches( self ):
        
        if self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'file_inbox', ) ).fetchone() is not None:
            
            self.inbox_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM file_inbox;' ) )
            
        
    
    def ArchiveFiles( self, hash_ids ):
        
        if not isinstance( hash_ids, set ):
            
            hash_ids = set( hash_ids )
            
        
        archiveable_hash_ids = hash_ids.intersection( self.inbox_hash_ids )
        
        if len( archiveable_hash_ids ) > 0:
            
            self._ExecuteMany( 'DELETE FROM file_inbox WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in archiveable_hash_ids ) )
            
            self.inbox_hash_ids.difference_update( archiveable_hash_ids )
            
            now = HydrusData.GetNow()
            
            self._ExecuteMany( 'REPLACE INTO archive_timestamps ( hash_id, archived_timestamp ) VALUES ( ?, ? );', ( ( hash_id, now ) for hash_id in archiveable_hash_ids ) )
            
            service_ids_to_counts = self.modules_files_storage.GetServiceIdCounts( archiveable_hash_ids )
            
            update_rows = list( service_ids_to_counts.items() )
            
            self._ExecuteMany( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in update_rows ] )
            
        
    
    def GetHashIdsToArchiveTimestamps( self, hash_ids_table_name: str ):
        
        return dict( self._Execute( 'SELECT hash_id, archived_timestamp FROM {} CROSS JOIN archive_timestamps USING ( hash_id );'.format( hash_ids_table_name ) ) )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'file_inbox', 'hash_id' ) )
            tables_and_columns.append( ( 'archive_timestamps', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
    def InboxFiles( self, hash_ids: typing.Collection[ int ] ):
        
        if not isinstance( hash_ids, set ):
            
            hash_ids = set( hash_ids )
            
        
        location_context = ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, ) )
        
        hash_ids = self.modules_files_storage.FilterHashIds( location_context, hash_ids )
        
        inboxable_hash_ids = hash_ids.difference( self.inbox_hash_ids )
        
        if len( inboxable_hash_ids ) > 0:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO file_inbox VALUES ( ? );', ( ( hash_id, ) for hash_id in inboxable_hash_ids ) )
            
            self.inbox_hash_ids.update( inboxable_hash_ids )
            
            service_ids_to_counts = self.modules_files_storage.GetServiceIdCounts( inboxable_hash_ids )
            
            if len( service_ids_to_counts ) > 0:
                
                self._ExecuteMany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in service_ids_to_counts.items() ] )
                
            
        
    
