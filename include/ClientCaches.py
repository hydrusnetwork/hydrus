import ClientDefaults
import ClientFiles
import ClientNetworking
import ClientRendering
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusPaths
import os
import random
import Queue
import threading
import time
import urllib
import wx
import HydrusData
import ClientData
import ClientConstants as CC
import HydrusGlobals
import collections
import HydrusTags
import itertools
import ClientSearch

class DataCache( object ):
    
    def __init__( self, cache_size_key ):
        
        self._cache_size_key = cache_size_key
        
        self._keys_to_data = {}
        self._keys_fifo = []
        
        self._total_estimated_memory_footprint = 0
        
        self._lock = threading.Lock()
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
    def _DeleteItem( self, index = 0 ):
        
        ( deletee_key, last_access_time ) = self._keys_fifo.pop( index )
        
        deletee_data = self._keys_to_data[ deletee_key ]
        
        self._total_estimated_memory_footprint -= deletee_data.GetEstimatedMemoryFootprint()
        
        del self._keys_to_data[ deletee_key ]
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._keys_to_data = {}
            self._keys_fifo = []
            
            self._total_estimated_memory_footprint = 0
            
        
    
    def AddData( self, key, data ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                options = HydrusGlobals.client_controller.GetOptions()
                
                while self._total_estimated_memory_footprint > options[ self._cache_size_key ]:
                    
                    self._DeleteItem()
                    
                
                self._keys_to_data[ key ] = data
                
                self._keys_fifo.append( ( key, HydrusData.GetNow() ) )
                
                self._total_estimated_memory_footprint += data.GetEstimatedMemoryFootprint()
                
            
        
    
    def GetData( self, key ):
        
        with self._lock:
            
            if key not in self._keys_to_data: raise Exception( 'Cache error! Looking for ' + HydrusData.ToUnicode( key ) + ', but it was missing.' )
            
            for ( i, ( fifo_key, last_access_time ) ) in enumerate( self._keys_fifo ):
                
                if fifo_key == key:
                    
                    del self._keys_fifo[ i ]
                    
                    break
                    
                
            
            self._keys_fifo.append( ( key, HydrusData.GetNow() ) )
            
            return self._keys_to_data[ key ]
            
        
    
    def HasData( self, key ):
        
        with self._lock: return key in self._keys_to_data
        
    
    def MaintainCache( self ):
        
        with self._lock:
            
            while True:
                
                if len( self._keys_fifo ) == 0: break
                else:
                    
                    oldest_index = 0
                    
                    ( key, last_access_time ) = self._keys_fifo[ oldest_index ]
                    
                    if HydrusData.TimeHasPassed( last_access_time + 1200 ):
                        
                        self._DeleteItem( oldest_index )
                        
                    else: break
                    
                
            
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
class LocalBooruCache( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self._RefreshShares()
        
        HydrusGlobals.client_controller.sub( self, 'RefreshShares', 'refresh_local_booru_shares' )
        HydrusGlobals.client_controller.sub( self, 'RefreshShares', 'restart_booru' )
        
    
    def _CheckDataUsage( self ):
        
        info = self._local_booru_service.GetInfo()
        
        max_monthly_data = info[ 'max_monthly_data' ]
        used_monthly_data = info[ 'used_monthly_data' ]
        
        if max_monthly_data is not None and used_monthly_data > max_monthly_data: raise HydrusExceptions.ForbiddenException( 'This booru has used all its monthly data. Please try again next month.' )
        
    
    def _CheckFileAuthorised( self, share_key, hash ):
        
        self._CheckShareAuthorised( share_key )
        
        info = self._GetInfo( share_key )
        
        if hash not in info[ 'hashes_set' ]: raise HydrusExceptions.NotFoundException( 'That file was not found in that share.' )
        
    
    def _CheckShareAuthorised( self, share_key ):
        
        self._CheckDataUsage()
        
        info = self._GetInfo( share_key )
        
        timeout = info[ 'timeout' ]
        
        if timeout is not None and HydrusData.TimeHasPassed( timeout ): raise HydrusExceptions.ForbiddenException( 'This share has expired.' )
        
    
    def _GetInfo( self, share_key ):
        
        try: info = self._keys_to_infos[ share_key ]
        except: raise HydrusExceptions.NotFoundException( 'Did not find that share on this booru.' )
        
        if info is None:
            
            info = HydrusGlobals.client_controller.Read( 'local_booru_share', share_key )
            
            hashes = info[ 'hashes' ]
            
            info[ 'hashes_set' ] = set( hashes )
            
            media_results = HydrusGlobals.client_controller.Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, hashes )
            
            info[ 'media_results' ] = media_results
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            info[ 'hashes_to_media_results' ] = hashes_to_media_results
            
            self._keys_to_infos[ share_key ] = info
            
        
        return info
        
    
    def _RefreshShares( self ):
        
        self._local_booru_service = HydrusGlobals.client_controller.GetServicesManager().GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        self._keys_to_infos = {}
        
        share_keys = HydrusGlobals.client_controller.Read( 'local_booru_share_keys' )
        
        for share_key in share_keys: self._keys_to_infos[ share_key ] = None
        
    
    def CheckShareAuthorised( self, share_key ):
        
        with self._lock: self._CheckShareAuthorised( share_key )
        
    
    def CheckFileAuthorised( self, share_key, hash ):
        
        with self._lock: self._CheckFileAuthorised( share_key, hash )
        
    
    def GetGalleryInfo( self, share_key ):
        
        with self._lock:
            
            self._CheckShareAuthorised( share_key )
            
            info = self._GetInfo( share_key )
            
            name = info[ 'name' ]
            text = info[ 'text' ]
            timeout = info[ 'timeout' ]
            media_results = info[ 'media_results' ]
            
            return ( name, text, timeout, media_results )
            
        
    
    def GetMediaResult( self, share_key, hash ):
        
        with self._lock:
            
            info = self._GetInfo( share_key )
            
            media_result = info[ 'hashes_to_media_results' ][ hash ]
            
            return media_result
            
        
    
    def GetPageInfo( self, share_key, hash ):
        
        with self._lock:
            
            self._CheckFileAuthorised( share_key, hash )
            
            info = self._GetInfo( share_key )
            
            name = info[ 'name' ]
            text = info[ 'text' ]
            timeout = info[ 'timeout' ]
            media_result = info[ 'hashes_to_media_results' ][ hash ]
            
            return ( name, text, timeout, media_result )
            
        
    
    def RefreshShares( self ):
        
        with self._lock:
            
            self._RefreshShares()
            
        
    
class MenuEventIdToActionCache( object ):
    
    def __init__( self ):
        
        self._ids_to_actions = {}
        self._actions_to_ids = {}
        
        self._temporary_ids = set()
        self._free_temporary_ids = set()
        
    
    def _ClearTemporaries( self ):
        
        for temporary_id in self._temporary_ids.difference( self._free_temporary_ids ):
            
            temporary_action = self._ids_to_actions[ temporary_id ]
            
            del self._ids_to_actions[ temporary_id ]
            del self._actions_to_ids[ temporary_action ]
            
        
        self._free_temporary_ids = set( self._temporary_ids )
        
    
    def _GetNewId( self, temporary ):
        
        if temporary:
            
            if len( self._free_temporary_ids ) == 0:
                
                new_id = wx.NewId()
                
                self._temporary_ids.add( new_id )
                self._free_temporary_ids.add( new_id )
                
            
            return self._free_temporary_ids.pop()
            
        else:
            
            return wx.NewId()
            
        
    
    def GetAction( self, event_id ):
        
        action = None
        
        if event_id in self._ids_to_actions:
            
            action = self._ids_to_actions[ event_id ]
            
            if event_id in self._temporary_ids:
                
                self._ClearTemporaries()
                
            
        
        return action
        
    
    def GetId( self, command, data = None, temporary = False ):
        
        action = ( command, data )
        
        if action not in self._actions_to_ids:
            
            event_id = self._GetNewId( temporary )
            
            self._ids_to_actions[ event_id ] = action
            self._actions_to_ids[ action ] = event_id
            
        
        return self._actions_to_ids[ action ]
        
    
    def GetPermanentId( self, command, data = None ):
        
        return self.GetId( command, data, False )
        
    
    def GetTemporaryId( self, command, data = None ):
        
        temporary = True
        
        if data is None:
            
            temporary = False
            
        
        return self.GetId( command, data, temporary )
        
    
MENU_EVENT_ID_TO_ACTION_CACHE = MenuEventIdToActionCache()

class RenderedImageCache( object ):
    
    def __init__( self, cache_type ):
        
        self._type = cache_type
        
        if self._type == 'fullscreen': self._data_cache = DataCache( 'fullscreen_cache_size' )
        elif self._type == 'preview': self._data_cache = DataCache( 'preview_cache_size' )
        
        self._total_estimated_memory_footprint = 0
        
        self._keys_being_rendered = {}
        
        HydrusGlobals.client_controller.sub( self, 'FinishedRendering', 'finished_rendering' )
        
    
    def Clear( self ): self._data_cache.Clear()
    
    def GetImage( self, media, target_resolution = None ):
        
        hash = media.GetHash()
        
        if target_resolution is None: target_resolution = media.GetResolution()
        
        key = ( hash, target_resolution )
        
        if self._data_cache.HasData( key ): return self._data_cache.GetData( key )
        elif key in self._keys_being_rendered: return self._keys_being_rendered[ key ]
        else:
            
            image_container = ClientRendering.RasterContainerImage( media, target_resolution )
            
            self._keys_being_rendered[ key ] = image_container
            
            return image_container
            
        
    
    def HasImage( self, hash, target_resolution ):
        
        key = ( hash, target_resolution )
        
        return self._data_cache.HasData( key ) or key in self._keys_being_rendered
        
    
    def FinishedRendering( self, key ):
        
        if key in self._keys_being_rendered:
            
            image_container = self._keys_being_rendered[ key ]
            
            del self._keys_being_rendered[ key ]
            
            self._data_cache.AddData( key, image_container )
            
        
    
class ThumbnailCache( object ):
    
    def __init__( self ):
        
        self._data_cache = DataCache( 'thumbnail_cache_size' )
        
        self._lock = threading.Lock()
        
        self._waterfall_queue_quick = set()
        self._waterfall_queue_random = []
        
        self._waterfall_event = threading.Event()
        
        self._special_thumbs = {}
        
        self.Clear()
        
        threading.Thread( target = self.DAEMONWaterfall, name = 'Waterfall Daemon' ).start()
        
        HydrusGlobals.client_controller.sub( self, 'Clear', 'thumbnail_resize' )
        
    
    def _RecalcWaterfallQueueRandom( self ):
    
        self._waterfall_queue_random = list( self._waterfall_queue_quick )
        
        random.shuffle( self._waterfall_queue_random )
        
    
    def CancelWaterfall( self, page_key, medias ):
        
        with self._lock:
            
            self._waterfall_queue_quick.difference_update( ( ( page_key, media ) for media in medias ) )
            
            self._RecalcWaterfallQueueRandom()
            
        
    
    def Clear( self ):
        
        self._data_cache.Clear()
        
        self._special_thumbs = {}
        
        names = [ 'hydrus', 'flash', 'pdf', 'audio', 'video' ]
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            for name in names:
                
                path = os.path.join( HC.STATIC_DIR, name + '.png' )
                
                options = HydrusGlobals.client_controller.GetOptions()
                
                thumbnail = HydrusFileHandling.GenerateThumbnail( path, options[ 'thumbnail_dimensions' ] )
                
                with open( temp_path, 'wb' ) as f: f.write( thumbnail )
                
                hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( temp_path )
                
                self._special_thumbs[ name ] = hydrus_bitmap
                
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
    def GetThumbnail( self, media ):
        
        display_media = media.GetDisplayMedia()
        
        mime = display_media.GetMime()
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            hash = display_media.GetHash()
            
            if not self._data_cache.HasData( hash ):
                
                path = None
                
                try:
                    
                    path = ClientFiles.GetThumbnailPath( hash, False )
                    
                    hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( path )
                    
                except HydrusExceptions.NotFoundException:
                    
                    print( 'Could not find the thumbnail for ' + hash.encode( 'hex' ) + '!' )
                    
                    return self._special_thumbs[ 'hydrus' ]
                    
                
                self._data_cache.AddData( hash, hydrus_bitmap )
                
            
            return self._data_cache.GetData( hash )
            
        elif mime in HC.AUDIO: return self._special_thumbs[ 'audio' ]
        elif mime in HC.VIDEO: return self._special_thumbs[ 'video' ]
        elif mime == HC.APPLICATION_FLASH: return self._special_thumbs[ 'flash' ]
        elif mime == HC.APPLICATION_PDF: return self._special_thumbs[ 'pdf' ]
        else: return self._special_thumbs[ 'hydrus' ]
        
    
    def HasThumbnailCached( self, media ):
        
        display_media = media.GetDisplayMedia()
        
        mime = display_media.GetMime()
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            hash = display_media.GetHash()
            
            return self._data_cache.HasData( hash )
            
        else:
            
            return True
            
        
    
    def Waterfall( self, page_key, medias ):
        
        with self._lock:
            
            self._waterfall_queue_quick.update( ( ( page_key, media ) for media in medias ) )
            
            self._RecalcWaterfallQueueRandom()
            
        
        self._waterfall_event.set()
        
    
    def DAEMONWaterfall( self ):
        
        last_paused = HydrusData.GetNowPrecise()
        
        while not HydrusGlobals.view_shutdown:
            
            with self._lock:
                
                do_wait = len( self._waterfall_queue_random ) == 0
                
            
            if do_wait:
                
                self._waterfall_event.wait( 1 )
                
                self._waterfall_event.clear()
                
                last_paused = HydrusData.GetNowPrecise()
                
            
            with self._lock:
                
                if len( self._waterfall_queue_random ) == 0:
                    
                    continue
                    
                else:
                    
                    result = self._waterfall_queue_random.pop( 0 )
                    
                    self._waterfall_queue_quick.discard( result )
                    
                    ( page_key, media ) = result
                    
                
            
            try:
                
                thumbnail = self.GetThumbnail( media ) # to load it
                
                HydrusGlobals.client_controller.pub( 'waterfall_thumbnail', page_key, media )
                
                if HydrusData.GetNowPrecise() - last_paused > 0.005:
                    
                    time.sleep( 0.00001 )
                    
                    last_paused = HydrusData.GetNowPrecise()
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
    
def LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
    
    potential_loop_paths = { parent }
    
    while len( potential_loop_paths.intersection( simple_children_to_parents.keys() ) ) > 0:
        
        new_potential_loop_paths = set()
        
        for potential_loop_path in potential_loop_paths.intersection( simple_children_to_parents.keys() ):
            
            new_potential_loop_paths.update( simple_children_to_parents[ potential_loop_path ] )
            
        
        potential_loop_paths = new_potential_loop_paths
        
        if child in potential_loop_paths: return True
        
    
    return False
    
def BuildSimpleChildrenToParents( pairs ):
    
    simple_children_to_parents = HydrusData.default_dict_set()
    
    for ( child, parent ) in pairs:
        
        if child == parent: continue
        
        if LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ): continue
        
        simple_children_to_parents[ child ].add( parent )
        
    
    return simple_children_to_parents
    
