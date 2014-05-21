import bisect
import collections
import ClientConstants as CC
import HydrusConstants as HC
import HydrusTags
import os
import random
import time
import traceback
import wx

class Media():
    
    def __init__( self ):
        
        self._id = os.urandom( 32 )
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._id.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
class MediaList():
    
    def __init__( self, file_service_identifier, media_results ):
        
        self._file_service_identifier = file_service_identifier
        
        self._sort_by = CC.SORT_BY_SMALLEST
        self._collect_by = None
        
        self._collect_map_singletons = {}
        self._collect_map_collected = {}
        
        self._sorted_media = HC.SortedList( [ self._GenerateMediaSingleton( media_result ) for media_result in media_results ] )
        
        self._singleton_media = set( self._sorted_media )
        self._collected_media = set()
        
    
    def _CalculateCollectionKeysToMedias( self, collect_by, medias ):
    
        namespaces_to_collect_by = [ data for ( collect_by_type, data ) in collect_by if collect_by_type == 'namespace' ]
        ratings_to_collect_by = [ data for ( collect_by_type, data ) in collect_by if collect_by_type == 'rating' ]
        
        local_ratings_to_collect_by = [ service_identifier for service_identifier in ratings_to_collect_by if service_identifier.GetType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
        remote_ratings_to_collect_by = [ service_identifier for service_identifier in ratings_to_collect_by if service_identifier.GetType() in ( HC.RATING_LIKE_REPOSITORY, HC.RATING_NUMERICAL_REPOSITORY ) ]
        
        keys_to_medias = collections.defaultdict( list )
        
        for media in medias:
            
            if len( namespaces_to_collect_by ) > 0: namespace_key = media.GetTagsManager().GetNamespaceSlice( namespaces_to_collect_by )
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
        
    
    def _GenerateMediaCollection( self, media_results ): return MediaCollection( self._file_service_identifier, media_results )
    
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
            
        
        self._sorted_media = HC.SortedList( list( self._singleton_media ) + list( self._collected_media ) )
        
    
    def DeletePending( self, service_identifier ):
        
        for media in self._collected_media: media.DeletePending( service_identifier )
        
    
    def GenerateMediaResults( self, discriminant = None, selected_media = None, unrated = None ):
        
        media_results = []
        
        for media in self._sorted_media:
            
            if selected_media is not None and media not in selected_media: continue
            
            if media.IsCollection(): media_results.extend( media.GenerateMediaResults( discriminant ) )
            else:
                
                if discriminant is not None:
                    if ( discriminant == CC.DISCRIMINANT_INBOX and not media.HasInbox() ) or ( discriminant == CC.DISCRIMINANT_LOCAL and not media.GetFileServiceIdentifiersCDPP().HasLocal() ) or ( discriminant == CC.DISCRIMINANT_NOT_LOCAL and media.GetFileServiceIdentifiersCDPP().HasLocal() ): continue
                
                if unrated is not None:
                    
                    ( local_ratings, remote_ratings ) = media.GetRatings()
                    
                    if local_ratings.GetRating( unrated ) is not None: continue
                    
                
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
    
    def ProcessContentUpdate( self, service_identifier, content_update ):
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        hashes = content_update.GetHashes()
        
        for media in self._GetMedia( hashes, 'collections' ): media.ProcessContentUpdate( service_identifier, content_update )
        
        if data_type == HC.CONTENT_DATA_TYPE_FILES:
            
            if action == HC.CONTENT_UPDATE_DELETE and service_identifier == self._file_service_identifier:
                
                affected_singleton_media = self._GetMedia( hashes, 'singletons' )
                affected_collected_media = [ media for media in self._collected_media if media.HasNoMedia() ]
                
                self._RemoveMedia( affected_singleton_media, affected_collected_media )
                
            
        
    
    def ProcessContentUpdates( self, service_identifiers_to_content_updates ):
        
        for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
            
            for content_update in content_updates: self.ProcessContentUpdate( service_identifier, content_update )
            
        
    
    def ProcessServiceUpdates( self, service_identifiers_to_service_updates ):
        
        for ( service_identifier, service_updates ) in service_identifiers_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action == HC.SERVICE_UPDATE_DELETE_PENDING: self.DeletePending( service_identifier )
                elif action == HC.SERVICE_UPDATE_RESET: self.ResetService( service_identifier )
                
            
        
    
    def ResetService( self, service_identifier ):
        
        if service_identifier == self._file_service_identifier: self._RemoveMedia( self._singleton_media, self._collected_media )
        else:
            
            for media in self._collected_media: media.ResetService( service_identifier )
            
        
    
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
                
                return [ x_tags_manager.GetComparableNamespaceSlice( ( namespace, ) ) for namespace in namespaces ]
                
            
            sort_function = lambda x: namespace_sort_function( sort_by_data, x )
            
        elif sort_by_type in ( 'rating_descend', 'rating_ascend' ):
            
            service_identifier = sort_by_data
            
            def ratings_sort_function( service_identifier, reverse, x ):
                
                ( x_local_ratings, x_remote_ratings ) = x.GetRatings()
                
                if service_identifier.GetType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): rating = deal_with_none( x_local_ratings.GetRating( service_identifier ) )
                else: rating = deal_with_none( x_remote_ratings.GetScore( service_identifier ) )
                
                if reverse: rating *= -1
                
                return rating
                
            
            reverse = sort_by_type == 'rating_descend'
            
            sort_function = lambda x: ratings_sort_function( service_identifier, reverse, x )
            
        
        self._sorted_media.sort( sort_function )
        
    
