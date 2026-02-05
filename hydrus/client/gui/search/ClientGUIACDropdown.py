import collections
import collections.abc
import itertools
import typing

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListBoxesData
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelSortCollect
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUILocation
from hydrus.client.gui.search import ClientGUISearch
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchAutocomplete
from hydrus.client.search import ClientSearchParseSystemPredicates
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.external import LogicExpressionQueryParser

def AppendLoadingPredicate( predicates, label ):
    
    predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_LABEL, value = label + HC.UNICODE_ELLIPSIS ) )
    

def InsertOtherPredicatesForRead( predicates: collections.abc.MutableSequence[ ClientSearchPredicate.Predicate ], parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText, include_unusual_predicate_types: bool, under_construction_or_predicate: ClientSearchPredicate.Predicate | None ):
    
    if include_unusual_predicate_types:
        
        allow_auto_wildcard_conversion = True
        
        non_tag_predicates = list( parsed_autocomplete_text.GetNonTagFileSearchPredicates( allow_auto_wildcard_conversion ) )
        
        non_tag_predicates.reverse()
        
        for predicate in non_tag_predicates:
            
            PutAtTopOfMatches( predicates, predicate )
            
        
    
    if under_construction_or_predicate is not None:
        
        PutAtTopOfMatches( predicates, under_construction_or_predicate )
        
    

def InsertTagPredicates( predicates: collections.abc.MutableSequence[ ClientSearchPredicate.Predicate ], tag_service_key: bytes, parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText, allow_auto_wildcard_conversion: bool, insert_if_does_not_exist: bool = True ):
    
    if parsed_autocomplete_text.IsTagSearch( allow_auto_wildcard_conversion ):
        
        tag_predicate = parsed_autocomplete_text.GetImmediateFileSearchPredicate( allow_auto_wildcard_conversion )
        
        ideal_predicate = None
        
        if tag_predicate in predicates:
            
            tag_predicate = predicates[ predicates.index( tag_predicate ) ]
            
            # this is write only, of course
            ideal_predicate = tag_predicate.GetIdealPredicate()
            
        else:
            
            entered_text_as_tag = tag_predicate.GetValue()
            
            for predicate in predicates:
                
                if predicate.HasBadSiblings() and entered_text_as_tag in predicate.GetMatchableSearchTexts():
                    
                    tag_predicate = predicate
                    
                    break
                    
                
            
        
        # this elevates other tags that have our entered tag as a sibling somewhere to the top but tbh it wasn't helpful
        # better to just hove any ideal and what we typed up top
        '''
        actual_tag = tag_predicate.GetValue()
        
        other_matching_predicates = []
        
        for predicate in predicates:
            
            matchable_search_texts = predicate.GetMatchableSearchTexts()
            
            if len( matchable_search_texts ) <= 1:
                
                continue
                
            
            if actual_tag in matchable_search_texts:
                
                if predicate.GetIdealPredicate() is not None:
                    
                    continue
                    
                
                other_matching_predicates.append( predicate )
                
            
        
        ClientSearchPredicate.SortPredicates( other_matching_predicates )
        
        other_matching_predicates.reverse()
        
        for predicate in other_matching_predicates:
            
            PutAtTopOfMatches( predicates, predicate, insert_if_does_not_exist = insert_if_does_not_exist )
            
        '''
        
        PutAtTopOfMatches( predicates, tag_predicate, insert_if_does_not_exist = insert_if_does_not_exist )
        
        if ideal_predicate is not None:
            
            PutAtTopOfMatches( predicates, ideal_predicate, insert_if_does_not_exist = insert_if_does_not_exist )
            
        
    

def ReadFetch(
    win: QW.QWidget,
    job_status: ClientThreading.JobStatus,
    prefetch_callable,
    results_callable,
    parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText,
    qt_media_callable,
    file_search_context: ClientSearchFileSearchContext.FileSearchContext,
    synchronised,
    include_unusual_predicate_types,
    results_cache: ClientSearchAutocomplete.PredicateResultsCache,
    under_construction_or_predicate,
    force_system_everything
):
    
    tag_context = file_search_context.GetTagContext()
    
    tag_service_key = tag_context.service_key
    
    if not parsed_autocomplete_text.IsAcceptableForTagSearches():
        
        if parsed_autocomplete_text.IsEmpty():
            
            matches = []
            
            AppendLoadingPredicate( matches, 'loading system predicates' )
            
            CG.client_controller.CallAfterQtSafe( win, prefetch_callable, job_status, matches, parsed_autocomplete_text )
            
            cache_valid = isinstance( results_cache, ClientSearchAutocomplete.PredicateResultsCacheSystem )
            
            we_need_results = not cache_valid
            
            db_not_going_to_hang_if_we_hit_it = not CG.client_controller.DBCurrentlyDoingJob()
            
            if we_need_results or db_not_going_to_hang_if_we_hit_it:
                
                predicates = CG.client_controller.Read( 'file_system_predicates', file_search_context, force_system_everything = force_system_everything )
                
                results_cache = ClientSearchAutocomplete.PredicateResultsCacheSystem( predicates )
                
                matches = predicates
                
            else:
                
                matches = results_cache.GetPredicates()
                
            
        elif parsed_autocomplete_text.IsValidSystemPredicate():
            
            matches = parsed_autocomplete_text.GetValidSystemPredicates()
            
        else:
            
            # if the user inputs '-' or 'creator:' or similar, let's go to an empty list
            matches = []
            
        
    else:
        
        db_based_results = True
        
        if synchronised and qt_media_callable is not None and not file_search_context.GetSystemPredicates().HasSystemLimit():
            
            try:
                
                media = CG.client_controller.CallBlockingToQt( win, qt_media_callable )
                
            except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
                
                job_status.Cancel()
                
                return
                
            
            if job_status.IsCancelled():
                
                return
                
            
            media_available_and_good = media is not None and len( media ) > 0
            
            if media_available_and_good:
                
                db_based_results = False
                
            
        
        strict_search_text = parsed_autocomplete_text.GetSearchText( False )
        autocomplete_search_text = parsed_autocomplete_text.GetSearchText( True )
        
        if db_based_results:
            
            allow_auto_wildcard_conversion = True
            
            is_explicit_wildcard = parsed_autocomplete_text.IsExplicitWildcard( allow_auto_wildcard_conversion )
            
            if is_explicit_wildcard:
                
                cache_valid = False
                
            else:
                
                cache_valid = results_cache.CanServeTagResults( parsed_autocomplete_text, False )
                
            
            if cache_valid:
                
                matches = results_cache.FilterPredicates( tag_service_key, autocomplete_search_text )
                
            else:
                
                exact_match_predicates = CG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, file_search_context, search_text = strict_search_text, exact_match = True, job_status = job_status )
                
                small_exact_match_search = ShouldDoExactSearch( parsed_autocomplete_text )
                
                if small_exact_match_search:
                    
                    results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( exact_match_predicates, strict_search_text, True )
                    
                    matches = results_cache.FilterPredicates( tag_service_key, strict_search_text )
                    
                else:
                    
                    exact_match_matches = ClientSearchAutocomplete.FilterPredicatesBySearchText( tag_service_key, autocomplete_search_text, exact_match_predicates )
                    
                    exact_match_matches = ClientSearchPredicate.SortPredicates( exact_match_matches )
                    
                    allow_auto_wildcard_conversion = True
                    
                    InsertTagPredicates( exact_match_matches, tag_service_key, parsed_autocomplete_text, allow_auto_wildcard_conversion, insert_if_does_not_exist = False )
                    
                    InsertOtherPredicatesForRead( exact_match_matches, parsed_autocomplete_text, include_unusual_predicate_types, under_construction_or_predicate )
                    
                    AppendLoadingPredicate( exact_match_matches, 'loading full results' )
                    
                    CG.client_controller.CallAfterQtSafe( win, prefetch_callable, job_status, exact_match_matches, parsed_autocomplete_text )
                    
                    #
                    
                    search_namespaces_into_full_tags = parsed_autocomplete_text.GetTagAutocompleteOptions().SearchNamespacesIntoFullTags()
                    
                    predicates = CG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, file_search_context, search_text = autocomplete_search_text, job_status = job_status, search_namespaces_into_full_tags = search_namespaces_into_full_tags )
                    
                    if job_status.IsCancelled():
                        
                        return
                        
                    
                    if is_explicit_wildcard:
                        
                        matches = ClientSearchAutocomplete.FilterPredicatesBySearchText( tag_service_key, autocomplete_search_text, predicates )
                        
                    else:
                        
                        results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, strict_search_text, False )
                        
                        matches = results_cache.FilterPredicates( tag_service_key, autocomplete_search_text )
                        
                    
                
            
            if job_status.IsCancelled():
                
                return
                
            
        else:
            
            if not isinstance( results_cache, ClientSearchAutocomplete.PredicateResultsCacheMedia ):
                
                matches = []
                
                AppendLoadingPredicate( matches, 'calculating results' )
                
                CG.client_controller.CallAfterQtSafe( win, prefetch_callable, job_status, matches, parsed_autocomplete_text )
                
                # it is possible that media will change between calls to this, so don't cache it
                
                tags_managers = []
                
                for m in media:
                    
                    if m.IsCollection():
                        
                        tags_managers.extend( m.GetSingletonsTagsManagers() )
                        
                    else:
                        
                        tags_managers.append( m.GetTagsManager() )
                        
                    
                
                if job_status.IsCancelled():
                    
                    return
                    
                
                current_tags_to_count = collections.Counter()
                pending_tags_to_count = collections.Counter()
                
                include_current_tags = tag_context.include_current_tags
                include_pending_tags = tag_context.include_pending_tags
                
                for ( num_done, num_to_do, group_of_tags_managers ) in HydrusLists.SplitListIntoChunksRich( tags_managers, 1000 ):
                    
                    if include_current_tags:
                        
                        current_tags_to_count.update( itertools.chain.from_iterable( tags_manager.GetCurrent( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) for tags_manager in group_of_tags_managers ) )
                        
                    
                    if include_pending_tags:
                        
                        pending_tags_to_count.update( itertools.chain.from_iterable( [ tags_manager.GetPending( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) for tags_manager in group_of_tags_managers ] ) )
                        
                    
                    if job_status.IsCancelled():
                        
                        return
                        
                    
                
                tags_to_do = set()
                
                tags_to_do.update( current_tags_to_count.keys() )
                tags_to_do.update( pending_tags_to_count.keys() )
                
                tags_to_count = { tag : ( current_tags_to_count[ tag ], pending_tags_to_count[ tag ] ) for tag in tags_to_do }
                
                if job_status.IsCancelled():
                    
                    return
                    
                
                # we have data sans siblings and parents. send it as prefetch results, user will have _something_
                
                prefetch_predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, value = tag, inclusive = parsed_autocomplete_text.inclusive, count = ClientSearchPredicate.PredicateCount( current_count, pending_count, None, None ) ) for ( tag, ( current_count, pending_count ) ) in tags_to_count.items() ]
                
                prefetch_matches = ClientSearchAutocomplete.FilterPredicatesBySearchText( tag_service_key, autocomplete_search_text, prefetch_predicates )
                
                prefetch_matches = ClientSearchPredicate.SortPredicates( prefetch_matches )
                
                allow_auto_wildcard_conversion = True
                
                InsertTagPredicates( prefetch_matches, tag_service_key, parsed_autocomplete_text, allow_auto_wildcard_conversion, insert_if_does_not_exist = False )
                
                InsertOtherPredicatesForRead( prefetch_matches, parsed_autocomplete_text, include_unusual_predicate_types, under_construction_or_predicate )
                
                AppendLoadingPredicate( prefetch_matches, 'loading sibling data' )
                
                CG.client_controller.CallAfterQtSafe( win, prefetch_callable, job_status, prefetch_matches, parsed_autocomplete_text )
                
                #
                
                # now spend time fetching siblings if needed
                
                predicates = CG.client_controller.Read( 'media_predicates', tag_context, tags_to_count, job_status = job_status )
                
                results_cache = ClientSearchAutocomplete.PredicateResultsCacheMedia( predicates )
                
            
            if job_status.IsCancelled():
                
                return
                
            
            predicates = results_cache.FilterPredicates( tag_service_key, autocomplete_search_text )
            
            if job_status.IsCancelled():
                
                return
                
            
            predicates = ClientSearchPredicate.MergePredicates( predicates )
            
            matches = predicates
            
        
        matches = HydrusLists.FastIndexUniqueList( matches )
        
        matches = ClientSearchPredicate.SortPredicates( matches )
        
    
    matches = HydrusLists.FastIndexUniqueList( matches )
    
    allow_auto_wildcard_conversion = True
    
    InsertTagPredicates( matches, tag_service_key, parsed_autocomplete_text, allow_auto_wildcard_conversion, insert_if_does_not_exist = False )
    
    InsertOtherPredicatesForRead( matches, parsed_autocomplete_text, include_unusual_predicate_types, under_construction_or_predicate )
    
    ClientSearchPredicate.SetPredicatesInclusivity( matches, parsed_autocomplete_text.inclusive )
    
    if job_status.IsCancelled():
        
        return
        
    
    CG.client_controller.CallAfterQtSafe( win, results_callable, job_status, parsed_autocomplete_text, results_cache, matches )
    