def CollapseTagSiblingChains( processed_siblings ):
    
    # now to collapse chains
    # A -> B and B -> C goes to A -> C and B -> C
    
    siblings = {}
    
    for ( old_tag, new_tag ) in processed_siblings.items():
        
        # adding A -> B
        
        if new_tag in siblings:
            
            # B -> F already calculated and added, so add A -> F
            
            siblings[ old_tag ] = siblings[ new_tag ]
            
        else:
            
            while new_tag in processed_siblings: new_tag = processed_siblings[ new_tag ] # pursue endpoint F
            
            siblings[ old_tag ] = new_tag
            
        
    
    reverse_lookup = collections.defaultdict( list )
    
    for ( old_tag, new_tag ) in siblings.items():
        
        reverse_lookup[ new_tag ].append( old_tag )
        
    
    return ( siblings, reverse_lookup )
    
def CombineTagSiblingPairs( service_keys_to_statuses_to_pairs ):
    
    # first combine the services
    # if A map already exists, don't overwrite
    # if A -> B forms a loop, don't write it
    
    processed_siblings = {}
    current_deleted_pairs = set()
    
    for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
        
        pairs = statuses_to_pairs[ HC.CURRENT ].union( statuses_to_pairs[ HC.PENDING ] )
        
        for ( old, new ) in pairs:
            
            if old == new: continue
            
            if old not in processed_siblings:
                
                next_new = new
                
                we_have_a_loop = False
                
                while next_new in processed_siblings:
                    
                    next_new = processed_siblings[ next_new ]
                    
                    if next_new == old:
                        
                        we_have_a_loop = True
                        
                        break
                        
                    
                
                if not we_have_a_loop: processed_siblings[ old ] = new
                
            
        
    
    return processed_siblings
    
