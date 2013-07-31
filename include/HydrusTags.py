import collections
import HydrusConstants as HC
import itertools
import os
import threading
import time
import traceback
import wx

def MergeTagsManagers( tag_service_precedence, tags_managers ):
    
    def CurrentAndPendingFilter( items ):
        
        for ( service_identifier, statuses_to_tags ) in items:
            
            filtered = { status : tags for ( status, tags ) in statuses_to_tags.items() if status in ( HC.CURRENT, HC.PENDING ) }
            
            yield ( service_identifier, filtered )
            
        
    
    # [[( service_identifier, statuses_to_tags )]]
    s_i_s_t_t_tupled = ( CurrentAndPendingFilter( tags_manager.GetServiceIdentifiersToStatusesToTags().items() ) for tags_manager in tags_managers )
    
    # [(service_identifier, statuses_to_tags)]
    flattened_s_i_s_t_t = itertools.chain.from_iterable( s_i_s_t_t_tupled )
    
    # service_identifier : [ statuses_to_tags ]
    s_i_s_t_t_dict = HC.BuildKeyToListDict( flattened_s_i_s_t_t )
    
    # now let's merge so we have service_identifier : statuses_to_tags
    
    merged_service_identifiers_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
    
    for ( service_identifier, several_statuses_to_tags ) in s_i_s_t_t_dict.items():
        
        # [[( status, tags )]]
        s_t_t_tupled = ( s_t_t.items() for s_t_t in several_statuses_to_tags )
        
        # [( status, tags )]
        flattened_s_t_t = itertools.chain.from_iterable( s_t_t_tupled )
        
        statuses_to_tags = HC.default_dict_set()
        
        for ( status, tags ) in flattened_s_t_t: statuses_to_tags[ status ].update( tags )
        
        merged_service_identifiers_to_statuses_to_tags[ service_identifier ] = statuses_to_tags
        
    
    return TagsManagerSimple( merged_service_identifiers_to_statuses_to_tags )
    
class TagsManagerSimple():
    
    def __init__( self, service_identifiers_to_statuses_to_tags ):
        
        self._service_identifiers_to_statuses_to_tags = service_identifiers_to_statuses_to_tags
        
        self._combined_namespaces_cache = None
        
    
    def GetCombinedNamespaces( self, namespaces ):
        
        if self._combined_namespaces_cache is None:
    
            combined_statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_IDENTIFIER ]
            
            combined_current = combined_statuses_to_tags[ HC.CURRENT ]
            combined_pending = combined_statuses_to_tags[ HC.PENDING ]
            
            self._combined_namespaces_cache = HC.BuildKeyToSetDict( tag.split( ':', 1 ) for tag in combined_current.union( combined_pending ) if ':' in tag )
            
            only_int_allowed = ( 'volume', 'chapter', 'page' )
            
            for namespace in only_int_allowed:
                
                tags = self._combined_namespaces_cache[ namespace ]
                
                int_tags = set()
                
                for tag in tags:
                    
                    try: tag = int( tag )
                    except: continue
                    
                    int_tags.add( tag )
                    
                
                self._combined_namespaces_cache[ namespace ] = int_tags
                
            
        
        result = { namespace : self._combined_namespaces_cache[ namespace ] for namespace in namespaces }
        
        return result
        
    
    def GetNamespaceSlice( self, namespaces, collapse = True ):
        
        combined_statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_IDENTIFIER ]
        
        combined_current = combined_statuses_to_tags[ HC.CURRENT ]
        combined_pending = combined_statuses_to_tags[ HC.PENDING ]
        
        slice = { tag for tag in combined_current.union( combined_pending ) if True in ( tag.startswith( namespace + ':' ) for namespace in namespaces ) }
        
        if collapse:
            
            siblings_manager = HC.app.GetTagSiblingsManager()
            
            slice = siblings_manager.CollapseTags( slice )
            
        
        slice = frozenset( slice )
        
        return slice
        
    