def PutAtTopOfMatches( matches: collections.abc.MutableSequence[ ClientSearchPredicate.Predicate ], predicate: ClientSearchPredicate.Predicate, insert_if_does_not_exist: bool = True ):
    
    # we have to be careful here to preserve autocomplete counts!
    # if it already exists, we move it up, do not replace with the test pred param
    
    if predicate in matches:
        
        index = matches.index( predicate )
        
        predicate_to_insert = matches[ index ]
        
        del matches[ index ]
        
        matches.insert( 0, predicate_to_insert )
        
    else:
        
        if insert_if_does_not_exist:
            
            matches.insert( 0, predicate )
            
        
    
def ShouldDoExactSearch( parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText ):
    
    allow_auto_wildcard_conversion = True
    
    if parsed_autocomplete_text.IsExplicitWildcard( allow_auto_wildcard_conversion ):
        
        return False
        
    
    strict_search_text = parsed_autocomplete_text.GetSearchText( False )
    
    exact_match_character_threshold = parsed_autocomplete_text.GetTagAutocompleteOptions().GetExactMatchCharacterThreshold()
    
    if exact_match_character_threshold is None:
        
        return False
        
    
    if ':' in strict_search_text:
        
        ( namespace, test_text ) = HydrusTags.SplitTag( strict_search_text )
        
    else:
        
        test_text = strict_search_text
        
    
    if len( test_text ) == 0:
        
        return False
        
    
    return len( test_text ) <= exact_match_character_threshold
    

def WriteFetch(
    win: QW.QWidget,
    job_status: ClientThreading.JobStatus,
    prefetch_callable,
    results_callable,
    parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText,
    file_search_context: ClientSearchFileSearchContext.FileSearchContext,
    results_cache: ClientSearchAutocomplete.PredicateResultsCache
):
    
    tag_context = file_search_context.GetTagContext()
    
    display_tag_service_key = tag_context.display_service_key
    
    if not parsed_autocomplete_text.IsAcceptableForTagSearches():
        
        matches = []
        
    else:
        
        allow_auto_wildcard_conversion = False
        
        # TODO: This allow_auto_wildcard_conversion hack to handle allow_unnamespaced_search_gives_any_namespace_wildcards is hell. I should write IsImplicitWildcard or something!
        is_explicit_wildcard = parsed_autocomplete_text.IsExplicitWildcard( allow_auto_wildcard_conversion )
        
        strict_search_text = parsed_autocomplete_text.GetSearchText( False, allow_auto_wildcard_conversion = allow_auto_wildcard_conversion )
        autocomplete_search_text = parsed_autocomplete_text.GetSearchText( True, allow_auto_wildcard_conversion = allow_auto_wildcard_conversion )
        
        if is_explicit_wildcard:
            
            cache_valid = False
            
        else:
            
            cache_valid = results_cache.CanServeTagResults( parsed_autocomplete_text, False, allow_auto_wildcard_conversion = allow_auto_wildcard_conversion )
            
        
        if cache_valid:
            
            matches = results_cache.FilterPredicates( display_tag_service_key, autocomplete_search_text )
            
        else:
            
            original_exact_match_predicates = CG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = strict_search_text, exact_match = True, zero_count_ok = True, job_status = job_status )
            
            exact_match_predicates = list( original_exact_match_predicates )
            
            small_exact_match_search = ShouldDoExactSearch( parsed_autocomplete_text )
            
            if small_exact_match_search:
                
                results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( exact_match_predicates, strict_search_text, True )
                
                matches = results_cache.FilterPredicates( display_tag_service_key, strict_search_text )
                
            else:
                
                exact_match_matches = ClientSearchAutocomplete.FilterPredicatesBySearchText( display_tag_service_key, autocomplete_search_text, exact_match_predicates )
                
                exact_match_matches = ClientSearchPredicate.SortPredicates( exact_match_matches )
                
                allow_auto_wildcard_conversion = False
                
                InsertTagPredicates( exact_match_matches, display_tag_service_key, parsed_autocomplete_text, allow_auto_wildcard_conversion )
                
                AppendLoadingPredicate( exact_match_matches, 'loading full results' )
                
                CG.client_controller.CallAfterQtSafe( win, prefetch_callable, job_status, exact_match_matches, parsed_autocomplete_text )
                
                if job_status.IsCancelled():
                    
                    return
                    
                
                #
                
                search_namespaces_into_full_tags = parsed_autocomplete_text.GetTagAutocompleteOptions().SearchNamespacesIntoFullTags()
                
                predicates = CG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = autocomplete_search_text, job_status = job_status, zero_count_ok = True, search_namespaces_into_full_tags = search_namespaces_into_full_tags )
                
                if is_explicit_wildcard:
                    
                    matches = ClientSearchAutocomplete.FilterPredicatesBySearchText( display_tag_service_key, autocomplete_search_text, predicates )
                    
                else:
                    
                    results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, strict_search_text, False )
                    
                    matches = results_cache.FilterPredicates( display_tag_service_key, autocomplete_search_text )
                    
                
            
            if job_status.IsCancelled():
                
                return
                
            
        
    
    matches = ClientSearchPredicate.SortPredicates( matches )
    
    matches = HydrusLists.FastIndexUniqueList( matches )
    
    allow_auto_wildcard_conversion = False
    
    InsertTagPredicates( matches, display_tag_service_key, parsed_autocomplete_text, allow_auto_wildcard_conversion )
    
    CG.client_controller.CallAfterQtSafe( win, results_callable, job_status, parsed_autocomplete_text, results_cache, matches )
    

class ListBoxTagsPredicatesAC( ClientGUIListBoxes.ListBoxTagsPredicates ):
    
    def __init__( self, parent, callable, float_mode, service_key, **kwargs ):
        
        super().__init__( parent, **kwargs )
        
        self._callable = callable
        self._float_mode = float_mode
        self._service_key = service_key
        
        self._predicates = {}
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        
        if self._float_mode:
            
            widget = self.window()
            
        else:
            
            widget = self
            
        
        predicates = ClientGUISearch.FleshOutPredicates( widget, predicates )
        
        if len( predicates ) > 0:
            
            self._callable( predicates, shift_down )
            
            return True
            
        
        return False
        
    
    def _GenerateTermFromPredicate( self, predicate: ClientSearchPredicate.Predicate ):
        
        term = ClientGUIListBoxes.ListBoxTagsPredicates._GenerateTermFromPredicate( self, predicate )
        
        if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER:
            
            term.SetORUnderConstruction( True )
            
        
        return term
        
    
    def SetPredicates( self, predicates, preserve_single_selection = False ):
        
        # need to do a clever compare, since normal predicate compare doesn't take count into account
        
        they_are_the_same = True
        
        if len( predicates ) == len( self._predicates ):
            
            for index in range( len( predicates ) ):
                
                p_1 = predicates[ index ]
                p_2 = self._predicates[ index ]
                
                if p_1 != p_2 or p_1.GetCount() != p_2.GetCount():
                    
                    they_are_the_same = False
                    
                    break
                    
                
            
        else:
            
            they_are_the_same = False
            
        
        if not they_are_the_same:
            
            previously_selected_predicate = None
            
            if len( self._selected_terms ) == 1:
                
                ( previously_selected_term, ) = self._selected_terms
                
                if isinstance( previously_selected_term, ClientGUIListBoxesData.ListBoxItemPredicate ):
                    
                    previously_selected_predicate = previously_selected_term.GetPredicate()
                    
                
            
            # important to make own copy, as same object originals can be altered (e.g. set non-inclusive) in cache, and we need to notice that change just above
            self._predicates = [ predicate.GetCopy() for predicate in predicates ]
            
            self._Clear()
            
            terms = [ self._GenerateTermFromPredicate( predicate ) for predicate in predicates ]
            
            self._AppendTerms( terms )
            
            self._DataHasChanged()
            
            if len( self._predicates ) > 0:
                
                ac_select_first_with_count = CG.client_controller.new_options.GetBoolean( 'ac_select_first_with_count' )
                
                if ac_select_first_with_count: # no matter what, selection preservation won't work well if we move selection down
                    
                    preserve_single_selection = False
                    
                
                if preserve_single_selection and previously_selected_predicate is not None and previously_selected_predicate in self._predicates:
                    
                    logical_index_to_select = self._predicates.index( previously_selected_predicate )
                    
                else:
                    
                    logical_index_to_select = 0
                    
                    if len( self._predicates ) > 1:
                        
                        skip_ors = True
                        
                        some_preds_have_count = True in ( predicate.GetCount().HasNonZeroCount() for predicate in self._predicates )
                        skip_countless = ac_select_first_with_count and some_preds_have_count
                        
                        for ( index, predicate ) in enumerate( self._predicates ):
                            
                            # now only apply this to simple tags, not wildcards and system tags
                            
                            if skip_ors and predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER:
                                
                                continue
                                
                            
                            if skip_countless and predicate.GetType() in ( ClientSearchPredicate.PREDICATE_TYPE_PARENT, ClientSearchPredicate.PREDICATE_TYPE_TAG ) and predicate.GetCount().HasZeroCount():
                                
                                continue
                                
                            
                            logical_index_to_select = index
                            
                            break
                            
                        
                    
                
                self._Hit( False, False, logical_index_to_select )
                
            
        
    
    def SetTagServiceKey( self, service_key: bytes ):
        
        self._service_key = service_key
        
    
class ListBoxTagsStringsAC( ClientGUIListBoxes.ListBoxTagsStrings ):
    
    def __init__( self, parent, callable, service_key, float_mode, **kwargs ):
        
        super().__init__( parent, service_key = service_key, sort_tags = False, **kwargs )
        
        self._callable = callable
        self._float_mode = float_mode
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        
        if self._float_mode:
            
            widget = self.window()
            
        else:
            
            widget = self
            
        
        predicates = ClientGUISearch.FleshOutPredicates( widget, predicates )
        
        if len( predicates ) > 0:
            
            self._callable( predicates, shift_down )
            
            return True
            
        
        return False
        
    

# TODO: this gubbins remains a huge mess. when does a result fetch job start? when is the input cleared? how does focus work?
# we need to decouple!
# first order of business is sucking the results generation out to a results factory
# also want to do 'broadcastchoices' and such through signals, not direct calls

