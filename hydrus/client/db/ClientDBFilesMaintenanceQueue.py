import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientFiles
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.media import ClientMediaResultCache

class ClientDBFilesMaintenanceQueue( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files maintenance queue', cursor )
        
        self.modules_hashes_local_cache = modules_hashes_local_cache
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'external_caches.file_maintenance_jobs' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, job_type INTEGER, time_can_start INTEGER, PRIMARY KEY ( hash_id, job_type ) );', 400 )
        }
        
    
    def AddJobs( self, hash_ids, job_type, time_can_start = 0 ):
        
        deletee_job_types =  ClientFiles.regen_file_enum_to_overruled_jobs[ job_type ]
        
        for deletee_job_type in deletee_job_types:
            
            self._ExecuteMany( 'DELETE FROM file_maintenance_jobs WHERE hash_id = ? AND job_type = ?;', ( ( hash_id, deletee_job_type ) for hash_id in hash_ids ) )
            
        
        #
        
        self._ExecuteMany( 'REPLACE INTO file_maintenance_jobs ( hash_id, job_type, time_can_start ) VALUES ( ?, ?, ? );', ( ( hash_id, job_type, time_can_start ) for hash_id in hash_ids ) )
        
    
    def AddJobsHashes( self, hashes, job_type, time_can_start = 0 ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        self.AddJobs( hash_ids, job_type, time_can_start = time_can_start )
        
    
    def CancelFiles( self, hash_ids ):
        
        self._ExecuteMany( 'DELETE FROM file_maintenance_jobs WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def CancelJobs( self, job_type ):
        
        self._Execute( 'DELETE FROM file_maintenance_jobs WHERE job_type = ?;', ( job_type, ) )
        
    
    def GetJob( self, job_types = None ):
        
        if job_types is None:
            
            possible_job_types = ClientFiles.ALL_REGEN_JOBS_IN_PREFERRED_ORDER
            
        else:
            
            possible_job_types = job_types
            
        
        for job_type in possible_job_types:
            
            hash_ids = self._STL( self._Execute( 'SELECT hash_id FROM file_maintenance_jobs WHERE job_type = ? AND time_can_start < ? LIMIT ?;', ( job_type, HydrusData.GetNow(), 256 ) ) )
            
            if len( hash_ids ) > 0:
                
                hashes = self.modules_hashes_local_cache.GetHashes( hash_ids )
                
                return ( hashes, job_type )
                
            
        
        return None
        
    
    def GetJobCounts( self ):
        
        result = self._Execute( 'SELECT job_type, COUNT( * ) FROM file_maintenance_jobs WHERE time_can_start < ? GROUP BY job_type;', ( HydrusData.GetNow(), ) ).fetchall()
        
        job_types_to_count = dict( result )
        
        return job_types_to_count
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'file_maintenance_jobs', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
