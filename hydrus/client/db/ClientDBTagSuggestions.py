import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

class ClientDBRecentTags( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_tags: ClientDBMaster.ClientDBMasterTags, modules_services: ClientDBServices.ClientDBMasterServices, modules_tags_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalTags ):
        
        self.modules_tags = modules_tags
        self.modules_services = modules_services
        self.modules_tags_local_cache = modules_tags_local_cache
        
        ClientDBModule.ClientDBModule.__init__( self, 'client recent tags', cursor )
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.recent_tags' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, tag_id INTEGER, timestamp_ms INTEGER, PRIMARY KEY ( service_id, tag_id ) );', 546 )
        }
        
    
    def Drop( self, service_id ):
        
        self._Execute( 'DELETE FROM recent_tags WHERe service_id = ?;', ( service_id, ) )
        
    
    def GetRecentTags( self, service_key ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        # we could be clever and do LIMIT and ORDER BY in the delete, but not all compilations of SQLite have that turned on, so let's KISS
        
        tag_ids_to_timestamps_ms = { tag_id : timestamp_ms for ( tag_id, timestamp_ms ) in self._Execute( 'SELECT tag_id, timestamp_ms FROM recent_tags WHERE service_id = ?;', ( service_id, ) ) }
        
        def sort_key( key ):
            
            return tag_ids_to_timestamps_ms[ key ]
            
        
        newest_first = sorted( tag_ids_to_timestamps_ms.keys(), key = sort_key, reverse = True )
        
        num_we_want = CG.client_controller.new_options.GetNoneableInteger( 'num_recent_tags' )
        
        if num_we_want is None:
            
            num_we_want = 20
            
        
        decayed = newest_first[ num_we_want : ]
        
        if len( decayed ) > 0:
            
            self._ExecuteMany( 'DELETE FROM recent_tags WHERE service_id = ? AND tag_id = ?;', ( ( service_id, tag_id ) for tag_id in decayed ) )
            
        
        sorted_recent_tag_ids = newest_first[ : num_we_want ]
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = sorted_recent_tag_ids )
        
        sorted_recent_tags = [ tag_ids_to_tags[ tag_id ] for tag_id in sorted_recent_tag_ids ]
        
        return sorted_recent_tags
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_TAG:
            
            tables_and_columns.append( ( 'recent_tags', 'tag_id' ) )
            
        
        return tables_and_columns
        
    
    def PushRecentTags( self, service_key, tags ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        if tags is None:
            
            self._Execute( 'DELETE FROM recent_tags WHERE service_id = ?;', ( service_id, ) )
            
        else:
            
            now_ms = HydrusTime.GetNowMS()
            
            tag_ids = [ self.modules_tags.GetTagId( tag ) for tag in tags ]
            
            self._ExecuteMany( 'REPLACE INTO recent_tags ( service_id, tag_id, timestamp_ms ) VALUES ( ?, ?, ? );', ( ( service_id, tag_id, now_ms ) for tag_id in tag_ids ) )
            
        
    
