import ClientDefaults
import ClientFiles
import ClientNetworking
import ClientRendering
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusPaths
import HydrusSessions
import itertools
import os
import random
import Queue
import shutil
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

# important thing here, and reason why it is recursive, is because we want to preserve the parent-grandparent interleaving
def BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents ):
    
    def AddParents( simple_children_to_parents, children_to_parents, child, parents ):
        
        for parent in parents:
            
            if parent not in children_to_parents[ child ]:
                
                children_to_parents[ child ].append( parent )
                
            
            if parent in simple_children_to_parents:
                
                grandparents = simple_children_to_parents[ parent ]
                
                AddParents( simple_children_to_parents, children_to_parents, child, grandparents )
                
            
        
    
    service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
    
    for ( service_key, simple_children_to_parents ) in service_keys_to_simple_children_to_parents.items():
        
        children_to_parents = service_keys_to_children_to_parents[ service_key ]
        
        for ( child, parents ) in simple_children_to_parents.items():
            
            AddParents( simple_children_to_parents, children_to_parents, child, parents )
            
        
    
    return service_keys_to_children_to_parents
    
def BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat ):
    
    service_keys_to_simple_children_to_parents = collections.defaultdict( HydrusData.default_dict_set )
    
    for ( service_key, pairs ) in service_keys_to_pairs_flat.items():
        
        service_keys_to_simple_children_to_parents[ service_key ] = BuildSimpleChildrenToParents( pairs )
        
    
    return service_keys_to_simple_children_to_parents
    
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
    
def LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
    
    potential_loop_paths = { parent }
    
    while len( potential_loop_paths.intersection( simple_children_to_parents.keys() ) ) > 0:
        
        new_potential_loop_paths = set()
        
        for potential_loop_path in potential_loop_paths.intersection( simple_children_to_parents.keys() ):
            
            new_potential_loop_paths.update( simple_children_to_parents[ potential_loop_path ] )
            
        
        potential_loop_paths = new_potential_loop_paths
        
        if child in potential_loop_paths: return True
        
    
    return False
    
class ClientFilesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._prefixes_to_locations = {}
        
        self._bad_error_occured = False
        
        self._Reinit()
        
    
    def _GetLocation( self, hash ):
        
        hash_encoded = hash.encode( 'hex' )
        
        prefix = hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        return location
        
    
    def _GetRecoverTuple( self ):
        
        paths = { path for path in self._prefixes_to_locations.values() }
        
        for path in paths:
            
            for prefix in HydrusData.IterateHexPrefixes():
                
                correct_path = self._prefixes_to_locations[ prefix ]
                
                if path != correct_path and os.path.exists( os.path.join( path, prefix ) ):
                    
                    return ( prefix, path, correct_path )
                    
                
            
        
        return None
        
    
    def _GetRebalanceTuple( self ):
        
        paths_to_ideal_weights = self._controller.GetNewOptions().GetClientFilesLocationsToIdealWeights()
        
        total_weight = sum( paths_to_ideal_weights.values() )
        
        paths_to_normalised_ideal_weights = { path : weight / total_weight for ( path, weight ) in paths_to_ideal_weights.items() }
        
        current_paths_to_normalised_weights = collections.defaultdict( lambda: 0 )
        
        for ( prefix, path ) in self._prefixes_to_locations.items():
            
            current_paths_to_normalised_weights[ path ] += 1.0 / 256
            
        
        for path in current_paths_to_normalised_weights.keys():
            
            if path not in paths_to_normalised_ideal_weights:
                
                paths_to_normalised_ideal_weights[ path ] = 0.0
                
            
        
        #
        
        overweight_paths = []
        underweight_paths = []
        
        for ( path, ideal_weight ) in paths_to_normalised_ideal_weights.items():
            
            if path in current_paths_to_normalised_weights:
                
                current_weight = current_paths_to_normalised_weights[ path ]
                
                if current_weight < ideal_weight:
                    
                    underweight_paths.append( path )
                    
                elif current_weight >= ideal_weight + 1.0 / 256:
                    
                    overweight_paths.append( path )
                    
                
            else:
                
                underweight_paths.append( path )
                
            
        
        #
        
        if len( underweight_paths ) == 0 or len( overweight_paths ) == 0:
            
            return None
            
        else:
            
            overweight_path = overweight_paths.pop( 0 )
            underweight_path = underweight_paths.pop( 0 )
            
            prefixes_and_paths = self._prefixes_to_locations.items()
            
            random.shuffle( prefixes_and_paths )
            
            for ( prefix, path ) in prefixes_and_paths:
                
                if path == overweight_path:
                    
                    return ( prefix, overweight_path, underweight_path )
                    
                
            
        
    
    def _IterateAllFilePaths( self ):
        
        for ( prefix, location ) in self._prefixes_to_locations.items():
            
            dir = os.path.join( location, prefix )
            
            next_filenames = os.listdir( dir )
            
            for filename in next_filenames:
                
                yield os.path.join( dir, filename )
                
            
        
    
    def _Reinit( self ):
        
        self._prefixes_to_locations = self._controller.Read( 'client_files_locations' )
        
        for ( prefix, location ) in self._prefixes_to_locations.items():
            
            if os.path.exists( location ):
                
                dir = os.path.join( location, prefix )
                
                if not os.path.exists( dir ):
                    
                    HydrusData.DebugPrint( 'The location ' + dir + ' was not found, so it was created.' )
                    
                    os.makedirs( dir )
                    
                
            else:
                
                self._bad_error_occured = True
                
                HydrusData.DebugPrint( 'The location ' + location + ' was not found during file manager init. A graphical error should follow.' )
                
            
        
    
    def GetExpectedFilePath( self, hash, mime ):
        
        with self._lock:
            
            location = self._GetLocation( hash )
            
            return ClientFiles.GetExpectedFilePath( location, hash, mime )
            
        
    
    def GetFilePath( self, hash, mime = None ):
        
        with self._lock:
            
            location = self._GetLocation( hash )
            
            return ClientFiles.GetFilePath( location, hash, mime )
            
        
    
    def IterateAllFileHashes( self ):
        
        with self._lock:
            
            for path in self._IterateAllFilePaths():
                
                ( base, filename ) = os.path.split( path )
                
                result = filename.split( '.', 1 )
                
                if len( result ) != 2: continue
                
                ( hash_encoded, ext ) = result
                
                try: hash = hash_encoded.decode( 'hex' )
                except TypeError: continue
                
                yield hash
                
            
        
    
    def IterateAllFilePaths( self ):
        
        with self._lock:
            
            for path in self._IterateAllFilePaths():
                
                yield path
                
            
        
    
    def Rebalance( self, partial = True, stop_time = None ):
        
        if self._bad_error_occured:
            
            return
            
        
        with self._lock:
            
            rebalance_tuple = self._GetRebalanceTuple()
            
            while rebalance_tuple is not None:
                
                ( prefix, overweight_path, underweight_path ) = rebalance_tuple
                
                text = 'Moving \'' + prefix + '\' files from ' + overweight_path + ' to ' + underweight_path
                
                if partial:
                    
                    HydrusData.Print( text )
                    
                else:
                    
                    self._controller.pub( 'splash_set_status_text', text )
                    HydrusData.ShowText( text )
                    
                
                self._controller.Write( 'relocate_client_files', prefix, overweight_path, underweight_path )
                
                self._Reinit()
                
                if partial:
                    
                    break
                    
                
                if stop_time is not None and HydrusData.TimeHasPassed( stop_time ):
                    
                    return
                    
                
                rebalance_tuple = self._GetRebalanceTuple()
                
            
            recover_tuple = self._GetRecoverTuple()
            
            while recover_tuple is not None:
                
                ( prefix, incorrect_path, correct_path ) = recover_tuple
                
                text = 'Recovering \'' + prefix + '\' files from ' + incorrect_path + ' to ' + correct_path
                
                if partial:
                    
                    HydrusData.Print( text )
                    
                else:
                    
                    self._controller.pub( 'splash_set_status_text', text )
                    HydrusData.ShowText( text )
                    
                
                full_incorrect_path = os.path.join( incorrect_path, prefix )
                full_correct_path = os.path.join( correct_path, prefix )
                
                HydrusPaths.CopyAndMergeTree( full_incorrect_path, full_correct_path )
                
                try: HydrusPaths.RecyclePath( full_incorrect_path )
                except:
                    
                    HydrusData.ShowText( 'After recovering some files, attempting to remove ' + full_incorrect_path + ' failed.' )
                    
                    return
                    
                
                if partial:
                    
                    break
                    
                
                if stop_time is not None and HydrusData.TimeHasPassed( stop_time ):
                    
                    return
                    
                
                recover_tuple = self._GetRecoverTuple()
                
            
        
        if not partial:
            
            HydrusData.ShowText( 'All folders balanced!' )
            
        
    
    def TestLocations( self ):
        
        with self._lock:
            
            locations = set( self._prefixes_to_locations.values() )
            
            for location in locations:
                
                if not os.path.exists( location ):
                    
                    self._bad_error_occured = True
                    
                    HydrusData.ShowText( 'The external location ' + location + ' does not exist! Please check your external storage options and restart the client.' )
                    
                
            
        
    
