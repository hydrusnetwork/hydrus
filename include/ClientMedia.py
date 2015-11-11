import bisect
import collections
import ClientConstants as CC
import ClientData
import ClientFiles
import ClientRatings
import HydrusConstants as HC
import HydrusTags
import os
import random
import time
import traceback
import wx
import HydrusData
import HydrusFileHandling
import HydrusExceptions
import HydrusGlobals
import itertools

def MergeTagsManagers( tags_managers ):
    
    def CurrentAndPendingFilter( items ):
        
        for ( service_key, statuses_to_tags ) in items:
            
            filtered = { status : tags for ( status, tags ) in statuses_to_tags.items() if status in ( HC.CURRENT, HC.PENDING ) }
            
            yield ( service_key, filtered )
            
        
    
    # [[( service_key, statuses_to_tags )]]
    s_k_s_t_t_tupled = ( CurrentAndPendingFilter( tags_manager.GetServiceKeysToStatusesToTags().items() ) for tags_manager in tags_managers )
    
    # [(service_key, statuses_to_tags)]
    flattened_s_k_s_t_t = itertools.chain.from_iterable( s_k_s_t_t_tupled )
    
    # service_key : [ statuses_to_tags ]
    s_k_s_t_t_dict = HydrusData.BuildKeyToListDict( flattened_s_k_s_t_t )
    
    # now let's merge so we have service_key : statuses_to_tags
    
    merged_service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
    
    for ( service_key, several_statuses_to_tags ) in s_k_s_t_t_dict.items():
        
        # [[( status, tags )]]
        s_t_t_tupled = ( s_t_t.items() for s_t_t in several_statuses_to_tags )
        
        # [( status, tags )]
        flattened_s_t_t = itertools.chain.from_iterable( s_t_t_tupled )
        
        statuses_to_tags = HydrusData.default_dict_set()
        
        for ( status, tags ) in flattened_s_t_t: statuses_to_tags[ status ].update( tags )
        
        merged_service_keys_to_statuses_to_tags[ service_key ] = statuses_to_tags
        
    
    return TagsManagerSimple( merged_service_keys_to_statuses_to_tags )
    
class LocationsManager( object ):
    
    LOCAL_LOCATIONS = { CC.LOCAL_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY }
    
    def __init__( self, current, deleted, pending, petitioned ):
        
        self._current = current
        self._deleted = deleted
        self._pending = pending
        self._petitioned = petitioned
        
    
    def DeletePending( self, service_key ):
        
        self._pending.discard( service_key )
        self._petitioned.discard( service_key )
        
    
    def GetCDPP( self ): return ( self._current, self._deleted, self._pending, self._petitioned )
    
    def GetCurrent( self ): return self._current
    def GetCurrentRemote( self ):
        
        return self._current - self.LOCAL_LOCATIONS
        
    
    def GetDeleted( self ): return self._deleted
    def GetDeletedRemote( self ):
        
        return self._deleted - self.LOCAL_LOCATIONS
        
    
    def GetFileRepositoryStrings( self ):
    
        current = self.GetCurrentRemote()
        pending = self.GetPendingRemote()
        petitioned = self.GetPetitionedRemote()
        
        file_repo_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.FILE_REPOSITORY, ) )
        
        file_repo_services = list( file_repo_services )
        
        cmp_func = lambda a, b: cmp( a.GetName(), b.GetName() )
        
        file_repo_services.sort( cmp = cmp_func )
        
        file_repo_service_keys_and_names = [ ( file_repo_service.GetServiceKey(), file_repo_service.GetName() ) for file_repo_service in file_repo_services ]
        
        file_repo_strings = []
        
        for ( service_key, name ) in file_repo_service_keys_and_names:
            
            if service_key in pending:
                
                file_repo_strings.append( name + ' (+)' )
                
            elif service_key in current:
                
                if service_key in petitioned:
                    
                    file_repo_strings.append( name + ' (-)' )
                    
                else:
                    
                    file_repo_strings.append( name )
                    
                
            
        
        return file_repo_strings
        
    
    def GetPending( self ): return self._pending
    def GetPendingRemote( self ):
        
        return self._pending - self.LOCAL_LOCATIONS
        
    
    def GetPetitioned( self ): return self._petitioned
    def GetPetitionedRemote( self ):
        
        return self._petitioned - self.LOCAL_LOCATIONS
        
    
    def HasDownloading( self ): return CC.LOCAL_FILE_SERVICE_KEY in self._pending
    
    def HasLocal( self ): return len( self._current.intersection( self.LOCAL_LOCATIONS ) ) > 0
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            self._current.add( service_key )
            
            self._deleted.discard( service_key )
            self._pending.discard( service_key )
            
            if service_key == CC.LOCAL_FILE_SERVICE_KEY:
                
                self._current.discard( CC.TRASH_SERVICE_KEY )
                
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            self._deleted.add( service_key )
            
            self._current.discard( service_key )
            self._petitioned.discard( service_key )
            
            if service_key == CC.LOCAL_FILE_SERVICE_KEY:
                
                self._current.add( CC.TRASH_SERVICE_KEY )
                
            
        elif action == HC.CONTENT_UPDATE_UNDELETE:
            
            self._current.discard( CC.TRASH_SERVICE_KEY )
            
            self._current.add( CC.LOCAL_FILE_SERVICE_KEY )
            
        elif action == HC.CONTENT_UPDATE_PEND:
            
            if service_key not in self._current: self._pending.add( service_key )
            
        elif action == HC.CONTENT_UPDATE_PETITION:
            
            if service_key not in self._deleted: self._petitioned.add( service_key )
            
        elif action == HC.CONTENT_UPDATE_RESCIND_PEND: self._pending.discard( service_key )
        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION: self._petitioned.discard( service_key )
        
    
    def ResetService( self, service_key ):
        
        self._current.discard( service_key )
        self._pending.discard( service_key )
        self._deleted.discard( service_key )
        self._petitioned.discard( service_key )
        
    