# important thing here, and reason why it is recursive, is because we want to preserve the parent-grandparent interleaving
def BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents ):
    
    def AddParents( simple_children_to_parents, children_to_parents, child, parents ):
        
        for parent in parents:
            
            children_to_parents[ child ].append( parent )
            
            if parent in simple_children_to_parents:
                
                grandparents = simple_children_to_parents[ parent ]
                
                AddParents( simple_children_to_parents, children_to_parents, child, grandparents )
                
            
        
    
    service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
    
    for ( service_key, simple_children_to_parents ) in service_keys_to_simple_children_to_parents.items():
        
        children_to_parents = service_keys_to_children_to_parents[ service_key ]
        
        for ( child, parents ) in simple_children_to_parents.items(): AddParents( simple_children_to_parents, children_to_parents, child, parents )
        
    
    return service_keys_to_children_to_parents
    
def BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat ):
    
    service_keys_to_simple_children_to_parents = collections.defaultdict( HydrusData.default_dict_set )
    
    for ( service_key, pairs ) in service_keys_to_pairs_flat.items():
        
        service_keys_to_simple_children_to_parents[ service_key ] = BuildSimpleChildrenToParents( pairs )
        
    
    return service_keys_to_simple_children_to_parents
    
class TagCensorshipManager( object ):
    
    def __init__( self ):
        
        self.RefreshData()
        
        HydrusGlobals.client_controller.sub( self, 'RefreshData', 'notify_new_tag_censorship' )
        
    
    def GetInfo( self, service_key ):
        
        if service_key in self._service_keys_to_info: return self._service_keys_to_info[ service_key ]
        else: return ( True, set() )
        
    
    def RefreshData( self ):
        
        info = HydrusGlobals.client_controller.Read( 'tag_censorship' )
        
        self._service_keys_to_info = {}
        self._service_keys_to_predicates = {}
        
        for ( service_key, blacklist, censorships ) in info:
            
            self._service_keys_to_info[ service_key ] = ( blacklist, censorships )
            
            tag_matches = lambda tag: True in ( HydrusTags.CensorshipMatch( tag, censorship ) for censorship in censorships )
            
            if blacklist: predicate = lambda tag: not tag_matches( tag )
            else: predicate = tag_matches
            
            self._service_keys_to_predicates[ service_key ] = predicate
            
        
    
    def FilterServiceKeysToStatusesToTags( self, service_keys_to_statuses_to_tags ):
        
        filtered_service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
            
            for service_key_lookup in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
                
                if service_key_lookup in self._service_keys_to_predicates:
                    
                    combined_predicate = self._service_keys_to_predicates[ service_key_lookup ]
                    
                    new_statuses_to_tags = HydrusData.default_dict_set()
                    
                    for ( status, tags ) in statuses_to_tags.items():
                        
                        new_statuses_to_tags[ status ] = { tag for tag in tags if combined_predicate( tag ) }
                        
                    
                    statuses_to_tags = new_statuses_to_tags
                    
                
            
            filtered_service_keys_to_statuses_to_tags[ service_key ] = statuses_to_tags
            
        
        return filtered_service_keys_to_statuses_to_tags
        
    
    def FilterTags( self, service_key, tags ):
        
        for service_key in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key in self._service_keys_to_predicates:
                
                predicate = self._service_keys_to_predicates[ service_key ]
                
                tags = { tag for tag in tags if predicate( tag ) }
                
            
        
        return tags
        
    
