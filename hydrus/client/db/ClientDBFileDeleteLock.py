import sqlite3
import typing

from hydrus.client import ClientGlobals as CG
from hydrus.client.db import ClientDBFilesInbox
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

class ClientDBFileDeleteLock( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_files_inbox: ClientDBFilesInbox.ClientDBFilesInbox ):
        
        self.modules_services = modules_services
        self.modules_files_inbox = modules_files_inbox
        
        super().__init__( 'client file delete lock', cursor )
        
    
    def FilterForPhysicalFileDeleteLock( self, hash_ids: typing.Collection[ int ] ):
        
        # TODO: like in the MediaSingleton object, eventually extend this to the metadata conditional object
        # however the trash clearance method uses this guy, so we probably don't want to load up media results over and over bro
        # probably figure out a table cache or something at that point
        
        if CG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' ):
            
            if not isinstance( hash_ids, set ):
                
                hash_ids = set( hash_ids )
                
            
            hash_ids = hash_ids.intersection( self.modules_files_inbox.inbox_hash_ids )
            
        
        return hash_ids
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