class Media( object ):
    
    def __init__( self ):
        
        self._id = HydrusData.GenerateKey()
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._id.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
class MediaList( object ):
    
    def __init__( self, file_service_key, media_results ):
        
        self._file_service_key = file_service_key
        
        self._sort_by = CC.SORT_BY_SMALLEST
        self._collect_by = None
        
        self._collect_map_singletons = {}
        self._collect_map_collected = {}
        
        self._sorted_media = SortedList( [ self._GenerateMediaSingleton( media_result ) for media_result in media_results ] )
        
        self._singleton_media = set( self._sorted_media )
        self._collected_media = set()
        
    
    def _CalculateCollectionKeysToMedias( self, collect_by, medias ):
    
        namespaces_to_collect_by = [ data for ( collect_by_type, data ) in collect_by if collect_by_type == 'namespace' ]
        ratings_to_collect_by = [ data for ( collect_by_type, data ) in collect_by if collect_by_type == 'rating' ]
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        local_ratings_to_collect_by = [ service_key for service_key in ratings_to_collect_by if services_manager.GetService( service_key ).GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
        remote_ratings_to_collect_by = [ service_key for service_key in ratings_to_collect_by if services_manager.GetService( service_key ).GetServiceType() in ( HC.RATING_LIKE_REPOSITORY, HC.RATING_NUMERICAL_REPOSITORY ) ]
        
        keys_to_medias = collections.defaultdict( list )
        
        for media in medias:
            
            if len( namespaces_to_collect_by ) > 0: namespace_key = media.GetTagsManager().GetNamespaceSlice( namespaces_to_collect_by, collapse_siblings = True )
            else: namespace_key = None
            
            if len( ratings_to_collect_by ) > 0:
                
                ( local_ratings, remote_ratings ) = media.GetRatings()
                
                if len( local_ratings_to_collect_by ) > 0: local_rating_key = local_ratings.GetRatingSlice( local_ratings_to_collect_by )
                else: local_rating_key = None
                
                if len( remote_ratings_to_collect_by ) > 0: remote_rating_key = remote_ratings.GetRatingSlice( remote_ratings_to_collect_by )
                else: remote_rating_key = None
                
                rating_key = ( local_rating_key, remote_rating_key )
                
            else: rating_key = None
            
            keys_to_medias[ ( namespace_key, rating_key ) ].append( media )
            
        
        return keys_to_medias
        
    
    def _GenerateMediaCollection( self, media_results ): return MediaCollection( self._file_service_key, media_results )
    
    def _GenerateMediaSingleton( self, media_result ): return MediaSingleton( media_result )
    
    def _GetFirst( self ): return self._sorted_media[ 0 ]
    
    def _GetHashes( self ):
        
        result = set()
        
        for media in self._sorted_media: result.update( media.GetHashes() )
        
        return result
        
    
    def _GetLast( self ): return self._sorted_media[ -1 ]
    
    def _GetMedia( self, hashes, discriminator = None ):
        
        if discriminator is None: medias = self._sorted_media
        elif discriminator == 'singletons': medias = self._singleton_media
        elif discriminator == 'collections': medias = self._collected_media
        
        return [ media for media in medias if not hashes.isdisjoint( media.GetHashes() ) ]
        
    
    def _GetNext( self, media ):
        
        if media is None: return None
        
        next_index = self._sorted_media.index( media ) + 1
        
        if next_index == len( self._sorted_media ): return self._GetFirst()
        else: return self._sorted_media[ next_index ]
        
    
    def _GetPrevious( self, media ):
        
        if media is None: return None
        
        previous_index = self._sorted_media.index( media ) - 1
        
        if previous_index == -1: return self._GetLast()
        else: return self._sorted_media[ previous_index ]
        
    
    def _RemoveMedia( self, singleton_media, collected_media ):
        
        if type( singleton_media ) != set: singleton_media = set( singleton_media )
        if type( collected_media ) != set: collected_media = set( collected_media )
        
        self._singleton_media.difference_update( singleton_media )
        self._collected_media.difference_update( collected_media )
        
        keys_to_remove = [ key for ( key, media ) in self._collect_map_singletons if media in singleton_media ]
        for key in keys_to_remove: del self._collect_map_singletons[ key ]
        
        keys_to_remove = [ key for ( key, media ) in self._collect_map_collected if media in collected_media ]
        for key in keys_to_remove: del self._collect_map_collected[ key ]
        
        self._sorted_media.remove_items( singleton_media.union( collected_media ) )
        
    
    def Collect( self, collect_by = -1 ):
        
        if collect_by == -1: collect_by = self._collect_by
        
        self._collect_by = collect_by
        
        for media in self._collected_media: self._singleton_media.update( [ self._GenerateMediaSingleton( media_result ) for media_result in media.GenerateMediaResults() ] )
        
        self._collected_media = set()
        
        self._collect_map_singletons = {}
        self._collect_map_collected = {}
        
        if collect_by is not None:
            
            keys_to_medias = self._CalculateCollectionKeysToMedias( collect_by, self._singleton_media )
            
            self._collect_map_singletons = { key : medias[0] for ( key, medias ) in keys_to_medias.items() if len( medias ) == 1 }
            self._collect_map_collected = { key : self._GenerateMediaCollection( [ media.GetMediaResult() for media in medias ] ) for ( key, medias ) in keys_to_medias.items() if len( medias ) > 1 }
            
            self._singleton_media = set( self._collect_map_singletons.values() )
            self._collected_media = set( self._collect_map_collected.values() )
            
        
        self._sorted_media = SortedList( list( self._singleton_media ) + list( self._collected_media ) )
        
    
    def DeletePending( self, service_key ):
        
        for media in self._collected_media: media.DeletePending( service_key )
        
    
    def GenerateMediaResults( self, has_location = None, discriminant = None, selected_media = None, unrated = None, for_media_viewer = False ):
        
        media_results = []
        
        for media in self._sorted_media:
            
            if has_location is not None:
                
                locations_manager = media.GetLocationsManager()
                
                if has_location not in locations_manager.GetCurrent():
                    
                    continue
                    
                
            
            if selected_media is not None and media not in selected_media: continue
            
            if media.IsCollection(): media_results.extend( media.GenerateMediaResults( has_location = has_location, discriminant = discriminant, selected_media = selected_media, unrated = unrated, for_media_viewer = True ) )
            else:
                
                if discriminant is not None:
                    
                    locations_manager = media.GetLocationsManager()
                    
                    inbox_failed = discriminant == CC.DISCRIMINANT_INBOX and not media.HasInbox()
                    local_failed = discriminant == CC.DISCRIMINANT_LOCAL and not locations_manager.HasLocal()
                    not_local_failed = discriminant == CC.DISCRIMINANT_NOT_LOCAL and locations_manager.HasLocal()
                    downloading_failed = discriminant == CC.DISCRIMINANT_DOWNLOADING and CC.LOCAL_FILE_SERVICE_KEY not in locations_manager.GetPending()
                    
                    if inbox_failed or local_failed or not_local_failed or downloading_failed: continue
                    
                
                if unrated is not None:
                    
                    ( local_ratings, remote_ratings ) = media.GetRatings()
                    
                    if local_ratings.GetRating( unrated ) is not None: continue
                    
                
                if for_media_viewer:
                    
                    if HC.options[ 'mime_media_viewer_actions' ][ media.GetMime() ] == CC.MEDIA_VIEWER_DO_NOT_SHOW:
                        
                        continue
                        
                    
                
                media_results.append( media.GetMediaResult() )
                
            
        
        return media_results
        
    
    def GetFlatMedia( self ):
        
        flat_media = []
        
        for media in self._sorted_media:
            
            if media.IsCollection(): flat_media.extend( media.GetFlatMedia() )
            else: flat_media.append( media )
            
        
        return flat_media
        
    
    def GetMediaIndex( self, media ): return self._sorted_media.index( media )
    
    def GetSortedMedia( self ): return self._sorted_media
    
    def HasMedia( self, media ):
        
        if media is None: return False
        
        if media in self._singleton_media: return True
        elif media in self._collected_media: return True
        else:
            
            for media_collection in self._collected_media:
                
                if media_collection.HasMedia( media ): return True
                
            
        
        return False
        
    
    def HasNoMedia( self ): return len( self._sorted_media ) == 0
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        hashes = content_update.GetHashes()
        
        for media in self._GetMedia( hashes, 'collections' ): media.ProcessContentUpdate( service_key, content_update )
        
        if data_type == HC.CONTENT_TYPE_FILES:
            
            if action == HC.CONTENT_UPDATE_DELETE:
                
                local_service_keys = ( CC.TRASH_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY )
                
                deleted_from_trash_and_local_view = service_key == CC.TRASH_SERVICE_KEY and self._file_service_key in local_service_keys
                
                deleted_from_local_and_option_set = HC.options[ 'remove_trashed_files' ] and service_key == CC.LOCAL_FILE_SERVICE_KEY and self._file_service_key in local_service_keys
                
                deleted_from_repo_and_repo_view = service_key not in local_service_keys and self._file_service_key == service_key
                
                if deleted_from_trash_and_local_view or deleted_from_local_and_option_set or deleted_from_repo_and_repo_view:
                    
                    affected_singleton_media = self._GetMedia( hashes, 'singletons' )
                    affected_collected_media = [ media for media in self._collected_media if media.HasNoMedia() ]
                    
                    self._RemoveMedia( affected_singleton_media, affected_collected_media )
                    
                
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            for content_update in content_updates: self.ProcessContentUpdate( service_key, content_update )
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action == HC.SERVICE_UPDATE_DELETE_PENDING: self.DeletePending( service_key )
                elif action == HC.SERVICE_UPDATE_RESET: self.ResetService( service_key )
                
            
        
    
    def ResetService( self, service_key ):
        
        if service_key == self._file_service_key: self._RemoveMedia( self._singleton_media, self._collected_media )
        else:
            
            for media in self._collected_media: media.ResetService( service_key )
            
        
    
    def Sort( self, sort_by = None ):
        
        for media in self._collected_media: media.Sort( sort_by )
        
        if sort_by is None: sort_by = self._sort_by
        
        self._sort_by = sort_by
        
        ( sort_by_type, sort_by_data ) = sort_by
        
        def deal_with_none( x ):
            
            if x == None: return -1
            else: return x
            
        
        if sort_by_type == 'system':
            
            if sort_by_data == CC.SORT_BY_RANDOM: sort_function = lambda x: random.random()
            elif sort_by_data == CC.SORT_BY_SMALLEST: sort_function = lambda x: deal_with_none( x.GetSize() )
            elif sort_by_data == CC.SORT_BY_LARGEST: sort_function = lambda x: -deal_with_none( x.GetSize() )
            elif sort_by_data == CC.SORT_BY_SHORTEST: sort_function = lambda x: deal_with_none( x.GetDuration() )
            elif sort_by_data == CC.SORT_BY_LONGEST: sort_function = lambda x: -deal_with_none( x.GetDuration() )
            elif sort_by_data == CC.SORT_BY_OLDEST: sort_function = lambda x: deal_with_none( x.GetTimestamp() )
            elif sort_by_data == CC.SORT_BY_NEWEST: sort_function = lambda x: -deal_with_none( x.GetTimestamp() )
            elif sort_by_data == CC.SORT_BY_MIME: sort_function = lambda x: x.GetMime()
            
        elif sort_by_type == 'namespaces':
            
            def namespace_sort_function( namespaces, x ):
                
                x_tags_manager = x.GetTagsManager()
                
                return [ x_tags_manager.GetComparableNamespaceSlice( ( namespace, ), collapse_siblings = True ) for namespace in namespaces ]
                
            
            sort_function = lambda x: namespace_sort_function( sort_by_data, x )
            
        elif sort_by_type in ( 'rating_descend', 'rating_ascend' ):
            
            service_key = sort_by_data
            
            def ratings_sort_function( service_key, reverse, x ):
                
                ( x_local_ratings, x_remote_ratings ) = x.GetRatings()
                
                service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
                
                if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): rating = deal_with_none( x_local_ratings.GetRating( service_key ) )
                else: rating = deal_with_none( x_remote_ratings.GetScore( service_key ) )
                
                if reverse: rating *= -1
                
                return rating
                
            
            reverse = sort_by_type == 'rating_descend'
            
            sort_function = lambda x: ratings_sort_function( service_key, reverse, x )
            
        
        self._sorted_media.sort( sort_function )
        
    
