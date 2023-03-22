import collections
import itertools
import random
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusText
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client import ClientThreading
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

def FilterServiceKeysToContentUpdates( full_service_keys_to_content_updates, hashes ):
    
    filtered_service_keys_to_content_updates = {}
    
    if not isinstance( hashes, set ):
        
        hashes = set( hashes )
        
    
    for ( service_key, full_content_updates ) in full_service_keys_to_content_updates.items():
        
        filtered_content_updates = [ content_update for content_update in full_content_updates if not hashes.isdisjoint( content_update.GetHashes() ) ]
        
        if len( filtered_content_updates ) > 0:
            
            filtered_service_keys_to_content_updates[ service_key ] = filtered_content_updates
            
        
    
    return filtered_service_keys_to_content_updates
    

def FlattenMedia( media_list ):
    
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
    

def GetMediasTagCount( pool, tag_service_key, tag_display_type ):
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection():
            
            tags_managers.extend( media.GetSingletonsTagsManagers() )
            
        else:
            
            tags_managers.append( media.GetTagsManager() )
            
        
    
    return GetTagsManagersTagCount( tags_managers, tag_service_key, tag_display_type )
    

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
    

def FilterAndReportDeleteLockFailures( medias: typing.Collection[ "Media" ] ):
    
    # TODO: update this system with some texts like 'file was archived' so user can know how to fix the situation
    
    deletee_medias = [ media for media in medias if not media.HasDeleteLocked() ]
    
    if len( deletee_medias ) < len( medias ):
        
        locked_medias = [ media for media in medias if media.HasDeleteLocked() ]
        
        ReportDeleteLockFailures( locked_medias )
        
    
    return deletee_medias
    

