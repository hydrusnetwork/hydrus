import collections
import collections.abc
import random
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.search import ClientSearchTagContext

class TagAutocompleteOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_AUTOCOMPLETE_OPTIONS
    SERIALISABLE_NAME = 'Tag Autocomplete Options'
    SERIALISABLE_VERSION = 5
    
    def __init__( self, service_key: typing.Optional[ bytes ] = None ):
        
        if service_key is None:
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        super().__init__()
        
        self._service_key = service_key
        
        self._write_autocomplete_tag_domain = self._service_key
        
        self._override_write_autocomplete_location_context = True
        
        if service_key == CC.DEFAULT_LOCAL_TAG_SERVICE_KEY:
            
            self._write_autocomplete_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
            
        else:
            
            self._write_autocomplete_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY )
            
        
        self._search_namespaces_into_full_tags = False
        self._unnamespaced_search_gives_any_namespace_wildcards = False
        self._namespace_bare_fetch_all_allowed = False
        self._namespace_fetch_all_allowed = False
        self._fetch_all_allowed = False
        self._fetch_results_automatically = True
        self._exact_match_character_threshold = 2
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_service_key = self._service_key.hex()
        
        serialisable_write_autocomplete_tag_domain = self._write_autocomplete_tag_domain.hex()
        serialisable_write_autocomplete_location_context = self._write_autocomplete_location_context.GetSerialisableTuple()
        
        serialisable_info = [
            serialisable_service_key,
            serialisable_write_autocomplete_tag_domain,
            self._override_write_autocomplete_location_context,
            serialisable_write_autocomplete_location_context,
            self._search_namespaces_into_full_tags,
            self._unnamespaced_search_gives_any_namespace_wildcards,
            self._namespace_bare_fetch_all_allowed,
            self._namespace_fetch_all_allowed,
            self._fetch_all_allowed,
            self._fetch_results_automatically,
            self._exact_match_character_threshold
        ]
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        [
            serialisable_service_key,
            serialisable_write_autocomplete_tag_domain,
            self._override_write_autocomplete_location_context,
            serialisable_write_autocomplete_location_context,
            self._search_namespaces_into_full_tags,
            self._unnamespaced_search_gives_any_namespace_wildcards,
            self._namespace_bare_fetch_all_allowed,
            self._namespace_fetch_all_allowed,
            self._fetch_all_allowed,
            self._fetch_results_automatically,
            self._exact_match_character_threshold
        ] = serialisable_info
        
        self._service_key = bytes.fromhex( serialisable_service_key )
        self._write_autocomplete_tag_domain = bytes.fromhex( serialisable_write_autocomplete_tag_domain )
        self._write_autocomplete_location_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_write_autocomplete_location_context )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_location_context,
                serialisable_write_autocomplete_file_domain,
                search_namespaces_into_full_tags,
                namespace_fetch_all_allowed,
                fetch_all_allowed
            ] = old_serialisable_info
            
            namespace_bare_fetch_all_allowed = False
            
            new_serialisable_info = [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_location_context,
                serialisable_write_autocomplete_file_domain,
                search_namespaces_into_full_tags,
                namespace_bare_fetch_all_allowed,
                namespace_fetch_all_allowed,
                fetch_all_allowed
            ]
            
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_location_context,
                serialisable_write_autocomplete_file_domain,
                search_namespaces_into_full_tags,
                namespace_bare_fetch_all_allowed,
                namespace_fetch_all_allowed,
                fetch_all_allowed
            ] = old_serialisable_info
            
            fetch_results_automatically = True
            exact_match_character_threshold = 2
            
            new_serialisable_info = [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_location_context,
                serialisable_write_autocomplete_file_domain,
                search_namespaces_into_full_tags,
                namespace_bare_fetch_all_allowed,
                namespace_fetch_all_allowed,
                fetch_all_allowed,
                fetch_results_automatically,
                exact_match_character_threshold
            ]
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_location_context,
                serialisable_write_autocomplete_file_domain,
                search_namespaces_into_full_tags,
                namespace_bare_fetch_all_allowed,
                namespace_fetch_all_allowed,
                fetch_all_allowed,
                fetch_results_automatically,
                exact_match_character_threshold
            ] = old_serialisable_info
            
            file_service_key = bytes.fromhex( serialisable_write_autocomplete_file_domain )
            location_context = ClientLocation.LocationContext.STATICCreateSimple( file_service_key )
            
            serialisable_write_autocomplete_location_context = location_context.GetSerialisableTuple()
            
            new_serialisable_info = [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_location_context,
                serialisable_write_autocomplete_location_context,
                search_namespaces_into_full_tags,
                namespace_bare_fetch_all_allowed,
                namespace_fetch_all_allowed,
                fetch_all_allowed,
                fetch_results_automatically,
                exact_match_character_threshold
            ]
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_location_context,
                serialisable_write_autocomplete_location_context,
                search_namespaces_into_full_tags,
                namespace_bare_fetch_all_allowed,
                namespace_fetch_all_allowed,
                fetch_all_allowed,
                fetch_results_automatically,
                exact_match_character_threshold
            ] = old_serialisable_info
            
            unnamespaced_search_gives_any_namespace_wildcards = False
            
            new_serialisable_info = [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_location_context,
                serialisable_write_autocomplete_location_context,
                search_namespaces_into_full_tags,
                unnamespaced_search_gives_any_namespace_wildcards,
                namespace_bare_fetch_all_allowed,
                namespace_fetch_all_allowed,
                fetch_all_allowed,
                fetch_results_automatically,
                exact_match_character_threshold
            ]
            
            return ( 5, new_serialisable_info )
            
        
    
    def FetchAllAllowed( self ):
        
        return self._fetch_all_allowed
        
    
    def FetchResultsAutomatically( self ):
        
        return self._fetch_results_automatically
        
    
    def GetExactMatchCharacterThreshold( self ):
        
        return self._exact_match_character_threshold
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
    def GetWriteAutocompleteLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._write_autocomplete_location_context
        
    
    def GetWriteAutocompleteSearchDomain( self, location_context: ClientLocation.LocationContext, display_tag_service_key: bytes ):
        
        tag_service_key = self._service_key
        
        if self._service_key != CC.COMBINED_TAG_SERVICE_KEY:
            
            if self._override_write_autocomplete_location_context:
                
                location_context = self._write_autocomplete_location_context.Duplicate()
                
            
            tag_service_key = self._write_autocomplete_tag_domain
            
        
        if location_context.IsAllKnownFiles() and tag_service_key == CC.COMBINED_TAG_SERVICE_KEY: # ruh roh
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
        
        tag_context = ClientSearchTagContext.TagContext( service_key = tag_service_key, display_service_key = display_tag_service_key )
        
        return ( location_context, tag_context )
        
    
    def GetWriteAutocompleteTagDomain( self ):
        
        return self._write_autocomplete_tag_domain
        
    
    def NamespaceBareFetchAllAllowed( self ):
        
        return self._namespace_bare_fetch_all_allowed
        
    
    def NamespaceFetchAllAllowed( self ):
        
        return self._namespace_fetch_all_allowed
        
    
    def OverridesWriteAutocompleteLocationContext( self ):
        
        return self._override_write_autocomplete_location_context
        
    
    def SearchNamespacesIntoFullTags( self ):
        
        return self._search_namespaces_into_full_tags
        
    
    def UnnamespacedSearchGivesAnyNamespaceWildcards( self ) -> bool:
        
        return self._unnamespaced_search_gives_any_namespace_wildcards
        
    
    def SetExactMatchCharacterThreshold( self, exact_match_character_threshold: typing.Optional[ int ] ):
        
        self._exact_match_character_threshold = exact_match_character_threshold
        
    
    def SetFetchResultsAutomatically( self, fetch_results_automatically: bool ):
        
        self._fetch_results_automatically = fetch_results_automatically
        
    
    def SetUnnamespacedSearchGivesAnyNamespaceWildcards( self, unnamespaced_search_gives_any_namespace_wildcards: bool ):
        
        self._unnamespaced_search_gives_any_namespace_wildcards = unnamespaced_search_gives_any_namespace_wildcards
        
    
    def SetTuple( self,
        write_autocomplete_tag_domain: bytes,
        override_write_autocomplete_location_context: bool,
        write_autocomplete_location_context: ClientLocation.LocationContext,
        search_namespaces_into_full_tags: bool,
        namespace_bare_fetch_all_allowed: bool,
        namespace_fetch_all_allowed: bool,
        fetch_all_allowed: bool
    ):
        
        self._write_autocomplete_tag_domain = write_autocomplete_tag_domain
        self._override_write_autocomplete_location_context = override_write_autocomplete_location_context
        self._write_autocomplete_location_context = write_autocomplete_location_context
        self._search_namespaces_into_full_tags = search_namespaces_into_full_tags
        self._namespace_bare_fetch_all_allowed = namespace_bare_fetch_all_allowed
        self._namespace_fetch_all_allowed = namespace_fetch_all_allowed
        self._fetch_all_allowed = fetch_all_allowed
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_AUTOCOMPLETE_OPTIONS ] = TagAutocompleteOptions

class TagDisplayMaintenanceManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller ):
        
        super().__init__( controller, 60 )
        
        self._service_keys_to_needs_work = {}
        
        self._go_faster = set()
        
        self._last_loop_work_period = 0.5
        
        self._new_data_event = threading.Event()
        
        self._last_last_new_data_event_time = 0
        self._last_new_data_event_time = 0
        
        self._controller.sub( self, 'NotifyNewDisplayData', 'notify_new_tag_display_application' )
        
    
    def _GetRestTime( self, service_key, expected_work_period, actual_work_period ):
        
        rest_ratio = None
        
        with self._lock:
            
            if service_key in self._go_faster:
                
                if service_key in self._service_keys_to_needs_work and not self._service_keys_to_needs_work[ service_key ]:
                    
                    self._go_faster.discard( service_key )
                    
                
                rest_ratio = CG.client_controller.new_options.GetInteger( 'tag_display_processing_rest_percentage_work_hard' ) / 100
                
            
        
        if rest_ratio is None:
            
            if self._controller.CurrentlyIdle():
                
                rest_ratio = CG.client_controller.new_options.GetInteger( 'tag_display_processing_rest_percentage_idle' ) / 100
                
            else:
                
                rest_ratio = CG.client_controller.new_options.GetInteger( 'tag_display_processing_rest_percentage_normal' ) / 100
                
                if actual_work_period > expected_work_period * 10:
                    
                    # if suddenly a job blats the user for ten seconds or _ten minutes_ during normal time, we are going to take a big break
                    rest_ratio *= 5
                    
                
            
        
        if actual_work_period > expected_work_period * 10:
            
            # if suddenly a job blats the user for ten seconds or _ten minutes_ during normal time, we are going to take a big break
            rest_ratio *= 30
            
        
        reasonable_work_period = min( 5 * expected_work_period, actual_work_period )
        
        return reasonable_work_period * rest_ratio
        
    
    def _GetServiceKeyToWorkOn( self ):
        
        if len( self._go_faster ) > 0:
            
            service_keys_that_need_work = list( self._go_faster )
            
        else:
            
            service_keys_that_need_work = [ service_key for ( service_key, needs_work ) in self._service_keys_to_needs_work.items() if needs_work ]
            
            if len( service_keys_that_need_work ) == 0:
                
                raise HydrusExceptions.NotFoundException( 'No service keys need work!' )
                
            
        
        ( service_key, ) = random.sample( service_keys_that_need_work, 1 )
        
        return service_key
        
    
    def _GetWorkPeriod( self, service_key ):
        
        with self._lock:
            
            # TODO: reinstitute accelerating time here with a new object
            # ok, this previously did a thing where it remembered the last last work time and accelerated the work time up to 30s
            # we should convert all this work/rest ratio thing, which we use all over the place, into an object we get a context around or something similar and unify it all
            # and then we can do clever stuff like accelerating code in one location!
            
            if service_key in self._go_faster:
                
                return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'tag_display_processing_work_time_ms_work_hard' ) )
                
            
        
        if self._controller.CurrentlyIdle():
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'tag_display_processing_work_time_ms_idle' ) )
            
        else:
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'tag_display_processing_work_time_ms_normal' ) )
            
        
    
    def _WorkPermitted( self ):
        
        if len( self._go_faster ) > 0:
            
            return True
            
        
        # we are getting new display data pretty fast. if it is streaming in, let's take a break
        if not HydrusTime.TimeHasPassed( self._last_last_new_data_event_time + 10 ):
            
            return False
            
        
        if self._controller.CurrentlyIdle():
            
            if self._controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                
                return True
                
            
        else:
            
            if self._controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                
                return True
                
            
        
        return False
        
    
    def _WorkToDo( self ):
        
        can_do_work = False
        
        service_keys = self._controller.services_manager.GetServiceKeys( HC.REAL_TAG_SERVICES )
        
        for service_key in service_keys:
            
            if service_key not in self._service_keys_to_needs_work:
                
                status = self._controller.Read( 'tag_display_maintenance_status', service_key )
                
                work_to_do = status[ 'num_siblings_to_sync' ] + status[ 'num_parents_to_sync' ] > 0
                sync_halted = len( status[ 'waiting_on_tag_repos' ] ) > 0
                
                self._service_keys_to_needs_work[ service_key ] = work_to_do and not sync_halted
                
            
            if self._service_keys_to_needs_work[ service_key ]:
                
                can_do_work = True
                
            
        
        return can_do_work
        
    
    def CurrentlyGoingFaster( self, service_key ):
        
        with self._lock:
            
            return service_key in self._go_faster
            
        
    
    def FlipSyncFaster( self, service_key ):
        
        with self._lock:
            
            if service_key in self._go_faster:
                
                self._go_faster.discard( service_key )
                
            else:
                
                self._go_faster.add( service_key )
                
            
        
        self._controller.pub( 'notify_new_tag_display_sync_status', service_key )
        
        self.Wake()
        
    
    def GetName( self ) -> str:
        
        return 'tag display sync'
        
    
    def _DoMainLoop( self ):
        
        while True:
            
            with self._lock:
                
                self._CheckShutdown()
                
            
            self._controller.WaitUntilViewFree()
            
            if self._WorkPermitted() and self._WorkToDo():
                
                try:
                    
                    service_key = self._GetServiceKeyToWorkOn()
                    
                except HydrusExceptions.NotFoundException:
                    
                    self._wake_event.wait( 5 )
                    
                    self._wake_event.clear()
                    
                    continue
                    
                
                expected_work_period = self._GetWorkPeriod( service_key )
                
                start_time = HydrusTime.GetNowPrecise()
                
                still_needs_work = self._controller.WriteSynchronous( 'sync_tag_display_maintenance', service_key, expected_work_period )
                
                finish_time = HydrusTime.GetNowPrecise()
                
                actual_work_period = finish_time - start_time
                
                self._service_keys_to_needs_work[ service_key ] = still_needs_work
                
                wait_time = self._GetRestTime( service_key, expected_work_period, actual_work_period )
                
                self._last_loop_work_period = expected_work_period
                
            else:
                
                wait_time = 10
                
            
            with self._lock:
                
                self._CheckShutdown()
                
            
            self._wake_event.wait( wait_time )
            
            self._wake_event.clear()
            
            if self._new_data_event.is_set():
                
                time.sleep( 1 )
                
                self._last_last_new_data_event_time = self._last_new_data_event_time
                self._last_new_data_event_time = HydrusTime.GetNow()
                
                self._service_keys_to_needs_work = {}
                
                self._new_data_event.clear()
                
            
        
        
    
    def NotifyNewDisplayData( self ):
        
        self._new_data_event.set()
        
        self.Wake()
        
    
    def SyncFasterNow( self ) -> bool:
        
        with self._lock:
            
            # this actually initialises the 'needs_work' structure, so it is important
            if self._WorkToDo():
                
                outstanding = { service_key for ( service_key, needs_work ) in self._service_keys_to_needs_work.items() if needs_work }
                
                self._go_faster.update( outstanding )
                
            else:
                
                return False
                
            
        
        for service_key in outstanding:
            
            self._controller.pub( 'notify_new_tag_display_sync_status', service_key )
            
        
        self.Wake()
        
        return True
        
    

class TagDisplayManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER
    SERIALISABLE_NAME = 'Tag Display Manager'
    SERIALISABLE_VERSION = 4
    
    def __init__( self ):
        
        super().__init__()
        
        service_keys_to_tag_filters_defaultdict = lambda: collections.defaultdict( HydrusTags.TagFilter )
        
        self._tag_display_types_to_service_keys_to_tag_filters = collections.defaultdict( service_keys_to_tag_filters_defaultdict )
        
        self._tag_service_keys_to_tag_autocomplete_options = dict()
        
        self._lock = threading.Lock()
        self._dirty = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_tag_display_types_to_service_keys_to_tag_filters = []
        
        for ( tag_display_type, service_keys_to_tag_filters ) in self._tag_display_types_to_service_keys_to_tag_filters.items():
            
            serialisable_service_keys_to_tag_filters = [ ( service_key.hex(), tag_filter.GetSerialisableTuple() ) for ( service_key, tag_filter ) in service_keys_to_tag_filters.items() ]
            
            serialisable_tag_display_types_to_service_keys_to_tag_filters.append( ( tag_display_type, serialisable_service_keys_to_tag_filters ) )
            
        
        serialisable_tag_autocomplete_options = HydrusSerialisable.SerialisableList( self._tag_service_keys_to_tag_autocomplete_options.values() ).GetSerialisableTuple()
        
        serialisable_info = [
            serialisable_tag_display_types_to_service_keys_to_tag_filters,
            serialisable_tag_autocomplete_options
        ]
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        [
            serialisable_tag_display_types_to_service_keys_to_tag_filters,
            serialisable_tag_autocomplete_options
        ] = serialisable_info
        
        for ( tag_display_type, serialisable_service_keys_to_tag_filters ) in serialisable_tag_display_types_to_service_keys_to_tag_filters:
            
            for ( serialisable_service_key, serialisable_tag_filter ) in serialisable_service_keys_to_tag_filters:
                
                service_key = bytes.fromhex( serialisable_service_key )
                tag_filter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filter )
                
                self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ] = tag_filter
                
            
        
        self._tag_service_keys_to_tag_autocomplete_options = { tag_autocomplete_options.GetServiceKey() : tag_autocomplete_options for tag_autocomplete_options in HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_autocomplete_options ) }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            serialisable_tag_display_types_to_service_keys_to_tag_filters = old_serialisable_info
            
            tag_autocomplete_options_list = HydrusSerialisable.SerialisableList()
            
            new_serialisable_info = [
                serialisable_tag_display_types_to_service_keys_to_tag_filters,
                tag_autocomplete_options_list.GetSerialisableTuple()
            ]
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            [
                serialisable_tag_display_types_to_service_keys_to_tag_filters,
                serialisable_tag_autocomplete_options
            ] = old_serialisable_info
            
            service_keys_to_ordered_sibling_service_keys = collections.defaultdict( list )
            service_keys_to_ordered_parent_service_keys = collections.defaultdict( list )
            
            serialisable_service_keys_to_ordered_sibling_service_keys = HydrusSerialisable.SerialisableBytesDictionary( service_keys_to_ordered_sibling_service_keys ).GetSerialisableTuple()
            serialisable_service_keys_to_ordered_parent_service_keys = HydrusSerialisable.SerialisableBytesDictionary( service_keys_to_ordered_parent_service_keys ).GetSerialisableTuple()
            
            new_serialisable_info = [
                serialisable_tag_display_types_to_service_keys_to_tag_filters,
                serialisable_tag_autocomplete_options,
                serialisable_service_keys_to_ordered_sibling_service_keys,
                serialisable_service_keys_to_ordered_parent_service_keys
            ]
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            # took it out again lmao, down to the db
            
            [
                serialisable_tag_display_types_to_service_keys_to_tag_filters,
                serialisable_tag_autocomplete_options,
                serialisable_service_keys_to_ordered_sibling_service_keys,
                serialisable_service_keys_to_ordered_parent_service_keys
            ] = old_serialisable_info
            
            
            new_serialisable_info = [
                serialisable_tag_display_types_to_service_keys_to_tag_filters,
                serialisable_tag_autocomplete_options
            ]
            
            return ( 4, new_serialisable_info )
        
        
    
    def ClearTagDisplayOptions( self ):
        
        with self._lock:
            
            service_keys_to_tag_filters_defaultdict = lambda: collections.defaultdict( HydrusTags.TagFilter )
            
            self._tag_display_types_to_service_keys_to_tag_filters = collections.defaultdict( service_keys_to_tag_filters_defaultdict )
            
            self._tag_service_keys_to_tag_autocomplete_options = dict()
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetDirty( self ):
        
        with self._lock:
            
            self._dirty = True
            
        
    
    def FilterTags( self, tag_display_type, service_key, tags ):
        
        with self._lock:
            
            if service_key in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                
                tag_filter = self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ]
                
                tags = tag_filter.Filter( tags )
                
            
            if service_key != CC.COMBINED_TAG_SERVICE_KEY and CC.COMBINED_TAG_SERVICE_KEY in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                
                tag_filter = self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ CC.COMBINED_TAG_SERVICE_KEY ]
                
                tags = tag_filter.Filter( tags )
                
            
            return tags
            
        
    
    def FiltersTags( self, tag_display_type, service_key ):
        
        with self._lock:
            
            if service_key in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                
                return True
                
            
            if service_key != CC.COMBINED_TAG_SERVICE_KEY and CC.COMBINED_TAG_SERVICE_KEY in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                
                return True
                
            
            return False
            
        
    
    def GetTagAutocompleteOptions( self, service_key: bytes ):
        
        with self._lock:
            
            if service_key not in self._tag_service_keys_to_tag_autocomplete_options:
                
                tag_autocomplete_options = TagAutocompleteOptions( service_key )
                
                self._tag_service_keys_to_tag_autocomplete_options[ service_key ] = tag_autocomplete_options
                
            
            return self._tag_service_keys_to_tag_autocomplete_options[ service_key ]
            
        
    
    def GetTagFilter( self, tag_display_type, service_key ):
        
        with self._lock:
            
            return self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ].Duplicate()
            
        
    
    def HideTag( self, tag_display_type, service_key, tag ):
        
        self.HideTags( tag_display_type, service_key, ( tag, ) )
        
    
    def HideTags( self, tag_display_type, service_key, tags ):
        
        with self._lock:
            
            tag_filter = self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ]
            
            tag_filter.SetRules( tags, HC.FILTER_BLACKLIST )
            
            self._dirty = True
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetTagAutocompleteOptions( self, tag_autocomplete_options: TagAutocompleteOptions ):
        
        with self._lock:
            
            self._tag_service_keys_to_tag_autocomplete_options[ tag_autocomplete_options.GetServiceKey() ] = tag_autocomplete_options
            
        
    
    def SetTagFilter( self, tag_display_type, service_key, tag_filter ):
        
        with self._lock:
            
            if tag_filter.AllowsEverything():
                
                if service_key in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                    
                    del self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ]
                    
                    self._dirty = True
                    
                
            else:
                
                self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ] = tag_filter
                
                self._dirty = True
                
            
        
    
    def TagOK( self, tag_display_type, service_key, tag ):
        
        return len( self.FilterTags( tag_display_type, service_key, ( tag, ) ) ) > 0
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER ] = TagDisplayManager