class ListeningMediaList( MediaList ):
    
    def __init__( self, file_service_key, media_results ):
        
        MediaList.__init__( self, file_service_key, media_results )
        
        self._file_query_result = ClientData.FileQueryResult( media_results )
        
        HydrusGlobals.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HydrusGlobals.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
    
    def AddMediaResults( self, media_results, append = True ):
        
        self._file_query_result.AddMediaResults( media_results )
        
        existing_hashes = self._GetHashes()
        
        new_media = []
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            if hash in existing_hashes: continue
            
            new_media.append( self._GenerateMediaSingleton( media_result ) )
            
        
        if append:
            
            self._singleton_media.update( new_media )
            self._sorted_media.append_items( new_media )
            
        else:
            
            if self._collect_by is not None:
                
                keys_to_medias = self._CalculateCollectionKeysToMedias( self._collect_by, new_media )
                
                new_media = []
                
                for ( key, medias ) in keys_to_medias.items():
                    
                    if key in self._collect_map_singletons:
                        
                        singleton_media = self._collect_map_singletons[ key ]
                        
                        self._sorted_media.remove_items( singleton_media )
                        self._singleton_media.discard( singleton_media )
                        del self._collect_map_singletons[ key ]
                        
                        medias.append( singleton_media )
                        
                        collected_media = self._GenerateMediaCollection( [ media.GetMediaResult() for media in medias ] )
                        
                        collected_media.Sort( self._sort_by )
                        
                        self._collected_media.add( collected_media )
                        self._collect_map_collected[ key ] = collected_media
                        
                        new_media.append( collected_media )
                        
                    elif key in self._collect_map_collected:
                        
                        collected_media = self._collect_map_collected[ key ]
                        
                        self._sorted_media.remove_items( collected_media )
                        
                        # mediacollection needs addmediaresult with efficient recalcinternals
                        collected_media.MagicalAddMediasOrMediaResultsWhatever( medias )
                        
                        collected_media.Sort( self._sort_by )
                        
                        new_media.append( collected_media )
                        
                    elif len( medias ) == 1:
                        
                        ( singleton_media, ) = medias
                        
                        self._singleton_media.add( singleton_media )
                        self._collect_map_singletons[ key ] = singleton_media
                        
                    else:
                        
                        collected_media = self._GenerateMediaCollection( [ media.GetMediaResult() for media in medias ] )
                        
                        collected_media.Sort( self._sort_by )
                        
                        self._collected_media.add( collected_media )
                        self._collect_map_collected[ key ] = collected_media
                        
                        new_media.append( collected_media )
                        
                    
                
            
            self._sorted_media.insert_items( new_media )
            
        
        return new_media
        
    