class AutoCompleteDropdown( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
    
    movePageLeft = QC.Signal()
    movePageRight = QC.Signal()
    showNext = QC.Signal()
    showPrevious = QC.Signal()
    externalCopyKeyPressEvent = QC.Signal( QG.QKeyEvent )
    
    def __init__( self, parent ):
        
        self._qss_colours = {
            CC.COLOUR_AUTOCOMPLETE_BACKGROUND : QG.QColor( 235, 248, 255 )
        }
        
        super().__init__( parent )
        
        self.setObjectName( 'HydrusTagAutocomplete' )
        
        self._can_intercept_unusual_key_events = True
        
        if self.window() == CG.client_controller.gui:
            
            use_float_mode = CG.client_controller.new_options.GetBoolean( 'autocomplete_float_main_gui' )
            
        else:
            
            use_float_mode = False
            
        
        self._float_mode = use_float_mode
        self._temporary_focus_widget = None
        self._time_results_last_set = 0
        
        self._text_input_panel = QW.QWidget( self )
        
        self._text_ctrl = QW.QLineEdit( self._text_input_panel )
        
        self.setFocusProxy( self._text_ctrl )
        
        self._last_attempted_dropdown_width = 0
        
        self._text_ctrl.textChanged.connect( self.NotifyTagTextInputChanged )
        
        self._text_ctrl.installEventFilter( self )
        
        self._main_vbox = QP.VBoxLayout( margin = 0 )
        
        self._SetupTopListBox()
        
        self._text_input_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._text_input_hbox, self._text_ctrl, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        self._text_input_panel.setLayout( self._text_input_hbox )
        
        QP.AddToLayout( self._main_vbox, self._text_input_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if self._float_mode:
            
            # needs to have bigger parent in order to draw fully, otherwise it is clipped by our little panel box
            p = self.parentWidget()
            
            # we don't want the .window() since that clusters all these a/cs as children of it. not beautiful, and page deletion won't delete them
            # let's try and chase page
            while not ( p is None or p == self.window() or isinstance( p.parentWidget(), QW.QTabWidget ) ):
                
                p = p.parentWidget()
                
            
            parent_to_use = p
            
            self._dropdown_window = QW.QFrame( parent_to_use )
            
            self._dropdown_window.setFrameStyle( QW.QFrame.Shape.Panel | QW.QFrame.Shadow.Raised )
            self._dropdown_window.setLineWidth( 2 )
            
            self._dropdown_hidden = True
            
            self._force_dropdown_hide = False
            
            # We need this, or else if the QSS does not define a Widget background color (the default), these 'raised' windows are transparent lmao
            self._dropdown_window.setAutoFillBackground( True )
            
            self._dropdown_window.hide()
            
            self._dropdown_window.setFocusProxy( self._text_ctrl )
            
        else:
            
            self._dropdown_window = QW.QWidget( self )
            
            QP.AddToLayout( self._main_vbox, self._dropdown_window, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        self._dropdown_notebook = QW.QTabWidget( self._dropdown_window )
        
        #
        
        self._search_results_list = self._InitSearchResultsList()
        
        self._dropdown_notebook.setCurrentIndex( self._dropdown_notebook.addTab( self._search_results_list, 'results' ) )
        
        #
        
        self.setLayout( self._main_vbox )
        
        self._current_list_parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText(
            '',
            tag_autocomplete_options = CG.client_controller.tag_display_manager.GetTagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY ),
            collapse_search_characters = True
        )
        
        self._results_cache: ClientSearchAutocomplete.PredicateResultsCache = ClientSearchAutocomplete.PredicateResultsCacheInit()
        
        self._current_fetch_job_status = None
        
        self._refresh_results_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._UpdateSearchResults )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'tags_autocomplete' ], alternate_filter_target = self._text_ctrl )
        
        if self._float_mode:
            
            parent = self
            
            self._scroll_event_filters = []
            
            while True:
                
                try:
                    
                    parent = parent.parentWidget()
                    
                    if parent is None or parent == self.window():
                        
                        break
                        
                    
                    if isinstance( parent, QW.QScrollArea ):
                        
                        parent.verticalScrollBar().valueChanged.connect( self.ParentWasScrolled )
                        
                    
                except Exception as e:
                    
                    break
                    
                
            
        
        CG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        CG.client_controller.sub( self, 'DoDropdownHideShow', 'notify_page_change' )
        
        self._refresh_results_updater.Update()
        
        CG.client_controller.CallLaterQtSafe( self, 0.05, 'hide/show dropdown', self._DropdownHideShow )
        
        # trying a second go to see if that improves some positioning
        CG.client_controller.CallLaterQtSafe( self, 0.25, 'hide/show dropdown', self._DropdownHideShow )
        
        CG.client_controller.CallLaterQtSafe( self, 0.05, 'do autocomplete background colour', self._UpdateBackgroundColour )
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        raise NotImplementedError()
        
    
    def _BroadcastCurrentInputFromEnterKey( self, shift_down ):
        
        raise NotImplementedError()
        
    
    def _CancelSearchResultsFetchJob( self ):
        
        if self._current_fetch_job_status is not None:
            
            self._current_fetch_job_status.Cancel()
            
            self._current_fetch_job_status = None
            
        
    
    def _ClearInput( self ):
        
        self._CancelSearchResultsFetchJob()
        
        self._text_ctrl.blockSignals( True )
        
        self._text_ctrl.clear()
        
        self._SetResultsToList( [], self._GetParsedAutocompleteText() )
        
        self._text_ctrl.blockSignals( False )
        
        self._refresh_results_updater.Update()
        
    
    def _GetParsedAutocompleteText( self ) -> ClientSearchAutocomplete.ParsedAutocompleteText:
        
        raise NotImplementedError()
        
    
    def _DropdownHideShow( self ):
        
        if not self._float_mode:
            
            return
            
        
        try:
            
            if self._ShouldShow():
                
                self._ShowDropdown()
                
            else:
                
                self._HideDropdown()
                
            
        except Exception as e:
            
            raise
            
        
    
    def _DueAutoRefresh( self ):
        
        if self._refresh_results_updater.IsWorking():
            
            return False
            
        
        return HydrusTime.TimeHasPassed( self._time_results_last_set + 300 )
        
    
    def _HandleEscape( self ):
        
        if self._text_ctrl.text() != '':
            
            self._ClearInput()
            
            return True
            
        elif self._float_mode:
            
            self.parentWidget().setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
            return True
            
        else:
            
            return False
            
        
    
    def _HideDropdown( self ):
        
        if not self._dropdown_hidden:
            
            self._dropdown_window.hide()
            
            self._dropdown_hidden = True
            
        
    
    def _InitSearchResultsList( self ):
        
        raise NotImplementedError()
        
    
    def _RestoreTextCtrlFocus( self ):
        
        # if an event came from clicking the dropdown or stop or something, we want to put focus back on textctrl
        current_focus_widget = QW.QApplication.focusWidget()
        
        if ClientGUIFunctions.IsQtAncestor( current_focus_widget, self ):
            
            ClientGUIFunctions.SetFocusLater( self._text_ctrl )
            
        
    
    def _SetupTopListBox( self ):
        
        pass
        
    
    def _SetListDirty( self ):
        
        self._results_cache = ClientSearchAutocomplete.PredicateResultsCacheInit()
        
        self._refresh_results_updater.Update()
        
    
    def _SetResultsToList( self, results, parsed_autocomplete_text ):
        
        self._time_results_last_set = HydrusTime.GetNow()
        
    
    def _ShouldBroadcastCurrentInputOnEnterKey( self ):
        
        raise NotImplementedError()
        
    
    def _ShouldShow( self ):
        
        if self._force_dropdown_hide:
            
            return False
            
        
        current_active_window = QW.QApplication.activeWindow()
        
        i_am_active_and_focused = self.window() == current_active_window and self._text_ctrl.hasFocus() and not self.visibleRegion().isEmpty()
        
        visible = self.isVisible()
        
        return i_am_active_and_focused and visible
        
    
    def _ShowDropdown( self ):
        
        text_panel_size = self._text_input_panel.size()
        
        text_input_width = text_panel_size.width()
        
        if self._text_input_panel.isVisible():
            
            desired_dropdown_position = self.mapTo( self._dropdown_window.parent(), self._text_input_panel.geometry().bottomLeft() )
            
            if self.pos() != desired_dropdown_position:
                
                self._dropdown_window.move( desired_dropdown_position )
                
            
        
        self._dropdown_window.raise_()
        
        #
        
        if self._dropdown_hidden:
            
            self._dropdown_window.show()
            
            self._dropdown_hidden = False
            
        
        if text_input_width != self._last_attempted_dropdown_width:
            
            self._dropdown_window.setFixedWidth( text_input_width )
            
            self._last_attempted_dropdown_width = text_input_width
            
            self._dropdown_window.adjustSize()
            
        
    
    def _StartSearchResultsFetchJob( self, job_status ):
        
        raise NotImplementedError()
        
    
    def _TryToProcessAPasteEvent( self ) -> bool:
        
        return False
        
    
    def _UpdateBackgroundColour( self ):
        
        bg_colour = self.GetColour( CC.COLOUR_AUTOCOMPLETE_BACKGROUND )
        
        if not self._can_intercept_unusual_key_events:
            
            bg_colour = ClientGUIFunctions.GetLighterDarkerColour( bg_colour )
            
        
        QP.SetBackgroundColour( self._text_ctrl, bg_colour )
        
        self._text_ctrl.update()
        
    
    def _UpdateSearchResults( self ):
        
        self._CancelSearchResultsFetchJob()
        
        self._current_fetch_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._StartSearchResultsFetchJob( self._current_fetch_job_status )
        
    
    def BroadcastChoices( self, predicates, shift_down = False ):
        
        self._BroadcastChoices( predicates, shift_down )
        
        self._RestoreTextCtrlFocus()
        
    
    def CancelCurrentResultsFetchJob( self ):
        
        self._CancelSearchResultsFetchJob()
        
    
    def DoDropdownHideShow( self ):
        
        self._DropdownHideShow()
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if watched == self._text_ctrl:
                
                if event.type() == QC.QEvent.Type.KeyPress and self._can_intercept_unusual_key_events:
                    
                    event = typing.cast( QG.QKeyEvent, event )
                    
                    # ok for a while this thing was a mis-mash of logical tests and basically sending anything not explicitly caught to the list
                    # this resulted in annoying miss-cases where ctrl+c et al were being passed to the list and so you couldn't copy text from the text input
                    # THUS we are moving to a strict whitelist. a handful of events will pass down to the list, everything else we jealously keep
                    
                    CG.client_controller.ResetIdleTimer()
                    
                    ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
                    
                    send_input_to_current_list = False
                    
                    ctrl = event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier
                    
                    # previous/next hardcoded shortcuts, should obviously be migrated to a user-customised shortcut set in future!
                    crazy_n_p_hardcodes = ctrl and key in ( ord( 'P' ), ord( 'p' ), ord( 'N' ), ord( 'n' ) )
                    
                    we_copying = ClientGUIShortcuts.KeyPressEventIsACopy( event )
                    
                    we_copying_elsewhere = we_copying and self._text_ctrl.selectedText() == ''
                    
                    current_results_list = typing.cast( ClientGUIListBoxes.ListBoxTags, self._dropdown_notebook.currentWidget() )
                    
                    try:
                        
                        stuff_in_results_list = len( current_results_list ) > 0
                        
                    except Exception as e:
                        
                        stuff_in_results_list = False
                        
                    
                    we_copying_the_results_list = we_copying_elsewhere and stuff_in_results_list
                    we_emitting_an_external_copy = we_copying_elsewhere and not stuff_in_results_list
                    
                    we_pasting = ClientGUIShortcuts.KeyPressEventIsAPaste( event )
                    
                    if we_pasting:
                        
                        processed = self._TryToProcessAPasteEvent()
                        
                        if processed:
                            
                            return True
                            
                        
                    
                    if we_emitting_an_external_copy:
                        
                        self.externalCopyKeyPressEvent.emit( event )
                        
                        return event.isAccepted()
                        
                    elif key in ( QC.Qt.Key.Key_Up, QC.Qt.Key.Key_Down, QC.Qt.Key.Key_PageDown, QC.Qt.Key.Key_PageUp, QC.Qt.Key.Key_Home, QC.Qt.Key.Key_End ) or crazy_n_p_hardcodes or we_copying_the_results_list:
                        
                        send_input_to_current_list = True
                        
                    elif key in ( QC.Qt.Key.Key_Return, QC.Qt.Key.Key_Enter ):
                        
                        if self._ShouldBroadcastCurrentInputOnEnterKey():
                            
                            shift_down = modifier == QC.Qt.KeyboardModifier.ShiftModifier
                            
                            self._BroadcastCurrentInputFromEnterKey( shift_down )
                            
                            event.accept()
                            
                            return True
                            
                        else:
                            
                            send_input_to_current_list = True
                            
                        
                    elif key == QC.Qt.Key.Key_Escape:
                        
                        escape_caught = self._HandleEscape()
                        
                        if escape_caught:
                            
                            event.accept()
                            
                            return True
                            
                        else:
                            
                            send_input_to_current_list = True
                            
                        
                    
                    if send_input_to_current_list:
                        
                        current_results_list = self._dropdown_notebook.currentWidget()
                        
                        current_results_list.keyPressEvent( event )
                        
                        return event.isAccepted()
                        
                    
                elif event.type() == QC.QEvent.Type.Wheel:
                    
                    event = typing.cast( QG.QWheelEvent, event )
                    
                    current_results_list = typing.cast( ClientGUIListBoxes.ListBoxTags, self._dropdown_notebook.currentWidget() )
                    
                    if self._text_ctrl.text() == '' and len( current_results_list ) == 0:
                        
                        if event.angleDelta().y() > 0:
                            
                            self.movePageLeft.emit()
                            
                        else:
                            
                            self.movePageRight.emit()
                            
                        
                        event.accept()
                        
                        return True
                        
                    elif event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier:
                        
                        if event.angleDelta().y() > 0:
                            
                            current_results_list.MoveSelectionUp()
                            
                        else:
                            
                            current_results_list.MoveSelectionDown()
                            
                        
                        event.accept()
                        
                        return True
                        
                    elif self._float_mode and not self._dropdown_hidden:
                        
                        # it is annoying to scroll on this lad when float is around, so swallow it here
                        
                        event.accept()
                        
                        return True
                        
                    
                elif self._float_mode:
                    
                    # I could probably wangle this garbagewith setFocusProxy on all the children of the dropdown, assuming that wouldn't break anything, but this seems to work ok nonetheless
                    
                    if event.type() == QC.QEvent.Type.FocusIn:
                        
                        self._DropdownHideShow()
                        
                        return False
                        
                    elif event.type() == QC.QEvent.Type.FocusOut:
                        
                        current_focus_widget = QW.QApplication.focusWidget()
                        
                        if current_focus_widget is not None and ClientGUIFunctions.IsQtAncestor( current_focus_widget, self._dropdown_window ):
                            
                            self._temporary_focus_widget = current_focus_widget
                            
                            self._temporary_focus_widget.installEventFilter( self )
                            
                        else:
                            
                            self._DropdownHideShow()
                            
                        
                        return False
                        
                    
                
            elif self._temporary_focus_widget is not None and watched == self._temporary_focus_widget:
                
                if self._float_mode and event.type() == QC.QEvent.Type.FocusOut:
                    
                    self._temporary_focus_widget.removeEventFilter( self )
                    
                    self._temporary_focus_widget = None
                    
                    current_focus_widget = QW.QApplication.focusWidget()
                    
                    if current_focus_widget is None:
                        
                        # happens sometimes when moving tabs in the tags dropdown list
                        ClientGUIFunctions.SetFocusLater( self._text_ctrl )
                        
                    elif ClientGUIFunctions.IsQtAncestor( current_focus_widget, self._dropdown_window ):
                        
                        self._temporary_focus_widget = current_focus_widget
                        
                        self._temporary_focus_widget.installEventFilter( self )
                        
                    else:
                        
                        self._DropdownHideShow()
                        
                    
                    return False
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def GetColour( self, colour_type ):
        
        new_options = CG.client_controller.new_options
        
        if new_options.GetBoolean( 'override_stylesheet_colours' ):
            
            return new_options.GetColour( colour_type )
            
        else:
            
            return self._qss_colours.get( colour_type, QG.QColor( 127, 127, 127 ) )
            
        
    
    def moveEvent( self, event ):
        
        self._DropdownHideShow()
        
        return super().moveEvent( event )
        
    
    def MoveNotebookPageFocus( self, index = None, direction = None ):
        
        new_index = None
        
        if index is not None:
            
            new_index = index
            
        elif direction is not None:
            
            current_index = self._dropdown_notebook.currentIndex()
            
            if current_index is not None and current_index != -1:
                
                number_of_pages = self._dropdown_notebook.count()
                
                new_index = ( current_index + direction ) % number_of_pages # does wraparound
                
            
        
        if new_index is not None:
            
            self._dropdown_notebook.setCurrentIndex( new_index )
            
            self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def NotifyTagTextInputChanged( self, new_text ):
        
        num_chars = len( self._text_ctrl.text() )
        
        if num_chars == 0:
            
            self._refresh_results_updater.Update()
            
        else:
            
            parsed_autocomplete_text = self._GetParsedAutocompleteText()
            
            if parsed_autocomplete_text.GetTagAutocompleteOptions().FetchResultsAutomatically():
                
                self._refresh_results_updater.Update()
                
            
            if self._dropdown_notebook.currentWidget() != self._search_results_list:
                
                self.MoveNotebookPageFocus( index = 0 )
                
            
        
    
    def ParentWasScrolled( self ):
        
        self._DropdownHideShow()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_AUTOCOMPLETE_IME_MODE:
                
                self._can_intercept_unusual_key_events = not self._can_intercept_unusual_key_events
                
                self._UpdateBackgroundColour()
                
            elif self._can_intercept_unusual_key_events:
                
                current_results_list = self._dropdown_notebook.currentWidget()
                
                current_list_is_empty = len( current_results_list ) == 0
                
                input_is_empty = self._text_ctrl.text() == ''
                
                everything_is_empty = input_is_empty and current_list_is_empty
                
                if action == CAC.SIMPLE_AUTOCOMPLETE_FORCE_FETCH:
                    
                    self._refresh_results_updater.Update()
                    
                elif input_is_empty and action in ( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_LEFT, CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_RIGHT ):
                    
                    if action == CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_LEFT:
                        
                        direction = -1
                        
                    else:
                        
                        direction = 1
                        
                    
                    self.MoveNotebookPageFocus( direction = direction )
                    
                elif everything_is_empty and action == CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_LEFT:
                    
                    self.movePageLeft.emit()
                    
                elif everything_is_empty and action == CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_RIGHT:
                    
                    self.movePageRight.emit()
                    
                elif everything_is_empty and action == CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_PREVIOUS:
                    
                    self.showPrevious.emit()
                    
                elif everything_is_empty and action == CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_NEXT:
                    
                    self.showNext.emit()
                    
                else:
                    
                    command_processed = False
                    
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def resizeEvent( self, event ):
        
        self._DropdownHideShow()
        
        super().resizeEvent( event )
        
    
    def SetForceDropdownHide( self, value ):
        
        self._force_dropdown_hide = value
        
        self._DropdownHideShow()
        
    
    def REPEATINGPageUpdate( self ):
        
        # we could do _GetParsedAutocompleteText to be neat here, but the IsEmpty test is just this, so let's optimise for this frequently-consulted method
        if self._DueAutoRefresh() and self._text_ctrl.text() == '':
            
            self._refresh_results_updater.Update()
            
        
    
    def get_hta_background( self ):
        
        return self._qss_colours[ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ]
        
    
    def set_hta_background( self, colour ):
        
        self._qss_colours[ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ] = colour
        
    
    hta_background = QC.Property( QG.QColor, get_hta_background, set_hta_background )
    

