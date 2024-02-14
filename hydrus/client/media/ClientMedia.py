import collections
import random
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusPSDHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientTime
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearch

def CanDisplayMedia( media: "MediaSingleton" ) -> bool:
    
    if media is None:
        
        return False
        
    
    media = media.GetDisplayMedia()
    
    if media is None:
        
        return False
        
    
    locations_manager = media.GetLocationsManager()
    
    if not locations_manager.IsLocal():
        
        return False
        
    
    # note width/height is None for audio etc..
    
    ( width, height ) = media.GetResolution()
    
    if width == 0 or height == 0: # we cannot display this gonked out svg
        
        return False
        
    
    if media.IsStaticImage() and ( width is None or height is None ):
        
        return False
        
    
    return True
    

def FlattenMedia( media_list ) -> typing.List[ "MediaSingleton" ]:
    
    flat_media = []
    
    for media in media_list:
        
        if media.IsCollection():
            
            flat_media.extend( media.GetFlatMedia() )
            
        else:
            
            flat_media.append( media )
            
        
    
    return flat_media
    

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
    

def GetMediasFiletypeSummaryString( medias: typing.Collection[ "Media" ] ):
    
        def GetDescriptor( plural, classes, num_collections ):
            
            suffix = 's' if plural else ''
            
            if len( classes ) == 0:
                
                return 'file' + suffix
                
            
            if len( classes ) == 1:
                
                ( mime, ) = classes
                
                if mime == HC.APPLICATION_HYDRUS_CLIENT_COLLECTION:
                    
                    collections_suffix = 's' if num_collections > 1 else ''
                    
                    return 'file{} in {} collection{}'.format( suffix, HydrusData.ToHumanInt( num_collections ), collections_suffix )
                    
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
        
        if num_files > 1000:
            
            filetype_summary = 'files'
            
        else:
            
            mimes = { media.GetMime() for media in medias }
            
            if HC.APPLICATION_HYDRUS_CLIENT_COLLECTION in mimes:
                
                num_collections = len( [ media for media in medias if isinstance( media, MediaCollection ) ] )
                
            else:
                
                num_collections = 0
                
            
            plural = len( medias ) > 1 or sum( ( m.GetNumFiles() for m in medias ) ) > 1
            
            filetype_summary = GetDescriptor( plural, mimes, num_collections )
            
        
        return f'{HydrusData.ToHumanInt( num_files )} {filetype_summary}'
        

def GetMediasTagCount( pool, tag_service_key, tag_display_type ):
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection():
            
            tags_managers.extend( media.GetSingletonsTagsManagers() )
            
        else:
            
            tags_managers.append( media.GetTagsManager() )
            
        
    
    return GetTagsManagersTagCount( tags_managers, tag_service_key, tag_display_type )
    

def GetShowAction( media: "MediaSingleton", canvas_type: int ):
    
    start_paused = False
    start_with_embed = False
    
    bad_result = ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, start_paused, start_with_embed )
    
    if media is None:
        
        return bad_result
        
    
    mime = media.GetMime()
    
    if mime not in HC.ALLOWED_MIMES: # stopgap to catch a collection or application_unknown due to unusual import order/media moving
        
        return bad_result
        
    
    if canvas_type == CC.CANVAS_PREVIEW:
        
        action =  CG.client_controller.new_options.GetPreviewShowAction( mime )
        
    else:
        
        action = CG.client_controller.new_options.GetMediaShowAction( mime )
        
    
    if mime == HC.APPLICATION_PSD and action[0] == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE and not HydrusPSDHandling.PSD_TOOLS_OK:
        
        # fallback to open externally button when psd_tools not available 
        action = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, start_paused, start_with_embed )
        
    
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
    