class MediaCollection( MediaList, Media ):
    
    def __init__( self, file_service_key, media_results ):
        
        Media.__init__( self )
        MediaList.__init__( self, file_service_key, media_results )
        
        self._hashes = set()
        
        self._archive = True
        self._inbox = False
        
        self._size = 0
        self._size_definite = True
        
        self._timestamp = 0
        
        self._width = None
        self._height = None
        self._duration = None
        self._num_frames = None
        self._num_words = None
        self._tags_manager = None
        self._locations_manager = None
        
        self._RecalcInternals()
        
    
    #def __hash__( self ): return frozenset( self._hashes ).__hash__()
    
    def _RecalcInternals( self ):
        
        self._hashes = set()
        
        for media in self._sorted_media: self._hashes.update( media.GetHashes() )
        
        self._archive = True in ( media.HasArchive() for media in self._sorted_media )
        self._inbox = True in ( media.HasInbox() for media in self._sorted_media )
        
        self._size = sum( [ media.GetSize() for media in self._sorted_media ] )
        self._size_definite = not False in ( media.IsSizeDefinite() for media in self._sorted_media )
        
        if len( self._sorted_media ) == 0: self._timestamp = 0
        else: self._timestamp = max( [ media.GetTimestamp() for media in self._sorted_media ] )
        
        duration_sum = sum( [ media.GetDuration() for media in self._sorted_media if media.HasDuration() ] )
        
        if duration_sum > 0: self._duration = duration_sum
        else: self._duration = None
        
        tags_managers = [ m.GetTagsManager() for m in self._sorted_media ]
        
        self._tags_manager = MergeTagsManagers( tags_managers )
        
        # horrible compromise
        if len( self._sorted_media ) > 0: self._ratings = self._sorted_media[0].GetRatings()
        else: self._ratings = ( ClientRatings.LocalRatingsManager( {} ), ClientRatings.CPRemoteRatingsServiceKeys( {} ) )
        
        all_locations_managers = [ media.GetLocationsManager() for media in self._sorted_media ]
        
        current = HydrusData.IntelligentMassIntersect( [ locations_manager.GetCurrent() for locations_manager in all_locations_managers ] )
        deleted = HydrusData.IntelligentMassIntersect( [ locations_manager.GetDeleted() for locations_manager in all_locations_managers ] )
        pending = HydrusData.IntelligentMassIntersect( [ locations_manager.GetPending() for locations_manager in all_locations_managers ] )
        petitioned = HydrusData.IntelligentMassIntersect( [ locations_manager.GetPetitioned() for locations_manager in all_locations_managers ] )
        
        self._locations_manager = LocationsManager( current, deleted, pending, petitioned )
        
    
    def DeletePending( self, service_key ):
        
        MediaList.DeletePending( self, service_key )
        
        self._RecalcInternals()
        
    
    def GetDisplayMedia( self ): return self._GetFirst().GetDisplayMedia()
    
    def GetDuration( self ): return self._duration
    
    def GetHash( self ): return self.GetDisplayMedia().GetHash()
    
    def GetHashes( self, has_location = None, discriminant = None, not_uploaded_to = None, ordered = False ):
        
        if has_location is None and discriminant is None and not_uploaded_to is None and not ordered: return self._hashes
        else:
            
            if ordered:
                
                result = []
                
                for media in self._sorted_media: result.extend( media.GetHashes( has_location, discriminant, not_uploaded_to, ordered ) )
                
            else:
                
                result = set()
                
                for media in self._sorted_media: result.update( media.GetHashes( has_location, discriminant, not_uploaded_to, ordered ) )
                
            
            return result
            
        
    
    def GetLocationsManager( self ): return self._locations_manager
    
    def GetMime( self ): return HC.APPLICATION_HYDRUS_CLIENT_COLLECTION
    
    def GetNumFiles( self ): return len( self._hashes )
    
    def GetNumInbox( self ): return sum( ( media.GetNumInbox() for media in self._sorted_media ) )
    
    def GetNumFrames( self ): return sum( ( media.GetNumFrames() for media in self._sorted_media ) )
    
    def GetNumWords( self ): return sum( ( media.GetNumWords() for media in self._sorted_media ) )
    
    def GetPrettyAge( self ): return 'imported ' + HydrusData.ConvertTimestampToPrettyAgo( self._timestamp )
    
    def GetPrettyInfo( self ):
        
        size = HydrusData.ConvertIntToBytes( self._size )
        
        mime = HC.mime_string_lookup[ HC.APPLICATION_HYDRUS_CLIENT_COLLECTION ]
        
        info_string = size + ' ' + mime
        
        info_string += ' (' + HydrusData.ConvertIntToPrettyString( self.GetNumFiles() ) + ' files)'
        
        return info_string
        
    
    def GetRatings( self ): return self._ratings
    
    def GetResolution( self ): return ( self._width, self._height )
    
    def GetSingletonsTagsManagers( self ):
        
        tags_managers = [ m.GetTagsManager() for m in self._singleton_media ] 
        
        for m in self._collected_media: tags_managers.extend( m.GetSingletonsTagsManagers() )
        
        return tags_managers
        
    
    def GetSize( self ): return self._size
    
    def GetTagsManager( self ): return self._tags_manager
    
    def GetTimestamp( self ): return self._timestamp
    
    def HasArchive( self ): return self._archive
    
    def HasDuration( self ): return self._duration is not None
    
    def HasImages( self ): return True in ( media.HasImages() for media in self._collected_media | self._singleton_media )
    
    def HasInbox( self ): return self._inbox
    
    def IsCollection( self ): return True
    
    def IsImage( self ): return False
    
    def IsNoisy( self ): return self.GetDisplayMedia().GetMime() in HC.NOISY_MIMES
    
    def IsSizeDefinite( self ): return self._size_definite
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        MediaList.ProcessContentUpdate( self, service_key, content_update )
        
        self._RecalcInternals()
        
    
    def ResetService( self, service_key ):
        
        MediaList.ResetService( self, service_key )
        
        self._RecalcInternals()
        
    
