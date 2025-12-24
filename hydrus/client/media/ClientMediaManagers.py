import collections
import collections.abc
import itertools
import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientTime
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchTagContext

class FileDuplicatesManager( object ):
    
    def __init__( self, media_group_king_hash, alternates_group_id, dupe_statuses_to_counts ):
        
        self.media_group_king_hash = media_group_king_hash
        self.alternates_group_id = alternates_group_id
        self.dupe_statuses_to_count = dupe_statuses_to_counts
        
    
    def Duplicate( self ):
        
        dupe_statuses_to_count = dict( self.dupe_statuses_to_count )
        
        return FileDuplicatesManager( self.media_group_king_hash, self.alternates_group_id, dupe_statuses_to_count )
        
    
    def GetDupeCount( self, dupe_type: int ):
        
        if dupe_type not in self.dupe_statuses_to_count:
            
            return 0
            
        
        return self.dupe_statuses_to_count[ dupe_type ]
        
    

class FileInfoManager( object ):
    
    def __init__(
        self,
        hash_id: int,
        hash: bytes,
        size: int | None = None,
        mime: int | None = None,
        width: int | None = None,
        height: int | None = None,
        duration_ms: int | None = None,
        num_frames: int | None = None,
        has_audio: bool | None = None,
        num_words: int | None = None
    ):
        
        if mime is None:
            
            mime = HC.APPLICATION_UNKNOWN
            
        
        self.hash_id = hash_id
        self.hash = hash
        self.size = size
        self.mime = mime
        self.width = width
        self.height = height
        self.duration_ms = duration_ms
        self.num_frames = num_frames
        self.has_audio = has_audio
        self.num_words = num_words
        
        self.original_mime = None
        
        self.has_transparency = False
        self.has_exif = False
        self.has_human_readable_embedded_metadata = False
        self.has_icc_profile = False
        self.blurhash = None
        self.pixel_hash: bytes | None = None
        
    
    def Duplicate( self ):
        
        fim = FileInfoManager( self.hash_id, self.hash, self.size, self.mime, self.width, self.height, self.duration_ms, self.num_frames, self.has_audio, self.num_words )
        
        fim.has_transparency = self.has_transparency
        fim.has_exif = self.has_exif
        fim.has_human_readable_embedded_metadata = self.has_human_readable_embedded_metadata
        fim.has_icc_profile = self.has_icc_profile
        fim.blurhash = self.blurhash
        fim.pixel_hash = self.pixel_hash
        
        return fim
        
    
    def FiletypeIsForced( self ):
        
        return self.original_mime is not None
        
    
    def GetFramerate( self ):
        
        if self.duration_ms is None or self.duration_ms <= 0 or self.num_frames is None or self.num_frames <= 0:
            
            return None
            
        else:
            
            try:
                
                return self.num_frames / HydrusTime.SecondiseMSFloat( self.duration_ms )
                
            except:
                
                return None
                
            
        
    
    def GetOriginalMime( self ):
        
        if self.FiletypeIsForced():
            
            return self.original_mime
            
        else:
            
            return self.mime
            
        
    
    def ToTuple( self ):
        
        return ( self.hash_id, self.hash, self.size, self.mime, self.width, self.height, self.duration_ms, self.num_frames, self.has_audio, self.num_words )
        
    