def UserWantsUsToDisplayMedia( media: "MediaSingleton", canvas_type: int ) -> bool:
    
    ( media_show_action, media_start_paused, media_start_with_embed ) = GetShowAction( media, canvas_type )
    
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
        
    
    def GetDisplayMedia( self ) -> 'Media':
        
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
        
    
    def GetPrettyInfoLines( self, only_interesting_lines = False ) -> typing.List[ str ]:
        
        raise NotImplementedError()
        
    
    def GetRatingsManager( self ) -> ClientMediaManagers.RatingsManager:
        
        raise NotImplementedError()
        
    
    def GetResolution( self ) -> typing.Tuple[ int, int ]:
        
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
        
    
    def HasDeleteLocked( self ) -> bool:
        
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
        
    
    def UpdateFileInfo( self, hashes_to_media_results ):
        
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
            
            tag_context = ClientSearch.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
        
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
            
            tag_context = ClientSearch.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
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
    
    def __init__( self, location_context: ClientLocation.LocationContext, media_results ):
        
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
        
        self._hashes = set()
        self._hashes_ordered = []
        
        self._hashes_to_singleton_media = {}
        self._hashes_to_collected_media = {}
        
        self._media_sort = MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        self._media_collect = MediaCollect()
        
        self._sorted_media = SortedList( [ self._GenerateMediaSingleton( media_result ) for media_result in media_results ] )
        self._selected_media = set()
        
        self._singleton_media = set( self._sorted_media )
        self._collected_media = set()
        
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
        self._sorted_media.append_items( addable_media )
        
        return new_media
        
    
    def Clear( self ):
        
        self._singleton_media = set()
        self._collected_media = set()
        
        self._selected_media = set()
        self._sorted_media = SortedList()
        
        self._RecalcAfterMediaRemove()
        
    
    def Collect( self, media_collect = None ):
        
        if media_collect is None:
            
            media_collect = self._media_collect
            
        
        self._media_collect = media_collect
        
        flat_media = list( self._singleton_media )
        
        for media in self._collected_media:
            
            flat_media.extend( [ self._GenerateMediaSingleton( media_result ) for media_result in media.GenerateMediaResults() ] )
            
        
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
            
        
        self._sorted_media = SortedList( list( self._singleton_media ) + list( self._collected_media ) )
        
        self._RecalcHashes()
        
    
    def DeletePending( self, service_key ):
        
        for media in self._collected_media:
            
            media.DeletePending( service_key )
            
        
    
    def GenerateMediaResults( self, is_in_file_service_key = None, discriminant = None, selected_media = None, unrated = None, for_media_viewer = False ):
        
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
                
                media_results.extend( media.GenerateMediaResults( is_in_file_service_key = is_in_file_service_key, discriminant = discriminant, unrated = unrated, for_media_viewer = True ) )
                
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
                    
                    if not UserWantsUsToDisplayMedia( media, CC.CANVAS_MEDIA_VIEWER ) or not CanDisplayMedia( media ):
                        
                        continue
                        
                    
                
                media_results.append( media.GetMediaResult() )
                
            
        
        return media_results
        
    
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
        
    
    def GetMediaIndex( self, media ):
        
        return self._sorted_media.index( media )
        
    
    def GetNext( self, media ):
        
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
        
    
    def MoveMedia( self, medias: typing.List[ Media ], insertion_index: int ):
        
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
                        possibly_trashed = service_key in local_file_domains and action == HC.CONTENT_UPDATE_DELETE
                        deleted_from_our_domain = self._location_context.IsOneDomain() and service_key in self._location_context.current_service_keys
                        
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
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action == HC.SERVICE_UPDATE_DELETE_PENDING:
                    
                    self.DeletePending( service_key )
                    
                elif action == HC.SERVICE_UPDATE_RESET:
                    
                    self.ResetService( service_key )
                    
                
            
        
    
    def ResetService( self, service_key ):
        
        if self._location_context.IsOneDomain() and service_key in self._location_context.current_service_keys:
            
            self._RemoveMediaDirectly( self._singleton_media, self._collected_media )
            
        else:
            
            for media in self._collected_media: media.ResetService( service_key )
            
        
    
    def Sort( self, media_sort = None ):
        
        for media in self._collected_media:
            
            media.Sort( media_sort )
            
        
        if media_sort is None:
            
            media_sort = self._media_sort
            
        
        self._media_sort = media_sort
        
        media_sort_fallback = CG.client_controller.new_options.GetFallbackSort()
        
        media_sort_fallback.Sort( self._location_context, self._sorted_media )
        
        # this is a stable sort, so the fallback order above will remain for equal items
        
        self._media_sort.Sort( self._location_context, self._sorted_media )
        
        self._RecalcHashes()
        
    