class TagParentsManager( object ):
    
    def __init__( self ):
        
        self._service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
        
        self._RefreshParents()
        
        self._lock = threading.Lock()
        
        HydrusGlobals.client_controller.sub( self, 'RefreshParents', 'notify_new_parents' )
        
    
    def _RefreshParents( self ):
        
        service_keys_to_statuses_to_pairs = HydrusGlobals.client_controller.Read( 'tag_parents' )
        
        # first collapse siblings
        
        sibling_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        collapsed_service_keys_to_statuses_to_pairs = collections.defaultdict( HydrusData.default_dict_set )
        
        for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY: continue
            
            for ( status, pairs ) in statuses_to_pairs.items():
                
                pairs = sibling_manager.CollapsePairs( pairs )
                
                collapsed_service_keys_to_statuses_to_pairs[ service_key ][ status ] = pairs
                
            
        
        # now collapse current and pending
        
        service_keys_to_pairs_flat = HydrusData.default_dict_set()
        
        for ( service_key, statuses_to_pairs ) in collapsed_service_keys_to_statuses_to_pairs.items():
            
            pairs_flat = statuses_to_pairs[ HC.CURRENT ].union( statuses_to_pairs[ HC.PENDING ] )
            
            service_keys_to_pairs_flat[ service_key ] = pairs_flat
            
        
        # now create the combined tag service
        
        combined_pairs_flat = set()
        
        for pairs_flat in service_keys_to_pairs_flat.values():
            
            combined_pairs_flat.update( pairs_flat )
            
        
        service_keys_to_pairs_flat[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_pairs_flat
        
        #
        
        service_keys_to_simple_children_to_parents = BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat )
        
        self._service_keys_to_children_to_parents = BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents )
        
    
    def ExpandPredicates( self, service_key, predicates ):
        
        results = []
        
        with self._lock:
            
            for predicate in predicates:
                
                results.append( predicate )
                
                if predicate.GetType() == HC.PREDICATE_TYPE_TAG:
                    
                    tag = predicate.GetValue()
                    
                    parents = self._service_keys_to_children_to_parents[ service_key ][ tag ]
                    
                    for parent in parents:
                        
                        parent_predicate = ClientData.Predicate( HC.PREDICATE_TYPE_PARENT, parent )
                        
                        results.append( parent_predicate )
                        
                    
                
            
            return results
            
        
    
    def ExpandTags( self, service_key, tags ):
        
        with self._lock:
            
            tags_results = set( tags )
            
            for tag in tags:
                
                tags_results.update( self._service_keys_to_children_to_parents[ service_key ][ tag ] )
                
            
            return tags_results
            
        
    
    def GetParents( self, service_key, tag ):
        
        with self._lock:
            
            return self._service_keys_to_children_to_parents[ service_key ][ tag ]
            
        
    
    def RefreshParents( self ):
        
        with self._lock:
            
            self._RefreshParents()
            
        
    
