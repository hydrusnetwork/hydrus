from . import ClientFiles
from . import ClientImageHandling
from . import ClientParsing
from . import ClientPaths
from . import ClientRendering
from . import ClientSearch
from . import ClientServices
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusFileHandling
from . import HydrusImageHandling
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusThreading
import json
import os
import random
import threading
import time
import wx
from . import HydrusData
from . import ClientData
from . import ClientConstants as CC
from . import HydrusGlobals as HG
import collections
from . import HydrusTags
import traceback
import weakref

# now let's fill out grandparents
def BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents ):
    
    # important thing here, and reason why it is recursive, is because we want to preserve the parent-grandparent interleaving in list order
    def AddParentsAndGrandparents( simple_children_to_parents, this_childs_parents, parents ):
        
        for parent in parents:
            
            if parent not in this_childs_parents:
                
                this_childs_parents.append( parent )
                
            
            # this parent has its own parents, so the child should get those as well
            if parent in simple_children_to_parents:
                
                grandparents = simple_children_to_parents[ parent ]
                
                AddParentsAndGrandparents( simple_children_to_parents, this_childs_parents, grandparents )
                
            
        
    
    service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
    
    for ( service_key, simple_children_to_parents ) in service_keys_to_simple_children_to_parents.items():
        
        children_to_parents = service_keys_to_children_to_parents[ service_key ]
        
        for ( child, parents ) in list(simple_children_to_parents.items()):
            
            this_childs_parents = children_to_parents[ child ]
            
            AddParentsAndGrandparents( simple_children_to_parents, this_childs_parents, parents )
            
        
    
    return service_keys_to_children_to_parents
    
def BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat ):
    
    service_keys_to_simple_children_to_parents = collections.defaultdict( HydrusData.default_dict_set )
    
    for ( service_key, pairs ) in service_keys_to_pairs_flat.items():
        
        service_keys_to_simple_children_to_parents[ service_key ] = BuildSimpleChildrenToParents( pairs )
        
    
    return service_keys_to_simple_children_to_parents
    
# take pairs, make dict of child -> parents while excluding loops
# no grandparents here
def BuildSimpleChildrenToParents( pairs ):
    
    simple_children_to_parents = HydrusData.default_dict_set()
    
    for ( child, parent ) in pairs:
        
        if child == parent:
            
            continue
            
        
        if parent in simple_children_to_parents and LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
            
            continue
            
        
        simple_children_to_parents[ child ].add( parent )
        
    
    return simple_children_to_parents
    
def CollapseTagSiblingPairs( groups_of_pairs ):
    
    # This now takes 'groups' of pairs in descending order of precedence
    
    # This allows us to mandate that local tags take precedence
    
    # a pair is invalid if:
    # it causes a loop (a->b, b->c, c->a)
    # there is already a relationship for the 'bad' sibling (a->b, a->c)
    
    valid_chains = {}
    
    for pairs in groups_of_pairs:
        
        pairs = list( pairs )
        
        pairs.sort()
        
        for ( bad, good ) in pairs:
            
            if bad == good:
                
                # a->a is a loop!
                
                continue
                
            
            if bad not in valid_chains:
                
                we_have_a_loop = False
                
                current_best = good
                
                while current_best in valid_chains:
                    
                    current_best = valid_chains[ current_best ]
                    
                    if current_best == bad:
                        
                        we_have_a_loop = True
                        
                        break
                        
                    
                
                if not we_have_a_loop:
                    
                    valid_chains[ bad ] = good
                    
                
            
        
    
    # now we collapse the chains, turning:
    # a->b, b->c ... e->f
    # into
    # a->f, b->f ... e->f
    
    siblings = {}
    
    for ( bad, good ) in list(valid_chains.items()):
        
        # given a->b, want to find f
        
        if good in siblings:
            
            # f already calculated and added
            
            best = siblings[ good ]
            
        else:
            
            # we don't know f for this chain, so let's figure it out
            
            current_best = good
            
            while current_best in valid_chains:
                
                current_best = valid_chains[ current_best ] # pursue endpoint f
                
            
            best = current_best
            
        
        # add a->f
        siblings[ bad ] = best
        
    
    return siblings
    
def DeLoopTagSiblingPairs( groups_of_pairs ):
    
    pass
    
def LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
    
    potential_loop_paths = { parent }
    
    while True:
        
        new_potential_loop_paths = set()
        
        for potential_loop_path in potential_loop_paths:
            
            if potential_loop_path in simple_children_to_parents:
                
                new_potential_loop_paths.update( simple_children_to_parents[ potential_loop_path ] )
                
            
        
        potential_loop_paths = new_potential_loop_paths
        
        if child in potential_loop_paths:
            
            return True
            
        elif len( potential_loop_paths ) == 0:
            
            return False
            
        
    
class BitmapManager( object ):
    
    MAX_MEMORY_ALLOWANCE = 512 * 1024 * 1024
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._unusued_bitmaps = collections.defaultdict( list )
        self._destroyee_bitmaps = []
        self._total_unused_memory_size = 0
        
        self._media_background_bmp_path = None
        self._media_background_bmp = None
        
        self._awaiting_destruction = False
        
        HG.client_controller.sub( self, 'MaintainMemory', 'memory_maintenance_pulse' )
        
    
    def _AdjustTotalMemory( self, direction, key ):
        
        ( width, height, depth ) = key
        
        amount = width * height * depth / 8
        
        self._total_unused_memory_size += direction * amount
        
    
    def _ClearDestroyees( self ):
        
        def action_destroyee( item ):
            
            ( destroy_timestamp, bitmap ) = item
            
            if HydrusData.TimeHasPassedPrecise( destroy_timestamp ) and bitmap:
                
                bitmap.Destroy()
                
                return False
                
            else:
                
                return True
                
            
        
        try:
            
            self._destroyee_bitmaps = list( filter( action_destroyee, self._destroyee_bitmaps ) )
            
        finally:
            
            self._awaiting_destruction = False
            
        
        if len( self._destroyee_bitmaps ) > 0:
            
            self._ScheduleDestruction()
            
        
    
    def _ScheduleDestruction( self ):
        
        if not self._awaiting_destruction:
            
            self._controller.CallLaterWXSafe( self._controller, 1.0, self._ClearDestroyees )
            
            self._awaiting_destruction = True
            
        
    
    def ReleaseBitmap( self, bitmap ):
        
        ( width, height ) = bitmap.GetSize()
        depth = bitmap.GetDepth()
        
        key = ( width, height, depth )
        
        if key in self._unusued_bitmaps and len( self._unusued_bitmaps[ key ] ) > 10:
            
            self._destroyee_bitmaps.append( ( HydrusData.GetNowPrecise() + 0.5, bitmap ) )
            
            self._ScheduleDestruction()
            
        else:
            
            self._unusued_bitmaps[ key ].append( bitmap )
            
            self._AdjustTotalMemory( 1, key )
            
            if self._total_unused_memory_size > self.MAX_MEMORY_ALLOWANCE:
                
                self._controller.CallLaterWXSafe( self._controller, 1.0, self.MaintainMemory )
                
            
        
    
    def GetBitmap( self, width, height, depth = 24 ):
        
        if width < 0:
            
            width = 20
            
        
        if height < 0:
            
            height = 20
            
        
        key = ( width, height, depth )
        
        if key in self._unusued_bitmaps:
            
            bitmaps = self._unusued_bitmaps[ key ]
            
            if len( bitmaps ) > 0:
                
                bitmap = bitmaps.pop()
                
                self._AdjustTotalMemory( -1, key )
                
                return bitmap
                
            else:
                
                del self._unusued_bitmaps[ key ]
                
            
        
        bitmap = wx.Bitmap( width, height, depth )
        
        return bitmap
        
    
    def GetBitmapFromBuffer( self, width, height, depth, data ):
        
        bitmap = self.GetBitmap( width, height, depth = depth )
        
        if depth == 24:
            
            bitmap.CopyFromBuffer( data, format = wx.BitmapBufferFormat_RGB )
            
        elif depth == 32:
            
            bitmap.CopyFromBuffer( data, format = wx.BitmapBufferFormat_RGBA )
            
        
        return bitmap
        
    
    def GetMediaBackgroundBitmap( self ):
        
        bmp_path = self._controller.new_options.GetNoneableString( 'media_background_bmp_path' )
        
        if bmp_path != self._media_background_bmp_path:
            
            self._media_background_bmp_path = bmp_path
            
            if self._media_background_bmp is not None:
                
                self.ReleaseBitmap( self._media_background_bmp )
                
            
            try:
                
                bmp = wx.Bitmap( self._media_background_bmp_path )
                
                self._media_background_bmp = bmp
                
            except Exception as e:
                
                self._media_background_bmp = None
                
                HydrusData.ShowText( 'Loading a bmp caused an error!' )
                
                HydrusData.ShowException( e )
                
                return None
                
            
        
        return self._media_background_bmp
        
    
    def MaintainMemory( self ):
        
        destroy_time = HydrusData.GetNowPrecise() + 0.5
        
        for bitmaps in self._unusued_bitmaps.values():
            
            self._destroyee_bitmaps.extend( ( ( destroy_time, bitmap ) for bitmap in bitmaps ) )
            
        
        self._unusued_bitmaps = collections.defaultdict( list )
        
        self._total_unused_memory_size = 0
        
        self._ScheduleDestruction()
        
    