class ChildrenTab( ListBoxTagsPredicatesAC ):
    
    def __init__( self, parent: QW.QWidget, broadcast_call, float_mode: bool, location_context: ClientLocation.LocationContext, tag_service_key: bytes, tag_display_type: int = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars: int = 4 ):
        
        self._location_context = location_context
        self._tags_to_child_predicates_cache = dict()
        self._children_need_updating = True
        
        super().__init__( parent, broadcast_call, float_mode, tag_service_key, tag_display_type = tag_display_type, height_num_chars = height_num_chars )
        
    
    def NotifyNeedsUpdating( self ):
        
        self._children_need_updating = True
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._location_context = location_context
        
    
    def SetTagServiceKey( self, service_key: bytes ):
        
        ListBoxTagsPredicatesAC.SetTagServiceKey( self, service_key )
        
        self._tags_to_child_predicates_cache = dict()
        
    
    def UpdateChildrenIfNeeded( self, context_tags: collections.abc.Collection[ str ] ):
        
        if self._children_need_updating:
            
            context_tags = set( context_tags )
            
            tag_display_type = self._tag_display_type
            location_context = self._location_context
            tag_service_key = self._service_key
            tags_to_child_predicates_cache = dict( self._tags_to_child_predicates_cache )
            
            if location_context.IsOneDomain():
                
                search_location_context = location_context
                
            else:
                
                # let's not blat the db on some crazy multi-domain just for this un-numbered list
                search_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_TAG_SERVICE_KEY )
                
            
            tag_context = ClientSearchTagContext.TagContext( service_key = tag_service_key )
            
            file_search_context = ClientSearchFileSearchContext.FileSearchContext(
                location_context = search_location_context,
                tag_context = tag_context
            )
            
            def work_callable():
                
                uncached_context_tags = { tag for tag in context_tags if tag not in tags_to_child_predicates_cache }
                
                if len( uncached_context_tags ) > 0:
                    
                    new_tags_to_child_tags = CG.client_controller.Read( 'tag_descendants_lookup', tag_service_key, uncached_context_tags )
                    
                    new_child_tags = HydrusLists.MassUnion( new_tags_to_child_tags.values() )
                    
                    child_predicates = CG.client_controller.Read(
                        'tag_predicates',
                        tag_display_type,
                        file_search_context,
                        new_child_tags,
                        zero_count_ok = True
                    )
                    
                    child_tags_to_child_predicates = { predicate.GetValue() : predicate for predicate in child_predicates }
                    
                    new_tags_to_child_predicates = { tag : { child_tags_to_child_predicates[ child_tag ] for child_tag in child_tags if child_tag in child_tags_to_child_predicates } for ( tag, child_tags ) in new_tags_to_child_tags.items() }
                    
                else:
                    
                    new_tags_to_child_predicates = dict()
                    
                
                child_predicates = set()
                
                for tag in context_tags:
                    
                    if tag in tags_to_child_predicates_cache:
                        
                        child_predicates.update( tags_to_child_predicates_cache[ tag ] )
                        
                    elif tag in new_tags_to_child_predicates:
                        
                        child_predicates.update( new_tags_to_child_predicates[ tag ] )
                        
                    
                
                child_predicates = [ predicate for predicate in child_predicates if predicate.GetValue() not in context_tags ]
                
                ClientSearchPredicate.SortPredicates( child_predicates )
                
                child_predicates = [ predicate.GetCountlessCopy() for predicate in child_predicates ]
                
                num_to_show_in_ac_dropdown_children_tab = CG.client_controller.new_options.GetNoneableInteger( 'num_to_show_in_ac_dropdown_children_tab' )
                
                if num_to_show_in_ac_dropdown_children_tab is not None:
                    
                    child_predicates = child_predicates[ : num_to_show_in_ac_dropdown_children_tab ]
                    
                
                return ( location_context, tag_service_key, child_predicates, new_tags_to_child_predicates )
                
            
            def publish_callable( result ):
                
                ( job_location_context, job_tag_service_key, child_predicates, new_tags_to_children ) = result
                
                if job_location_context != self._location_context or job_tag_service_key != self._service_key:
                    
                    self.SetPredicates( [] )
                    
                    return
                    
                
                self._tags_to_child_predicates_cache.update( new_tags_to_children )
                
                self.SetPredicates( child_predicates, preserve_single_selection = True )
                
                self._children_need_updating = False
                
            
            def errback_callable( etype, value, tb ):
                
                self.SetPredicates( [] )
                
                self._children_need_updating = False
                
                HydrusData.ShowText( 'Trying to load some child tags failed, please send this to hydev:' )
                HydrusData.ShowExceptionTuple( etype, value, tb, do_wait = False )
                
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable )
            
            job.start()
            
        
    