class MediaSingleton( Media ):
    
    def __init__( self, media_result ):
        
        Media.__init__( self )
        
        self._media_result = media_result
        
    
    def GetDisplayMedia( self ): return self
    
    def GetDuration( self ): return self._media_result.GetDuration()
    
    def GetHash( self ): return self._media_result.GetHash()
    
    def GetHashes( self, has_location = None, discriminant = None, not_uploaded_to = None, ordered = False ):
        
        if ordered:
            
            no_result = []
            
        else:
            
            no_result = set()
            
        
        locations_manager = self._media_result.GetLocationsManager()
        
        if discriminant is not None:
            
            inbox = self._media_result.GetInbox()
            
            if ( discriminant == CC.DISCRIMINANT_INBOX and not inbox ) or ( discriminant == CC.DISCRIMINANT_ARCHIVE and inbox ) or ( discriminant == CC.DISCRIMINANT_LOCAL and not locations_manager.HasLocal() ) or ( discriminant == CC.DISCRIMINANT_NOT_LOCAL and locations_manager.HasLocal() ): return no_result
            
        
        if has_location is not None:
            
            if has_location not in locations_manager.GetCurrent(): return no_result
            
        
        if not_uploaded_to is not None:
            
            if not_uploaded_to in locations_manager.GetCurrentRemote(): return no_result
            
        
        if ordered:
            
            return [ self._media_result.GetHash() ]
            
        else:
            
            return { self._media_result.GetHash() }
            
        
    
    def GetLocationsManager( self ): return self._media_result.GetLocationsManager()
    
    def GetMediaResult( self ): return self._media_result
    
    def GetMime( self ): return self._media_result.GetMime()
    
    def GetNumFiles( self ): return 1
    
    def GetNumFrames( self ): return self._media_result.GetNumFrames()
    
    def GetNumInbox( self ):
        
        if self.HasInbox(): return 1
        else: return 0
        
    
    def GetNumWords( self ): return self._media_result.GetNumWords()
    
    def GetTimestamp( self ):
        
        timestamp = self._media_result.GetTimestamp()
        
        if timestamp is None: return 0
        else: return timestamp
        
    
    def GetPrettyAge( self ): return 'imported ' + HydrusData.ConvertTimestampToPrettyAgo( self._media_result.GetTimestamp() )
    
    def GetPrettyInfo( self ):
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings ) = self._media_result.ToTuple()
        
        info_string = HydrusData.ConvertIntToBytes( size ) + ' ' + HC.mime_string_lookup[ mime ]
        
        if width is not None and height is not None: info_string += ' (' + HydrusData.ConvertIntToPrettyString( width ) + 'x' + HydrusData.ConvertIntToPrettyString( height ) + ')'
        
        if duration is not None: info_string += ', ' + HydrusData.ConvertMillisecondsToPrettyTime( duration )
        
        if num_frames is not None: info_string += ' (' + HydrusData.ConvertIntToPrettyString( num_frames ) + ' frames)'
        
        if num_words is not None: info_string += ' (' + HydrusData.ConvertIntToPrettyString( num_words ) + ' words)'
        
        return info_string
        
    
    def GetRatings( self ): return self._media_result.GetRatings()
    
    def GetResolution( self ):
        
        ( width, height ) = self._media_result.GetResolution()
        
        if width is None: return ( 0, 0 )
        else: return ( width, height )
        
    
    def GetSize( self ):
        
        size = self._media_result.GetSize()
        
        if size is None: return 0
        else: return size
        
    
    def GetTagsManager( self ): return self._media_result.GetTagsManager()
    
    def GetTitleString( self ):
        
        title_string = ''
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        namespaces = self._media_result.GetTagsManager().GetCombinedNamespaces( ( 'creator', 'series', 'title', 'volume', 'chapter', 'page' ) )
        
        creators = namespaces[ 'creator' ]
        series = namespaces[ 'series' ]
        titles = namespaces[ 'title' ]
        volumes = namespaces[ 'volume' ]
        chapters = namespaces[ 'chapter' ]
        pages = namespaces[ 'page' ]
        
        if len( creators ) > 0:
            
            creators = siblings_manager.CollapseNamespacedTags( 'creator', creators )
            
            title_string_append = ', '.join( creators )
            
            if len( title_string ) > 0: title_string += ' - ' + title_string_append
            else: title_string = title_string_append
            
        
        if len( series ) > 0:
            
            series = siblings_manager.CollapseNamespacedTags( 'series', series )
            
            title_string_append = ', '.join( series )
            
            if len( title_string ) > 0: title_string += ' - ' + title_string_append
            else: title_string = title_string_append
            
        
        if len( titles ) > 0:
            
            titles = siblings_manager.CollapseNamespacedTags( 'title', titles )
            
            title_string_append = ', '.join( titles )
            
            if len( title_string ) > 0: title_string += ' - ' + title_string_append
            else: title_string = title_string_append
            
        
        if len( volumes ) > 0:
            
            if len( volumes ) == 1:
                
                ( volume, ) = volumes
                
                title_string_append = 'volume ' + str( volume )
                
            else:
                
                volumes_sorted = HydrusTags.SortTags( volumes )
                
                title_string_append = 'volumes ' + str( volumes_sorted[0] ) + '-' + str( volumes_sorted[-1] )
                
            
            if len( title_string ) > 0: title_string += ' - ' + title_string_append
            else: title_string = title_string_append
            
        
        if len( chapters ) > 0:
            
            if len( chapters ) == 1:
                
                ( chapter, ) = chapters
                
                title_string_append = 'chapter ' + str( chapter )
                
            else:
                
                chapters_sorted = HydrusTags.SortTags( chapters )
                
                title_string_append = 'chapters ' + str( chapters_sorted[0] ) + '-' + str( chapters_sorted[-1] )
                
            
            if len( title_string ) > 0: title_string += ' - ' + title_string_append
            else: title_string = title_string_append
            
        
        if len( pages ) > 0:
            
            if len( pages ) == 1:
                
                ( page, ) = pages
                
                title_string_append = 'page ' + str( page )
                
            else:
                
                pages_sorted = HydrusTags.SortTags( pages )
                
                title_string_append = 'pages ' + str( pages_sorted[0] ) + '-' + str( pages_sorted[-1] )
                
            
            if len( title_string ) > 0: title_string += ' - ' + title_string_append
            else: title_string = title_string_append
            
        
        return title_string
        
    
    def HasArchive( self ): return not self._media_result.GetInbox()
    
    def HasDuration( self ): return self._media_result.GetDuration() is not None and self._media_result.GetNumFrames() > 1
    
    def HasImages( self ): return self.IsImage()
    
    def HasInbox( self ): return self._media_result.GetInbox()
    
    def IsCollection( self ): return False
    
    def IsImage( self ): return self._media_result.GetMime() in HC.IMAGES
    
    def IsNoisy( self ): return self._media_result.GetMime() in HC.NOISY_MIMES
    
    def IsSizeDefinite( self ): return self._media_result.GetSize() is not None