class ListeningMediaList( MediaList ):
    
    def __init__( self, file_service_identifier, media_results ):
        
        MediaList.__init__( self, file_service_identifier, media_results )
        
        self._file_query_result = CC.FileQueryResult( media_results )
        
        HC.pubsub.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HC.pubsub.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
    
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
                
                keys_to_medias = self._CalculateCollectionKeysToMedias( collect_by, new_media )
                
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
    
    def __init__( self, file_service_identifier, media_results ):
        
        Media.__init__( self )
        MediaList.__init__( self, file_service_identifier, media_results )
        
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
        self._file_service_identifiers = None
        
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
        
        t_s_p = HC.app.Read( 'tag_service_precedence' )
        
        self._tags_manager = HydrusTags.MergeTagsManagers( t_s_p, tags_managers )
        
        # horrible compromise
        if len( self._sorted_media ) > 0: self._ratings = self._sorted_media[0].GetRatings()
        else: self._ratings = ( CC.LocalRatings( {} ), CC.CPRemoteRatingsServiceIdentifiers( {} ) )
        
        all_file_service_identifiers = [ media.GetFileServiceIdentifiersCDPP() for media in self._sorted_media ]
        
        current = HC.IntelligentMassIntersect( [ file_service_identifiers.GetCurrent() for file_service_identifiers in all_file_service_identifiers ] )
        deleted = HC.IntelligentMassIntersect( [ file_service_identifiers.GetDeleted() for file_service_identifiers in all_file_service_identifiers ] )
        pending = HC.IntelligentMassIntersect( [ file_service_identifiers.GetPending() for file_service_identifiers in all_file_service_identifiers ] )
        petitioned = HC.IntelligentMassIntersect( [ file_service_identifiers.GetPetitioned() for file_service_identifiers in all_file_service_identifiers ] )
        
        self._file_service_identifiers = CC.CDPPFileServiceIdentifiers( current, deleted, pending, petitioned )
        
    
    def DeletePending( self, service_identifier ):
        
        MediaList.DeletePending( self, service_identifier )
        
        self._RecalcInternals()
        
    
    def GetDisplayMedia( self ): return self._GetFirst().GetDisplayMedia()
    
    def GetDuration( self ): return self._duration
    
    def GetHash( self ): return self.GetDisplayMedia().GetHash()
    
    def GetHashes( self, discriminant = None, not_uploaded_to = None ):
        
        if discriminant is None and not_uploaded_to is None: return self._hashes
        else:
            
            result = set()
            
            for media in self._sorted_media: result.update( media.GetHashes( discriminant, not_uploaded_to ) )
            
            return result
            
        
    
    def GetHashes( self, discriminant = None, not_uploaded_to = None ):
        
        if discriminant is not None:
            if ( discriminant == CC.DISCRIMINANT_INBOX and not self._inbox ) or ( discriminant == CC.DISCRIMINANT_ARCHIVE and not self._archive ) or ( discriminant == CC.DISCRIMINANT_LOCAL and not self.GetFileServiceIdentifiersCDPP().HasLocal() ) or ( discriminant == CC.DISCRIMINANT_NOT_LOCAL and self.GetFileServiceIdentifiersCDPP().HasLocal() ): return set()
        
        if not_uploaded_to is not None:
            if not_uploaded_to in self._file_service_identifiers.GetCurrentRemote(): return set()
        
        return self._hashes
        
    
    def GetFileServiceIdentifiersCDPP( self ): return self._file_service_identifiers
    
    def GetMime( self ): return HC.APPLICATION_HYDRUS_CLIENT_COLLECTION
    
    def GetNumFiles( self ): return len( self._hashes )
    
    def GetNumFrames( self ): return sum( [ media.GetNumFrames() for media in self._sorted_media ] )
    
    def GetNumWords( self ): return sum( [ media.GetNumWords() for media in self._sorted_media ] )
    
    def GetPrettyAge( self ): return 'imported ' + HC.ConvertTimestampToPrettyAgo( self._timestamp )
    
    def GetPrettyInfo( self ):
        
        size = HC.ConvertIntToBytes( self._size )
        
        mime = HC.mime_string_lookup[ HC.APPLICATION_HYDRUS_CLIENT_COLLECTION ]
        
        info_string = size + ' ' + mime
        
        info_string += ' (' + HC.ConvertIntToPrettyString( self.GetNumFiles() ) + ' files)'
        
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
    
    def IsImage( self ): return HC.IsImage( self._mime )
    
    def IsNoisy( self ): return self.GetDisplayMedia().GetMime() in HC.NOISY_MIMES
    
    def IsSizeDefinite( self ): return self._size_definite
    
    def ProcessContentUpdate( self, service_identifier, content_update ):
        
        MediaList.ProcessContentUpdate( self, service_identifier, content_update )
        
        self._RecalcInternals()
        
    
    def ResetService( self, service_identifier ):
        
        MediaList.ResetService( self, service_identifier )
        
        self._RecalcInternals()
        
    
