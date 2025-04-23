import typing

from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG

SORT_BY_HUMAN_TAG = 0
SORT_BY_HUMAN_SUBTAG = 1
SORT_BY_COUNT = 2

GROUP_BY_NOTHING = 0
GROUP_BY_NAMESPACE_AZ = 1
GROUP_BY_NAMESPACE_USER = 2

group_by_str_lookup = {
    GROUP_BY_NOTHING : 'no grouping',
    GROUP_BY_NAMESPACE_AZ : 'namespace (a-z)',
    GROUP_BY_NAMESPACE_USER : 'namespace (user)'
}

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
        
    
    def AffectedByCount( self ):
        
        return self.sort_type == SORT_BY_COUNT
        
    
    def ToString( self ):
        
        if self.group_by == GROUP_BY_NOTHING:
            
            gp_str = ''
            
        else:
            
            gp_str = f' {group_by_str_lookup[ self.group_by ]}'
            
        
        return '{} {}{}'.format(
            sort_type_str_lookup[ self.sort_type ],
            'asc' if self.sort_order == CC.SORT_ASC else 'desc',
            gp_str
        )
        
    
    def ToDictForAPI( self ):
        
        return {
            'sort_type' : self.sort_type,
            'sort_order' : self.sort_order,
            'use_siblings': self.use_siblings,
            'group_by' : self.group_by
        }
        
    
    @staticmethod
    def STATICGetTextASCDefault() -> "TagSort":
        
        return TagSort(
            sort_type = SORT_BY_HUMAN_TAG,
            sort_order = CC.SORT_ASC,
            use_siblings = True,
            group_by = GROUP_BY_NOTHING
        )
        
    
    @staticmethod
    def STATICGetTextASCUserGroupedDefault() -> "TagSort":
        
        return TagSort(
            sort_type = SORT_BY_HUMAN_TAG,
            sort_order = CC.SORT_ASC,
            use_siblings = True,
            group_by = GROUP_BY_NAMESPACE_USER
        )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_SORT ] = TagSort

def lexicographic_key( tag ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    comparable_subtag = HydrusText.HumanTextSortKey( subtag )
    
    if namespace == '':
        
        return ( comparable_subtag, comparable_subtag )
        
    else:
        
        comparable_namespace = HydrusText.HumanTextSortKey( namespace )
        
        return ( comparable_namespace, comparable_subtag )
        
    

def subtag_lexicographic_key( tag ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    comparable_subtag = HydrusText.HumanTextSortKey( subtag )
    
    return comparable_subtag
    

def namespace_az_key( tag ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    if namespace == '':
        
        return ( 1, )
        
    else:
        
        comparable_namespace = HydrusText.HumanTextSortKey( namespace )
        
        return ( 0, comparable_namespace )
        
    

def namespace_user_key_factory():
    
    namespace_list = CG.client_controller.new_options.GetStringList( 'user_namespace_group_by_sort' )
    namespace_list_fast = set( namespace_list )
    
    any_namespace_index = len( namespace_list )
    no_namespace_index = any_namespace_index + 1
    
    if ':' in namespace_list:
        
        any_namespace_index = namespace_list.index( ':' )
        
    
    def namespace_user_key( tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if namespace in namespace_list_fast:
            
            index = namespace_list.index( namespace )
            
            return ( index, )
            
        else:
            
            if namespace == '':
                
                return ( no_namespace_index, )
                
            else:
                
                comparable_namespace = HydrusText.HumanTextSortKey( namespace )
                
                return ( any_namespace_index, comparable_namespace )
                
            
        
    
    return namespace_user_key
    

def SortTags( tag_sort: TagSort, list_of_tag_items: typing.List, tag_items_to_count = None, item_to_tag_key_wrapper = None, item_to_sibling_key_wrapper = None ):
    
    def incidence_key( tag_item ):
        
        if tag_items_to_count is None:
            
            return 1
            
        else:
            
            return tag_items_to_count[ tag_item ]
            
        
    
    sorts_to_do = []
    
    if tag_sort.sort_type == SORT_BY_COUNT:
        
        reverse = tag_sort.sort_order == CC.SORT_DESC
        lexicographic_complement_reverse = not reverse
        
        # let's establish a-z here for equal incidence values later
        sorts_to_do.append( ( lexicographic_key, lexicographic_complement_reverse ) )
        
        sorts_to_do.append( ( incidence_key, reverse ) )
        
    else:
        
        reverse = tag_sort.sort_order == CC.SORT_DESC
        lexicographic_complement_reverse = reverse
        
        if tag_sort.sort_type == SORT_BY_HUMAN_SUBTAG:
            
            key = subtag_lexicographic_key
            
        else:
            
            key = lexicographic_key
            
        
        sorts_to_do.append( ( key, reverse ) )
        
    
    if tag_sort.sort_type in ( SORT_BY_COUNT, SORT_BY_HUMAN_TAG ):
        
        if tag_sort.group_by == GROUP_BY_NAMESPACE_AZ:
            
            sorts_to_do.append( ( namespace_az_key, False ) )
            
        elif tag_sort.group_by == GROUP_BY_NAMESPACE_USER:
            
            sorts_to_do.append( ( namespace_user_key_factory(), False ) )
            
        
    
    for ( key, reverse ) in sorts_to_do:
        
        key_to_use = key
        
        if key_to_use is not incidence_key: # other keys use tag, incidence uses tag item
            
            if tag_sort.use_siblings and item_to_sibling_key_wrapper is not None:
                
                key_to_use = lambda item: key( item_to_sibling_key_wrapper( item ) )
                
            elif item_to_tag_key_wrapper is not None:
                
                key_to_use = lambda item: key( item_to_tag_key_wrapper( item ) )
                
            
        
        list_of_tag_items.sort( key = key_to_use, reverse = reverse )
        
    