class TagsManager( TagsManagerSimple ):
    
    def __init__( self, tag_service_precedence, service_identifiers_to_statuses_to_tags ):
        
        TagsManagerSimple.__init__( self, service_identifiers_to_statuses_to_tags )
        
        self._tag_service_precedence = tag_service_precedence
        
    
    def _RecalcCombined( self ):
        
        t_s_p = list( self._tag_service_precedence )
        
        t_s_p.reverse()
        
        combined_current = set()
        combined_pending = set()
        
        for service_identifier in t_s_p:
            
            statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ service_identifier ]
            
            combined_current.update( statuses_to_tags[ HC.CURRENT ] )
            combined_current.difference_update( statuses_to_tags[ HC.DELETED ] )
            
            combined_pending.update( statuses_to_tags[ HC.PENDING ] )
            
        
        combined_statuses_to_tags = collections.defaultdict( set )
        
        combined_statuses_to_tags[ HC.CURRENT ] = combined_current
        combined_statuses_to_tags[ HC.PENDING ] = combined_pending
        
        self._service_identifiers_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_IDENTIFIER ] = combined_statuses_to_tags
        
        self._combined_namespaces_cache = None
        
    
    def DeletePending( self, service_identifier ):
        
        statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ service_identifier ]
        
        if len( statuses_to_tags[ HC.PENDING ] ) + len( statuses_to_tags[ HC.PETITIONED ] ) > 0:
            
            statuses_to_tags[ HC.PENDING ] = set()
            statuses_to_tags[ HC.PETITIONED ] = set()
            
            self._RecalcCombined()
            
        
    
    def GetCurrent( self, service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER ):
        
        statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ service_identifier ]
        
        return set( statuses_to_tags[ HC.CURRENT ] )
        
    
    def GetDeleted( self, service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER ):
        
        statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ service_identifier ]
        
        return statuses_to_tags[ HC.DELETED ]
        
    
    def GetNumTags( self, tag_service_identifier, include_current_tags = True, include_pending_tags = False ):
        
        num_tags = 0
        
        statuses_to_tags = self.GetStatusesToTags( tag_service_identifier )
        
        if include_current_tags: num_tags += len( statuses_to_tags[ HC.CURRENT ] )
        if include_pending_tags: num_tags += len( statuses_to_tags[ HC.PENDING ] )
        
        return num_tags
        
    
    def GetPending( self, service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER ):
        
        statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ service_identifier ]
        
        return statuses_to_tags[ HC.PENDING ]
        
    
    def GetPetitioned( self, service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER ):
        
        statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ service_identifier ]
        
        return set( statuses_to_tags[ HC.PETITIONED ] )
        
    
    def GetServiceIdentifiersToStatusesToTags( self ): return self._service_identifiers_to_statuses_to_tags
    
    def GetStatusesToTags( self, service_identifier ): return self._service_identifiers_to_statuses_to_tags[ service_identifier ]
    
    def HasTag( self, tag ):
        
        combined_statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_IDENTIFIER ]
        
        return tag in combined_statuses_to_tags[ HC.CURRENT ] or tag in combined_statuses_to_tags[ HC.PENDING ]
        
    
    def ProcessContentUpdate( self, service_identifier, content_update ):
        
        statuses_to_tags = self._service_identifiers_to_statuses_to_tags[ service_identifier ]
        
        ( data_type, action, row ) = content_update.ToTuple()
        
        if action == HC.CONTENT_UPDATE_PETITION: ( tag, hashes, reason ) = row
        else: ( tag, hashes ) = row
        
        if action == HC.CONTENT_UPDATE_ADD:
            
            statuses_to_tags[ HC.CURRENT ].add( tag )
            
            statuses_to_tags[ HC.DELETED ].discard( tag )
            statuses_to_tags[ HC.PENDING ].discard( tag )
            
        elif action == HC.CONTENT_UPDATE_DELETE:
            
            statuses_to_tags[ HC.DELETED ].add( tag )
            
            statuses_to_tags[ HC.CURRENT ].discard( tag )
            statuses_to_tags[ HC.PETITIONED ].discard( tag )
            
        elif action == HC.CONTENT_UPDATE_PENDING: statuses_to_tags[ HC.PENDING ].add( tag )
        elif action == HC.CONTENT_UPDATE_RESCIND_PENDING: statuses_to_tags[ HC.PENDING ].discard( tag )
        elif action == HC.CONTENT_UPDATE_PETITION: statuses_to_tags[ HC.PETITIONED ].add( tag )
        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION: statuses_to_tags[ HC.PETITIONED ].discard( tag )
        
        self._RecalcCombined()
        
    
    def ResetService( self, service_identifier ):
        
        if service_identifier in self._service_identifiers_to_statuses_to_tags:
            
            del self._service_identifiers_to_statuses_to_tags[ service_identifier ]
            
            self._RecalcCombined()
            
        
    
