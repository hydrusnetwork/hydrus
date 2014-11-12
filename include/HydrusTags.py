import collections
import HydrusConstants as HC
import itertools
import os
import threading
import time
import traceback
import wx

# important thing here, and reason why it is recursive, is because we want to preserve the parent-grandparent interleaving
def BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents ):
    
    def AddParents( simple_children_to_parents, children_to_parents, child, parents ):
        
        for parent in parents:
            
            children_to_parents[ child ].append( parent )
            
            if parent in simple_children_to_parents:
                
                grandparents = simple_children_to_parents[ parent ]
                
                AddParents( simple_children_to_parents, children_to_parents, child, grandparents )
                
            
        
    
    service_keys_to_children_to_parents = collections.defaultdict( HC.default_dict_list )
    
    for ( service_key, simple_children_to_parents ) in service_keys_to_simple_children_to_parents.items():
        
        children_to_parents = service_keys_to_children_to_parents[ service_key ]
        
        for ( child, parents ) in simple_children_to_parents.items(): AddParents( simple_children_to_parents, children_to_parents, child, parents )
        
    
    return service_keys_to_children_to_parents
    
def BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat ):
    
    service_keys_to_simple_children_to_parents = collections.defaultdict( HC.default_dict_set )
    
    for ( service_key, pairs ) in service_keys_to_pairs_flat.items():
        
        service_keys_to_simple_children_to_parents[ service_key ] = BuildSimpleChildrenToParents( pairs )
        
    
    return service_keys_to_simple_children_to_parents
    
def BuildSimpleChildrenToParents( pairs ):
    
    simple_children_to_parents = HC.default_dict_set()
    
    for ( child, parent ) in pairs:
        
        if child == parent: continue
        
        if LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ): continue
        
        simple_children_to_parents[ child ].add( parent )
        
    
    return simple_children_to_parents
    
def CensorshipMatch( tag, censorship ):
    
    if ':' in censorship:
        
        if censorship == ':': return ':' in tag # ':' - all namespaced tags
        else: return tag == censorship
        
    else:
        
        if censorship == '': return ':' not in tag # '' - all non namespaced tags
        else: # 'table' - normal tag, or namespaced version of same
            
            if ':' in tag: ( namespace, tag ) = tag.split( ':', 1 )
            
            return tag == censorship
            
        
    
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
    
def CombineTagSiblingPairs( service_keys_to_statuses_to_pairs ):
    
    # first combine the services
    # if A map already exists, don't overwrite
    # if A -> B forms a loop, don't write it
    
    processed_siblings = {}
    current_deleted_pairs = set()
    
    for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
        
        pairs = statuses_to_pairs[ HC.CURRENT ].union( statuses_to_pairs[ HC.PENDING ] )
        
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
                
            
        
    
    return processed_siblings
    
def FilterNamespaces( tags, namespaces ):
    
    processed_tags = collections.defaultdict( set )
    
    for tag in tags:
        
        if ':' in tag:
            
            ( namespace, subtag ) = tag.split( ':', 1 )
            
            processed_tags[ namespace ].add( tag )
            
        else: processed_tags[ '' ].add( tag )
        
    
    result = set()
    
    for namespace in namespaces:
        
        if namespace in ( '', None ): result.update( processed_tags[ '' ] )
        
        result.update( processed_tags[ namespace ] )
        
    
    return result
    
def LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
    
    potential_loop_paths = { parent }
    
    while len( potential_loop_paths.intersection( simple_children_to_parents.keys() ) ) > 0:
        
        new_potential_loop_paths = set()
        
        for potential_loop_path in potential_loop_paths.intersection( simple_children_to_parents.keys() ):
            
            new_potential_loop_paths.update( simple_children_to_parents[ potential_loop_path ] )
            
        
        potential_loop_paths = new_potential_loop_paths
        
        if child in potential_loop_paths: return True
        
    
    return False
    
