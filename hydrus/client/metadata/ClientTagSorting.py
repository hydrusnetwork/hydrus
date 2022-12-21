import typing

from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC

SORT_BY_HUMAN_TAG = 0
SORT_BY_HUMAN_SUBTAG = 1
SORT_BY_COUNT = 2

GROUP_BY_NOTHING = 0
GROUP_BY_NAMESPACE = 1

sort_type_str_lookup = {
    SORT_BY_HUMAN_TAG : 'sort by tag',
    SORT_BY_HUMAN_SUBTAG : 'sort by subtag',
    SORT_BY_COUNT : 'sort by count'
}

class TagSort( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_SORT
    SERIALISABLE_NAME = 'Tag Sort'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, sort_type = None, sort_order = None, use_siblings = None, group_by = None ):
        
        if sort_type is None:
            
            sort_type = SORT_BY_HUMAN_TAG
            
        
        if sort_order is None:
            
            sort_order = CC.SORT_ASC
            
        
        if use_siblings is None:
            
            use_siblings = True
            
        
        if group_by is None:
            
            group_by = GROUP_BY_NOTHING
            
        
        self.sort_type = sort_type
        self.sort_order = sort_order
        self.use_siblings = use_siblings
        self.group_by = group_by
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self.sort_type, self.sort_order, self.use_siblings, self.group_by )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.sort_type, self.sort_order, self.use_siblings, self.group_by ) = serialisable_info
        
    
    def ToString( self ):
        
        return '{} {}{}'.format(
            sort_type_str_lookup[ self.sort_type ],
            'asc' if self.sort_order == CC.SORT_ASC else 'desc',
            ' namespace' if self.group_by == GROUP_BY_NAMESPACE else ''
        )
        
    
    @staticmethod
    def STATICGetTextASCDefault() -> "TagSort":
        
        return TagSort(
            sort_type = SORT_BY_HUMAN_TAG,
            sort_order = CC.SORT_ASC,
            use_siblings = True,
            group_by = GROUP_BY_NOTHING
        )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_SORT ] = TagSort

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
        
    

def SortTags( tag_sort: TagSort, list_of_tag_items: typing.List, tag_items_to_count = None, item_to_tag_key_wrapper = None, item_to_sibling_key_wrapper = None ):
    
    def incidence_key( tag_item ):
        
        if tag_items_to_count is None:
            
            return 1
            
        else:
            
            return tag_items_to_count[ tag_item ]
            
        
    
    sorts_to_do = []
    
    if tag_sort.sort_type == SORT_BY_COUNT:
        
        # let's establish a-z here for equal incidence values later
        if tag_sort.sort_order == CC.SORT_ASC:
            
            sorts_to_do.append( ( lexicographic_key, True ) )
            
            reverse = False
            
        else:
            
            sorts_to_do.append( ( lexicographic_key, False ) )
            
            reverse = True
            
        
        sorts_to_do.append( ( incidence_key, reverse ) )
        
        if tag_sort.group_by == GROUP_BY_NAMESPACE:
            
            # python list sort is stable, so lets now sort again
            
            if tag_sort.sort_order == CC.SORT_ASC:
                
                reverse = True
                
            else:
                
                reverse = False
                
            
            sorts_to_do.append( ( namespace_key, reverse ) )
            
        
    else:
        
        if tag_sort.sort_order == CC.SORT_ASC:
            
            reverse = False
            
        else:
            
            reverse = True
            
        
        if tag_sort.sort_type == SORT_BY_HUMAN_SUBTAG:
            
            key = subtag_lexicographic_key
            
        else:
            
            if tag_sort.group_by == GROUP_BY_NAMESPACE:
                
                key = namespace_lexicographic_key
                
            else:
                
                key = lexicographic_key
                
            
        
        sorts_to_do.append( ( key, reverse ) )
        
    
    for ( key, reverse ) in sorts_to_do:
        
        key_to_use = key
        
        if key_to_use is not incidence_key: # other keys use tag, incidence uses tag item
            
            if tag_sort.use_siblings and item_to_sibling_key_wrapper is not None:
                
                key_to_use = lambda item: key( item_to_sibling_key_wrapper( item ) )
                
            elif item_to_tag_key_wrapper is not None:
                
                key_to_use = lambda item: key( item_to_tag_key_wrapper( item ) )
                
            
        
        list_of_tag_items.sort( key = key_to_use, reverse = reverse )
        
    
