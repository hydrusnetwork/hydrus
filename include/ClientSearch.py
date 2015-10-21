import ClientData
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import re
import wx

def SearchEntryMatchesPredicate( search_entry, predicate ):
    
    ( predicate_type, value, inclusive ) = predicate.GetInfo()
    
    if predicate_type == HC.PREDICATE_TYPE_TAG: return SearchEntryMatchesTag( search_entry, value, search_siblings = True )
    else: return False

def SearchEntryMatchesTag( search_entry, tag, search_siblings = True ):
    
    def compile_re( s ):
        
        regular_parts_of_s = s.split( '*' )
        
        escaped_parts_of_s = [ re.escape( part ) for part in regular_parts_of_s ]
        
        s = '.*'.join( escaped_parts_of_s )
        
        return re.compile( '(\\A|\\s)' + s + '(\\s|\\Z)', flags = re.UNICODE )
        
    
    if ':' in search_entry:
        
        search_namespace = True
        
        ( namespace_entry, search_entry ) = search_entry.split( ':', 1 )
        
        namespace_re_predicate = compile_re( namespace_entry )
        
    else: search_namespace = False
    
    if '*' not in search_entry: search_entry += '*'
    
    re_predicate = compile_re( search_entry )
    
    if search_siblings:
        
        sibling_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        tags = sibling_manager.GetAllSiblings( tag )
        
    else: tags = [ tag ]
    
    for tag in tags:
        
        if ':' in tag:
            
            ( n, t ) = tag.split( ':', 1 )
            
            if search_namespace and re.search( namespace_re_predicate, n ) is None: continue
            
            comparee = t
            
        else:
            
            if search_namespace: continue
            
            comparee = tag
            
        
        if re.search( re_predicate, comparee ) is not None: return True
        
    
    return False

def FilterPredicates( search_entry, predicates, service_key = None, expand_parents = False ):
    
    matches = [ predicate for predicate in predicates if SearchEntryMatchesPredicate( search_entry, predicate ) ]
    
    if service_key is not None and expand_parents:
        
        parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
        
        matches = parents_manager.ExpandPredicates( service_key, matches )
        
    
    return matches

def SortPredicates( predicates, collapse_siblings = False ):
    
    if collapse_siblings:
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        predicates = siblings_manager.CollapsePredicates( predicates )
        
    
    def cmp_func( x, y ): return cmp( x.GetCount(), y.GetCount() )
    
    predicates.sort( cmp = cmp_func, reverse = True )
    
    return predicates

SYSTEM_PREDICATE_INBOX = ClientData.Predicate( HC.PREDICATE_TYPE_SYSTEM_INBOX, None )

SYSTEM_PREDICATE_ARCHIVE = ClientData.Predicate( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, None )

SYSTEM_PREDICATE_LOCAL = ClientData.Predicate( HC.PREDICATE_TYPE_SYSTEM_LOCAL, None )

SYSTEM_PREDICATE_NOT_LOCAL = ClientData.Predicate( HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None )

    
    
    
    
    
