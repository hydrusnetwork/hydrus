import collections
import threading

from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC

TAG_DISPLAY_STORAGE = 0
TAG_DISPLAY_ACTUAL = 1
TAG_DISPLAY_SINGLE_MEDIA = 2
TAG_DISPLAY_SELECTION_LIST = 3
TAG_DISPLAY_IDEAL = 4

have_shown_invalid_tag_warning = False

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
        
    
def RenderTag( tag, render_for_user: bool ):
    
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
        
    
def SortTags( sort_by, tags_list, tags_to_count = None, item_to_tag_key_wrapper = None ):
    
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
            
        
    
    sorts_to_do = []
    
    if sort_by in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
        
        # let's establish a-z here for equal incidence values later
        if sort_by in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC ):
            
            sorts_to_do.append( ( lexicographic_key, True ) )
            
            reverse = False
            
        elif sort_by in ( CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
            
            sorts_to_do.append( ( lexicographic_key, False ) )
            
            reverse = True
            
        
        sorts_to_do.append( ( incidence_key, reverse ) )
        
        if sort_by in ( CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
            
            # python list sort is stable, so lets now sort again
            
            if sort_by == CC.SORT_BY_INCIDENCE_NAMESPACE_ASC:
                
                reverse = True
                
            elif sort_by == CC.SORT_BY_INCIDENCE_NAMESPACE_DESC:
                
                reverse = False
                
            
            sorts_to_do.append( ( namespace_key, reverse ) )
            
        
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
            
        
        sorts_to_do.append( ( key, reverse ) )
        
    
    for ( key, reverse ) in sorts_to_do:
        
        key_to_use = key
        
        if item_to_tag_key_wrapper is not None:
            
            key_to_use = lambda item: key( item_to_tag_key_wrapper( item ) )
            
        
        tags_list.sort( key = key_to_use, reverse = reverse )
        
    
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

class TagFilter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER
    SERIALISABLE_NAME = 'Tag Filter Rules'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._tag_slices_to_rules = {}
        
        self._all_unnamespaced_whitelisted = False
        self._all_namespaced_whitelisted = False
        self._namespaces_whitelist = set()
        self._tags_whitelist = set()
        
        self._all_unnamespaced_blacklisted = False
        self._all_namespaced_blacklisted = False
        self._namespaces_blacklist = set()
        self._tags_blacklist = set()
        
        self._namespaced_interesting = False
        self._tags_interesting = False
        
    
    def __eq__( self, other ):
        
        if isinstance( other, TagFilter ):
            
            return self._tag_slices_to_rules == other._tag_slices_to_rules
            
        
        return NotImplemented
        
    
    def _IterateTagSlices( self, tag, apply_unnamespaced_rules_to_namespaced_tags ):
        
        # this guy gets called a lot, so we are making it an iterator
        
        yield tag
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if tag != subtag and apply_unnamespaced_rules_to_namespaced_tags:
            
            yield subtag
            
        
        if namespace != '':
            
            yield '{}:'.format( namespace )
            yield ':'
            
        else:
            
            yield ''
            
        
    
    def _GetSerialisableInfo( self ):
        
        return list( self._tag_slices_to_rules.items() )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._tag_slices_to_rules = dict( serialisable_info )
        
        self._UpdateRuleCache()
        
    
    def _TagOK( self, tag, apply_unnamespaced_rules_to_namespaced_tags = False ):
        
        # old method, has a bunch of overhead due to iteration
        '''
        blacklist_encountered = False
        
        for tag_slice in self._IterateTagSlices( tag, apply_unnamespaced_rules_to_namespaced_tags = apply_unnamespaced_rules_to_namespaced_tags ):
            
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
            
        '''
        
        #
        
        # since this is called a whole bunch and overhead piles up, we are now splaying the logic out to hardcoded tests
        
        blacklist_encountered = False
        
        if self._tags_interesting:
            
            if tag in self._tags_whitelist:
                
                return True
                
            
            if tag in self._tags_blacklist:
                
                blacklist_encountered = True
                
            
        
        if self._namespaced_interesting or apply_unnamespaced_rules_to_namespaced_tags:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if apply_unnamespaced_rules_to_namespaced_tags and self._tags_interesting and subtag != tag:
                
                if subtag in self._tags_whitelist:
                    
                    return True
                    
                
                if subtag in self._tags_blacklist:
                    
                    blacklist_encountered = True
                    
                
            
            if self._namespaced_interesting:
                
                if namespace == '':
                    
                    if self._all_unnamespaced_whitelisted:
                        
                        return True
                        
                    
                    if self._all_unnamespaced_blacklisted:
                        
                        blacklist_encountered = True
                        
                    
                else:
                    
                    if self._all_namespaced_whitelisted or namespace in self._namespaces_whitelist:
                        
                        return True
                        
                    
                    if self._all_namespaced_blacklisted or namespace in self._namespaces_blacklist:
                        
                        blacklist_encountered = True
                        
                    
                
            
        
        if blacklist_encountered: # rule against and no exceptions
            
            return False
            
        else:
            
            return True # no rules against or explicitly for, so permitted
            
        
    
    def _UpdateRuleCache( self ):
        
        self._all_unnamespaced_whitelisted = False
        self._all_namespaced_whitelisted = False
        self._namespaces_whitelist = set()
        self._tags_whitelist = set()
        
        self._all_unnamespaced_blacklisted = False
        self._all_namespaced_blacklisted = False
        self._namespaces_blacklist = set()
        self._tags_blacklist = set()
        
        self._namespaced_interesting = False
        self._tags_interesting = False
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if tag_slice == '':
                
                if rule == CC.FILTER_WHITELIST:
                    
                    self._all_unnamespaced_whitelisted = True
                    
                else:
                    
                    self._all_unnamespaced_blacklisted = True
                    
                
                self._namespaced_interesting = True
                
            elif tag_slice == ':':
                
                if rule == CC.FILTER_WHITELIST:
                    
                    self._all_namespaced_whitelisted = True
                    
                else:
                    
                    self._all_namespaced_blacklisted = True
                    
                
                self._namespaced_interesting = True
                
            elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
                
                if rule == CC.FILTER_WHITELIST:
                    
                    self._namespaces_whitelist.add( tag_slice[:-1] )
                    
                else:
                    
                    self._namespaces_blacklist.add( tag_slice[:-1] )
                    
                
                self._namespaced_interesting = True
                
            else:
                
                if rule == CC.FILTER_WHITELIST:
                    
                    self._tags_whitelist.add( tag_slice )
                    
                else:
                    
                    self._tags_blacklist.add( tag_slice )
                    
                
                self._tags_interesting = True
                
            
        
    
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
            
            self._UpdateRuleCache()
            
        
    
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