def ReportDeleteLockFailures( medias: typing.Collection[ "Media" ] ):
    
    job_key = ClientThreading.JobKey()
    
    message = 'Was unable to delete one or more files because of a delete lock!'
    
    job_key.SetStatusText( message )
    
    hashes = list( itertools.chain.from_iterable( ( media.GetHashes() for media in medias ) ) )
    
    job_key.SetFiles( hashes, 'see them' )
    
    HG.client_controller.pub( 'message', job_key )
    

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
        
    
    def GetCurrentTimestamp( self, service_key: bytes ) -> typing.Optional[ int ]:
        
        raise NotImplementedError()
        
    
    def GetDeletedTimestamps( self, service_key: bytes ) -> typing.Tuple[ typing.Optional[ int ], typing.Optional[ int ] ]:
        
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
        
    
    def HasImages( self ) -> bool:
        
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
        s_list.extend( [ HG.client_controller.services_manager.GetName( service_key ) for service_key in self.rating_service_keys if HG.client_controller.services_manager.ServiceExists( service_key ) ] )
        
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
                
                namespace_key = media.GetTagsManager().GetNamespaceSlice( tag_context.service_key, namespaces_to_collect_by, ClientTags.TAG_DISPLAY_ACTUAL )
                
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
        
    
    def _RecalcAfterContentUpdates( self, service_keys_to_content_updates ):
        
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
        
        if media_collect == None:
            
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
            
        
    
    def GetFilteredFileCount( self, file_filter ):
        
        if file_filter.filter_type == FILE_FILTER_ALL:
            
            return self.GetNumFiles()
            
        elif file_filter.filter_type == FILE_FILTER_SELECTED:
            
            return sum( ( m.GetNumFiles() for m in self._selected_media ) )
            
        elif file_filter.filter_type == FILE_FILTER_NOT_SELECTED:
            
            return self.GetNumFiles() - sum( ( m.GetNumFiles() for m in self._selected_media ) )
            
        elif file_filter.filter_type == FILE_FILTER_NONE:
            
            return 0
            
        elif file_filter.filter_type == FILE_FILTER_INBOX:
            
            return sum( ( m.GetNumInbox() for m in self._selected_media ) )
            
        elif file_filter.filter_type == FILE_FILTER_ARCHIVE:
            
            return self.GetNumFiles() - sum( ( m.GetNumInbox() for m in self._selected_media ) )
            
        else:
            
            flat_media = self.GetFlatMedia()
            
            if file_filter.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = file_filter.filter_data
                
                return sum( ( 1 for m in flat_media if file_service_key in m.GetLocationsManager().GetCurrent() ) )
                
            elif file_filter.filter_type == FILE_FILTER_LOCAL:
                
                return sum( ( 1 for m in flat_media if m.GetLocationsManager().IsLocal() ) )
                
            elif file_filter.filter_type == FILE_FILTER_REMOTE:
                
                return sum( ( 1 for m in flat_media if m.GetLocationsManager().IsRemote() ) )
                
            elif file_filter.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = file_filter.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    return sum( ( 1 for m in flat_media if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ) ) ) )
                    
                elif and_or_or == 'OR':
                    
                    return sum( ( 1 for m in flat_media if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), select_tags ) ) )
                    
                
            
        
        return 0
        
    
    def GetFilteredHashes( self, file_filter ):
        
        if file_filter.filter_type == FILE_FILTER_ALL:
            
            return self._hashes
            
        elif file_filter.filter_type == FILE_FILTER_SELECTED:
            
            hashes = set()
            
            for m in self._selected_media:
                
                hashes.update( m.GetHashes() )
                
            
            return hashes
            
        elif file_filter.filter_type == FILE_FILTER_NOT_SELECTED:
            
            hashes = set()
            
            for m in self._sorted_media:
                
                if m not in self._selected_media:
                    
                    hashes.update( m.GetHashes() )
                    
                
            
            return hashes
            
        elif file_filter.filter_type == FILE_FILTER_NONE:
            
            return set()
            
        else:
            
            flat_media = self.GetFlatMedia()
            
            if file_filter.filter_type == FILE_FILTER_INBOX:
                
                filtered_media = [ m for m in flat_media if m.HasInbox() ]
                
            elif file_filter.filter_type == FILE_FILTER_ARCHIVE:
                
                filtered_media = [ m for m in flat_media if not m.HasInbox() ]
                
            elif file_filter.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = file_filter.filter_data
                
                filtered_media = [ m for m in flat_media if file_service_key in m.GetLocationsManager().GetCurrent() ]
                
            elif file_filter.filter_type == FILE_FILTER_LOCAL:
                
                filtered_media = [ m for m in flat_media if m.GetLocationsManager().IsLocal() ]
                
            elif file_filter.filter_type == FILE_FILTER_REMOTE:
                
                filtered_media = [ m for m in flat_media if m.GetLocationsManager().IsRemote() ]
                
            elif file_filter.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = file_filter.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    filtered_media = [ m for m in flat_media if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ) ) ]
                    
                elif and_or_or == 'OR':
                    
                    filtered_media = [ m for m in flat_media if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), select_tags ) ]
                    
                
            
            hashes = { m.GetHash() for m in filtered_media }
            
            return hashes
            
        
        return set()
        
    
    def GetFilteredMedia( self, file_filter ):
        
        if file_filter.filter_type == FILE_FILTER_ALL:
            
            return set( self._sorted_media )
            
        elif file_filter.filter_type == FILE_FILTER_SELECTED:
            
            return self._selected_media
            
        elif file_filter.filter_type == FILE_FILTER_NOT_SELECTED:
            
            return { m for m in self._sorted_media if m not in self._selected_media }
            
        elif file_filter.filter_type == FILE_FILTER_NONE:
            
            return set()
            
        else:
            
            if file_filter.filter_type == FILE_FILTER_INBOX:
                
                filtered_media = { m for m in self._sorted_media if m.HasInbox() }
                
            elif file_filter.filter_type == FILE_FILTER_ARCHIVE:
                
                filtered_media = { m for m in self._sorted_media if not m.HasInbox() }
                
            elif file_filter.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = file_filter.filter_data
                
                filtered_media = { m for m in self._sorted_media if file_service_key in m.GetLocationsManager().GetCurrent() }
                
            elif file_filter.filter_type == FILE_FILTER_LOCAL:
                
                filtered_media = { m for m in self._sorted_media if m.GetLocationsManager().IsLocal() }
                
            elif file_filter.filter_type == FILE_FILTER_REMOTE:
                
                filtered_media = { m for m in self._sorted_media if m.GetLocationsManager().IsRemote() }
                
            elif file_filter.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = file_filter.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    filtered_media = { m for m in self._sorted_media if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ) ) }
                    
                elif and_or_or == 'OR':
                    
                    filtered_media = { m for m in self._sorted_media if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), select_tags ) }
                    
                
            
            return filtered_media
            
        
        return set()
        
    
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
                    
                    new_options = HG.client_controller.new_options
                    
                    ( media_show_action, media_start_paused, media_start_with_embed ) = new_options.GetMediaShowAction( media.GetMime() )
                    
                    if media_show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
                        
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
        
    
    def ProcessContentUpdates( self, full_service_keys_to_content_updates ):
        
        if len( full_service_keys_to_content_updates ) == 0:
            
            return
            
        
        service_keys_to_content_updates = FilterServiceKeysToContentUpdates( full_service_keys_to_content_updates, self._hashes )
        
        if len( service_keys_to_content_updates ) == 0:
            
            return
            
        
        for m in self._collected_media:
            
            m.ProcessContentUpdates( service_keys_to_content_updates )
            
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                hashes = content_update.GetHashes()
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action == HC.CONTENT_UPDATE_DELETE:
                        
                        local_file_domains = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
                        all_local_file_services = set( list( local_file_domains ) + [ CC.COMBINED_LOCAL_FILE_SERVICE_KEY, CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY, CC.TRASH_SERVICE_KEY ] )
                        
                        #
                        
                        physically_deleted = service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                        trashed = service_key in local_file_domains
                        deleted_from_our_domain = self._location_context.IsOneDomain() and service_key in self._location_context.current_service_keys
                        
                        we_are_looking_at_trash = self._location_context.IsOneDomain() and CC.TRASH_SERVICE_KEY in self._location_context.current_service_keys
                        our_view_is_all_local = self._location_context.IncludesCurrent() and not self._location_context.IncludesDeleted() and self._location_context.current_service_keys.issubset( all_local_file_services )
                        
                        # case one, disappeared from hard drive and we are looking at local files
                        physically_deleted_and_local_view = physically_deleted and our_view_is_all_local
                        
                        # case two, disappeared from repo hard drive while we are looking at it
                        deleted_from_repo_and_repo_view = service_key not in all_local_file_services and deleted_from_our_domain
                        
                        # case three, user asked for this to happen
                        user_says_remove_and_trashed_from_non_trash_local_view = HC.options[ 'remove_trashed_files' ] and trashed and not we_are_looking_at_trash
                        
                        if physically_deleted_and_local_view or user_says_remove_and_trashed_from_non_trash_local_view or deleted_from_repo_and_repo_view:
                            
                            self._RemoveMediaByHashes( hashes )
                            
                        
                    
                
            
        
        self._RecalcAfterContentUpdates( service_keys_to_content_updates )
        
    
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
        
        media_sort_fallback = HG.client_controller.new_options.GetFallbackSort()
        
        media_sort_fallback.Sort( self._location_context, self._sorted_media )
        
        # this is a stable sort, so the fallback order above will remain for equal items
        
        self._media_sort.Sort( self._location_context, self._sorted_media )
        
        self._RecalcHashes()
        
    
