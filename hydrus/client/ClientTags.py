import collections
import threading
import typing

from hydrus.client import ClientConstants as CC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

def ConvertTagSliceToString( tag_slice ):
    
    if tag_slice == '':
        
        return 'unnamespaced tags'
        
    elif tag_slice == ':':
        
        return 'namespaced tags'
        
    elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
        
        namespace = tag_slice[ : -1 ]
        
        return '\'' + namespace + '\' tags'
        
    else:
        
        return tag_slice
        
    
def RenderNamespaceForUser( namespace ):
    
    if namespace == '' or namespace is None:
        
        return 'unnamespaced'
        
    else:
        
        return namespace
        
    
def RenderTag( tag, render_for_user ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    if namespace == '':
        
        return subtag
        
    else:
        
        if render_for_user:
            
            new_options = HG.client_controller.new_options
            
            if new_options.GetBoolean( 'show_namespaces' ):
                
                connector = new_options.GetString( 'namespace_connector' )
                
            else:
                
                return subtag
                
            
        else:
            
            connector = ':'
            
        
        return namespace + connector + subtag
        
    
def SortTags( sort_by, tags_list, tags_to_count = None ):
    
    def lexicographic_key( tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        comparable_namespace = HydrusTags.ConvertTagToSortable( namespace )
        comparable_subtag = HydrusTags.ConvertTagToSortable( subtag )
        
        if namespace == '':
            
            return ( comparable_subtag, comparable_subtag )
            
        else:
            
            return ( comparable_namespace, comparable_subtag )
            
        
    
    def subtag_lexicographic_key( tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        comparable_subtag = HydrusTags.ConvertTagToSortable( subtag )
        
        return comparable_subtag
        
    
    def incidence_key( tag ):
        
        if tags_to_count is None:
            
            return 1
            
        else:
            
            return tags_to_count[ tag ]
            
        
    
    def namespace_key( tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if namespace == '':
            
            namespace = '{' # '{' is above 'z' in ascii, so this works for most situations
            
        
        return namespace
        
    
    def namespace_lexicographic_key( tag ):
        
        # '{' is above 'z' in ascii, so this works for most situations
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if namespace == '':
            
            return ( '{', HydrusTags.ConvertTagToSortable( subtag ) )
            
        else:
            
            return ( namespace, HydrusTags.ConvertTagToSortable( subtag ) )
            
        
    
    if sort_by in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
        
        # let's establish a-z here for equal incidence values later
        if sort_by in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC ):
            
            tags_list.sort( key = lexicographic_key, reverse = True )
            
            reverse = False
            
        elif sort_by in ( CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
            
            tags_list.sort( key = lexicographic_key )
            
            reverse = True
            
        
        tags_list.sort( key = incidence_key, reverse = reverse )
        
        if sort_by in ( CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
            
            # python list sort is stable, so lets now sort again
            
            if sort_by == CC.SORT_BY_INCIDENCE_NAMESPACE_ASC:
                
                reverse = True
                
            elif sort_by == CC.SORT_BY_INCIDENCE_NAMESPACE_DESC:
                
                reverse = False
                
            
            tags_list.sort( key = namespace_key, reverse = reverse )
            
        
    else:
        
        if sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_DESC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC, CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_DESC ):
            
            reverse = True
            
        elif sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_ASC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_ASC ):
            
            reverse = False
            
        
        if sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC ):
            
            key = namespace_lexicographic_key
            
        elif sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_ASC, CC.SORT_BY_LEXICOGRAPHIC_DESC ):
            
            key = lexicographic_key
            
        elif sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_DESC ):
            
            key = subtag_lexicographic_key
            
        
        tags_list.sort( key = key, reverse = reverse )
        
    
class ServiceKeysToTags( HydrusSerialisable.SerialisableBase, collections.defaultdict ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS
    SERIALISABLE_NAME = 'Service Keys To Tags'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, *args, **kwargs ):
        
        collections.defaultdict.__init__( self, set, *args, **kwargs )
        HydrusSerialisable.SerialisableBase.__init__( self )
        
    
    def _GetSerialisableInfo( self ):
        
        return [ ( service_key.hex(), list( tags ) ) for ( service_key, tags ) in self.items() ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( service_key_hex, tags_list ) in serialisable_info:
            
            self[ bytes.fromhex( service_key_hex ) ] = set( tags_list )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS ] = ServiceKeysToTags

TAG_DISPLAY_STORAGE = 0
TAG_DISPLAY_SIBLINGS_AND_PARENTS = 1
TAG_DISPLAY_SINGLE_MEDIA = 2
TAG_DISPLAY_SELECTION_LIST = 3

class TagAutocompleteOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_AUTOCOMPLETE_OPTIONS
    SERIALISABLE_NAME = 'Tag Autocomplete Options'
    SERIALISABLE_VERSION = 1
    
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
            self._namespace_fetch_all_allowed,
            self._fetch_all_allowed
        ] = serialisable_info
        
        self._service_key = bytes.fromhex( serialisable_service_key )
        self._write_autocomplete_tag_domain = bytes.fromhex( serialisable_write_autocomplete_tag_domain )
        self._write_autocomplete_file_domain = bytes.fromhex( serialisable_write_autocomplete_file_domain )
        
    
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
        namespace_fetch_all_allowed: bool,
        fetch_all_allowed: bool
    ):
        
        self._write_autocomplete_tag_domain = write_autocomplete_tag_domain
        self._override_write_autocomplete_file_domain = override_write_autocomplete_file_domain
        self._write_autocomplete_file_domain = write_autocomplete_file_domain
        self._search_namespaces_into_full_tags = search_namespaces_into_full_tags
        self._namespace_fetch_all_allowed = namespace_fetch_all_allowed
        self._fetch_all_allowed = fetch_all_allowed
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_AUTOCOMPLETE_OPTIONS ] = TagAutocompleteOptions

class TagDisplayManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER
    SERIALISABLE_NAME = 'Tag Display Manager'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        service_keys_to_tag_filters_defaultdict = lambda: collections.defaultdict( TagFilter )
        
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

TAG_DISPLAY_STORAGE = 0
TAG_DISPLAY_SIBLINGS_AND_PARENTS = 1
TAG_DISPLAY_SINGLE_MEDIA = 2
TAG_DISPLAY_SELECTION_LIST = 3

class TagFilter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER
    SERIALISABLE_NAME = 'Tag Filter Rules'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._tag_slices_to_rules = {}
        
    
    def __eq__( self, other ):
        
        if isinstance( other, TagFilter ):
            
            return self._tag_slices_to_rules == other._tag_slices_to_rules
            
        
        return NotImplemented
        
    
    def _GetTagSlices( self, tag, apply_unnamespaced_rules_to_namespaced_tags ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        tag_slices = []
        
        tag_slices.append( tag )
        
        if tag != subtag and apply_unnamespaced_rules_to_namespaced_tags:
            
            tag_slices.append( subtag )
            
        
        if namespace != '':
            
            tag_slices.append( namespace + ':' )
            tag_slices.append( ':' )
            
        else:
            
            tag_slices.append( '' )
            
        
        return tag_slices
        
    
    def _GetSerialisableInfo( self ):
        
        return list( self._tag_slices_to_rules.items() )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._tag_slices_to_rules = dict( serialisable_info )
        
    
    def _TagOK( self, tag, apply_unnamespaced_rules_to_namespaced_tags = False ):
        
        tag_slices = self._GetTagSlices( tag, apply_unnamespaced_rules_to_namespaced_tags = apply_unnamespaced_rules_to_namespaced_tags )
        
        blacklist_encountered = False
        
        for tag_slice in tag_slices:
            
            if tag_slice in self._tag_slices_to_rules:
                
                rule = self._tag_slices_to_rules[ tag_slice ]
                
                if rule == CC.FILTER_WHITELIST:
                    
                    return True # there is an exception for this class of tag
                    
                elif rule == CC.FILTER_BLACKLIST: # there is a rule against this class of tag
                    
                    blacklist_encountered = True
                    
                
            
        
        if blacklist_encountered: # rule against and no exceptions
            
            return False
            
        else:
            
            return True # no rules against or explicitly for, so permitted
            
        
    
    def AllowsEverything( self ):
        
        with self._lock:
            
            for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
                
                if rule == CC.FILTER_BLACKLIST:
                    
                    return False
                    
                
            
            return True
            
        
    
    def Filter( self, tags, apply_unnamespaced_rules_to_namespaced_tags = False ):
        
        with self._lock:
            
            return { tag for tag in tags if self._TagOK( tag, apply_unnamespaced_rules_to_namespaced_tags = apply_unnamespaced_rules_to_namespaced_tags ) }
            
        
    
    def GetTagSlicesToRules( self ):
        
        with self._lock:
            
            return dict( self._tag_slices_to_rules )
            
        
    
    def SetRule( self, tag_slice, rule ):
        
        with self._lock:
            
            self._tag_slices_to_rules[ tag_slice ] = rule
            
        
    
    def TagOK( self, tag, apply_unnamespaced_rules_to_namespaced_tags = False ):
        
        with self._lock:
            
            return self._TagOK( tag, apply_unnamespaced_rules_to_namespaced_tags = apply_unnamespaced_rules_to_namespaced_tags )
            
        
    
    def ToBlacklistString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
                
                if rule == CC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == CC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'no blacklist set'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    text = 'blacklisting on any tags'
                    
                else:
                    
                    text = 'blacklisting on ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                    
                
                if len( whitelist ) > 0:
                    
                    text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
                return text
                
            
        
    
    def ToCensoredString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in list(self._tag_slices_to_rules.items()):
                
                if rule == CC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == CC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'all tags allowed'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    text = 'no tags allowed'
                    
                else:
                    
                    text = 'all but ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) ) + ' allowed'
                    
                
                if len( whitelist ) > 0:
                    
                    text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
                return text
                
            
        
    
    def ToPermittedString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in list(self._tag_slices_to_rules.items()):
                
                if rule == CC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == CC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'all tags'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    if len( whitelist ) == 0:
                        
                        text = 'no tags'
                        
                    else:
                        
                        text = 'only ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                elif set( blacklist ) == { '' }:
                    
                    text = 'all namespaced tags'
                    
                    if len( whitelist ) > 0:
                        
                        text += ' and ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                elif set( blacklist ) == { ':' }:
                    
                    text = 'all unnamespaced tags'
                    
                    if len( whitelist ) > 0:
                        
                        text += ' and ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                else:
                    
                    text = 'all tags except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                    
                    if len( whitelist ) > 0:
                        
                        text += ' (except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) ) + ')'
                        
                    
                
            
            return text
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER ] = TagFilter

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
            
            joined_chain_ideal = self._bad_tags_to_ideal_tags
            
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
        