def CombineTagParentPairs( tag_service_precedence, service_identifiers_to_statuses_to_pairs ):
    
    service_identifiers_to_pairs_flat = HC.default_dict_set()
    
    combined = service_identifiers_to_pairs_flat[ HC.COMBINED_TAG_SERVICE_IDENTIFIER ]
    
    current_deleted_pairs = set()
    
    for service_identifier in tag_service_precedence:
        
        statuses_to_pairs = service_identifiers_to_statuses_to_pairs[ service_identifier ]
        
        pairs = statuses_to_pairs[ HC.CURRENT ].union( statuses_to_pairs[ HC.PENDING ] )
        
        service_identifiers_to_pairs_flat[ service_identifier ] = pairs
        
        pairs.difference_update( current_deleted_pairs )
        
        combined.update( pairs )
        
        current_deleted_pairs.update( statuses_to_pairs[ HC.DELETED ] )
        
    
    return service_identifiers_to_pairs_flat
    
def BuildSimpleChildrenToParents( pairs ):
    
    simple_children_to_parents = HC.default_dict_set()
    
    for ( child, parent ) in pairs:
        
        if child == parent: continue
        
        if LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ): continue
        
        simple_children_to_parents[ child ].add( parent )
        
    
    return simple_children_to_parents
    
def BuildServiceIdentifiersToSimpleChildrenToParents( service_identifiers_to_pairs_flat ):
    
    service_identifiers_to_simple_children_to_parents = collections.defaultdict( HC.default_dict_set )
    
    for ( service_identifier, pairs ) in service_identifiers_to_pairs_flat.items():
        
        service_identifiers_to_simple_children_to_parents[ service_identifier ] = BuildSimpleChildrenToParents( pairs )
        
    
    return service_identifiers_to_simple_children_to_parents
    
def LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
    
    potential_loop_paths = { parent }
    
    while len( potential_loop_paths.intersection( simple_children_to_parents.keys() ) ) > 0:
        
        new_potential_loop_paths = set()
        
        for potential_loop_path in potential_loop_paths.intersection( simple_children_to_parents.keys() ):
            
            new_potential_loop_paths.update( simple_children_to_parents[ potential_loop_path ] )
            
        
        potential_loop_paths = new_potential_loop_paths
        
        if child in potential_loop_paths: return True
        
    
    return False
    
# important thing here, and reason why it is recursive, is because we want to preserve the parent-grandparent interleaving
def BuildServiceIdentifiersToChildrenToParents( service_identifiers_to_simple_children_to_parents ):
    
    def AddParents( simple_children_to_parents, children_to_parents, child, parents ):
        
        for parent in parents:
            
            children_to_parents[ child ].append( parent )
            
            if parent in simple_children_to_parents:
                
                grandparents = simple_children_to_parents[ parent ]
                
                AddParents( simple_children_to_parents, children_to_parents, child, grandparents )
                
            
        
    
    service_identifiers_to_children_to_parents = collections.defaultdict( HC.default_dict_list )
    
    for ( service_identifier, simple_children_to_parents ) in service_identifiers_to_simple_children_to_parents.items():
        
        children_to_parents = service_identifiers_to_children_to_parents[ service_identifier ]
        
        for ( child, parents ) in simple_children_to_parents.items(): AddParents( simple_children_to_parents, children_to_parents, child, parents )
        
    
    return service_identifiers_to_children_to_parents
    