class AutoCompleteDropdownTags( AutoCompleteDropdown ):
    
    locationChanged = QC.Signal( ClientLocation.LocationContext )
    tagContextChanged = QC.Signal( ClientSearchTagContext.TagContext )
    
    def __init__( self, parent, location_context: ClientLocation.LocationContext, tag_context: ClientSearchTagContext.TagContext ):
        
        location_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        if not CG.client_controller.services_manager.ServiceExists( tag_context.service_key ):
            
            tag_context = ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
            
        
        self._last_prefetch_job_status = None
        
        self._current_context_tags = {}
        
        super().__init__( parent )
        
        self._location_context_button = ClientGUILocation.LocationSearchContextButton( self._dropdown_window, location_context, is_paired_with_tag_domain = True )
        self._location_context_button.setMinimumWidth( 20 )
        
        self._tag_context_button = ClientGUISearch.TagContextButton( self._dropdown_window, tag_context )
        self._tag_context_button.setMinimumWidth( 20 )
        
        self._search_results_list.SetTagServiceKey( tag_context.service_key )
        
        self._favourites_list = self._InitFavouritesList()
        
        if self._favourites_list is not None:
            
            self.RefreshFavouriteTags()
            
            self._dropdown_notebook.addTab( self._favourites_list, 'favourites' )
            
        
        self._children_list = self._InitChildrenList()
        
        if self._children_list is not None:
            
            self._dropdown_notebook.addTab( self._children_list, 'children' )
            
        
        #
        
        self._location_context_button.locationChanged.connect( self._LocationContextJustChanged )
        self._tag_context_button.valueChanged.connect( self._TagContextJustChanged )
        
        CG.client_controller.sub( self, 'RefreshFavouriteTags', 'notify_new_favourite_tags' )
        CG.client_controller.sub( self, 'NotifyNewServices', 'notify_new_services' )
        
        self._dropdown_notebook.currentChanged.connect( self._UpdateChildrenListIfNeeded )
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        raise NotImplementedError()
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> ClientSearchPredicate.Predicate | None:
        
        raise NotImplementedError()
        
    
    def _BroadcastCurrentInputFromEnterKey( self, shift_down ):
        
        raise NotImplementedError()
        
    
    def _GetParsedAutocompleteText( self ) -> ClientSearchAutocomplete.ParsedAutocompleteText:
        
        collapse_search_characters = True
        
        tag_service_key = self._tag_context_button.GetValue().service_key
        
        tag_autocomplete_options = CG.client_controller.tag_display_manager.GetTagAutocompleteOptions( tag_service_key )
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( self._text_ctrl.text(), tag_autocomplete_options, collapse_search_characters )
        
        return parsed_autocomplete_text
        
    
    def _InitChildrenList( self ) -> ChildrenTab | None:
        
        tag_service_key = self._tag_context_button.GetValue().service_key
        
        return ChildrenTab( self._dropdown_notebook, self.BroadcastChoices, self._float_mode, self._location_context_button.GetValue(), tag_service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = 4 )
        
    
    def _InitFavouritesList( self ) -> ListBoxTagsPredicatesAC | ListBoxTagsStringsAC | None:
        
        return None
        
    
    def _InitSearchResultsList( self ):
        
        raise NotImplementedError()
        
    
    def _LocationContextJustChanged( self, location_context: ClientLocation.LocationContext ):
        
        self._RestoreTextCtrlFocus()
        
        tag_service_key = self._tag_context_button.GetValue().service_key
        
        if location_context.IsAllKnownFiles() and tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            top_local_tag_service_key = CG.client_controller.services_manager.GetDefaultLocalTagService().GetServiceKey()
            
            self._tag_context_button.SetTagServiceKey( top_local_tag_service_key )
            
        
        if self._children_list is not None:
            
            self._children_list.SetLocationContext( location_context )
            
        
        self._NotifyChildrenListNeedsUpdating()
        
        self.locationChanged.emit( location_context )
        
        self._SetListDirty()
        
    
    def _NotifyChildrenListNeedsUpdating( self ):
        
        if self._children_list is not None:
            
            self._children_list.NotifyNeedsUpdating()
            
        
        self._UpdateChildrenListIfNeeded()
        
    
    def _SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        location_context = location_context.Duplicate()
        
        location_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        if location_context == self._location_context_button.GetValue():
            
            return
            
        
        tag_service_key = self._tag_context_button.GetValue().service_key
        
        if location_context.IsAllKnownFiles() and tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            local_tag_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
            
            self._tag_context_button.SetTagServiceKey( local_tag_services[0].GetServiceKey() )
            
        
        self._location_context_button.SetValue( location_context )
        
    
    def _SetResultsToList( self, results, parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText, preserve_single_selection = False ):
        
        AutoCompleteDropdown._SetResultsToList( self, results, parsed_autocomplete_text )
        
        self._search_results_list.SetPredicates( results, preserve_single_selection = preserve_single_selection )
        
        self._current_list_parsed_autocomplete_text = parsed_autocomplete_text
        
    
    def _SetTagContext( self, tag_context: ClientSearchTagContext.TagContext ):
        
        if not CG.client_controller.services_manager.ServiceExists( tag_context.service_key ):
            
            tag_context.service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        if tag_context.service_key == CC.COMBINED_TAG_SERVICE_KEY and self._location_context_button.GetValue().IsAllKnownFiles():
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._SetLocationContext( default_location_context )
            
        
        existing_tag_context = self._tag_context_button.GetValue()
        
        if tag_context == existing_tag_context:
            
            return False
            
        
        self._tag_context_button.SetValue( tag_context )
        
        return True
        
    
    def _ShouldBroadcastCurrentInputOnEnterKey( self ):
        
        raise NotImplementedError()
        
    
    def _StartSearchResultsFetchJob( self, job_status ):
        
        raise NotImplementedError()
        
    
    def _TagContextJustChanged( self, tag_context: ClientSearchTagContext.TagContext ):
        
        self._RestoreTextCtrlFocus()
        
        tag_service_key = tag_context.service_key
        
        if not CG.client_controller.services_manager.ServiceExists( tag_service_key ):
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY and self._location_context_button.GetValue().IsAllKnownFiles():
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._SetLocationContext( default_location_context )
            
        
        self._search_results_list.SetTagServiceKey( tag_service_key )
        
        if self._favourites_list is not None:
            
            self._favourites_list.SetTagServiceKey( tag_service_key )
            
        
        if self._children_list is not None:
            
            self._children_list.SetTagServiceKey( tag_service_key )
            
        
        self._NotifyChildrenListNeedsUpdating()
        
        self.tagContextChanged.emit( self._tag_context_button.GetValue() )
        
        self._SetListDirty()
        
        return True
        
    
    def _UpdateChildrenListIfNeeded( self ):
        
        if self._children_list is None:
            
            return
            
        
        if self._dropdown_notebook.currentWidget() == self._children_list:
            
            self._children_list.UpdateChildrenIfNeeded( set( self._current_context_tags ) )
            
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._location_context_button.GetValue()
        
    
    def NotifyNewServices( self ):
        
        self._SetLocationContext( self._location_context_button.GetValue() )
        self._SetTagContext( self._tag_context_button.GetValue() )
        
    
    def RefreshFavouriteTags( self ):
        
        if self._favourites_list is None:
            
            return
            
        
        favourite_tags = sorted( CG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
        
        predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, value = tag ) for tag in favourite_tags ]
        
        self._favourites_list.SetPredicates( predicates )
        
    
    def SetFetchedResults( self, job_status: ClientThreading.JobStatus, parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText, results_cache: ClientSearchAutocomplete.PredicateResultsCache, results: list ):
        
        if self._current_fetch_job_status is not None and self._current_fetch_job_status.GetKey() == job_status.GetKey():
            
            preserve_single_selection = False
            
            if self._last_prefetch_job_status == self._current_fetch_job_status:
                
                # we are completing a prefetch, so see if we can preserve if the user moved position
                preserve_single_selection = True
                
            
            if self._results_cache == results_cache and len( self._search_results_list ) >= len( results ):
                
                # if we are filtering down existing results, then preserve selection
                # don't preserve on user backspace, filtering up, it is confusing
                preserve_single_selection = True
                
            
            self._CancelSearchResultsFetchJob()
            
            self._results_cache = results_cache
            
            self._SetResultsToList( results, parsed_autocomplete_text, preserve_single_selection = preserve_single_selection )
            
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._SetLocationContext( location_context )
        
    
    def SetPrefetchResults( self, job_status: ClientThreading.JobStatus, predicates: list[ ClientSearchPredicate.Predicate ], parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText ):
        
        if self._current_fetch_job_status is not None and self._current_fetch_job_status.GetKey() == job_status.GetKey():
            
            self._last_prefetch_job_status = self._current_fetch_job_status
            
            self._SetResultsToList( predicates, parsed_autocomplete_text, preserve_single_selection = False )
            
        
    
    def SetContextTags( self, tags: collections.abc.Collection[ str ] ):
        """
        The search context or the taglist we are editing just changed, so let's tell anything in here that wants to filter or do lookups based on that.
        """
        
        self._current_context_tags = set( tags )
        
        self._NotifyChildrenListNeedsUpdating()
        
    
    def SetTagServiceKey( self, tag_service_key ):
        
        self._tag_context_button.SetTagServiceKey( tag_service_key )
        
    

class AutoCompleteDropdownTagsFileSearchContext( AutoCompleteDropdownTags ):
    
    def __init__(
        self,
        parent: QW.QWidget,
        location_context: ClientLocation.LocationContext,
        tag_context: ClientSearchTagContext.TagContext,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext
    ):
        
        self._file_search_context = file_search_context.Duplicate()
        
        super().__init__( parent, location_context, tag_context )
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        raise NotImplementedError()
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> ClientSearchPredicate.Predicate | None:
        
        raise NotImplementedError()
        
    
    def _BroadcastCurrentInputFromEnterKey( self, shift_down ):
        
        raise NotImplementedError()
        
    
    def _TagContextJustChanged( self, tag_context: ClientSearchTagContext.TagContext ):
        
        it_changed = super()._TagContextJustChanged( tag_context )
        
        if it_changed:
            
            self._file_search_context.SetTagContext( tag_context )
            
        
        return it_changed
        
    
    def GetFileSearchContext( self ) -> ClientSearchFileSearchContext.FileSearchContext:
        
        return self._file_search_context.Duplicate()
        
    
    def SetFileSearchContext( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext ):
        
        self._file_search_context = file_search_context.Duplicate()
        
    

class AutocompleteDropdownTagsFileSearchContextORCapable( AutoCompleteDropdownTagsFileSearchContext ):
    
    def __init__(
        self,
        parent: QW.QWidget,
        location_context: ClientLocation.LocationContext,
        tag_context: ClientSearchTagContext.TagContext,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        page_key: bytes, # remove me, I shouldn't be here
        for_metadata_conditional: bool # also not great!!
    ):
        
        self._page_key = page_key
        self._for_metadata_conditional = for_metadata_conditional
        
        super().__init__( parent, location_context, tag_context, file_search_context )
        
        self._under_construction_or_predicate = None
        
        self._or_basic = ClientGUICommon.BetterButton( self._dropdown_window, 'OR', self._CreateNewOR )
        self._or_basic.setToolTip( ClientGUIFunctions.WrapToolTip( 'Create a new empty OR predicate in the dialog.' ) )
        
        self._or_cancel = ClientGUICommon.IconButton( self._dropdown_window, CC.global_icons().delete, self._CancelORConstruction )
        self._or_cancel.setToolTip( ClientGUIFunctions.WrapToolTip( 'Cancel OR Predicate construction.' ) )
        self._or_cancel.hide()
        
        self._or_rewind = ClientGUICommon.IconButton( self._dropdown_window, CC.global_icons().position_previous, self._RewindORConstruction )
        self._or_rewind.setToolTip( ClientGUIFunctions.WrapToolTip( 'Rewind OR Predicate construction.' ) )
        self._or_rewind.hide()
        
    
    def _BroadcastCurrentInputFromEnterKey( self, shift_down ):
        
        raise NotImplementedError()
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        or_pred_in_broadcast = self._under_construction_or_predicate is not None and self._under_construction_or_predicate in predicates
        
        if shift_down:
            
            if self._under_construction_or_predicate is None:
                
                self._under_construction_or_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = predicates )
                
            else:
                
                if or_pred_in_broadcast:
                    
                    predicates.remove( self._under_construction_or_predicate )
                    
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                or_preds.extend( [ predicate for predicate in predicates if predicate not in or_preds ] )
                
                self._under_construction_or_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = or_preds )
                
            
        else:
            
            if or_pred_in_broadcast:
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                if len( or_preds ) == 1:
                    
                    predicates.remove( self._under_construction_or_predicate )
                    
                    predicates.extend( or_preds )
                    
                
            elif self._under_construction_or_predicate is not None:
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                or_preds.extend( [ predicate for predicate in predicates if predicate not in or_preds ] )
                
                predicates = { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = or_preds ) }
                
            
            self._under_construction_or_predicate = None
            
            self._predicates_listbox.EnterPredicates( self._page_key, predicates )
            
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
    
    def _CancelORConstruction( self ):
        
        self._under_construction_or_predicate = None
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
        ClientGUIFunctions.SetFocusLater( self._text_ctrl )
        
    
    def _CreateNewOR( self ):
        
        predicates = { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = [] ) }
        
        try:
            
            empty_file_search_context = self._file_search_context.Duplicate()
            
            empty_file_search_context.SetPredicates( [] )
            
            predicates = ClientGUISearch.EditPredicates( self, predicates, empty_file_search_context = empty_file_search_context, for_metadata_conditional = self._for_metadata_conditional )
            
        except HydrusExceptions.CancelledException:
            
            ClientGUIFunctions.SetFocusLater( self._text_ctrl )
            
            return
            
        
        shift_down = False
        
        self._BroadcastChoices( predicates, shift_down )
        
        ClientGUIFunctions.SetFocusLater( self._text_ctrl )
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> ClientSearchPredicate.Predicate | None:
        
        raise NotImplementedError()
        
    
    def _HandleEscape( self ):
        
        if self._under_construction_or_predicate is not None and self._text_ctrl.text() == '':
            
            or_preds = self._under_construction_or_predicate.GetValue()
            
            if len( or_preds ) > 1:
                
                self._RewindORConstruction()
                
            else:
                
                self._CancelORConstruction()
                
            
            return True
            
        else:
            
            return super()._HandleEscape()
            
        
    
    def _RewindORConstruction( self ):
        
        if self._under_construction_or_predicate is not None:
            
            or_preds = self._under_construction_or_predicate.GetValue()
            
            if len( or_preds ) <= 1:
                
                self._CancelORConstruction()
                
                return
                
            
            or_preds = or_preds[:-1]
            
            self._under_construction_or_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = or_preds )
            
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
        ClientGUIFunctions.SetFocusLater( self._text_ctrl )
        
    
    def _SetupTopListBox( self ):
        
        # TODO: this call shouldn't be here, but it was convenient when doing metadata conditional OR support rewrite
        #  rewangle predicates_listbox stuff out of the OR subclass, make the broadcastchoices stuff a QC.Signal, clean it all up 
        
        self._predicates_listbox = ListBoxTagsActiveSearchPredicates( self, self._page_key, self._file_search_context, self._for_metadata_conditional )
        
        QP.AddToLayout( self._main_vbox, self._predicates_listbox, CC.FLAGS_EXPAND_BOTH_WAYS_SHY )
        
    
    def _UpdateORButtons( self ):
        
        if self._under_construction_or_predicate is None:
            
            if self._or_cancel.isVisible():
                
                self._or_cancel.hide()
                
            
            if self._or_rewind.isVisible():
                
                self._or_rewind.hide()
                
            
        else:
            
            or_preds = self._under_construction_or_predicate.GetValue()
            
            if len( or_preds ) > 1:
                
                if not self._or_rewind.isVisible():
                    
                    self._or_rewind.show()
                    
                
            else:
                
                if self._or_rewind.isVisible():
                    
                    self._or_rewind.hide()
                    
                
            
            if not self._or_cancel.isVisible():
                
                self._or_cancel.show()
            
        
    