class MediaResult( object ):
    
    def __init__( self, tuple ):
        
        # hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings
        
        self._tuple = tuple
        
    
    def DeletePending( self, service_key ):
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings ) = self._tuple
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        service_type = service.GetServiceType()
        
        if service_type == HC.TAG_REPOSITORY: tags_manager.DeletePending( service_key )
        elif service_type in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ): locations_manager.DeletePending( service_key )
        
    
    def GetHash( self ): return self._tuple[0]
    
    def GetDuration( self ): return self._tuple[7]
    
    def GetInbox( self ): return self._tuple[1]
    
    def GetLocationsManager( self ): return self._tuple[11]
    
    def GetMime( self ): return self._tuple[3]
    
    def GetNumFrames( self ): return self._tuple[8]
    
    def GetNumWords( self ): return self._tuple[9]
    
    def GetRatings( self ): return ( self._tuple[12], self._tuple[13] )
    
    def GetResolution( self ): return ( self._tuple[5], self._tuple[6] )
    
    def GetSize( self ): return self._tuple[2]
    
    def GetTagsManager( self ): return self._tuple[10]
    
    def GetTimestamp( self ): return self._tuple[4]
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings ) = self._tuple
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        service_type = service.GetServiceType()
        
        if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ): tags_manager.ProcessContentUpdate( service_key, content_update )
        elif service_type in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ):
            
            if service_type == HC.LOCAL_FILE:
                
                if action == HC.CONTENT_UPDATE_ARCHIVE: inbox = False
                elif action == HC.CONTENT_UPDATE_INBOX: inbox = True
                
                if service_key == CC.LOCAL_FILE_SERVICE_KEY:
                    
                    if action == HC.CONTENT_UPDATE_ADD and CC.TRASH_SERVICE_KEY not in locations_manager.GetCurrent():
                        
                        inbox = True
                        
                    
                elif service_key == CC.TRASH_SERVICE_KEY:
                    
                    if action == HC.CONTENT_UPDATE_DELETE:
                        
                        inbox = False
                        
                    
                
                self._tuple = ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings )
                
            
            locations_manager.ProcessContentUpdate( service_key, content_update )
            
        elif service_type in HC.RATINGS_SERVICES:
            
            if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): local_ratings.ProcessContentUpdate( service_key, content_update )
            else: remote_ratings.ProcessContentUpdate( service_key, content_update )
            
        
    
    def ResetService( self, service_key ):
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings ) = self._tuple
        
        tags_manager.ResetService( service_key )
        locations_manager.ResetService( service_key )
        
    
    def ToTuple( self ): return self._tuple