class DataCache( object ):
    
    def __init__( self, controller, cache_size, timeout = 1200 ):
        
        self._controller = controller
        self._cache_size = cache_size
        self._timeout = timeout
        
        self._keys_to_data = {}
        self._keys_fifo = collections.OrderedDict()
        
        self._total_estimated_memory_footprint = 0
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'MaintainCache', 'memory_maintenance_pulse' )
        
    
    def _Delete( self, key ):
        
        if key not in self._keys_to_data:
            
            return
            
        
        deletee_data = self._keys_to_data[ key ]
        
        del self._keys_to_data[ key ]
        
        self._RecalcMemoryUsage()
        
    
    def _DeleteItem( self ):
        
        ( deletee_key, last_access_time ) = self._keys_fifo.popitem( last = False )
        
        self._Delete( deletee_key )
        
    
    def _RecalcMemoryUsage( self ):
        
        self._total_estimated_memory_footprint = sum( ( data.GetEstimatedMemoryFootprint() for data in list(self._keys_to_data.values()) ) )
        
    
    def _TouchKey( self, key ):
        
        # have to delete first, rather than overwriting, so the ordereddict updates its internal order
        if key in self._keys_fifo:
            
            del self._keys_fifo[ key ]
            
        
        self._keys_fifo[ key ] = HydrusData.GetNow()
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._keys_to_data = {}
            self._keys_fifo = collections.OrderedDict()
            
            self._total_estimated_memory_footprint = 0
            
        
    
    def AddData( self, key, data ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                while self._total_estimated_memory_footprint > self._cache_size:
                    
                    self._DeleteItem()
                    
                
                self._keys_to_data[ key ] = data
                
                self._TouchKey( key )
                
                self._RecalcMemoryUsage()
                
            
        
    
    def DeleteData( self, key ):
        
        with self._lock:
            
            self._Delete( key )
            
        
    
    def GetData( self, key ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                raise Exception( 'Cache error! Looking for ' + str( key ) + ', but it was missing.' )
                
            
            self._TouchKey( key )
            
            return self._keys_to_data[ key ]
            
        
    
    def GetIfHasData( self, key ):
        
        with self._lock:
            
            if key in self._keys_to_data:
                
                self._TouchKey( key )
                
                return self._keys_to_data[ key ]
                
            else:
                
                return None
                
            
        
    
    def HasData( self, key ):
        
        with self._lock:
            
            return key in self._keys_to_data
            
        
    
    def MaintainCache( self ):
        
        with self._lock:
            
            while True:
                
                if len( self._keys_fifo ) == 0:
                    
                    break
                    
                else:
                    
                    ( key, last_access_time ) = next( iter(self._keys_fifo.items()) )
                    
                    if HydrusData.TimeHasPassed( last_access_time + self._timeout ):
                        
                        self._DeleteItem()
                        
                    else:
                        
                        break
                        
                    
                
            
        
    
class FileViewingStatsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._pending_updates = {}
        
        self._last_update = HydrusData.GetNow()
        
        self._my_flush_job = self._controller.CallRepeating( 5, 60, self.REPEATINGFlush )
        
    
    def _GenerateViewsRow( self, viewtype, viewtime_delta ):
        
        new_options = HG.client_controller.new_options
        
        preview_views_delta = 0
        preview_viewtime_delta = 0
        media_views_delta = 0
        media_viewtime_delta = 0
        
        if viewtype == 'preview':
            
            preview_min = new_options.GetNoneableInteger( 'file_viewing_statistics_preview_min_time' )
            preview_max = new_options.GetNoneableInteger( 'file_viewing_statistics_preview_max_time' )
            
            if preview_max is not None:
                
                viewtime_delta = min( viewtime_delta, preview_max )
                
            
            if preview_min is None or viewtime_delta >= preview_min:
                
                preview_views_delta = 1
                preview_viewtime_delta = viewtime_delta
                
            
        elif viewtype in ( 'media', 'media_duplicates_filter' ):
            
            do_it = True
            
            if viewtime_delta == 'media_duplicates_filter' and not new_options.GetBoolean( 'file_viewing_statistics_active_on_dupe_filter' ):
                
                do_it = False
                
            
            if do_it:
                
                media_min = new_options.GetNoneableInteger( 'file_viewing_statistics_media_min_time' )
                media_max = new_options.GetNoneableInteger( 'file_viewing_statistics_media_max_time' )
                
                if media_max is not None:
                    
                    viewtime_delta = min( viewtime_delta, media_max )
                    
                
                if media_min is None or viewtime_delta >= media_min:
                    
                    media_views_delta = 1
                    media_viewtime_delta = viewtime_delta
                    
                
            
        
        return ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
        
    
    def _PubSubRow( self, hash, row ):
        
        ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta ) = row
        
        pubsub_row = ( hash, preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, pubsub_row )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        HG.client_controller.pub( 'content_updates_data', service_keys_to_content_updates )
        HG.client_controller.pub( 'content_updates_gui', service_keys_to_content_updates )
        
    
    def REPEATINGFlush( self ):
        
        self.Flush()
        
    
    def Flush( self ):
        
        with self._lock:
            
            if len( self._pending_updates ) > 0:
                
                content_updates = []
                
                for ( hash, ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta ) ) in self._pending_updates.items():
                    
                    row = ( hash, preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, row )
                    
                    content_updates.append( content_update )
                    
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : content_updates }
                
                # non-synchronous
                self._controller.Write( 'content_updates', service_keys_to_content_updates, do_pubsubs = False )
                
                self._pending_updates = {}
                
            
        
    
    def FinishViewing( self, viewtype, hash, viewtime_delta ):
        
        if not HG.client_controller.new_options.GetBoolean( 'file_viewing_statistics_active' ):
            
            return
            
        
        with self._lock:
            
            row = self._GenerateViewsRow( viewtype, viewtime_delta )
            
            if hash not in self._pending_updates:
                
                self._pending_updates[ hash ] = row
                
            else:
                
                ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta ) = row
                
                ( existing_preview_views_delta, existing_preview_viewtime_delta, existing_media_views_delta, existing_media_viewtime_delta ) = self._pending_updates[ hash ]
                
                self._pending_updates[ hash ] = ( existing_preview_views_delta + preview_views_delta, existing_preview_viewtime_delta + preview_viewtime_delta, existing_media_views_delta + media_views_delta, existing_media_viewtime_delta + media_viewtime_delta )
                
            
        
        self._PubSubRow( hash, row )
        

class LocalBooruCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._RefreshShares()
        
        self._controller.sub( self, 'RefreshShares', 'refresh_local_booru_shares' )
        self._controller.sub( self, 'RefreshShares', 'restart_client_server_service' )
        
    
    def _CheckDataUsage( self ):
        
        if not self._local_booru_service.BandwidthOK():
            
            raise HydrusExceptions.InsufficientCredentialsException( 'This booru has used all its monthly data. Please try again next month.' )
            
        
    
    def _CheckFileAuthorised( self, share_key, hash ):
        
        self._CheckShareAuthorised( share_key )
        
        info = self._GetInfo( share_key )
        
        if hash not in info[ 'hashes_set' ]:
            
            raise HydrusExceptions.NotFoundException( 'That file was not found in that share.' )
            
        
    
    def _CheckShareAuthorised( self, share_key ):
        
        self._CheckDataUsage()
        
        info = self._GetInfo( share_key )
        
        timeout = info[ 'timeout' ]
        
        if timeout is not None and HydrusData.TimeHasPassed( timeout ):
            
            raise HydrusExceptions.InsufficientCredentialsException( 'This share has expired.' )
            
        
    
    def _GetInfo( self, share_key ):
        
        try: info = self._keys_to_infos[ share_key ]
        except: raise HydrusExceptions.NotFoundException( 'Did not find that share on this booru.' )
        
        if info is None:
            
            info = self._controller.Read( 'local_booru_share', share_key )
            
            hashes = info[ 'hashes' ]
            
            info[ 'hashes_set' ] = set( hashes )
            
            media_results = self._controller.Read( 'media_results', hashes )
            
            info[ 'media_results' ] = media_results
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            info[ 'hashes_to_media_results' ] = hashes_to_media_results
            
            self._keys_to_infos[ share_key ] = info
            
        
        return info
        
    
    def _RefreshShares( self ):
        
        self._local_booru_service = self._controller.services_manager.GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        self._keys_to_infos = {}
        
        share_keys = self._controller.Read( 'local_booru_share_keys' )
        
        for share_key in share_keys:
            
            self._keys_to_infos[ share_key ] = None
            
        
    
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
            
        
    
    def RefreshShares( self, *args, **kwargs ):
        
        with self._lock:
            
            self._RefreshShares()
            
        
    