class TimesManager( object ):
    
    def __init__( self ):
        
        self._simple_timestamp_types_to_timestamps_ms = {}
        self._domains_to_modified_timestamps_ms = {}
        
        self._timestamp_types_to_service_keys_to_timestamps_ms = { timestamp_type : {} for timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES }
        
        self._canvas_types_to_last_viewed_timestamps_ms = {}
        
        # we can complete this task and not populate the dict, so we'll handle 'did we do it?' checks with a bool, otherwise we'll loop the non-generation over and over
        self._aggregate_modified_is_generated = False
        
    
    def _ClearAggregateModifiedTime( self ):
        
        if HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE in self._simple_timestamp_types_to_timestamps_ms:
            
            del self._simple_timestamp_types_to_timestamps_ms[ HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE ]
            
        
        self._aggregate_modified_is_generated = False
        
    
    def _ClearFileServiceTime( self, timestamp_type: int, service_key: bytes ):
        
        service_keys_to_timestamps_ms = self._timestamp_types_to_service_keys_to_timestamps_ms[ timestamp_type ]
        
        if service_key in service_keys_to_timestamps_ms:
            
            del service_keys_to_timestamps_ms[ service_key ]
            
        
    
    def _ClearLastViewedTime( self, canvas_type: int ):
        
        if canvas_type in self._canvas_types_to_last_viewed_timestamps_ms:
            
            del self._canvas_types_to_last_viewed_timestamps_ms[ canvas_type ]
            
        
    
    def _ClearSimpleTime( self, timestamp_type: int ):
        
        if timestamp_type in self._simple_timestamp_types_to_timestamps_ms:
            
            del self._simple_timestamp_types_to_timestamps_ms[ timestamp_type ]
            
            if timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE:
                
                self._ClearAggregateModifiedTime()
                
            
        
    
    def _GenerateAggregateModifiedTime( self ):
        
        all_timestamps_ms = { timestamp_ms for ( domain, timestamp_ms ) in self._domains_to_modified_timestamps_ms.items() }
        
        if HC.TIMESTAMP_TYPE_MODIFIED_FILE in self._simple_timestamp_types_to_timestamps_ms:
            
            all_timestamps_ms.add( self._simple_timestamp_types_to_timestamps_ms[ HC.TIMESTAMP_TYPE_MODIFIED_FILE ])
            
        
        if len( all_timestamps_ms ) > 0:
            
            self._simple_timestamp_types_to_timestamps_ms[ HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE ] = min( all_timestamps_ms )
            
        
        self._aggregate_modified_is_generated = True
        
    
    def _GetFileServiceTimestampMS( self, timestamp_type: int, service_key: bytes ) -> int | None:
        
        return self._timestamp_types_to_service_keys_to_timestamps_ms[ timestamp_type ].get( service_key, None )
        
    
    def _GetLastViewedTimestampMS( self, canvas_type: int ) -> int | None:
        
        return self._canvas_types_to_last_viewed_timestamps_ms.get( canvas_type, None )
        
    
    def _GetSimpleTimestampMS( self, timestamp_type: int ) -> int | None:
        
        if timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE and not self._aggregate_modified_is_generated:
            
            self._GenerateAggregateModifiedTime()
            
        
        return self._simple_timestamp_types_to_timestamps_ms.get( timestamp_type, None )
        
    
    def _GetDomainModifiedTimestampMS( self, domain: str ) -> int | None:
        
        return self._domains_to_modified_timestamps_ms.get( domain, None )
        
    
    def _SetDomainModifiedTimestampMS( self, domain: str, timestamp_ms: int ):
        
        self._domains_to_modified_timestamps_ms[ domain ] = timestamp_ms
        
        self._ClearAggregateModifiedTime()
        
    
    def _SetFileServiceTimestampMS( self, timestamp_type: int, service_key: bytes, timestamp_ms: int ):
        
        self._timestamp_types_to_service_keys_to_timestamps_ms[ timestamp_type ][ service_key ] = timestamp_ms
        
    
    def _SetLastViewedTimestampMS( self, canvas_type: int, timestamp_ms: int ):
        
        self._canvas_types_to_last_viewed_timestamps_ms[ canvas_type ] = timestamp_ms
        
    
    def _SetSimpleTimestampMS( self, timestamp_type: int, timestamp_ms: int ):
        
        self._simple_timestamp_types_to_timestamps_ms[ timestamp_type ] = timestamp_ms
        
        if timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_FILE:
            
            self._ClearAggregateModifiedTime()
            
        
    
    def ClearArchivedTime( self ):
        
        self._ClearSimpleTime( HC.TIMESTAMP_TYPE_ARCHIVED )
        
    
    def ClearDeletedTime( self, service_key: bytes ):
        
        self._ClearFileServiceTime( HC.TIMESTAMP_TYPE_DELETED, service_key )
        
    
    def ClearImportedTime( self, service_key: bytes ):
        
        self._ClearFileServiceTime( HC.TIMESTAMP_TYPE_IMPORTED, service_key )
        
    
    def ClearLastViewedTime( self, canvas_type: int ):
        
        self._ClearLastViewedTime( canvas_type )
        
    
    def ClearPreviouslyImportedTime( self, service_key: bytes ):
        
        self._ClearFileServiceTime( HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, service_key )
        
    
    def ClearTime( self, timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data.location in self._domains_to_modified_timestamps_ms:
                
                del self._domains_to_modified_timestamps_ms[ timestamp_data.location ]
                
                self._ClearAggregateModifiedTime()
                
            
        elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            self._ClearLastViewedTime( timestamp_data.location )
            
        elif timestamp_data.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            self._ClearFileServiceTime( timestamp_data.timestamp_type, timestamp_data.location )
            
        elif timestamp_data.timestamp_type in ClientTime.SIMPLE_TIMESTAMP_TYPES:
            
            self._ClearSimpleTime( timestamp_data.timestamp_type )
            
        
    
    def Duplicate( self ) -> "TimesManager":
        
        times_manager = TimesManager()
        
        times_manager._simple_timestamp_types_to_timestamps_ms = dict( self._simple_timestamp_types_to_timestamps_ms )
        times_manager._domains_to_modified_timestamps_ms = dict( self._domains_to_modified_timestamps_ms )
        
        return times_manager
        
    
    def GetAggregateModifiedTimestampMS( self ):
        
        return self._GetSimpleTimestampMS( HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE )
        
    
    def GetArchivedTimestampMS( self ) -> int | None:
        
        return self._GetSimpleTimestampMS( HC.TIMESTAMP_TYPE_ARCHIVED )
        
    
    def GetDeletedTimestampMS( self, service_key: bytes ) -> int | None:
        
        return self._GetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_DELETED, service_key )
        
    
    def GetDomainModifiedTimestampMS( self, domain: str ) -> int | None:
        
        return self._GetDomainModifiedTimestampMS( domain )
        
    
    def GetDomainModifiedTimestampsMS( self ) -> dict[ str, int ]:
        
        return dict( self._domains_to_modified_timestamps_ms )
        
    
    def GetDomainModifiedTimestampDatas( self ) -> collections.abc.Collection[ ClientTime.TimestampData ]:
        
        return [ ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN, location = domain, timestamp_ms = timestamp_ms ) for ( domain, timestamp_ms ) in self._domains_to_modified_timestamps_ms.items() ]
        
    
    def GetFileModifiedTimestampMS( self ) -> int | None:
        
        return self._GetSimpleTimestampMS( HC.TIMESTAMP_TYPE_MODIFIED_FILE )
        
    
    def GetFileServiceTimestampDatas( self ) -> collections.abc.Collection[ ClientTime.TimestampData ]:
        
        result = []
        
        for ( timestamp_type, service_keys_to_timestamps_ms ) in self._timestamp_types_to_service_keys_to_timestamps_ms.items():
            
            for ( service_key, timestamp_ms ) in service_keys_to_timestamps_ms.items():
                
                result.append( ClientTime.TimestampData( timestamp_type = timestamp_type, location = service_key, timestamp_ms = timestamp_ms ) )
                
            
        
        return result
        
    
    def GetImportedTimestampMS( self, service_key: bytes ) -> int | None:
        
        return self._GetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_IMPORTED, service_key )
        
    
    def GetLastViewedTimestampMS( self, canvas_type ) -> int | None:
        
        return self._GetLastViewedTimestampMS( canvas_type )
        
    
    def GetPreviouslyImportedTimestampMS( self, service_key: bytes ) -> int | None:
        
        return self._GetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, service_key )
        
    
    def GetTimestampMSFromStub( self, timestamp_data_stub: ClientTime.TimestampData ) -> int | None:
        
        if timestamp_data_stub.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data_stub.location is None:
                
                return None
                
            
            return self._GetDomainModifiedTimestampMS( timestamp_data_stub.location )
            
        elif timestamp_data_stub.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            if timestamp_data_stub.location is None:
                
                return None
                
            
            return self._GetLastViewedTimestampMS( timestamp_data_stub.location )
            
        elif timestamp_data_stub.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            if timestamp_data_stub.location is None:
                
                return None
                
            
            return self._GetFileServiceTimestampMS( timestamp_data_stub.timestamp_type, timestamp_data_stub.location )
            
        elif timestamp_data_stub.timestamp_type in ClientTime.SIMPLE_TIMESTAMP_TYPES:
            
            return self._GetSimpleTimestampMS( timestamp_data_stub.timestamp_type )
            
        
        return None
        
    
    def SetArchivedTimestampMS( self, timestamp_ms: int ):
        
        self._SetSimpleTimestampMS( HC.TIMESTAMP_TYPE_ARCHIVED, timestamp_ms )
        
    
    def SetDeletedTimestampMS( self, service_key: bytes, timestamp_ms: int ):
        
        self._SetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_DELETED, service_key, timestamp_ms )
        
    
    def SetDeletedTimestampsMS( self, service_keys_to_timestamps_ms: dict[ bytes, int ] ):
        
        for ( service_key, timestamp_ms ) in service_keys_to_timestamps_ms.items():
            
            self._SetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_DELETED, service_key, timestamp_ms )
            
        
    
    def SetDomainModifiedTimestampMS( self, domain: str, timestamp_ms: int ):
        
        self._SetDomainModifiedTimestampMS( domain, timestamp_ms )
        
    
    def SetFileModifiedTimestampMS( self, timestamp_ms: int ):
        
        self._SetSimpleTimestampMS( HC.TIMESTAMP_TYPE_MODIFIED_FILE, timestamp_ms )
        
    
    def SetLastViewedTimestampMS( self, canvas_type, timestamp_ms ):
        
        self._SetLastViewedTimestampMS( canvas_type, timestamp_ms )
        
    
    def SetPreviouslyImportedTimestampMS( self, service_key, timestamp_ms ):
        
        self._SetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, service_key, timestamp_ms )
        
    
    def SetPreviouslyImportedTimestampsMS( self, service_keys_to_timestamps_ms: dict[ bytes, int ] ):
        
        for ( service_key, timestamp_ms ) in service_keys_to_timestamps_ms.items():
            
            self._SetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, service_key, timestamp_ms )
            
        
    
    def SetImportedTimestampMS( self, service_key: bytes, timestamp_ms: int ):
        
        self._SetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_IMPORTED, service_key, timestamp_ms )
        
    
    def SetImportedTimestampsMS( self, service_keys_to_timestamps_ms: dict[ bytes, int ] ):
        
        for ( service_key, timestamp_ms ) in service_keys_to_timestamps_ms.items():
            
            self._SetFileServiceTimestampMS( HC.TIMESTAMP_TYPE_IMPORTED, service_key, timestamp_ms )
            
        
    
    def SetTime( self, timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp_ms is None:
            
            return
            
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_data.location is None:
                
                return
                
            
            self._SetDomainModifiedTimestampMS( timestamp_data.location, timestamp_data.timestamp_ms )
            
        elif timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            if timestamp_data.location is None:
                
                return
                
            
            self._SetLastViewedTimestampMS( timestamp_data.location, timestamp_data.timestamp_ms )
            
        elif timestamp_data.timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            if timestamp_data.location is None:
                
                return
                
            
            self._SetFileServiceTimestampMS( timestamp_data.timestamp_type, timestamp_data.location, timestamp_data.timestamp_ms )
            
        elif timestamp_data.timestamp_type in ClientTime.SIMPLE_TIMESTAMP_TYPES:
            
            self._SetSimpleTimestampMS( timestamp_data.timestamp_type, timestamp_data.timestamp_ms )
            
        
    
    def UpdateTime( self, timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.timestamp_ms is None:
            
            return
            
        
        if timestamp_data.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            existing_timestamp_ms = self._GetDomainModifiedTimestampMS( timestamp_data.location )
            
        else:
            
            existing_timestamp_ms = self._GetSimpleTimestampMS( timestamp_data.timestamp_type )
            
        
        if existing_timestamp_ms is None or ClientTime.ShouldUpdateModifiedTime( existing_timestamp_ms, timestamp_data.timestamp_ms ):
            
            self.SetTime( timestamp_data )
            
        
    

class FileViewingStatsManager( object ):
    
    def __init__(
        self,
        times_manager: TimesManager,
        view_rows: collections.abc.Collection
    ):
        
        self._times_manager = times_manager
        
        self.views = collections.Counter()
        self.viewtimes_ms = collections.Counter()
        
        for ( canvas_type, last_viewed_timestamp_ms, views, viewtime_ms ) in view_rows:
            
            if last_viewed_timestamp_ms is not None:
                
                self._times_manager.SetLastViewedTimestampMS( canvas_type, last_viewed_timestamp_ms )
                
            
            if views != 0:
                
                self.views[ canvas_type ] = views
                
            
            if viewtime_ms != 0:
                
                self.viewtimes_ms[ canvas_type ] = viewtime_ms
                
            
        
    
    def Duplicate( self, pre_duped_times_manager: TimesManager ) -> "FileViewingStatsManager":
        
        view_rows = []
        
        for canvas_type in ( CC.CANVAS_MEDIA_VIEWER, CC.CANVAS_PREVIEW, CC.CANVAS_CLIENT_API ):
            
            last_viewed_timestamp_ms = self._times_manager.GetLastViewedTimestampMS( canvas_type )
            
            views = self.views[ canvas_type ]
            viewtime_ms = self.viewtimes_ms[ canvas_type ]
            
            view_rows.append( ( canvas_type, last_viewed_timestamp_ms, views, viewtime_ms ) )
            
        
        return FileViewingStatsManager( pre_duped_times_manager, view_rows )
        
    
    def GetPrettyViewsLine( self, canvas_types: collections.abc.Collection[ int ] ) -> str:
        
        # TODO: update this and callers to handle client api canvas
        if len( canvas_types ) == 1:
            
            canvas_type = list( canvas_types )[0]
            
            canvas_type_string = ' in ' + CC.canvas_type_str_lookup[ canvas_type ]
            
        else:
            
            canvas_type_string = ''
            
        
        views_total = sum( ( self.views[ canvas_type ] for canvas_type in canvas_types ) )
        viewtime_ms_total = sum( ( self.viewtimes_ms[ canvas_type ] for canvas_type in canvas_types ) )
        
        if views_total == 0:
            
            return 'no view record{}'.format( canvas_type_string )
            
        
        last_viewed_times_ms = []
        
        for canvas_type in canvas_types:
            
            last_viewed_timestamp_ms = self._times_manager.GetLastViewedTimestampMS( canvas_type )
            
            if last_viewed_timestamp_ms is not None:
                
                last_viewed_times_ms.append( last_viewed_timestamp_ms )
                
            
        
        if len( last_viewed_times_ms ) == 0:
            
            last_viewed_string = 'no recorded last view time'
            
        else:
            
            last_viewed_string = 'last {}'.format( HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( max( last_viewed_times_ms ) ) ) )
            
        
        return 'viewed {} times{}, totalling {}, {}'.format( HydrusNumbers.ToHumanInt( views_total ), canvas_type_string, HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusTime.SecondiseMSFloat( viewtime_ms_total ) ), last_viewed_string )
        
    
    def GetTimesManager( self ) -> TimesManager:
        
        return self._times_manager
        
    
    def GetViews( self, canvas_type: int ) -> int:
        
        return self.views[ canvas_type ]
        
    
    def GetViewtimeMS( self, canvas_type: int ) -> int:
        
        return self.viewtimes_ms[ canvas_type ]
        
    
    def HasViews( self, canvas_type: int ) -> bool:
        
        return self.views[ canvas_type ] > 0
        
    
    def MergeCounts( self, file_viewing_stats_manager: "FileViewingStatsManager" ):
        
        for canvas_type in ( CC.CANVAS_MEDIA_VIEWER, CC.CANVAS_PREVIEW, CC.CANVAS_CLIENT_API ):
            
            timestamps_ms = { self._times_manager.GetLastViewedTimestampMS( canvas_type ), file_viewing_stats_manager.GetTimesManager().GetLastViewedTimestampMS( canvas_type ) }
            
            timestamps_ms.discard( None )
            
            if len( timestamps_ms ) > 0:
                
                last_viewed_timestamp_ms = max( timestamps_ms )
                
                self._times_manager.SetLastViewedTimestampMS( canvas_type, last_viewed_timestamp_ms )
                
            
        
        self.views.update( file_viewing_stats_manager.views )
        self.viewtimes_ms.update( file_viewing_stats_manager.viewtimes_ms )
        
    
    def ProcessContentUpdate( self, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            ( hash, canvas_type, view_timestamp_ms, views_delta, viewtime_delta_ms ) = row
            
            if view_timestamp_ms is not None:
                
                self._times_manager.SetLastViewedTimestampMS( canvas_type, view_timestamp_ms )
                
            
            self.views[ canvas_type ] += views_delta
            self.viewtimes_ms[ canvas_type ] += viewtime_delta_ms
            
        elif action == HC.CONTENT_UPDATE_SET:
            
            ( hash, canvas_type, view_timestamp_ms, views, viewtime_ms ) = row
            
            if view_timestamp_ms is not None:
                
                self._times_manager.SetLastViewedTimestampMS( canvas_type, view_timestamp_ms )
                
            
            self.views[ canvas_type ] = views
            self.viewtimes_ms[ canvas_type ] = viewtime_ms
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            self._times_manager.ClearLastViewedTime( CC.CANVAS_MEDIA_VIEWER )
            self._times_manager.ClearLastViewedTime( CC.CANVAS_PREVIEW )
            self._times_manager.ClearLastViewedTime( CC.CANVAS_CLIENT_API )
            
            self.views = collections.Counter()
            self.viewtimes_ms = collections.Counter()
            
        
    
    @staticmethod
    def STATICGenerateCombinedManager( sub_fvsms: collections.abc.Iterable[ "FileViewingStatsManager" ] ):
        
        fvsm = FileViewingStatsManager.STATICGenerateEmptyManager( TimesManager() )
        
        for sub_fvsm in sub_fvsms:
            
            fvsm.MergeCounts( sub_fvsm )
            
        
        return fvsm
        
    
    @staticmethod
    def STATICGenerateEmptyManager( times_manager: TimesManager ):
        
        return FileViewingStatsManager( times_manager, [] )
        
    

class LocationsManager( object ):
    
    def __init__(
        self,
        current: set[ bytes ],
        deleted: set[ bytes ],
        pending: set[ bytes ],
        petitioned: set[ bytes ],
        times_manager: TimesManager,
        inbox: bool = False,
        urls: set[ str ] | None = None,
        service_keys_to_filenames: dict[ bytes, str ] | None = None,
        local_file_deletion_reason: str = None
    ):
        
        self._current = current
        self._deleted = deleted
        self._pending = pending
        self._petitioned = petitioned
        self._times_manager = times_manager
        
        self.inbox = inbox
        
        if urls is None:
            
            urls = set()
            
        
        self._urls = urls
        
        if service_keys_to_filenames is None:
            
            service_keys_to_filenames = {}
            
        
        self._service_keys_to_filenames = service_keys_to_filenames
        
        self._local_file_deletion_reason = local_file_deletion_reason
        
    
    def _AddToService( self, service_key, do_undelete = False, forced_import_time_ms = None ):
        
        service_type = CG.client_controller.services_manager.GetServiceType( service_key )
        
        if forced_import_time_ms is None:
            
            import_timestamp_ms = HydrusTime.GetNowMS()
            
        else:
            
            import_timestamp_ms = forced_import_time_ms
            
        
        if service_key in self._deleted:
            
            if do_undelete:
                
                previously_imported_timestamp_ms = self._times_manager.GetPreviouslyImportedTimestampMS( service_key )
                
                if previously_imported_timestamp_ms is not None:
                    
                    import_timestamp_ms = previously_imported_timestamp_ms
                    
                
            
            self._times_manager.ClearDeletedTime( service_key )
            self._times_manager.ClearPreviouslyImportedTime( service_key )
            
            self._deleted.discard( service_key )
            
        else:
            
            if do_undelete:
                
                # was never deleted from here, so no undelete to do!
                return
                
            
        
        local_service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
        
        if service_key in local_service_keys:
            
            if CC.TRASH_SERVICE_KEY in self._current:
                
                self._times_manager.ClearImportedTime( CC.TRASH_SERVICE_KEY )
                
                self._current.discard( CC.TRASH_SERVICE_KEY )
                
            
            # forced import time here to handle do_undelete, ensuring old timestamp is propagated
            
            self._AddToService( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, forced_import_time_ms = import_timestamp_ms )
            self._AddToService( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, forced_import_time_ms = import_timestamp_ms )
            
        
        if service_key not in self._current:
            
            self._times_manager.SetImportedTimestampMS( service_key, import_timestamp_ms )
            
            self._current.add( service_key )
            
            if service_key == CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY:
                
                self.inbox = True
                
            
        
        self._pending.discard( service_key )
        
        if service_type in HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE:
            
            all_service_keys_covered_by_combined_deleted_files = CG.client_controller.services_manager.GetServiceKeys( HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE )
            
            if len( self._deleted.intersection( all_service_keys_covered_by_combined_deleted_files ) ) == 0:
                
                self._DeleteFromService( CC.COMBINED_DELETED_FILE_SERVICE_KEY, None )
                
            
        
    
    def _DeleteFromService( self, service_key: bytes, reason: str | None ):
        
        service_type = CG.client_controller.services_manager.GetServiceType( service_key )
        
        if service_key in self._current:
            
            previously_imported_timestamp_ms = self._times_manager.GetImportedTimestampMS( service_key )
            
            self._times_manager.ClearImportedTime( service_key )
            
            self._current.discard( service_key )
            
        else:
            
            previously_imported_timestamp_ms = None
            
        
        if service_type in HC.FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE:
            
            self._AddToService( CC.COMBINED_DELETED_FILE_SERVICE_KEY )
            
        
        make_a_delete_record = service_key not in self._deleted and service_type not in HC.FILE_SERVICES_WITH_NO_DELETE_RECORD
        
        if make_a_delete_record:
            
            self._times_manager.SetDeletedTimestampMS( service_key, HydrusTime.GetNowMS() )
            self._times_manager.SetPreviouslyImportedTimestampMS( service_key, previously_imported_timestamp_ms )
            
            self._deleted.add( service_key )
            
        
        self._petitioned.discard( service_key )
        
        local_service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
        
        if service_key in local_service_keys:
            
            if reason is not None:
                
                self._local_file_deletion_reason = reason
                
            
            not_in_a_local_service_any_more = self._current.isdisjoint( local_service_keys )
            
            if not_in_a_local_service_any_more:
                
                self._DeleteFromService( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, reason )
                self._AddToService( CC.TRASH_SERVICE_KEY )
                
            
        elif service_key == CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY:
            
            for local_service_key in list( self._current.intersection( local_service_keys ) ):
                
                self._DeleteFromService( local_service_key, reason )
                
            
            if CC.TRASH_SERVICE_KEY in self._current:
                
                self._DeleteFromService( CC.TRASH_SERVICE_KEY, reason )
                
            
            self.inbox = False
            
        
    
    def DeletePending( self, service_key ):
        
        self._pending.discard( service_key )
        self._petitioned.discard( service_key )
        
    
    def Duplicate( self, times_manager: TimesManager ):
        
        current = set( self._current )
        deleted = set( self._deleted )
        pending = set( self._pending )
        petitioned = set( self._petitioned )
        urls = set( self._urls )
        service_keys_to_filenames = dict( self._service_keys_to_filenames )
        
        return LocationsManager(
            current,
            deleted,
            pending,
            petitioned,
            times_manager,
            inbox = self.inbox,
            urls = urls,
            service_keys_to_filenames = service_keys_to_filenames,
            local_file_deletion_reason = self._local_file_deletion_reason
        )
        
    
    def GetCDPP( self ):
        
        return ( self._current, self._deleted, self._pending, self._petitioned )
        
    
    def GetCurrent( self ):
        
        return self._current
        
    
    def GetDeleted( self ):
        
        return self._deleted
        
    
    def GetInbox( self ):
        
        return self.inbox
        
    
    def GetPending( self ):
        
        return self._pending
        
    
    def GetPetitioned( self ):
        
        return self._petitioned
        
    
    def GetBestCurrentTimestamp( self, location_context: ClientLocation.LocationContext ):
        
        timestamps_ms = { self._times_manager.GetImportedTimestampMS( service_key ) for service_key in location_context.current_service_keys }
        
        timestamps_ms.discard( None )
        
        if len( timestamps_ms ) == 0:
            
            return None
            
        else:
            
            return min( timestamps_ms )
            
        
    
    def GetLocalFileDeletionReason( self ) -> str:
        
        if self._local_file_deletion_reason is None:
            
            return 'Unknown deletion reason.'
            
        else:
            
            return self._local_file_deletion_reason
            
        
    
    def GetLocationStrings( self ):
        
        # this whole method seems ass-backwards somehow!
        
        service_location_strings = []
        
        local_file_services = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) ) )
        
        local_file_services.sort( key = lambda s: s.GetName() )
        
        for local_service in local_file_services:
            
            name = local_service.GetName()
            service_key = local_service.GetServiceKey()
            
            if service_key in self._current:
                
                service_location_strings.append( name )
                
            
        
        remote_file_services = list( CG.client_controller.services_manager.GetServices( ( HC.FILE_REPOSITORY, HC.IPFS ) ) )
        
        remote_file_services.sort( key = lambda s: s.GetName() )
        
        for remote_service in remote_file_services:
            
            name = remote_service.GetName()
            service_key = remote_service.GetServiceKey()
            
            if service_key in self._pending:
                
                service_location_strings.append( name + ' (+)' )
                
            elif service_key in self._current:
                
                if service_key in self._petitioned:
                    
                    service_location_strings.append( name + ' (-)' )
                    
                else:
                    
                    service_location_strings.append( name )
                    
                
            
        
        return service_location_strings
        
    
    def GetServiceFilename( self, service_key ) -> str | None:
        
        if service_key in self._service_keys_to_filenames:
            
            return self._service_keys_to_filenames[ service_key ]
            
        else:
            
            return None
            
        
    
    def GetServiceFilenames( self ) -> dict[ bytes, str ]:
        
        return dict( self._service_keys_to_filenames )
        
    
    def GetTimesManager( self ) -> TimesManager:
        
        return self._times_manager
        
    
    def GetURLs( self ):
        
        return self._urls
        
    
    def HasLocalFileDeletionReason( self ) -> bool:
        
        return self._local_file_deletion_reason is not None
        
    
    def IsDownloading( self ):
        
        return CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in self._pending
        
    
    def IsInLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        if location_context.IsAllKnownFiles():
            
            return True
            
        
        for current_service_key in location_context.current_service_keys:
            
            if current_service_key in self._current:
                
                return True
                
            
        
        for deleted_service_key in location_context.deleted_service_keys:
            
            if deleted_service_key in self._deleted:
                
                return True
                
            
        
        return False
        
    
    def IsLocal( self ):
        
        return CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in self._current
        
    
    def IsRemote( self ):
        
        return CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY not in self._current
        
    
    def IsTrashed( self ):
        
        return CC.TRASH_SERVICE_KEY in self._current
        
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if data_type == HC.CONTENT_TYPE_FILES:
            
            if action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                
                if service_key in self._deleted:
                    
                    if service_key == CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY:
                        
                        service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, HC.HYDRUS_LOCAL_FILE_STORAGE ) )
                        
                    else:
                        
                        service_keys = ( service_key, )
                        
                    
                    for service_key in service_keys:
                        
                        self._times_manager.ClearDeletedTime( service_key )
                        self._times_manager.ClearPreviouslyImportedTime( service_key )
                        
                        self._deleted.discard( service_key )
                        
                    
                
            elif action == HC.CONTENT_UPDATE_ARCHIVE:
                
                if self.inbox:
                    
                    self.inbox = False
                    
                    self._times_manager.SetArchivedTimestampMS( HydrusTime.GetNowMS() )
                    
                
            elif action == HC.CONTENT_UPDATE_INBOX:
                
                self.inbox = True
                
                self._times_manager.ClearArchivedTime()
                
            elif action == HC.CONTENT_UPDATE_ADD:
                
                try:
                    
                    service_type = CG.client_controller.services_manager.GetServiceType( service_key )
                    
                except HydrusExceptions.DataMissing:
                    
                    return
                    
                
                if service_type == HC.IPFS:
                    
                    self._AddToService( service_key )
                    
                    if service_type == HC.IPFS:
                        
                        ( file_info_manager, multihash ) = row
                        
                        self._service_keys_to_filenames[ service_key ] = multihash
                        
                    
                else:
                    
                    ( file_info_manager, timestamp_ms ) = row
                    
                    self._AddToService( service_key, forced_import_time_ms = timestamp_ms )
                    
                
            elif action in ( HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_DELETE_FROM_SOURCE_AFTER_MIGRATE ):
                
                if content_update.HasReason():
                    
                    reason = content_update.GetReason()
                    
                else:
                    
                    reason = None
                    
                
                if service_key == CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY:
                    
                    for s_k in CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, HC.COMBINED_LOCAL_FILE_DOMAINS ) ):
                        
                        if s_k in self._current:
                            
                            self._DeleteFromService( s_k, reason )
                            
                        
                    
                elif service_key == CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY:
                    
                    for s_k in CG.client_controller.services_manager.GetServiceKeys( ( HC.HYDRUS_LOCAL_FILE_STORAGE, HC.COMBINED_LOCAL_FILE_DOMAINS, HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_TRASH_DOMAIN, HC.LOCAL_FILE_UPDATE_DOMAIN ) ):
                        
                        if s_k in self._current:
                            
                            self._DeleteFromService( s_k, reason )
                            
                        
                    
                else:
                    
                    self._DeleteFromService( service_key, reason )
                    
                
            elif action == HC.CONTENT_UPDATE_UNDELETE:
                
                if service_key == CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY:
                    
                    for s_k in CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ):
                        
                        if s_k in self._deleted:
                            
                            self._AddToService( s_k, do_undelete = True )
                            
                        
                    
                else:
                    
                    self._AddToService( service_key, do_undelete = True )
                    
                
            elif action == HC.CONTENT_UPDATE_PEND:
                
                if service_key not in self._current:
                    
                    self._pending.add( service_key )
                    
                
            elif action == HC.CONTENT_UPDATE_PETITION:
                
                if service_key not in self._deleted:
                    
                    self._petitioned.add( service_key )
                    
                
            elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                
                self._pending.discard( service_key )
                
            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                
                self._petitioned.discard( service_key )
                
            
        elif data_type == HC.CONTENT_TYPE_URLS:
            
            if action == HC.CONTENT_UPDATE_ADD:
                
                ( urls, hashes ) = row
                
                self._urls.update( urls )
                
            elif action == HC.CONTENT_UPDATE_DELETE:
                
                ( urls, hashes ) = row
                
                self._urls.difference_update( urls )
                
                
            
        elif data_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            ( hashes, timestamp_data ) = row
            
            if action == HC.CONTENT_UPDATE_ADD:
                
                self._times_manager.UpdateTime( timestamp_data )
                
            elif action == HC.CONTENT_UPDATE_SET:
                
                self._times_manager.SetTime( timestamp_data )
                
            elif action == HC.CONTENT_UPDATE_DELETE:
                
                self._times_manager.ClearTime( timestamp_data )
                
            
        
    
    def ResetService( self, service_key ):
        
        self._times_manager.ClearImportedTime( service_key )
        self._times_manager.ClearDeletedTime( service_key )
        self._times_manager.ClearPreviouslyImportedTime( service_key )
        
        self._current.discard( service_key )
        self._deleted.discard( service_key )
        self._pending.discard( service_key )
        self._petitioned.discard( service_key )
        
    