FILE_FILTER_ALL = 0
FILE_FILTER_NOT_SELECTED = 1
FILE_FILTER_NONE = 2
FILE_FILTER_INBOX = 3
FILE_FILTER_ARCHIVE = 4
FILE_FILTER_FILE_SERVICE = 5
FILE_FILTER_LOCAL = 6
FILE_FILTER_REMOTE = 7
FILE_FILTER_TAGS = 8
FILE_FILTER_SELECTED = 9
FILE_FILTER_MIME = 10

file_filter_str_lookup = {}

file_filter_str_lookup[ FILE_FILTER_ALL ] = 'all'
file_filter_str_lookup[ FILE_FILTER_NOT_SELECTED ] = 'not selected'
file_filter_str_lookup[ FILE_FILTER_SELECTED ] = 'selected'
file_filter_str_lookup[ FILE_FILTER_NONE ] = 'none'
file_filter_str_lookup[ FILE_FILTER_INBOX ] = 'inbox'
file_filter_str_lookup[ FILE_FILTER_ARCHIVE ] = 'archive'
file_filter_str_lookup[ FILE_FILTER_FILE_SERVICE ] = 'file service'
file_filter_str_lookup[ FILE_FILTER_LOCAL ] = 'local'
file_filter_str_lookup[ FILE_FILTER_REMOTE ] = 'not local'
file_filter_str_lookup[ FILE_FILTER_TAGS ] = 'tags'
file_filter_str_lookup[ FILE_FILTER_MIME ] = 'filetype'

