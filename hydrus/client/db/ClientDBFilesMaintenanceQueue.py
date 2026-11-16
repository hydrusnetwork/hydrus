import collections
import collections.abc
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBModule
from hydrus.client.files import ClientFilesMaintenance

class ClientDBFilesMaintenanceQueue( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        ):
        
        super().__init__( 'client files maintenance queue', cursor )
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_hashes_local_cache = modules_hashes_local_cache
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'external_caches.file_maintenance_jobs' ] = [
            ( [ 'job_type' ], False, 545 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'external_caches.file_maintenance_jobs' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, job_type INTEGER, time_can_start INTEGER, PRIMARY KEY ( hash_id, job_type ) );', 400 )
        }
        
    
    def AddJobs( self, hash_ids, job_type, time_can_start = 0 ):
        
        deletee_job_types =  ClientFilesMaintenance.regen_file_enum_to_overruled_jobs[ job_type ]
        
        for deletee_job_type in deletee_job_types:
            
            self._ExecuteMany( 'DELETE FROM file_maintenance_jobs WHERE hash_id = ? AND job_type = ?;', ( ( hash_id, deletee_job_type ) for hash_id in hash_ids ) )
            
        
        #
        
        self._ExecuteMany( 'REPLACE INTO file_maintenance_jobs ( hash_id, job_type, time_can_start ) VALUES ( ?, ?, ? );', ( ( hash_id, job_type, time_can_start ) for hash_id in hash_ids ) )
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_file_maintenance_work' )
        
    
    def AddJobsHashes( self, hashes, job_type, time_can_start = 0 ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        self.AddJobs( hash_ids, job_type, time_can_start = time_can_start )
        
    
    def CancelFiles( self, hash_ids ):
        
        self._ExecuteMany( 'DELETE FROM file_maintenance_jobs WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def CancelJobs( self, job_type ):
        
        self._Execute( 'DELETE FROM file_maintenance_jobs WHERE job_type = ?;', ( job_type, ) )
        
    
    def ClearJobs( self, hash_id, job_types_to_delete ):
        
        self._ExecuteMany( 'DELETE FROM file_maintenance_jobs WHERE hash_id = ? AND job_type = ?;', ( ( hash_id, job_type_to_delete ) for job_type_to_delete in job_types_to_delete ) )
        
    
    def GetJobs( self, job_types = None ):
        
        if job_types is None:
            
            possible_job_types = ClientFilesMaintenance.ALL_REGEN_JOBS_IN_RUN_ORDER
            
        else:
            
            possible_job_types = job_types
            
        
        now = HydrusTime.GetNow()
        
        for job_type in possible_job_types:
            
            hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM file_maintenance_jobs WHERE job_type = ? AND time_can_start < ? LIMIT ?;', ( job_type, now, 256 ) ) )
            
            if len( hash_ids ) > 0:
                
                with self._MakeTemporaryIntegerTable( hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
                    
                    splayed_job_types = HydrusLists.SplayListForDB( possible_job_types )
                    
                    # temp to file jobs
                    hash_ids_to_job_types = HydrusData.BuildKeyToSetDict( self._Execute( f'SELECT hash_id, job_type FROM {temp_hash_ids_table_name} CROSS JOIN file_maintenance_jobs USING ( hash_id ) WHERE time_can_start < ? AND job_type IN {splayed_job_types};', ( HydrusTime.GetNow(), ) ) )
                    
                
                hash_ids_to_hashes = self.modules_hashes_local_cache.GetHashIdsToHashes( hash_ids = hash_ids )
                
                hashes_to_job_types = {}
                
                sort_index = { job_type : index for ( index, job_type ) in enumerate( ClientFilesMaintenance.ALL_REGEN_JOBS_IN_RUN_ORDER ) }
                
                for ( hash_id, job_types ) in hash_ids_to_job_types.items():
                    
                    hash = hash_ids_to_hashes[ hash_id ]
                    
                    job_types = sorted( job_types, key = lambda s: sort_index[ s ] )
                    
                    hashes_to_job_types[ hash ] = job_types
                    
                
                hashes_to_job_types = { hash_ids_to_hashes[ hash_id ] : job_types for ( hash_id, job_types ) in hash_ids_to_job_types.items() }
                
                return hashes_to_job_types
                
            
        
        return {}
        
    
    def GetJobCounts( self ):
        
        now = HydrusTime.GetNow()
        
        result = self._Execute( 'SELECT job_type, time_can_start < ?, COUNT( * ) FROM file_maintenance_jobs GROUP BY job_type, time_can_start < ?;', ( now, now ) ).fetchall()
        
        job_types_to_count = collections.Counter( { job_type : count for ( job_type, can_start, count ) in result if can_start } )
        job_types_to_not_due_count = collections.Counter( { job_type : count for ( job_type, can_start, count ) in result if not can_start } )
        
        all_keys = set( job_types_to_count.keys() ).union( job_types_to_not_due_count.keys() )
        
        job_types_to_counts = { key : ( job_types_to_count[ key ], job_types_to_not_due_count[ key ] ) for key in all_keys }
        
        return job_types_to_counts
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'file_maintenance_jobs', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