def MergeTagsManagers( tags_managers ):
    
    def CurrentAndPendingFilter( items ):
        
        for ( service_key, statuses_to_tags ) in items:
            
            filtered = { status : tags for ( status, tags ) in statuses_to_tags.items() if status in ( HC.CURRENT, HC.PENDING ) }
            
            yield ( service_key, filtered )
            
        
    
    # [[( service_key, statuses_to_tags )]]
    s_k_s_t_t_tupled = ( CurrentAndPendingFilter( tags_manager.GetServiceKeysToStatusesToTags().items() ) for tags_manager in tags_managers )
    
    # [(service_key, statuses_to_tags)]
    flattened_s_k_s_t_t = itertools.chain.from_iterable( s_k_s_t_t_tupled )
    
    # service_key : [ statuses_to_tags ]
    s_k_s_t_t_dict = HC.BuildKeyToListDict( flattened_s_k_s_t_t )
    
    # now let's merge so we have service_key : statuses_to_tags
    
    merged_service_keys_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
    
    for ( service_key, several_statuses_to_tags ) in s_k_s_t_t_dict.items():
        
        # [[( status, tags )]]
        s_t_t_tupled = ( s_t_t.items() for s_t_t in several_statuses_to_tags )
        
        # [( status, tags )]
        flattened_s_t_t = itertools.chain.from_iterable( s_t_t_tupled )
        
        statuses_to_tags = HC.default_dict_set()
        
        for ( status, tags ) in flattened_s_t_t: statuses_to_tags[ status ].update( tags )
        
        merged_service_keys_to_statuses_to_tags[ service_key ] = statuses_to_tags
        
    
    return TagsManagerSimple( merged_service_keys_to_statuses_to_tags )
    
class TagsManagerSimple( object ):
    
    def __init__( self, service_keys_to_statuses_to_tags ):
        
        tag_censorship_manager = HC.app.GetManager( 'tag_censorship' )
        
        service_keys_to_statuses_to_tags = tag_censorship_manager.FilterServiceKeysToStatusesToTags( service_keys_to_statuses_to_tags )
        
        self._service_keys_to_statuses_to_tags = service_keys_to_statuses_to_tags
        
        self._combined_namespaces_cache = None
        
    
    def GetCombinedNamespaces( self, namespaces ):
        
        if self._combined_namespaces_cache is None:
    
            combined_statuses_to_tags = self._service_keys_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_KEY ]
            
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
        
    
    def GetComparableNamespaceSlice( self, namespaces, collapse = True ):
        
        combined_statuses_to_tags = self._service_keys_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_KEY ]
        
        combined_current = combined_statuses_to_tags[ HC.CURRENT ]
        combined_pending = combined_statuses_to_tags[ HC.PENDING ]
        
        combined = combined_current.union( combined_pending )
        
        siblings_manager = HC.app.GetManager( 'tag_siblings' )
        
        slice = []
        
        for namespace in namespaces:
            
            tags = [ tag for tag in combined if tag.startswith( namespace + ':' ) ]
            
            if collapse:
            
                tags = list( siblings_manager.CollapseTags( tags ) )
                
            
            tags = [ tag.split( ':', 1 )[1] for tag in tags ]
            
            def process_tag( t ):
                
                try: return int( t )
                except: return t
                
            
            tags = [ process_tag( tag ) for tag in tags ]
            
            tags.sort()
            
            tags = tuple( tags )
            
            slice.append( tags )
            
        
        return tuple( slice )
        
    
    def GetNamespaceSlice( self, namespaces, collapse = True ):
        
        combined_statuses_to_tags = self._service_keys_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_KEY ]
        
        combined_current = combined_statuses_to_tags[ HC.CURRENT ]
        combined_pending = combined_statuses_to_tags[ HC.PENDING ]
        
        slice = { tag for tag in combined_current.union( combined_pending ) if True in ( tag.startswith( namespace + ':' ) for namespace in namespaces ) }
        
        if collapse:
            
            siblings_manager = HC.app.GetManager( 'tag_siblings' )
            
            slice = siblings_manager.CollapseTags( slice )
            
        
        slice = frozenset( slice )
        
        return slice
        
    
