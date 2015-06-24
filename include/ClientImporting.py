import ClientConstants as CC
import HydrusConstants as HC
import HydrusData
import HydrusSerialisable
import threading
import traceback

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
        
        self._search_seeds = SeedQueue()
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
        
    
    def _ProcessImportSeed( self, seed, seed_info ):
        
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
                
                ( seed, seed_info ) = result
                
                self._ProcessImportSeed( import_seed, seed_info )
                
            
        
    
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
            
        
    
class ImportControllerHDD( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        # this stuff is all moved to the search seed
        self._paths_info = None
        self._paths_to_tags = None
        self._delete_file_after_import = None
        self._import_file_options = None
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = HydrusSerialisable.GetSerialisableTuple( self._url_cache )
        
        serialisable_options = { name : HydrusSerialisable.GetSerialisableTuple( options ) for ( name, options ) in self._options.items() }
        
        return ( self._site_type, self._query_type, self._query, self._get_tags_if_redundant, serialisable_url_cache, serialisable_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._site_type, self._query_type, self._query, self._get_tags_if_redundant, serialisable_url_cache_tuple, serialisable_options_tuple ) = serialisable_info
        
        self._url_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache_tuple )
        
        self._options = { name : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_suboptions_tuple ) for ( name, serialisable_suboptions_tuple ) in serialisable_options_tuple.items() }
        
    
    def GetImportStatus( self ):
        
        with self._lock:
            
            return self._import_status
            
        
    
    def GetQueueStatus( self ):
        
        with self._lock:
            
            gauge_value = self._current_position
            gauge_range = len( self._paths_info )
            
            # return progress string
            # also return string for num_successful and so on
            
            pass
            
        
    
    def GetTuple( self ):
        
        return ( self._paths_info, self._paths_to_tags, self._delete_file_after_import, self._import_file_options )
        
    
    def MainLoop( self ):
        
        # use the lock sparingly, remember
        # obey pause and hc.shutdown
        # maybe also an internal shutdown, on managementpanel cleanupbeforedestroy
        # update file_status_counts
        # increment current_position
        
        pass
        
    
    def Pause( self ):
        
        with self._lock:
            
            self._paused = True
            
        
    
    def Resume( self ):
        
        with self._lock:
            
            self._paused = False
            
        
    
    def SetTuple( self, paths_info, paths_to_tags, delete_file_after_import, import_file_options ):
        
        self._paths_info = paths_info
        self._paths_to_tags = paths_to_tags
        self._delete_file_after_import = delete_file_after_import
        self._import_file_options = import_file_options
        
    
    def Start( self ):
        
        # init a daemon to work through the list
        
        pass
        
    
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
        self._url_cache = URLCache()
        self._options = options
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_QUERY ] = GalleryQuery

class SubscriptionController( HydrusSerialisable.SerialisableBaseNamed ):
    
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

class SeedQueue( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED_QUEUE
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._seeds_ordered = []
        self._seeds_to_info = {}
        
        self._lock = threading.Lock()
        
    
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
                
            
        
    
    def AddSeed( self, seed, additional_info = None ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                self._seeds_ordered.remove( seed )
                
            
            self._seeds_ordered.append( seed )
            
            seed_info = {}
            
            seed_info[ 'status' ] = CC.STATUS_UNKNOWN
            seed_info[ 'timestamp' ] = HydrusData.GetNow()
            seed_info[ 'note' ] = ''
            
            if additional_info is not None:
                
                seed_info.update( additional_info )
                
            
            self._seeds_to_info[ seed ] = seed_info
            
            
        
    
    def AdvanceSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_ordered.index( seed )
                
                if index > 0:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index - 1, seed )
                    
                
            
        
    
    def DelaySeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_ordered.index( seed )
                
                if index < len( self._seeds_ordered ) - 1:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index + 1, seed )
                    
                
            
        
    
    def GetNextUnknownSeed( self ):
        
        with self._lock:
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                if seed_info[ 'status' ] == CC.STATUS_UNKNOWN:
                    
                    return ( seed, seed_info )
                    
                
            
        
        return None
        
    
    def GetSeeds( self ):
        
        with self._lock:
            
            return list( self._seeds_ordered )
            
        
    
    def GetSeedsDisplayInfo( self ):
        
        with self._lock:
            
            all_info = []
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                timestamp = seed_info[ 'timestamp' ]
                status = seed_info[ 'status' ]
                note = seed_info[ 'note' ]
                
                all_info.append( ( seed, status, timestamp, note ) )
                
            
            return all_info
            
        
    
    def RemoveSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                del self._seeds_to_info[ seed ]
                
                self._seeds_ordered.remove( seed )
                
            
        
    
    def SetSeedStatus( self, seed, status, note = '' ):
        
        with self._lock:
            
            seed_info = self._seeds_to_info[ seed ]
            
            seed_info[ 'status' ] = status
            seed_info[ 'timestamp' ] = HydrusData.GetNow()
            seed_info[ 'note' ] = note
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED_QUEUE ] = SeedQueue