class SortedList( object ):
    
    def __init__( self, initial_items = None, sort_function = None ):
        
        if initial_items is None: initial_items = []
        
        do_sort = sort_function is not None
        
        if sort_function is None: sort_function = lambda x: x
        
        self._sort_function = sort_function
        
        self._sorted_list = list( initial_items )
        
        self._items_to_indices = None
        
        if do_sort: self.sort()
        
    
    def __contains__( self, item ): return self._items_to_indices.__contains__( item )
    
    def __getitem__( self, value ): return self._sorted_list.__getitem__( value )
    
    def __iter__( self ):
        
        for item in self._sorted_list: yield item
        
    
    def __len__( self ): return self._sorted_list.__len__()
    
    def _DirtyIndices( self ): self._items_to_indices = None
    
    def _RecalcIndices( self ): self._items_to_indices = { item : index for ( index, item ) in enumerate( self._sorted_list ) }
    
    def append_items( self, items ):
        
        self._sorted_list.extend( items )
        
        self._DirtyIndices()
        
    
    def index( self, item ):
        
        if self._items_to_indices is None: self._RecalcIndices()
        
        try:
            
            result = self._items_to_indices[ item ]
            
        except KeyError:
            
            raise HydrusExceptions.NotFoundException()
            
        
        return result
        
    
    def insert_items( self, items ):
        
        self.append_items( items )
        
        self.sort()
        
    
    def remove_items( self, items ):
        
        deletee_indices = [ self.index( item ) for item in items ]
        
        deletee_indices.sort()
        
        deletee_indices.reverse()
        
        for index in deletee_indices: del self._sorted_list[ index ]
        
        self._DirtyIndices()
        
    
    def sort( self, f = None ):
        
        if f is not None: self._sort_function = f
        
        self._sorted_list.sort( key = f )
        
        self._DirtyIndices()
        
    