class ListeningMediaList( MediaList ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, media_results ):
        
        MediaList.__init__( self, location_context, media_results )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        CG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
    
    def AddMediaResults( self, media_results ):
        
        new_media = []
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            if hash in self._hashes:
                
                continue
                
            
            new_media.append( self._GenerateMediaSingleton( media_result ) )
            
        
        self.AddMedia( new_media )
        
        return new_media
        
    

class MediaCollection( MediaList, Media ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, media_results ):
        
        # note for later: ideal here is to stop this multiple inheritance mess and instead have this be a media that *has* a list, not *is* a list
        
        Media.__init__( self )
        MediaList.__init__( self, location_context, media_results )
        
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
        
        pending = HydrusData.MassUnion( [ locations_manager.GetPending() for locations_manager in all_locations_managers ] )
        petitioned = HydrusData.MassUnion( [ locations_manager.GetPetitioned() for locations_manager in all_locations_managers ] )
        
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
        
    
    def GetDisplayMedia( self ):
        
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
        
    
    def GetPrettyInfoLines( self, only_interesting_lines = False ):
        
        size = HydrusData.ToHumanBytes( self._size )
        
        mime = HC.mime_string_lookup[ HC.APPLICATION_HYDRUS_CLIENT_COLLECTION ]
        
        info_string = size + ' ' + mime
        
        info_string += ' (' + HydrusData.ToHumanInt( self.GetNumFiles() ) + ' files)'
        
        return [ info_string ]
        
    
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
        
    
    def HasDeleteLocked( self ):
        
        return True in ( media.HasDeleteLocked() for media in self._sorted_media )
        
    
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
        
    
    def IsStaticImage( self ):
        
        return False
        
    
    def IsSizeDefinite( self ):
        
        return self._size_definite
        
    
    def RecalcInternals( self ):
        
        self._RecalcInternals()
        
    
    def ResetService( self, service_key ):
        
        MediaList.ResetService( self, service_key )
        
        self._RecalcInternals()
        
    
    def UpdateFileInfo( self, hashes_to_media_results ):
        
        for media in self._sorted_media:
            
            media.UpdateFileInfo( hashes_to_media_results )
            
        
        self._RecalcInternals()
        
    
