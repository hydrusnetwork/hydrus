import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientFiles
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesMaintenanceQueue
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBRepositories
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.media import ClientMediaResultCache

class ClientDBFilesMaintenance( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_files_maintenance_queue: ClientDBFilesMaintenanceQueue.ClientDBFilesMaintenanceQueue,
        modules_hashes: ClientDBMaster.ClientDBMasterHashes,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_files_metadata_basic: ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles,
        modules_repositories: ClientDBRepositories.ClientDBRepositories,
        weakref_media_result_cache: ClientMediaResultCache.MediaResultCache
        ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files maintenance', cursor )
        
        self.modules_files_maintenance_queue = modules_files_maintenance_queue
        self.modules_hashes = modules_hashes
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_files_metadata_basic = modules_files_metadata_basic
        self.modules_similar_files = modules_similar_files
        self.modules_repositories = modules_repositories
        self._weakref_media_result_cache = weakref_media_result_cache
        
    
    def ClearJobs( self, cleared_job_tuples ):
        
        new_file_info = set()
        
        for ( hash, job_type, additional_data ) in cleared_job_tuples:
            
            hash_id = self.modules_hashes_local_cache.GetHashId( hash )
            
            if additional_data is not None:
                
                if job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA:
                    
                    original_resolution = self.modules_files_metadata_basic.GetResolution( hash_id )
                    original_mime = self.modules_files_metadata_basic.GetMime( hash_id )
                    
                    ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = additional_data
                    
                    resolution_changed = original_resolution != ( width, height )
                    
                    files_rows = [ ( hash_id, size, mime, width, height, duration, num_frames, has_audio, num_words ) ]
                    
                    self.modules_files_metadata_basic.AddFilesInfo( files_rows, overwrite = True )
                    
                    new_file_info.add( ( hash_id, hash ) )
                    
                    if mime not in HC.HYDRUS_UPDATE_FILES:
                        
                        if not self.modules_hashes.HasExtraHashes( hash_id ):
                            
                            self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFiles.REGENERATE_FILE_DATA_JOB_OTHER_HASHES )
                            
                        
                        result = self._Execute( 'SELECT 1 FROM file_modified_timestamps WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                        
                        if result is None:
                            
                            self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP )
                            
                        
                    
                    if mime != original_mime and ( mime in HC.HYDRUS_UPDATE_FILES or original_mime in HC.HYDRUS_UPDATE_FILES ):
                        
                        self.modules_repositories.NotifyUpdatesChanged( ( hash_id, ) )
                        
                    
                    if mime in HC.MIMES_WITH_THUMBNAILS and resolution_changed:
                        
                        self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                        
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_OTHER_HASHES:
                    
                    ( md5, sha1, sha512 ) = additional_data
                    
                    self.modules_hashes.SetExtraHashes( hash_id, md5, sha1, sha512 )
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE:
                    
                    previous_has_icc_profile = self.modules_files_metadata_basic.GetHasICCProfile( hash_id )
                    
                    has_icc_profile = additional_data
                    
                    if previous_has_icc_profile != has_icc_profile:
                        
                        self.modules_files_metadata_basic.SetHasICCProfile( hash_id, has_icc_profile )
                        
                        if has_icc_profile: # we have switched from off to on
                            
                            self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                            
                        
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_PIXEL_HASH:
                    
                    pixel_hash = additional_data
                    
                    pixel_hash_id = self.modules_hashes.GetHashId( pixel_hash )
                    
                    self.modules_similar_files.SetPixelHash( hash_id, pixel_hash_id )
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP:
                    
                    file_modified_timestamp = additional_data
                    
                    self._Execute( 'REPLACE INTO file_modified_timestamps ( hash_id, file_modified_timestamp ) VALUES ( ?, ? );', ( hash_id, file_modified_timestamp ) )
                    
                    new_file_info.add( ( hash_id, hash ) )
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA:
                    
                    perceptual_hashes = additional_data
                    
                    self.modules_similar_files.SetPerceptualHashes( hash_id, perceptual_hashes )
                    
                elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP:
                    
                    should_include = additional_data
                    
                    if should_include:
                        
                        if not self.modules_similar_files.FileIsInSystem( hash_id ):
                            
                            self.modules_files_maintenance_queue.AddJobs( ( hash_id, ), ClientFiles.REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA )
                            
                        
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
                
            
        
    
