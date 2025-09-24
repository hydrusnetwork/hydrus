import collections
import collections.abc
import random
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core.files.images import HydrusBlurhash

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientServices
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchTagContext

def CanDisplayMedia( media: "MediaSingleton" ) -> bool:
    
    if media is None:
        
        return False
        
    
    media = media.GetDisplayMedia()
    
    if media is None:
        
        return False
        
    
    locations_manager = media.GetLocationsManager()
    
    if not locations_manager.IsLocal():
        
        return False
        
    
    # note width/height is None for audio etc.., so it isn't immediately disqualifying
    
    ( width, height ) = media.GetResolution()
    
    if width == 0 or height == 0: # we cannot display this gonked out svg
        
        return False
        
    
    if media.IsStaticImage() and not media.HasUsefulResolution():
        
        return False
        
    
    return True
    

def FlattenMedia( medias ) -> list[ "MediaSingleton" ]:
    
    flat_media = []
    
    for media in medias:
        
        if media.IsCollection():
            
            flat_media.extend( media.GetFlatMedia() )
            
        else:
            
            flat_media.append( media )
            
        
    
    return flat_media
    

sort_data_to_blurhash_to_sortable_calls = {
    CC.SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS : HydrusBlurhash.ConvertBlurhashToSortableLightness,
    CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE : HydrusBlurhash.ConvertBlurhashToSortableChromaticMagnitude,
    CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED : HydrusBlurhash.ConvertBlurhashToSortableGreenRed,
    CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW : HydrusBlurhash.ConvertBlurhashToSortableBlueYellow,
    CC.SORT_FILES_BY_AVERAGE_COLOUR_HUE : HydrusBlurhash.ConvertBlurhashToSortableHue
}

def GetBlurhashToSortableCall( sort_data: int ):
    
    return sort_data_to_blurhash_to_sortable_calls.get( sort_data, HydrusBlurhash.ConvertBlurhashToSortableLightness )
    

