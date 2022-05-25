import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesMetadataBasic
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBURLMap
from hydrus.client.importing import ClientImportFiles
from hydrus.client.networking import ClientNetworkingFunctions

class ClientDBFilesMetadataRich( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_services: ClientDBServices,
        modules_hashes: ClientDBMaster.ClientDBMasterHashes,
        modules_files_metadata_basic: ClientDBFilesMetadataBasic.ClientDBFilesMetadataBasic,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_url_map: ClientDBURLMap.ClientDBURLMap
    ):
        
        # we could make this guy take urls, tags, ratings, notes, all that, and then make him the MediaResult cache guy
        # he could also probably do file searching too
        
        self.modules_services = modules_services
        self.modules_hashes = modules_hashes
        self.modules_files_metadata_basic = modules_files_metadata_basic
        self.modules_files_storage = modules_files_storage
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_url_map = modules_url_map
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files rich metadata', cursor )
        
    
    def FilterHashesByService( self, location_context: ClientLocation.LocationContext, hashes: typing.Sequence[ bytes ] ) -> typing.List[ bytes ]:
        
        # returns hashes in order, to be nice to UI
        
        if location_context.IsEmpty():
            
            return []
            
        
        if location_context.IsAllKnownFiles():
            
            return list( hashes )
            
        
        hashes_to_hash_ids = { hash : self.modules_hashes_local_cache.GetHashId( hash ) for hash in hashes if self.modules_hashes.HasHash( hash ) }
        
        valid_hash_ids = self.modules_files_storage.FilterHashIds( location_context, hashes_to_hash_ids.values() )
        
        return [ hash for hash in hashes if hash in hashes_to_hash_ids and hashes_to_hash_ids[ hash ] in valid_hash_ids ]
        
    
    def GetFileHistory( self, num_steps: int ):
        
        # get all sorts of stats and present them in ( timestamp, cumulative_num ) tuple pairs
        
        file_history = {}
        
        # first let's do current files. we increment when added, decrement when we know removed
        
        current_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_media_service_id, HC.CONTENT_STATUS_CURRENT )
        
        current_timestamps = self._STL( self._Execute( 'SELECT timestamp FROM {};'.format( current_files_table_name ) ) )
        
        deleted_files_table_name = ClientDBFilesStorage.GenerateFilesTableName( self.modules_services.combined_local_media_service_id, HC.CONTENT_STATUS_DELETED )
        
        since_deleted = self._STL( self._Execute( 'SELECT original_timestamp FROM {} WHERE original_timestamp IS NOT NULL;'.format( deleted_files_table_name ) ) )
        
        all_known_import_timestamps = list( current_timestamps )
        
        all_known_import_timestamps.extend( since_deleted )
        
        all_known_import_timestamps.sort()
        
        deleted_timestamps = self._STL( self._Execute( 'SELECT timestamp FROM {} WHERE timestamp IS NOT NULL ORDER BY timestamp ASC;'.format( deleted_files_table_name ) ) )
        
        combined_timestamps_with_delta = [ ( timestamp, 1 ) for timestamp in all_known_import_timestamps ]
        combined_timestamps_with_delta.extend( ( ( timestamp, -1 ) for timestamp in deleted_timestamps ) )
        
        combined_timestamps_with_delta.sort()
        
        current_file_history = []
        
        if len( combined_timestamps_with_delta ) > 0:
            
            # set 0 on first file import time
            current_file_history.append( ( combined_timestamps_with_delta[0][0], 0 ) )
            
            if len( combined_timestamps_with_delta ) < 2:
                
                step_gap = 1
                
            else:
                
                step_gap = max( ( combined_timestamps_with_delta[-1][0] - combined_timestamps_with_delta[0][0] ) // num_steps, 1 )
                
            
            total_current_files = 0
            step_timestamp = combined_timestamps_with_delta[0][0]
            
            for ( timestamp, delta ) in combined_timestamps_with_delta:
                
                while timestamp > step_timestamp + step_gap:
                    
                    current_file_history.append( ( step_timestamp, total_current_files ) )
                    
                    step_timestamp += step_gap
                    
                
                total_current_files += delta
                
            
        
        file_history[ 'current' ] = current_file_history
        
        # now deleted times. we will pre-populate total_num_files with non-timestamped records
        
        ( total_deleted_files, ) = self._Execute( 'SELECT COUNT( * ) FROM {} WHERE timestamp IS NULL;'.format( deleted_files_table_name ) ).fetchone()
        
        deleted_file_history = []
        
        if len( deleted_timestamps ) > 0:
            
            if len( deleted_timestamps ) < 2:
                
                step_gap = 1
                
            else:
                
                step_gap = max( ( deleted_timestamps[-1] - deleted_timestamps[0] ) // num_steps, 1 )
                
            
            step_timestamp = deleted_timestamps[0]
            
            for deleted_timestamp in deleted_timestamps:
                
                while deleted_timestamp > step_timestamp + step_gap:
                    
                    deleted_file_history.append( ( step_timestamp, total_deleted_files ) )
                    
                    step_timestamp += step_gap
                    
                
                total_deleted_files += 1
                
            
        
        file_history[ 'deleted' ] = deleted_file_history
        
        # and inbox, which will work backwards since we have numbers for archiving. several subtle differences here
        # we know the inbox now and the recent history of archives and file changes
        # working backwards in time (which reverses increment/decrement):
        # - an archive increments
        # - a file import decrements
        # note that we archive right before we delete a file, so file deletes shouldn't change anything for inbox count. all deletes are on archived files, so the increment will already be counted
        # UPDATE: and now we add archived, which is mostly the same deal but we subtract from current files to start and don't care about file imports since they are always inbox but do care about file deletes
        
        inbox_file_history = []
        archive_file_history = []
        
        ( total_inbox_files, ) = self._Execute( 'SELECT COUNT( * ) FROM file_inbox;' ).fetchone()
        total_current_files = len( current_timestamps )
        
        # I now exclude updates and trash my searching 'all my files'
        total_update_files = 0 #self.modules_files_storage.GetCurrentFilesCount( self.modules_services.local_update_service_id, HC.CONTENT_STATUS_CURRENT )
        total_trash_files = 0 #self.modules_files_storage.GetCurrentFilesCount( self.modules_services.trash_service_id, HC.CONTENT_STATUS_CURRENT )
        
        total_archive_files = ( total_current_files - total_update_files - total_trash_files ) - total_inbox_files
        
        # note also that we do not scrub archived time on a file delete, so this upcoming fetch is for all files ever. this is useful, so don't undo it m8
        archive_timestamps = self._STL( self._Execute( 'SELECT archived_timestamp FROM archive_timestamps ORDER BY archived_timestamp ASC;' ) )
        
        if len( archive_timestamps ) > 0:
            
            first_archive_time = archive_timestamps[0]
            
            combined_timestamps_with_deltas = [ ( timestamp, 1, -1 ) for timestamp in archive_timestamps ]
            combined_timestamps_with_deltas.extend( ( ( timestamp, -1, 0 ) for timestamp in all_known_import_timestamps if timestamp >= first_archive_time ) )
            combined_timestamps_with_deltas.extend( ( ( timestamp, 0, 1 ) for timestamp in deleted_timestamps if timestamp >= first_archive_time ) )
            
            combined_timestamps_with_deltas.sort( reverse = True )
            
            if len( combined_timestamps_with_deltas ) > 0:
                
                if len( combined_timestamps_with_deltas ) < 2:
                    
                    step_gap = 1
                    
                else:
                    
                    # reversed, so first minus last
                    step_gap = max( ( combined_timestamps_with_deltas[0][0] - combined_timestamps_with_deltas[-1][0] ) // num_steps, 1 )
                    
                
                step_timestamp = combined_timestamps_with_deltas[0][0]
                
                for ( archived_timestamp, inbox_delta, archive_delta ) in combined_timestamps_with_deltas:
                    
                    while archived_timestamp < step_timestamp - step_gap:
                        
                        inbox_file_history.append( ( archived_timestamp, total_inbox_files ) )
                        archive_file_history.append( ( archived_timestamp, total_archive_files ) )
                        
                        step_timestamp -= step_gap
                        
                    
                    total_inbox_files += inbox_delta
                    total_archive_files += archive_delta
                    
                
                inbox_file_history.reverse()
                archive_file_history.reverse()
                
            
        
        file_history[ 'inbox' ] = inbox_file_history
        file_history[ 'archive' ] = archive_file_history
        
        return file_history
        
    
    def GetHashIdStatus( self, hash_id, prefix = '' ) -> ClientImportFiles.FileImportStatus:
        
        if prefix != '':
            
            prefix += ': '
            
        
        hash = self.modules_hashes_local_cache.GetHash( hash_id )
        
        ( is_deleted, timestamp, file_deletion_reason ) = self.modules_files_storage.GetDeletionStatus( self.modules_services.combined_local_file_service_id, hash_id )
        
        if is_deleted:
            
            if timestamp is None:
                
                note = 'Deleted from the client before delete times were tracked ({}).'.format( file_deletion_reason )
                
            else:
                
                note = 'Deleted from the client {} ({}), which was {} before this check.'.format( HydrusData.ConvertTimestampToPrettyTime( timestamp ), file_deletion_reason, HydrusData.BaseTimestampToPrettyTimeDelta( timestamp ) )
                
            
            return ClientImportFiles.FileImportStatus( CC.STATUS_DELETED, hash, note = prefix + note )
            
        
        result = self.modules_files_storage.GetCurrentTimestamp( self.modules_services.trash_service_id, hash_id )
        
        if result is not None:
            
            timestamp = result
            
            note = 'Currently in trash ({}). Sent there at {}, which was {} before this check.'.format( file_deletion_reason, HydrusData.ConvertTimestampToPrettyTime( timestamp ), HydrusData.BaseTimestampToPrettyTimeDelta( timestamp, just_now_threshold = 0 ) )
            
            return ClientImportFiles.FileImportStatus( CC.STATUS_DELETED, hash, note = prefix + note )
            
        
        result = self.modules_files_storage.GetCurrentTimestamp( self.modules_services.combined_local_file_service_id, hash_id )
        
        if result is not None:
            
            timestamp = result
            
            mime = self.modules_files_metadata_basic.GetMime( hash_id )
            
            note = 'Imported at {}, which was {} before this check.'.format( HydrusData.ConvertTimestampToPrettyTime( timestamp ), HydrusData.BaseTimestampToPrettyTimeDelta( timestamp, just_now_threshold = 0 ) )
            
            return ClientImportFiles.FileImportStatus( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, hash, mime = mime, note = prefix + note )
            
        
        return ClientImportFiles.FileImportStatus( CC.STATUS_UNKNOWN, hash )
        
    
    def GetHashStatus( self, hash_type, hash, prefix = None ) -> ClientImportFiles.FileImportStatus:
        
        if prefix is None:
            
            prefix = hash_type + ' recognised'
            
        
        if hash_type == 'sha256':
            
            if not self.modules_hashes.HasHash( hash ):
                
                f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
                
                f.hash = hash
                
                return f
                
            else:
                
                hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                
            
        else:
            
            try:
                
                hash_id = self.modules_hashes.GetHashIdFromExtraHash( hash_type, hash )
                
            except HydrusExceptions.DataMissing:
                
                return ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
                
            
        
        return self.GetHashIdStatus( hash_id, prefix = prefix )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        return []
        
    
    def GetURLStatuses( self, url ) -> typing.List[ ClientImportFiles.FileImportStatus ]:
        
        search_urls = ClientNetworkingFunctions.GetSearchURLs( url )
        
        hash_ids = set()
        
        for search_url in search_urls:
            
            results = self.modules_url_map.GetHashIds( search_url )
            
            hash_ids.update( results )
            
        
        try:
            
            results = [ self.GetHashIdStatus( hash_id, prefix = 'url recognised' ) for hash_id in hash_ids ]
            
        except:
            
            return []
            
        
        return results
        
    
