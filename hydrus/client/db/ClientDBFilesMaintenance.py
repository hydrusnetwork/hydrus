import sqlite3
import typing

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientTime
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesMaintenanceQueue
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBMediaResults
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBRepositories
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.db import ClientDBFilesTimestamps
from hydrus.client.files import ClientFilesMaintenance

class ClientDBFilesMaintenance( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_files_maintenance_queue: ClientDBFilesMaintenanceQueue.ClientDBFilesMaintenanceQueue,
        modules_hashes: ClientDBMaster.ClientDBMasterHashes,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_files_metadata_basic: ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic,
        modules_files_timestamps: ClientDBFilesTimestamps.ClientDBFilesTimestamps,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles,
        modules_repositories: ClientDBRepositories.ClientDBRepositories,
        modules_media_results: ClientDBMediaResults.ClientDBMediaResults
        ):
        
        super().__init__( 'client files maintenance', cursor )
        
        self.modules_files_maintenance_queue = modules_files_maintenance_queue
        self.modules_hashes = modules_hashes
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_files_metadata_basic = modules_files_metadata_basic
        self.modules_files_timestamps = modules_files_timestamps
        self.modules_similar_files = modules_similar_files
        self.modules_repositories = modules_repositories
        self.modules_media_results = modules_media_results
        
    
    def ClearJobs( self, cleared_job_tuples ):
        
        new_file_info_managers_info = set()
        new_modified_timestamps_info = set()
        
        for ( hash, job_type, additional_data ) in cleared_job_tuples:
            
            hash_id = self.modules_hashes_local_cache.GetHashId( hash )
            
            if additional_data is not None:
                
                if job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_METADATA:
                    
                    original_resolution = self.modules_files_metadata_basic.GetResolution( hash_id )
                    original_mime = self.modules_files_metadata_basic.GetMime( hash_id )
                    
                    ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = additional_data
                    
                    resolution_changed = original_resolution != ( width, height )
                    
                    files_rows = [ ( hash_id, size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) ]
                    
                    self.modules_files_metadata_basic.AddFilesInfo( files_rows, overwrite = True )
                    
                    new_file_info_managers_info.add( ( hash_id, hash ) )
                    
                    if mime not in HC.HYDRUS_UPDATE_FILES:
                        
                        if not self.modules_hashes.HasExtraHashes( hash_id ):
                            
                            self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_OTHER_HASHES )
                            
                        
                        result = self.modules_files_timestamps.GetTimestampMS( hash_id, ClientTime.TimestampData.STATICSimpleStub( HC.TIMESTAMP_TYPE_MODIFIED_FILE ) )
                        
                        if result is None:
                            
                            self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP )
                            
                        
                    
                    if mime != original_mime and ( mime in HC.HYDRUS_UPDATE_FILES or original_mime in HC.HYDRUS_UPDATE_FILES ):
                        
                        self.modules_repositories.NotifyUpdatesChanged( ( hash_id, ) )
                        
                    
                    if mime in HC.MIMES_WITH_THUMBNAILS and resolution_changed:
                        
                        self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                        
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_OTHER_HASHES:
                    
                    ( md5, sha1, sha512 ) = additional_data
                    
                    self.modules_hashes.SetExtraHashes( hash_id, md5, sha1, sha512 )
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY:
                    
                    previous_has_transparency = self.modules_files_metadata_basic.GetHasTransparency( hash_id )
                    
                    has_transparency = additional_data
                    
                    if previous_has_transparency != has_transparency:
                        
                        self.modules_files_metadata_basic.SetHasTransparency( hash_id, has_transparency )
                        
                        if has_transparency:
                            
                            self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                            
                        
                    
                    new_file_info_managers_info.add( ( hash_id, hash ) )
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF:
                    
                    previous_has_exif = self.modules_files_metadata_basic.GetHasEXIF( hash_id )
                    
                    has_exif = additional_data
                    
                    if previous_has_exif != has_exif:
                        
                        self.modules_files_metadata_basic.SetHasEXIF( hash_id, has_exif )
                        
                    
                    new_file_info_managers_info.add( ( hash_id, hash ) )
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA:
                    
                    previous_has_human_readable_embedded_metadata = self.modules_files_metadata_basic.GetHasHumanReadableEmbeddedMetadata( hash_id )
                    
                    has_human_readable_embedded_metadata = additional_data
                    
                    if previous_has_human_readable_embedded_metadata != has_human_readable_embedded_metadata:
                        
                        self.modules_files_metadata_basic.SetHasHumanReadableEmbeddedMetadata( hash_id, has_human_readable_embedded_metadata )
                        
                    
                    new_file_info_managers_info.add( ( hash_id, hash ) )
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE:
                    
                    previous_has_icc_profile = self.modules_files_metadata_basic.GetHasICCProfile( hash_id )
                    
                    has_icc_profile = additional_data
                    
                    if previous_has_icc_profile != has_icc_profile:
                        
                        self.modules_files_metadata_basic.SetHasICCProfile( hash_id, has_icc_profile )
                        
                        if has_icc_profile: # we have switched from off to on
                            
                            self.modules_files_maintenance_queue.AddJobs( { hash_id }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                            
                        
                    
                    new_file_info_managers_info.add( ( hash_id, hash ) )
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_PIXEL_HASH:
                    
                    pixel_hash = additional_data
                    
                    pixel_hash_id = self.modules_hashes.GetHashId( pixel_hash )
                    
                    self.modules_similar_files.SetPixelHash( hash_id, pixel_hash_id )
                    
                    new_file_info_managers_info.add( ( hash_id, hash ) )
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP:
                    
                    file_modified_timestamp_ms = additional_data
                    
                    self.modules_files_timestamps.SetTime( [ hash_id ], ClientTime.TimestampData.STATICFileModifiedTime( file_modified_timestamp_ms ) )
                    
                    new_modified_timestamps_info.add( ( hash_id, hash ) )
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA:
                    
                    perceptual_hashes = additional_data
                    
                    self.modules_similar_files.SetPerceptualHashes( hash_id, perceptual_hashes )
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP:
                    
                    should_include = additional_data
                    
                    if should_include:
                        
                        if not self.modules_similar_files.FileIsInSystem( hash_id ):
                            
                            self.modules_files_maintenance_queue.AddJobs( ( hash_id, ), ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA )
                            self.modules_files_maintenance_queue.AddJobs( ( hash_id, ), ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_PIXEL_HASH )
                            
                        
                    else:
                        
                        # this actually also dissolved the media_id previously to module refactoring. not sure that is really needed, so here we are
                        
                        if self.modules_similar_files.FileIsInSystem( hash_id ):
                            
                            self.modules_similar_files.StopSearchingFile( hash_id )
                            
                        
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL or job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL:
                    
                    if job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL:
                        
                        was_regenerated = True
                        
                    else:
                        
                        was_regenerated = additional_data
                        
                    
                    if was_regenerated:
                        
                        self.modules_files_maintenance_queue.AddJobs( ( hash_id, ), ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_BLURHASH )
                        
                    
                elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_BLURHASH:
                    
                    blurhash: str = additional_data
                    
                    self.modules_files_metadata_basic.SetBlurhash( hash_id, blurhash )
                    
                    new_file_info_managers_info.add( ( hash_id, hash ) )
                    
                
            
            job_types_to_delete = [ job_type ]
            
            # if a user-made 'force regen thumb' call happens to come in while a 'regen thumb if wrong size' job is queued, we can clear it
            
            job_types_to_delete.extend( ClientFilesMaintenance.regen_file_enum_to_overruled_jobs[ job_type ] )
            
            self._ExecuteMany( 'DELETE FROM file_maintenance_jobs WHERE hash_id = ? AND job_type = ?;', ( ( hash_id, job_type_to_delete ) for job_type_to_delete in job_types_to_delete ) )
            
        
        if len( new_file_info_managers_info ) > 0:
            
            self.modules_media_results.ForceRefreshFileInfoManagers( dict( new_file_info_managers_info ) )
            
        
        if len( new_modified_timestamps_info ) > 0:
            
            self.modules_media_results.ForceRefreshFileModifiedTimestamps( dict( new_modified_timestamps_info ) )
            
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        return []
        
    