class FileFilter( object ):
    
    def __init__( self, filter_type, filter_data = None ):
        
        self.filter_type = filter_type
        self.filter_data = filter_data
        
    
    def __eq__( self, other ):
        
        if isinstance( other, FileFilter ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        if self.filter_data is None:
            
            return self.filter_type.__hash__()
            
        else:
            
            return ( self.filter_type, self.filter_data ).__hash__()
            
        
    
    def PopulateFilterCounts( self, media_list: MediaList, filter_counts: dict ):
        
        if self not in filter_counts:
            
            if self.filter_type == FILE_FILTER_NONE:
                
                filter_counts[ self ] = 0
                
                return
                
            
            quick_inverse_lookups= {}
            
            quick_inverse_lookups[ FileFilter( FILE_FILTER_INBOX ) ] = FileFilter( FILE_FILTER_ARCHIVE )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_ARCHIVE ) ] = FileFilter( FILE_FILTER_INBOX )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_SELECTED ) ] = FileFilter( FILE_FILTER_NOT_SELECTED )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_NOT_SELECTED ) ] = FileFilter( FILE_FILTER_SELECTED )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_LOCAL ) ] = FileFilter( FILE_FILTER_REMOTE )
            quick_inverse_lookups[ FileFilter( FILE_FILTER_REMOTE ) ] = FileFilter( FILE_FILTER_LOCAL )
            
            if self in quick_inverse_lookups:
                
                inverse = quick_inverse_lookups[ self ]
                
                all_filter = FileFilter( FILE_FILTER_ALL )
                
                if all_filter in filter_counts and inverse in filter_counts:
                    
                    filter_counts[ self ] = filter_counts[ all_filter ] - filter_counts[ inverse ]
                    
                    return
                    
                
            
            count = media_list.GetFilteredFileCount( self )
            
            filter_counts[ self ] = count
            
        
    
    def GetCount( self, media_list: MediaList, filter_counts: dict ):
        
        self.PopulateFilterCounts( media_list, filter_counts )
        
        return filter_counts[ self ]
        
    
    def ToString( self, media_list: MediaList, filter_counts: dict ):
        
        if self.filter_type == FILE_FILTER_FILE_SERVICE:
            
            file_service_key = self.filter_data
            
            s = HG.client_controller.services_manager.GetName( file_service_key )
            
        elif self.filter_type == FILE_FILTER_TAGS:
            
            ( tag_service_key, and_or_or, select_tags ) = self.filter_data
            
            s = and_or_or.join( select_tags )
            
            if tag_service_key != CC.COMBINED_TAG_SERVICE_KEY:
                
                s = '{} on {}'.format( s, HG.client_controller.services_manager.GetName( tag_service_key ) )
                
            
            s = HydrusText.ElideText( s, 64 )
            
        elif self.filter_type == FILE_FILTER_MIME:
            
            mime = self.filter_data
            
            s = HC.mime_string_lookup[ mime ]
            
        else:
            
            s = file_filter_str_lookup[ self.filter_type ]
            
        
        self.PopulateFilterCounts( media_list, filter_counts )
        
        my_count = filter_counts[ self ]
        
        s += ' ({})'.format( HydrusData.ToHumanInt( my_count ) )
        
        if self.filter_type == FILE_FILTER_ALL:
            
            inbox_filter = FileFilter( FILE_FILTER_INBOX )
            archive_filter = FileFilter( FILE_FILTER_ARCHIVE )
            
            inbox_filter.PopulateFilterCounts( media_list, filter_counts )
            archive_filter.PopulateFilterCounts( media_list, filter_counts )
            
            inbox_count = filter_counts[ inbox_filter ]
            
            if inbox_count > 0 and inbox_count == my_count:
                
                s += ' (all in inbox)'
                
            else:
                
                archive_count = filter_counts[ archive_filter ]
                
                if archive_count > 0 and archive_count == my_count:
                    
                    s += ' (all in archive)'
                    
                
            
        
        return s
        
    