class MediaResultCache( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self._hash_ids_to_media_results = weakref.WeakValueDictionary()
        self._hashes_to_media_results = weakref.WeakValueDictionary()
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_data' )
        HG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        HG.client_controller.sub( self, 'NewForceRefreshTags', 'notify_new_force_refresh_tags_data' )
        HG.client_controller.sub( self, 'NewSiblings', 'notify_new_siblings_data' )
        
    
    def AddMediaResults( self, media_results ):
        
        with self._lock:
            
            for media_result in media_results:
                
                hash_id = media_result.GetHashId()
                hash = media_result.GetHash()
                
                self._hash_ids_to_media_results[ hash_id ] = media_result
                self._hashes_to_media_results[ hash ] = media_result
                
            
        
    
    def DropMediaResult( self, hash_id, hash ):
        
        with self._lock:
            
            if hash_id in self._hash_ids_to_media_results:
                
                del self._hash_ids_to_media_results[ hash_id ]
                
            
            if hash in self._hashes_to_media_results:
                
                del self._hashes_to_media_results[ hash ]
                
            
        
    
    def GetMediaResultsAndMissing( self, hash_ids ):
        
        with self._lock:
            
            media_results = []
            missing_hash_ids = []
            
            for hash_id in hash_ids:
                
                if hash_id in self._hash_ids_to_media_results:
                    
                    media_results.append( self._hash_ids_to_media_results[ hash_id ] )
                    
                else:
                    
                    missing_hash_ids.append( hash_id )
                    
                
            
            return ( media_results, missing_hash_ids )
            
        
    
    def NewForceRefreshTags( self ):
        
        # repo sync or advanced content update occurred, so we need complete refresh
        
        with self._lock:
            
            if len( self._hash_ids_to_media_results ) < 10000:
                
                hash_ids = list( self._hash_ids_to_media_results.keys() )
                
                for group_of_hash_ids in HydrusData.SplitListIntoChunks( hash_ids, 256 ):
                    
                    hash_ids_to_tags_managers = HG.client_controller.Read( 'force_refresh_tags_managers', group_of_hash_ids )
                    
                    for ( hash_id, tags_manager ) in list(hash_ids_to_tags_managers.items()):
                        
                        if hash_id in self._hash_ids_to_media_results:
                            
                            self._hash_ids_to_media_results[ hash_id ].SetTagsManager( tags_manager )
                            
                        
                    
                
                HG.client_controller.pub( 'notify_new_force_refresh_tags_gui' )
                
            
        
    
    def NewSiblings( self ):
        
        with self._lock:
            
            for media_result in list(self._hash_ids_to_media_results.values()):
                
                media_result.GetTagsManager().NewSiblings()
                
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        with self._lock:
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                for content_update in content_updates:
                    
                    hashes = content_update.GetHashes()
                    
                    for hash in hashes:
                        
                        if hash in self._hashes_to_media_results:
                            
                            self._hashes_to_media_results[ hash ].ProcessContentUpdate( service_key, content_update )
                            
                        
                    
                
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        with self._lock:
            
            for ( service_key, service_updates ) in list(service_keys_to_service_updates.items()):
                
                for service_update in service_updates:
                    
                    ( action, row ) = service_update.ToTuple()
                    
                    if action in ( HC.SERVICE_UPDATE_DELETE_PENDING, HC.SERVICE_UPDATE_RESET ):
                        
                        for media_result in list(self._hash_ids_to_media_results.values()):
                            
                            if action == HC.SERVICE_UPDATE_DELETE_PENDING:
                                
                                media_result.DeletePending( service_key )
                                
                            elif action == HC.SERVICE_UPDATE_RESET:
                                
                                media_result.ResetService( service_key )
                                
                            
                        
                    
                
            
        
    
    
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

class ParsingCache( object ):
    
    def __init__( self ):
        
        self._next_clean_cache_time = HydrusData.GetNow()
        
        self._html_to_soups = {}
        self._json_to_jsons = {}
        
        self._lock = threading.Lock()
        
    
    def _CleanCache( self ):
        
        if HydrusData.TimeHasPassed( self._next_clean_cache_time ):
            
            for cache in ( self._html_to_soups, self._json_to_jsons ):
                
                dead_datas = set()
                
                for ( data, ( last_accessed, parsed_object ) ) in list(cache.items()):
                    
                    if HydrusData.TimeHasPassed( last_accessed + 10 ):
                        
                        dead_datas.add( data )
                        
                    
                
                for dead_data in dead_datas:
                    
                    del cache[ dead_data ]
                    
                
            
            self._next_clean_cache_time = HydrusData.GetNow() + 5
            
        
    
    def CleanCache( self ):
        
        with self._lock:
            
            self._CleanCache()
            
        
    
    def GetJSON( self, json_text ):
        
        with self._lock:
            
            now = HydrusData.GetNow()
            
            if json_text not in self._json_to_jsons:
                
                json_object = json.loads( json_text )
                
                self._json_to_jsons[ json_text ] = ( now, json_object )
                
            
            ( last_accessed, json_object ) = self._json_to_jsons[ json_text ]
            
            if last_accessed != now:
                
                self._json_to_jsons[ json_text ] = ( now, json_object )
                
            
            if len( self._json_to_jsons ) > 10:
                
                self._CleanCache()
                
            
            return json_object
            
        
    
    def GetSoup( self, html ):
        
        with self._lock:
            
            now = HydrusData.GetNow()
            
            if html not in self._html_to_soups:
                
                soup = ClientParsing.GetSoup( html )
                
                self._html_to_soups[ html ] = ( now, soup )
                
            
            ( last_accessed, soup ) = self._html_to_soups[ html ]
            
            if last_accessed != now:
                
                self._html_to_soups[ html ] = ( now, soup )
                
            
            if len( self._html_to_soups ) > 10:
                
                self._CleanCache()
                
            
            return soup
            
        
    
class RenderedImageCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        cache_size = self._controller.options[ 'fullscreen_cache_size' ]
        cache_timeout = self._controller.new_options.GetInteger( 'image_cache_timeout' )
        
        self._data_cache = DataCache( self._controller, cache_size, timeout = cache_timeout )
        
    
    def Clear( self ):
        
        self._data_cache.Clear()
        
    
    def GetImageRenderer( self, media ):
        
        hash = media.GetHash()
        
        key = hash
        
        result = self._data_cache.GetIfHasData( key )
        
        if result is None:
            
            image_renderer = ClientRendering.ImageRenderer( media )
            
            self._data_cache.AddData( key, image_renderer )
            
        else:
            
            image_renderer = result
            
        
        return image_renderer
        
    
    def HasImageRenderer( self, hash ):
        
        key = hash
        
        return self._data_cache.HasData( key )
        
    
class ServicesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        self._keys_to_services = {}
        self._services_sorted = []
        
        self.RefreshServices()
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_data' )
        
    
    def _GetService( self, service_key ):
        
        try:
            
            return self._keys_to_services[ service_key ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'That service was not found!' )
            
        
    
    def _SetServices( self, services ):
        
        self._keys_to_services = { service.GetServiceKey() : service for service in services }
        
        self._keys_to_services[ CC.TEST_SERVICE_KEY ] = ClientServices.GenerateService( CC.TEST_SERVICE_KEY, HC.TEST_SERVICE, 'test service' )
        
        key = lambda s: s.GetName()
        
        self._services_sorted = list( services )
        self._services_sorted.sort( key = key )
        
    
    def Filter( self, service_keys, desired_types ):
        
        with self._lock:
            
            def func( service_key ):
                
                return self._keys_to_services[ service_key ].GetServiceType() in desired_types
                
            
            filtered_service_keys = list(filter( func, service_keys ))
            
            return filtered_service_keys
            
        
    
    def FilterValidServiceKeys( self, service_keys ):
        
        with self._lock:
            
            def func( service_key ):
                
                return service_key in self._keys_to_services
                
            
            filtered_service_keys = list(filter( func, service_keys ))
            
            return filtered_service_keys
            
        
    
    def GetName( self, service_key ):
        
        with self._lock:
            
            service = self._GetService( service_key )
            
            return service.GetName()
            
        
    
    def GetService( self, service_key ):
        
        with self._lock:
            
            return self._GetService( service_key )
            
        
    
    def GetServiceType( self, service_key ):
        
        with self._lock:
            
            return self._GetService( service_key ).GetServiceType()
            
        
    
    def GetServiceKeyFromName( self, allowed_types, service_name ):
        
        with self._lock:
            
            for service in self._services_sorted:
                
                if service.GetServiceType() in allowed_types and service.GetName() == service_name:
                    
                    return service.GetServiceKey()
                    
                
            
            raise HydrusExceptions.DataMissing()
            
        
    
    def GetServiceKeys( self, desired_types = HC.ALL_SERVICES ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for ( service_key, service ) in list(self._keys_to_services.items()) if service.GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def GetServices( self, desired_types = HC.ALL_SERVICES, randomised = True ):
        
        with self._lock:
            
            def func( service ):
                
                return service.GetServiceType() in desired_types
                
            
            services = list(filter( func, self._services_sorted ))
            
            if randomised:
                
                random.shuffle( services )
                
            
            return services
            
        
    
    def RefreshServices( self ):
        
        with self._lock:
            
            services = self._controller.Read( 'services' )
            
            self._SetServices( services )
            
        
    
    def ServiceExists( self, service_key ):
        
        with self._lock:
            
            return service_key in self._keys_to_services
            
        
    
class TagCensorshipManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self.RefreshData()
        
        self._controller.sub( self, 'RefreshData', 'notify_new_tag_censorship' )
        
    
    def _CensorshipMatches( self, tag, blacklist, censorships ):
        
        if blacklist:
            
            return not HydrusTags.CensorshipMatch( tag, censorships )
            
        else:
            
            return HydrusTags.CensorshipMatch( tag, censorships )
            
        
    
    def GetInfo( self, service_key ):
        
        if service_key in self._service_keys_to_info: return self._service_keys_to_info[ service_key ]
        else: return ( True, set() )
        
    
    def RefreshData( self ):
        
        rows = self._controller.Read( 'tag_censorship' )
        
        self._service_keys_to_info = { service_key : ( blacklist, censorships ) for ( service_key, blacklist, censorships ) in rows }
        
    
    def FilterPredicates( self, service_key, predicates ):
        
        for service_key_lookup in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key_lookup in self._service_keys_to_info:
                
                ( blacklist, censorships ) = self._service_keys_to_info[ service_key_lookup ]
                
                predicates = [ predicate for predicate in predicates if predicate.GetType() != HC.PREDICATE_TYPE_TAG or self._CensorshipMatches( predicate.GetValue(), blacklist, censorships ) ]
                
            
        
        return predicates
        
    
    def FilterStatusesToPairs( self, service_key, statuses_to_pairs ):
        
        for service_key_lookup in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key_lookup in self._service_keys_to_info:
                
                ( blacklist, censorships ) = self._service_keys_to_info[ service_key_lookup ]
                
                new_statuses_to_pairs = HydrusData.default_dict_set()
                
                for ( status, pairs ) in list(statuses_to_pairs.items()):
                    
                    new_statuses_to_pairs[ status ] = { ( one, two ) for ( one, two ) in pairs if self._CensorshipMatches( one, blacklist, censorships ) and self._CensorshipMatches( two, blacklist, censorships ) }
                    
                
                statuses_to_pairs = new_statuses_to_pairs
                
            
        
        return statuses_to_pairs
        
    
    def FilterServiceKeysToStatusesToTags( self, service_keys_to_statuses_to_tags ):
        
        if CC.COMBINED_TAG_SERVICE_KEY in self._service_keys_to_info:
            
            ( blacklist, censorships ) = self._service_keys_to_info[ CC.COMBINED_TAG_SERVICE_KEY ]
            
            service_keys = list(service_keys_to_statuses_to_tags.keys())
            
            for service_key in service_keys:
                
                statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
                
                statuses = list(statuses_to_tags.keys())
                
                for status in statuses:
                    
                    tags = statuses_to_tags[ status ]
                    
                    statuses_to_tags[ status ] = { tag for tag in tags if self._CensorshipMatches( tag, blacklist, censorships ) }
                    
                
            
        
        for ( service_key, ( blacklist, censorships ) ) in list(self._service_keys_to_info.items()):
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            if service_key in service_keys_to_statuses_to_tags:
                
                statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
                
                statuses = list(statuses_to_tags.keys())
                
                for status in statuses:
                    
                    tags = statuses_to_tags[ status ]
                    
                    statuses_to_tags[ status ] = { tag for tag in tags if self._CensorshipMatches( tag, blacklist, censorships ) }
                    
                
            
        
        return service_keys_to_statuses_to_tags
        
    
    def FilterTags( self, service_key, tags ):
        
        for service_key_lookup in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key_lookup in self._service_keys_to_info:
                
                ( blacklist, censorships ) = self._service_keys_to_info[ service_key_lookup ]
                
                tags = { tag for tag in tags if self._CensorshipMatches( tag, blacklist, censorships ) }
                
            
        
        return tags
        
    
class TagParentsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._dirty = False
        self._refresh_job = None
        
        self._service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
        
        self._RefreshParents()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'NotifyNewParents', 'notify_new_parents' )
        
    
    def _RefreshParents( self ):
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_parents' )
        
        # first collapse siblings
        
        siblings_manager = self._controller.tag_siblings_manager
        
        collapsed_service_keys_to_statuses_to_pairs = collections.defaultdict( HydrusData.default_dict_set )
        
        for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            for ( status, pairs ) in statuses_to_pairs.items():
                
                pairs = siblings_manager.CollapsePairs( service_key, pairs )
                
                collapsed_service_keys_to_statuses_to_pairs[ service_key ][ status ] = pairs
                
            
        
        # now collapse current and pending
        
        service_keys_to_pairs_flat = HydrusData.default_dict_set()
        
        for ( service_key, statuses_to_pairs ) in list(collapsed_service_keys_to_statuses_to_pairs.items()):
            
            pairs_flat = statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
            
            service_keys_to_pairs_flat[ service_key ] = pairs_flat
            
        
        # now create the combined tag service
        
        combined_pairs_flat = set()
        
        for pairs_flat in service_keys_to_pairs_flat.values():
            
            combined_pairs_flat.update( pairs_flat )
            
        
        service_keys_to_pairs_flat[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_pairs_flat
        
        #
        
        service_keys_to_simple_children_to_parents = BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat )
        
        self._service_keys_to_children_to_parents = BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents )
        
    
    def ExpandPredicates( self, service_key, predicates, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        results = []
        
        with self._lock:
            
            for predicate in predicates:
                
                results.append( predicate )
                
                if predicate.GetType() == HC.PREDICATE_TYPE_TAG:
                    
                    tag = predicate.GetValue()
                    
                    parents = self._service_keys_to_children_to_parents[ service_key ][ tag ]
                    
                    for parent in parents:
                        
                        parent_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, parent )
                        
                        results.append( parent_predicate )
                        
                    
                
            
            return results
            
        
    
    def ExpandTags( self, service_key, tags, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            tags_results = set( tags )
            
            for tag in tags:
                
                tags_results.update( self._service_keys_to_children_to_parents[ service_key ][ tag ] )
                
            
            return tags_results
            
        
    
    def GetParents( self, service_key, tag, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            return self._service_keys_to_children_to_parents[ service_key ][ tag ]
            
        
    
    def NotifyNewParents( self ):
        
        with self._lock:
            
            self._dirty = True
            
            if self._refresh_job is not None:
                
                self._refresh_job.Cancel()
                
            
            self._refresh_job = self._controller.CallLater( 8.0, self.RefreshParentsIfDirty )
            
        
    
    def RefreshParentsIfDirty( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._RefreshParents()
                
                self._dirty = False
                
            
        
    
class TagSiblingsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._dirty = False
        self._refresh_job = None
        
        self._service_keys_to_siblings = collections.defaultdict( dict )
        self._service_keys_to_reverse_lookup = collections.defaultdict( dict )
        
        self._RefreshSiblings()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'NotifyNewSiblings', 'notify_new_siblings_data' )
        
    
    def _CollapseTags( self, service_key, tags ):
    
        siblings = self._service_keys_to_siblings[ service_key ]
        
        return { siblings[ tag ] if tag in siblings else tag for tag in tags }
        
    
    def _RefreshSiblings( self ):
        
        self._service_keys_to_siblings = collections.defaultdict( dict )
        self._service_keys_to_reverse_lookup = collections.defaultdict( dict )
        
        local_tags_pairs = set()
        
        tag_repo_pairs = set()
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_siblings' )
        
        for ( service_key, statuses_to_pairs ) in list(service_keys_to_statuses_to_pairs.items()):
            
            all_pairs = statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
            
            if service_key == CC.LOCAL_TAG_SERVICE_KEY:
                
                local_tags_pairs = set( all_pairs )
                
            else:
                
                tag_repo_pairs.update( all_pairs )
                
            
            siblings = CollapseTagSiblingPairs( [ all_pairs ] )
            
            self._service_keys_to_siblings[ service_key ] = siblings
            
            reverse_lookup = collections.defaultdict( list )
            
            for ( bad, good ) in list(siblings.items()):
                
                reverse_lookup[ good ].append( bad )
                
            
            self._service_keys_to_reverse_lookup[ service_key ] = reverse_lookup
            
        
        combined_siblings = CollapseTagSiblingPairs( [ local_tags_pairs, tag_repo_pairs ] )
        
        self._service_keys_to_siblings[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_siblings
        
        combined_reverse_lookup = collections.defaultdict( list )
        
        for ( bad, good ) in list(combined_siblings.items()):
            
            combined_reverse_lookup[ good ].append( bad )
            
        
        self._service_keys_to_reverse_lookup[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_reverse_lookup
        
        self._controller.pub( 'new_siblings_gui' )
        
    
    def CollapsePredicates( self, service_key, predicates, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            results = [ predicate for predicate in predicates if predicate.GetType() != HC.PREDICATE_TYPE_TAG ]
            
            tag_predicates = [ predicate for predicate in predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG ]
            
            tags_to_predicates = { predicate.GetValue() : predicate for predicate in predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG }
            
            tags = list(tags_to_predicates.keys())
            
            tags_to_include_in_results = set()
            
            for tag in tags:
                
                if tag in siblings:
                    
                    old_tag = tag
                    old_predicate = tags_to_predicates[ old_tag ]
                    
                    new_tag = siblings[ old_tag ]
                    
                    if new_tag not in tags_to_predicates:
                        
                        ( old_pred_type, old_value, old_inclusive ) = old_predicate.GetInfo()
                        
                        new_predicate = ClientSearch.Predicate( old_pred_type, new_tag, old_inclusive )
                        
                        tags_to_predicates[ new_tag ] = new_predicate
                        
                        tags_to_include_in_results.add( new_tag )
                        
                    
                    new_predicate = tags_to_predicates[ new_tag ]
                    
                    new_predicate.AddCounts( old_predicate )
                    
                else:
                    
                    tags_to_include_in_results.add( tag )
                    
                
            
            results.extend( [ tags_to_predicates[ tag ] for tag in tags_to_include_in_results ] )
            
            return results
            
        
    
    def CollapsePairs( self, service_key, pairs, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            result = set()
            
            for ( a, b ) in pairs:
                
                if a in siblings:
                    
                    a = siblings[ a ]
                    
                
                if b in siblings:
                    
                    b = siblings[ b ]
                    
                
                result.add( ( a, b ) )
                
            
            return result
            
        
    
    def CollapseStatusesToTags( self, service_key, statuses_to_tags, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            statuses = list(statuses_to_tags.keys())
            
            new_statuses_to_tags = HydrusData.default_dict_set()
            
            for status in statuses:
                
                new_statuses_to_tags[ status ] = self._CollapseTags( service_key, statuses_to_tags[ status ] )
                
            
            return new_statuses_to_tags
            
        
    
    def CollapseTag( self, service_key, tag, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            if tag in siblings:
                
                return siblings[ tag ]
                
            else:
                
                return tag
                
            
        
    
    def CollapseTags( self, service_key, tags, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            return self._CollapseTags( service_key, tags )
            
        
    
    def CollapseTagsToCount( self, service_key, tags_to_count, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            results = collections.Counter()
            
            for ( tag, count ) in list(tags_to_count.items()):
                
                if tag in siblings:
                    
                    tag = siblings[ tag ]
                    
                
                results[ tag ] += count
                
            
            return results
            
        
    
    def GetSibling( self, service_key, tag, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            if tag in siblings:
                
                return siblings[ tag ]
                
            else:
                
                return None
                
            
        
    
    def GetAllSiblings( self, service_key, tag, service_strict = False ):
        
        if not service_strict and self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            reverse_lookup = self._service_keys_to_reverse_lookup[ service_key ]
            
            if tag in siblings:
                
                best_tag = siblings[ tag ]
                
            elif tag in reverse_lookup:
                
                best_tag = tag
                
            else:
                
                return [ tag ]
                
            
            all_siblings = list( reverse_lookup[ best_tag ] )
            
            all_siblings.append( best_tag )
            
            return all_siblings
            
        
    
    def NotifyNewSiblings( self ):
        
        with self._lock:
            
            self._dirty = True
            
            if self._refresh_job is not None:
                
                self._refresh_job.Cancel()
                
            
            self._refresh_job = self._controller.CallLater( 8.0, self.RefreshSiblingsIfDirty )
            
        
    
    def RefreshSiblingsIfDirty( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._RefreshSiblings()
                
                self._dirty = False
                
                self._controller.pub( 'notify_new_siblings_gui' )
                
            
        
    
class ThumbnailCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        cache_size = self._controller.options[ 'thumbnail_cache_size' ]
        cache_timeout = self._controller.new_options.GetInteger( 'thumbnail_cache_timeout' )
        
        self._data_cache = DataCache( self._controller, cache_size, timeout = cache_timeout )
        
        self._magic_mime_thumbnail_ease_score_lookup = {}
        
        self._InitialiseMagicMimeScores()
        
        self._lock = threading.Lock()
        
        self._thumbnail_error_occurred = False
        
        self._waterfall_queue_quick = set()
        self._waterfall_queue = []
        
        self._delayed_regeneration_queue_quick = set()
        self._delayed_regeneration_queue = []
        
        self._waterfall_event = threading.Event()
        
        self._special_thumbs = {}
        
        self.Clear()
        
        self._controller.CallToThreadLongRunning( self.DAEMONWaterfall )
        
        self._controller.sub( self, 'Clear', 'clear_all_thumbnails' )
        self._controller.sub( self, 'ClearThumbnails', 'clear_thumbnails' )
        
    
    def _GetThumbnailHydrusBitmap( self, display_media ):
        
        bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
        
        hash = display_media.GetHash()
        mime = display_media.GetMime()
        
        locations_manager = display_media.GetLocationsManager()
        
        try:
            
            path = self._controller.client_files_manager.GetThumbnailPath( display_media )
            
        except HydrusExceptions.FileMissingException as e:
            
            if locations_manager.IsLocal():
                
                summary = 'Unable to get thumbnail for file {}.'.format( hash.hex() )
                
                self._HandleThumbnailException( e, summary )
                
            
            return self._special_thumbs[ 'hydrus' ]
            
        
        try:
            
            numpy_image = ClientImageHandling.GenerateNumPyImage( path, mime )
            
        except Exception as e:
            
            try:
                
                # file is malformed, let's force a regen
                self._controller.files_maintenance_manager.RunJobImmediately( [ display_media ], ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL, pub_job_key = False )
                
            except Exception as e:
                
                summary = 'The thumbnail for file ' + hash.hex() + ' was not loadable. An attempt to regenerate it failed.'
                
                self._HandleThumbnailException( e, summary )
                
                return self._special_thumbs[ 'hydrus' ]
                
            
            try:
                
                numpy_image = ClientImageHandling.GenerateNumPyImage( path, mime )
                
            except Exception as e:
                
                summary = 'The thumbnail for file ' + hash.hex() + ' was not loadable. It was regenerated, but that file would not render either. Your image libraries or hard drive connection are unreliable. Please inform the hydrus developer what has happened.'
                
                self._HandleThumbnailException( e, summary )
                
                return self._special_thumbs[ 'hydrus' ]
                
            
        
        ( current_width, current_height ) = HydrusImageHandling.GetResolutionNumPy( numpy_image )
        
        ( media_width, media_height ) = display_media.GetResolution()
        
        ( expected_width, expected_height ) = HydrusImageHandling.GetThumbnailResolution( ( media_width, media_height ), bounding_dimensions )
        
        exactly_as_expected = current_width == expected_width and current_height == expected_height
        
        rotation_exception = current_width == expected_height and current_height == expected_width
        
        correct_size = exactly_as_expected or rotation_exception
        
        if not correct_size:
            
            it_is_definitely_too_big = current_width >= expected_width and current_height >= expected_height
            
            if it_is_definitely_too_big:
                
                if HG.file_report_mode:
                    
                    HydrusData.ShowText( 'Thumbnail {} too big.'.format( hash.hex() ) )
                    
                
                # the thumb we have is larger than desired. we can use it to generate what we actually want without losing significant data
                
                # this is _resize_, not _thumbnail_, because we already know the dimensions we want
                # and in some edge cases, doing getthumbresolution on existing thumb dimensions results in float/int conversion imprecision and you get 90px/91px regen cycles that never get fixed
                numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, ( expected_width, expected_height ) )
                
                if locations_manager.IsLocal():
                    
                    # we have the master file, so it is safe to save our resized thumb back to disk since we can regen from source if needed
                    
                    if HG.file_report_mode:
                        
                        HydrusData.ShowText( 'Thumbnail {} too big, saving back to disk.'.format( hash.hex() ) )
                        
                    
                    try:
                        
                        try:
                            
                            thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesNumPy( numpy_image, mime )
                            
                        except HydrusExceptions.CantRenderWithCVException:
                            
                            thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesFromStaticImagePath( path, ( expected_width, expected_height ), mime )
                            
                        
                    except:
                        
                        summary = 'The thumbnail for file {} was too large, but an attempt to shrink it failed.'.format( hash.hex() )
                        
                        self._HandleThumbnailException( e, summary )
                        
                        return self._special_thumbs[ 'hydrus' ]
                        
                    
                    try:
                        
                        self._controller.client_files_manager.AddThumbnailFromBytes( hash, thumbnail_bytes, silent = True )
                        
                        self._controller.files_maintenance_manager.ClearJobs( { hash }, ClientFiles.REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL )
                        
                    except:
                        
                        summary = 'The thumbnail for file {} was too large, but an attempt to save back the shrunk file failed.'.format( hash.hex() )
                        
                        self._HandleThumbnailException( e, summary )
                        
                        return self._special_thumbs[ 'hydrus' ]
                        
                    
                
            else:
                
                # the thumb we have is either too small or completely messed up due to a previous ratio misparse
                
                media_is_same_size_as_current_thumb = current_width == media_width and current_height == media_height
                
                if media_is_same_size_as_current_thumb:
                    
                    # the thumb is smaller than expected, but this is a 32x32 pixilart image or whatever, so no need to scale
                    
                    if HG.file_report_mode:
                        
                        HydrusData.ShowText( 'Thumbnail {} too small due to small source file.'.format( hash.hex() ) )
                        
                    
                    pass
                    
                else:
                    
                    numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, ( expected_width, expected_height ) )
                    
                    if locations_manager.IsLocal():
                        
                        # we have the master file, so we should regen the thumb from source
                        
                        if HG.file_report_mode:
                            
                            HydrusData.ShowText( 'Thumbnail {} too small, scheduling regeneration from source.'.format( hash.hex() ) )
                            
                        
                        delayed_item = display_media.GetMediaResult()
                        
                        with self._lock:
                            
                            if delayed_item not in self._delayed_regeneration_queue_quick:
                                
                                self._delayed_regeneration_queue_quick.add( delayed_item )
                                
                                self._delayed_regeneration_queue.append( delayed_item )
                                
                            
                        
                    else:
                        
                        # we do not have the master file, so we have to scale up from what we have
                        
                        if HG.file_report_mode:
                            
                            HydrusData.ShowText( 'Thumbnail {} was too small, only scaling up due to no local source.'.format( hash.hex() ) )
                            
                        
                    
                
            
        
        hydrus_bitmap = ClientRendering.GenerateHydrusBitmapFromNumPyImage( numpy_image )
        
        return hydrus_bitmap
        
    
    def _HandleThumbnailException( self, e, summary ):
        
        if self._thumbnail_error_occurred:
            
            HydrusData.Print( summary )
            
        else:
            
            self._thumbnail_error_occurred = True
            
            message = 'A thumbnail error has occurred. The problem thumbnail will appear with the default \'hydrus\' symbol. You may need to take hard drive recovery actions, and if the error is not obviously fixable, you can contact hydrus dev for additional help. Specific information for this first error follows. Subsequent thumbnail errors in this session will be silently printed to the log.'
            message += os.linesep * 2
            message += str( e )
            message += os.linesep * 2
            message += summary
            
            HydrusData.ShowText( message )
            
        
    
    def _InitialiseMagicMimeScores( self ):
        
        # let's render our thumbs in order of ease of regeneration, so we rush what we can to screen as fast as possible and leave big vids until the end
        
        for mime in HC.ALLOWED_MIMES:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 5
            
        
        # default filetype thumbs are easiest
        
        self._magic_mime_thumbnail_ease_score_lookup[ None ] = 0
        self._magic_mime_thumbnail_ease_score_lookup[ HC.APPLICATION_UNKNOWN ] = 0
        
        for mime in HC.APPLICATIONS:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 0
            
        
        for mime in HC.AUDIO:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 0
            
        
        # images a little trickier
        
        for mime in HC.IMAGES:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 1
            
        
        # override because these are a bit more
        self._magic_mime_thumbnail_ease_score_lookup[ HC.IMAGE_APNG ] = 2
        self._magic_mime_thumbnail_ease_score_lookup[ HC.IMAGE_GIF ] = 2
        
        # ffmpeg hellzone
        
        for mime in HC.VIDEO:
            
            self._magic_mime_thumbnail_ease_score_lookup[ mime ] = 3
            
        
    
    def _RecalcQueues( self ):
        
        # here we sort by the hash since this is both breddy random and more likely to access faster on a well defragged hard drive!
        # and now with the magic mime order
        
        def sort_waterfall( item ):
            
            ( page_key, media ) = item
            
            display_media = media.GetDisplayMedia()
            
            magic_score = self._magic_mime_thumbnail_ease_score_lookup[ display_media.GetMime() ]
            hash = display_media.GetHash()
            
            return ( magic_score, hash )
            
        
        self._waterfall_queue = list( self._waterfall_queue_quick )
        
        # we pop off the end, so reverse
        self._waterfall_queue.sort( key = sort_waterfall, reverse = True )
        
        def sort_regen( item ):
            
            media_result = item
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            magic_score = self._magic_mime_thumbnail_ease_score_lookup[ mime ]
            
            return ( magic_score, hash )
            
        
        self._delayed_regeneration_queue = list( self._delayed_regeneration_queue_quick )
        
        # we pop off the end, so reverse
        self._delayed_regeneration_queue.sort( key = sort_regen, reverse = True )
        
    
    def CancelWaterfall( self, page_key, medias ):
        
        with self._lock:
            
            self._waterfall_queue_quick.difference_update( ( ( page_key, media ) for media in medias ) )
            
            cancelled_media_results = { media.GetDisplayMedia().GetMediaResult() for media in medias }
            
            outstanding_delayed_hashes = { media_result.GetHash() for media_result in cancelled_media_results if media_result in self._delayed_regeneration_queue_quick }
            
            if len( outstanding_delayed_hashes ) > 0:
                
                self._controller.files_maintenance_manager.ScheduleJob( outstanding_delayed_hashes, ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
                
            
            self._delayed_regeneration_queue_quick.difference_update( cancelled_media_results )
            
            self._RecalcQueues()
            
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._data_cache.Clear()
            
            self._special_thumbs = {}
            
            names = [ 'hydrus', 'pdf', 'psd', 'audio', 'video', 'zip' ]
            
            bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
            
            for name in names:
                
                path = os.path.join( HC.STATIC_DIR, name + '.png' )
                
                numpy_image = ClientImageHandling.GenerateNumPyImage( path, HC.IMAGE_PNG )
                
                numpy_image_resolution = HydrusImageHandling.GetResolutionNumPy( numpy_image )
                
                target_resolution = HydrusImageHandling.GetThumbnailResolution( numpy_image_resolution, bounding_dimensions )
                
                numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, target_resolution )
                
                hydrus_bitmap = ClientRendering.GenerateHydrusBitmapFromNumPyImage( numpy_image )
                
                self._special_thumbs[ name ] = hydrus_bitmap
                
            
            self._controller.pub( 'redraw_all_thumbnails' )
            
            self._waterfall_queue_quick = set()
            self._delayed_regeneration_queue_quick = set()
            
            self._RecalcQueues()
            
        
    
    def ClearThumbnails( self, hashes ):
        
        with self._lock:
            
            for hash in hashes:
                
                self._data_cache.DeleteData( hash )
                
            
        
    
    def DoingWork( self ):
        
        with self._lock:
            
            return len( self._waterfall_queue ) > 0
            
        
    
    def GetThumbnail( self, media ):
        
        try:
            
            display_media = media.GetDisplayMedia()
            
        except:
            
            # sometimes media can get switched around during a collect event, and if this happens during waterfall, we have a problem here
            # just return for now, we'll see how it goes
            
            return self._special_thumbs[ 'hydrus' ]
            
        
        locations_manager = display_media.GetLocationsManager()
        
        if locations_manager.ShouldIdeallyHaveThumbnail():
            
            mime = display_media.GetMime()
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                hash = display_media.GetHash()
                
                result = self._data_cache.GetIfHasData( hash )
                
                if result is None:
                    
                    try:
                        
                        hydrus_bitmap = self._GetThumbnailHydrusBitmap( display_media )
                        
                    except:
                        
                        hydrus_bitmap = self._special_thumbs[ 'hydrus' ]
                        
                    
                    self._data_cache.AddData( hash, hydrus_bitmap )
                    
                else:
                    
                    hydrus_bitmap = result
                    
                
                return hydrus_bitmap
                
            elif mime in HC.AUDIO: return self._special_thumbs[ 'audio' ]
            elif mime in HC.VIDEO: return self._special_thumbs[ 'video' ]
            elif mime == HC.APPLICATION_PDF: return self._special_thumbs[ 'pdf' ]
            elif mime == HC.APPLICATION_PSD: return self._special_thumbs[ 'psd' ]
            elif mime in HC.ARCHIVES: return self._special_thumbs[ 'zip' ]
            else: return self._special_thumbs[ 'hydrus' ]
            
        else:
            
            return self._special_thumbs[ 'hydrus' ]
            
        
    
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
            
            self._RecalcQueues()
            
        
        self._waterfall_event.set()
        
    
    def DAEMONWaterfall( self ):
        
        last_paused = HydrusData.GetNowPrecise()
        
        while not HydrusThreading.IsThreadShuttingDown():
            
            time.sleep( 0.00001 )
            
            with self._lock:
                
                do_wait = len( self._waterfall_queue ) == 0 and len( self._delayed_regeneration_queue ) == 0
                
            
            if do_wait:
                
                self._waterfall_event.wait( 1 )
                
                self._waterfall_event.clear()
                
                last_paused = HydrusData.GetNowPrecise()
                
            
            start_time = HydrusData.GetNowPrecise()
            stop_time = start_time + 0.005 # a bit of a typical frame
            
            page_keys_to_rendered_medias = collections.defaultdict( list )
            
            while not HydrusData.TimeHasPassedPrecise( stop_time ):
                
                with self._lock:
                    
                    if len( self._waterfall_queue ) == 0:
                        
                        break
                        
                    
                    result = self._waterfall_queue.pop()
                    
                    self._waterfall_queue_quick.discard( result )
                    
                
                ( page_key, media ) = result
                
                self.GetThumbnail( media )
                
                page_keys_to_rendered_medias[ page_key ].append( media )
                
            
            if len( page_keys_to_rendered_medias ) > 0:
                
                for ( page_key, rendered_medias ) in page_keys_to_rendered_medias.items():
                    
                    self._controller.pub( 'waterfall_thumbnails', page_key, rendered_medias )
                    
                
                time.sleep( 0.00001 )
                
            
            # now we will do regen if appropriate
            
            with self._lock:
                
                # got more important work or no work to do
                if len( self._waterfall_queue ) > 0 or len( self._delayed_regeneration_queue ) == 0 or HG.client_controller.CurrentlyPubSubbing():
                    
                    continue
                    
                
                media_result = self._delayed_regeneration_queue.pop()
                
                self._delayed_regeneration_queue_quick.discard( media_result )
                
            
            if HG.file_report_mode:
                
                hash = media_result.GetHash()
                
                HydrusData.ShowText( 'Thumbnail {} now regenerating from source.'.format( hash.hex() ) )
                
            
            try:
                
                self._controller.files_maintenance_manager.RunJobImmediately( [ media_result ], ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL, pub_job_key = False )
                
            except HydrusExceptions.FileMissingException:
                
                pass
                
            except Exception as e:
                
                hash = media_result.GetHash()
                
                summary = 'The thumbnail for file {} was incorrect, but a later attempt to regenerate it or load the new file back failed.'.format( hash.hex() )
                
                self._HandleThumbnailException( e, summary )
                
            
        
    
class UndoManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._commands = []
        self._inverted_commands = []
        self._current_index = 0
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'Undo', 'undo' )
        self._controller.sub( self, 'Redo', 'redo' )
        
    
    def _FilterServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        filtered_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
            
            filtered_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_UNDELETE, HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ):
                        
                        continue
                        
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    if action in ( HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ):
                        
                        continue
                        
                    
                else:
                    
                    continue
                    
                
                filtered_content_update = HydrusData.ContentUpdate( data_type, action, row )
                
                filtered_content_updates.append( filtered_content_update )
                
            
            if len( filtered_content_updates ) > 0:
                
                filtered_service_keys_to_content_updates[ service_key ] = filtered_content_updates
                
            
        
        return filtered_service_keys_to_content_updates
        
    
    def _InvertServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        inverted_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
            
            inverted_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                inverted_row = row
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action == HC.CONTENT_UPDATE_ARCHIVE: inverted_action = HC.CONTENT_UPDATE_INBOX
                    elif action == HC.CONTENT_UPDATE_INBOX: inverted_action = HC.CONTENT_UPDATE_ARCHIVE
                    elif action == HC.CONTENT_UPDATE_PEND: inverted_action = HC.CONTENT_UPDATE_RESCIND_PEND
                    elif action == HC.CONTENT_UPDATE_RESCIND_PEND: inverted_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_PETITION: inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    if action == HC.CONTENT_UPDATE_ADD: inverted_action = HC.CONTENT_UPDATE_DELETE
                    elif action == HC.CONTENT_UPDATE_DELETE: inverted_action = HC.CONTENT_UPDATE_ADD
                    elif action == HC.CONTENT_UPDATE_PEND: inverted_action = HC.CONTENT_UPDATE_RESCIND_PEND
                    elif action == HC.CONTENT_UPDATE_RESCIND_PEND: inverted_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_PETITION: inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                    
                
                inverted_content_update = HydrusData.ContentUpdate( data_type, inverted_action, inverted_row )
                
                inverted_content_updates.append( inverted_content_update )
                
            
            inverted_service_keys_to_content_updates[ service_key ] = inverted_content_updates
            
        
        return inverted_service_keys_to_content_updates
        
    
    def AddCommand( self, action, *args, **kwargs ):
        
        with self._lock:
            
            inverted_action = action
            inverted_args = args
            inverted_kwargs = kwargs
            
            if action == 'content_updates':
                
                ( service_keys_to_content_updates, ) = args
                
                service_keys_to_content_updates = self._FilterServiceKeysToContentUpdates( service_keys_to_content_updates )
                
                if len( service_keys_to_content_updates ) == 0: return
                
                inverted_service_keys_to_content_updates = self._InvertServiceKeysToContentUpdates( service_keys_to_content_updates )
                
                if len( inverted_service_keys_to_content_updates ) == 0: return
                
                inverted_args = ( inverted_service_keys_to_content_updates, )
                
            else: return
            
            self._commands = self._commands[ : self._current_index ]
            self._inverted_commands = self._inverted_commands[ : self._current_index ]
            
            self._commands.append( ( action, args, kwargs ) )
            
            self._inverted_commands.append( ( inverted_action, inverted_args, inverted_kwargs ) )
            
            self._current_index += 1
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
    def GetUndoRedoStrings( self ):
        
        with self._lock:
            
            ( undo_string, redo_string ) = ( None, None )
            
            if self._current_index > 0:
                
                undo_index = self._current_index - 1
                
                ( action, args, kwargs ) = self._commands[ undo_index ]
                
                if action == 'content_updates':
                    
                    ( service_keys_to_content_updates, ) = args
                    
                    undo_string = 'undo ' + ClientData.ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates )
                    
                
            
            if len( self._commands ) > 0 and self._current_index < len( self._commands ):
                
                redo_index = self._current_index
                
                ( action, args, kwargs ) = self._commands[ redo_index ]
                
                if action == 'content_updates':
                    
                    ( service_keys_to_content_updates, ) = args
                    
                    redo_string = 'redo ' + ClientData.ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates )
                    
                
            
            return ( undo_string, redo_string )
            
        
    
    def Undo( self ):
        
        action = None
        
        with self._lock:
            
            if self._current_index > 0:
                
                self._current_index -= 1
                
                ( action, args, kwargs ) = self._inverted_commands[ self._current_index ]
                
        
        if action is not None:
            
            self._controller.WriteSynchronous( action, *args, **kwargs )
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
    def Redo( self ):
        
        action = None
        
        with self._lock:
            
            if len( self._commands ) > 0 and self._current_index < len( self._commands ):
                
                ( action, args, kwargs ) = self._commands[ self._current_index ]
                
                self._current_index += 1
                
            
        
        if action is not None:
            
            self._controller.WriteSynchronous( action, *args, **kwargs )
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