class TagSiblingsManager( object ):
    
    def __init__( self ):
        
        self._RefreshSiblings()
        
        self._lock = threading.Lock()
        
        HydrusGlobals.client_controller.sub( self, 'RefreshSiblings', 'notify_new_siblings' )
        
    
    def _CollapseTags( self, tags ):
        
        return { self._siblings[ tag ] if tag in self._siblings else tag for tag in tags }
        
    
    def _RefreshSiblings( self ):
        
        service_keys_to_statuses_to_pairs = HydrusGlobals.client_controller.Read( 'tag_siblings' )
        
        processed_siblings = CombineTagSiblingPairs( service_keys_to_statuses_to_pairs )
        
        ( self._siblings, self._reverse_lookup ) = CollapseTagSiblingChains( processed_siblings )
        
        HydrusGlobals.client_controller.pub( 'new_siblings_gui' )
        
    
    def GetAutocompleteSiblings( self, half_complete_tag ):
        
        with self._lock:
            
            key_based_matching_values = { self._siblings[ key ] for key in self._siblings.keys() if ClientSearch.SearchEntryMatchesTag( half_complete_tag, key, search_siblings = False ) }
            
            value_based_matching_values = { value for value in self._siblings.values() if ClientSearch.SearchEntryMatchesTag( half_complete_tag, value, search_siblings = False ) }
            
            matching_values = key_based_matching_values.union( value_based_matching_values )
            
            # all the matching values have a matching sibling somewhere in their network
            # so now fetch the networks
            
            lists_of_matching_keys = [ self._reverse_lookup[ value ] for value in matching_values ]
            
            matching_keys = itertools.chain.from_iterable( lists_of_matching_keys )
            
            matches = matching_values.union( matching_keys )
            
            return matches
            
        
    
    def GetSibling( self, tag ):
        
        with self._lock:
            
            if tag in self._siblings: return self._siblings[ tag ]
            else: return None
            
        
    
    def GetAllSiblings( self, tag ):
        
        with self._lock:
            
            if tag in self._siblings:
                
                new_tag = self._siblings[ tag ]
                
            elif tag in self._reverse_lookup: new_tag = tag
            else: return [ tag ]
            
            all_siblings = list( self._reverse_lookup[ new_tag ] )
            
            all_siblings.append( new_tag )
            
            return all_siblings
            
        
    
    def RefreshSiblings( self ):
        
        with self._lock: self._RefreshSiblings()
        
    
    def CollapseNamespacedTags( self, namespace, tags ):
        
        with self._lock:
            
            results = set()
            
            for tag in tags:
                
                full_tag = namespace + ':' + tag
                
                if full_tag in self._siblings:
                    
                    sibling = self._siblings[ full_tag ]
                    
                    if ':' in sibling: sibling = sibling.split( ':', 1 )[1]
                    
                    results.add( sibling )
                    
                else: results.add( tag )
                
            
            return results
            
        
    
    def CollapsePredicates( self, predicates ):
        
        with self._lock:
            
            results = [ predicate for predicate in predicates if predicate.GetType() != HC.PREDICATE_TYPE_TAG ]
            
            tag_predicates = [ predicate for predicate in predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG ]
            
            tags_to_predicates = { predicate.GetValue() : predicate for predicate in predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG }
            
            tags = tags_to_predicates.keys()
            
            tags_to_include_in_results = set()
            
            for tag in tags:
                
                if tag in self._siblings:
                    
                    old_tag = tag
                    old_predicate = tags_to_predicates[ old_tag ]
                    
                    new_tag = self._siblings[ old_tag ]
                    
                    if new_tag not in tags_to_predicates:
                        
                        ( old_pred_type, old_value, old_inclusive ) = old_predicate.GetInfo()
                        
                        new_predicate = ClientData.Predicate( old_pred_type, new_tag, inclusive = old_inclusive )
                        
                        tags_to_predicates[ new_tag ] = new_predicate
                        
                        tags_to_include_in_results.add( new_tag )
                        
                    
                    new_predicate = tags_to_predicates[ new_tag ]
                    
                    current_count = old_predicate.GetCount( HC.CURRENT )
                    pending_count = old_predicate.GetCount( HC.PENDING )
                    
                    new_predicate.AddToCount( HC.CURRENT, current_count )
                    new_predicate.AddToCount( HC.PENDING, pending_count )
                    
                else: tags_to_include_in_results.add( tag )
                
            
            results.extend( [ tags_to_predicates[ tag ] for tag in tags_to_include_in_results ] )
            
            return results
            
        
    
    def CollapsePairs( self, pairs ):
        
        with self._lock:
            
            result = set()
            
            for ( a, b ) in pairs:
                
                if a in self._siblings: a = self._siblings[ a ]
                if b in self._siblings: b = self._siblings[ b ]
                
                result.add( ( a, b ) )
                
            
            return result
            
        
    
    def CollapseStatusesToTags( self, statuses_to_tags ):
        
        with self._lock:
            
            statuses = statuses_to_tags.keys()
            
            for status in statuses:
                
                statuses_to_tags[ status ] = self._CollapseTags( statuses_to_tags[ status ] )
                
            
            return statuses_to_tags
            
        
    
    def CollapseTags( self, tags ):
        
        with self._lock:
            
            return self._CollapseTags( tags )
            
        
    
    def CollapseTagsToCount( self, tags_to_count ):
        
        with self._lock:
            
            results = collections.Counter()
            
            for ( tag, count ) in tags_to_count.items():
                
                if tag in self._siblings: tag = self._siblings[ tag ]
                
                results[ tag ] += count
                
            
            return results
            
        
    
