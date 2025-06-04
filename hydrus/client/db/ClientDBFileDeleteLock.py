import collections.abc
import sqlite3

from hydrus.client import ClientGlobals as CG
from hydrus.client.db import ClientDBFilesInbox
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

class ClientDBFileDeleteLock( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_files_inbox: ClientDBFilesInbox.ClientDBFilesInbox ):
        
        self.modules_services = modules_services
        self.modules_files_inbox = modules_files_inbox
        
        super().__init__( 'client file delete lock', cursor )
        
    
    def FilterForPhysicalFileDeleteLock( self, hash_ids: collections.abc.Collection[ int ] ):
        
        # IN ORDER TO KISS, WE MUST NEVER MAKE THIS TOO COMPLICATED BRO
        # If we introduce the Metadata Conditional to the delete file lock, it must be a subset of MCs that support instant quick database lookup predicate generation 
        
        if CG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' ):
            
            if not isinstance( hash_ids, set ):
                
                hash_ids = set( hash_ids )
                
            
            hash_ids = hash_ids.intersection( self.modules_files_inbox.inbox_hash_ids )
            
        
        return hash_ids
        
    
    def GetPhysicalFileDeleteLockSQLitePredicates( self, hash_ids_column_name: str ):
        
        # trying to maintain an air of generalisability here, although if we end up going full metadata conditional this will probably need to get much more complicated and maybe we are talking a table cache
        
        # IN ORDER TO KISS, WE MUST NEVER MAKE THIS TOO COMPLICATED BRO
        # If we introduce the Metadata Conditional to the delete file lock, it must be a subset of MCs that support instant quick database lookup predicate generation 
        
        predicates = []
        
        if CG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' ):
            
            predicates.append( f'EXISTS ( SELECT 1 FROM file_inbox WHERE {hash_ids_column_name} = file_inbox.hash_id )' )
            
        
        return predicates
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