class DataCache( object ):
    
    def __init__( self, controller, cache_size_key ):
        
        self._controller = controller
        self._cache_size_key = cache_size_key
        
        self._keys_to_data = {}
        self._keys_fifo = []
        
        self._total_estimated_memory_footprint = 0
        
        self._lock = threading.Lock()
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
    def _DeleteItem( self ):
        
        ( deletee_key, last_access_time ) = self._keys_fifo.pop( 0 )
        
        deletee_data = self._keys_to_data[ deletee_key ]
        
        del self._keys_to_data[ deletee_key ]
        
        self._RecalcMemoryUsage()
        
    
    def _RecalcMemoryUsage( self ):
        
        self._total_estimated_memory_footprint = sum( ( data.GetEstimatedMemoryFootprint() for data in self._keys_to_data.values() ) )
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._keys_to_data = {}
            self._keys_fifo = []
            
            self._total_estimated_memory_footprint = 0
            
        
    
    def AddData( self, key, data ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                options = self._controller.GetOptions()
                
                while self._total_estimated_memory_footprint > options[ self._cache_size_key ]:
                    
                    self._DeleteItem()
                    
                
                self._keys_to_data[ key ] = data
                
                self._keys_fifo.append( ( key, HydrusData.GetNow() ) )
                
                self._RecalcMemoryUsage()
                
            
        
    
    def GetData( self, key ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                raise Exception( 'Cache error! Looking for ' + HydrusData.ToUnicode( key ) + ', but it was missing.' )
                
            
            for ( i, ( fifo_key, last_access_time ) ) in enumerate( self._keys_fifo ):
                
                if fifo_key == key:
                    
                    del self._keys_fifo[ i ]
                    
                    break
                    
                
            
            self._keys_fifo.append( ( key, HydrusData.GetNow() ) )
            
            return self._keys_to_data[ key ]
            
        
    
    def HasData( self, key ):
        
        with self._lock:
            
            return key in self._keys_to_data
            
        
    
    def MaintainCache( self ):
        
        with self._lock:
            
            while True:
                
                if len( self._keys_fifo ) == 0:
                    
                    break
                    
                else:
                    
                    ( key, last_access_time ) = self._keys_fifo[ 0 ]
                    
                    if HydrusData.TimeHasPassed( last_access_time + 1200 ):
                        
                        self._DeleteItem()
                        
                    else:
                        
                        break
                        
                    
                
            
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
class LocalBooruCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._RefreshShares()
        
        self._controller.sub( self, 'RefreshShares', 'refresh_local_booru_shares' )
        self._controller.sub( self, 'RefreshShares', 'restart_booru' )
        
    
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
            
            info = self._controller.Read( 'local_booru_share', share_key )
            
            hashes = info[ 'hashes' ]
            
            info[ 'hashes_set' ] = set( hashes )
            
            media_results = self._controller.Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, hashes )
            
            info[ 'media_results' ] = media_results
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            info[ 'hashes_to_media_results' ] = hashes_to_media_results
            
            self._keys_to_infos[ share_key ] = info
            
        
        return info
        
    
    def _RefreshShares( self ):
        
        self._local_booru_service = self._controller.GetServicesManager().GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        self._keys_to_infos = {}
        
        share_keys = self._controller.Read( 'local_booru_share_keys' )
        
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
            
        
    
class HydrusSessionManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        existing_sessions = self._controller.Read( 'hydrus_sessions' )
        
        self._service_keys_to_sessions = { service_key : ( session_key, expires ) for ( service_key, session_key, expires ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def DeleteSessionKey( self, service_key ):
        
        with self._lock:
            
            self._controller.Write( 'delete_hydrus_session_key', service_key )
            
            if service_key in self._service_keys_to_sessions:
                
                del self._service_keys_to_sessions[ service_key ]
                
            
        
    
    def GetSessionKey( self, service_key ):
        
        now = HydrusData.GetNow()
        
        with self._lock:
            
            if service_key in self._service_keys_to_sessions:
                
                ( session_key, expires ) = self._service_keys_to_sessions[ service_key ]
                
                if now + 600 > expires: del self._service_keys_to_sessions[ service_key ]
                else: return session_key
                
            
            # session key expired or not found
            
            service = self._controller.GetServicesManager().GetService( service_key )
            
            ( response_gumpf, cookies ) = service.Request( HC.GET, 'session_key', return_cookies = True )
            
            try: session_key = cookies[ 'session_key' ].decode( 'hex' )
            except: raise Exception( 'Service did not return a session key!' )
            
            expires = now + HydrusSessions.HYDRUS_SESSION_LIFETIME
            
            self._service_keys_to_sessions[ service_key ] = ( session_key, expires )
            
            self._controller.Write( 'hydrus_session', service_key, session_key, expires )
            
            return session_key
            
        
    
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
    
    def __init__( self, controller, cache_type ):
        
        self._controller = controller
        self._type = cache_type
        
        if self._type == 'fullscreen': self._data_cache = DataCache( self._controller, 'fullscreen_cache_size' )
        elif self._type == 'preview': self._data_cache = DataCache( self._controller, 'preview_cache_size' )
        
    
    def Clear( self ): self._data_cache.Clear()
    
    def GetImage( self, media, target_resolution = None ):
        
        hash = media.GetHash()
        
        if target_resolution is None:
            
            target_resolution = media.GetResolution()
            
        
        ( media_width, media_height ) = media.GetResolution()
        ( target_width, target_height ) = target_resolution
        
        if target_width > media_width or target_height > media_height:
            
            target_resolution = media.GetResolution()
            
        else:
            
            target_resolution = ( target_width, target_height ) # to convert from wx.size or list to tuple for the cache key
            
        
        key = ( hash, target_resolution )
        
        if self._data_cache.HasData( key ):
            
            return self._data_cache.GetData( key )
            
        else:
            
            image_container = ClientRendering.RasterContainerImage( media, target_resolution )
            
            self._data_cache.AddData( key, image_container )
            
            return image_container
            
        
    
    def HasImage( self, hash, target_resolution ):
        
        key = ( hash, target_resolution )
        
        return self._data_cache.HasData( key )
        
    
class ThumbnailCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        self._data_cache = DataCache( self._controller, 'thumbnail_cache_size' )
        
        self._lock = threading.Lock()
        
        self._waterfall_queue_quick = set()
        self._waterfall_queue_random = []
        
        self._waterfall_event = threading.Event()
        
        self._special_thumbs = {}
        
        self.Clear()
        
        threading.Thread( target = self.DAEMONWaterfall, name = 'Waterfall Daemon' ).start()
        
        self._controller.sub( self, 'Clear', 'thumbnail_resize' )
        
    
    def _GetResizedHydrusBitmapFromHardDrive( self, display_media, from_error = False ):
        
        hash = display_media.GetHash()
        
        path = None
        
        locations_manager = display_media.GetLocationsManager()
        
        if locations_manager.HasLocal():
            
            try:
                
                path = ClientFiles.GetThumbnailPath( hash, False )
                
            except HydrusExceptions.FileMissingException as e:
                
                HydrusData.ShowException( e )
                
            
        else:
            
            try:
                
                path = ClientFiles.GetThumbnailPath( hash, False )
                
            except:
                
                pass
                
            
        
        if path is None:
            
            hydrus_bitmap = self._special_thumbs[ 'hydrus' ]
            
        else:
            
            try:
                
                hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( path )
                
                options = HydrusGlobals.client_controller.GetOptions()
                
                ( media_x, media_y ) = display_media.GetResolution()
                ( actual_x, actual_y ) = hydrus_bitmap.GetSize()
                ( desired_x, desired_y ) = options[ 'thumbnail_dimensions' ]
                
                too_large = actual_x > desired_x or actual_y > desired_y
                
                small_original_image = actual_x == media_x and actual_y == media_y
                
                too_small = actual_x < desired_x and actual_y < desired_y
                
                if too_large or ( too_small and not small_original_image ):
                    
                    if not from_error: # If we get back here with an error, just return the badly sized bitmap--it'll probably get sorted next session
                        
                        del hydrus_bitmap
                        
                        try:
                            
                            os.remove( path ) # Sometimes, the image library doesn't release this fast enough, so this fails
                            
                        finally:
                            
                            hydrus_bitmap = self._GetResizedHydrusBitmapFromHardDrive( display_media, from_error = True )
                            
                        
                    
                
            except Exception as e:
                
                if from_error:
                    
                    raise
                    
                
                HydrusData.ShowException( e )
                
                try:
                    
                    try:
                        
                        os.remove( path )
                        
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                        raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was found, but it would not render for the above reason. Furthermore, the faulty thumbnail file could not be deleted. This event could indicate hard drive corruption, and it also suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.' )
                        
                    
                    try:
                        
                        hydrus_bitmap = self._GetResizedHydrusBitmapFromHardDrive( display_media, from_error = True )
                        
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                        raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was found, but it would not render for the above reason. It was deleted, but it could not be regenerated for the other above reason. This event could indicate hard drive corruption. Please check everything is ok.' )
                        
                    
                    HydrusData.ShowText( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was found, but it would not render for the above reason. It was deleted and regenerated. This event could indicate hard drive corruption. Please check everything is ok.' )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    hydrus_bitmap = self._special_thumbs[ 'hydrus' ]
                    
                
            
        
        return hydrus_bitmap
        
    
    def _RecalcWaterfallQueueRandom( self ):
    
        self._waterfall_queue_random = list( self._waterfall_queue_quick )
        
        random.shuffle( self._waterfall_queue_random )
        
    
    def CancelWaterfall( self, page_key, medias ):
        
        with self._lock:
            
            self._waterfall_queue_quick.difference_update( ( ( page_key, media ) for media in medias ) )
            
            self._RecalcWaterfallQueueRandom()
            
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._data_cache.Clear()
            
            self._special_thumbs = {}
            
            names = [ 'hydrus', 'flash', 'pdf', 'audio', 'video' ]
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            try:
                
                for name in names:
                    
                    path = os.path.join( HC.STATIC_DIR, name + '.png' )
                    
                    options = self._controller.GetOptions()
                    
                    thumbnail = HydrusFileHandling.GenerateThumbnail( path, options[ 'thumbnail_dimensions' ] )
                    
                    with open( temp_path, 'wb' ) as f: f.write( thumbnail )
                    
                    hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( temp_path )
                    
                    self._special_thumbs[ name ] = hydrus_bitmap
                    
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
        
    
    def GetThumbnail( self, media ):
        
        display_media = media.GetDisplayMedia()
        
        if display_media.GetLocationsManager().ShouldHaveThumbnail():
            
            mime = display_media.GetMime()
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                hash = display_media.GetHash()
                
                if not self._data_cache.HasData( hash ):
                    
                    hydrus_bitmap = self._GetResizedHydrusBitmapFromHardDrive( display_media )
                    
                    self._data_cache.AddData( hash, hydrus_bitmap )
                    
                
                return self._data_cache.GetData( hash )
                
            elif mime in HC.AUDIO: return self._special_thumbs[ 'audio' ]
            elif mime in HC.VIDEO: return self._special_thumbs[ 'video' ]
            elif mime == HC.APPLICATION_FLASH: return self._special_thumbs[ 'flash' ]
            elif mime == HC.APPLICATION_PDF: return self._special_thumbs[ 'pdf' ]
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
                
                self.GetThumbnail( media ) # to load it
                
                self._controller.pub( 'waterfall_thumbnail', page_key, media )
                
                if HydrusData.GetNowPrecise() - last_paused > 0.005:
                    
                    time.sleep( 0.00001 )
                    
                    last_paused = HydrusData.GetNowPrecise()
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
    
class ServicesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        self._keys_to_services = {}
        self._services_sorted = []
        
        self.RefreshServices()
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_data' )
        
    
    def FilterValidServiceKeys( self, service_keys ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for service_key in service_keys if service_key in self._keys_to_services ]
            
            return filtered_service_keys
            
        
    
    def GetService( self, service_key ):
        
        with self._lock:
            
            try:
                
                return self._keys_to_services[ service_key ]
                
            except KeyError:
                
                raise HydrusExceptions.DataMissing( 'That service was not found!' )
                
            
        
    
    def GetServices( self, types = HC.ALL_SERVICES, randomised = True ):
        
        with self._lock:
            
            services = [ service for service in self._services_sorted if service.GetServiceType() in types ]
            
            if randomised:
                
                random.shuffle( services )
                
            
            return services
            
        
    
    def RefreshServices( self ):
        
        with self._lock:
            
            services = self._controller.Read( 'services' )
            
            self._keys_to_services = { service.GetServiceKey() : service for service in services }
            
            compare_function = lambda a, b: cmp( a.GetName(), b.GetName() )
            
            self._services_sorted = list( services )
            self._services_sorted.sort( cmp = compare_function )
            
        
    
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
        
    
    def FilterStatusesToPairs( self, service_key, statuses_to_pairs ):
        
        for service_key_lookup in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key_lookup in self._service_keys_to_info:
                
                ( blacklist, censorships ) = self._service_keys_to_info[ service_key_lookup ]
                
                new_statuses_to_pairs = HydrusData.default_dict_set()
                
                for ( status, pairs ) in statuses_to_pairs.items():
                    
                    new_statuses_to_pairs[ status ] = { ( one, two ) for ( one, two ) in pairs if self._CensorshipMatches( one, blacklist, censorships ) and self._CensorshipMatches( two, blacklist, censorships ) }
                    
                
                statuses_to_pairs = new_statuses_to_pairs
                
            
        
        return statuses_to_pairs
        
    
    def FilterServiceKeysToStatusesToTags( self, service_keys_to_statuses_to_tags ):
        
        if CC.COMBINED_TAG_SERVICE_KEY in self._service_keys_to_info:
            
            ( blacklist, censorships ) = self._service_keys_to_info[ CC.COMBINED_TAG_SERVICE_KEY ]
            
            service_keys = service_keys_to_statuses_to_tags.keys()
            
            for service_key in service_keys:
                
                statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
                
                statuses = statuses_to_tags.keys()
                
                for status in statuses:
                    
                    tags = statuses_to_tags[ status ]
                    
                    statuses_to_tags[ status ] = { tag for tag in tags if self._CensorshipMatches( tag, blacklist, censorships ) }
                    
                
            
        
        for ( service_key, ( blacklist, censorships ) ) in self._service_keys_to_info.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            if service_key in service_keys_to_statuses_to_tags:
                
                statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
                
                statuses = statuses_to_tags.keys()
                
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
        
        self._service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
        
        self._RefreshParents()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'RefreshParents', 'notify_new_parents' )
        
    
    def _RefreshParents( self ):
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_parents' )
        
        # first collapse siblings
        
        sibling_manager = self._controller.GetManager( 'tag_siblings' )
        
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
        
        new_options = self._controller.GetNewOptions()
        
        if new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
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
            
        
    
    def ExpandTags( self, service_key, tags ):
        
        new_options = self._controller.GetNewOptions()
        
        if new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            tags_results = set( tags )
            
            for tag in tags:
                
                tags_results.update( self._service_keys_to_children_to_parents[ service_key ][ tag ] )
                
            
            return tags_results
            
        
    
    def GetParents( self, service_key, tag ):
        
        new_options = self._controller.GetNewOptions()
        
        if new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            return self._service_keys_to_children_to_parents[ service_key ][ tag ]
            
        
    
    def RefreshParents( self ):
        
        with self._lock:
            
            self._RefreshParents()
            
        
    
class TagSiblingsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._RefreshSiblings()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'RefreshSiblings', 'notify_new_siblings' )
        
    
    def _CollapseTags( self, tags ):
        
        return { self._siblings[ tag ] if tag in self._siblings else tag for tag in tags }
        
    
    def _RefreshSiblings( self ):
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_siblings' )
        
        processed_siblings = CombineTagSiblingPairs( service_keys_to_statuses_to_pairs )
        
        ( self._siblings, self._reverse_lookup ) = CollapseTagSiblingChains( processed_siblings )
        
        self._controller.pub( 'new_siblings_gui' )
        
    
    def GetAutocompleteSiblings( self, search_text, exact_match = False ):
        
        with self._lock:
            
            if exact_match:
                
                key_based_matching_values = set()
                
                if search_text in self._siblings:
                    
                    key_based_matching_values = { self._siblings[ search_text ] }
                    
                else:
                    
                    key_based_matching_values = set()
                    
                
                value_based_matching_values = { value for value in self._siblings.values() if value == search_text }
                
            else:
                
                matching_keys = ClientSearch.FilterTagsBySearchEntry( search_text, self._siblings.keys(), search_siblings = False )
                
                key_based_matching_values = { self._siblings[ key ] for key in matching_keys }
                
                value_based_matching_values = ClientSearch.FilterTagsBySearchEntry( search_text, self._siblings.values(), search_siblings = False )
                
            
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
                        
                        new_predicate = ClientSearch.Predicate( old_pred_type, new_tag, inclusive = old_inclusive )
                        
                        tags_to_predicates[ new_tag ] = new_predicate
                        
                        tags_to_include_in_results.add( new_tag )
                        
                    
                    new_predicate = tags_to_predicates[ new_tag ]
                    
                    current_count = old_predicate.GetCount( HC.CURRENT )
                    pending_count = old_predicate.GetCount( HC.PENDING )
                    
                    new_predicate.AddToCount( HC.CURRENT, current_count )
                    new_predicate.AddToCount( HC.PENDING, pending_count )
                    
                else:
                    
                    tags_to_include_in_results.add( tag )
                    
                
            
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
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            filtered_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_UNDELETE, HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ): continue
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    if action in ( HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ): continue
                    
                else: continue
                
                filtered_content_update = HydrusData.ContentUpdate( data_type, action, row )
                
                filtered_content_updates.append( filtered_content_update )
                
            
            if len( filtered_content_updates ) > 0:
                
                filtered_service_keys_to_content_updates[ service_key ] = filtered_content_updates
                
            
        
        return filtered_service_keys_to_content_updates
        
    
    def _InvertServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        inverted_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            inverted_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                inverted_row = row
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action == HC.CONTENT_UPDATE_ARCHIVE: inverted_action = HC.CONTENT_UPDATE_INBOX
                    elif action == HC.CONTENT_UPDATE_INBOX: inverted_action = HC.CONTENT_UPDATE_ARCHIVE
                    elif action == HC.CONTENT_UPDATE_PEND: inverted_action = HC.CONTENT_UPDATE_RESCIND_PEND
                    elif action == HC.CONTENT_UPDATE_RESCIND_PEND: inverted_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_PETITION:
                        
                        inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                        
                        ( hashes, reason ) = row
                        
                        inverted_row = hashes
                        
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    if action == HC.CONTENT_UPDATE_ADD: inverted_action = HC.CONTENT_UPDATE_DELETE
                    elif action == HC.CONTENT_UPDATE_DELETE: inverted_action = HC.CONTENT_UPDATE_ADD
                    elif action == HC.CONTENT_UPDATE_PEND: inverted_action = HC.CONTENT_UPDATE_RESCIND_PEND
                    elif action == HC.CONTENT_UPDATE_RESCIND_PEND: inverted_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_PETITION:
                        
                        inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                        
                        ( tag, hashes, reason ) = row
                        
                        inverted_row = ( tag, hashes )
                        
                    
                
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
            
        
    
class WebSessionManagerClient( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        existing_sessions = self._controller.Read( 'web_sessions' )
        
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
                
                ( response_gumpf, cookies ) = self._controller.DoHTTP( HC.GET, 'http://www.deviantart.com/', return_cookies = True )
                
                expires = now + 30 * 86400
                
            if name == 'hentai foundry':
                
                ( response_gumpf, cookies ) = self._controller.DoHTTP( HC.GET, 'http://www.hentai-foundry.com/?enterAgree=1', return_cookies = True )
                
                raw_csrf = cookies[ 'YII_CSRF_TOKEN' ] # 19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B
                
                processed_csrf = urllib.unquote( raw_csrf ) # 19b05b536885ec60b8b37650a32f8deb11c08cd1s:40:"2917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32";
                
                csrf_token = processed_csrf.split( '"' )[1] # the 2917... bit
                
                hentai_foundry_form_info = ClientDefaults.GetDefaultHentaiFoundryInfo()
                
                hentai_foundry_form_info[ 'YII_CSRF_TOKEN' ] = csrf_token
                
                body = urllib.urlencode( hentai_foundry_form_info )
                
                request_headers = {}
                ClientNetworking.AddCookiesToHeaders( cookies, request_headers )
                request_headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
                
                self._controller.DoHTTP( HC.POST, 'http://www.hentai-foundry.com/site/filters', request_headers = request_headers, body = body )
                
                expires = now + 60 * 60
                
            elif name == 'pixiv':
                
                result = self._controller.Read( 'serialisable_simple', 'pixiv_account' )
                
                if result is None:
                    
                    raise HydrusExceptions.DataMissing( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                    
                
                ( id, password ) = result
                
                form_fields = {}
                
                form_fields[ 'mode' ] = 'login'
                form_fields[ 'pixiv_id' ] = id
                form_fields[ 'pass' ] = password
                form_fields[ 'skip' ] = '1'
                
                body = urllib.urlencode( form_fields )
                
                headers = {}
                headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
                
                ( response_gumpf, cookies ) = self._controller.DoHTTP( HC.POST, 'http://www.pixiv.net/login.php', request_headers = headers, body = body, return_cookies = True )
                
                # _ only given to logged in php sessions
                if 'PHPSESSID' not in cookies or '_' not in cookies[ 'PHPSESSID' ]: raise Exception( 'Pixiv login credentials not accepted!' )
                
                expires = now + 30 * 86400
                
            
            self._names_to_sessions[ name ] = ( cookies, expires )
            
            self._controller.Write( 'web_session', name, cookies, expires )
            
            return cookies
            
        
    