class AutoCompleteDropdownTagsRead( AutocompleteDropdownTagsFileSearchContextORCapable ):
    
    searchChanged = QC.Signal( ClientSearchFileSearchContext.FileSearchContext )
    searchCancelled = QC.Signal()
    lockSearch = QC.Signal()
    
    def __init__(
        self,
        parent: QW.QWidget,
        page_key,
        file_search_context: ClientSearchFileSearchContext.FileSearchContext,
        media_sort_widget: ClientGUIMediaResultsPanelSortCollect.MediaSortControl | None = None,
        media_collect_widget: ClientGUIMediaResultsPanelSortCollect.MediaCollectControl | None = None,
        media_callable = None,
        synchronised = True,
        include_unusual_predicate_types = True,
        allow_all_known_files = True,
        only_allow_local_file_domains = False,
        only_allow_combined_local_file_domains = False,
        allow_multiple_file_domains = True,
        force_system_everything = False,
        hide_favourites_edit_actions = False,
        fixed_results_list_height = None,
        show_lock_search_button = False
    ):
        
        # make a dupe here so we know that any direct changes we make to this guy will not affect other copies around
        file_search_context = file_search_context.Duplicate()
        
        location_context = file_search_context.GetLocationContext()
        tag_context = file_search_context.GetTagContext()
        
        self._include_unusual_predicate_types = include_unusual_predicate_types
        self._force_system_everything = force_system_everything
        self._hide_favourites_edit_actions = hide_favourites_edit_actions
        
        # '*•.¸¸.•*' Debug In Memoriam '*•.¸¸.•*'
        # self.widget().children()[3].children()[0].children()[0].children()[0].children()[2].children()[0].children()[0].children()[0].children()[0].sizeHint()
        self._fixed_results_list_height = fixed_results_list_height
        
        self._media_sort_widget = media_sort_widget
        self._media_collect_widget = media_collect_widget
        
        self._media_callable = media_callable
        for_metadata_conditional = False
        
        super().__init__( parent, location_context, tag_context, file_search_context, page_key, for_metadata_conditional )
        
        self._location_context_button.SetMultipleFileDomainsAllowed( allow_multiple_file_domains )
        self._location_context_button.SetOnlyLocalFileDomainsAllowed( only_allow_local_file_domains )
        self._location_context_button.SetOnlyCombinedLocalFileDomainsAllowed( only_allow_combined_local_file_domains )
        self._location_context_button.SetAllKnownFilesAllowed( allow_all_known_files, True )
        
        #
        
        self._cancel_search_button = ClientGUICommon.IconButton( self._text_input_panel, CC.global_icons().stop, self.searchCancelled.emit )
        
        self._paste_button = ClientGUICommon.IconButton( self._text_input_panel, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can paste a newline-separated list of regular tags and/or system predicates.' ) )
        
        self._favourite_searches_button = ClientGUICommon.IconButton( self._text_input_panel, CC.global_icons().star, self._FavouriteSearchesMenu )
        self._favourite_searches_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Load or save a favourite search.' ) )
        
        self._empty_search_button = ClientGUICommon.IconButton( self._text_input_panel, CC.global_icons().clear_highlight, self._ClearSearch )
        self._empty_search_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Clear the search back to an empty page.' ) )
        
        self._lock_search_button = ClientGUICommon.IconButton( self._text_input_panel, CC.global_icons().lock, self.lockSearch.emit )
        self._lock_search_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Lock the current files in view to a fixed system:hash.' ) )
        
        self._cancel_search_button.hide()
        self._lock_search_button.setVisible( show_lock_search_button )
        
        QP.AddToLayout( self._text_input_hbox, self._cancel_search_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._text_input_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._text_input_hbox, self._favourite_searches_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._text_input_hbox, self._empty_search_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._text_input_hbox, self._lock_search_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        #
        
        self._include_current_tags = ClientGUICommon.OnOffButton( self._dropdown_window, on_label = 'include current tags', off_label = 'exclude current tags', start_on = tag_context.include_current_tags )
        self._include_current_tags.setToolTip( ClientGUIFunctions.WrapToolTip( 'select whether to include current tags in the search' ) )
        self._include_pending_tags = ClientGUICommon.OnOffButton( self._dropdown_window, on_label = 'include pending tags', off_label = 'exclude pending tags', start_on = tag_context.include_pending_tags )
        self._include_pending_tags.setToolTip( ClientGUIFunctions.WrapToolTip( 'select whether to include pending tags in the search' ) )
        
        self._search_pause_play = ClientGUICommon.OnOffButton( self._dropdown_window, on_label = 'searching immediately', off_label = 'search paused', start_on = synchronised )
        self._search_pause_play.setToolTip( ClientGUIFunctions.WrapToolTip( 'select whether to renew the search as soon as a new predicate is entered' ) )
        
        self._or_advanced = ClientGUICommon.BetterButton( self._dropdown_window, 'advanced', self._AdvancedORInput )
        self._or_advanced.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can paste complicated predicate strings in here and it will parse into proper logic.' ) )
        
        if not CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._or_advanced.hide()
            
        
        button_hbox_1 = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox_1, self._include_current_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox_1, self._include_pending_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        sync_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( sync_button_hbox, self._search_pause_play, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( sync_button_hbox, self._or_basic, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( sync_button_hbox, self._or_advanced, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( sync_button_hbox, self._or_cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( sync_button_hbox, self._or_rewind, CC.FLAGS_CENTER_PERPENDICULAR )
        
        button_hbox_2 = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox_2, self._location_context_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox_2, self._tag_context_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, button_hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, sync_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, button_hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.setLayout( vbox )
        
        self._predicates_listbox.listBoxChanged.connect( self._NotifyPredicatesBoxChanged )
        
        self._include_current_tags.valueChanged.connect( self._tag_context_button.SetIncludeCurrent )
        self._include_pending_tags.valueChanged.connect( self._tag_context_button.SetIncludePending )
        self._search_pause_play.valueChanged.connect( self._SynchronisedChanged )
        
        predicates = self._file_search_context.GetPredicates()
        
        tags = [ predicate.GetValue() for predicate in predicates if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_TAG ]
        
        self.SetContextTags( tags )
        
        self.externalCopyKeyPressEvent.connect( self._predicates_listbox.keyPressEvent )
        
    
    def _AdvancedORInput( self ):
        
        title = 'parse advanced predicate string'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = EditAdvancedORPredicates( dlg )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                predicates = panel.GetValue()
                shift_down = False
                
                if len( predicates ) > 0:
                    
                    self._BroadcastChoices( predicates, shift_down )
                    
                
            
        
        ClientGUIFunctions.SetFocusLater( self._text_ctrl )
        
    
    def _BroadcastCurrentInputFromEnterKey( self, shift_down ):
        
        current_broadcast_predicate = self._GetCurrentBroadcastTextPredicate()
        
        if current_broadcast_predicate is not None:
            
            self._BroadcastChoices( { current_broadcast_predicate }, shift_down )
            
        
    
    def _ClearSearch( self ):
        
        location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        tag_context = ClientSearchTagContext.TagContext()
        
        predicates = []
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = predicates )
        
        synchronised = True
        media_sort = None
        media_collect = None
        
        self.blockSignals( True )
        
        self.SetFileSearchContext( file_search_context )
        
        if media_sort is not None and self._media_sort_widget is not None:
            
            self._media_sort_widget.SetSort( media_sort )
            
        
        if media_collect is not None and self._media_collect_widget is not None:
            
            self._media_collect_widget.SetCollect( media_collect )
            
        
        self._search_pause_play.SetOnOff( synchronised )
        
        self.blockSignals( False )
        
        self.locationChanged.emit( self._location_context_button.GetValue() )
        self.tagContextChanged.emit( self._tag_context_button.GetValue() )
        
        self._SignalNewSearchState()
        
    
    def _FavouriteSearchesMenu( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if not self._hide_favourites_edit_actions:
            
            ClientGUIMenus.AppendMenuItem( menu, 'manage favourite searches', 'Open a dialog to edit your favourite searches.', self._ManageFavouriteSearches )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'save this search', 'Save this search for later.', self._SaveFavouriteSearch )
            
        
        # what the hell, this will work for now
        # I am bodging this weird 'string and None' system to support '/' for nested menu structure, let's go
        nested_folders_to_names = CG.client_controller.favourite_search_manager.GetNestedFoldersToNames()
        
        if len( nested_folders_to_names ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            def populate_a_folder( folder_menu, folder_dict ):
                
                subfolder_names = list( folder_dict.keys() )
                
                if None in subfolder_names:
                    
                    subfolder_names.remove( None )
                    
                    folder_names_and_names_on_this_level = folder_dict[ None ]
                    
                    # trust me on the key lambda, in some annoying situations the folder name can be none or '/'
                    for ( full_folder_name, name ) in sorted( folder_names_and_names_on_this_level, key = lambda a: a[1] ):
                        
                        ClientGUIMenus.AppendMenuItem( folder_menu, name, 'Load the {} search.'.format( name ), self._LoadFavouriteSearch, full_folder_name, name )
                        
                    
                
                subfolder_names.sort()
                
                for subfolder_name in subfolder_names:
                    
                    subfolder_menu = ClientGUIMenus.GenerateMenu( menu )
                    
                    ClientGUIMenus.AppendMenu( folder_menu, subfolder_menu, subfolder_name )
                    
                    subfolder_dict = folder_dict[ subfolder_name ]
                    
                    populate_a_folder( subfolder_menu, subfolder_dict )
                    
                
            
            populate_a_folder( menu, nested_folders_to_names )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> ClientSearchPredicate.Predicate | None:
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        if parsed_autocomplete_text.IsAcceptableForFileSearches():
            
            allow_auto_wildcard_conversion = True
            
            return parsed_autocomplete_text.GetImmediateFileSearchPredicate( allow_auto_wildcard_conversion )
            
        else:
            
            return None
            
        
    
    def _InitFavouritesList( self ) -> ListBoxTagsPredicatesAC:
        
        if self._fixed_results_list_height is None:
            
            height_num_chars = CG.client_controller.new_options.GetInteger( 'ac_read_list_height_num_chars' )
            
        else:
            
            height_num_chars = self._fixed_results_list_height
            
        
        tag_service_key = self._file_search_context.GetTagContext().service_key
        
        favs_list = ListBoxTagsPredicatesAC( self._dropdown_notebook, self.BroadcastChoices, self._float_mode, tag_service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = height_num_chars )
        
        return favs_list
        
    
    def _InitSearchResultsList( self ):
        
        if self._fixed_results_list_height is None:
            
            height_num_chars = CG.client_controller.new_options.GetInteger( 'ac_read_list_height_num_chars' )
            
        else:
            
            height_num_chars = self._fixed_results_list_height
            
        
        tag_service_key = self._file_search_context.GetTagContext().service_key
        
        return ListBoxTagsPredicatesAC( self._dropdown_notebook, self.BroadcastChoices, self._float_mode, tag_service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = height_num_chars )
        
    
    def _LocationContextJustChanged( self, location_context: ClientLocation.LocationContext ):
        
        super()._LocationContextJustChanged( location_context )
        
        self._file_search_context.SetLocationContext( location_context )
        
        self._SignalNewSearchState()
        
    
    def _LoadFavouriteSearch( self, folder_name, name ):
        
        ( file_search_context, synchronised, media_sort, media_collect ) = CG.client_controller.favourite_search_manager.GetFavouriteSearch( folder_name, name )
        
        self.blockSignals( True )
        
        self.SetFileSearchContext( file_search_context )
        
        if media_sort is not None and self._media_sort_widget is not None:
            
            self._media_sort_widget.SetSort( media_sort )
            
        
        if media_collect is not None and self._media_collect_widget is not None:
            
            self._media_collect_widget.SetCollect( media_collect )
            
        
        self._search_pause_play.SetOnOff( synchronised )
        
        self.blockSignals( False )
        
        self.locationChanged.emit( self._location_context_button.GetValue() )
        self.tagContextChanged.emit( self._tag_context_button.GetValue() )
        
        self._SignalNewSearchState()
        
    
    def _ManageFavouriteSearches( self, favourite_search_row_to_save = None ):
        
        from hydrus.client.gui.search import ClientGUISearchPanels
        
        favourite_searches_rows = CG.client_controller.favourite_search_manager.GetFavouriteSearchRows()
        
        title = 'edit favourite searches'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUISearchPanels.EditFavouriteSearchesPanel( dlg, favourite_searches_rows, initial_search_row_to_edit = favourite_search_row_to_save )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_favourite_searches_rows = panel.GetValue()
                
                CG.client_controller.favourite_search_manager.SetFavouriteSearchRows( edited_favourite_searches_rows )
                
            
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            texts = HydrusText.DeserialiseNewlinedTexts( raw_text )
            
            predicates = []
            
            for text in texts:
                
                try:
                    
                    tag_service_key = self._tag_context_button.GetValue().service_key
                    
                    tag_autocomplete_options = CG.client_controller.tag_display_manager.GetTagAutocompleteOptions( tag_service_key )
                    
                    collapse_search_characters = True
                    
                    pat = ClientSearchAutocomplete.ParsedAutocompleteText( text, tag_autocomplete_options, collapse_search_characters = collapse_search_characters )
                    
                    if pat.IsAcceptableForFileSearches():
                        
                        predicates.append( pat.GetImmediateFileSearchPredicate( allow_auto_wildcard_conversion = True ) )
                        
                    
                except Exception as e:
                    
                    continue
                    
                
            
            if len( predicates ) > 0:
                
                shift_down = False
                
                self._BroadcastChoices( predicates, shift_down )
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of tags', e )
            
        
    
    def _RestoreTextCtrlFocus( self ):
        
        # if an event came from clicking the dropdown or stop or something, we want to put focus back on textctrl
        current_focus_widget = QW.QApplication.focusWidget()
        
        if current_focus_widget != self._favourite_searches_button:
            
            super()._RestoreTextCtrlFocus()
            
        
    
    def _SaveFavouriteSearch( self ):
        
        foldername = None
        name = 'new favourite search'
        file_search_context = self.GetFileSearchContext()
        synchronised = self.IsSynchronised()
        
        if self._media_sort_widget is None:
            
            media_sort = None
            
        else:
            
            media_sort = self._media_sort_widget.GetSort()
            
        
        if self._media_collect_widget is None:
            
            media_collect = None
            
        else:
            
            media_collect = self._media_collect_widget.GetValue()
            
        
        search_row = ( foldername, name, file_search_context, synchronised, media_sort, media_collect )
        
        self._ManageFavouriteSearches( favourite_search_row_to_save = search_row )
        
    
    def _NotifyPredicatesBoxChanged( self ):
        
        predicates = self._predicates_listbox.GetPredicates()
        
        self._file_search_context.SetPredicates( predicates )
        
        tags = [ predicate.GetValue() for predicate in predicates if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_TAG ]
        
        self.SetContextTags( tags )
        
        self._SignalNewSearchState()
        
    
    def _SetTagContext( self, tag_context: ClientSearchTagContext.TagContext ):
        
        it_changed = super()._SetTagContext( tag_context )
        
        if it_changed:
            
            self._include_current_tags.SetOnOff( tag_context.include_current_tags )
            self._include_pending_tags.SetOnOff( tag_context.include_pending_tags )
            
        
        return it_changed
        
    
    def _ShouldBroadcastCurrentInputOnEnterKey( self ):
        
        looking_at_search_results = self._dropdown_notebook.currentWidget() == self._search_results_list
        
        something_to_broadcast = self._GetCurrentBroadcastTextPredicate() is not None
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        # the list has results, but they are out of sync with what we have currently entered
        # when the user has quickly typed something in and the results are not yet in
        results_desynced_with_text = parsed_autocomplete_text != self._current_list_parsed_autocomplete_text
        
        p1 = looking_at_search_results and something_to_broadcast and results_desynced_with_text
        
        return p1
        
    
    def _SignalNewSearchState( self ):
        
        file_search_context = self._file_search_context.Duplicate()
        
        self.searchChanged.emit( file_search_context )
        
    
    def _StartSearchResultsFetchJob( self, job_status ):
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        fsc = self.GetFileSearchContext()
        
        if self._under_construction_or_predicate is None:
            
            under_construction_or_predicate = None
            
        else:
            
            under_construction_or_predicate = self._under_construction_or_predicate.Duplicate()
            
        
        CG.client_controller.CallToThread( ReadFetch, self, job_status, self.SetPrefetchResults, self.SetFetchedResults, parsed_autocomplete_text, self._media_callable, fsc, self._search_pause_play.IsOn(), self._include_unusual_predicate_types, self._results_cache, under_construction_or_predicate, self._force_system_everything )
        
    
    def _SynchronisedChanged( self, value ):
        
        self._SignalNewSearchState()
        
        self._RestoreTextCtrlFocus()
        
        if not self._search_pause_play.IsOn() and not self._file_search_context.GetSystemPredicates().HasSystemLimit():
            
            # update if user goes from sync to non-sync
            self._SetListDirty()
            
        
    
    def _TagContextJustChanged( self, tag_context: ClientSearchTagContext.TagContext ):
        
        it_changed = super()._TagContextJustChanged( tag_context )
        
        if it_changed:
            
            self._SignalNewSearchState()
            
        
        return it_changed
        
    
    def ActivateFavouriteSearch( self, fav_search: tuple[ str, str ] ):
        
        ( folder_name, name ) = fav_search
        
        self._LoadFavouriteSearch( folder_name, name )
        
    
    def EnterPredicates( self, page_key, predicates: set[ ClientSearchPredicate.Predicate ] ):
        
        if page_key == self._page_key:
            
            self._predicates_listbox.EnterPredicates( page_key, predicates )
            
        
    
    def GetPredicates( self ) -> set[ ClientSearchPredicate.Predicate ]:
        
        return self._file_search_context.GetPredicates()
        
    
    def IsSynchronised( self ):
        
        return self._search_pause_play.IsOn()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if self._can_intercept_unusual_key_events and command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_SYNCHRONISED_WAIT_SWITCH:
                
                self.PausePlaySearch()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = super().ProcessApplicationCommand( command )
            
        
        return command_processed
        
    
    def SetFileSearchContext( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext ):
        
        self._ClearInput()
        
        self._CancelORConstruction()
        
        super().SetFileSearchContext( file_search_context )
        
        self._predicates_listbox.SetFileSearchContext( self._file_search_context )
        
        self._SetLocationContext( self._file_search_context.GetLocationContext() )
        self._SetTagContext( self._file_search_context.GetTagContext() )
        
        self._SignalNewSearchState()
        
    
    def SetIncludeCurrent( self, value: bool ):
        
        self._include_current_tags.SetOnOff( value )
        
    
    def SetIncludePending( self, value: bool ):
        
        self._include_pending_tags.SetOnOff( value )
        
    
    def SetSynchronised( self, value: bool ):
        
        self._search_pause_play.SetOnOff( value )
        
    
    def PausePlaySearch( self ):
        
        self._search_pause_play.Flip()
        
        self._RestoreTextCtrlFocus()
        
    
    def ShowCancelSearchButton( self, show ):
        
        if self._cancel_search_button.isVisible() != show:
            
            self._cancel_search_button.setVisible( show )
            
        
    

class ListBoxTagsActiveSearchPredicates( ClientGUIListBoxes.ListBoxTagsPredicates ):
    
    def __init__( self, parent: AutocompleteDropdownTagsFileSearchContextORCapable, page_key, file_search_context: ClientSearchFileSearchContext.FileSearchContext, for_metadata_conditional: bool ):
        
        height_num_chars = CG.client_controller.new_options.GetInteger( 'active_search_predicates_height_num_chars' )
        
        super().__init__( parent, height_num_chars = height_num_chars )
        
        self._my_ac_parent = parent
        
        self._page_key = page_key
        
        self._file_search_context = file_search_context
        self._for_metadata_conditional = for_metadata_conditional
        
        initial_predicates = self._file_search_context.GetPredicates()
        
        if len( initial_predicates ) > 0:
            
            terms = [ self._GenerateTermFromPredicate( predicate ) for predicate in initial_predicates ]
            
            self._AppendTerms( terms )
            
            self._Sort()
            
            self._DataHasChanged()
            
        
        CG.client_controller.sub( self, 'EnterPredicates', 'enter_predicates' )
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        
        if len( predicates ) > 0:
            
            if shift_down:
                
                self._EditPredicates( set( predicates ) )
                
            elif ctrl_down:
                
                ( predicates, or_predicate, inverse_predicates, namespace_predicate, inverse_namespace_predicate ) = self._GetSelectedPredicatesAndInverseCopies()
                
                self._EnterPredicates( inverse_predicates )
                
            else:
                
                self._EnterPredicates( set( predicates ) )
                
            
            return True
            
        
        return False
        
    
    def _AddEditMenu( self, menu: QW.QMenu ):
        
        ( editable_predicates, only_invertible_predicates, non_editable_predicates ) = ClientGUISearch.GetEditablePredicates( self._GetPredicatesFromTerms( self._selected_terms ) )
        
        if len( editable_predicates ) > 0:
            
            editable_and_invertible_predicates = list( editable_predicates )
            editable_and_invertible_predicates.extend( only_invertible_predicates )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if len( editable_and_invertible_predicates ) == 1:
                
                desc = list( editable_and_invertible_predicates )[0].ToString()
                
            else:
                
                desc = '{} search terms'.format( HydrusNumbers.ToHumanInt( len( editable_and_invertible_predicates ) ) )
                
            
            label = 'edit {}'.format( desc )
            
            ClientGUIMenus.AppendMenuItem( menu, label, 'Edit these predicates and refresh the search. Not all predicates are editable.', self._EditPredicates, editable_and_invertible_predicates )
            
        
    
    def _CanProvideCurrentPagePredicates( self ):
        
        return True
        
    
    def _DeleteActivate( self ):
        
        ctrl_down = False
        shift_down = False
        
        self._Activate( ctrl_down, shift_down )
        
    
    def _EditPredicates( self, predicates ):
        
        original_predicates = set( predicates )
        
        try:
            
            empty_file_search_context = self._file_search_context.Duplicate()
            
            empty_file_search_context.SetPredicates( [] )
            
            edited_predicates = set( ClientGUISearch.EditPredicates( self, predicates, empty_file_search_context = empty_file_search_context, for_metadata_conditional = self._for_metadata_conditional ) )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        non_edited_predicates = original_predicates.intersection( edited_predicates )
        
        predicates_to_add = edited_predicates.difference( non_edited_predicates )
        predicates_to_remove = original_predicates.difference( non_edited_predicates )
        
        if len( predicates_to_add ) + len( predicates_to_remove ) == 0:
            
            return
            
        
        terms_to_remove = [ self._GenerateTermFromPredicate( predicate ) for predicate in predicates_to_remove ]
        
        self._RemoveTerms( terms_to_remove )
        
        terms_to_add = [ self._GenerateTermFromPredicate( predicate ) for predicate in predicates_to_add ]
        
        self._AppendTerms( terms_to_add )
        
        self._selected_terms.update( terms_to_add )
        
        self._Sort()
        
        self._DataHasChanged()
        
    
    def _EnterPredicates( self, predicates, permit_add = True, permit_remove = True, start_or_predicate = False ):
        
        if len( predicates ) == 0:
            
            return
            
        
        if start_or_predicate:
            
            or_based_predicates = { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = list( predicates ) ) }
            
            try:
                
                empty_file_search_context = self._file_search_context.Duplicate()
                
                empty_file_search_context.SetPredicates( or_based_predicates )
                
                or_based_predicates = ClientGUISearch.EditPredicates( self, or_based_predicates, empty_file_search_context = empty_file_search_context, for_metadata_conditional = self._for_metadata_conditional )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._EnterPredicates( predicates, permit_add = False )
            self._EnterPredicates( or_based_predicates, permit_remove = False )
            
            return
            
        
        terms_to_be_added = set()
        terms_to_be_removed = set()
        
        terms_to_select = set()
        
        for predicate in predicates:
            
            predicate = predicate.GetCountlessCopy()
            
            term = self._GenerateTermFromPredicate( predicate )
            
            if term in self._terms_to_logical_indices:
                
                if permit_remove:
                    
                    terms_to_be_removed.add( term )
                    
                
            else:
                
                if permit_add:
                    
                    terms_to_be_added.add( term )
                    
                    m_e_preds = self._GetMutuallyExclusivePredicates( predicate )
                    
                    new_removees = [ self._GenerateTermFromPredicate( pred ) for pred in m_e_preds ]
                    
                    if True in ( t in self._selected_terms for t in new_removees ):
                        
                        terms_to_select.add( term )
                        
                    
                    terms_to_be_removed.update( new_removees )
                    
                
            
        
        self._AppendTerms( terms_to_be_added )
        
        self._RemoveTerms( terms_to_be_removed )
        
        self._Sort()
        
        if len( terms_to_select ) > 0:
            
            self._selected_terms.update( terms_to_select )
            
            earliest_guy = sorted( terms_to_select, key = lambda t: self._terms_to_logical_indices[ t ] )[0]
            
            self._Hit( False, False, self._terms_to_logical_indices[ earliest_guy ] )
            
        
        self._DataHasChanged()
        
    
    def _GetCurrentLocationContext( self ):
        
        return self._my_ac_parent.GetFileSearchContext().GetLocationContext()
        
    
    def _GetCurrentPagePredicates( self ) -> set[ ClientSearchPredicate.Predicate ]:
        
        return self.GetPredicates()
        
    
    def _HasCounts( self ):
        
        return False
        
    
    def _ProcessMenuPredicateEvent( self, command ):
        
        ( predicates, or_predicate, inverse_predicates, namespace_predicate, inverse_namespace_predicate ) = self._GetSelectedPredicatesAndInverseCopies()
        
        if command == 'add_predicates':
            
            self._EnterPredicates( predicates, permit_remove = False )
            
        elif command == 'add_or_predicate':
            
            if or_predicate is not None:
                
                self._EnterPredicates( ( or_predicate, ), permit_remove = False )
                
            
        elif command == 'dissolve_or_predicate':
            
            or_preds = [ p for p in predicates if p.IsORPredicate() ]
            
            sub_preds = HydrusLists.MassUnion( [ p.GetValue() for p in or_preds ] )
            
            self._EnterPredicates( or_preds, permit_add = False )
            self._EnterPredicates( sub_preds, permit_remove = False )
            
        elif command == 'replace_or_predicate':
            
            if or_predicate is not None:
                
                self._EnterPredicates( predicates, permit_add = False )
                self._EnterPredicates( ( or_predicate, ), permit_remove = False )
                
            
        elif command == 'start_or_predicate':
            
            self._EnterPredicates( predicates, start_or_predicate = True )
            
        elif command == 'remove_predicates':
            
            self._EnterPredicates( predicates, permit_add = False )
            
        elif command == 'add_inverse_predicates':
            
            self._EnterPredicates( inverse_predicates, permit_remove = False )
            
        elif command == 'add_namespace_predicate':
            
            self._EnterPredicates( ( namespace_predicate, ), permit_remove = False )
            
        elif command == 'add_inverse_namespace_predicate':
            
            self._EnterPredicates( ( inverse_namespace_predicate, ), permit_remove = False )
            
        
    
    def EnterPredicates( self, page_key, predicates, permit_add = True, permit_remove = True, start_or_predicate = False ):
        
        if page_key == self._page_key:
            
            self._EnterPredicates( predicates, permit_add = permit_add, permit_remove = permit_remove, start_or_predicate = start_or_predicate )
            
        
    
    def SetFileSearchContext( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext ):
        
        self._Clear()
        
        self._file_search_context = file_search_context
        
        predicates = self._file_search_context.GetPredicates()
        
        terms = [ self._GenerateTermFromPredicate( predicate ) for predicate in predicates ]
        
        self._AppendTerms( terms )
        
        self._Sort()
        
        self._DataHasChanged()
        
    

class AutoCompleteDropdownTagsWrite( AutoCompleteDropdownTags ):
    
    nullEntered = QC.Signal()
    tagsPasted = QC.Signal( list )
    
    def __init__(
        self,
        parent,
        chosen_tag_callable,
        location_context,
        tag_service_key,
        show_paste_button = False
    ):
        
        # don't touch this bro, trust me
        self._display_tag_service_key = tag_service_key
        self._show_paste_button = show_paste_button
        
        self._chosen_tag_callable = chosen_tag_callable
        
        tag_autocomplete_options = CG.client_controller.tag_display_manager.GetTagAutocompleteOptions( tag_service_key )
        
        ( location_context, tag_context ) = tag_autocomplete_options.GetWriteAutocompleteSearchDomain( location_context, self._display_tag_service_key )
        
        super().__init__( parent, location_context, tag_context )
        
        self._location_context_button.SetAllKnownFilesAllowed( True, False )
        
        self._paste_button = ClientGUICommon.IconButton( self._text_input_panel, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste from the clipboard and quick-enter as if you had typed. This can take multiple newline-separated tags.' ) )
        
        if not self._show_paste_button:
            
            self._paste_button.hide()
            
        
        QP.AddToLayout( self._text_input_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._location_context_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._tag_context_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.setLayout( vbox )
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        tags = { predicate.GetValue() for predicate in predicates }
        
        if len( tags ) > 0:
            
            self._chosen_tag_callable( tags )
            
        
        self._ClearInput()
        
    
    def _BroadcastCurrentInputFromEnterKey( self, shift_down ):
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        if parsed_autocomplete_text.IsEmpty() and self._dropdown_notebook.currentWidget() == self._search_results_list:
            
            self.nullEntered.emit()
            
        else:
            
            current_broadcast_predicate = self._GetCurrentBroadcastTextPredicate()
            
            if current_broadcast_predicate is not None:
                
                self._BroadcastChoices( { current_broadcast_predicate }, shift_down )
                
            
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> ClientSearchPredicate.Predicate | None:
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        allow_auto_wildcard_conversion = False
        
        if parsed_autocomplete_text.IsTagSearch( allow_auto_wildcard_conversion ):
            
            return parsed_autocomplete_text.GetImmediateFileSearchPredicate( allow_auto_wildcard_conversion )
            
        else:
            
            return None
            
        
    
    def _GetParsedAutocompleteText( self ) -> ClientSearchAutocomplete.ParsedAutocompleteText:
        
        parsed_autocomplete_text = super()._GetParsedAutocompleteText()
        
        parsed_autocomplete_text.SetInclusive( True )
        
        return parsed_autocomplete_text
        
    
    def _InitFavouritesList( self ) -> ListBoxTagsStringsAC:
        
        height_num_chars = CG.client_controller.new_options.GetInteger( 'ac_write_list_height_num_chars' )
        
        favs_list = ListBoxTagsStringsAC( self._dropdown_notebook, self.BroadcastChoices, self._display_tag_service_key, self._float_mode, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE, height_num_chars = height_num_chars )
        
        favs_list.SetExtraParentRowsAllowed( CG.client_controller.new_options.GetBoolean( 'expand_parents_on_storage_autocomplete_taglists' ) )
        favs_list.SetParentDecoratorsAllowed( CG.client_controller.new_options.GetBoolean( 'show_parent_decorators_on_storage_autocomplete_taglists' ) )
        favs_list.SetSiblingDecoratorsAllowed( CG.client_controller.new_options.GetBoolean( 'show_sibling_decorators_on_storage_autocomplete_taglists' ) )
        
        return favs_list
        
    
    def _InitSearchResultsList( self ):
        
        height_num_chars = CG.client_controller.new_options.GetInteger( 'ac_write_list_height_num_chars' )
        
        preds_list = ListBoxTagsPredicatesAC( self._dropdown_notebook, self.BroadcastChoices, self._float_mode, self._display_tag_service_key, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE, height_num_chars = height_num_chars )
        
        preds_list.SetExtraParentRowsAllowed( CG.client_controller.new_options.GetBoolean( 'expand_parents_on_storage_autocomplete_taglists' ) )
        preds_list.SetParentDecoratorsAllowed( CG.client_controller.new_options.GetBoolean( 'show_parent_decorators_on_storage_autocomplete_taglists' ) )
        preds_list.SetSiblingDecoratorsAllowed( CG.client_controller.new_options.GetBoolean( 'show_sibling_decorators_on_storage_autocomplete_taglists' ) )
        
        return preds_list
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            tags = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            tags = HydrusTags.CleanTags( tags )
            
            self.tagsPasted.emit( list( tags ) )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of tags', e )
            
            raise
            
        
    
    def _ShouldBroadcastCurrentInputOnEnterKey( self ):
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        looking_at_search_results = self._dropdown_notebook.currentWidget() == self._search_results_list
        
        sitting_on_empty = parsed_autocomplete_text.IsEmpty()
        
        something_to_broadcast = self._GetCurrentBroadcastTextPredicate() is not None
        
        # the list has results, but they are out of sync with what we have currently entered
        # when the user has quickly typed something in and the results are not yet in
        results_desynced_with_text = parsed_autocomplete_text != self._current_list_parsed_autocomplete_text
        
        p1 = something_to_broadcast and results_desynced_with_text
        
        # when the text ctrl is empty and we want to push a None to the parent dialog
        p2 = sitting_on_empty
        
        return looking_at_search_results and ( p1 or p2 )
        
    
    def _StartSearchResultsFetchJob( self, job_status ):
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = self._location_context_button.GetValue(), tag_context = self._tag_context_button.GetValue() )
        
        CG.client_controller.CallToThread( WriteFetch, self, job_status, self.SetPrefetchResults, self.SetFetchedResults, parsed_autocomplete_text, file_search_context, self._results_cache )
        
    
    def _TryToProcessAPasteEvent( self ) -> bool:
        
        # ok we are going to eat a ctrl+v if we have a paste button and the current clipboard contains multiple lines
        
        if not self._show_paste_button:
            
            return False
            
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return False
            
        
        try:
            
            tags = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            tags = HydrusTags.CleanTags( tags )
            
            if len( tags ) > 1:
                
                do_it = False
                
                if CG.client_controller.new_options.GetBoolean( 'skip_yesno_on_write_autocomplete_multiline_paste' ):
                    
                    do_it = True
                    
                else:
                    
                    message = 'You have pasted multiple lines of content. Want to enter them all as separate tags? You entered:'
                    message += HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( tags, do_sort = False, no_trailing_whitespace = True )
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Want to paste everything?' )
                    
                    if result == QW.QDialog.DialogCode.Accepted:
                        
                        do_it = True
                        
                    
                
                if do_it:
                    
                    self._Paste()
                    
                    return True
                    
                
            
            return False
            
        except Exception as e:
            
            return False
            
        
    
    def RefreshFavouriteTags( self ):
        
        if self._favourites_list is None:
            
            return
            
        
        favourite_tags = sorted( CG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
        
        self._favourites_list.SetTags( favourite_tags )
        
    
    def SetDisplayTagServiceKey( self, service_key ):
        
        self._tag_context_button.SetDisplayTagServiceKey( service_key )
        
    
class EditAdvancedORPredicates( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, initial_string = None ):
        
        super().__init__( parent )
        
        self._input_text = QW.QLineEdit( self )
        
        self._result_preview = QW.QPlainTextEdit()
        self._result_preview.setReadOnly( True )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._result_preview, ( 64, 6 ) )
        
        self._result_preview.setMinimumWidth( width )
        self._result_preview.setMinimumHeight( height )
        
        self._current_predicates = []
        
        #
        
        if initial_string is not None:
            
            self._input_text.setText( initial_string )
            
        
        #
        
        rows = []
        
        rows.append( ( 'Input: ', self._input_text ) )
        rows.append( ( 'Result preview: ', self._result_preview ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        summary = 'Enter a complicated tag search here as text, such as \'( blue eyes and blonde hair ) or ( green eyes and red hair )\', and this should turn it into hydrus-compatible search predicates.'
        summary += '\n' * 2
        summary += 'Accepted operators: not (!, -), and (&&), or (||), implies (=>), xor, xnor (iff, <=>), nand, nor. Many system predicates are also supported.'
        summary += '\n' * 2
        summary += 'Parentheses work the usual way. \\ can be used to escape characters (e.g. to search for tags including parentheses)'
        
        st = ClientGUICommon.BetterStaticText( self, summary )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._UpdateText()
        
        self._input_text.textChanged.connect( self.EventUpdateText )
        
        ClientGUIFunctions.SetFocusLater( self._input_text )
        
    
    def _UpdateText( self ):
        
        text = self._input_text.text()
        
        self._current_predicates = []
        
        object_name = ''
        
        output = ''
        
        if len( text ) > 0:
            
            try:
                
                # this makes a list of sets, each set representing a list of AND preds
                result = LogicExpressionQueryParser.parse_logic_expression_query( text )
                
                for s in result:
                    
                    tag_preds = []
                    
                    system_preds = []
                    negated_system_pred_strings = []
                    system_pred_strings = []
                    
                    for tag_string in s:
                        
                        if tag_string.startswith( '-system:' ):
                            
                            negated_system_pred_strings.append( tag_string )
                            
                            continue
                            
                        
                        if tag_string.startswith( 'system:' ):
                            
                            system_pred_strings.append( tag_string )
                            
                            continue
                            
                        
                        if tag_string.startswith( '-' ):
                            
                            inclusive = False
                            
                            tag_string = tag_string[1:]
                            
                        else:
                            
                            inclusive = True
                            
                        
                        try:
                            
                            tag_string = HydrusTags.CleanTag( tag_string )
                            
                            HydrusTags.CheckTagNotEmpty( tag_string )
                            
                        except Exception as e:
                            
                            raise ValueError( str( e ) )
                            
                        
                        if '*' in tag_string:
                            
                            ( namespace, subtag ) = HydrusTags.SplitTag( tag_string )
                            
                            if len( namespace ) > 0 and subtag == '*':
                                
                                row_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, value = namespace, inclusive = inclusive )
                                
                            else:
                                
                                row_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, value = tag_string, inclusive = inclusive )
                                
                            
                        else:
                            
                            row_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, value = tag_string, inclusive = inclusive )
                            
                        
                        tag_preds.append( row_pred )
                        
                    
                    if len( negated_system_pred_strings ) > 0:
                        
                        raise ValueError( 'Sorry, that would make negated system tags, which are not supported yet! Try to rephrase or negate the system tag yourself.' )
                        
                    
                    if len( system_pred_strings ) > 0:
                        
                        try:
                            
                            system_preds = ClientSearchParseSystemPredicates.ParseSystemPredicateStringsToPredicates( system_pred_strings )
                            
                        except Exception as e:
                            
                            raise ValueError( str( e ) )
                            
                        
                    
                    row_preds = tag_preds + system_preds
                    
                    if len( row_preds ) == 1:
                        
                        self._current_predicates.append( row_preds[0] )
                        
                    else:
                        
                        self._current_predicates.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = row_preds ) )
                        
                    
                
                output = '\n'.join( ( pred.ToString() for pred in self._current_predicates ) )
                object_name = 'HydrusValid'
                
            except ValueError as e:
                
                output = 'Could not parse! {}'.format( e )
                object_name = 'HydrusInvalid'
                
            
        
        self._result_preview.setPlainText( output )
        
        self._result_preview.setObjectName( object_name )
        self._result_preview.style().polish( self._result_preview )
        
    
    def EventUpdateText( self, text ):
        
        self._UpdateText()
        
    
    def GetValue( self ):
        
        self._UpdateText()
        
        if len( self._current_predicates ) == 0:
            
            raise HydrusExceptions.VetoException( 'Please enter a string that parses into a set of search rules.' )
            
        
        return self._current_predicates
        
    