class WebSessionManagerClient( object ):
    
    def __init__( self ):
        
        existing_sessions = HydrusGlobals.client_controller.Read( 'web_sessions' )
        
        self._names_to_sessions = { name : ( cookies, expires ) for ( name, cookies, expires ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def GetCookies( self, name ):
        
        now = HydrusData.GetNow()
        
        with self._lock:
            
            if name in self._names_to_sessions:
                
                ( cookies, expires ) = self._names_to_sessions[ name ]
                
                if HydrusData.TimeHasPassed( expires - 300 ): del self._names_to_sessions[ name ]
                else: return cookies
                
            
            # name not found, or expired
            
            if name == 'deviant art':
                
                ( response_gumpf, cookies ) = HydrusGlobals.client_controller.DoHTTP( HC.GET, 'http://www.deviantart.com/', return_cookies = True )
                
                expires = now + 30 * 86400
                
            if name == 'hentai foundry':
                
                ( response_gumpf, cookies ) = HydrusGlobals.client_controller.DoHTTP( HC.GET, 'http://www.hentai-foundry.com/?enterAgree=1', return_cookies = True )
                
                raw_csrf = cookies[ 'YII_CSRF_TOKEN' ] # 19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B
                
                processed_csrf = urllib.unquote( raw_csrf ) # 19b05b536885ec60b8b37650a32f8deb11c08cd1s:40:"2917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32";
                
                csrf_token = processed_csrf.split( '"' )[1] # the 2917... bit
                
                hentai_foundry_form_info = ClientDefaults.GetDefaultHentaiFoundryInfo()
                
                hentai_foundry_form_info[ 'YII_CSRF_TOKEN' ] = csrf_token
                
                body = urllib.urlencode( hentai_foundry_form_info )
                
                request_headers = {}
                ClientNetworking.AddCookiesToHeaders( cookies, request_headers )
                request_headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
                
                HydrusGlobals.client_controller.DoHTTP( HC.POST, 'http://www.hentai-foundry.com/site/filters', request_headers = request_headers, body = body )
                
                expires = now + 60 * 60
                
            elif name == 'pixiv':
                
                ( id, password ) = HydrusGlobals.client_controller.Read( 'pixiv_account' )
                
                if id == '' and password == '':
                    
                    raise Exception( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                    
                
                form_fields = {}
                
                form_fields[ 'mode' ] = 'login'
                form_fields[ 'pixiv_id' ] = id
                form_fields[ 'pass' ] = password
                form_fields[ 'skip' ] = '1'
                
                body = urllib.urlencode( form_fields )
                
                headers = {}
                headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
                
                ( response_gumpf, cookies ) = HydrusGlobals.client_controller.DoHTTP( HC.POST, 'http://www.pixiv.net/login.php', request_headers = headers, body = body, return_cookies = True )
                
                # _ only given to logged in php sessions
                if 'PHPSESSID' not in cookies or '_' not in cookies[ 'PHPSESSID' ]: raise Exception( 'Pixiv login credentials not accepted!' )
                
                expires = now + 30 * 86400
                
            
            self._names_to_sessions[ name ] = ( cookies, expires )
            
            HydrusGlobals.client_controller.Write( 'web_session', name, cookies, expires )
            
            return cookies
            
        
    