class TagParentsManager():
    
    def __init__( self ):
        
        self._tag_service_precedence = HC.app.Read( 'tag_service_precedence' )
        
        self._RefreshParents()
        
        self._lock = threading.Lock()
        
        HC.pubsub.sub( self, 'RefreshParents', 'notify_new_parents' )
        
    
    def _RefreshParents( self ):
        
        service_identifiers_to_statuses_to_pairs = HC.app.Read( 'tag_parents' )
        
        t_s_p = list( self._tag_service_precedence )
        
        service_identifiers_to_pairs_flat = CombineTagParentPairs( t_s_p, service_identifiers_to_statuses_to_pairs )
        
        service_identifiers_to_simple_children_to_parents = BuildServiceIdentifiersToSimpleChildrenToParents( service_identifiers_to_pairs_flat )
        
        self._service_identifiers_to_children_to_parents = BuildServiceIdentifiersToChildrenToParents( service_identifiers_to_simple_children_to_parents )
        
    
    def ExpandPredicates( self, service_identifier, predicates ):
        
        # for now -- we will make an option, later
        service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER
        
        results = []
        
        with self._lock:
            
            for predicate in predicates:
                
                results.append( predicate )
                
                if predicate.GetPredicateType() == HC.PREDICATE_TYPE_TAG:
                    
                    tag = predicate.GetTag()
                    
                    parents = self._service_identifiers_to_children_to_parents[ service_identifier ][ tag ]
                    
                    for parent in parents:
                        
                        parent_predicate = HC.Predicate( HC.PREDICATE_TYPE_PARENT, parent, None )
                        
                        results.append( parent_predicate )
                        
                    
                
            
            return results
            
        
    
    def ExpandTags( self, service_identifier, tags ):
        
        with self._lock:
            
            # for now -- we will make an option, later
            service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER
            
            tags_results = set( tags )
            
            for tag in tags: tags_results.update( self._service_identifiers_to_children_to_parents[ service_identifier ][ tag ] )
            
            return tags_results
            
        
    
    def GetParents( self, service_identifier, tag ):
        
        with self._lock:
            
            # for now -- we will make an option, later
            service_identifier = HC.COMBINED_TAG_SERVICE_IDENTIFIER
            
            return self._service_identifiers_to_children_to_parents[ service_identifier ][ tag ]
            
        
    
    def RefreshParents( self ):
        
        with self._lock: self._RefreshParents()
        
    
def CombineTagSiblingPairs( tag_service_precedence, service_identifiers_to_statuses_to_pairs ):
    
    # first combine the services
    # go from high precedence to low, writing A -> B
    # if A map already exists, don't overwrite
    # if A -> B forms a loop, don't write it
    
    processed_siblings = {}
    current_deleted_pairs = set()
    
    for service_identifier in tag_service_precedence:
        
        statuses_to_pairs = service_identifiers_to_statuses_to_pairs[ service_identifier ]
        
        pairs = statuses_to_pairs[ HC.CURRENT ].union( statuses_to_pairs[ HC.PENDING ] )
        
        pairs.difference_update( current_deleted_pairs )
        
        for ( old, new ) in pairs:
            
            if old == new: continue
            
            if old not in processed_siblings:
                
                next_new = new
                
                we_have_a_loop = False
                
                while next_new in processed_siblings:
                    
                    next_new = processed_siblings[ next_new ]
                    
                    if next_new == old:
                        
                        we_have_a_loop = True
                        
                        break
                        
                    
                
                if not we_have_a_loop: processed_siblings[ old ] = new
                
            
        
        current_deleted_pairs.update( statuses_to_pairs[ HC.DELETED ] )
        
    
    return processed_siblings
    
def CollapseTagSiblingChains( processed_siblings ):
    
    # now to collapse chains
    # A -> B and B -> C goes to A -> C and B -> C
    
    siblings = {}
    
    for ( old_tag, new_tag ) in processed_siblings.items():
        
        # adding A -> B
        
        if new_tag in siblings:
            
            # B -> F already calculated and added, so add A -> F
            
            siblings[ old_tag ] = siblings[ new_tag ]
            
        else:
            
            while new_tag in processed_siblings: new_tag = processed_siblings[ new_tag ] # pursue endpoint F
            
            siblings[ old_tag ] = new_tag
            
        
    
    reverse_lookup = collections.defaultdict( list )
    
    for ( old_tag, new_tag ) in siblings.items(): reverse_lookup[ new_tag ].append( old_tag )
    
    return ( siblings, reverse_lookup )
    
