import collections
import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult

def CanDisplayMedia( media: "Media | None" ) -> bool:
    
    if media is None:
        
        return False
        
    
    media_result = media.GetDisplayMediaResult()
    
    if media_result is None:
        
        return False
        
    
    return CanDisplayMediaResult( media_result )
    

def CanDisplayMediaResult( media_result: ClientMediaResult.MediaResult ) -> bool:
    
    if media_result is None:
        
        return False
        
    
    locations_manager = media_result.GetLocationsManager()
    
    if not locations_manager.IsLocal():
        
        return False
        
    
    # note width/height is None for audio etc.., so it isn't immediately disqualifying
    
    ( width, height ) = media_result.GetResolution()
    
    if width == 0 or height == 0: # we cannot display this gonked out svg
        
        return False
        
    
    if media_result.IsStaticImage() and not media_result.HasUsefulResolution():
        
        return False
        
    
    return True
    

def GetLocalFileServiceKeys( flat_medias: collections.abc.Collection[ "Media" ] ):
    
    local_media_file_service_keys = set( CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ) )
    
    local_file_service_keys_counter = collections.Counter()
    
    for m in flat_medias:
        
        locations_manager = m.GetLocationsManager()
        
        local_file_service_keys_counter.update( local_media_file_service_keys.intersection( locations_manager.GetCurrent() ) )
        
    
    return local_file_service_keys_counter
    

def GetMediasTags( pool, tag_service_key, tag_display_type, content_statuses ):
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection():
            
            tags_managers.extend( media.GetSingletonsTagsManagers() )
            
        else:
            
            tags_managers.append( media.GetTagsManager() )
            
        
    
    tags = set()
    
    for tags_manager in tags_managers:
        
        statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, tag_display_type )
        
        for content_status in content_statuses:
            
            tags.update( statuses_to_tags[ content_status ] )
            
        
    
    return tags
    

def GetMediaResultsTagCount( media_results, tag_service_key, tag_display_type ):
    
    tags_managers = [ media_result.GetTagsManager() for media_result in media_results ]
    
    return GetTagsManagersTagCount( tags_managers, tag_service_key, tag_display_type )
    

def GetMediasFiletypeSummaryString( medias: collections.abc.Collection[ "Media" ] ):
    
        def GetDescriptor( plural, classes, num_collections ):
            
            suffix = 's' if plural else ''
            
            if len( classes ) == 0:
                
                return 'file' + suffix
                
            
            if len( classes ) == 1:
                
                ( mime, ) = classes
                
                if mime == HC.APPLICATION_HYDRUS_CLIENT_COLLECTION:
                    
                    collections_suffix = 's' if num_collections > 1 else ''
                    
                    return 'file{} in {} collection{}'.format( suffix, HydrusNumbers.ToHumanInt( num_collections ), collections_suffix )
                    
                else:
                    
                    return HC.mime_string_lookup[ mime ] + suffix
                    
                
            
            if len( classes.difference( HC.IMAGES ) ) == 0:
                
                return 'image' + suffix
                
            elif len( classes.difference( HC.ANIMATIONS ) ) == 0:
                
                return 'animation' + suffix
                
            elif len( classes.difference( HC.VIDEO ) ) == 0:
                
                return 'video' + suffix
                
            elif len( classes.difference( HC.AUDIO ) ) == 0:
                
                return 'audio file' + suffix
                
            else:
                
                return 'file' + suffix
                
            
        
        num_files = sum( [ media.GetNumFiles() for media in medias ] )
        
        if num_files > 100000:
            
            filetype_summary = 'files'
            
        else:
            
            mimes = { media.GetMime() for media in medias }
            
            if HC.APPLICATION_HYDRUS_CLIENT_COLLECTION in mimes:
                
                num_collections = len( [ media for media in medias if media.IsCollection() ] )
                
            else:
                
                num_collections = 0
                
            
            plural = len( medias ) > 1 or sum( ( m.GetNumFiles() for m in medias ) ) > 1
            
            filetype_summary = GetDescriptor( plural, mimes, num_collections )
            
        
        return f'{HydrusNumbers.ToHumanInt( num_files )} {filetype_summary}'
        

