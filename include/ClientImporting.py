import ClientConstants as CC
import collections
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusSerialisable
import HydrusThreading
import os
import threading
import time
import traceback
import wx

class ImportController( HydrusSerialisable.SerialisableBase ):
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        # queues of stuff, where every kind of queue can be serialised
        # hence don't have __init__ for subclasses! nothing beyond temp vars
        # everything must fit inside what I declare here
        # subclasses should mostly fill in _ProcessQueue kind of stuff.
        # don't forget THREAD stuff, which should probably be explicitly started by the managementpanel?
        # also, what about page_key? how are we reporting new imports and so on? maybe that can be temp var in the daemonspawner
        
        # hence maybe make a 'queue' object representing a list of urls or whatever -- maybe a urlcache can do that job.
        
        # a number of queues
        # a thing that extends a queue using a search
        # a list of searches that will be built into queues
        
        # maybe some class variables saying what parts to engage, like HDD doesn't accept new queues and so on
        
        self._file_status_counts = {}
        
        # if I decide to link search_seeds to the import_seed_queues, then why not bundle the import_seed_queue into the search_seed_info?
        # yes, this is a good idea.
        
        self._import_seed_queues = []
        self._importer_status = ( '', 0, 1 )
        
        self._search_seeds = SeedCache()
        self._searcher_status = ( '', 0, 1 )
        
        self._options = {}
        
        self._lock = threading.Lock()
        self._import_status = ''
        
    
    def _GetSerialisableInfo( self ):
        
        # collapse file status counts into a list because of stupid int dict json thing
        
        serialisable_url_cache = HydrusSerialisable.GetSerialisableTuple( self._url_cache )
        
        serialisable_options = { name : HydrusSerialisable.GetSerialisableTuple( options ) for ( name, options ) in self._options.items() }
        
        return ( self._site_type, self._query_type, self._query, self._get_tags_if_redundant, serialisable_url_cache, serialisable_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._site_type, self._query_type, self._query, self._get_tags_if_redundant, serialisable_url_cache_tuple, serialisable_options_tuple ) = serialisable_info
        
        self._url_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache_tuple )
        
        self._options = { name : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_suboptions_tuple ) for ( name, serialisable_suboptions_tuple ) in serialisable_options_tuple.items() }
        
    
    def _ProcessImportSeed( self, seed ):
        
        raise NotImplementedError()
        
    
    def _ProcessSearchSeed( self, seed, seed_info ):
        
        raise NotImplementedError()
        
    
    def _DAEMONProcessImportSeeds( self ):
        
        while True:
            
            # if importer paused
            
            with self._lock:
                
                result = None
                
                # determine paused/cancelled status via searchseedqueue or whatever
                
                for import_seed_queue in self._import_seed_queues:
                    
                    result = import_seed_queue.GetNextUnknownSeed()
                    
                    if result is not None:
                        
                        # remember current import_seed_queue so we can set seed status later
                        
                        break
                        
                    
                
            
            if result is not None:
                
                seed = result
                
                self._ProcessImportSeed( seed )
                
            
        
    
    def _DAEMONProcessSearchSeeds( self ):
        
        while True:
            
            # if searcher paused
            
            with self._lock:
                
                result = import_seed_queue.GetNextUnknownSeed()
                
            
            if result is not None:
                
                ( seed, seed_info ) = result
                
                self._ProcessSearchSeed( seed, seed_info )
                
            
        
    
    def GetOptions( self, name ):
        
        with self._lock:
            
            return self._options[ name ]
            
        
    
    def GetStatuses( self ):
        
        with self._lock:
            
            return ( dict( self._file_status_counts ), self._import_status, self._current_queue_status, self._searcher_status )
            
        
    
    def PauseSearcher( self ):
        
        with self._lock:
            
            self._searcher_paused = True
            
        
    
    def ResumeCurrentQueue( self ):
        
        with self._lock:
            
            self._current_queue_paused = False
            
        
    
    def ResumeSearcher( self ):
        
        with self._lock:
            
            self._searcher_paused = False
            
        
    
    def SetOptions( self, name, options ):
        
        with self._lock:
            
            self._options[ name ] = options
            
        
    
class HDDImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, paths = None, import_file_options = None, paths_to_tags = None, delete_after_success = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if paths is None:
            
            self._paths_cache = None
            
        else:
            
            self._paths_cache = SeedCache()
            
            for path in paths:
                
                self._paths_cache.AddSeed( path )
                
            
        
        self._import_file_options = import_file_options
        self._paths_to_tags = paths_to_tags
        self._delete_after_success = delete_after_success
        self._paused = False
        
        self._overall_status = ( 'initialising', ( 0, 1 ) )
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = HydrusSerialisable.GetSerialisableTuple( self._paths_cache )
        serialisable_options = HydrusSerialisable.GetSerialisableTuple( self._import_file_options )
        serialisable_paths_to_tags = { path : { service_key.encode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in self._paths_to_tags.items() }
        
        return ( serialisable_url_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_url_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused ) = serialisable_info
        
        self._paths_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_options )
        self._paths_to_tags = { path : { service_key.decode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in serialisable_paths_to_tags.items() }
        
    
    def _RegenerateStatus( self ):
        
        self._overall_status = self._paths_cache.GetStatus()
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateStatus()
            
        
        HydrusGlobals.pubsub.pub( 'update_status', page_key )
        
        while True:
            
            if HydrusGlobals.shutdown:
                
                return
                
            
            while self._paused:
                
                if HydrusGlobals.shutdown:
                    
                    return
                    
                
                time.sleep( 0.1 )
                
            
            try:
                
                with self._lock:
                    
                    path = self._paths_cache.GetNextUnknownSeed()
                    
                    if path is not None:
                        
                        if path in self._paths_to_tags:
                            
                            service_keys_to_tags = self._paths_to_tags[ path ]
                            
                        else:
                            
                            service_keys_to_tags = {}
                            
                        
                    
                
                if path is not None:
                    
                    try:
                        
                        ( status, media_result ) = wx.GetApp().WriteSynchronous( 'import_file', path, import_file_options = self._import_file_options, service_keys_to_tags = service_keys_to_tags, generate_media_result = True )
                        
                        with self._lock:
                            
                            self._paths_cache.UpdateSeedStatus( path, status )
                            
                            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                                
                                HydrusGlobals.pubsub.pub( 'add_media_results', page_key, ( media_result, ) )
                                
                                if self._delete_after_success:
                                    
                                    try: os.remove( path )
                                    except: pass
                                    
                                
                            
                        
                    except Exception as e:
                        
                        status = CC.STATUS_FAILED
                        
                        note = HydrusData.ToString( e )
                        
                        with self._lock:
                            
                            self._paths_cache.UpdateSeedStatus( path, status, note = note )
                            
                        
                    
                    with self._lock:
                        
                        self._RegenerateStatus()
                        
                    
                    HydrusGlobals.pubsub.pub( 'update_status', page_key )
                    
                else:
                    
                    time.sleep( 1 )
                    
                
                wx.GetApp().WaitUntilWXThreadIdle()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                return
                
            
        
    
    def GetSeedCache( self ):
        
        return self._paths_cache
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._overall_status, self._paused )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
        
    
    def Start( self, page_key ):
        
        threading.Thread( target = self._THREADWork, args = ( page_key, ) ).start()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT ] = HDDImport

class GalleryQuery( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_QUERY
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._site_type = None
        self._query_type = None
        self._query = None
        self._get_tags_if_redundant = False
        self._file_limit = 500
        self._paused = False
        self._page_index = 0
        self._url_cache = None
        self._options = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = HydrusSerialisable.GetSerialisableTuple( self._url_cache )
        
        serialisable_options = { name : HydrusSerialisable.GetSerialisableTuple( options ) for ( name, options ) in self._options.items() }
        
        return ( self._site_type, self._query_type, self._query, self._get_tags_if_redundant, self._file_limit, serialisable_url_cache, serialisable_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._site_type, self._query_type, self._query, self._get_tags_if_redundant, serialisable_url_cache_tuple, serialisable_options_tuple ) = serialisable_info
        
        self._url_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache_tuple )
        
        self._options = { name : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_suboptions_tuple ) for ( name, serialisable_suboptions_tuple ) in serialisable_options_tuple.items() }
        
    
    def GetQuery( self ):
        
        return self._query
        
    
    def SetTuple( self, site_type, query_type, query, get_tags_if_redundant, file_limit, options ):
        
        self._site_type = site_type
        self._query_type = query_type
        self._query = query
        self._get_tags_if_redundant = get_tags_if_redundant
        self._file_limit = file_limit
        self._url_cache = SeedCache()
        self._options = options
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_QUERY ] = GalleryQuery

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._site_type = None
        self._query_type = None
        self._query = None
        self._get_tags_if_redundant = False
        self._file_limit = 500
        self._periodic = None
        self._page_index = 0
        self._url_cache = None
        self._options = {}
        
    
    def _GetSerialisableInfo( self ):
        
        return ( HydrusSerialisable.GetSerialisableTuple( self._gallery_query ), HydrusSerialisable.GetSerialisableTuple( self._periodic ) )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialised_gallery_query_tuple, serialised_periodic_tuple ) = serialisable_info
        
        self._gallery_query = HydrusSerialisable.CreateFromSerialisableTuple( serialised_gallery_query_tuple )
        
        self._periodic = HydrusSerialisable.CreateFromSerialisableTuple( serialised_periodic_tuple )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ] = Subscription