class TagParentsStructure( object ):
    
    def __init__( self ):
        
        self._descendants_to_ancestors = collections.defaultdict( set )
        self._ancestors_to_descendants = collections.defaultdict( set )
        
        # some sort of structure for 'bad cycles' so we can later raise these to the user to fix
        # we now do this elsewhere, in the dialog code. maybe we'll want to merge, not sure
        
    
    def AddPair( self, child: object, parent: object ):
        
        # disallowed parents are:
        # A -> A
        # larger loops
        
        if child == parent:
            
            return
            
        
        if parent in self._descendants_to_ancestors:
            
            if child in self._descendants_to_ancestors[ parent ]:
                
                # this is a loop!
                
                return
                
            
        
        if child in self._descendants_to_ancestors and parent in self._descendants_to_ancestors[ child ]:
            
            # already in
            
            return
            
        
        # let's now gather all ancestors of parent and all descendants of child
        
        new_ancestors = { parent }
        
        if parent in self._descendants_to_ancestors:
            
            new_ancestors.update( self._descendants_to_ancestors[ parent ] )
            
        
        new_descendants = { child }
        
        if child in self._ancestors_to_descendants:
            
            new_descendants.update( self._ancestors_to_descendants[ child ] )
            
        
        # every (grand)parent now gets all new (grand)kids
        for ancestor in new_ancestors:
            
            self._ancestors_to_descendants[ ancestor ].update( new_descendants )
            
        
        # every (grand)kid now gets all new (grand)parents
        for descendant in new_descendants:
            
            self._descendants_to_ancestors[ descendant ].update( new_ancestors )
            
        
    
    def GetTagsToAncestors( self ):
        
        return self._descendants_to_ancestors
        
    
    def IterateDescendantAncestorPairs( self ):
        
        for ( descandant, ancestors ) in self._descendants_to_ancestors.items():
            
            for ancestor in ancestors:
                
                yield ( descandant, ancestor )
                
            
        
    