class TagsManager( TagsManagerSimple ):
    
    def __init__( self, service_keys_to_statuses_to_tags ):
        
        TagsManagerSimple.__init__( self, service_keys_to_statuses_to_tags )
        
        self._RecalcCombined()
        
    
    def _RecalcCombined( self ):
        
        combined_statuses_to_tags = collections.defaultdict( set )
        
        for ( service_key, statuses_to_tags ) in self._service_keys_to_statuses_to_tags.items():
            
            if service_key == HC.COMBINED_TAG_SERVICE_KEY: continue
            
            combined_statuses_to_tags[ HC.CURRENT ].update( statuses_to_tags[ HC.CURRENT ] )
            combined_statuses_to_tags[ HC.PENDING ].update( statuses_to_tags[ HC.PENDING ] )
            
        
        self._service_keys_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_KEY ] = combined_statuses_to_tags
        
        self._combined_namespaces_cache = None
        
    
    def DeletePending( self, service_key ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        if len( statuses_to_tags[ HC.PENDING ] ) + len( statuses_to_tags[ HC.PETITIONED ] ) > 0:
            
            statuses_to_tags[ HC.PENDING ] = set()
            statuses_to_tags[ HC.PETITIONED ] = set()
            
            self._RecalcCombined()
            
        
    
    def GetCurrent( self, service_key = HC.COMBINED_TAG_SERVICE_KEY ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        return set( statuses_to_tags[ HC.CURRENT ] )
        
    
    def GetDeleted( self, service_key = HC.COMBINED_TAG_SERVICE_KEY ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        return set( statuses_to_tags[ HC.DELETED ] )
        
    
    def GetNumTags( self, service_key, include_current_tags = True, include_pending_tags = False ):
        
        num_tags = 0
        
        statuses_to_tags = self.GetStatusesToTags( service_key )
        
        if include_current_tags: num_tags += len( statuses_to_tags[ HC.CURRENT ] )
        if include_pending_tags: num_tags += len( statuses_to_tags[ HC.PENDING ] )
        
        return num_tags
        
    
    def GetPending( self, service_key = HC.COMBINED_TAG_SERVICE_KEY ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        return set( statuses_to_tags[ HC.PENDING ] )
        
    
    def GetPetitioned( self, service_key = HC.COMBINED_TAG_SERVICE_KEY ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
        return set( statuses_to_tags[ HC.PETITIONED ] )
        
    
    def GetServiceKeysToStatusesToTags( self ): return self._service_keys_to_statuses_to_tags
    
    def GetStatusesToTags( self, service_key ): return self._service_keys_to_statuses_to_tags[ service_key ]
    
    def HasTag( self, tag ):
        
        combined_statuses_to_tags = self._service_keys_to_statuses_to_tags[ HC.COMBINED_TAG_SERVICE_KEY ]
        
        return tag in combined_statuses_to_tags[ HC.CURRENT ] or tag in combined_statuses_to_tags[ HC.PENDING ]
        
    
    def ProcessContentUpdate( self, service_key, content_update ):
        
        statuses_to_tags = self._service_keys_to_statuses_to_tags[ service_key ]
        
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
        
    
    def ResetService( self, service_key ):
        
        if service_key in self._service_keys_to_statuses_to_tags:
            
            del self._service_keys_to_statuses_to_tags[ service_key ]
            
            self._RecalcCombined()
            
        
    
class TagCensorshipManager( object ):
    
    def __init__( self ):
        
        self.RefreshData()
        
        HC.pubsub.sub( self, 'RefreshData', 'notify_new_tag_censorship' )
        
    
    def GetInfo( self, service_key ):
        
        if service_key in self._service_keys_to_predicates: return self._service_keys_to_predicates[ service_key ]
        else: return ( True, set() )
        
    
    def RefreshData( self ):
        
        info = HC.app.Read( 'tag_censorship' )
        
        self._service_keys_to_predicates = {}
        
        for ( service_key, blacklist, censorships ) in info:
            
            tag_matches = lambda tag: True in ( CensorshipMatch( tag, censorship ) for censorship in censorships )
            
            if blacklist: predicate = lambda tag: not tag_matches( tag )
            else: predicate = tag_matches
            
            self._service_keys_to_predicates[ service_key ] = predicate
            
        
    
    def FilterServiceKeysToStatusesToTags( self, service_keys_to_statuses_to_tags ):
        
        filtered_service_keys_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
        
        for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
            
            for service_key_lookup in ( HC.COMBINED_TAG_SERVICE_KEY, service_key ):
                
                if service_key_lookup in self._service_keys_to_predicates:
                    
                    combined_predicate = self._service_keys_to_predicates[ service_key_lookup ]
                    
                    tuples = statuses_to_tags.items()
                    
                    for ( status, tags ) in tuples:
                        
                        tags = { tag for tag in tags if combined_predicate( tag ) }
                        
                        statuses_to_tags[ status ] = tags
                        
                    
                
            
            filtered_service_keys_to_statuses_to_tags[ service_key ] = statuses_to_tags
            
        
        return filtered_service_keys_to_statuses_to_tags
        
    
    def FilterTags( self, service_key, tags ):
        
        for service_key in ( HC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key in self._service_keys_to_predicates:
                
                predicate = self._service_keys_to_predicates[ service_key ]
                
                tags = { tag for tag in tags if predicate( tag ) }
                
            
        
        return tags
        
    
class TagParentsManager( object ):
    
    def __init__( self ):
        
        self._RefreshParents()
        
        self._lock = threading.Lock()
        
        HC.pubsub.sub( self, 'RefreshParents', 'notify_new_parents' )
        
    
    def _RefreshParents( self ):
        
        service_keys_to_statuses_to_pairs = HC.app.Read( 'tag_parents' )
        
        # first collapse siblings
        
        sibling_manager = HC.app.GetManager( 'tag_siblings' )
        
        collapsed_service_keys_to_statuses_to_pairs = collections.defaultdict( HC.default_dict_set )
        
        for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
            
            if service_key == HC.COMBINED_TAG_SERVICE_KEY: continue
            
            for ( status, pairs ) in statuses_to_pairs.items():
                
                pairs = sibling_manager.CollapsePairs( pairs )
                
                collapsed_service_keys_to_statuses_to_pairs[ service_key ][ status ] = pairs
                
            
        
        # now collapse current and pending
        
        service_keys_to_pairs_flat = HC.default_dict_set()
        
        for ( service_key, statuses_to_pairs ) in collapsed_service_keys_to_statuses_to_pairs.items():
            
            pairs_flat = statuses_to_pairs[ HC.CURRENT ].union( statuses_to_pairs[ HC.PENDING ] )
            
            service_keys_to_pairs_flat[ service_key ] = pairs_flat
            
        
        # now create the combined tag service
        
        combined_pairs_flat = set()
        
        for pairs_flat in service_keys_to_pairs_flat.values():
            
            combined_pairs_flat.update( pairs_flat )
            
        
        service_keys_to_pairs_flat[ HC.COMBINED_TAG_SERVICE_KEY ] = combined_pairs_flat
        
        #
        
        service_keys_to_simple_children_to_parents = BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat )
        
        self._service_keys_to_children_to_parents = BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents )
        
    
    def ExpandPredicates( self, service_key, predicates ):
        
        # for now -- we will make an option, later
        service_key = HC.COMBINED_TAG_SERVICE_KEY
        
        results = []
        
        with self._lock:
            
            for predicate in predicates:
                
                results.append( predicate )
                
                if predicate.GetPredicateType() == HC.PREDICATE_TYPE_TAG:
                    
                    tag = predicate.GetTag()
                    
                    parents = self._service_keys_to_children_to_parents[ service_key ][ tag ]
                    
                    for parent in parents:
                        
                        parent_predicate = HC.Predicate( HC.PREDICATE_TYPE_PARENT, parent )
                        
                        results.append( parent_predicate )
                        
                    
                
            
            return results
            
        
    
    def ExpandTags( self, service_key, tags ):
        
        with self._lock:
            
            # for now -- we will make an option, later
            service_key = HC.COMBINED_TAG_SERVICE_KEY
            
            tags_results = set( tags )
            
            for tag in tags: tags_results.update( self._service_keys_to_children_to_parents[ service_key ][ tag ] )
            
            return tags_results
            
        
    
    def GetParents( self, service_key, tag ):
        
        with self._lock:
            
            # for now -- we will make an option, later
            service_key = HC.COMBINED_TAG_SERVICE_KEY
            
            return self._service_keys_to_children_to_parents[ service_key ][ tag ]
            
        
    
    def RefreshParents( self ):
        
        with self._lock: self._RefreshParents()
        
    
class TagSiblingsManager( object ):
    
    def __init__( self ):
        
        self._RefreshSiblings()
        
        self._lock = threading.Lock()
        
        HC.pubsub.sub( self, 'RefreshSiblings', 'notify_new_siblings' )
        
    
    def _RefreshSiblings( self ):
        
        service_keys_to_statuses_to_pairs = HC.app.Read( 'tag_siblings' )
        
        processed_siblings = CombineTagSiblingPairs( service_keys_to_statuses_to_pairs )
        
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
                        
                        new_predicate = HC.Predicate( HC.PREDICATE_TYPE_TAG, ( old_operator, new_tag ) )
                        
                        tags_to_predicates[ new_tag ] = new_predicate
                        
                        tags_to_include_in_results.add( new_tag )
                        
                    
                    new_predicate = tags_to_predicates[ new_tag ]
                    
                    current_count = old_predicate.GetCount( HC.CURRENT )
                    pending_count = old_predicate.GetCount( HC.PENDING )
                    
                    new_predicate.AddToCount( HC.CURRENT, current_count )
                    new_predicate.AddToCount( HC.PENDING, pending_count )
                    
                else: tags_to_include_in_results.add( tag )
                
            
            results.extend( [ tags_to_predicates[ tag ] for tag in tags_to_include_in_results ] )
            
            return results
            
        
    
    def CollapsePairs( self, pairs ):
        
        with self._lock:
            
            result = set()
            
            for ( a, b ) in pairs:
                
                if a in self._siblings: a = self._siblings[ a ]
                if b in self._siblings: b = self._siblings[ b ]
                
                result.add( ( a, b ) )
                
            
            return result
            
        
    
    def CollapseTags( self, tags ):
        
        with self._lock: return { self._siblings[ tag ] if tag in self._siblings else tag for tag in tags }
        
    
    def CollapseTagsToCount( self, tags_to_count ):
        
        with self._lock:
            
            results = collections.Counter()
            
            for ( tag, count ) in tags_to_count.items():
                
                if tag in self._siblings: tag = self._siblings[ tag ]
                
                results[ tag ] += count
                
            
            return results
            
        
    