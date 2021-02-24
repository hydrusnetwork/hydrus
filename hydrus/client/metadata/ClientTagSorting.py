from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC

def SortTags( sort_by, list_of_tag_items, tag_items_to_count = None, item_to_tag_key_wrapper = None ):
    
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
        
    
    def incidence_key( tag_item ):
        
        if tag_items_to_count is None:
            
            return 1
            
        else:
            
            return tag_items_to_count[ tag_item ]
            
        
    
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
        
        if key_to_use != incidence_key: # other keys use tag, incidence uses tag item
            
            if item_to_tag_key_wrapper is not None:
                
                key_to_use = lambda item: key( item_to_tag_key_wrapper( item ) )
                
            
        
        list_of_tag_items.sort( key = key_to_use, reverse = reverse )
        
    