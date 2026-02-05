import collections.abc
import sqlite3

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime

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
        
        super().__init__( 'client files rich metadata', cursor )
        
    
    def FilterHashesByService( self, location_context: ClientLocation.LocationContext, hashes: collections.abc.Sequence[ bytes ] ) -> list[ bytes ]:
        
        # returns hashes in order, to be nice to UI
        
        if location_context.IsEmpty():
            
            return []
            
        
        if location_context.IsAllKnownFiles():
            
            return list( hashes )
            
        
        hashes_to_hash_ids = { hash : self.modules_hashes_local_cache.GetHashId( hash ) for hash in hashes if self.modules_hashes.HasHash( hash ) }
        
        valid_hash_ids = self.modules_files_storage.FilterHashIds( location_context, hashes_to_hash_ids.values() )
        
        return [ hash for hash in hashes if hash in hashes_to_hash_ids and hashes_to_hash_ids[ hash ] in valid_hash_ids ]
        
    
    def GetHashIdStatus( self, hash_id, prefix = '' ) -> ClientImportFiles.FileImportStatus:
        
        if prefix != '':
            
            prefix += ': '
            
        
        hash = self.modules_hashes_local_cache.GetHash( hash_id )
        
        ( is_deleted, timestamp_ms, file_deletion_reason ) = self.modules_files_storage.GetDeletionStatus( self.modules_services.hydrus_local_file_storage_service_id, hash_id )
        
        if is_deleted:
            
            if timestamp_ms is None:
                
                note = 'Deleted from the client before delete times were tracked ({}).'.format( file_deletion_reason )
                
            else:
                
                timestamp = HydrusTime.SecondiseMS( timestamp_ms )
                
                note = 'Deleted from the client {} ({}), which was {} before this check.'.format( HydrusTime.TimestampToPrettyTime( timestamp ), file_deletion_reason, HydrusTime.TimestampToPrettyTimeDelta( timestamp, force_no_iso = True ) )
                
            
            return ClientImportFiles.FileImportStatus( CC.STATUS_DELETED, hash, note = prefix + note )
            
        
        result = self.modules_files_storage.GetImportedTimestampMS( self.modules_services.trash_service_id, hash_id )
        
        if result is not None:
            
            timestamp_ms = result
            
            timestamp = HydrusTime.SecondiseMS( timestamp_ms )
            
            note = 'Currently in trash ({}). Sent there at {}, which was {} before this check.'.format( file_deletion_reason, HydrusTime.TimestampToPrettyTime( timestamp ), HydrusTime.TimestampToPrettyTimeDelta( timestamp, just_now_threshold = 0, force_no_iso = True ) )
            
            return ClientImportFiles.FileImportStatus( CC.STATUS_DELETED, hash, note = prefix + note )
            
        
        result = self.modules_files_storage.GetImportedTimestampMS( self.modules_services.hydrus_local_file_storage_service_id, hash_id )
        
        if result is not None:
            
            timestamp_ms = result
            
            timestamp = HydrusTime.SecondiseMS( timestamp_ms )
            
            mime = self.modules_files_metadata_basic.GetMime( hash_id )
            
            note = 'Imported at {}, which was {} before this check.'.format( HydrusTime.TimestampToPrettyTime( timestamp ), HydrusTime.TimestampToPrettyTimeDelta( timestamp, just_now_threshold = 0, force_no_iso = True ) )
            
            return ClientImportFiles.FileImportStatus( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, hash, mime = mime, note = prefix + note )
            
        
        return ClientImportFiles.FileImportStatus( CC.STATUS_UNKNOWN, hash )
        
    
    def GetHashStatus( self, hash_type, hash, prefix = None ) -> ClientImportFiles.FileImportStatus:
        
        if prefix is None:
            
            prefix = hash_type + ' recognised'
            
        
        if hash_type == 'sha256':
            
            if not self.modules_hashes.HasHash( hash ):
                
                # this used to set the fis.hash = hash here, but that's unhelpful for the callers, who already know the hash and really want to know if there was a good match
                
                return ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
                
            else:
                
                hash_id = self.modules_hashes_local_cache.GetHashId( hash )
                
            
        else:
            
            try:
                
                hash_id = self.modules_hashes.GetHashIdFromExtraHash( hash_type, hash )
                
            except HydrusExceptions.DataMissing:
                
                return ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
                
            
        
        return self.GetHashIdStatus( hash_id, prefix = prefix )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        return []
        
    
    def GetURLStatuses( self, url ) -> list[ ClientImportFiles.FileImportStatus ]:
        
        search_urls = ClientNetworkingFunctions.GetSearchURLs( url )
        
        hash_ids = set()
        
        for search_url in search_urls:
            
            results = self.modules_url_map.GetHashIds( search_url )
            
            hash_ids.update( results )
            
        
        try:
            
            results = [ self.GetHashIdStatus( hash_id, prefix = 'url recognised' ) for hash_id in hash_ids ]
            
        except Exception as e:
            
            return []
            
        
        return results
        
    