class TagsManagerSimple( object ):
    
    def __init__( self, service_keys_to_statuses_to_tags ):
        
        tag_censorship_manager = HydrusGlobals.client_controller.GetManager( 'tag_censorship' )
        
        service_keys_to_statuses_to_tags = tag_censorship_manager.FilterServiceKeysToStatusesToTags( service_keys_to_statuses_to_tags )
        
        self._service_keys_to_statuses_to_tags = service_keys_to_statuses_to_tags
        
        self._combined_namespaces_cache = None
        
    
    def GetCombinedNamespaces( self, namespaces ):
        
        if self._combined_namespaces_cache is None:
    
            combined_statuses_to_tags = self._service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ]
            
            combined_current = combined_statuses_to_tags[ HC.CURRENT ]
            combined_pending = combined_statuses_to_tags[ HC.PENDING ]
            
            self._combined_namespaces_cache = HydrusData.BuildKeyToSetDict( tag.split( ':', 1 ) for tag in combined_current.union( combined_pending ) if ':' in tag )
            
        
        result = { namespace : self._combined_namespaces_cache[ namespace ] for namespace in namespaces }
        
        return result
        
    
    def GetComparableNamespaceSlice( self, namespaces, collapse_siblings = False ):
        
        combined_statuses_to_tags = self._service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ]
        
        combined_current = combined_statuses_to_tags[ HC.CURRENT ]
        combined_pending = combined_statuses_to_tags[ HC.PENDING ]
        
        combined = combined_current.union( combined_pending )
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        slice = []
        
        for namespace in namespaces:
            
            tags = [ tag for tag in combined if tag.startswith( namespace + ':' ) ]
            
            if collapse_siblings: tags = list( siblings_manager.CollapseTags( tags ) )
            
            tags = [ tag.split( ':', 1 )[1] for tag in tags ]
            
            tags = HydrusTags.SortTags( tags )
            
            tags = tuple( ( HydrusTags.ConvertTagToSortable( tag ) for tag in tags ) )
            
            slice.append( tags )
            
        
        return tuple( slice )
        
    
    def GetNamespaceSlice( self, namespaces, collapse_siblings = False ):
        
        combined_statuses_to_tags = self._service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ]
        
        combined_current = combined_statuses_to_tags[ HC.CURRENT ]
        combined_pending = combined_statuses_to_tags[ HC.PENDING ]
        
        slice = { tag for tag in combined_current.union( combined_pending ) if True in ( tag.startswith( namespace + ':' ) for namespace in namespaces ) }
        
        if collapse_siblings:
            
            siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
            
            slice = siblings_manager.CollapseTags( slice )
            
        
        slice = frozenset( slice )
        
        return slice
        
    
class TagsManager( TagsManagerSimple ):
    
    def __init__( self, service_keys_to_statuses_to_tags ):
        
        TagsManagerSimple.__init__( self, service_keys_to_statuses_to_tags )
        
        self._RecalcCombined()
        
    
    def _RecalcCombined( self ):
        
        combined_statuses_to_tags = collections.defaultdict( set )
        
        for ( service_key, statuses_to_tags ) in self._service_keys_to_statuses_to_tags.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY: continue
            
            combined_statuses_to_tags[ HC.CURRENT ].update( statuses_to_tags[ HC.CURRENT ] )
            combined_statuses_to_tags[ HC.PENDING ].update( statuses_to_tags[ HC.PENDING ] )
            combined_statuses_to_tags[ HC.PETITIONED ].update( statuses_to_tags[ HC.PETITIONED ] )
            combined_statuses_to_tags[ HC.DELETED ].update( statuses_to_tags[ HC.DELETED ] )
            
        
        self._service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_statuses_to_tags
        
        self._combined_namespaces_cache = None
        
    
    def DeletePending( self, service_key ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        if len( statuses_to_tags[ HC.PENDING ] ) + len( statuses_to_tags[ HC.PETITIONED ] ) > 0:
            
            statuses_to_tags[ HC.PENDING ] = set()
            statuses_to_tags[ HC.PETITIONED ] = set()
            
            self._RecalcCombined()
            
        
    
    def GetCurrent( self, service_key = CC.COMBINED_TAG_SERVICE_KEY ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        return set( statuses_to_tags[ HC.CURRENT ] )
        
    
    def GetDeleted( self, service_key = CC.COMBINED_TAG_SERVICE_KEY ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        return set( statuses_to_tags[ HC.DELETED ] )
        
    
    def GetNumTags( self, service_key, include_current_tags = True, include_pending_tags = False ):
        
        num_tags = 0
        
        statuses_to_tags = self.GetStatusesToTags( service_key )
        
        if include_current_tags: num_tags += len( statuses_to_tags[ HC.CURRENT ] )
        if include_pending_tags: num_tags += len( statuses_to_tags[ HC.PENDING ] )
        
        return num_tags
        
    
    def GetPending( self, service_key = CC.COMBINED_TAG_SERVICE_KEY ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        return set( statuses_to_tags[ HC.PENDING ] )
        
    
    def GetPetitioned( self, service_key = CC.COMBINED_TAG_SERVICE_KEY ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        return set( statuses_to_tags[ HC.PETITIONED ] )
        
    
    def GetServiceKeysToStatusesToTags( self ): return self._service_keys_to_statuses_to_tags
    
    def GetStatusesToTags( self, service_key ): return self._service_keys_to_statuses_to_tags[ service_key ]
    
    def HasTag( self, tag ):
        
        combined_statuses_to_tags = self._service_keys_to_statuses_to_tags[ CC.COMBINED_TAG_SERVICE_KEY ]
        
        return tag in combined_statuses_to_tags[ HC.CURRENT ] or tag in combined_statuses_to_tags[ HC.PENDING ]
        
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_PETITION: ( tag, hashes, reason ) = row
        else: ( tag, hashes ) = row
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            statuses_to_tags[ HC.CURRENT ].add( tag )
            
            statuses_to_tags[ HC.DELETED ].discard( tag )
            statuses_to_tags[ HC.PENDING ].discard( tag )
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            statuses_to_tags[ HC.DELETED ].add( tag )
            
            statuses_to_tags[ HC.CURRENT ].discard( tag )
            statuses_to_tags[ HC.PETITIONED ].discard( tag )
            
        elif action == HC.CONTENT_UPDATE_PEND: statuses_to_tags[ HC.PENDING ].add( tag )
        elif action == HC.CONTENT_UPDATE_RESCIND_PEND: statuses_to_tags[ HC.PENDING ].discard( tag )
        elif action == HC.CONTENT_UPDATE_PETITION: statuses_to_tags[ HC.PETITIONED ].add( tag )
        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION: statuses_to_tags[ HC.PETITIONED ].discard( tag )
        
        self._RecalcCombined()
        
    
    def ResetService( self, service_key ):
        
        if service_key in self._service_keys_to_statuses_to_tags:
            
            del self._service_keys_to_statuses_to_tags[ service_key ]
            
            self._RecalcCombined()
            
        
    