class TagSiblingsManager():
    
    def __init__( self ):
        
        self._tag_service_precedence = HC.app.Read( 'tag_service_precedence' )
        
        # I should offload this to a thread (rather than the gui thread), and have an event to say when it is ready
        # gui requests should pause until it is ready, which should kick in during refreshes, too!
        
        self._RefreshSiblings()
        
        self._lock = threading.Lock()
        
        HC.pubsub.sub( self, 'RefreshSiblings', 'notify_new_siblings' )
        
    
    def _RefreshSiblings( self ):
        
        service_identifiers_to_statuses_to_pairs = HC.app.Read( 'tag_siblings' )
        
        tag_service_precedence = list( self._tag_service_precedence )
        
        processed_siblings = CombineTagSiblingPairs( tag_service_precedence, service_identifiers_to_statuses_to_pairs )
        
        ( self._siblings, self._reverse_lookup ) = CollapseTagSiblingChains( processed_siblings )
        
        HC.pubsub.pub( 'new_siblings_gui' )
        
    
    def GetAutocompleteSiblings( self, half_complete_tag ):
        
        with self._lock:
            
            key_based_matching_values = { self._siblings[ key ] for key in self._siblings.keys() if HC.SearchEntryMatchesTag( half_complete_tag, key, search_siblings = False ) }
            
            value_based_matching_values = { value for value in self._siblings.values() if HC.SearchEntryMatchesTag( half_complete_tag, value, search_siblings = False ) }
            
            matching_values = key_based_matching_values.union( value_based_matching_values )
            
            # all the matching values have a matching sibling somewhere in their network
            # so now fetch the networks
            
            lists_of_matching_keys = [ self._reverse_lookup[ value ] for value in matching_values ]
            
            matching_keys = itertools.chain.from_iterable( lists_of_matching_keys )
            
            matches = matching_values.union( matching_keys )
            
            return matches
            
        
    
    def GetSibling( self, tag ):
        
        with self._lock:
            
            if tag in self._siblings: return self._siblings[ tag ]
            else: return None
            
        
    
    def GetAllSiblings( self, tag ):
        
        with self._lock:
            
            if tag in self._siblings:
                
                new_tag = self._siblings[ tag ]
                
            elif tag in self._reverse_lookup: new_tag = tag
            else: return [ tag ]
            
            all_siblings = list( self._reverse_lookup[ new_tag ] )
            
            all_siblings.append( new_tag )
            
            return all_siblings
            
        
    
    def RefreshSiblings( self ):
        
        with self._lock: self._RefreshSiblings()
        
    
    def CollapseNamespacedTags( self, namespace, tags ):
        
        with self._lock:
            
            results = set()
            
            for tag in tags:
                
                full_tag = namespace + ':' + tag
                
                if full_tag in self._siblings:
                    
                    sibling = self._siblings[ full_tag ]
                    
                    if ':' in sibling: sibling = sibling.split( ':', 1 )[1]
                    
                    results.add( sibling )
                    
                else: results.add( tag )
                
            
            return results
            
        
    
    def CollapsePredicates( self, predicates ):
        
        with self._lock:
            
            results = [ predicate for predicate in predicates if predicate.GetPredicateType() != HC.PREDICATE_TYPE_TAG ]
            
            tag_predicates = [ predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_TAG ]
            
            tags_to_predicates = { predicate.GetTag() : predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_TAG }
            
            tags = tags_to_predicates.keys()
            
            tags_to_include_in_results = set()
            
            for tag in tags:
                
                if tag in self._siblings:
                    
                    old_tag = tag
                    old_predicate = tags_to_predicates[ old_tag ]
                    
                    new_tag = self._siblings[ old_tag ]
                    
                    if new_tag not in tags_to_predicates:
                        
                        ( old_operator, old_tag ) = old_predicate.GetValue()
                        
                        new_predicate = HC.Predicate( HC.PREDICATE_TYPE_TAG, ( old_operator, new_tag ), 0 )
                        
                        tags_to_predicates[ new_tag ] = new_predicate
                        
                        tags_to_include_in_results.add( new_tag )
                        
                    
                    new_predicate = tags_to_predicates[ new_tag ]
                    
                    count = old_predicate.GetCount()
                    
                    new_predicate.AddToCount( count )
                    
                else: tags_to_include_in_results.add( tag )
                
            
            results.extend( [ tags_to_predicates[ tag ] for tag in tags_to_include_in_results ] )
            
            return results
            
        
    
    def CollapseTags( self, tags ):
        
        with self._lock: return { self._siblings[ tag ] if tag in self._siblings else tag for tag in tags }
        
    
    def CollapseTagsToCount( self, tags_to_count ):
        
        with self._lock:
            
            results = collections.Counter()
            
            for ( tag, count ) in tags_to_count.items():
                
                if tag in self._siblings: tag = self._siblings[ tag ]
                
                results[ tag ] += count
                
            
            return results
            
        
    