class SeedCache( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._seeds_ordered = []
        self._seeds_to_info = {}
        
        self._lock = threading.Lock()
        
    
    def _GetSeedTuple( self, seed ):
        
        seed_info = self._seeds_to_info[ seed ]
        
        status = seed_info[ 'status' ]
        added_timestamp = seed_info[ 'added_timestamp' ]
        last_modified_timestamp = seed_info[ 'last_modified_timestamp' ]
        note = seed_info[ 'note' ]
        
        return ( seed, status, added_timestamp, last_modified_timestamp, note )
        
    
    def _GetSerialisableInfo( self ):
        
        with self._lock:
            
            serialisable_info = []
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                serialisable_info.append( ( seed, seed_info ) )
                
            
            return serialisable_info
            
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            for ( seed, seed_info ) in serialisable_info:
                
                self._seeds_ordered.append( seed )
                
                self._seeds_to_info[ seed ] = seed_info
                
            
        
    
    def AddSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                self._seeds_ordered.remove( seed )
                
            
            self._seeds_ordered.append( seed )
            
            now = HydrusData.GetNow()
            
            seed_info = {}
            
            seed_info[ 'status' ] = CC.STATUS_UNKNOWN
            seed_info[ 'added_timestamp' ] = now
            seed_info[ 'last_modified_timestamp' ] = now
            seed_info[ 'note' ] = ''
            
            self._seeds_to_info[ seed ] = seed_info
            
        
        HydrusGlobals.pubsub.pub( 'seed_cache_seed_updated', seed )
        
    
    def AdvanceSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_ordered.index( seed )
                
                if index > 0:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index - 1, seed )
                    
                
            
        
        HydrusGlobals.pubsub.pub( 'seed_cache_seed_updated', seed )
        
    
    def DelaySeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_ordered.index( seed )
                
                if index < len( self._seeds_ordered ) - 1:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index + 1, seed )
                    
                
            
        
        HydrusGlobals.pubsub.pub( 'seed_cache_seed_updated', seed )
        
    
    def GetNextUnknownSeed( self ):
        
        with self._lock:
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                if seed_info[ 'status' ] == CC.STATUS_UNKNOWN:
                    
                    return seed
                    
                
            
        
        return None
        
    
    def GetSeeds( self ):
        
        with self._lock:
            
            return list( self._seeds_ordered )
            
        
    
    def GetSeedsWithInfo( self ):
        
        with self._lock:
            
            all_info = []
            
            for seed in self._seeds_ordered:
                
                seed_tuple = self._GetSeedTuple( seed )
                
                all_info.append( seed_tuple )
                
            
            return all_info
            
        
    
    def GetSeedInfo( self, seed ):
        
        with self._lock:
            
            return self._GetSeedTuple( seed )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            statuses_to_counts = collections.Counter()
            
            for seed_info in self._seeds_to_info.values():
                
                statuses_to_counts[ seed_info[ 'status' ] ] += 1
                
            
            num_successful = statuses_to_counts[ CC.STATUS_SUCCESSFUL ]
            num_failed = statuses_to_counts[ CC.STATUS_FAILED ]
            num_deleted = statuses_to_counts[ CC.STATUS_DELETED ]
            num_redundant = statuses_to_counts[ CC.STATUS_REDUNDANT ]
            num_unknown = statuses_to_counts[ CC.STATUS_UNKNOWN ]
            
            status_strings = []
            
            if num_successful > 0: status_strings.append( HydrusData.ToString( num_successful ) + ' successful' )
            if num_failed > 0: status_strings.append( HydrusData.ToString( num_failed ) + ' failed' )
            if num_deleted > 0: status_strings.append( HydrusData.ToString( num_deleted ) + ' already deleted' )
            if num_redundant > 0: status_strings.append( HydrusData.ToString( num_redundant ) + ' already in db' )
            
            status = ', '.join( status_strings )
            
            total_processed = len( self._seeds_ordered ) - num_unknown
            total = len( self._seeds_ordered )
            
            return ( status, ( total_processed, total ) )
            
        
    
    def HasSeed( self, seed ):
        
        with self._lock:
            
            return seed in self._seeds_to_info
            
        
    
    def RemoveSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                del self._seeds_to_info[ seed ]
                
                self._seeds_ordered.remove( seed )
                
            
        
        HydrusGlobals.pubsub.pub( 'seed_cache_seed_updated', seed )
        
    
    def UpdateSeedStatus( self, seed, status, note = '' ):
        
        with self._lock:
            
            seed_info = self._seeds_to_info[ seed ]
            
            seed_info[ 'status' ] = status
            seed_info[ 'last_modified_timestamp' ] = HydrusData.GetNow()
            seed_info[ 'note' ] = note
            
        
        HydrusGlobals.pubsub.pub( 'seed_cache_seed_updated', seed )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE ] = SeedCache
