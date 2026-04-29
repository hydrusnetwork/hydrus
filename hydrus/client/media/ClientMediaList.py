import collections
import collections.abc
import random
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientServices
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaCollect
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaSingle
from hydrus.client.media import ClientMediaSort
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchTagContext

def FlattenMedia( medias: collections.abc.Collection[ ClientMedia.Media ] ) -> list[ ClientMediaSingle.MediaSingle ]:
    
    flat_media = []
    
    for media in medias:
        
        if media.IsCollection():
            
            collected_media = typing.cast( MediaCollection, media )
            
            flat_media.extend( collected_media.GetFlatMedia() )
            
        else:
            
            single_media = typing.cast( ClientMediaSingle.MediaSingle, media )
            
            flat_media.append( single_media )
            
        
    
    return flat_media
    

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
        
        self._media_sort = ClientMediaSort.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        self._secondary_media_sort = None
        self._media_collect = ClientMediaCollect.MediaCollect()
        
        self._sorted_media = HydrusLists.FastIndexUniqueList( [ self._GenerateMediaSingle( media_result ) for media_result in media_results ] )
        self._selected_media: set[ ClientMedia.Media ] = set()
        
        self._singleton_media = set( self._sorted_media )
        self._collected_media = set()
        
        self._media_index_history = []
        
        self._RecalcHashes()
        
    
    def __len__( self ):
        
        return len( self._singleton_media ) + sum( map( len, self._collected_media ) )
        
    
    def _CalculateCollectionKeysToMedias( self, media_collect: ClientMediaCollect.MediaCollect, medias ):
        
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
        
    
    def _GenerateMediaSingle( self, media_result ):
        
        return ClientMediaSingle.MediaSingle( media_result )
        
    
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
            
            if m.IsCollection():
                
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
                
            
            new_media.append( self._GenerateMediaSingle( media_result ) )
            
        
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
            
            flat_media.extend( [ self._GenerateMediaSingle( media_result ) for media_result in media.GetMediaResults() ] )
            
        
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
        
        selected_media = self.GetSelectedMedia()
        flat_selected_media = FlattenMedia( selected_media )
        
        d[ 'num_files_selected' ] = len( flat_selected_media )
        d[ 'hash_ids_selected' ] = [ m.GetMediaResult().GetHashId() for m in flat_selected_media ]
        
        if not simple:
            
            hashes = self.GetHashes( ordered = True )
            
            d[ 'hashes' ] = [ hash.hex() for hash in hashes ]
            
            selected_hashes = [ m.GetHash() for m in flat_selected_media ]
            
            d[ 'hashes_selected' ] = [ hash.hex() for hash in selected_hashes ]
            
        
        return d
        
    
    def GetFirst( self ):
        
        return self._GetFirst()
        
    
    def GetFlatMedia( self ) -> list[ ClientMediaSingle.MediaSingle ]:
        
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
                    
                    if not ClientMedia.UserWantsUsToDisplayMedia( media.GetMediaResult(), CC.CANVAS_MEDIA_VIEWER ) or not ClientMedia.CanDisplayMedia( media ):
                        
                        continue
                        
                    
                
                media_results.append( media.GetMediaResult() )
                
            
        
        return media_results
        
    
    def GetNext( self, media ) -> ClientMedia.Media | None:
        
        return self._GetNext( media )
        
    
    def GetNumArchive( self ):
        
        num_archive = sum( ( 1 for m in self._singleton_media if not m.HasInbox() ) ) + sum( ( m.GetNumArchive() for m in self._collected_media ) )
        
        return num_archive
        
    
    def GetNumFiles( self ):
        
        return len( self._hashes )
        
    
    def GetNumInbox( self ):
        
        num_inbox = sum( ( 1 for m in self._singleton_media if m.HasInbox() ) ) + sum( ( m.GetNumInbox() for m in self._collected_media ) )
        
        return num_inbox
        
    
    def GetPrevious( self, media ) -> ClientMedia.Media | None:
        
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
        
    
    def IndexOf( self, media: ClientMedia.Media ):
        
        return self._sorted_media.index( media )
        
    
    def MoveMedia( self, medias: list[ ClientMedia.Media ], insertion_index: int ):
        
        if len( medias ) == 0:
            
            return
            
        
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
                        all_local_file_services = set( list( local_file_domains ) + [ CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, CC.TRASH_SERVICE_KEY, CC.LOCAL_UPDATE_SERVICE_KEY ] )
                        
                        #
                        
                        physically_deleted = service_key == CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY
                        possibly_trashed = ( service_key in local_file_domains or service_key == CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) and action == HC.CONTENT_UPDATE_DELETE
                        
                        deleted_specifically_from_our_domain = self._location_context.IsOneDomain() and service_key in self._location_context.current_service_keys
                        deleted_implicitly_from_our_domain = set( self._location_context.current_service_keys ).issubset( local_file_domains ) and service_key == CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY
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
        
    
    def Sort( self, media_sort: ClientMediaSort.MediaSort | None = None, secondary_sort: ClientMediaSort.MediaSort | None = None ):
        
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
        
    

class MediaCollection( MediaList, ClientMedia.Media ):
    
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
        
        self._has_simulated_duration = False
        
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
        
        self._has_simulated_duration = True in ( media.HasSimulatedDuration() for media in self._sorted_media )
        
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
        
    
    def GetDisplayMedia( self ) -> "ClientMediaSingle.MediaSingle | None":
        
        first = self._GetFirst()
        
        if first is None:
            
            return None
            
        else:
            
            return first.GetDisplayMedia()
            
        
    
    def GetDisplayMediaResult( self ) -> ClientMediaResult.MediaResult | None:
        
        first = self._GetFirst()
        
        if first is None:
            
            return None
            
        else:
            
            return first.GetDisplayMediaResult()
            
        
    
    def GetDurationMS( self ):
        
        return self._duration
        
    
    def GetEarliestHashId( self ):
        
        return min( ( m.GetEarliestHashId() for m in self._sorted_media ) )
        
    
    def GetFileViewingStatsManager( self ):
        
        return self._file_viewing_stats_manager
        
    
    def GetFramerate( self ):
        
        duration_ms = self.GetDurationMS()
        num_frames = self.GetNumFrames()
        
        # I wanted to do `num_frames <= 1`, but it caused complications in db search, so KISS
        
        if duration_ms is None or duration_ms == 0 or num_frames is None or num_frames <= 0:
            
            return None
            
        else:
            
            try:
                
                return num_frames / HydrusTime.SecondiseMSFloat( duration_ms )
                
            except Exception as e:
                
                return None
                
            
        
    
    def GetHash( self ):
        
        display_media_result = self.GetDisplayMediaResult()
        
        if display_media_result is None:
            
            return None
            
        else:
            
            return display_media_result.GetHash()
            
        
    
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
        
    
    def HasSimulatedDuration( self ) -> bool:
        
        return self._has_simulated_duration
        
    
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
        
    