def GetLocalFileServiceKeys( flat_medias: collections.abc.Collection[ "MediaSingleton" ] ):
    
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
                
                num_collections = len( [ media for media in medias if isinstance( media, MediaCollection ) ] )
                
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
        
    
    def GetDisplayMedia( self ) -> 'MediaSingleton':
        
        raise NotImplementedError()
        
    
    def GetDurationMS( self ) -> typing.Optional[ int ]:
        
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
        
    
    def GetNumFrames( self ) -> typing.Optional[ int ]:
        
        raise NotImplementedError()
        
    
    def GetNumInbox( self ) -> int:
        
        raise NotImplementedError()
        
    
    def GetNumWords( self ) -> typing.Optional[ int ]:
        
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
        
    
    def HasStaticImages( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasInbox( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def HasNotes( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsCollection( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsImage( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsSizeDefinite( self ) -> bool:
        
        raise NotImplementedError()
        
    

class MediaCollect( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_COLLECT
    SERIALISABLE_NAME = 'Media Collect'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, namespaces = None, rating_service_keys = None, collect_unmatched = None, tag_context = None ):
        
        if namespaces is None:
            
            namespaces = []
            
        
        if rating_service_keys is None:
            
            rating_service_keys = []
            
        
        if collect_unmatched is None:
            
            collect_unmatched = True
            
        
        if tag_context is None:
            
            tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
        
        self.namespaces = namespaces
        self.rating_service_keys = rating_service_keys
        self.collect_unmatched = collect_unmatched
        self.tag_context = tag_context
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_rating_service_keys = [ key.hex() for key in self.rating_service_keys ]
        
        serialisable_tag_context = self.tag_context.GetSerialisableTuple()
        
        return ( self.namespaces, serialisable_rating_service_keys, self.collect_unmatched, serialisable_tag_context )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.namespaces, serialisable_rating_service_keys, self.collect_unmatched, serialisable_tag_context ) = serialisable_info
        
        self.rating_service_keys = [ bytes.fromhex( serialisable_key ) for serialisable_key in serialisable_rating_service_keys ]
        
        self.tag_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_context )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( namespaces, serialisable_rating_service_keys, collect_unmatched ) = old_serialisable_info
            
            tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
            serialisable_tag_context = tag_context.GetSerialisableTuple()
            
            new_serialisable_info = ( namespaces, serialisable_rating_service_keys, collect_unmatched, serialisable_tag_context )
            
            return ( 2, new_serialisable_info )
            
        
    
    def DoesACollect( self ):
        
        return len( self.namespaces ) > 0 or len( self.rating_service_keys ) > 0
        
    
    def ToString( self ):
        
        s_list = list( self.namespaces )
        s_list.extend( [ CG.client_controller.services_manager.GetName( service_key ) for service_key in self.rating_service_keys if CG.client_controller.services_manager.ServiceExists( service_key ) ] )
        
        if len( s_list ) == 0:
            
            return 'no collections'
            
        else:
            
            return ', '.join( s_list )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_COLLECT ] = MediaCollect

class MediaList( object ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, media_results, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
        hashes_seen = set()
        
        media_results_dedupe = []
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            if hash in hashes_seen:
                
                continue
                
            
            media_results_dedupe.append( media_result )
            hashes_seen.add( hash )
            
        
        media_results = media_results_dedupe
        
        self._location_context = location_context
        self._tag_context = ClientSearchTagContext.TagContext()
        
        self._hashes = set()
        self._hashes_ordered = []
        
        self._hashes_to_singleton_media = {}
        self._hashes_to_collected_media = {}
        
        self._media_sort = MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        self._secondary_media_sort = None
        self._media_collect = MediaCollect()
        
        self._sorted_media = HydrusLists.FastIndexUniqueList( [ self._GenerateMediaSingleton( media_result ) for media_result in media_results ] )
        self._selected_media = set()
        
        self._singleton_media = set( self._sorted_media )
        self._collected_media = set()
        
        self._media_index_history = []
        
        self._RecalcHashes()
        
    
    def __len__( self ):
        
        return len( self._singleton_media ) + sum( map( len, self._collected_media ) )
        
    
    def _CalculateCollectionKeysToMedias( self, media_collect: MediaCollect, medias ):
        
        keys_to_medias = collections.defaultdict( list )
        
        namespaces_to_collect_by = list( media_collect.namespaces )
        ratings_to_collect_by = list( media_collect.rating_service_keys )
        tag_context = media_collect.tag_context
        
        for media in medias:
            
            if len( namespaces_to_collect_by ) > 0:
                
                namespace_key = media.GetTagsManager().GetNamespaceSlice( tag_context.service_key, namespaces_to_collect_by, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                
            else:
                
                namespace_key = frozenset()
                
            
            if len( ratings_to_collect_by ) > 0:
                
                rating_key = media.GetRatingsManager().GetStarRatingSlice( ratings_to_collect_by )
                
            else:
                
                rating_key = frozenset()
                
            
            keys_to_medias[ ( namespace_key, rating_key ) ].append( media )
            
        
        return keys_to_medias
        
    
    def _GenerateMediaCollection( self, media_results ):
        
        return MediaCollection( self._location_context, media_results )
        
    
    def _GenerateMediaSingleton( self, media_result ):
        
        return MediaSingleton( media_result )
        
    
    def _GetFirst( self ):
        
        if len( self._sorted_media ) > 0:
            
            return self._sorted_media[ 0 ]
            
        else:
            
            return None
            
        
    
    def _GetLast( self ):
        
        if len( self._sorted_media ) > 0:
            
            return self._sorted_media[ -1 ]
            
        else:
            
            return None
            
        
    
    def _GetMedia( self, hashes, discriminator = None ):
        
        if not isinstance( hashes, set ):
            
            hashes = set( hashes )
            
        
        if hashes.isdisjoint( self._hashes ):
            
            return []
            
        
        medias = []
        
        if discriminator is None or discriminator == 'singletons':
            
            medias.extend( ( self._hashes_to_singleton_media[ hash ] for hash in hashes if hash in self._hashes_to_singleton_media ) )
            
        
        if discriminator is None or discriminator == 'collections':
            
            medias.extend( { self._hashes_to_collected_media[ hash ] for hash in hashes if hash in self._hashes_to_collected_media } )
            
        
        return medias
        
    
    def _GetNext( self, media ):
        
        if media is None:
            
            return None
            
        
        next_index = self._sorted_media.index( media ) + 1
        
        if next_index == len( self._sorted_media ):
            
            return self._GetFirst()
            
        else:
            
            return self._sorted_media[ next_index ]
            
        
    
    def _GetPrevious( self, media ):
        
        if media is None: return None
        
        previous_index = self._sorted_media.index( media ) - 1
        
        if previous_index == -1:
            
            return self._GetLast()
            
        else:
            
            return self._sorted_media[ previous_index ]
            
        
    
    def _GetRandom( self, media ):
        
        if len( self._sorted_media ) == 0 or media is None:
            
            return None
            
        
        if len( self._sorted_media ) == 1:
            
            return media
            
        
        curr_index = self._sorted_media.index( media )
        
        self._media_index_history.append( curr_index )
        
        while True:
            
            random_index = random.randrange( len( self._sorted_media ) )
            
            if random_index != curr_index:
                
                return self._sorted_media[ random_index ]
                
            
        
    
    def _UndoRandom( self, media ):
        
        if len ( self._media_index_history ) == 0:
            
            return media
            
        
        recent_index = self._media_index_history.pop()
        
        return self._sorted_media[ recent_index ]
        
    
    def _HasHashes( self, hashes ):
        
        for hash in hashes:
            
            if hash in self._hashes:
                
                return True
                
            
        
        return False
        
    
    def _RecalcAfterContentUpdates( self, content_update_package ):
        
        pass
        
    
    def _RecalcAfterMediaRemove( self ):
        
        self._RecalcHashes()
        
    
    def _RecalcHashes( self ):
        
        self._hashes = set()
        self._hashes_ordered = []
        
        self._hashes_to_singleton_media = {}
        self._hashes_to_collected_media = {}
        
        for m in self._sorted_media:
            
            if isinstance( m, MediaCollection ):
                
                hashes = m.GetHashes( ordered = True )
                
                self._hashes.update( hashes )
                self._hashes_ordered.extend( hashes )
                
                for hash in hashes:
                    
                    self._hashes_to_collected_media[ hash ] = m
                    
                
            else:
                
                hash = m.GetHash()
                
                self._hashes.add( hash )
                self._hashes_ordered.append( hash )
                
                self._hashes_to_singleton_media[ hash ] = m
                
            
        
        self._media_index_history = []
        
    
    def _RemoveMediaByHashes( self, hashes ):
        
        if not isinstance( hashes, set ):
            
            hashes = set( hashes )
            
        
        affected_singleton_media = self._GetMedia( hashes, discriminator = 'singletons' )
        
        for media in self._collected_media:
            
            media._RemoveMediaByHashes( hashes )
            
        
        affected_collected_media = [ media for media in self._collected_media if media.HasNoMedia() ]
        
        self._RemoveMediaDirectly( affected_singleton_media, affected_collected_media )
        
    
    def _RemoveMediaDirectly( self, singleton_media, collected_media ):
        
        if not isinstance( singleton_media, set ):
            
            singleton_media = set( singleton_media )
            
        
        if not isinstance( collected_media, set ):
            
            collected_media = set( collected_media )
            
        
        self._singleton_media.difference_update( singleton_media )
        self._collected_media.difference_update( collected_media )
        
        self._selected_media.difference_update( singleton_media )
        self._selected_media.difference_update( collected_media )
        
        self._sorted_media.remove_items( singleton_media.union( collected_media ) )
        
        self._RecalcAfterMediaRemove()
        
    
    def AddMedia( self, new_media ):
        
        new_media = FlattenMedia( new_media )
        
        addable_media = []
        
        for media in new_media:
            
            hash = media.GetHash()
            
            if hash in self._hashes:
                
                continue
                
            
            addable_media.append( media )
            
            self._hashes.add( hash )
            self._hashes_ordered.append( hash )
            
            self._hashes_to_singleton_media[ hash ] = media
            
        
        self._singleton_media.update( addable_media )
        self._sorted_media.extend( addable_media )
        
        return new_media
        
    
    def AddMediaResults( self, media_results ):
        
        new_media = []
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            if hash in self._hashes:
                
                continue
                
            
            new_media.append( self._GenerateMediaSingleton( media_result ) )
            
        
        self.AddMedia( new_media )
        
        return new_media
        
    
    def Clear( self ):
        
        self._singleton_media = set()
        self._collected_media = set()
        
        self._selected_media = set()
        self._sorted_media = HydrusLists.FastIndexUniqueList()
        
        self._RecalcAfterMediaRemove()
        
    
    def Collect( self, media_collect = None ):
        
        if media_collect is None:
            
            media_collect = self._media_collect
            
        
        self._media_collect = media_collect
        
        flat_media = list( self._singleton_media )
        
        for media in self._collected_media:
            
            flat_media.extend( [ self._GenerateMediaSingleton( media_result ) for media_result in media.GetMediaResults() ] )
            
        
        if self._media_collect.DoesACollect():
            
            keys_to_medias = self._CalculateCollectionKeysToMedias( media_collect, flat_media )
            
            # add an option here I think, to media_collect to say if collections with one item should be singletons or not
            
            self._singleton_media = set()#{ medias[0] for ( key, medias ) in keys_to_medias.items() if len( medias ) == 1 }
            
            if not self._media_collect.collect_unmatched:
                
                unmatched_key = ( frozenset(), frozenset() )
                
                if unmatched_key in keys_to_medias:
                    
                    unmatched_medias = keys_to_medias[ unmatched_key ]
                    
                    self._singleton_media.update( unmatched_medias )
                    
                    del keys_to_medias[ unmatched_key ]
                    
                
            
            self._collected_media = { self._GenerateMediaCollection( [ media.GetMediaResult() for media in medias ] ) for ( key, medias ) in keys_to_medias.items() }# if len( medias ) > 1 }
            
        else:
            
            self._singleton_media = set( flat_media )
            
            self._collected_media = set()
            
        
        self._sorted_media = HydrusLists.FastIndexUniqueList( list( self._singleton_media ) + list( self._collected_media ) )
        
        self._RecalcHashes()
        
    
    def DeletePending( self, service_key ):
        
        for media in self._collected_media:
            
            media.DeletePending( service_key )
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        d = {}
        
        d[ 'num_files' ] = self.GetNumFiles()
        
        flat_media = self.GetFlatMedia()
        
        d[ 'hash_ids' ] = [ m.GetMediaResult().GetHashId() for m in flat_media ]
        
        if not simple:
            
            hashes = self.GetHashes( ordered = True )
            
            d[ 'hashes' ] = [ hash.hex() for hash in hashes ]
            
        
        return d
        
    
    def GetFirst( self ):
        
        return self._GetFirst()
        
    
    def GetFlatMedia( self ):
        
        flat_media = []
        
        for media in self._sorted_media:
            
            if media.IsCollection():
                
                flat_media.extend( media.GetFlatMedia() )
                
            else:
                
                flat_media.append( media )
                
            
        
        return flat_media
        
    
    def GetHashes( self, is_in_file_service_key = None, discriminant = None, is_not_in_file_service_key = None, ordered = False ):
        
        if is_in_file_service_key is None and discriminant is None and is_not_in_file_service_key is None:
            
            if ordered:
                
                return self._hashes_ordered
                
            else:
                
                return self._hashes
                
            
        else:
            
            if ordered:
                
                result = []
                
                for media in self._sorted_media:
                    
                    result.extend( media.GetHashes( is_in_file_service_key, discriminant, is_not_in_file_service_key, ordered ) )
                    
                
            else:
                
                result = set()
                
                for media in self._sorted_media:
                    
                    result.update( media.GetHashes( is_in_file_service_key, discriminant, is_not_in_file_service_key, ordered ) )
                    
                
            
            return result
            
        
    
    def GetLast( self ):
        
        return self._GetLast()
        
    
    def GetMediaByHashes( self, hashes ):
        
        return self._GetMedia( hashes )
        
    
    def GetMediaResults( self, is_in_file_service_key = None, discriminant = None, selected_media = None, unrated = None, for_media_viewer = False ) -> list[ ClientMediaResult.MediaResult ]:
        
        media_results = []
        
        for media in self._sorted_media:
            
            if is_in_file_service_key is not None:
                
                locations_manager = media.GetLocationsManager()
                
                if is_in_file_service_key not in locations_manager.GetCurrent():
                    
                    continue
                    
                
            
            if selected_media is not None and media not in selected_media:
                
                continue
                
            
            if media.IsCollection():
                
                # don't include selected_media here as it is not valid at the deeper collection level
                
                media_results.extend( media.GetMediaResults( is_in_file_service_key = is_in_file_service_key, discriminant = discriminant, unrated = unrated, for_media_viewer = True ) )
                
            else:
                
                if discriminant is not None:
                    
                    locations_manager = media.GetLocationsManager()
                    
                    if discriminant == CC.DISCRIMINANT_INBOX:
                        
                        p = media.HasInbox()
                        
                    elif discriminant == CC.DISCRIMINANT_ARCHIVE:
                        
                        p = not media.HasInbox()
                        
                    elif discriminant == CC.DISCRIMINANT_LOCAL:
                        
                        p = locations_manager.IsLocal()
                        
                    elif discriminant == CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH:
                        
                        p = locations_manager.IsLocal() and not locations_manager.IsTrashed()
                        
                    elif discriminant == CC.DISCRIMINANT_NOT_LOCAL:
                        
                        p = not locations_manager.IsLocal()
                        
                    elif discriminant == CC.DISCRIMINANT_DOWNLOADING:
                        
                        p = locations_manager.IsDownloading()
                        
                    
                    if not p:
                        
                        continue
                        
                    
                
                if unrated is not None:
                    
                    ratings_manager = media.GetRatingsManager()
                    
                    if ratings_manager.GetRating( unrated ) is not None:
                        
                        continue
                        
                    
                
                if for_media_viewer:
                    
                    if not UserWantsUsToDisplayMedia( media.GetMediaResult(), CC.CANVAS_MEDIA_VIEWER ) or not CanDisplayMedia( media ):
                        
                        continue
                        
                    
                
                media_results.append( media.GetMediaResult() )
                
            
        
        return media_results
        
    
    def GetNext( self, media ) -> Media:
        
        return self._GetNext( media )
        
    
    def GetNumArchive( self ):
        
        num_archive = sum( ( 1 for m in self._singleton_media if not m.HasInbox() ) ) + sum( ( m.GetNumArchive() for m in self._collected_media ) )
        
        return num_archive
        
    
    def GetNumFiles( self ):
        
        return len( self._hashes )
        
    
    def GetNumInbox( self ):
        
        num_inbox = sum( ( 1 for m in self._singleton_media if m.HasInbox() ) ) + sum( ( m.GetNumInbox() for m in self._collected_media ) )
        
        return num_inbox
        
    
    def GetPrevious( self, media ):
        
        return self._GetPrevious( media )
        
    
    def GetRandom( self, media ):
        
        return self._GetRandom( media )
        
    
    def UndoRandom( self, media ):
        
        return self._UndoRandom( media )
        
    
    def GetSelectedMedia( self ):
        
        return self._selected_media
        
    
    def GetSortedMedia( self ):
        
        return self._sorted_media
        
    
    def HasAnyOfTheseHashes( self, hashes: set ):
        
        return not hashes.isdisjoint( self._hashes )
        
    
    def HasMedia( self, media ):
        
        if media is None:
            
            return False
            
        
        if media in self._singleton_media:
            
            return True
            
        elif media in self._collected_media:
            
            return True
            
        else:
            
            for media_collection in self._collected_media:
                
                if media_collection.HasMedia( media ):
                    
                    return True
                    
                
            
        
        return False
        
    
    def HasNoMedia( self ):
        
        return len( self._sorted_media ) == 0
        
    
    def IndexOf( self, media: Media ):
        
        return self._sorted_media.index( media )
        
    
    def MoveMedia( self, medias: list[ Media ], insertion_index: int ):
        
        self._sorted_media.move_items( medias, insertion_index )
        
        self._RecalcHashes()
        
    
    def ProcessContentUpdatePackage( self, full_content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if not full_content_update_package.HasContent():
            
            return
            
        
        content_update_package = full_content_update_package.FilterToHashes( self._hashes )
        
        if not content_update_package.HasContent():
            
            return
            
        
        for m in self._collected_media:
            
            m.ProcessContentUpdatePackage( content_update_package )
            
        
        check_for_empty_collections = False
        
        for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                hashes = content_update.GetHashes()
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action in ( HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_DELETE_FROM_SOURCE_AFTER_MIGRATE ):
                        
                        local_file_domains = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
                        all_local_file_services = set( list( local_file_domains ) + [ CC.COMBINED_LOCAL_FILE_SERVICE_KEY, CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY, CC.TRASH_SERVICE_KEY, CC.LOCAL_UPDATE_SERVICE_KEY ] )
                        
                        #
                        
                        physically_deleted = service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                        possibly_trashed = ( service_key in local_file_domains or service_key == CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) and action == HC.CONTENT_UPDATE_DELETE
                        
                        deleted_specifically_from_our_domain = self._location_context.IsOneDomain() and service_key in self._location_context.current_service_keys
                        deleted_implicitly_from_our_domain = set( self._location_context.current_service_keys ).issubset( local_file_domains ) and service_key == CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY
                        deleted_from_our_domain = deleted_specifically_from_our_domain or deleted_implicitly_from_our_domain
                        
                        we_are_looking_at_trash = self._location_context.IsOneDomain() and CC.TRASH_SERVICE_KEY in self._location_context.current_service_keys
                        our_view_is_all_local = self._location_context.IncludesCurrent() and not self._location_context.IncludesDeleted() and self._location_context.current_service_keys.issubset( all_local_file_services )
                        
                        # case one, disappeared from hard drive and we are looking at local files
                        physically_deleted_and_local_view = physically_deleted and our_view_is_all_local
                        
                        # case two, disappeared from repo hard drive while we are looking at it
                        deleted_from_repo_and_repo_view = service_key not in all_local_file_services and deleted_from_our_domain
                        
                        moved_from_this_domain_to_another = action == HC.CONTENT_UPDATE_DELETE_FROM_SOURCE_AFTER_MIGRATE and service_key in self._location_context.current_service_keys
                        
                        user_says_remove_and_possibly_trashed_from_non_trash_local_view = HC.options[ 'remove_trashed_files' ] and possibly_trashed and not we_are_looking_at_trash
                        
                        user_says_remove_and_moved_from_this_local_file_domain = CG.client_controller.new_options.GetBoolean( 'remove_local_domain_moved_files' ) and moved_from_this_domain_to_another
                        
                        if physically_deleted_and_local_view or user_says_remove_and_possibly_trashed_from_non_trash_local_view or deleted_from_repo_and_repo_view or user_says_remove_and_moved_from_this_local_file_domain:
                            
                            if user_says_remove_and_possibly_trashed_from_non_trash_local_view:
                                
                                actual_trash_hashes = self.GetHashes( is_in_file_service_key = CC.TRASH_SERVICE_KEY )
                                
                                hashes = set( hashes ).intersection( actual_trash_hashes )
                                
                            
                            if len( hashes ) > 0:
                                
                                self._RemoveMediaByHashes( hashes )
                                
                            else:
                                
                                check_for_empty_collections = True
                                
                            
                        
                    
                
            
        
        if check_for_empty_collections:
            
            # there are some situations with nested collected media that they have already emptied and the above actual trash hashes test no longer works and we have empty 'bubble' collections hanging around, so let's clear them now
            now_empty_collected_media = [ media for media in self._collected_media if media.HasNoMedia() ]
            
            if len( now_empty_collected_media ) > 0:
                
                self._RemoveMediaDirectly( set(), now_empty_collected_media )
                
            
        
        self._RecalcAfterContentUpdates( content_update_package )
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates: dict[ bytes, collections.abc.Collection[ ClientServices.ServiceUpdate ] ] ):
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action == HC.SERVICE_UPDATE_DELETE_PENDING:
                    
                    self.DeletePending( service_key )
                    
                elif action == HC.SERVICE_UPDATE_RESET:
                    
                    self.ResetService( service_key )
                    
                
            
        
    
    def RemoveMediaDirectly( self, singleton_media, collected_media ):
        
        self._RemoveMediaDirectly( singleton_media, collected_media )
        
    
    def ResetService( self, service_key ):
        
        if self._location_context.IsOneDomain() and service_key in self._location_context.current_service_keys:
            
            self._RemoveMediaDirectly( self._singleton_media, self._collected_media )
            
        else:
            
            for media in self._collected_media: media.ResetService( service_key )
            
        
    
    def SetTagContext( self, tag_context: ClientSearchTagContext.TagContext ):
        
        self._tag_context = tag_context
        
    
    def Sort( self, media_sort: typing.Optional[ "MediaSort" ] = None, secondary_sort: typing.Optional[ "MediaSort" ] = None ):
        
        # TODO: TBH, I think I should stop caching the last sort and just take params every time. that's KISS
        
        if media_sort is None:
            
            media_sort = self._media_sort
            
        
        if secondary_sort is None:
            
            if self._secondary_media_sort is None:
                
                secondary_sort = CG.client_controller.new_options.GetFallbackSort()
                
            else:
                
                secondary_sort = self._secondary_media_sort
                
            
        
        self._media_sort = media_sort
        self._secondary_media_sort = secondary_sort
        
        for media in self._collected_media:
            
            media.Sort( media_sort = media_sort, secondary_sort = secondary_sort )
            
        
        self._secondary_media_sort.Sort( self._location_context, self._tag_context, self._sorted_media )
        self._media_sort.Sort( self._location_context, self._tag_context, self._sorted_media )
        
        self._RecalcHashes()
        
    

class ListeningMediaList( MediaList ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, media_results, *args, **kwargs ):
        
        super().__init__( location_context, media_results, *args, **kwargs )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        CG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
    

class MediaCollection( MediaList, Media ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, media_results ):
        
        # note for later: ideal here is to stop this multiple inheritance mess and instead have this be a media that *has* a list, not *is* a list
        
        super().__init__( location_context, media_results )
        
        self._archive = True
        self._inbox = False
        
        self._size = 0
        self._size_definite = True
        
        self._width = None
        self._height = None
        self._duration = None
        self._num_frames = None
        self._num_words = None
        self._has_audio = None
        self._tags_manager = None
        self._locations_manager = None
        self._file_viewing_stats_manager = None
        
        self._internals_dirty = False
        
        self._RecalcInternals()
        
    
    def _RecalcAfterContentUpdates( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        archive_or_inbox = False
        
        data_types = set()
        
        for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
            
            for content_update in content_updates:
                
                data_type = content_update.GetDataType()
                
                if data_type in ( HC.CONTENT_TYPE_URLS, HC.CONTENT_TYPE_NOTES ):
                    
                    continue
                    
                elif data_type == HC.CONTENT_TYPE_FILES:
                    
                    action = content_update.GetAction()
                    
                    if action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_INBOX ):
                        
                        archive_or_inbox = True
                        
                        continue
                        
                    
                
                data_types.add( data_type )
                
            
        
        if archive_or_inbox and data_types.issubset( {
            HC.CONTENT_TYPE_RATINGS,
            HC.CONTENT_TYPE_FILE_VIEWING_STATS,
            HC.CONTENT_TYPE_MAPPINGS
        }):
            
            if archive_or_inbox:
                
                self._RecalcArchiveInbox()
                
            
            for data_type in data_types:
                
                if data_type == HC.CONTENT_TYPE_RATINGS:
                    
                    self._RecalcRatings()
                    
                elif data_type == HC.CONTENT_TYPE_FILE_VIEWING_STATS:
                    
                    self._RecalcFileViewingStats()
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    self._RecalcTags()
                    
                
            
        elif len( data_types ) > 0:
            
            self._RecalcInternals()
            
        
    
    def _RecalcAfterMediaRemove( self ):
        
        MediaList._RecalcAfterMediaRemove( self )
        
        self._RecalcArchiveInbox()
        
    
    def _RecalcArchiveInbox( self ):
        
        self._archive = True in ( media.HasArchive() for media in self._sorted_media )
        self._inbox = True in ( media.HasInbox() for media in self._sorted_media )
        
        if self._locations_manager is not None:
            
            all_locations_managers = [ media.GetLocationsManager() for media in self._sorted_media ]
            all_timestamp_managers = [ location_manager.GetTimesManager() for location_manager in all_locations_managers ]
            
            archived_timestamps_ms = { times_manager.GetArchivedTimestampMS() for times_manager in all_timestamp_managers }
            
            archived_timestamps_ms.discard( None )
            
            if len( archived_timestamps_ms ) > 0:
                
                self._locations_manager.GetTimesManager().SetArchivedTimestampMS( max( archived_timestamps_ms ) )
                
            else:
                
                self._locations_manager.GetTimesManager().ClearArchivedTime()
                
            
        
    
    def _RecalcFileViewingStats( self ):
        
        self._file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateCombinedManager( [ m.GetFileViewingStatsManager() for m in self._sorted_media ] )
        
    
    def _RecalcHashes( self ):
        
        MediaList._RecalcHashes( self )
        
        all_locations_managers = [ media.GetLocationsManager() for media in self._sorted_media ]
        all_timestamp_managers = [ location_manager.GetTimesManager() for location_manager in all_locations_managers ]
        
        current_to_timestamps_ms = {}
        deleted_to_timestamps_ms = {}
        deleted_to_previously_imported_timestamps_ms = {}
        
        for service_key in CG.client_controller.services_manager.GetServiceKeys( HC.REAL_FILE_SERVICES ):
            
            current_timestamps_ms = [ timestamp_ms for timestamp_ms in ( times_manager.GetImportedTimestampMS( service_key ) for times_manager in all_timestamp_managers ) if timestamp_ms is not None ]
            
            if len( current_timestamps_ms ) > 0:
                
                current_to_timestamps_ms[ service_key ] = max( current_timestamps_ms )
                
            
            deleted_timestamps_ms = [ timestamp_ms for timestamp_ms in ( times_manager.GetDeletedTimestampMS( service_key ) for times_manager in all_timestamp_managers ) if timestamp_ms is not None ]
            
            if len( deleted_timestamps_ms ) > 0:
                
                deleted_to_timestamps_ms[ service_key ] = max( deleted_timestamps_ms )
                
            
            previously_imported_timestamps_ms = [ timestamp_ms for timestamp_ms in ( times_manager.GetPreviouslyImportedTimestampMS( service_key ) for times_manager in all_timestamp_managers ) if timestamp_ms is not None ]
            
            if len( previously_imported_timestamps_ms ) > 0:
                
                deleted_to_previously_imported_timestamps_ms[ service_key ] = max( previously_imported_timestamps_ms )
                
            
        
        current = set( current_to_timestamps_ms.keys() )
        deleted = set( deleted_to_timestamps_ms.keys() )
        
        pending = HydrusLists.MassUnion( [ locations_manager.GetPending() for locations_manager in all_locations_managers ] )
        petitioned = HydrusLists.MassUnion( [ locations_manager.GetPetitioned() for locations_manager in all_locations_managers ] )
        
        times_manager = ClientMediaManagers.TimesManager()
        
        modified_timestamps_ms = { times_manager.GetAggregateModifiedTimestampMS() for times_manager in all_timestamp_managers }
        
        modified_timestamps_ms.discard( None )
        
        if len( modified_timestamps_ms ) > 0:
            
            times_manager.SetFileModifiedTimestampMS( max( modified_timestamps_ms ) )
            
        
        archived_timestamps_ms = { times_manager.GetArchivedTimestampMS() for times_manager in all_timestamp_managers }
        
        archived_timestamps_ms.discard( None )
        
        if len( archived_timestamps_ms ) > 0:
            
            times_manager.SetArchivedTimestampMS( max( archived_timestamps_ms ) )
            
        
        times_manager.SetImportedTimestampsMS( current_to_timestamps_ms )
        times_manager.SetDeletedTimestampsMS( deleted_to_timestamps_ms )
        times_manager.SetPreviouslyImportedTimestampsMS( deleted_to_previously_imported_timestamps_ms )
        
        self._locations_manager = ClientMediaManagers.LocationsManager( current, deleted, pending, petitioned, times_manager )
        
    
    def _RecalcInternals( self ):
        
        self._RecalcHashes()
        
        self._RecalcTags()
        
        self._RecalcArchiveInbox()
        
        self._size = sum( [ media.GetSize() for media in self._sorted_media ] )
        self._size_definite = False not in ( media.IsSizeDefinite() for media in self._sorted_media )
        
        duration_sum = sum( [ media.GetDurationMS() for media in self._sorted_media if media.HasDuration() ] )
        
        if duration_sum > 0: self._duration = duration_sum
        else: self._duration = None
        
        self._has_audio = True in ( media.HasAudio() for media in self._sorted_media )
        
        self._has_notes = True in ( media.HasNotes() for media in self._sorted_media )
        
        self._width = None
        self._height = None
        current_num_pixels_leader = 0
        
        for m in self._sorted_media:
            
            ( width, height ) = m.GetResolution()
            
            if width is not None and height is not None:
                
                num_pixels = width * height
                
                if num_pixels > current_num_pixels_leader:
                    
                    self._width = width
                    self._height = height
                    
                    current_num_pixels_leader = num_pixels
                    
                
            
        
        self._RecalcRatings()
        self._RecalcFileViewingStats()
        
    
    def _RecalcRatings( self ):
        
        # horrible compromise
        if len( self._sorted_media ) > 0:
            
            self._ratings_manager = self._sorted_media[0].GetRatingsManager()
            
        else:
            
            self._ratings_manager = ClientMediaManagers.RatingsManager( {} )
            
        
    
    def _RecalcTags( self ):
        
        tags_managers = [ m.GetTagsManager() for m in self._sorted_media ]
        
        self._tags_manager = ClientMediaManagers.TagsManager.MergeTagsManagers( tags_managers )
        
    
    def AddMedia( self, new_media ):
        
        MediaList.AddMedia( self, new_media )
        
        self._RecalcInternals()
        
    
    def DeletePending( self, service_key ):
        
        MediaList.DeletePending( self, service_key )
        
        self._RecalcInternals()
        
    
    def GetDisplayMedia( self ) -> typing.Optional[ "MediaSingleton" ]:
        
        first = self._GetFirst()
        
        if first is None:
            
            return None
            
        else:
            
            return first.GetDisplayMedia()
            
        
    
    def GetDurationMS( self ):
        
        return self._duration
        
    
    def GetEarliestHashId( self ):
        
        return min( ( m.GetEarliestHashId() for m in self._sorted_media ) )
        
    
    def GetFileViewingStatsManager( self ):
        
        return self._file_viewing_stats_manager
        
    
    def GetHash( self ):
        
        display_media = self.GetDisplayMedia()
        
        if display_media is None:
            
            return None
            
        else:
            
            return display_media.GetHash()
            
        
    
    def GetLocationsManager( self ): 
        
        return self._locations_manager
        
    
    def GetMime( self ):
        
        return HC.APPLICATION_HYDRUS_CLIENT_COLLECTION
        
    
    def GetNumInbox( self ):
        
        return sum( ( media.GetNumInbox() for media in self._sorted_media ) )
        
    
    def GetNumFrames( self ):
        
        num_frames = ( media.GetNumFrames() for media in self._sorted_media )
        
        return sum( ( nf for nf in num_frames if nf is not None ) )
        
    
    def GetNumWords( self ):
        
        num_words = ( media.GetNumWords() for media in self._sorted_media )
        
        return sum( ( nw for nw in num_words if nw is not None ) )
        
    
    def GetRatingsManager( self ):
        
        return self._ratings_manager
        
    
    def GetResolution( self ):
        
        if self._width is None:
            
            return ( 0, 0 )
            
        else:
            
            return ( self._width, self._height )
            
        
    
    def GetSingletonsTagsManagers( self ):
        
        tags_managers = [ m.GetTagsManager() for m in self._singleton_media ] 
        
        for m in self._collected_media: tags_managers.extend( m.GetSingletonsTagsManagers() )
        
        return tags_managers
        
    
    def GetSize( self ):
        
        return self._size
        
    
    def GetTagsManager( self ):
        
        return self._tags_manager
        
    
    def HasArchive( self ):
        
        return self._archive
        
    
    def HasAudio( self ):
        
        return self._has_audio
        
    
    def HasDuration( self ):
        
        return self._duration is not None
        
    
    def HasStaticImages( self ):
        
        return True in ( media.HasStaticImages() for media in self._sorted_media )
        
    
    def HasInbox( self ):
        
        return self._inbox
        
    
    def HasNotes( self ):
        
        return self._has_notes
        
    
    def IsCollection( self ):
        
        return True
        
    
    def HasUsefulResolution( self ):
        
        ( width, height ) = self.GetResolution()
        
        return width is not None and width != 0 and height is not None and height != 0
        
    
    def IsStaticImage( self ):
        
        return False
        
    
    def IsSizeDefinite( self ):
        
        return self._size_definite
        
    
    def RecalcInternals( self ):
        
        self._RecalcInternals()
        
    
    def ResetService( self, service_key ):
        
        MediaList.ResetService( self, service_key )
        
        self._RecalcInternals()
        
    

class MediaSingleton( Media ):
    
    def __init__( self, media_result: ClientMediaResult.MediaResult ):
        
        super().__init__()
        
        self._media_result = media_result
        
    
    def Duplicate( self ):
        
        return MediaSingleton( self._media_result.Duplicate() )
        
    
    def GetDisplayMedia( self ) -> 'MediaSingleton':
        
        return self
        
    
    def GetDurationMS( self ):
        
        return self._media_result.GetDurationMS()
        
    
    def GetEarliestHashId( self ):
        
        return self._media_result.GetFileInfoManager().hash_id
        
    
    def GetFileInfoManager( self ):
        
        return self._media_result.GetFileInfoManager()
        
    
    def GetFileViewingStatsManager( self ):
        
        return self._media_result.GetFileViewingStatsManager()
        
    
    def GetHash( self ):
        
        return self._media_result.GetHash()
        
    
    def GetHashId( self ):
        
        return self._media_result.GetHashId()
        
    
    def GetHashes( self, is_in_file_service_key = None, discriminant = None, is_not_in_file_service_key = None, ordered = False ):
        
        if self.MatchesDiscriminant( is_in_file_service_key = is_in_file_service_key, discriminant = discriminant, is_not_in_file_service_key = is_not_in_file_service_key ):
            
            if ordered:
                
                return [ self._media_result.GetHash() ]
                
            else:
                
                return { self._media_result.GetHash() }
                
            
        else:
            
            if ordered:
                
                return []
                
            else:
                
                return set()
                
            
        
    
    def GetLocationsManager( self ):
        
        return self._media_result.GetLocationsManager()
        
    
    def GetMediaResult( self ):
        
        return self._media_result
        
    
    def GetMime( self ):
        
        return self._media_result.GetMime()
        
    
    def GetNotesManager( self ) -> ClientMediaManagers.NotesManager:
        
        return self._media_result.GetNotesManager()
        
    
    def GetNumFiles( self ): return 1
    
    def GetNumFrames( self ): return self._media_result.GetNumFrames()
    
    def GetNumInbox( self ):
        
        if self.HasInbox(): return 1
        else: return 0
        
    
    def GetNumWords( self ): return self._media_result.GetNumWords()
    
    def GetRatingsManager( self ): return self._media_result.GetRatingsManager()
    
    def GetResolution( self ):
        
        return self._media_result.GetResolution()
        
    
    def GetSize( self ):
        
        size = self._media_result.GetSize()
        
        if size is None: return 0
        else: return size
        
    
    def GetTagsManager( self ):
        
        return self._media_result.GetTagsManager()
        
    
    def GetTimesManager( self ):
        
        return self._media_result.GetTimesManager()
        
    
    def GetTitleString( self ):
        
        new_options = CG.client_controller.new_options
        
        tag_summary_generator = new_options.GetTagSummaryGenerator( 'media_viewer_top' )
        
        tags = self.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
        
        if len( tags ) == 0:
            
            return ''
            
        
        summary = tag_summary_generator.GenerateSummary( tags )
        
        return summary
        
    
    def HasAnyOfTheseHashes( self, hashes ):
        
        return self._media_result.GetHash() in hashes
        
    
    def HasArchive( self ):
        
        return not self._media_result.GetInbox()
        
    
    def HasAudio( self ):
        
        return self._media_result.HasAudio()
        
    
    def IsPhysicalDeleteLocked( self ):
        
        return self._media_result.IsPhysicalDeleteLocked()
        
    
    def HasDuration( self ):
        
        return self._media_result.HasDuration()
        
    
    def HasStaticImages( self ):
        
        return self.IsStaticImage()
        
    
    def HasInbox( self ):
        
        return self._media_result.GetInbox()
        
    
    def HasNotes( self ):
        
        return self._media_result.HasNotes()
        
    
    def HasUsefulResolution( self ):
        
        return self._media_result.HasUsefulResolution()
        
    
    def IsCollection( self ):
        
        return False
        
    
    def IsSizeDefinite( self ):
        
        return self._media_result.GetSize() is not None
        
    
    def IsStaticImage( self ):
        
        return self._media_result.IsStaticImage()
        
    
    def MatchesDiscriminant( self, is_in_file_service_key = None, discriminant = None, is_not_in_file_service_key = None ):
        
        if discriminant is not None:
            
            inbox = self._media_result.GetInbox()
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if discriminant == CC.DISCRIMINANT_INBOX:
                
                p = inbox
                
            elif discriminant == CC.DISCRIMINANT_ARCHIVE:
                
                p = not inbox
                
            elif discriminant == CC.DISCRIMINANT_LOCAL:
                
                p = locations_manager.IsLocal()
                
            elif discriminant == CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH:
                
                p = locations_manager.IsLocal() and not locations_manager.IsTrashed()
                
            elif discriminant == CC.DISCRIMINANT_NOT_LOCAL:
                
                p = not locations_manager.IsLocal()
                
            elif discriminant == CC.DISCRIMINANT_DOWNLOADING:
                
                p = locations_manager.IsDownloading()
                
            
            if not p:
                
                return False
                
            
        
        if is_in_file_service_key is not None:
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if is_in_file_service_key not in locations_manager.GetCurrent():
                
                return False
                
            
        
        if is_not_in_file_service_key is not None:
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if is_not_in_file_service_key in locations_manager.GetCurrent():
                
                return False
                
            
        
        return True
        
    

class MediaSort( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_SORT
    SERIALISABLE_NAME = 'Media Sort'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, sort_type = None, sort_order = None, tag_context = None ):
        
        if sort_type is None:
            
            sort_type = ( 'system', CC.SORT_FILES_BY_FILESIZE )
            
        
        if sort_order is None:
            
            sort_order = CC.SORT_ASC
            
        
        if tag_context is None:
            
            tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
        
        ( sort_metatype, sort_data ) = sort_type
        
        if sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            sort_data = ( tuple( namespaces ), tag_display_type )
            
            sort_type = ( sort_metatype, sort_data )
            
        
        self.sort_type = sort_type
        self.sort_order = sort_order
        self.tag_context = tag_context
        
    
    def __eq__( self, other ):
        
        if isinstance( other, MediaSort ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.sort_type, self.sort_order, self.tag_context ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            serialisable_sort_data = sort_data
            
        elif sort_metatype == 'namespaces':
            
            serialisable_sort_data = sort_data
            
        elif sort_metatype == 'rating':
            
            service_key = sort_data
            
            serialisable_sort_data = service_key.hex()
            
        
        serialisable_tag_context = self.tag_context.GetSerialisableTuple()
        
        return ( sort_metatype, serialisable_sort_data, self.sort_order, serialisable_tag_context )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( sort_metatype, serialisable_sort_data, self.sort_order, serialisable_tag_context ) = serialisable_info
        
        if sort_metatype == 'system':
            
            sort_data = serialisable_sort_data
            
        elif sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = serialisable_sort_data
            
            sort_data = ( tuple( namespaces ), tag_display_type )
            
        elif sort_metatype == 'rating':
            
            sort_data = bytes.fromhex( serialisable_sort_data )
            
        
        self.sort_type = ( sort_metatype, sort_data )
        
        self.tag_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_context )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( sort_metatype, serialisable_sort_data, sort_order ) = old_serialisable_info
            
            if sort_metatype == 'namespaces':
                
                namespaces = serialisable_sort_data
                serialisable_sort_data = ( namespaces, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                
            
            new_serialisable_info = ( sort_metatype, serialisable_sort_data, sort_order )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( sort_metatype, serialisable_sort_data, sort_order ) = old_serialisable_info
            
            tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
            serialisable_tag_context = tag_context.GetSerialisableTuple()
            
            new_serialisable_info = ( sort_metatype, serialisable_sort_data, sort_order, serialisable_tag_context )
            
            return ( 3, new_serialisable_info )
            
        
    
    def CanAsc( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            if sort_data in ( CC.SORT_FILES_BY_MIME, CC.SORT_FILES_BY_RANDOM ):
                
                return False
                
            
        
        return True
        
    
    def CanSortAtDBLevel( self, location_context: ClientLocation.LocationContext ) -> bool:
        
        if location_context.IsAllKnownFiles():
            
            return False
            
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        if sort_metadata == 'system':
            
            return sort_data in {
                CC.SORT_FILES_BY_IMPORT_TIME,
                CC.SORT_FILES_BY_FILESIZE,
                CC.SORT_FILES_BY_DURATION,
                CC.SORT_FILES_BY_FRAMERATE,
                CC.SORT_FILES_BY_NUM_FRAMES,
                CC.SORT_FILES_BY_WIDTH,
                CC.SORT_FILES_BY_HEIGHT,
                CC.SORT_FILES_BY_RATIO,
                CC.SORT_FILES_BY_NUM_PIXELS,
                CC.SORT_FILES_BY_MEDIA_VIEWS,
                CC.SORT_FILES_BY_MEDIA_VIEWTIME,
                CC.SORT_FILES_BY_APPROX_BITRATE,
                CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP,
                CC.SORT_FILES_BY_LAST_VIEWED_TIME,
                CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP,
                CC.SORT_FILES_BY_RANDOM,
                CC.SORT_FILES_BY_HASH,
                CC.SORT_FILES_BY_PIXEL_HASH,
                CC.SORT_FILES_BY_BLURHASH,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW,
                CC.SORT_FILES_BY_AVERAGE_COLOUR_HUE
            }
            
        
        return False
        
    
    def GetNamespaces( self ):
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        if sort_metadata == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            return list( namespaces )
            
        else:
            
            return []
            
        
    
    def GetSortKeyAndReverse( self, location_context: ClientLocation.LocationContext ):
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        def deal_with_none( x ):
            
            if x is None: return -1
            else: return x
            
        
        reverse = self.sort_order == CC.SORT_DESC
        
        if sort_metadata == 'system':
            
            if sort_data == CC.SORT_FILES_BY_RANDOM:
                
                def sort_key( x ):
                    
                    return random.random()
                    
                
            elif sort_data == CC.SORT_FILES_BY_HASH:
                
                def sort_key( x ):
                    
                    return x.GetHash().hex()
                    
                
            elif sort_data == CC.SORT_FILES_BY_PIXEL_HASH:
                
                def sort_key( x ):
                    
                    pixel_hash = x.GetDisplayMedia().GetMediaResult().GetFileInfoManager().pixel_hash
                    
                    if pixel_hash is None:
                        
                        return ( 0 if reverse else 1, b'\xff' * 32 )
                        
                    else:
                        
                        return ( 1 if reverse else 0, pixel_hash )
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_BLURHASH:
                
                def sort_key( x ):
                    
                    blurhash = x.GetDisplayMedia().GetMediaResult().GetFileInfoManager().blurhash
                    
                    if blurhash is None:
                        
                        return ( 0 if reverse else 1, '' )
                        
                    else:
                        
                        return ( 1 if reverse else 0, blurhash )
                        
                    
                
            elif sort_data in CC.AVERAGE_COLOUR_FILE_SORTS:
                
                blurhash_converter = GetBlurhashToSortableCall( sort_data )
                
                def sort_key( x ):
                    
                    blurhash = x.GetDisplayMedia().GetMediaResult().GetFileInfoManager().blurhash
                    
                    if blurhash is None:
                        
                        return ( 0 if reverse else 1, '' )
                        
                    else:
                        
                        return ( 1 if reverse else 0, blurhash_converter( blurhash, reverse ) )
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_APPROX_BITRATE:
                
                def sort_key( x ):
                    
                    # videos > images > pdfs
                    # heavy vids first, heavy images first
                    
                    duration_ms = x.GetDurationMS()
                    num_frames = x.GetNumFrames()
                    size = x.GetSize()
                    resolution = x.GetResolution()
                    
                    if duration_ms is None or duration_ms == 0:
                        
                        if size is None or size == 0:
                            
                            duration_bitrate = -1
                            frame_bitrate = -1
                            
                        else:
                            
                            duration_bitrate = 0
                            
                            if resolution is None:
                                
                                frame_bitrate = 0
                                
                            else:
                                
                                ( width, height ) = x.GetResolution()
                                
                                if size is None or size == 0 or not x.HasUsefulResolution():
                                    
                                    frame_bitrate = -1
                                    
                                else:
                                    
                                    num_pixels = width * height
                                    
                                    frame_bitrate = size / num_pixels
                                    
                                
                            
                        
                    else:
                        
                        if size is None or size == 0:
                            
                            duration_bitrate = -1
                            frame_bitrate = -1
                            
                        else:
                            
                            duration_bitrate = size / duration_ms
                            
                            if num_frames is None or num_frames == 0:
                                
                                frame_bitrate = 0
                                
                            else:
                                
                                frame_bitrate = duration_bitrate / num_frames
                                
                            
                        
                    
                    return ( duration_bitrate, frame_bitrate )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FILESIZE:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetSize() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_DURATION:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetDurationMS() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FRAMERATE:
                
                def sort_key( x ):
                    
                    num_frames = x.GetNumFrames()
                    
                    if num_frames is None or num_frames == 0:
                        
                        return -1
                        
                    
                    duration_ms = x.GetDurationMS()
                    
                    if duration_ms is None or duration_ms == 0:
                        
                        return -1
                        
                    
                    return num_frames / duration_ms
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_COLLECTION_FILES:
                
                def sort_key( x ):
                    
                    return ( x.GetNumFiles(), isinstance( x, MediaCollection ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_FRAMES:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetNumFrames() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_HAS_AUDIO:
                
                def sort_key( x ):
                    
                    return - deal_with_none( x.HasAudio() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_IMPORT_TIME:
                
                def sort_key( x ):
                    
                    # note we use hash_id here, thanks to a user for pointing it out, as a nice way to break 1-second-resolution ties
                    
                    return ( deal_with_none( x.GetLocationsManager().GetBestCurrentTimestamp( location_context ) ), x.GetEarliestHashId() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetLocationsManager().GetTimesManager().GetAggregateModifiedTimestampMS() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_LAST_VIEWED_TIME:
                
                def sort_key( x ):
                    
                    times_manager = x.GetFileViewingStatsManager().GetTimesManager()
                    
                    # do not do viewtime as a secondary sort here, to allow for user secondary sort to help out
                    
                    return deal_with_none( times_manager.GetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP:
                
                def sort_key( x ):
                    
                    locations_manager = x.GetLocationsManager()
                    
                    return ( not locations_manager.inbox, deal_with_none( x.GetLocationsManager().GetTimesManager().GetArchivedTimestampMS() ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_HEIGHT:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetResolution()[1] )
                    
                
            elif sort_data == CC.SORT_FILES_BY_WIDTH:
                
                def sort_key( x ):
                    
                    return deal_with_none( x.GetResolution()[0] )
                    
                
            elif sort_data == CC.SORT_FILES_BY_RATIO:
                
                def sort_key( x ):
                    
                    ( width, height ) = x.GetResolution()
                    
                    if not x.HasUsefulResolution():
                        
                        return -1
                        
                    else:
                        
                        return width / height
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_PIXELS:
                
                def sort_key( x ):
                    
                    ( width, height ) = x.GetResolution()
                    
                    if width is None or height is None:
                        
                        return -1
                        
                    else:
                        
                        return width * height
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_NUM_TAGS:
                
                def sort_key( x ):
                    
                    tags_manager = x.GetTagsManager()
                    
                    # this is self.tag_context, not the given tag context
                    
                    return len( tags_manager.GetCurrentAndPending( self.tag_context.service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_MIME:
                
                def sort_key( x ):
                    
                    return x.GetMime()
                    
                
            elif sort_data in ( CC.SORT_FILES_BY_MEDIA_VIEWS, CC.SORT_FILES_BY_MEDIA_VIEWTIME ):
                
                desired_canvas_types = CG.client_controller.new_options.GetIntegerList( 'file_viewing_stats_interesting_canvas_types' )
                
                if sort_data == CC.SORT_FILES_BY_MEDIA_VIEWS:
                    
                    def sort_key( x ):
                        
                        fvsm = x.GetFileViewingStatsManager()
                        
                        # do not do viewtime as a secondary sort here, to allow for user secondary sort to help out
                        
                        return sum( fvsm.GetViews( canvas_type ) for canvas_type in desired_canvas_types )
                        
                    
                else:
                    
                    def sort_key( x ):
                        
                        fvsm = x.GetFileViewingStatsManager()
                        
                        # do not do views as a secondary sort here, to allow for user secondary sort to help out
                        
                        return sum( fvsm.GetViewtimeMS( canvas_type ) for canvas_type in desired_canvas_types )
                        
                    
                
            
        elif sort_metadata == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            def sort_key( x ):
                
                x_tags_manager = x.GetTagsManager()
                
                return [ x_tags_manager.GetComparableNamespaceSlice( self.tag_context.service_key, ( namespace, ), tag_display_type ) for namespace in namespaces ]
                
            
        elif sort_metadata == 'rating':
            
            service_key = sort_data
            
            def sort_key( x ):
                
                x_ratings_manager = x.GetRatingsManager()
                
                rating = deal_with_none( x_ratings_manager.GetRating( service_key ) )
                
                return rating
                
            
        
        return ( sort_key, reverse )
        
    
    def GetSortOrderStrings( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            sort_string_lookup = {}
            
            sort_string_lookup[ CC.SORT_FILES_BY_APPROX_BITRATE ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FILESIZE ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_DURATION ] = ( 'shortest first', 'longest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FRAMERATE ] = ( 'slowest first', 'fastest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_COLLECTION_FILES ] = ( 'fewest first', 'most first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_FRAMES ] = ( 'smallest first', 'largest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_HAS_AUDIO ] = ( 'audio first', 'silent first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_IMPORT_TIME ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_LAST_VIEWED_TIME ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP ] = ( 'oldest first', 'newest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_MIME ] = ( 'filetype', 'filetype', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_RANDOM ] = ( 'random', 'random', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_PIXEL_HASH ] = ( 'lexicographic', 'reverse lexicographic', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_HASH ] = ( 'lexicographic', 'reverse lexicographic', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_BLURHASH ] = ( 'lexicographic', 'reverse lexicographic', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS ] = ( 'darkest first', 'lightest first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE ] = ( 'greys first', 'colours first', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED ] = ( 'greens first', 'reds first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW ] = ( 'blues first', 'yellows first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_AVERAGE_COLOUR_HUE ] = ( 'rainbow - red first', 'rainbow - purple first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_WIDTH ] = ( 'slimmest first', 'widest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_HEIGHT ] = ( 'shortest first', 'tallest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_RATIO ] = ( 'tallest first', 'widest first', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_PIXELS ] = ( 'ascending', 'descending', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_NUM_TAGS ] = ( 'ascending', 'descending', CC.SORT_ASC )
            sort_string_lookup[ CC.SORT_FILES_BY_MEDIA_VIEWS ] = ( 'ascending', 'descending', CC.SORT_DESC )
            sort_string_lookup[ CC.SORT_FILES_BY_MEDIA_VIEWTIME ] = ( 'ascending', 'descending', CC.SORT_DESC )
            
            return sort_string_lookup[ sort_data ]
            
        elif sort_metatype == 'namespaces':
            
            return ( 'a-z', 'z-a', CC.SORT_ASC )
            
        else:
            
            return ( 'ascending', 'descending', CC.SORT_DESC )
            
        
    
    def GetSortTypeString( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        sort_string = 'sort by '
        
        if sort_metatype == 'system':
            
            sort_string += CC.sort_type_string_lookup[ sort_data ]
            
        elif sort_metatype == 'namespaces':
            
            ( namespaces, tag_display_type ) = sort_data
            
            sort_string += 'tags: ' + '-'.join( namespaces )
            
        elif sort_metatype == 'rating':
            
            service_key = sort_data
            
            try:
                
                service = CG.client_controller.services_manager.GetService( service_key )
                
                name = service.GetName()
                
            except HydrusExceptions.DataMissing:
                
                name = 'unknown service'
                
            
            sort_string += 'rating: {}'.format( name )
            
        
        return sort_string
        
    
    def Sort( self, location_context: ClientLocation.LocationContext, tag_context: ClientSearchTagContext.TagContext, media_results_list: HydrusLists.FastIndexUniqueList ):
        
        # the tag context here is that of the page overall. I removed it from GetSortKeyAndReverse when I started sucking it from the media sort here for num_tags, but maybe in future we'll want some
        # sophisticated logic somewhere that soys 'use the page' instead of what the sort has. so don't remove it too aggressively m8
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        if sort_data == CC.SORT_FILES_BY_RANDOM:
            
            media_results_list.random_sort()
            
        else:
            
            ( sort_key, reverse ) = self.GetSortKeyAndReverse( location_context )
            
            media_results_list.sort( key = sort_key, reverse = reverse )
            
            if HG.file_sort_report_mode:
                
                HydrusData.ShowText( f'Sort occurred according to {self.ToString()}' )
                
                for mr in media_results_list:
                    
                    HydrusData.ShowText( ( mr.GetHash().hex(), sort_key( mr ) ) )
                    
                
            
        
    
    def ToString( self ):
        
        sort_type_string = self.GetSortTypeString()
        
        ( asc_string, desc_string, sort_gumpf ) = self.GetSortOrderStrings()
        
        sort_order_string = asc_string if self.sort_order == CC.SORT_ASC else desc_string
        
        return '{}, {}'.format( sort_type_string, sort_order_string )
        
    
    def ToDictForAPI( self ):

        ( sort_metatype, sort_data ) = self.sort_type

        data = {
            'sort_metatype' : sort_metatype,
            'sort_order' : self.sort_order,
            'tag_context': self.tag_context.ToDictForAPI(),
        }

        if sort_metatype == 'system':
            
            data[ 'sort_type' ] = sort_data
            
        elif sort_metatype == 'namespaces':
            
            (namespaces, tag_display_type) = sort_data

            data[ 'namespaces' ] = self.GetNamespaces()
            data[ 'tag_display_type' ] = tag_display_type
            
        elif sort_metatype == 'rating':
            
            service_key = sort_data
            
            data[ 'service_key' ] = service_key.hex()
        
        return data
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MEDIA_SORT ] = MediaSort