def GetMediasTagCount( pool, tag_service_key, tag_display_type ):
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection():
            
            tags_managers.extend( media.GetSingletonsTagsManagers() )
            
        else:
            
            tags_managers.append( media.GetTagsManager() )
            
        
    
    return GetTagsManagersTagCount( tags_managers, tag_service_key, tag_display_type )
    

def GetShowAction( media_result: ClientMediaResult.MediaResult, canvas_type: int ):
    
    start_paused = False
    start_with_embed = False
    
    bad_result = ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, start_paused, start_with_embed )
    
    if media_result is None:
        
        return bad_result
        
    
    mime = media_result.GetMime()
    
    if mime not in HC.ALLOWED_MIMES: # stopgap to catch a collection or application_unknown due to unusual import order/media moving
        
        return bad_result
        
    
    if canvas_type == CC.CANVAS_PREVIEW:
        
        action =  CG.client_controller.new_options.GetPreviewShowAction( mime )
        
    else:
        
        action = CG.client_controller.new_options.GetMediaShowAction( mime )
        
    
    return action
    

def GetTagsManagersTagCount( tags_managers, tag_service_key, tag_display_type ):
    
    current_tags_to_count = collections.Counter()
    deleted_tags_to_count = collections.Counter()
    pending_tags_to_count = collections.Counter()
    petitioned_tags_to_count = collections.Counter()
    
    for tags_manager in tags_managers:
        
        statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, tag_display_type )
        
        current_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ] )
        deleted_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_DELETED ] )
        pending_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] )
        petitioned_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ] )
        
    
    return ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
    

def UserWantsUsToDisplayMedia( media_result: ClientMediaResult.MediaResult, canvas_type: int ) -> bool:
    
    ( media_show_action, media_start_paused, media_start_with_embed ) = GetShowAction( media_result, canvas_type )
    
    if media_show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
        
        return False
        
    
    return True
    

class Media( object ):
    
    def __init__( self ):
        
        self._id = HydrusData.GenerateKey()
        self._id_hash = self._id.__hash__()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Media ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self._id_hash
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def GetDisplayMedia( self ) -> "Media":
        
        raise NotImplementedError()
        
    
    def GetDisplayMediaResult( self ) -> ClientMediaResult.MediaResult | None:
        
        raise NotImplementedError()
        
    
    def GetDurationMS( self ) -> int | None:
        
        raise NotImplementedError()
        
    
    def GetFlatMedia( self ) -> "list[ Media ]":
        
        raise NotImplementedError()
        
    
    def GetFileViewingStatsManager( self ) -> ClientMediaManagers.FileViewingStatsManager:
        
        raise NotImplementedError()
        
    
    def GetHash( self ) -> bytes:
        
        raise NotImplementedError()
        
    
    def GetHashes( self, is_in_file_service_key = None, discriminant = None, is_not_in_file_service_key = None, ordered = False ):
        
        raise NotImplementedError()
        
    
    def GetLocationsManager( self ) -> ClientMediaManagers.LocationsManager:
        
        raise NotImplementedError()
        
    
    def GetMime( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetNumFiles( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetNumFrames( self ) -> int | None:
        
        raise NotImplementedError()
        
    
    def GetNumInbox( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetNumWords( self ) -> int | None:
        
        raise NotImplementedError()
        
    
    def GetRatingsManager( self ) -> ClientMediaManagers.RatingsManager:
        
        raise NotImplementedError()
        
    
    def GetResolution( self ) -> tuple[ int, int ]:
        
        raise NotImplementedError()
        
    
    def GetSize( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetTagsManager( self ) -> ClientMediaManagers.TagsManager:
        
        raise NotImplementedError()
        
    
    def HasAnyOfTheseHashes( self, hashes ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasArchive( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasAudio( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasDuration( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasSimulatedDuration( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasStaticImages( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasInbox( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasNotes( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasUsefulResolution( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsCollection( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsImage( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsSizeDefinite( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsStaticImage( self ):
        
        raise NotImplementedError()
        
    