class NotesManager( object ):
    
    def __init__( self, names_to_notes: dict[ str, str ] ):
        
        self._names_to_notes = names_to_notes
        
    
    def Duplicate( self ):
        
        return NotesManager( dict( self._names_to_notes ) )
        
    
    def GetNames( self ):
        
        names = sorted( self._names_to_notes.keys() )
        
        return names
        
    
    def GetNamesToNotes( self ):
        
        return dict( self._names_to_notes )
        
    
    def SetNamesToNotes( self, names_to_notes: dict[ str, str ] ):
        
        self._names_to_notes = names_to_notes
        
    
    def GetNote( self, name: str ):
        
        if name in self._names_to_notes:
            
            return self._names_to_notes[ name ]
            
        else:
            
            raise HydrusExceptions.DataMissing( 'Note "{}" does not exist!'.format( name ) )
            
        
    
    def GetNumNotes( self ):
        
        return len( self._names_to_notes )
        
    
    def HasNote( self, name: str ):
        
        return name in self._names_to_notes
        
    
    def ProcessContentUpdate( self, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_SET:
            
            ( hash, name, note ) = row
            
            if note == '':
                
                if name in self._names_to_notes:
                    
                    del self._names_to_notes[ name ]
                    
                
            else:
                
                self._names_to_notes[ name ] = note
                
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            ( hash, name ) = row
            
            if name in self._names_to_notes:
                
                del self._names_to_notes[ name ]
                
            
        
    
class RatingsManager( object ):
    
    def __init__( self, service_keys_to_ratings: dict[ bytes, int | float | None ] ):
        
        self._service_keys_to_ratings = service_keys_to_ratings
        
    
    def Duplicate( self ):
        
        return RatingsManager( dict( self._service_keys_to_ratings ) )
        
    
    def GetRating( self, service_key ):
        
        if service_key in self._service_keys_to_ratings:
            
            return self._service_keys_to_ratings[ service_key ]
            
        else:
            
            try:
                
                service_type = CG.client_controller.services_manager.GetServiceType( service_key )
                
            except HydrusExceptions.DataMissing:
                
                return None
                
            
            if service_type == HC.LOCAL_RATING_INCDEC:
                
                return 0
                
            else:
                
                return None
                
            
        
    
    def GetRatingForAPI( self, service_key ) -> int | bool | None:
        
        try:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
        except HydrusExceptions.DataMissing:
            
            return None
            
        
        service_type = service.GetServiceType()
        
        if service_key in self._service_keys_to_ratings:
            
            rating = self._service_keys_to_ratings[ service_key ]
            
            if rating is None:
                
                return None
                
            
            if service_type == HC.LOCAL_RATING_LIKE:
                
                return rating >= 0.5
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                return service.ConvertRatingToStars( rating )
                
            elif service_type == HC.LOCAL_RATING_INCDEC:
                
                return int( rating )
                
            
        else:
            
            if service_type == HC.LOCAL_RATING_INCDEC:
                
                return 0
                
            else:
                
                return None
                
            
        
    
    def GetStarRatingSlice( self, service_keys ):
        
        return frozenset( { self._service_keys_to_ratings[ service_key ] for service_key in service_keys if service_key in self._service_keys_to_ratings } )
        
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            ( rating, hashes ) = row
            
            if rating is None and service_key in self._service_keys_to_ratings:
                
                del self._service_keys_to_ratings[ service_key ]
                
            else:
                
                self._service_keys_to_ratings[ service_key ] = rating
                
            
        
    
    def ResetService( self, service_key ):
        
        if service_key in self._service_keys_to_ratings:
            
            del self._service_keys_to_ratings[ service_key ]
            
        
    

class TagsManager( object ):
    
    def __init__(
        self,
        service_keys_to_statuses_to_storage_tags: dict[ bytes, dict[ int, set[ str ] ] ],
        service_keys_to_statuses_to_display_tags: dict[ bytes, dict[ int, set[ str ] ] ]
        ):
        
        self._tag_display_types_to_service_keys_to_statuses_to_tags = {
            ClientTags.TAG_DISPLAY_STORAGE : service_keys_to_statuses_to_storage_tags,
            ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL : service_keys_to_statuses_to_display_tags
        }
        
        self._storage_cache_is_dirty = True
        self._display_cache_is_dirty = True
        self._single_media_cache_is_dirty = True
        self._selection_list_cache_is_dirty = True
        
        self._lock = threading.Lock()
        
    
    def _GetServiceKeysToStatusesToTags( self, tag_display_type ):
        
        # this gets called a lot, so we are hardcoding some gubbins to avoid too many method calls
        
        if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE and self._storage_cache_is_dirty:
            
            self._RecalcStorageCache()
            
        
        if tag_display_type == ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL and self._display_cache_is_dirty:
            
            self._RecalcDisplayCache()
            
        elif tag_display_type == ClientTags.TAG_DISPLAY_SELECTION_LIST and self._selection_list_cache_is_dirty:
            
            self._RecalcDisplayFilteredCache( ClientTags.TAG_DISPLAY_SELECTION_LIST )
            
        elif tag_display_type == ClientTags.TAG_DISPLAY_SINGLE_MEDIA and self._single_media_cache_is_dirty:
            
            self._RecalcDisplayFilteredCache( ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
            
        
        return self._tag_display_types_to_service_keys_to_statuses_to_tags[ tag_display_type ]
        
    
    def _RecalcStorageCache( self ):
        
        service_keys_to_statuses_to_tags = self._tag_display_types_to_service_keys_to_statuses_to_tags[ ClientTags.TAG_DISPLAY_STORAGE ]
        
        # just combined service merge calculation
        
        combined_statuses_to_tags = HydrusData.default_dict_set()
        
        for ( service_key, source_statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            for ( status, tags ) in source_statuses_to_tags.items():
                
                combined_statuses_to_tags[ status ].update( tags )
                
            
        
        service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_statuses_to_tags
        
        #
        
        self._storage_cache_is_dirty = False
        
    
    def _RecalcDisplayCache( self ):
        
        if self._storage_cache_is_dirty:
            
            self._RecalcStorageCache()
            
        
        # display tags don't have petitioned or deleted, so we just copy from storage
        
        source_service_keys_to_statuses_to_tags = self._tag_display_types_to_service_keys_to_statuses_to_tags[ ClientTags.TAG_DISPLAY_STORAGE ]
        
        destination_service_keys_to_statuses_to_tags = self._tag_display_types_to_service_keys_to_statuses_to_tags[ ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ]
        
        combined_statuses_to_tags = HydrusData.default_dict_set()
        
        for ( service_key, source_statuses_to_tags ) in source_service_keys_to_statuses_to_tags.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            destination_statuses_to_tags = destination_service_keys_to_statuses_to_tags[ service_key ]
            
            for status in ( HC.CONTENT_STATUS_DELETED, HC.CONTENT_STATUS_PETITIONED ):
                
                if status in destination_statuses_to_tags:
                    
                    del destination_statuses_to_tags[ status ]
                    
                
                if status in source_statuses_to_tags:
                    
                    destination_statuses_to_tags[ status ] = set( source_statuses_to_tags[ status ] )
                    
                
            
            for ( status, tags ) in destination_statuses_to_tags.items():
                
                combined_statuses_to_tags[ status ].update( tags )
                
            
        
        destination_service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_statuses_to_tags
        
        #
        
        self._display_cache_is_dirty = False
        
    
    def _RecalcDisplayFilteredCache( self, tag_display_type ):
        
        if self._display_cache_is_dirty:
            
            self._RecalcDisplayCache()
            
        
        # display filtering
        
        tag_display_manager = CG.client_controller.tag_display_manager
        
        source_service_keys_to_statuses_to_tags = self._tag_display_types_to_service_keys_to_statuses_to_tags[ ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ]
        
        destination_service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        combined_statuses_to_tags = HydrusData.default_dict_set()
        
        for ( service_key, source_statuses_to_tags ) in source_service_keys_to_statuses_to_tags.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            if tag_display_manager.FiltersTags( tag_display_type, service_key ):
                
                destination_statuses_to_tags = HydrusData.default_dict_set()
                
                for ( status, source_tags ) in source_statuses_to_tags.items():
                    
                    dest_tags = tag_display_manager.FilterTags( tag_display_type, service_key, source_tags )
                    
                    if len( source_tags ) != len( dest_tags ):
                        
                        if len( dest_tags ) > 0:
                            
                            destination_statuses_to_tags[ status ] = dest_tags
                            
                        
                    else:
                        
                        destination_statuses_to_tags[ status ] = source_tags
                        
                    
                
            else:
                
                destination_statuses_to_tags = source_statuses_to_tags
                
            
            destination_service_keys_to_statuses_to_tags[ service_key ] = destination_statuses_to_tags
            
            for ( status, tags ) in destination_statuses_to_tags.items():
                
                combined_statuses_to_tags[ status ].update( tags )
                
            
        
        destination_service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_statuses_to_tags
        
        self._tag_display_types_to_service_keys_to_statuses_to_tags[ tag_display_type ] = destination_service_keys_to_statuses_to_tags
        
        #
        
        if tag_display_type == ClientTags.TAG_DISPLAY_SELECTION_LIST:
            
            self._selection_list_cache_is_dirty = False
            
        elif tag_display_type == ClientTags.TAG_DISPLAY_SINGLE_MEDIA:
            
            self._single_media_cache_is_dirty = False
            
        
    
    def _SetDirty( self ):
        
        self._storage_cache_is_dirty = True
        self._display_cache_is_dirty = True
        self._single_media_cache_is_dirty = True
        self._selection_list_cache_is_dirty = True
        
    
    @staticmethod
    def MergeTagsManagers( tags_managers ):
        
        # we cheat here and just get display tags, since this is read only and storage exacts isn't super important
        
        def CurrentAndPendingFilter( items ):
            
            for ( service_key, statuses_to_tags ) in items:
                
                filtered = { status : tags for ( status, tags ) in list(statuses_to_tags.items()) if status in ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) }
                
                yield ( service_key, filtered )
                
            
        
        # [[( service_key, statuses_to_tags )]]
        s_k_s_t_t_tupled = ( CurrentAndPendingFilter( tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ).items() ) for tags_manager in tags_managers )
        
        # [(service_key, statuses_to_tags)]
        flattened_s_k_s_t_t = itertools.chain.from_iterable( s_k_s_t_t_tupled )
        
        # service_key : [ statuses_to_tags ]
        s_k_s_t_t_dict = HydrusData.BuildKeyToListDict( flattened_s_k_s_t_t )
        
        # now let's merge so we have service_key : statuses_to_tags
        
        merged_service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        for ( service_key, several_statuses_to_tags ) in list(s_k_s_t_t_dict.items()):
            
            # [[( status, tags )]]
            s_t_t_tupled = ( list(s_t_t.items()) for s_t_t in several_statuses_to_tags )
            
            # [( status, tags )]
            flattened_s_t_t = itertools.chain.from_iterable( s_t_t_tupled )
            
            statuses_to_tags = HydrusData.default_dict_set()
            
            for ( status, tags ) in flattened_s_t_t:
                
                statuses_to_tags[ status ].update( tags )
                
            
            merged_service_keys_to_statuses_to_tags[ service_key ] = statuses_to_tags
            
        
        return TagsManager( merged_service_keys_to_statuses_to_tags, merged_service_keys_to_statuses_to_tags )
        
    
    def DeletePending( self, service_key ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            if len( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] ) + len( statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ] ) > 0:
                
                statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] = set()
                statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ] = set()
                
                self._SetDirty()
                
            
        
    
    def Duplicate( self ):
        
        with self._lock:
            
            dupe_tags_manager = TagsManager( {}, {} )
            
            dupe_tag_display_types_to_service_keys_to_statuses_to_tags = dict()
            
            for ( tag_display_type, service_keys_to_statuses_to_tags ) in self._tag_display_types_to_service_keys_to_statuses_to_tags.items():
                
                dupe_service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
                
                for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                    
                    dupe_statuses_to_tags = HydrusData.default_dict_set()
                    
                    for ( status, tags ) in statuses_to_tags.items():
                        
                        dupe_statuses_to_tags[ status ] = set( tags )
                        
                    
                    dupe_service_keys_to_statuses_to_tags[ service_key ] = dupe_statuses_to_tags
                    
                
                dupe_tag_display_types_to_service_keys_to_statuses_to_tags[ tag_display_type ] = dupe_service_keys_to_statuses_to_tags
                
            
            dupe_tags_manager._tag_display_types_to_service_keys_to_statuses_to_tags = dupe_tag_display_types_to_service_keys_to_statuses_to_tags
            dupe_tags_manager._display_cache_is_dirty = self._display_cache_is_dirty
            
            return dupe_tags_manager
            
        
    
    def GetComparableNamespaceSlice( self, service_key: bytes, namespaces: collections.abc.Collection[ str ], tag_display_type: int ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            combined_tags = statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] )
            
            pairs = [ HydrusTags.SplitTag( tag ) for tag in combined_tags ]
            
            slice_tags = []
            
            for desired_namespace in namespaces:
                
                # yes this is correct, we want _comparable_ tag slice
                subtags = sorted( ( HydrusText.HumanTextSortKey( subtag ) for ( namespace, subtag ) in pairs if namespace == desired_namespace ) )
                
                slice_tags.append( tuple( subtags ) )
                
            
            return tuple( slice_tags )
            
        
    
    def GetCurrent( self, service_key, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            return set( statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ] )
            
        
    
    def GetCurrentAndPending( self, service_key, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            return statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] )
            
        
    
    def GetDeleted( self, service_key, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            return set( statuses_to_tags[ HC.CONTENT_STATUS_DELETED ] )
            
        
    
    def GetNamespaceSlice( self, service_key: bytes, namespaces: collections.abc.Collection[ str ], tag_display_type: int ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            combined_tags = statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] )
            
            namespaces_with_colons = [ '{}:'.format( namespace ) for namespace in namespaces ]
            
            tag_slice = frozenset( ( tag for tag in combined_tags if True in ( tag.startswith( namespace_with_colon ) for namespace_with_colon in namespaces_with_colons ) ) )
            
            return tag_slice
            
        
    
    def GetNumDeletedMappings( self, tag_context: ClientSearchTagContext.TagContext, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            return len( service_keys_to_statuses_to_tags[ tag_context.service_key ][ HC.CONTENT_STATUS_DELETED ] )
            
        
    
    def GetNumTags( self, tag_context: ClientSearchTagContext.TagContext, tag_display_type ):
        
        with self._lock:
            
            num_tags = 0
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ tag_context.service_key ]
            
            if tag_context.include_current_tags: num_tags += len( statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ] )
            if tag_context.include_pending_tags: num_tags += len( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] )
            
            return num_tags
            
        
    
    def GetPending( self, service_key, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            return set( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] )
            
        
    
    def GetPetitioned( self, service_key, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            return set( statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ] )
            
        
    
    def GetServiceKeysToStatusesToTags( self, tag_display_type ) -> dict[ bytes, dict[ int, set[ str ] ] ]:
        
        with self._lock:
            
            # until I figure out a read/write lock on media results, we are going to do a naive copy here. full dict comprehension, which I understand is more performative than copy.deepcopy
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            return { service_key : { status : tags.copy() for ( status, tags ) in statuses_to_tags.items() } for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items() }
            
        
    
    def GetStatusesToTags( self, service_key, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            if service_key in service_keys_to_statuses_to_tags:
                
                return service_keys_to_statuses_to_tags[ service_key ]
                
            else:
                
                return collections.defaultdict( set )
                
            
        
    
    def GetTags( self, service_key, tag_display_type, status ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            return set( statuses_to_tags[ status ] )
            
        
    
    def HasTag( self, tag, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            combined_statuses_to_tags = service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ]
            
            return tag in combined_statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ] or tag in combined_statuses_to_tags[ HC.CONTENT_STATUS_PENDING ]
            
        
    
    def HasAnyOfTheseTags( self, tags, tag_display_type ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( tag_display_type )
            
            combined_statuses_to_tags = service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ]
            
            return True in ( tag in combined_statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ] or tag in combined_statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] for tag in tags )
            
        
    
    def NewTagDisplayRules( self ):
        
        with self._lock:
            
            self._SetDirty()
            
        
    
    def ProcessContentUpdate( self, service_key, content_update: ClientContentUpdates.ContentUpdate ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            ( data_type, action, row ) = content_update.ToTuple()
            
            ( tag, hashes ) = row
            
            if action == HC.CONTENT_UPDATE_ADD:
                
                statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ].add( tag )
                
                statuses_to_tags[ HC.CONTENT_STATUS_DELETED ].discard( tag )
                statuses_to_tags[ HC.CONTENT_STATUS_PENDING ].discard( tag )
                
            elif action == HC.CONTENT_UPDATE_DELETE:
                
                statuses_to_tags[ HC.CONTENT_STATUS_DELETED ].add( tag )
                
                statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ].discard( tag )
                statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ].discard( tag )
                
            elif action == HC.CONTENT_UPDATE_PEND:
                
                if tag not in statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ] and tag not in statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    statuses_to_tags[ HC.CONTENT_STATUS_PENDING ].add( tag )
                    
                
            elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                
                statuses_to_tags[ HC.CONTENT_STATUS_PENDING ].discard( tag )
                
            elif action == HC.CONTENT_UPDATE_PETITION:
                
                if tag not in statuses_to_tags[ HC.CONTENT_STATUS_PENDING ]:
                    
                    statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ].add( tag )
                    
                
            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                
                statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ].discard( tag )
                
            elif action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                
                statuses_to_tags[ HC.CONTENT_STATUS_DELETED ].discard( tag )
                
            
            #
            
            # this does not need to do clever sibling collapse or parent gubbins, because in that case, the db forces tagsmanager refresh
            # so this is just handling things if the content update has no sibling/parent tags
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
            
            statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
            
            ( data_type, action, row ) = content_update.ToTuple()
            
            ( tag, hashes ) = row
            
            if action == HC.CONTENT_UPDATE_ADD:
                
                statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ].add( tag )
                
                statuses_to_tags[ HC.CONTENT_STATUS_DELETED ].discard( tag )
                statuses_to_tags[ HC.CONTENT_STATUS_PENDING ].discard( tag )
                
            elif action == HC.CONTENT_UPDATE_DELETE:
                
                statuses_to_tags[ HC.CONTENT_STATUS_DELETED ].add( tag )
                
                statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ].discard( tag )
                statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ].discard( tag )
                
            elif action == HC.CONTENT_UPDATE_PEND:
                
                if tag not in statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    statuses_to_tags[ HC.CONTENT_STATUS_PENDING ].add( tag )
                    
                
            elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                
                statuses_to_tags[ HC.CONTENT_STATUS_PENDING ].discard( tag )
                
            elif action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                
                statuses_to_tags[ HC.CONTENT_STATUS_DELETED ].discard( tag )
                
            
            #
            
            self._SetDirty()
            
        
    
    def ResetService( self, service_key ):
        
        with self._lock:
            
            service_keys_to_statuses_to_tags = self._GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
            
            if service_key in service_keys_to_statuses_to_tags:
                
                del service_keys_to_statuses_to_tags[ service_key ]
                
                self._SetDirty()
                
            
        
    