class TagSiblingsStructure( object ):
    
    def __init__( self ):
        
        self._bad_tags_to_good_tags = {}
        self._bad_tags_to_ideal_tags = {}
        self._ideal_tags_to_all_worse_tags = collections.defaultdict( set )
        
        # some sort of structure for 'bad cycles' so we can later raise these to the user to fix
        # we now do this elsewhere, in the dialog code. maybe we'll want to merge, not sure
        
    
    def AddPair( self, bad_tag: object, good_tag: object ):
        
        # disallowed siblings are:
        # A -> A
        # larger loops
        # A -> C when A -> B already exists
        
        if bad_tag == good_tag:
            
            return
            
        
        if bad_tag in self._bad_tags_to_good_tags:
            
            return
            
        
        joining_existing_chain = good_tag in self._bad_tags_to_ideal_tags
        extending_existing_chain = bad_tag in self._ideal_tags_to_all_worse_tags
        
        if extending_existing_chain and joining_existing_chain:
            
            joined_chain_ideal = self._bad_tags_to_ideal_tags[ good_tag ]
            
            if joined_chain_ideal == bad_tag:
                
                # we found a cycle, as the ideal of the chain we are joining is our bad tag
                # basically the chain we are joining and the chain we are extending are the same one
                
                return
                
            
        
        # now compute our ideal
        
        ideal_tags_that_need_updating = set()
        
        if joining_existing_chain:
            
            # our ideal will be the end of that chain
            
            ideal_tag = self._bad_tags_to_ideal_tags[ good_tag ]
            
        else:
            
            ideal_tag = good_tag
            
        
        self._bad_tags_to_good_tags[ bad_tag ] = good_tag
        self._bad_tags_to_ideal_tags[ bad_tag ] = ideal_tag
        self._ideal_tags_to_all_worse_tags[ ideal_tag ].add( bad_tag )
        
        if extending_existing_chain:
            
            # the existing chain needs its ideal updating
            
            old_ideal_tag = bad_tag
            
            bad_tags_that_need_updating = self._ideal_tags_to_all_worse_tags[ old_ideal_tag ]
            
            for bad_tag_that_needs_updating in bad_tags_that_need_updating:
                
                self._bad_tags_to_ideal_tags[ bad_tag_that_needs_updating ] = ideal_tag
                
            
            self._ideal_tags_to_all_worse_tags[ ideal_tag ].update( bad_tags_that_need_updating )
            
            del self._ideal_tags_to_all_worse_tags[ old_ideal_tag ]
            
        
    
    def GetBadTagsToIdealTags( self ):
        
        return self._bad_tags_to_ideal_tags
        
    