class ListeningMediaList( MediaList ):
    
    def __init__( self, location_context: ClientLocation.LocationContext, media_results ):
        
        MediaList.__init__( self, location_context, media_results )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
    
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
        
    
    def _RecalcAfterContentUpdates( self, service_keys_to_content_updates ):
        
        archive_or_inbox = False
        
        data_types = set()
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
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
        
    
    def _RecalcFileViewingStats( self ):
        
        self._file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateCombinedManager( [ m.GetFileViewingStatsManager() for m in self._sorted_media ] )
        
    
    def _RecalcHashes( self ):
        
        MediaList._RecalcHashes( self )
        
        all_locations_managers = [ media.GetLocationsManager() for media in self._sorted_media ]
        
        current_to_timestamps = {}
        deleted_to_timestamps = {}
        
        for service_key in HG.client_controller.services_manager.GetServiceKeys( HC.FILE_SERVICES ):
            
            current_timestamps = [ timestamp for timestamp in ( locations_manager.GetCurrentTimestamp( service_key ) for locations_manager in all_locations_managers ) if timestamp is not None ]
            
            if len( current_timestamps ) > 0:
                
                current_to_timestamps[ service_key ] = max( current_timestamps )
                
            
            deleted_timestamps = [ timestamps for timestamps in ( locations_manager.GetDeletedTimestamps( service_key ) for locations_manager in all_locations_managers ) if timestamps is not None and timestamps[0] is not None ]
            
            if len( deleted_timestamps ) > 0:
                
                deleted_to_timestamps[ service_key ] = max( deleted_timestamps, key = lambda ts: ts[0] )
                
            
        
        pending = HydrusData.MassUnion( [ locations_manager.GetPending() for locations_manager in all_locations_managers ] )
        petitioned = HydrusData.MassUnion( [ locations_manager.GetPetitioned() for locations_manager in all_locations_managers ] )
        
        modified_times = { locations_manager.GetTimestampManager().GetAggregateModifiedTimestamp() for locations_manager in all_locations_managers }
        
        modified_times.discard( None )
        
        timestamp_manager = ClientMediaManagers.TimestampManager()
        
        if len( modified_times ) > 0:
            
            timestamp_manager.SetFileModifiedTimestamp( max( modified_times ) )
            
        
        self._locations_manager = ClientMediaManagers.LocationsManager( current_to_timestamps, deleted_to_timestamps, pending, petitioned, timestamp_manager = timestamp_manager )
        
    
    def _RecalcInternals( self ):
        
        self._RecalcHashes()
        
        self._RecalcTags()
        
        self._RecalcArchiveInbox()
        
        self._size = sum( [ media.GetSize() for media in self._sorted_media ] )
        self._size_definite = not False in ( media.IsSizeDefinite() for media in self._sorted_media )
        
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
        
    
    def GetCurrentTimestamp( self, service_key: bytes ) -> typing.Optional[ int ]:
        
        return self._locations_manager.GetCurrentTimestamp( service_key )
        
    
    def GetDeletedTimestamps( self, service_key: bytes ) -> typing.Tuple[ typing.Optional[ int ], typing.Optional[ int ] ]:
        
        return self._locations_manager.GetDeletedTimestamps( service_key )
        
    
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
        
    
    def HasImages( self ):
        
        return True in ( media.HasImages() for media in self._sorted_media )
        
    
    def HasInbox( self ):
        
        return self._inbox
        
    
    def HasNotes( self ):
        
        return self._has_notes
        
    
    def IsCollection( self ):
        
        return True
        
    
    def IsImage( self ):
        
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
    
    def GetCurrentTimestamp( self, service_key ) -> typing.Optional[ int ]:
        
        return self._media_result.GetLocationsManager().GetCurrentTimestamp( service_key )
        
    
    def GetDeletedTimestamps( self, service_key: bytes ) -> typing.Tuple[ typing.Optional[ int ], typing.Optional[ int ] ]:
        
        return self._media_result.GetLocationsManager().GetDeletedTimestamps( service_key )
        
    
    def GetPrettyInfoLines( self, only_interesting_lines = False ):
        
        def timestamp_is_interesting( timestamp_1, timestamp_2 ):
            
            distance_1 = abs( timestamp_1 - HydrusData.GetNow() )
            distance_2 = abs( timestamp_2 - HydrusData.GetNow() )
            
            # 50000 / 51000 = 0.98 = not interesting
            # 10000 / 51000 = 0.20 = interesting
            difference = min( distance_1, distance_2 ) / max( distance_1, distance_2, 1 )
            
            return difference < 0.9
            
        
        file_info_manager = self._media_result.GetFileInfoManager()
        locations_manager = self._media_result.GetLocationsManager()
        
        ( hash_id, hash, size, mime, width, height, duration, num_frames, has_audio, num_words ) = file_info_manager.ToTuple()
        
        info_string = HydrusData.ToHumanBytes( size ) + ' ' + HC.mime_string_lookup[ mime ]
        
        if width is not None and height is not None:
            
            info_string += ' ({})'.format( HydrusData.ConvertResolutionToPrettyString( ( width, height ) ) )
            
        
        if duration is not None:
            
            info_string += ', ' + HydrusData.ConvertMillisecondsToPrettyTime( duration )
            
        
        if num_frames is not None:
            
            if duration is None or duration == 0 or num_frames == 0:
                
                framerate_insert = ''
                
            else:
                
                framerate_insert = ', {}fps'.format( round( num_frames / ( duration / 1000 ) ) )
                
            
            info_string += ' ({} frames{})'.format( HydrusData.ToHumanInt( num_frames ), framerate_insert )
            
        
        if has_audio:
            
            info_string += ', {}'.format( HG.client_controller.new_options.GetString( 'has_audio_label' ) )
            
        
        if num_words is not None: info_string += ' (' + HydrusData.ToHumanInt( num_words ) + ' words)'
        
        lines = [ ( True, info_string ) ]
        
        locations_manager = self._media_result.GetLocationsManager()
        
        current_service_keys = locations_manager.GetCurrent()
        deleted_service_keys = locations_manager.GetDeleted()
        
        local_file_services = HG.client_controller.services_manager.GetLocalMediaFileServices()
        
        seen_local_file_service_timestamps = set()
        
        current_local_file_services = [ service for service in local_file_services if service.GetServiceKey() in current_service_keys ]
        
        if len( current_local_file_services ) > 0:
            
            for local_file_service in current_local_file_services:
                
                timestamp = locations_manager.GetCurrentTimestamp( local_file_service.GetServiceKey() )
                
                lines.append( ( True, 'added to {}: {}'.format( local_file_service.GetName(), ClientData.TimestampToPrettyTimeDelta( timestamp ) ) ) )
                
                seen_local_file_service_timestamps.add( timestamp )
                
            
        
        if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in current_service_keys:
            
            import_timestamp = locations_manager.GetCurrentTimestamp( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
            # if we haven't already printed this timestamp somewhere
            line_is_interesting = False not in ( timestamp_is_interesting( t, import_timestamp ) for t in seen_local_file_service_timestamps )
            
            lines.append( ( line_is_interesting, 'imported: {}'.format( ClientData.TimestampToPrettyTimeDelta( import_timestamp ) ) ) )
            
            if line_is_interesting:
                
                seen_local_file_service_timestamps.add( import_timestamp )
                
            
        
        deleted_local_file_services = [ service for service in local_file_services if service.GetServiceKey() in deleted_service_keys ]
        
        local_file_deletion_reason = locations_manager.GetLocalFileDeletionReason()
        
        if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in deleted_service_keys:
            
            ( timestamp, original_timestamp ) = locations_manager.GetDeletedTimestamps( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
            lines.append( ( True, 'deleted from this client {} ({})'.format( ClientData.TimestampToPrettyTimeDelta( timestamp ), local_file_deletion_reason ) ) )
            
        elif len( deleted_local_file_services ) > 0:
            
            for local_file_service in deleted_local_file_services:
                
                ( timestamp, original_timestamp ) = locations_manager.GetDeletedTimestamps( local_file_service.GetServiceKey() )
                
                l = 'removed from {} {}'.format( local_file_service.GetName(), ClientData.TimestampToPrettyTimeDelta( timestamp ) )
                
                if len( deleted_local_file_services ) == 1:
                    
                    l = '{} ({})'.format( l, local_file_deletion_reason )
                    
                
                lines.append( ( True, l ) )
                
            
            if len( deleted_local_file_services ) > 1:
                
                lines.append( ( False, 'Deletion reason: {}'.format( local_file_deletion_reason ) ) )
                
            
        
        if locations_manager.IsTrashed():
            
            lines.append( ( True, 'in the trash' ) )
            
        
        timestamp_manager = locations_manager.GetTimestampManager()
        
        file_modified_timestamp = timestamp_manager.GetAggregateModifiedTimestamp()
        
        if file_modified_timestamp is not None:
            
            # if we haven't already printed this timestamp somewhere
            line_is_interesting = False not in ( timestamp_is_interesting( timestamp, file_modified_timestamp ) for timestamp in seen_local_file_service_timestamps )
            
            lines.append( ( line_is_interesting, 'modified: {}'.format( ClientData.TimestampToPrettyTimeDelta( file_modified_timestamp ) ) ) )
            
            modified_timestamp_lines = []
            
            timestamp = timestamp_manager.GetFileModifiedTimestamp()
            
            if timestamp is not None:
                
                modified_timestamp_lines.append( 'local: {}'.format( ClientData.TimestampToPrettyTimeDelta( timestamp ) ) )
                
            
            for ( domain, timestamp ) in sorted( timestamp_manager.GetDomainModifiedTimestamps().items() ):
                
                modified_timestamp_lines.append( '{}: {}'.format( domain, ClientData.TimestampToPrettyTimeDelta( timestamp ) ) )
                
            
            if len( modified_timestamp_lines ) > 1:
                
                lines.append( ( False, ( 'all modified dates', modified_timestamp_lines ) ) )
                
            
        
        if not locations_manager.inbox:
            
            archive_timestamp = timestamp_manager.GetArchivedTimestamp()
            
            if archive_timestamp is not None:
                
                lines.append( ( True, 'archived: {}'.format( ClientData.TimestampToPrettyTimeDelta( archive_timestamp ) ) ) )
                
            
        
        for service_key in current_service_keys.intersection( HG.client_controller.services_manager.GetServiceKeys( HC.REMOTE_FILE_SERVICES ) ):
            
            timestamp = locations_manager.GetCurrentTimestamp( service_key )
            
            try:
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service_type = service.GetServiceType()
            
            if service_type == HC.IPFS:
                
                status_label = 'pinned'
                
            else:
                
                status_label = 'uploaded'
                
            
            lines.append( ( True, '{} to {} {}'.format( status_label, service.GetName(), ClientData.TimestampToPrettyTimeDelta( timestamp ) ) ) )
            
        
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
        
    
    def GetTitleString( self ):
        
        new_options = HG.client_controller.new_options
        
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
        
    
    def HasImages( self ): return self.IsImage()
    
    def HasInbox( self ): return self._media_result.GetInbox()
    
    def HasNotes( self ):
        
        return self._media_result.HasNotes()
        
    
    def IsCollection( self ): return False
    
    def IsImage( self ):
        
        return self._media_result.GetMime() in HC.IMAGES
        
    
    def IsSizeDefinite( self ): return self._media_result.GetSize() is not None
    
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
                serialisable_sort_data = ( namespaces, ClientTags.TAG_DISPLAY_ACTUAL )
                
            
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
            
            if sort_data in ( CC.SORT_FILES_BY_MIME, CC.SORT_FILES_BY_RANDOM, CC.SORT_FILES_BY_HASH ):
                
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
            
        
        if sort_metadata == 'system':
            
            if sort_data == CC.SORT_FILES_BY_RANDOM:
                
                def sort_key( x ):
                    
                    return random.random()
                    
                
            elif sort_data == CC.SORT_FILES_BY_HASH:
                
                def sort_key( x ):
                    
                    return x.GetHash().hex()
                    
                
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
                    
                    return deal_with_none( x.GetLocationsManager().GetTimestampManager().GetAggregateModifiedTimestamp() )
                    
                
            elif sort_data == CC.SORT_FILES_BY_LAST_VIEWED_TIME:
                
                def sort_key( x ):
                    
                    fvsm = x.GetFileViewingStatsManager()
                    
                    # do not do viewtime as a secondary sort here, to allow for user secondary sort to help out
                    
                    return deal_with_none( fvsm.GetLastViewedTime( CC.CANVAS_MEDIA_VIEWER ) )
                    
                
            elif sort_data == CC.SORT_FILES_BY_ARCHIVED_TIMESTAMP:
                
                def sort_key( x ):
                    
                    locations_manager = x.GetLocationsManager()
                    
                    return ( not locations_manager.inbox, deal_with_none( x.GetLocationsManager().GetTimestampManager().GetArchivedTimestamp() ) )
                    
                
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
                    
                    return len( tags_manager.GetCurrentAndPending( self.tag_context.service_key, ClientTags.TAG_DISPLAY_ACTUAL ) )
                    
                
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
                
            
        
        reverse = self.sort_order == CC.SORT_DESC
        
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
            sort_string_lookup[ CC.SORT_FILES_BY_HASH ] = ( 'hash', 'hash', CC.SORT_ASC )
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
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
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
        
        if self._indices_dirty:
            
            self._RecalcIndices()
            
        
        try:
            
            result = self._items_to_indices[ item ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing()
            
        
        return result
        
    
    def insert_items( self, items ):
        
        self.append_items( items )
        
        self.sort()
        
    
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
        
    