class MediaSingleton( Media ):
    
    def __init__( self, media_result: ClientMediaResult.MediaResult ):
        
        Media.__init__( self )
        
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
        
    
    def GetMediaResult( self ): return self._media_result
    
    def GetMime( self ): return self._media_result.GetMime()
    
    def GetNotesManager( self ) -> ClientMediaManagers.NotesManager:
        
        return self._media_result.GetNotesManager()
        
    
    def GetNumFiles( self ): return 1
    
    def GetNumFrames( self ): return self._media_result.GetNumFrames()
    
    def GetNumInbox( self ):
        
        if self.HasInbox(): return 1
        else: return 0
        
    
    def GetNumWords( self ): return self._media_result.GetNumWords()
    
    def GetPrettyInfoLines( self, only_interesting_lines = False ):
        
        def timestamp_ms_is_interesting( timestamp_ms_1, timestamp_ms_2 ):
            
            distance_1 = abs( timestamp_ms_1 - HydrusTime.GetNowMS() )
            distance_2 = abs( timestamp_ms_2 - HydrusTime.GetNowMS() )
            
            # 50000 / 51000 = 0.98 = not interesting
            # 10000 / 51000 = 0.20 = interesting
            difference = min( distance_1, distance_2 ) / max( distance_1, distance_2, 1 )
            
            return difference < 0.9
            
        
        file_info_manager = self._media_result.GetFileInfoManager()
        locations_manager = self._media_result.GetLocationsManager()
        times_manager = locations_manager.GetTimesManager()
        
        ( hash_id, hash, size, mime, width, height, duration, num_frames, has_audio, num_words ) = file_info_manager.ToTuple()
        
        info_string = f'{HydrusData.ToHumanBytes( size )} {HC.mime_string_lookup[ mime ]}'
        
        if width is not None and height is not None:
            
            info_string += f' ({HydrusData.ConvertResolutionToPrettyString( ( width, height ) )})'
            
        
        if duration is not None:
            
            info_string += f', {HydrusTime.MillisecondsDurationToPrettyTime( duration )}'
            
        
        if num_frames is not None:
            
            if duration is None or duration == 0 or num_frames == 0:
                
                framerate_insert = ''
                
            else:
                
                framerate_insert = f', {round( num_frames / ( duration / 1000 ) )}fps'
                
            
            info_string += f' ({HydrusData.ToHumanInt( num_frames )} frames{framerate_insert})'
            
        
        if has_audio:
            
            audio_label = CG.client_controller.new_options.GetString( 'has_audio_label' )
            
            info_string += f', {audio_label}'
            
        
        if num_words is not None:
            
            info_string += f' ({HydrusData.ToHumanInt( num_words )} words)'
            
        
        lines = [ ( True, info_string ) ]
        
        if file_info_manager.FiletypeIsForced():
            
            lines.append( ( False, f'filetype was originally: {HC.mime_string_lookup[ file_info_manager.original_mime ]}' ) )
            
        
        current_service_keys = locations_manager.GetCurrent()
        deleted_service_keys = locations_manager.GetDeleted()
        
        local_file_services = CG.client_controller.services_manager.GetLocalMediaFileServices()
        
        seen_local_file_service_timestamps_ms = set()
        
        current_local_file_services = [ service for service in local_file_services if service.GetServiceKey() in current_service_keys ]
        
        if len( current_local_file_services ) > 0:
            
            for local_file_service in current_local_file_services:
                
                import_timestamp_ms = times_manager.GetImportedTimestampMS( local_file_service.GetServiceKey() )
                
                lines.append( ( True, 'added to {}: {}'.format( local_file_service.GetName(), ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( import_timestamp_ms ) ) ) ) )
                
                seen_local_file_service_timestamps_ms.add( import_timestamp_ms )
                
            
        
        if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in current_service_keys:
            
            import_timestamp_ms = times_manager.GetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
            if CG.client_controller.new_options.GetBoolean( 'hide_uninteresting_local_import_time' ):
                
                # if we haven't already printed this timestamp somewhere
                line_is_interesting = False not in ( timestamp_ms_is_interesting( timestamp_ms, import_timestamp_ms ) for timestamp_ms in seen_local_file_service_timestamps_ms )
                
            else:
                
                line_is_interesting = True
                
            
            lines.append( ( line_is_interesting, 'imported: {}'.format( ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( import_timestamp_ms ) ) ) ) )
            
            if line_is_interesting:
                
                seen_local_file_service_timestamps_ms.add( import_timestamp_ms )
                
            
        
        deleted_local_file_services = [ service for service in local_file_services if service.GetServiceKey() in deleted_service_keys ]
        
        local_file_deletion_reason = locations_manager.GetLocalFileDeletionReason()
        
        if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in deleted_service_keys:
            
            timestamp_ms = times_manager.GetDeletedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
            lines.append( ( True, 'deleted from this client {} ({})'.format( ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) ), local_file_deletion_reason ) ) )
            
        elif CC.TRASH_SERVICE_KEY in current_service_keys:
            
            # I used to list these always as part of 'interesting' lines, but without the trash qualifier, you get spammy 'removed from x 5 years ago' lines for migrations. not helpful!
            
            for local_file_service in deleted_local_file_services:
                
                timestamp_ms = times_manager.GetDeletedTimestampMS( local_file_service.GetServiceKey() )
                
                line = 'removed from {} {}'.format( local_file_service.GetName(), ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) ) )
                
                if len( deleted_local_file_services ) == 1:
                    
                    line = f'{line} ({local_file_deletion_reason})'
                    
                
                lines.append( ( True, line ) )
                
            
            if len( deleted_local_file_services ) > 1:
                
                lines.append( ( False, 'Deletion reason: {}'.format( local_file_deletion_reason ) ) )
                
            
        
        if locations_manager.IsTrashed():
            
            lines.append( ( True, 'in the trash' ) )
            
        
        times_manager = locations_manager.GetTimesManager()
        
        file_modified_timestamp_ms = times_manager.GetAggregateModifiedTimestampMS()
        
        if file_modified_timestamp_ms is not None:
            
            if CG.client_controller.new_options.GetBoolean( 'hide_uninteresting_modified_time' ):
                
                # if we haven't already printed this timestamp somewhere
                line_is_interesting = False not in ( timestamp_ms_is_interesting( timestamp_ms, file_modified_timestamp_ms ) for timestamp_ms in seen_local_file_service_timestamps_ms )
                
            else:
                
                line_is_interesting = True
                
            
            lines.append( ( line_is_interesting, 'modified: {}'.format( ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( file_modified_timestamp_ms ) ) ) ) )
            
            modified_timestamp_lines = []
            
            timestamp_ms = times_manager.GetFileModifiedTimestampMS()
            
            if timestamp_ms is not None:
                
                modified_timestamp_lines.append( 'local: {}'.format( ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) ) ) )
                
            
            for ( domain, timestamp_ms ) in sorted( times_manager.GetDomainModifiedTimestampsMS().items() ):
                
                modified_timestamp_lines.append( '{}: {}'.format( domain, ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) ) ) )
                
            
            if len( modified_timestamp_lines ) > 1:
                
                lines.append( ( False, ( 'all modified times', modified_timestamp_lines ) ) )
                
            
        
        if not locations_manager.inbox:
            
            archived_timestamp_ms = times_manager.GetArchivedTimestampMS()
            
            if archived_timestamp_ms is not None:
                
                lines.append( ( True, 'archived: {}'.format( ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( archived_timestamp_ms ) ) ) ) )
                
            
        
        for service_key in current_service_keys.intersection( CG.client_controller.services_manager.GetServiceKeys( HC.REMOTE_FILE_SERVICES ) ):
            
            timestamp_ms = times_manager.GetImportedTimestampMS( service_key )
            
            try:
                
                service = CG.client_controller.services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service_type = service.GetServiceType()
            
            if service_type == HC.IPFS:
                
                status_label = 'pinned'
                
            else:
                
                status_label = 'uploaded'
                
            
            lines.append( ( True, '{} to {} {}'.format( status_label, service.GetName(), ClientTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) ) ) ) )
            
        
        if self.GetFileInfoManager().has_audio:
            
            lines.append( ( False, 'has audio' ) )
            
        
        if self.GetFileInfoManager().has_transparency:
            
            lines.append( ( False, 'has transparency' ) )
            
        
        if self.GetFileInfoManager().has_exif:
            
            lines.append( ( False, 'has exif data' ) )
            
        
        if self.GetFileInfoManager().has_human_readable_embedded_metadata:
            
            lines.append( ( False, 'has human-readable embedded metadata' ) )
            
        
        if self.GetFileInfoManager().has_icc_profile:
            
            lines.append( ( False, 'has icc profile' ) )
            
        
        lines = [ line for ( interesting, line ) in lines if interesting or not only_interesting_lines ]
        
        return lines
        
    
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
        
    
    def HasDeleteLocked( self ):
        
        return self._media_result.IsDeleteLocked()
        
    
    IsDeleteLocked = HasDeleteLocked
    
    def HasDuration( self ):
        
        duration = self._media_result.GetDurationMS()
        
        return duration is not None and duration > 0
        
    
    def HasStaticImages( self ):
        
        return self.IsStaticImage()
        
    
    def HasInbox( self ):
        
        return self._media_result.GetInbox()
        
    
    def HasNotes( self ):
        
        return self._media_result.HasNotes()
        
    
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
        
    
    def UpdateFileInfo( self, hashes_to_media_results ):
        
        hash = self.GetHash()
        
        if hash in hashes_to_media_results:
            
            media_result = hashes_to_media_results[ hash ]
            
            self._media_result = media_result
            
        
    
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
            
            tag_context = ClientSearch.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
        
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
            
            tag_context = ClientSearch.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
            serialisable_tag_context = tag_context.GetSerialisableTuple()
            
            new_serialisable_info = ( sort_metatype, serialisable_sort_data, sort_order, serialisable_tag_context )
            
            return ( 3, new_serialisable_info )
            
        
    
    def CanAsc( self ):
        
        ( sort_metatype, sort_data ) = self.sort_type
        
        if sort_metatype == 'system':
            
            if sort_data in ( CC.SORT_FILES_BY_MIME, CC.SORT_FILES_BY_RANDOM ):
                
                return False
                
            
        
        return True
        
    
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
                        
                        return b'\xff' * 32
                        
                    else:
                        
                        return pixel_hash
                        
                    
                
            elif sort_data == CC.SORT_FILES_BY_APPROX_BITRATE:
                
                def sort_key( x ):
                    
                    # videos > images > pdfs
                    # heavy vids first, heavy images first
                    
                    duration = x.GetDurationMS()
                    num_frames = x.GetNumFrames()
                    size = x.GetSize()
                    resolution = x.GetResolution()
                    
                    if duration is None or duration == 0:
                        
                        if size is None or size == 0:
                            
                            duration_bitrate = -1
                            frame_bitrate = -1
                            
                        else:
                            
                            duration_bitrate = 0
                            
                            if resolution is None:
                                
                                frame_bitrate = 0
                                
                            else:
                                
                                ( width, height ) = x.GetResolution()
                                
                                if size is None or size == 0 or width is None or width == 0 or height is None or height == 0:
                                    
                                    frame_bitrate = -1
                                    
                                else:
                                    
                                    num_pixels = width * height
                                    
                                    frame_bitrate = size / num_pixels
                                    
                                
                            
                        
                    else:
                        
                        if size is None or size == 0:
                            
                            duration_bitrate = -1
                            frame_bitrate = -1
                            
                        else:
                            
                            duration_bitrate = size / duration
                            
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
                        
                    
                    duration = x.GetDurationMS()
                    
                    if duration is None or duration == 0:
                        
                        return -1
                        
                    
                    return num_frames / duration
                    
                
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
                    
                    if width is None or height is None or width == 0 or height == 0:
                        
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
                    
                    return len( tags_manager.GetCurrentAndPending( self.tag_context.service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_MIME:
                
                def sort_key( x ):
                    
                    return x.GetMime()
                    
                
            elif sort_data == CC.SORT_FILES_BY_MEDIA_VIEWS:
                
                def sort_key( x ):
                    
                    fvsm = x.GetFileViewingStatsManager()
                    
                    # do not do viewtime as a secondary sort here, to allow for user secondary sort to help out
                    
                    return fvsm.GetViews( CC.CANVAS_MEDIA_VIEWER )
                    
                
            elif sort_data == CC.SORT_FILES_BY_MEDIA_VIEWTIME:
                
                def sort_key( x ):
                    
                    fvsm = x.GetFileViewingStatsManager()
                    
                    # do not do views as a secondary sort here, to allow for user secondary sort to help out
                    
                    return fvsm.GetViewtime( CC.CANVAS_MEDIA_VIEWER )
                    
                
            
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
        
    
    def Sort( self, location_context: ClientLocation.LocationContext, media_results_list: "SortedList" ):
        
        ( sort_metadata, sort_data ) = self.sort_type
        
        if sort_data == CC.SORT_FILES_BY_RANDOM:
            
            media_results_list.random_sort()
            
        else:
            
            ( sort_key, reverse ) = self.GetSortKeyAndReverse( location_context )
            
            media_results_list.sort( sort_key = sort_key, reverse = reverse )
            
        
    
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

class SortedList( object ):
    
    def __init__( self, initial_items = None ):
        
        if initial_items is None:
            
            initial_items = []
            
        
        self._sort_key = None
        self._sort_reverse = False
        
        self._sorted_list = list( initial_items )
        
        self._items_to_indices = {}
        self._indices_dirty = True
        
    
    def __contains__( self, item ):
        
        if self._indices_dirty:
            
            self._RecalcIndices()
            
        
        return self._items_to_indices.__contains__( item )
        
    
    def __getitem__( self, value ):
        
        return self._sorted_list.__getitem__( value )
        
    
    def __iter__( self ):
        
        return iter( self._sorted_list )
        
    
    def __len__( self ):
        
        return len( self._sorted_list )
        
    
    def _DirtyIndices( self ):
        
        self._indices_dirty = True
        
        self._items_to_indices = {}
        
    
    def _RecalcIndices( self ):
        
        self._items_to_indices = { item : index for ( index, item ) in enumerate( self._sorted_list ) }
        
        self._indices_dirty = False
        
    
    def append_items( self, items ):
        
        if self._indices_dirty is None:
            
            self._RecalcIndices()
            
        
        for ( i, item ) in enumerate( items, start = len( self._sorted_list ) ):
            
            self._items_to_indices[ item ] = i
            
        
        self._sorted_list.extend( items )
        
    
    def index( self, item ):
        """
        This is fast!
        """
        
        if self._indices_dirty:
            
            self._RecalcIndices()
            
        
        try:
            
            result = self._items_to_indices[ item ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing()
            
        
        return result
        
    
    def insert_items( self, items, insertion_index = None ):
        
        if insertion_index is None:
            
            self.append_items( items )
            
            self.sort()
            
        else:
            
            # don't forget we can insert elements in the final slot for an append, where index >= len( muh_list ) 
            
            for ( i, item ) in enumerate( items ):
                
                self._sorted_list.insert( insertion_index + i, item )
                
            
            self._DirtyIndices()
            
        
    
    def move_items( self, new_items: typing.List, insertion_index: int ):
        
        items_to_move = []
        items_before_insertion_index = 0
        
        if insertion_index < 0:
            
            insertion_index = max( 0, len( self._sorted_list ) + ( insertion_index + 1 ) )
            
        
        for new_item in new_items:
            
            try:
                
                index = self.index( new_item )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            items_to_move.append( new_item )
            
            if index < insertion_index:
                
                items_before_insertion_index += 1
                
            
        
        if items_before_insertion_index > 0: # i.e. we are moving to the right
            
            items_before_insertion_index -= 1
            
        
        adjusted_insertion_index = insertion_index# - items_before_insertion_index
        
        if len( items_to_move ) == 0:
            
            return
            
        
        self.remove_items( items_to_move )
        
        self.insert_items( items_to_move, insertion_index = adjusted_insertion_index )
        
    
    def remove_items( self, items ):
        
        deletee_indices = [ self.index( item ) for item in items ]
        
        deletee_indices.sort( reverse = True )
        
        for index in deletee_indices:
            
            del self._sorted_list[ index ]
            
        
        self._DirtyIndices()
        
    
    def random_sort( self ):
        
        def sort_key( x ):
            
            return random.random()
            
        
        self._sort_key = sort_key
        
        random.shuffle( self._sorted_list )
        
        self._DirtyIndices()
        
    
    def sort( self, sort_key = None, reverse = False ):
        
        if sort_key is None:
            
            sort_key = self._sort_key
            reverse = self._sort_reverse
            
        else:
            
            self._sort_key = sort_key
            self._sort_reverse = reverse
            
        
        self._sorted_list.sort( key = sort_key, reverse = reverse )
        
        self._DirtyIndices()
        
    
