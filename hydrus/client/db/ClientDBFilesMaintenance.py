import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientFiles
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.media import ClientMediaResultCache

class ClientDBFilesMaintenance( HydrusDBModule.HydrusDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_hashes: ClientDBMaster.ClientDBMasterHashes,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_files_metadata_basic: ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles,
        weakref_media_result_cache: ClientMediaResultCache.MediaResultCache
        ):
        
        HydrusDBModule.HydrusDBModule.__init__( self, 'client files maintenance', cursor )
        
        self.modules_hashes = modules_hashes
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_files_metadata_basic = modules_files_metadata_basic
        self.modules_similar_files = modules_similar_files
        self._weakref_media_result_cache = weakref_media_result_cache
        
    
    def _GetInitialIndexGenerationTuples( self ):
        
        index_generation_tuples = []
        
        return index_generation_tuples
        
    
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
        
    
    def CreateInitialTables( self ):
        
        self._Execute( 'CREATE TABLE IF NOT EXISTS external_caches.file_maintenance_jobs ( hash_id INTEGER, job_type INTEGER, time_can_start INTEGER, PRIMARY KEY ( hash_id, job_type ) );' )
        
    
    def ClearJobs( self, cleared_job_tuples ):
        
        new_file_info = set()
        
        for ( hash, job_type, additional_data ) in cleared_job_tuples:
            
            hash_id = self.modules_hashes_local_cache.GetHashId( hash )
            
            if additional_data is not None:
                
                if job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA:
                    
                    original_resolution = self.modules_files_metadata_basic.GetResolution( hash_id )
                    
                    ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = additional_data
                    
                    resolution_changed = original_resolution != ( width, height )
                    
                    files_rows = [ ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) ]
                    
                    self.modules_files_metadata_basic.AddFilesInfo( files_rows, overwrite = True )
                    
                    new_file_info.add( ( hash_id, hash ) )
                    
                    if mime not in HC.HYDRUS_UPDATE_FILES:
                        
                        if not self.modules_hashes.HasExtraHashes( hash_id ):
                            
                            self.AddJobs( { hash_id }, ClientFiles.REGENERATE_FILE_DATA_JOB_OTHER_HASHES )
                            
                        
                        result = self._Execute( 'SELECT 1 FROM file_modified_timestamps WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                        
                        if result is None:
                            
                            self.AddJobs( { hash_id }, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP )
                            
                        
                    
                    if mime in HC.MIMES_WITH_THUMBNAILS and resolution_changed:
                        
                        self.AddJobs( { hash_id }, ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                        
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_OTHER_HASHES:
                    
                    ( md5, sha1, sha512 ) = additional_data
                    
                    self.modules_hashes.SetExtraHashes( hash_id, md5, sha1, sha512 )
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP:
                    
                    file_modified_timestamp = additional_data
                    
                    self._Execute( 'REPLACE INTO file_modified_timestamps ( hash_id, file_modified_timestamp ) VALUES ( ?, ? );', ( hash_id, file_modified_timestamp ) )
                    
                    new_file_info.add( ( hash_id, hash ) )
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA:
                    
                    phashes = additional_data
                    
                    self.modules_similar_files.SetPHashes( hash_id, phashes )
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP:
                    
                    should_include = additional_data
                    
                    if should_include:
                        
                        if not self.modules_similar_files.FileIsInSystem( hash_id ):
                            
                            self.AddJobs( ( hash_id, ), ClientFiles.REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA )
                            
                        
                    else:
                        
                        # this actually also dissolved the media_id previously to module refactoring. not sure that is really needed, so here we are
                        
                        if self.modules_similar_files.FileIsInSystem( hash_id ):
                            
                            self.modules_similar_files.StopSearchingFile( hash_id )
                            
                        
                    
                
            
            job_types_to_delete = [ job_type ]
            
            # if a user-made 'force regen thumb' call happens to come in while a 'regen thumb if wrong size' job is queued, we can clear it
            
            job_types_to_delete.extend( ClientFiles.regen_file_enum_to_overruled_jobs[ job_type ] )
            
            self._ExecuteMany( 'DELETE FROM file_maintenance_jobs WHERE hash_id = ? AND job_type = ?;', ( ( hash_id, job_type_to_delete ) for job_type_to_delete in job_types_to_delete ) )
            
        
        if len( new_file_info ) > 0:
            
            hashes_that_need_refresh = set()
            
            for ( hash_id, hash ) in new_file_info:
                
                if self._weakref_media_result_cache.HasFile( hash_id ):
                    
                    self._weakref_media_result_cache.DropMediaResult( hash_id, hash )
                    
                    hashes_that_need_refresh.add( hash )
                    
                
            
            if len( hashes_that_need_refresh ) > 0:
                
                HG.client_controller.pub( 'new_file_info', hashes_that_need_refresh )
                
            
        
    
    def GetExpectedTableNames( self ) -> typing.Collection[ str ]:
        
        expected_table_names = [
            'external_caches.file_maintenance_jobs'
        ]
        
        return expected_table_names
        
    
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
        
        if HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'file_maintenance_jobs', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