class MediaSingleton( Media ):
    
    def __init__( self, media_result ):
        
        Media.__init__( self )
        
        self._media_result = media_result
        
    
    #def __hash__( self ): return self.GetHash().__hash__()
    
    def GetDisplayMedia( self ): return self
    
    def GetDuration( self ): return self._media_result.GetDuration()
    
    def GetHash( self ): return self._media_result.GetHash()
    
    def GetHashes( self, discriminant = None, not_uploaded_to = None ):
        
        if discriminant is not None:
            
            inbox = self._media_result.GetInbox()
            
            file_service_identifiers = self._media_result.GetFileServiceIdentifiersCDPP()
            
            if ( discriminant == CC.DISCRIMINANT_INBOX and not inbox ) or ( discriminant == CC.DISCRIMINANT_ARCHIVE and inbox ) or ( discriminant == CC.DISCRIMINANT_LOCAL and not file_service_identifiers.HasLocal() ) or ( discriminant == CC.DISCRIMINANT_NOT_LOCAL and file_service_identifiers.HasLocal() ): return set()
            
        
        if not_uploaded_to is not None:
            
            file_service_identifiers = self._media_result.GetFileServiceIdentifiersCDPP()
            
            if not_uploaded_to in file_service_identifiers.GetCurrentRemote(): return set()
            
        
        return { self._media_result.GetHash() }
        
    
    def GetFileServiceIdentifiersCDPP( self ): return self._media_result.GetFileServiceIdentifiersCDPP()
    
    def GetMediaResult( self ): return self._media_result
    
    def GetMime( self ): return self._media_result.GetMime()
    
    def GetNumFiles( self ): return 1
    
    def GetNumFrames( self ): return self._media_result.GetNumFrames()
    
    def GetNumWords( self ): return self._media_result.GetNumWords()
    
    def GetTimestamp( self ):
        
        timestamp = self._media_result.GetTimestamp()
        
        if timestamp is None: return 0
        else: return timestamp
        
    
    def GetPrettyAge( self ): return 'imported ' + HC.ConvertTimestampToPrettyAgo( self._media_result.GetTimestamp() )
    
    def GetPrettyInfo( self ):
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, file_service_identifiers, local_ratings, remote_ratings ) = self._media_result.ToTuple()
        
        info_string = HC.ConvertIntToBytes( size ) + ' ' + HC.mime_string_lookup[ mime ]
        
        if width is not None and height is not None: info_string += ' (' + HC.ConvertIntToPrettyString( width ) + 'x' + HC.ConvertIntToPrettyString( height ) + ')'
        
        if duration is not None: info_string += ', ' + HC.ConvertMillisecondsToPrettyTime( duration )
        
        if num_frames is not None: info_string += ' (' + HC.ConvertIntToPrettyString( num_frames ) + ' frames)'
        
        if num_words is not None: info_string += ' (' + HC.ConvertIntToPrettyString( num_words ) + ' words)'
        
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
    
    def HasArchive( self ): return not self._media_result.GetInbox()
    
    def HasDuration( self ): return self._media_result.GetDuration() is not None and self._media_result.GetNumFrames() > 1
    
    def HasImages( self ): return self.IsImage()
    
    def HasInbox( self ): return self._media_result.GetInbox()
    
    def IsCollection( self ): return False
    
    def IsImage( self ): return HC.IsImage( self._media_result.GetMime() )
    
    def IsNoisy( self ): return self.GetMime() in HC.NOISY_MIMES
    
    def IsSizeDefinite( self ): return self._media_result.GetSize() is not None
    