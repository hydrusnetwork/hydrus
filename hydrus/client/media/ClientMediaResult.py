from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client.media import ClientMediaManagers

class MediaResult( object ):
    
    def __init__(
        self,
        file_info_manager: ClientMediaManagers.FileInfoManager,
        tags_manager: ClientMediaManagers.TagsManager,
        times_manager: ClientMediaManagers.TimesManager,
        locations_manager: ClientMediaManagers.LocationsManager,
        ratings_manager: ClientMediaManagers.RatingsManager,
        notes_manager: ClientMediaManagers.NotesManager,
        file_viewing_stats_manager: ClientMediaManagers.FileViewingStatsManager
    ):
        
        self._file_info_manager = file_info_manager
        self._tags_manager = tags_manager
        self._times_manager = times_manager
        self._locations_manager = locations_manager
        self._ratings_manager = ratings_manager
        self._notes_manager = notes_manager
        self._file_viewing_stats_manager = file_viewing_stats_manager
        
    
    def DeletePending( self, service_key: bytes ):
        
        try:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
        except HydrusExceptions.DataMissing:
            
            return
            
        
        service_type = service.GetServiceType()
        
        if service_type in HC.REAL_TAG_SERVICES:
            
            self._tags_manager.DeletePending( service_key )
            
        elif service_type in HC.REAL_FILE_SERVICES:
            
            self._locations_manager.DeletePending( service_key )
            
        
    
    def Duplicate( self ):
        
        file_info_manager = self._file_info_manager.Duplicate()
        tags_manager = self._tags_manager.Duplicate()
        times_manager = self._times_manager.Duplicate()
        locations_manager = self._locations_manager.Duplicate( times_manager )
        ratings_manager = self._ratings_manager.Duplicate()
        notes_manager = self._notes_manager.Duplicate()
        file_viewing_stats_manager = self._file_viewing_stats_manager.Duplicate( times_manager )
        
        return MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
    
    def GetDurationS( self ):
        
        return HydrusTime.SecondiseMSFloat( self._file_info_manager.duration_ms )
        
    
    def GetDurationMS( self ):
        
        return self._file_info_manager.duration_ms
        
    
    def GetFileInfoManager( self ):
        
        return self._file_info_manager
        
    
    def GetFileViewingStatsManager( self ) -> ClientMediaManagers.FileViewingStatsManager:
        
        return self._file_viewing_stats_manager
        
    
    def GetHash( self ):
        
        return self._file_info_manager.hash
        
    
    def GetHashId( self ):
        
        return self._file_info_manager.hash_id
        
    
    def GetInbox( self ):
        
        return self._locations_manager.inbox
        
    
    def GetLocationsManager( self ):
        
        return self._locations_manager
        
    
    def GetMediaResult( self ):
        
        return self
        
    
    def GetMime( self ):
        
        return self._file_info_manager.mime
        
    
    def GetNotesManager( self ) -> ClientMediaManagers.NotesManager:
        
        return self._notes_manager
        
    
    def GetNumFrames( self ):
        
        return self._file_info_manager.num_frames
        
    
    def GetNumWords( self ):
        
        return self._file_info_manager.num_words
        
    
    def GetRatingsManager( self ) -> ClientMediaManagers.RatingsManager:
        
        return self._ratings_manager
        
    
    def GetResolution( self ):
        
        return ( self._file_info_manager.width, self._file_info_manager.height )
        
    
    def GetSimulatedDurationMSAndSource( self ):
        
        if self._file_info_manager.mime == HC.ANIMATION_UGOIRA:
            
            num_frames = self._file_info_manager.num_frames
            
            if num_frames is not None and num_frames > 1:
                
                from hydrus.client import ClientUgoiraHandling
                
                if ClientUgoiraHandling.HasFrameTimesNote( self ):
                    
                    try:
                        
                        # this is more work than we'd normally want to do, but prettyinfolines is called on a per-file basis so I think we are good. a tiny no-latency json load per human click is fine
                        # we'll see how it goes
                        frame_durations_ms = ClientUgoiraHandling.GetFrameDurationsMSFromNote( self )
                        
                        if frame_durations_ms is not None:
                            
                            note_duration_ms = sum( frame_durations_ms )
                            
                            return ( note_duration_ms, 'note-based' )
                            
                        
                    except Exception as e:
                        
                        return ( 0, 'unknown note-based duration' )
                        
                    
                else:
                    
                    simulated_duration_ms = num_frames * ClientUgoiraHandling.UGOIRA_DEFAULT_FRAME_DURATION_MS
                    
                    return ( simulated_duration_ms, 'speculated' )
                    
                
            
        
        return ( 0, 'unknown simulated duration request' )
        
    
    def GetSize( self ):
        
        return self._file_info_manager.size
        
    
    def GetTagsManager( self ) -> ClientMediaManagers.TagsManager:
        
        return self._tags_manager
        
    
    def GetTimesManager( self ) -> ClientMediaManagers.TimesManager:
        
        return self._times_manager
        
    
    def HasAudio( self ):
        
        return self._file_info_manager.has_audio is True
        
    
    def HasDuration( self ):
        
        duration_ms = self._file_info_manager.duration_ms
        
        return duration_ms is not None and duration_ms > 0
        
    
    def HasSimulatedDuration( self ) -> bool:
        
        if not self.HasDuration():
            
            if self._file_info_manager.mime == HC.ANIMATION_UGOIRA:
                
                num_frames = self._file_info_manager.num_frames
                
                return num_frames is not None and num_frames > 1
                
            
        
        return False
        
    
    def HasNotes( self ):
        
        return self._notes_manager.GetNumNotes() > 0
        
    
    def HasUsefulResolution( self ):
        
        ( width, height ) = self.GetResolution()
        
        return width is not None and height is not None and width > 0 and height > 0
        
    
    def IsPhysicalDeleteLocked( self ):
        
        # TODO: ultimately replace this with metadata conditionals for whatever the user likes, 'don't delete anything rated 5 stars', whatever
        
        delete_lock_for_archived_files = CG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' )
        
        if delete_lock_for_archived_files:
            
            if self._locations_manager.IsLocal() and not self.GetInbox():
                
                return True
                
            
        
        return False
        
    
    def IsStaticImage( self ):
        
        if self._file_info_manager.mime in HC.IMAGES:
            
            return True
            
        elif self._file_info_manager.mime in HC.VIEWABLE_IMAGE_PROJECT_FILES:
            
            return True
            
        
        return False
        
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        try:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
        except HydrusExceptions.DataMissing:
            
            return
            
        
        service_type = service.GetServiceType()
        
        if service_type in HC.REAL_TAG_SERVICES:
            
            self._tags_manager.ProcessContentUpdate( service_key, content_update )
            
        elif service_type in HC.REAL_FILE_SERVICES:
            
            if content_update.GetDataType() == HC.CONTENT_TYPE_FILE_VIEWING_STATS:
                
                self._file_viewing_stats_manager.ProcessContentUpdate( content_update )
                
            else:
                
                self._locations_manager.ProcessContentUpdate( service_key, content_update )
                
            
        elif service_type in HC.RATINGS_SERVICES:
            
            self._ratings_manager.ProcessContentUpdate( service_key, content_update )
            
        elif service_type == HC.LOCAL_NOTES:
            
            self._notes_manager.ProcessContentUpdate( content_update )
            
        
    
    def ResetService( self, service_key ):
        
        self._tags_manager.ResetService( service_key )
        self._locations_manager.ResetService( service_key )
        
    
    def SetFileInfoManager( self, file_info_manager ):
        
        self._file_info_manager = file_info_manager
        
    
    def SetTagsManager( self, tags_manager ):
        
        self._tags_manager = tags_manager
        
    
    def ToTuple( self ):
        
        return ( self._file_info_manager, self._tags_manager, self._locations_manager, self._ratings_manager )
        
    
