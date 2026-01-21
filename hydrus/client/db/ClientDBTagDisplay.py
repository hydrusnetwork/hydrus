import collections
import collections.abc
import itertools
import sqlite3
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBTagParents
from hydrus.client.db import ClientDBTagSiblings
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

class ClientDBTagDisplay( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_tags: ClientDBMaster.ClientDBMasterTags,
        modules_tags_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalTags,
        modules_tag_siblings: ClientDBTagSiblings.ClientDBTagSiblings,
        modules_tag_parents: ClientDBTagParents.ClientDBTagParents
    ):
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_services = modules_services
        self.modules_tags = modules_tags
        self.modules_tags_local_cache = modules_tags_local_cache
        self.modules_tag_parents = modules_tag_parents
        self.modules_tag_siblings = modules_tag_siblings
        
        super().__init__( 'client tag display', cursor )
        
    
    def FilterChained( self, display_type, tag_service_id, tag_ids ) -> set[ int ]:
        
        # we are not passing ideal_tag_ids here, but that's ok, we are testing sibling chains in one second
        parents_chained_tag_ids = self.modules_tag_parents.FilterChained( display_type, tag_service_id, tag_ids )
        
        unknown_tag_ids = set( tag_ids ).difference( parents_chained_tag_ids )
        
        sibling_chained_tag_ids = self.modules_tag_siblings.FilterChained( display_type, tag_service_id, unknown_tag_ids )
        
        chained_tag_ids = set( parents_chained_tag_ids ).union( sibling_chained_tag_ids )
        
        return chained_tag_ids
        
    
    def GeneratePredicatesFromTagIdsAndCounts( self, tag_display_type: int, display_tag_service_id: int, tag_ids_to_full_counts, job_status = None ):
        
        inclusive = True
        
        tag_ids = set( tag_ids_to_full_counts.keys() )
        
        predicates = []
        
        if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE:
            
            if display_tag_service_id != self.modules_services.combined_tag_service_id:
                
                tag_ids_to_ideal_tag_ids = self.modules_tag_siblings.GetTagIdsToIdealTagIds( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, display_tag_service_id, tag_ids )
                
                tag_ids_that_are_sibling_chained = self.modules_tag_siblings.FilterChained( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, display_tag_service_id, tag_ids )
                
                tag_ids_to_ideal_tag_ids_for_siblings = { tag_id : ideal_tag_id for ( tag_id, ideal_tag_id ) in tag_ids_to_ideal_tag_ids.items() if tag_id in tag_ids_that_are_sibling_chained }
                
                ideal_tag_ids_to_sibling_chain_tag_ids = self.modules_tag_siblings.GetIdealTagIdsToChains( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, display_tag_service_id, set( tag_ids_to_ideal_tag_ids_for_siblings.values() ) )
                
                #
                
                ideal_tag_ids = set( tag_ids_to_ideal_tag_ids.values() )
                
                ideal_tag_ids_that_are_parent_chained = self.modules_tag_parents.FilterChained( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, display_tag_service_id, ideal_tag_ids )
                
                tag_ids_to_ideal_tag_ids_for_parents = { tag_id : ideal_tag_id for ( tag_id, ideal_tag_id ) in tag_ids_to_ideal_tag_ids.items() if ideal_tag_id in ideal_tag_ids_that_are_parent_chained }
                
                ideal_tag_ids_to_ancestor_tag_ids = self.modules_tag_parents.GetTagsToAncestors( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, display_tag_service_id, set( tag_ids_to_ideal_tag_ids_for_parents.values() ) )
                
            else:
                
                # shouldn't ever happen with storage display
                
                tag_ids_to_ideal_tag_ids_for_siblings = {}
                tag_ids_to_ideal_tag_ids_for_parents = {}
                
                ideal_tag_ids_to_sibling_chain_tag_ids = {}
                
                ideal_tag_ids_to_ancestor_tag_ids = {}
                
            
            tag_ids_we_want_to_look_up = set( tag_ids )
            tag_ids_we_want_to_look_up.update( itertools.chain.from_iterable( ideal_tag_ids_to_sibling_chain_tag_ids.values() ) )
            tag_ids_we_want_to_look_up.update( itertools.chain.from_iterable( ideal_tag_ids_to_ancestor_tag_ids.values() ) )
            
            if job_status is not None and job_status.IsCancelled():
                
                return []
                
            
            tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = tag_ids_we_want_to_look_up )
            
            if job_status is not None and job_status.IsCancelled():
                
                return []
                
            
            ideal_tag_ids_to_chain_tags = { ideal_tag_id : { tag_ids_to_tags[ chain_tag_id ] for chain_tag_id in chain_tag_ids } for ( ideal_tag_id, chain_tag_ids ) in ideal_tag_ids_to_sibling_chain_tag_ids.items() }
            
            ideal_tag_ids_to_ancestor_tags = { ideal_tag_id : { tag_ids_to_tags[ ancestor_tag_id ] for ancestor_tag_id in ancestor_tag_ids } for ( ideal_tag_id, ancestor_tag_ids ) in ideal_tag_ids_to_ancestor_tag_ids.items() }
            
            for ( tag_id, ( min_current_count, max_current_count, min_pending_count, max_pending_count ) ) in tag_ids_to_full_counts.items():
                
                tag = tag_ids_to_tags[ tag_id ]
                
                predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, value = tag, inclusive = inclusive, count = ClientSearchPredicate.PredicateCount( min_current_count, min_pending_count, max_current_count, max_pending_count ) )
                
                if tag_id in tag_ids_to_ideal_tag_ids_for_siblings:
                    
                    ideal_tag_id = tag_ids_to_ideal_tag_ids_for_siblings[ tag_id ]
                    
                    if ideal_tag_id != tag_id:
                        
                        predicate.SetIdealSibling( tag_ids_to_tags[ ideal_tag_id ] )
                        
                    
                    predicate.SetKnownSiblings( ideal_tag_ids_to_chain_tags[ ideal_tag_id ] )
                    
                
                if tag_id in tag_ids_to_ideal_tag_ids_for_parents:
                    
                    ideal_tag_id = tag_ids_to_ideal_tag_ids_for_parents[ tag_id ]
                    
                    parents = ideal_tag_ids_to_ancestor_tags[ ideal_tag_id ]
                    
                    if len( parents ) > 0:
                        
                        predicate.SetKnownParents( parents )
                        
                    
                
                predicates.append( predicate )
                
            
        elif tag_display_type == ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL:
            
            tag_ids_to_known_chain_tag_ids = collections.defaultdict( set )
            
            if display_tag_service_id == self.modules_services.combined_tag_service_id:
                
                search_tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
                
            else:
                
                search_tag_service_ids = ( display_tag_service_id, )
                
            
            for search_tag_service_id in search_tag_service_ids:
                
                tag_ids_that_are_sibling_chained = self.modules_tag_siblings.FilterChained( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, search_tag_service_id, tag_ids )
                
                tag_ids_to_ideal_tag_ids_for_siblings = self.modules_tag_siblings.GetTagIdsToIdealTagIds( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, search_tag_service_id, tag_ids_that_are_sibling_chained )
                
                ideal_tag_ids = set( tag_ids_to_ideal_tag_ids_for_siblings.values() )
                
                ideal_tag_ids_to_sibling_chain_tag_ids = self.modules_tag_siblings.GetIdealTagIdsToChains( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, search_tag_service_id, ideal_tag_ids )
                
                for ( tag_id, ideal_tag_id ) in tag_ids_to_ideal_tag_ids_for_siblings.items():
                    
                    tag_ids_to_known_chain_tag_ids[ tag_id ].update( ideal_tag_ids_to_sibling_chain_tag_ids[ ideal_tag_id ] )
                    
                
            
            tag_ids_we_want_to_look_up = set( tag_ids ).union( itertools.chain.from_iterable( tag_ids_to_known_chain_tag_ids.values() ) )
            
            if job_status is not None and job_status.IsCancelled():
                
                return []
                
            
            tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = tag_ids_we_want_to_look_up )
            
            if job_status is not None and job_status.IsCancelled():
                
                return []
                
            
            for ( tag_id, ( min_current_count, max_current_count, min_pending_count, max_pending_count ) ) in tag_ids_to_full_counts.items():
                
                tag = tag_ids_to_tags[ tag_id ]
                
                predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, value = tag, inclusive = inclusive, count = ClientSearchPredicate.PredicateCount( min_current_count, min_pending_count, max_current_count, max_pending_count ) )
                
                if tag_id in tag_ids_to_known_chain_tag_ids:
                    
                    chain_tags = { tag_ids_to_tags[ chain_tag_id ] for chain_tag_id in tag_ids_to_known_chain_tag_ids[ tag_id ] }
                    
                    predicate.SetKnownSiblings( chain_tags )
                    
                
                predicates.append( predicate )
                
            
        
        return predicates
        
    
    def GetApplication( self ):
        
        service_keys_to_sibling_applicable_service_keys = self.modules_tag_siblings.GetApplication()
        service_keys_to_parent_applicable_service_keys = self.modules_tag_parents.GetApplication()
        
        return ( service_keys_to_sibling_applicable_service_keys, service_keys_to_parent_applicable_service_keys )
        
    
    def GetApplicationStatus( self, service_id ):
        
        ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove ) = self.modules_tag_siblings.GetApplicationStatus( service_id )
        ( actual_parent_rows, ideal_parent_rows, parent_rows_to_add, parent_rows_to_remove ) = self.modules_tag_parents.GetApplicationStatus( service_id )
        
        num_actual_rows = len( actual_sibling_rows ) + len( actual_parent_rows )
        num_ideal_rows = len( ideal_sibling_rows ) + len( ideal_parent_rows )
        
        return ( sibling_rows_to_add, sibling_rows_to_remove, parent_rows_to_add, parent_rows_to_remove, num_actual_rows, num_ideal_rows )
        
    
    def GetApplicableServiceIds( self, tag_service_id ) -> set[ int ]:
        
        return set( self.modules_tag_siblings.GetApplicableServiceIds( tag_service_id ) ).union( self.modules_tag_parents.GetApplicableServiceIds( tag_service_id ) )
        
    
    def GetChainsMembers( self, display_type, tag_service_id, tag_ids ) -> set[ int ]:
        
        # all parent definitions are sibling collapsed, so are terminus of their sibling chains
        # so get all of the parent chain, then get all chains that point to those
        
        ideal_tag_ids = self.modules_tag_siblings.GetIdealTagIds( display_type, tag_service_id, tag_ids )
        
        parent_chain_members = self.modules_tag_parents.GetChainsMembers( display_type, tag_service_id, ideal_tag_ids )
        
        sibling_chain_members = self.modules_tag_siblings.GetChainsMembersFromIdeals( display_type, tag_service_id, parent_chain_members )
        
        return sibling_chain_members.union( parent_chain_members )
        
        # ok revisit this sometime I guess but it needs work
        '''
        with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
            
            with self._MakeTemporaryIntegerTable( [], 'ideal_tag_id' ) as temp_ideal_tag_ids_table_name:
                
                self.modules_tag_siblings.GetIdealTagIdsIntoTable( display_type, tag_service_id, temp_tag_ids_table_name, temp_ideal_tag_ids_table_name )
                
                with self._MakeTemporaryIntegerTable( [], 'ideal_tag_id' ) as temp_parent_chain_members_table_name:
                    
                    # this is actually not implemented LMAO
                    self.modules_tag_parents.GetChainsMembersTables( display_type, tag_service_id, temp_ideal_tag_ids_table_name, temp_parent_chain_members_table_name, 'ideal_tag_id' )
                    
                    with self._MakeTemporaryIntegerTable( [], 'tag_id' ) as temp_chain_members_table_name:
                        
                        self.modules_tag_siblings.GetChainsMembersFromIdealsTables( display_type, tag_service_id, temp_parent_chain_members_table_name, temp_chain_members_table_name )
                        
                        return self._STS( self._Execute( 'SELECT tag_id FROM {};'.format( temp_chain_members_table_name ) ) )
                        
                    
                
            
        '''
    
    def GetDescendantsForTags( self, service_key, tags ):
        
        if service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            tag_services = self.modules_services.GetServices( HC.REAL_TAG_SERVICES )
            
            search_service_keys = [ tag_service.GetServiceKey() for tag_service in tag_services ]
            
        else:
            
            search_service_keys = [ service_key ]
            
        
        tags_to_descendants = collections.defaultdict( set )
        
        for service_key in search_service_keys:
            
            tag_service_id = self.modules_services.GetServiceId( service_key )
            
            existing_tags = { tag for tag in tags if self.modules_tags.TagExists( tag ) }
            
            existing_tag_ids_to_tags = self.modules_tags.GetTagIdsToTags( tags = existing_tags )
            
            existing_tag_ids = set( existing_tag_ids_to_tags.keys() )
            
            tag_ids_to_ideal_tag_ids = self.modules_tag_siblings.GetTagIdsToIdealTagIds( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, existing_tag_ids )
            
            ideal_tag_ids = set( tag_ids_to_ideal_tag_ids.values() )
            
            ideal_tag_ids_to_descendant_tag_ids = self.modules_tag_parents.GetTagsToDescendants( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, ideal_tag_ids )
            
            all_tag_ids = set()
            
            all_tag_ids.update( itertools.chain.from_iterable( ideal_tag_ids_to_descendant_tag_ids.values() ) )
            
            tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = all_tag_ids )
            
            for ( tag_id, tag ) in existing_tag_ids_to_tags.items():
                
                ideal_tag_id = tag_ids_to_ideal_tag_ids[ tag_id ]
                descendant_tag_ids = ideal_tag_ids_to_descendant_tag_ids[ ideal_tag_id ]
                descendants = { tag_ids_to_tags[ descendant_tag_id ] for descendant_tag_id in descendant_tag_ids }
                
                tags_to_descendants[ tag ].update( descendants )
                
            
        
        return tags_to_descendants
        
    
    def GetImpliedBy( self, display_type, tag_service_id, tag_id ) -> set[ int ]:
        
        ideal_tag_id = self.modules_tag_siblings.GetIdealTagId( display_type, tag_service_id, tag_id )
        
        if ideal_tag_id == tag_id:
            
            # this tag exists in display
            # it is also implied by any descendant
            # and any of its or those descendants' siblings
            
            # these are all ideal siblings
            self_and_descendant_ids = { tag_id }.union( self.modules_tag_parents.GetDescendants( display_type, tag_service_id, ideal_tag_id ) )
            
            implication_ids = self.modules_tag_siblings.GetChainsMembersFromIdeals( display_type, tag_service_id, self_and_descendant_ids )
            
        else:
            
            # this tag does not exist in display
            
            implication_ids = set()
            
        
        return implication_ids
        
    
    def GetImplies( self, display_type, tag_service_id, tag_id ) -> set[ int ]:
        
        # a tag implies its ideal sibling and any ancestors
        
        ideal_tag_id = self.modules_tag_siblings.GetIdealTagId( display_type, tag_service_id, tag_id )
        
        implies = { ideal_tag_id }
        
        implies.update( self.modules_tag_parents.GetAncestors( display_type, tag_service_id, ideal_tag_id ) )
        
        return implies
        
    
    def GetInterestedServiceIds( self, tag_service_id ) -> set[ int ]:
        
        return set( self.modules_tag_siblings.GetInterestedServiceIds( tag_service_id ) ).union( self.modules_tag_parents.GetInterestedServiceIds( tag_service_id ) )
        
    
    def GetMediaPredicates( self, tag_context: ClientSearchTagContext.TagContext, tags_to_counts, job_status = None ):
        
        if HG.autocomplete_delay_mode:
            
            time_to_stop = HydrusTime.GetNowFloat() + 3.0
            
            while not HydrusTime.TimeHasPassedFloat( time_to_stop ):
                
                time.sleep( 0.1 )
                
                if job_status.IsCancelled():
                    
                    return []
                    
                
            
        
        display_tag_service_id = self.modules_services.GetServiceId( tag_context.display_service_key )
        
        max_current_count = None
        max_pending_count = None
        
        tag_ids_to_full_counts = {}
        
        showed_bad_tag_error = False
        
        for ( i, ( tag, ( current_count, pending_count ) ) ) in enumerate( tags_to_counts.items() ):
            
            try:
                
                tag_id = self.modules_tags.GetTagId( tag )
                
            except HydrusExceptions.TagSizeException:
                
                if not showed_bad_tag_error:
                    
                    showed_bad_tag_error = True
                    
                    HydrusData.ShowText( 'Hey, you seem to have an invalid tag in view right now! Please run the \'fix invalid tags\' routine under the \'database\' menu asap!' )
                    
                
                continue
                
            
            tag_ids_to_full_counts[ tag_id ] = ( current_count, max_current_count, pending_count, max_pending_count )
            
            if i % 100 == 0:
                
                if job_status is not None and job_status.IsCancelled():
                    
                    return []
                    
                
            
        
        if job_status is not None and job_status.IsCancelled():
            
            return []
            
        
        predicates = self.GeneratePredicatesFromTagIdsAndCounts( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, display_tag_service_id, tag_ids_to_full_counts, job_status = job_status )
        
        return predicates
        
    
    def GetSiblingsAndParentsForTags( self, tag_display_type: int, tags: collections.abc.Collection[ str ] ):
        
        tag_services = self.modules_services.GetServices( HC.REAL_TAG_SERVICES )
        
        service_keys = [ tag_service.GetServiceKey() for tag_service in tag_services ]
        
        tags_to_service_keys_to_siblings_and_parents = {}
        
        for tag in tags:
            
            sibling_chain_members = { tag }
            ideal_tag = tag
            descendants = set()
            ancestors = set()
            
            tags_to_service_keys_to_siblings_and_parents[ tag ] = { service_key : ( sibling_chain_members, ideal_tag, descendants, ancestors ) for service_key in service_keys }
            
        
        for service_key in service_keys:
            
            tag_service_id = self.modules_services.GetServiceId( service_key )
            
            existing_tags = { tag for tag in tags if self.modules_tags.TagExists( tag ) }
            
            existing_tag_ids_to_tags = self.modules_tags.GetTagIdsToTags( tags = existing_tags )
            
            existing_tag_ids = set( existing_tag_ids_to_tags.keys() )
            
            tag_ids_to_ideal_tag_ids = self.modules_tag_siblings.GetTagIdsToIdealTagIds( tag_display_type, tag_service_id, existing_tag_ids )
            
            ideal_tag_ids = set( tag_ids_to_ideal_tag_ids.values() )
            
            ideal_tag_ids_to_sibling_chain_ids = self.modules_tag_siblings.GetIdealTagIdsToChains( tag_display_type, tag_service_id, ideal_tag_ids )
            
            ideal_tag_ids_to_descendant_tag_ids = self.modules_tag_parents.GetTagsToDescendants( tag_display_type, tag_service_id, ideal_tag_ids )
            ideal_tag_ids_to_ancestor_tag_ids = self.modules_tag_parents.GetTagsToAncestors( tag_display_type, tag_service_id, ideal_tag_ids )
            
            all_tag_ids = set()
            
            all_tag_ids.update( ideal_tag_ids_to_sibling_chain_ids.keys() )
            all_tag_ids.update( itertools.chain.from_iterable( ideal_tag_ids_to_sibling_chain_ids.values() ) )
            all_tag_ids.update( itertools.chain.from_iterable( ideal_tag_ids_to_descendant_tag_ids.values() ) )
            all_tag_ids.update( itertools.chain.from_iterable( ideal_tag_ids_to_ancestor_tag_ids.values() ) )
            
            tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = all_tag_ids )
            
            for ( tag_id, tag ) in existing_tag_ids_to_tags.items():
                
                ideal_tag_id = tag_ids_to_ideal_tag_ids[ tag_id ]
                sibling_chain_ids = ideal_tag_ids_to_sibling_chain_ids[ ideal_tag_id ]
                descendant_tag_ids = ideal_tag_ids_to_descendant_tag_ids[ ideal_tag_id ]
                ancestor_tag_ids = ideal_tag_ids_to_ancestor_tag_ids[ ideal_tag_id ]
                
                ideal_tag = tag_ids_to_tags[ ideal_tag_id ]
                sibling_chain_members = { tag_ids_to_tags[ sibling_chain_id ] for sibling_chain_id in sibling_chain_ids }
                descendants = { tag_ids_to_tags[ descendant_tag_id ] for descendant_tag_id in descendant_tag_ids }
                ancestors = { tag_ids_to_tags[ ancestor_tag_id ] for ancestor_tag_id in ancestor_tag_ids }
                
                tags_to_service_keys_to_siblings_and_parents[ tag ][ service_key ] = ( sibling_chain_members, ideal_tag, descendants, ancestors )
                
            
        
        return tags_to_service_keys_to_siblings_and_parents
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        return []
        
    
    def GetTagsToImpliedBy( self, display_type, tag_service_id, tag_ids, tags_are_ideal = False ):
        
        tag_ids_to_implied_by = collections.defaultdict( set )
        
        if tags_are_ideal:
            
            tag_ids_that_exist_in_display = set( tag_ids )
            
        else:
            
            tag_ids_to_ideals = self.modules_tag_siblings.GetTagIdsToIdealTagIds( display_type, tag_service_id, tag_ids )
            
            tag_ids_that_exist_in_display = set()
            
            for ( tag_id, ideal_tag_id ) in tag_ids_to_ideals.items():
                
                if tag_id == ideal_tag_id:
                    
                    tag_ids_that_exist_in_display.add( ideal_tag_id )
                    
                else:
                    
                    # this tag does not exist in display
                    
                    tag_ids_to_implied_by[ tag_id ] = set()
                    
                
            
        
        # tags are implied by descendants, and their siblings
        
        tag_ids_to_descendants = self.modules_tag_parents.GetTagsToDescendants( display_type, tag_service_id, tag_ids_that_exist_in_display )
        
        all_tags_and_descendants = set( tag_ids_that_exist_in_display )
        all_tags_and_descendants.update( itertools.chain.from_iterable( tag_ids_to_descendants.values() ) )
        
        # these are all ideal_tag_ids
        all_tags_and_descendants_to_chains = self.modules_tag_siblings.GetIdealTagIdsToChains( display_type, tag_service_id, all_tags_and_descendants )
        
        for ( tag_id, descendants ) in tag_ids_to_descendants.items():
            
            implications = set( itertools.chain.from_iterable( ( all_tags_and_descendants_to_chains[ descendant ] for descendant in descendants ) ) )
            implications.update( all_tags_and_descendants_to_chains[ tag_id ] )
            
            tag_ids_to_implied_by[ tag_id ] = implications
            
        
        return tag_ids_to_implied_by
        
    
    def GetTagsToImplies( self, display_type, tag_service_id, tag_ids ):
        
        # a tag implies its ideal sibling and any ancestors
        
        tag_ids_to_implies = collections.defaultdict( set )
        
        tag_ids_to_ideals = self.modules_tag_siblings.GetTagIdsToIdealTagIds( display_type, tag_service_id, tag_ids )
        
        ideal_tag_ids = set( tag_ids_to_ideals.values() )
        
        ideal_tag_ids_to_ancestors = self.modules_tag_parents.GetTagsToAncestors( display_type, tag_service_id, ideal_tag_ids )
        
        for ( tag_id, ideal_tag_id ) in tag_ids_to_ideals.items():
            
            implies = { ideal_tag_id }
            implies.update( ideal_tag_ids_to_ancestors[ ideal_tag_id ] )
            
            tag_ids_to_implies[ tag_id ] = implies
            
        
        return tag_ids_to_implies
        
    
    def GetUIDecorators( self, service_key, tags ):
        
        tags_to_display_decorators = { tag : None for tag in tags }
        
        if service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            return tags_to_display_decorators
            
        
        tag_service_id = self.modules_services.GetServiceId( service_key )
        
        existing_tags = { tag for tag in tags if self.modules_tags.TagExists( tag ) }
        
        existing_tag_ids = { self.modules_tags.GetTagId( tag ) for tag in existing_tags }
        
        existing_tag_ids_to_ideal_tag_ids = self.modules_tag_siblings.GetTagIdsToIdealTagIds( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, existing_tag_ids )
        
        ideal_tag_ids = set( existing_tag_ids_to_ideal_tag_ids.values() )
        
        interesting_tag_ids_to_ideal_tag_ids = { tag_id : ideal_tag_id for ( tag_id, ideal_tag_id ) in existing_tag_ids_to_ideal_tag_ids.items() if tag_id != ideal_tag_id }
        
        ideal_tag_ids_to_ancestor_tag_ids = self.modules_tag_parents.GetTagsToAncestors( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, ideal_tag_ids )
        
        existing_tag_ids_to_ancestor_tag_ids = { existing_tag_id : ideal_tag_ids_to_ancestor_tag_ids[ existing_tag_ids_to_ideal_tag_ids[ existing_tag_id ] ] for existing_tag_id in existing_tag_ids }
        
        interesting_tag_ids_to_ancestor_tag_ids = { tag_id : ancestor_tag_ids for ( tag_id, ancestor_tag_ids ) in existing_tag_ids_to_ancestor_tag_ids.items() if len( ancestor_tag_ids ) > 0 }
        
        all_interesting_tag_ids = set()
        
        all_interesting_tag_ids.update( interesting_tag_ids_to_ideal_tag_ids.keys() )
        all_interesting_tag_ids.update( interesting_tag_ids_to_ideal_tag_ids.values() )
        all_interesting_tag_ids.update( interesting_tag_ids_to_ancestor_tag_ids.keys() )
        all_interesting_tag_ids.update( itertools.chain.from_iterable( interesting_tag_ids_to_ancestor_tag_ids.values() ) )
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = all_interesting_tag_ids )
        
        for tag_id in existing_tag_ids:
            
            if tag_id in interesting_tag_ids_to_ideal_tag_ids:
                
                ideal = tag_ids_to_tags[ interesting_tag_ids_to_ideal_tag_ids[ tag_id ] ]
                
            else:
                
                ideal = None
                
            
            if tag_id in interesting_tag_ids_to_ancestor_tag_ids:
                
                parents = { tag_ids_to_tags[ ancestor_tag_id ] for ancestor_tag_id in interesting_tag_ids_to_ancestor_tag_ids[ tag_id ] }
                
            else:
                
                parents = None
                
            
            if ideal is not None or parents is not None:
                
                tag = tag_ids_to_tags[ tag_id ]
                
                tags_to_display_decorators[ tag ] = ( ideal, parents )
                
            
        
        return tags_to_display_decorators
        
    
    def IsChained( self, display_type, tag_service_id, tag_id ) -> bool:
        
        return self.modules_tag_parents.IsChained( display_type, tag_service_id, tag_id ) or self.modules_tag_siblings.IsChained( display_type, tag_service_id, tag_id )
        
    
    def NotifyParentsChanged( self, tag_service_id_that_changed, tag_ids_that_changed ):
        
        if len( tag_ids_that_changed ) == 0:
            
            return
            
        
        # the parents for tag_ids have changed for tag_service_id
        # therefore any service that is interested in tag_service_ids's parents needs to regen the respective chains for these tags
        
        interested_tag_service_ids = self.modules_tag_parents.GetInterestedServiceIds( tag_service_id_that_changed )
        
        self.modules_tag_parents.RegenChains( interested_tag_service_ids, tag_ids_that_changed )
        
    
    def NotifySiblingsChanged( self, tag_service_id_that_changed, tag_ids_that_changed ):
        
        if len( tag_ids_that_changed ) == 0:
            
            return
            
        
        # the siblings for tag_ids have changed for tag_service_id
        # therefore any service that is interested in tag_service_ids's siblings needs to regen the respective chains for these tags
        
        interested_tag_service_ids = self.modules_tag_siblings.GetInterestedServiceIds( tag_service_id_that_changed )
        
        self.modules_tag_siblings.RegenChains( interested_tag_service_ids, tag_ids_that_changed )
        
        # since siblings just changed, parents can as well! any interested service that has any of these tag_ids in its parent structure may need new ids, so let's regen
        
        self.modules_tag_parents.RegenChains( interested_tag_service_ids, tag_ids_that_changed )
        
    
    def RegenerateTagSiblingsAndParentsCache( self, only_these_service_ids = None ):
        
        if only_these_service_ids is None:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            tag_service_ids = only_these_service_ids
            
        
        self.modules_tag_siblings.Regen( tag_service_ids )
        
        # as siblings may have changed, parents may have as well
        self.modules_tag_parents.Regen( tag_service_ids )
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
        
    
    def SetApplication( self, service_keys_to_sibling_applicable_service_keys, service_keys_to_parent_applicable_service_keys ):
        
        sibling_service_ids_to_sync = self.modules_tag_siblings.SetApplication( service_keys_to_sibling_applicable_service_keys )
        parent_service_ids_to_sync = self.modules_tag_parents.SetApplication( service_keys_to_parent_applicable_service_keys )
        
        service_ids_to_sync = sibling_service_ids_to_sync.union( parent_service_ids_to_sync )
        
        #
        
        self.RegenerateTagSiblingsAndParentsCache( only_these_service_ids = service_ids_to_sync )
        
        self._cursor_transaction_wrapper.pub_after_job( 'notify_new_tag_display_application' )
        
