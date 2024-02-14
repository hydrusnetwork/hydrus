import sqlite3
import typing

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientGlobals as CG
from hydrus.client.db import ClientDBFilesInbox
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

class ClientDBFileDeleteLock( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_files_inbox: ClientDBFilesInbox.ClientDBFilesInbox ):
        
        self.modules_services = modules_services
        self.modules_files_inbox = modules_files_inbox
        
        ClientDBModule.ClientDBModule.__init__( self, 'client file delete lock', cursor )
        
    
    def FilterForFileDeleteLock( self, service_id, hash_ids ):
        
        # TODO: like in the MediaSingleton object, eventually extend this to the metadata conditional object
        
        if CG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' ):
            
            service = self.modules_services.GetService( service_id )
            
            if service.GetServiceType() in HC.LOCAL_FILE_SERVICES:
                
                hash_ids = set( hash_ids ).intersection( self.modules_files_inbox.inbox_hash_ids )
                
            
        
        return hash_ids
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
