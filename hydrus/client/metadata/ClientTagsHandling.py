import collections
import threading
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientServices
from hydrus.client.metadata import ClientTags

class TagAutocompleteOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_AUTOCOMPLETE_OPTIONS
    SERIALISABLE_NAME = 'Tag Autocomplete Options'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, service_key: typing.Optional[ bytes ] = None ):
        
        if service_key is None:
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._service_key = service_key
        
        self._write_autocomplete_tag_domain = self._service_key
        
        self._override_write_autocomplete_file_domain = True
        
        if service_key == CC.DEFAULT_LOCAL_TAG_SERVICE_KEY:
            
            self._write_autocomplete_file_domain = CC.LOCAL_FILE_SERVICE_KEY
            
        else:
            
            self._write_autocomplete_file_domain = CC.COMBINED_FILE_SERVICE_KEY
            
        
        self._search_namespaces_into_full_tags = False
        self._namespace_bare_fetch_all_allowed = False
        self._namespace_fetch_all_allowed = False
        self._fetch_all_allowed = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_service_key = self._service_key.hex()
        
        serialisable_write_autocomplete_tag_domain = self._write_autocomplete_tag_domain.hex()
        serialisable_write_autocomplete_file_domain = self._write_autocomplete_file_domain.hex()
        
        serialisable_info = [
            serialisable_service_key,
            serialisable_write_autocomplete_tag_domain,
            self._override_write_autocomplete_file_domain,
            serialisable_write_autocomplete_file_domain,
            self._search_namespaces_into_full_tags,
            self._namespace_bare_fetch_all_allowed,
            self._namespace_fetch_all_allowed,
            self._fetch_all_allowed
        ]
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        [
            serialisable_service_key,
            serialisable_write_autocomplete_tag_domain,
            self._override_write_autocomplete_file_domain,
            serialisable_write_autocomplete_file_domain,
            self._search_namespaces_into_full_tags,
            self._namespace_bare_fetch_all_allowed,
            self._namespace_fetch_all_allowed,
            self._fetch_all_allowed
        ] = serialisable_info
        
        self._service_key = bytes.fromhex( serialisable_service_key )
        self._write_autocomplete_tag_domain = bytes.fromhex( serialisable_write_autocomplete_tag_domain )
        self._write_autocomplete_file_domain = bytes.fromhex( serialisable_write_autocomplete_file_domain )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_file_domain,
                serialisable_write_autocomplete_file_domain,
                search_namespaces_into_full_tags,
                namespace_fetch_all_allowed,
                fetch_all_allowed
            ] = old_serialisable_info
            
            namespace_bare_fetch_all_allowed = False
            
            new_serialisable_info = [
                serialisable_service_key,
                serialisable_write_autocomplete_tag_domain,
                override_write_autocomplete_file_domain,
                serialisable_write_autocomplete_file_domain,
                search_namespaces_into_full_tags,
                namespace_bare_fetch_all_allowed,
                namespace_fetch_all_allowed,
                fetch_all_allowed
            ]
            
            
            return ( 2, new_serialisable_info )
            
        
    def FetchAllAllowed( self ):
        
        return self._fetch_all_allowed
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
    def GetWriteAutocompleteFileDomain( self ):
        
        return self._write_autocomplete_file_domain
        
    
    def GetWriteAutocompleteServiceKeys( self, file_service_key: bytes ):
        
        tag_service_key = self._service_key
        
        if self._service_key != CC.COMBINED_TAG_SERVICE_KEY:
            
            if self._override_write_autocomplete_file_domain:
                
                file_service_key = self._write_autocomplete_file_domain
                
            
            tag_service_key = self._write_autocomplete_tag_domain
            
        
        if file_service_key == CC.COMBINED_FILE_SERVICE_KEY and tag_service_key == CC.COMBINED_TAG_SERVICE_KEY: # ruh roh
            
            file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
            
        
        return ( file_service_key, tag_service_key )
        
    
    def GetWriteAutocompleteTagDomain( self ):
        
        return self._write_autocomplete_tag_domain
        
    
    def NamespaceBareFetchAllAllowed( self ):
        
        return self._namespace_bare_fetch_all_allowed
        
    
    def NamespaceFetchAllAllowed( self ):
        
        return self._namespace_fetch_all_allowed
        
    
    def OverridesWriteAutocompleteFileDomain( self ):
        
        return self._override_write_autocomplete_file_domain
        
    
    def SearchNamespacesIntoFullTags( self ):
        
        return self._search_namespaces_into_full_tags
        
    
    def SetTuple( self,
        write_autocomplete_tag_domain: bytes,
        override_write_autocomplete_file_domain: bool,
        write_autocomplete_file_domain: bytes,
        search_namespaces_into_full_tags: bool,
        namespace_bare_fetch_all_allowed: bool,
        namespace_fetch_all_allowed: bool,
        fetch_all_allowed: bool
    ):
        
        self._write_autocomplete_tag_domain = write_autocomplete_tag_domain
        self._override_write_autocomplete_file_domain = override_write_autocomplete_file_domain
        self._write_autocomplete_file_domain = write_autocomplete_file_domain
        self._search_namespaces_into_full_tags = search_namespaces_into_full_tags
        self._namespace_bare_fetch_all_allowed = namespace_bare_fetch_all_allowed
        self._namespace_fetch_all_allowed = namespace_fetch_all_allowed
        self._fetch_all_allowed = fetch_all_allowed
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_AUTOCOMPLETE_OPTIONS ] = TagAutocompleteOptions

class TagDisplayManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER
    SERIALISABLE_NAME = 'Tag Display Manager'
    SERIALISABLE_VERSION = 4
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        service_keys_to_tag_filters_defaultdict = lambda: collections.defaultdict( ClientTags.TagFilter )
        
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
            
            service_keys_to_tag_filters_defaultdict = lambda: collections.defaultdict( ClientTags.TagFilter )
            
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
        
        with self._lock:
            
            tag_filter = self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ]
            
            tag_filter.SetRule( tag, CC.FILTER_BLACKLIST )
            
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

class TagSiblingsStructure( object ):
    
    def __init__( self ):
        
        self._bad_tags_to_good_tags = {}
        self._bad_tags_to_ideal_tags = {}
        self._ideal_tags_to_all_worse_tags = collections.defaultdict( set )
        
        # some sort of structure for 'bad cycles' so we can later raise these to the user to fix
        
    
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
        
