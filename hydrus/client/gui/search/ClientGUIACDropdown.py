import collections
import itertools
import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListBoxesData
from hydrus.client.gui.pages import ClientGUIResultsSortCollect
from hydrus.client.gui.search import ClientGUISearch
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientTags

from hydrus.external import LogicExpressionQueryParser

def AppendLoadingPredicate( predicates ):
    
    predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_LABEL, value = 'loading results\u2026' ) )
    
def GetPossibleFileDomainServicesInOrder( all_known_files_allowed: bool ):
    
    services_manager = HG.client_controller.services_manager
    
    service_types_in_order = [ HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_TRASH_DOMAIN ]
    
    advanced_mode = HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
    
    if advanced_mode:
        
        service_types_in_order.append( HC.COMBINED_LOCAL_FILE )
        
    
    service_types_in_order.append( HC.FILE_REPOSITORY )
    service_types_in_order.append( HC.IPFS )
    
    if all_known_files_allowed:
        
        service_types_in_order.append( HC.COMBINED_FILE )
        
    
    services = services_manager.GetServices( service_types_in_order )
    
    if not advanced_mode:
        
        services = [ service for service in services if service.GetServiceKey() != CC.LOCAL_UPDATE_SERVICE_KEY ]
        
    
    return services
    

def InsertOtherPredicatesForRead( predicates: list, parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText, include_unusual_predicate_types: bool, under_construction_or_predicate: typing.Optional[ ClientSearch.Predicate ] ):
    
    if include_unusual_predicate_types:
        
        non_tag_predicates = list( parsed_autocomplete_text.GetNonTagFileSearchPredicates() )
        
        non_tag_predicates.reverse()
        
        for predicate in non_tag_predicates:
            
            PutAtTopOfMatches( predicates, predicate )
            
        
    
    if under_construction_or_predicate is not None:
        
        PutAtTopOfMatches( predicates, under_construction_or_predicate )
        
    
def InsertTagPredicates( predicates: list, tag_service_key: bytes, parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText, insert_if_does_not_exist: bool = True ):
    
    if parsed_autocomplete_text.IsTagSearch():
        
        tag_predicate = parsed_autocomplete_text.GetImmediateFileSearchPredicate()
        
        actual_tag = tag_predicate.GetValue()
        
        ideal_predicate = None
        other_matching_predicates = []
        
        for predicate in predicates:
            
            # this works due to __hash__
            if predicate == tag_predicate:
                
                ideal_predicate = predicate.GetIdealPredicate()
                
                continue
                
            
            matchable_search_texts = predicate.GetMatchableSearchTexts()
            
            if len( matchable_search_texts ) <= 1:
                
                continue
                
            
            if actual_tag in matchable_search_texts:
                
                other_matching_predicates.append( predicate )
                
            
        
        for predicate in other_matching_predicates:
            
            PutAtTopOfMatches( predicates, predicate, insert_if_does_not_exist = insert_if_does_not_exist )
            
        
        PutAtTopOfMatches( predicates, tag_predicate, insert_if_does_not_exist = insert_if_does_not_exist )
        
        if ideal_predicate is not None:
            
            PutAtTopOfMatches( predicates, ideal_predicate, insert_if_does_not_exist = insert_if_does_not_exist )
            
        
    
def ReadFetch(
    win: QW.QWidget,
    job_key: ClientThreading.JobKey,
    results_callable,
    parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText,
    qt_media_callable,
    file_search_context: ClientSearch.FileSearchContext,
    synchronised,
    include_unusual_predicate_types,
    results_cache: ClientSearch.PredicateResultsCache,
    under_construction_or_predicate,
    force_system_everything
):
    
    tag_search_context = file_search_context.GetTagSearchContext()
    
    tag_service_key = tag_search_context.service_key
    
    if not parsed_autocomplete_text.IsAcceptableForTagSearches():
        
        if parsed_autocomplete_text.IsEmpty():
            
            cache_valid = isinstance( results_cache, ClientSearch.PredicateResultsCacheSystem )
            
            we_need_results = not cache_valid
            
            db_not_going_to_hang_if_we_hit_it = not HG.client_controller.DBCurrentlyDoingJob()
            
            if we_need_results or db_not_going_to_hang_if_we_hit_it:
                
                predicates = HG.client_controller.Read( 'file_system_predicates', file_search_context, force_system_everything = force_system_everything )
                
                results_cache = ClientSearch.PredicateResultsCacheSystem( predicates )
                
                matches = predicates
                
            else:
                
                matches = results_cache.GetPredicates()
                
            
        else:
            
            # if the user inputs '-' or 'creator:' or similar, let's go to an empty list
            matches = []
            
        
    else:
        
        fetch_from_db = True
        
        if synchronised and qt_media_callable is not None and not file_search_context.GetSystemPredicates().HasSystemLimit():
            
            try:
                
                media = HG.client_controller.CallBlockingToQt( win, qt_media_callable )
                
            except HydrusExceptions.QtDeadWindowException:
                
                return
                
            
            if job_key.IsCancelled():
                
                return
                
            
            media_available_and_good = media is not None and len( media ) > 0
            
            if media_available_and_good:
                
                fetch_from_db = False
                
            
        
        strict_search_text = parsed_autocomplete_text.GetSearchText( False )
        autocomplete_search_text = parsed_autocomplete_text.GetSearchText( True )
        
        # if user searches 'blah', then we include 'blah (23)' for 'series:blah (10)', 'blah (13)'
        # if they search for 'series:blah', then we don't!
        add_namespaceless = ':' not in strict_search_text
        
        if fetch_from_db:
            
            is_explicit_wildcard = parsed_autocomplete_text.IsExplicitWildcard()
            
            small_exact_match_search = ShouldDoExactSearch( parsed_autocomplete_text )
            
            matches = []
            
            if small_exact_match_search:
                
                if not results_cache.CanServeTagResults( parsed_autocomplete_text, True ):
                    
                    predicates = HG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_ACTUAL, file_search_context, search_text = strict_search_text, exact_match = True, inclusive = parsed_autocomplete_text.inclusive, add_namespaceless = add_namespaceless, job_key = job_key )
                    
                    results_cache = ClientSearch.PredicateResultsCacheTag( predicates, strict_search_text, True )
                    
                
                matches = results_cache.FilterPredicates( tag_service_key, strict_search_text )
                
            else:
                
                if is_explicit_wildcard:
                    
                    cache_valid = False
                    
                else:
                    
                    cache_valid = results_cache.CanServeTagResults( parsed_autocomplete_text, False )
                    
                
                if cache_valid:
                    
                    matches = results_cache.FilterPredicates( tag_service_key, autocomplete_search_text )
                    
                else:
                    
                    search_namespaces_into_full_tags = parsed_autocomplete_text.GetTagAutocompleteOptions().SearchNamespacesIntoFullTags()
                    
                    predicates = HG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_ACTUAL, file_search_context, search_text = autocomplete_search_text, inclusive = parsed_autocomplete_text.inclusive, add_namespaceless = add_namespaceless, job_key = job_key, search_namespaces_into_full_tags = search_namespaces_into_full_tags )
                    
                    if job_key.IsCancelled():
                        
                        return
                        
                    
                    if is_explicit_wildcard:
                        
                        matches = ClientSearch.FilterPredicatesBySearchText( tag_service_key, autocomplete_search_text, predicates )
                        
                    else:
                        
                        results_cache = ClientSearch.PredicateResultsCacheTag( predicates, strict_search_text, False )
                        
                        matches = results_cache.FilterPredicates( tag_service_key, autocomplete_search_text )
                        
                    
                
            
            if job_key.IsCancelled():
                
                return
                
            
        else:
            
            if not isinstance( results_cache, ClientSearch.PredicateResultsCacheMedia ):
                
                # it is possible that media will change between calls to this, so don't cache it
                
                tags_managers = []
                
                for m in media:
                    
                    if m.IsCollection():
                        
                        tags_managers.extend( m.GetSingletonsTagsManagers() )
                        
                    else:
                        
                        tags_managers.append( m.GetTagsManager() )
                        
                    
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                current_tags_to_count = collections.Counter()
                pending_tags_to_count = collections.Counter()
                
                include_current_tags = tag_search_context.include_current_tags
                include_pending_tags = tag_search_context.include_pending_tags
                
                for group_of_tags_managers in HydrusData.SplitListIntoChunks( tags_managers, 1000 ):
                    
                    if include_current_tags:
                        
                        current_tags_to_count.update( itertools.chain.from_iterable( tags_manager.GetCurrent( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ) for tags_manager in group_of_tags_managers ) )
                        
                    
                    if include_pending_tags:
                        
                        pending_tags_to_count.update( itertools.chain.from_iterable( [ tags_manager.GetPending( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL ) for tags_manager in group_of_tags_managers ] ) )
                        
                    
                    if job_key.IsCancelled():
                        
                        return
                        
                    
                
                tags_to_do = set()
                
                tags_to_do.update( current_tags_to_count.keys() )
                tags_to_do.update( pending_tags_to_count.keys() )
                
                tags_to_count = { tag : ( current_tags_to_count[ tag ], pending_tags_to_count[ tag ] ) for tag in tags_to_do }
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                predicates = HG.client_controller.Read( 'media_predicates', tag_search_context, tags_to_count, parsed_autocomplete_text.inclusive, job_key = job_key )
                
                results_cache = ClientSearch.PredicateResultsCacheMedia( predicates )
                
            
            if job_key.IsCancelled():
                
                return
                
            
            predicates = results_cache.FilterPredicates( tag_service_key, autocomplete_search_text )
            
            if job_key.IsCancelled():
                
                return
                
            
            predicates = ClientSearch.MergePredicates( predicates, add_namespaceless = add_namespaceless )
            
            matches = predicates
            
        
        matches = ClientSearch.SortPredicates( matches )
        
        if not parsed_autocomplete_text.inclusive:
            
            for match in matches:
                
                match.SetInclusive( False )
                
            
        
    
    InsertTagPredicates( matches, tag_service_key, parsed_autocomplete_text, insert_if_does_not_exist = False )
    
    InsertOtherPredicatesForRead( matches, parsed_autocomplete_text, include_unusual_predicate_types, under_construction_or_predicate )
    
    if job_key.IsCancelled():
        
        return
        
    
    HG.client_controller.CallAfterQtSafe( win, 'read a/c fetch', results_callable, job_key, parsed_autocomplete_text, results_cache, matches )
    
def PutAtTopOfMatches( matches: list, predicate: ClientSearch.Predicate, insert_if_does_not_exist: bool = True ):
    
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
            
        
    
def ShouldDoExactSearch( parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText ):
    
    if parsed_autocomplete_text.IsExplicitWildcard():
        
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
    
def WriteFetch( win, job_key, results_callable, parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText, file_search_context: ClientSearch.FileSearchContext, results_cache: ClientSearch.PredicateResultsCache ):
    
    tag_search_context = file_search_context.GetTagSearchContext()
    
    display_tag_service_key = tag_search_context.display_service_key
    
    if not parsed_autocomplete_text.IsAcceptableForTagSearches():
        
        matches = []
        
    else:
        
        is_explicit_wildcard = parsed_autocomplete_text.IsExplicitWildcard()
        
        strict_search_text = parsed_autocomplete_text.GetSearchText( False )
        autocomplete_search_text = parsed_autocomplete_text.GetSearchText( True )
        
        small_exact_match_search = ShouldDoExactSearch( parsed_autocomplete_text )
        
        if small_exact_match_search:
            
            if not results_cache.CanServeTagResults( parsed_autocomplete_text, True ):
                
                predicates = HG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = strict_search_text, exact_match = True, add_namespaceless = False, job_key = job_key )
                
                results_cache = ClientSearch.PredicateResultsCacheTag( predicates, strict_search_text, True )
                
            
            matches = results_cache.FilterPredicates( display_tag_service_key, strict_search_text )
            
        else:
            
            if is_explicit_wildcard:
                
                cache_valid = False
                
            else:
                
                cache_valid = results_cache.CanServeTagResults( parsed_autocomplete_text, False )
                
            
            if cache_valid:
                
                matches = results_cache.FilterPredicates( display_tag_service_key, autocomplete_search_text )
                
            else:
                
                search_namespaces_into_full_tags = parsed_autocomplete_text.GetTagAutocompleteOptions().SearchNamespacesIntoFullTags()
                
                predicates = HG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = autocomplete_search_text, add_namespaceless = False, job_key = job_key, search_namespaces_into_full_tags = search_namespaces_into_full_tags )
                
                if is_explicit_wildcard:
                    
                    matches = ClientSearch.FilterPredicatesBySearchText( display_tag_service_key, autocomplete_search_text, predicates )
                    
                else:
                    
                    results_cache = ClientSearch.PredicateResultsCacheTag( predicates, strict_search_text, False )
                    
                    matches = results_cache.FilterPredicates( display_tag_service_key, autocomplete_search_text )
                    
                
            
        
        if not is_explicit_wildcard:
            
            # this lets us get sibling data for tags that do not exist with count in the domain
            
            # we always do this, because results cache will not have current text input data
            
            input_text_predicates = HG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = strict_search_text, exact_match = True, add_namespaceless = False, zero_count_ok = True, job_key = job_key )
            
            for input_text_predicate in input_text_predicates:
                
                if ( input_text_predicate.HasIdealSibling() or input_text_predicate.HasParentPredicates() ) and input_text_predicate not in matches:
                    
                    matches.append( input_text_predicate )
                    
                
            
        
        matches = ClientSearch.SortPredicates( matches )
        
    
    InsertTagPredicates( matches, display_tag_service_key, parsed_autocomplete_text )
    
    HG.client_controller.CallAfterQtSafe( win, 'write a/c fetch', results_callable, job_key, parsed_autocomplete_text, results_cache, matches )
    
class EditLocationContextPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, location_context: ClientLocation.LocationContext, all_known_files_allowed: bool ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_location_context = location_context
        self._all_known_files_allowed = all_known_files_allowed
        
        self._location_list = ClientGUICommon.BetterCheckBoxList( self )
        
        services = GetPossibleFileDomainServicesInOrder( all_known_files_allowed )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            starts_checked = service_key in self._original_location_context.current_service_keys
            
            self._location_list.Append( name, ( HC.CONTENT_STATUS_CURRENT, service_key ), starts_checked = starts_checked )
            
        
        advanced_mode = HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        if advanced_mode:
            
            for service in services:
                
                name = service.GetName()
                service_key = service.GetServiceKey()
                
                if service_key in ( CC.COMBINED_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY ):
                    
                    continue
                    
                
                starts_checked = service_key in self._original_location_context.deleted_service_keys
                
                self._location_list.Append( 'deleted from {}'.format( name ), ( HC.CONTENT_STATUS_DELETED, service_key ), starts_checked = starts_checked )
                
            
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._location_list, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._location_list.checkBoxListChanged.connect( self._ClearSurplusServices )
        
    
    def _ClearSurplusServices( self ):
        
        # if user clicks all known files, then all other services will be wiped
        # all local files should do other file services too
        
        location_context = self._GetValue()
        
        filter_func = lambda service_key: HG.client_controller.services_manager.GetServiceType( service_key ) not in ( HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_TRASH_DOMAIN )
        
        location_context.ClearAllLocalFilesServices( filter_func )
        
        if set( self._GetStatusesAndServiceKeys( location_context ) ) != set( self._location_list.GetValue() ):
            
            self._SetValue( location_context )
            
        
    
    def _GetStatusesAndServiceKeys( self, location_context: ClientLocation.LocationContext ):
        
        statuses_and_service_keys = [ ( HC.CONTENT_STATUS_CURRENT, service_key ) for service_key in location_context.current_service_keys ]
        statuses_and_service_keys.extend( [ ( HC.CONTENT_STATUS_DELETED, service_key ) for service_key in location_context.deleted_service_keys ] )
        
        return statuses_and_service_keys
        
    
    def _GetValue( self ):
        
        statuses_and_service_keys = self._location_list.GetValue()
        
        current_service_keys = { service_key for ( status, service_key ) in statuses_and_service_keys if status == HC.CONTENT_STATUS_CURRENT }
        deleted_service_keys = { service_key for ( status, service_key ) in statuses_and_service_keys if status == HC.CONTENT_STATUS_DELETED }
        
        location_context = ClientLocation.LocationContext( current_service_keys = current_service_keys, deleted_service_keys = deleted_service_keys )
        
        return location_context
        
    
    def _SetValue( self, location_context: ClientLocation.LocationContext ):
        
        self._location_list.blockSignals( True )
        
        statuses_and_service_keys = self._GetStatusesAndServiceKeys( location_context )
        
        self._location_list.SetValue( statuses_and_service_keys )
        
        self._location_list.blockSignals( False )
        
    
    def GetValue( self ) -> ClientLocation.LocationContext:
        
        location_context = self._GetValue()
        
        return location_context
        
    
    def SetValue( self, location_context: ClientLocation.LocationContext ):
        
        self._SetValue( location_context )
        
        self._location_list.checkBoxListChanged.emit()
        
    
class ListBoxTagsPredicatesAC( ClientGUIListBoxes.ListBoxTagsPredicates ):
    
    def __init__( self, parent, callable, service_key, float_mode, **kwargs ):
        
        ClientGUIListBoxes.ListBoxTagsPredicates.__init__( self, parent, **kwargs )
        
        self._callable = callable
        self._service_key = service_key
        self._float_mode = float_mode
        
        self._predicates = {}
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        
        if self._float_mode:
            
            widget = self.window().parentWidget()
            
            if not QP.isValid( widget ):
                
                # seems to be a dialog posting late or similar
                
                return False
                
            
        else:
            
            widget = self
            
        
        predicates = ClientGUISearch.FleshOutPredicates( widget, predicates )
        
        if len( predicates ) > 0:
            
            self._callable( predicates, shift_down )
            
            return True
            
        
        return False
        
    
    def _GenerateTermFromPredicate( self, predicate: ClientSearch.Predicate ):
        
        term = ClientGUIListBoxes.ListBoxTagsPredicates._GenerateTermFromPredicate( self, predicate )
        
        if predicate.GetType() == ClientSearch.PREDICATE_TYPE_OR_CONTAINER:
            
            term.SetORUnderConstruction( True )
            
        
        return term
        
    
    def SetPredicates( self, predicates ):
        
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
            
            # important to make own copy, as same object originals can be altered (e.g. set non-inclusive) in cache, and we need to notice that change just above
            self._predicates = [ predicate.GetCopy() for predicate in predicates ]
            
            self._Clear()
            
            terms = [ self._GenerateTermFromPredicate( predicate ) for predicate in predicates ]
            
            self._AppendTerms( terms )
            
            self._DataHasChanged()
            
            if len( predicates ) > 0:
                
                logical_index = 0
                
                if len( predicates ) > 1:
                    
                    skip_ors = True
                    
                    some_preds_have_count = True in ( predicate.GetCount().HasNonZeroCount() for predicate in predicates )
                    skip_countless = HG.client_controller.new_options.GetBoolean( 'ac_select_first_with_count' ) and some_preds_have_count
                    
                    for ( index, predicate ) in enumerate( predicates ):
                        
                        # now only apply this to simple tags, not wildcards and system tags
                        
                        if skip_ors and predicate.GetType() == ClientSearch.PREDICATE_TYPE_OR_CONTAINER:
                            
                            continue
                            
                        
                        if skip_countless and predicate.GetType() in ( ClientSearch.PREDICATE_TYPE_PARENT, ClientSearch.PREDICATE_TYPE_TAG ) and predicate.GetCount().HasZeroCount():
                            
                            continue
                            
                        
                        logical_index = index
                        
                        break
                        
                    
                
                self._Hit( False, False, logical_index )
                
            
        
    
    def SetTagServiceKey( self, service_key: bytes ):
        
        self._service_key = service_key
        
    
class ListBoxTagsStringsAC( ClientGUIListBoxes.ListBoxTagsStrings ):
    
    def __init__( self, parent, callable, service_key, float_mode, **kwargs ):
        
        ClientGUIListBoxes.ListBoxTagsStrings.__init__( self, parent, service_key = service_key, sort_tags = False, **kwargs )
        
        self._callable = callable
        self._float_mode = float_mode
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        
        if self._float_mode:
            
            widget = self.window().parentWidget()
            
        else:
            
            widget = self
            
        
        predicates = ClientGUISearch.FleshOutPredicates( widget, predicates )
        
        if len( predicates ) > 0:
            
            self._callable( predicates, shift_down )
            
            return True
            
        
        return False
        
    
# much of this is based on the excellent TexCtrlAutoComplete class by Edward Flick, Michele Petrazzo and Will Sadkin, just with plenty of simplification and integration into hydrus
class AutoCompleteDropdown( QW.QWidget ):
    
    selectUp = QC.Signal()
    selectDown = QC.Signal()
    showNext = QC.Signal()
    showPrevious = QC.Signal()
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._can_intercept_unusual_key_events = True
        
        if self.window() == HG.client_controller.gui:
            
            use_float_mode = HG.client_controller.new_options.GetBoolean( 'autocomplete_float_main_gui' )
            
        else:
            
            use_float_mode = HG.client_controller.new_options.GetBoolean( 'autocomplete_float_frames' )
            
        
        self._float_mode = use_float_mode
        
        self._text_input_panel = QW.QWidget( self )
        
        self._text_ctrl = QW.QLineEdit( self._text_input_panel )
        
        self.setFocusProxy( self._text_ctrl )
        
        self._UpdateBackgroundColour()
        
        self._last_attempted_dropdown_width = 0
        self._last_attempted_dropdown_position = ( None, None )
        
        self._text_ctrl_widget_event_filter = QP.WidgetEventFilter( self._text_ctrl )
        
        self._text_ctrl.textChanged.connect( self.EventText )
        
        self._text_ctrl_widget_event_filter.EVT_KEY_DOWN( self.keyPressFilter )
        
        self._text_ctrl.installEventFilter( self )
        
        self._main_vbox = QP.VBoxLayout( margin = 0 )
        
        self._SetupTopListBox()
        
        self._text_input_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._text_input_hbox, self._text_ctrl, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        self._text_input_panel.setLayout( self._text_input_hbox )
        
        QP.AddToLayout( self._main_vbox, self._text_input_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if self._float_mode:
            
            self._dropdown_window = QW.QFrame( self )
            
            self._dropdown_window.setWindowFlags( QC.Qt.Tool | QC.Qt.FramelessWindowHint )
            
            self._dropdown_window.setAttribute( QC.Qt.WA_ShowWithoutActivating )
            
            self._dropdown_window.setFrameStyle( QW.QFrame.Panel | QW.QFrame.Raised )
            self._dropdown_window.setLineWidth( 2 )
            
            self._dropdown_window.move( ClientGUIFunctions.ClientToScreen( self._text_ctrl, QC.QPoint( 0, 0 ) ) )
            
            self._dropdown_window_widget_event_filter = QP.WidgetEventFilter( self._dropdown_window )
            self._dropdown_window_widget_event_filter.EVT_CLOSE( self.EventCloseDropdown )
            
            self._dropdown_hidden = True
            
            self._force_dropdown_hide = False
            
        else:
            
            self._dropdown_window = QW.QWidget( self )
            
        
        self._dropdown_window.installEventFilter( self )
        
        self._dropdown_notebook = QW.QTabWidget( self._dropdown_window )
        
        #
        
        self._search_results_list = self._InitSearchResultsList()
        
        self._dropdown_notebook.setCurrentIndex( self._dropdown_notebook.addTab( self._search_results_list, 'results' ) )
        
        #
        
        if not self._float_mode:
            
            QP.AddToLayout( self._main_vbox, self._dropdown_window, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        self.setLayout( self._main_vbox )
        
        self._current_list_parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        self._results_cache: ClientSearch.PredicateResultsCache = ClientSearch.PredicateResultsCacheInit()
        
        self._current_fetch_job_key = None
        
        self._schedule_results_refresh_job = None
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'tags_autocomplete' ], alternate_filter_target = self._text_ctrl )
        
        if self._float_mode:
            
            self._widget_event_filter = QP.WidgetEventFilter( self )
            self._widget_event_filter.EVT_MOVE( self.EventMove )
            self._widget_event_filter.EVT_SIZE( self.EventMove )
            
            HG.client_controller.sub( self, '_DropdownHideShow', 'top_level_window_move_event' )
            
            parent = self
            
            self._scroll_event_filters = []
            
            while True:
                
                try:
                    
                    parent = parent.parentWidget()
                    
                    if isinstance( parent, QW.QScrollArea ):
                        
                        scroll_event_filter = QP.WidgetEventFilter( parent )
                        
                        self._scroll_event_filters.append( scroll_event_filter )
                        
                        scroll_event_filter.EVT_SCROLLWIN( self.EventMove )
                        
                    
                except:
                    
                    break
                    
                
            
        
        HG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        HG.client_controller.sub( self, 'DoDropdownHideShow', 'notify_page_change' )
        
        self._ScheduleResultsRefresh( 0.0 )
        
        HG.client_controller.CallLaterQtSafe( self, 0.05, 'hide/show dropdown', self._DropdownHideShow )
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        raise NotImplementedError()
        
    
    def _CancelSearchResultsFetchJob( self ):
        
        if self._current_fetch_job_key is not None:
            
            self._current_fetch_job_key.Cancel()
            
            self._current_fetch_job_key = None
            
        
    
    def _ClearInput( self ):
        
        self._CancelSearchResultsFetchJob()
        
        self._text_ctrl.blockSignals( True )
        
        self._text_ctrl.clear()
        
        self._SetResultsToList( [], self._GetParsedAutocompleteText() )
        
        self._text_ctrl.blockSignals( False )
        
        self._ScheduleResultsRefresh( 0.0 )
        
    
    def _GetParsedAutocompleteText( self ) -> ClientSearch.ParsedAutocompleteText:
        
        raise NotImplementedError()
        
    
    def _DropdownHideShow( self ):
        
        if not self._float_mode:
            
            return
            
        
        try:
            
            if self._ShouldShow():
                
                self._ShowDropdown()
                
            else:
                
                self._HideDropdown()
                
            
        except:
            
            raise
            
        
    
    def _HandleEscape( self ):
        
        if self._text_ctrl.text() != '':
            
            self._ClearInput()
            
            return True
            
        elif self._float_mode:
            
            self.parentWidget().setFocus( QC.Qt.OtherFocusReason )
            
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
        
        # if an event came from clicking the dropdown, we want to put focus back on textctrl
        
        if self._float_mode:
            
            self.window().activateWindow()
            
        else:
            
            ClientGUIFunctions.SetFocusLater( self._text_ctrl )
            
        
    
    def _ScheduleResultsRefresh( self, delay ):
        
        if self._schedule_results_refresh_job is not None:
            
            self._schedule_results_refresh_job.Cancel()
            
        
        self._schedule_results_refresh_job = HG.client_controller.CallLaterQtSafe( self, delay, 'a/c results refresh', self._UpdateSearchResults )
        
    
    def _SetupTopListBox( self ):
        
        pass
        
    
    def _SetListDirty( self ):
        
        self._results_cache = ClientSearch.PredicateResultsCacheInit()
        
        self._ScheduleResultsRefresh( 0.0 )
        
    
    def _SetResultsToList( self, results, parsed_autocomplete_text ):
        
        raise NotImplementedError()
        
    
    def _ShouldShow( self ):
        
        if self._force_dropdown_hide:
            
            return False
            
        
        current_active_window = QW.QApplication.activeWindow()
        
        i_am_active_and_focused = self.window() == current_active_window and self._text_ctrl.hasFocus() and not self.visibleRegion().isEmpty()
        
        dropdown_is_active = self._dropdown_window == current_active_window
        
        focus_or_active_good = i_am_active_and_focused or dropdown_is_active
        
        visible = self.isVisible()
        
        return focus_or_active_good and visible
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        raise NotImplementedError()
        
    
    def _ShowDropdown( self ):
        
        text_panel_size = self._text_input_panel.size()
        
        text_input_width = text_panel_size.width()
        text_input_height = text_panel_size.height()
        
        if self._text_input_panel.isVisible():
            
            desired_dropdown_position = ClientGUIFunctions.ClientToScreen( self._text_input_panel, QC.QPoint( 0, text_input_height ) )
            
            if self._last_attempted_dropdown_position != desired_dropdown_position:
                
                self._dropdown_window.move( desired_dropdown_position )
                
                self._last_attempted_dropdown_position = desired_dropdown_position
                
            
        
        #
        
        if self._dropdown_hidden:
            
            self._dropdown_window.show()
            
            self._dropdown_hidden = False
            
        
        if text_input_width != self._last_attempted_dropdown_width:
            
            self._dropdown_window.setFixedWidth( text_input_width )
            
            self._last_attempted_dropdown_width = text_input_width
            
        
    
    def _StartSearchResultsFetchJob( self, job_key ):
        
        raise NotImplementedError()
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        raise NotImplementedError()
        
    
    def _UpdateBackgroundColour( self ):
        
        colour = HG.client_controller.new_options.GetColour( CC.COLOUR_AUTOCOMPLETE_BACKGROUND )
        
        if not self._can_intercept_unusual_key_events:
            
            colour = ClientGUIFunctions.GetLighterDarkerColour( colour )
            
        
        QP.SetBackgroundColour( self._text_ctrl, colour )
        
        self._text_ctrl.update()
        
    
    def _UpdateSearchResults( self ):
        
        self._schedule_results_refresh_job = None
        
        self._CancelSearchResultsFetchJob()
        
        self._current_fetch_job_key = ClientThreading.JobKey( cancellable = True )
        
        self._StartSearchResultsFetchJob( self._current_fetch_job_key )
        
    
    def BroadcastChoices( self, predicates, shift_down = False ):
        
        self._BroadcastChoices( predicates, shift_down )
        
        self._RestoreTextCtrlFocus()
        
    
    def CancelCurrentResultsFetchJob( self ):
        
        self._CancelSearchResultsFetchJob()
        
    
    def DoDropdownHideShow( self ):
        
        self._DropdownHideShow()
        
    
    def keyPressFilter( self, event ):
        
        HG.client_controller.ResetIdleTimer()
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if self._can_intercept_unusual_key_events:
            
            send_input_to_current_list = False
            
            current_results_list = self._dropdown_notebook.currentWidget()
            
            if key in ( ord( 'A' ), ord( 'a' ) ) and modifier == QC.Qt.ControlModifier:
                
                return True # was: event.ignore()
                
            elif key in ( QC.Qt.Key_Return, QC.Qt.Key_Enter ) and self._ShouldTakeResponsibilityForEnter():
                
                shift_down = modifier == QC.Qt.ShiftModifier
                
                self._TakeResponsibilityForEnter( shift_down )
                
            elif key == QC.Qt.Key_Escape:
                
                escape_caught = self._HandleEscape()
                
                if not escape_caught:
                    
                    send_input_to_current_list = True
                    
                
            else:
                
                send_input_to_current_list = True
                
            
            if send_input_to_current_list:
                
                current_results_list.keyPressEvent( event ) # ultimately, this typically ignores the event, letting the text ctrl take it
                
                return not event.isAccepted()
                
            
        else:
            
            return True # was: event.ignore()
            
        
    
    def EventCloseDropdown( self, event ):
        
        HG.client_controller.gui.close()
        
        return True
        
    
    def eventFilter( self, watched, event ):
        
        if watched == self._text_ctrl:
            
            if event.type() == QC.QEvent.Wheel:
                
                current_results_list = self._dropdown_notebook.currentWidget()
                
                if self._text_ctrl.text() == '' and len( current_results_list ) == 0:
                    
                    if event.angleDelta().y() > 0:
                        
                        self.selectUp.emit()
                        
                    else:
                        
                        self.selectDown.emit()
                        
                    
                    event.accept()
                    
                    return True
                    
                else:
                    
                    if event.modifiers() & QC.Qt.ControlModifier:
                        
                        if event.angleDelta().y() > 0:
                            
                            current_results_list.MoveSelectionUp()
                            
                        else:
                            
                            current_results_list.MoveSelectionDown()
                            
                        
                        event.accept()
                        
                        return True
                        
                    
                
            elif self._float_mode:
                
                if event.type() in ( QC.QEvent.FocusOut, QC.QEvent.FocusIn ):
                    
                    self._DropdownHideShow()
                    
                    return False
                    
                
            
        elif watched == self._dropdown_window:
            
            if self._float_mode and event.type() in ( QC.QEvent.WindowActivate, QC.QEvent.WindowDeactivate ):
                
                # we delay this slightly because when you click from dropdown to text, the deactivate event fires before the focusin, leading to a frame of hide
                HG.client_controller.CallLaterQtSafe( self, 0.05, 'hide/show dropdown', self._DropdownHideShow )
                
                return False
                
            
        
        return False
        
    
    def EventMove( self, event ):
        
        self._DropdownHideShow()
        
        return True # was: event.ignore()
        
    
    def EventText( self, new_text ):
        
        num_chars = len( self._text_ctrl.text() )
        
        if num_chars == 0:
            
            self._ScheduleResultsRefresh( 0.0 )
            
        else:
            
            parsed_autocomplete_text = self._GetParsedAutocompleteText()
            
            if parsed_autocomplete_text.GetTagAutocompleteOptions().FetchResultsAutomatically():
                
                self._ScheduleResultsRefresh( 0.0 )
                
            
            if self._dropdown_notebook.currentWidget() != self._search_results_list:
                
                self.MoveNotebookPageFocus( index = 0 )
                
            
        
    
    def ForceSizeCalcNow( self ):
        
        if self._float_mode:
            
            self._DropdownHideShow()
            
        
    
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
            
            self.setFocus( QC.Qt.OtherFocusReason )
            
        
    
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
                    
                    self._ScheduleResultsRefresh( 0.0 )
                    
                elif input_is_empty and action in ( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_LEFT, CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_RIGHT ):
                    
                    if action == CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_LEFT:
                        
                        direction = -1
                        
                    else:
                        
                        direction = 1
                        
                    
                    self.MoveNotebookPageFocus( direction = direction )
                    
                elif everything_is_empty and action == CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_LEFT:
                    
                    self.selectUp.emit()
                    
                elif everything_is_empty and action == CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_RIGHT:
                    
                    self.selectDown.emit()
                    
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
        
    
    def SetFetchedResults( self, job_key: ClientThreading.JobKey, parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText, results_cache: ClientSearch.PredicateResultsCache, results: list ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            self._CancelSearchResultsFetchJob()
            
            self._results_cache = results_cache
            
            self._SetResultsToList( results, parsed_autocomplete_text )
            
        
    
    def SetForceDropdownHide( self, value ):
        
        self._force_dropdown_hide = value
        
        self._DropdownHideShow()
        
    
class AutoCompleteDropdownTags( AutoCompleteDropdown ):
    
    locationChanged = QC.Signal( ClientLocation.LocationContext )
    tagServiceChanged = QC.Signal( bytes )
    
    def __init__( self, parent, location_context: ClientLocation.LocationContext, tag_service_key ):
        
        location_context.FixMissingServices( HG.client_controller.services_manager.FilterValidServiceKeys )
        
        if not HG.client_controller.services_manager.ServiceExists( tag_service_key ):
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        self._location_context = location_context
        self._tag_service_key = tag_service_key
        
        AutoCompleteDropdown.__init__( self, parent )
        
        self._allow_all_known_files = True
        
        tag_service = HG.client_controller.services_manager.GetService( self._tag_service_key )
        
        self._file_repo_button = ClientGUICommon.BetterButton( self._dropdown_window, location_context.ToString( HG.client_controller.services_manager.GetName ), self.FileButtonHit )
        self._file_repo_button.setMinimumWidth( 20 )
        
        self._tag_repo_button = ClientGUICommon.BetterButton( self._dropdown_window, tag_service.GetName(), self.TagButtonHit )
        self._tag_repo_button.setMinimumWidth( 20 )
        
        self._favourites_list = self._InitFavouritesList()
        
        self.RefreshFavouriteTags()
        
        self._dropdown_notebook.addTab( self._favourites_list, 'favourites' )
        
        #
        
        HG.client_controller.sub( self, 'RefreshFavouriteTags', 'notify_new_favourite_tags' )
        HG.client_controller.sub( self, 'NotifyNewServices', 'notify_new_services' )
        
    
    def _IsAllKnownFilesServiceTypeAllowed( self ):
        
        raise NotImplementedError()
        
    
    def _ChangeLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        location_context.FixMissingServices( HG.client_controller.services_manager.FilterValidServiceKeys )
        
        if location_context.IsAllKnownFiles() and self._tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            local_tag_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
            
            self._ChangeTagService( local_tag_services[0].GetServiceKey() )
            
        
        self._location_context = location_context
        
        self._UpdateFileServiceLabel()
        
        self.locationChanged.emit( self._location_context )
        
        self._SetListDirty()
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        if not HG.client_controller.services_manager.ServiceExists( tag_service_key ):
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY and self._location_context.IsAllKnownFiles():
            
            default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
            
            self._ChangeLocationContext( default_location_context )
            
        
        self._tag_service_key = tag_service_key
        
        self._search_results_list.SetTagServiceKey( self._tag_service_key )
        self._favourites_list.SetTagServiceKey( self._tag_service_key )
        
        self._UpdateTagServiceLabel()
        
        self.tagServiceChanged.emit( self._tag_service_key )
        
        self._SetListDirty()
        
    
    def _EditMultipleLocationContext( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit multiple location' ) as dlg:
            
            panel = EditLocationContextPanel( dlg, self._location_context, self._IsAllKnownFilesServiceTypeAllowed() )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                location_context = panel.GetValue()
                
                self._ChangeLocationContext( location_context )
                
            
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> typing.Optional[ ClientSearch.Predicate ]:
        
        raise NotImplementedError()
        
    
    def _GetParsedAutocompleteText( self ) -> ClientSearch.ParsedAutocompleteText:
        
        collapse_search_characters = True
        
        tag_autocomplete_options = HG.client_controller.tag_display_manager.GetTagAutocompleteOptions( self._tag_service_key )
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( self._text_ctrl.text(), tag_autocomplete_options, collapse_search_characters )
        
        return parsed_autocomplete_text
        
    
    def _InitFavouritesList( self ):
        
        raise NotImplementedError()
        
    
    def _SetResultsToList( self, results, parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText ):
        
        self._search_results_list.SetPredicates( results )
        
        self._current_list_parsed_autocomplete_text = parsed_autocomplete_text
        
    
    def _UpdateFileServiceLabel( self ):
        
        name = self._location_context.ToString( HG.client_controller.services_manager.GetName )
        
        self._file_repo_button.setText( name )
        
        self._SetListDirty()
        
    
    def _UpdateTagServiceLabel( self ):
        
        tag_service = HG.client_controller.services_manager.GetService( self._tag_service_key )
        
        name = tag_service.GetName()
        
        self._tag_repo_button.setText( name )
        
    
    def FileButtonHit( self ):
        
        services = GetPossibleFileDomainServicesInOrder( self._IsAllKnownFilesServiceTypeAllowed() )
        
        advanced_mode = HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        menu = QW.QMenu()
        
        for service in services:
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( service.GetServiceKey() )
            
            ClientGUIMenus.AppendMenuItem( menu, service.GetName(), 'Change the current file domain to ' + service.GetName() + '.', self._ChangeLocationContext, location_context )
            
        
        if advanced_mode and False:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            for service in services:
                
                if service.GetServiceKey() in ( CC.COMBINED_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY ):
                    
                    continue
                    
                
                location_context = ClientLocation.LocationContext( [], [ service.GetServiceKey() ] )
                
                ClientGUIMenus.AppendMenuItem( menu, 'deleted from {}'.format( service.GetName() ), 'Change the current file domain to files deleted from ' + service.GetName() + '.', self._ChangeLocationContext, location_context )
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'multiple locations', 'Change the current file domain to something with multiple locations.', self._EditMultipleLocationContext )
        
        CGC.core().PopupMenu( self._file_repo_button, menu )
        
        self._RestoreTextCtrlFocus()
        
    
    def NotifyNewServices( self ):
        
        self._ChangeLocationContext( self._location_context )
        self._ChangeTagService( self._tag_service_key )
        
    
    def RefreshFavouriteTags( self ):
        
        favourite_tags = sorted( HG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
        
        predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, value = tag ) for tag in favourite_tags ]
        
        self._favourites_list.SetPredicates( predicates )
        
    
    def ChangeLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._ChangeLocationContext( location_context )
        
    
    def SetStubPredicates( self, job_key, stub_predicates, parsed_autocomplete_text ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            self._SetResultsToList( stub_predicates, parsed_autocomplete_text )
            
        
    
    def SetTagServiceKey( self, tag_service_key ):
        
        self._ChangeTagService( tag_service_key )
        
    
    def TagButtonHit( self ):
        
        services_manager = HG.client_controller.services_manager
        
        service_types_in_order = [ HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.COMBINED_TAG ]
        
        services = services_manager.GetServices( service_types_in_order )
        
        menu = QW.QMenu()
        
        for service in services:
            
            ClientGUIMenus.AppendMenuItem( menu, service.GetName(), 'Change the current tag domain to ' + service.GetName() + '.', self._ChangeTagService, service.GetServiceKey() )
            
        
        CGC.core().PopupMenu( self._tag_repo_button, menu )
        
        self._RestoreTextCtrlFocus()
        
    
class AutoCompleteDropdownTagsRead( AutoCompleteDropdownTags ):
    
    searchChanged = QC.Signal( ClientSearch.FileSearchContext )
    searchCancelled = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, page_key, file_search_context: ClientSearch.FileSearchContext, media_sort_widget: typing.Optional[ ClientGUIResultsSortCollect.MediaSortControl ] = None, media_collect_widget: typing.Optional[ ClientGUIResultsSortCollect.MediaCollectControl ] = None, media_callable = None, synchronised = True, include_unusual_predicate_types = True, allow_all_known_files = True, force_system_everything = False, hide_favourites_edit_actions = False ):
        
        self._page_key = page_key
        
        self._under_construction_or_predicate = None
        
        location_context = file_search_context.GetLocationContext()
        tag_search_context = file_search_context.GetTagSearchContext()
        
        self._include_unusual_predicate_types = include_unusual_predicate_types
        self._force_system_everything = force_system_everything
        self._hide_favourites_edit_actions = hide_favourites_edit_actions
        
        self._media_sort_widget = media_sort_widget
        self._media_collect_widget = media_collect_widget
        
        self._allow_all_known_files = allow_all_known_files
        
        self._media_callable = media_callable
        
        self._file_search_context = file_search_context
        
        AutoCompleteDropdownTags.__init__( self, parent, location_context, tag_search_context.service_key )
        
        self._predicates_listbox.SetPredicates( self._file_search_context.GetPredicates() )
        
        #
        
        self._favourite_searches_button = ClientGUICommon.BetterBitmapButton( self._text_input_panel, CC.global_pixmaps().star, self._FavouriteSearchesMenu )
        self._favourite_searches_button.setToolTip( 'Load or save a favourite search.' )
        
        self._cancel_search_button = ClientGUICommon.BetterBitmapButton( self._text_input_panel, CC.global_pixmaps().stop, self.searchCancelled.emit )
        
        self._cancel_search_button.hide()
        
        QP.AddToLayout( self._text_input_hbox, self._favourite_searches_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._text_input_hbox, self._cancel_search_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        #
        
        self._include_current_tags = ClientGUICommon.OnOffButton( self._dropdown_window, on_label = 'include current tags', off_label = 'exclude current tags', start_on = tag_search_context.include_current_tags )
        self._include_current_tags.setToolTip( 'select whether to include current tags in the search' )
        self._include_pending_tags = ClientGUICommon.OnOffButton( self._dropdown_window, on_label = 'include pending tags', off_label = 'exclude pending tags', start_on = tag_search_context.include_pending_tags )
        self._include_pending_tags.setToolTip( 'select whether to include pending tags in the search' )
        
        self._search_pause_play = ClientGUICommon.OnOffButton( self._dropdown_window, on_label = 'searching immediately', off_label = 'search paused', start_on = synchronised )
        self._search_pause_play.setToolTip( 'select whether to renew the search as soon as a new predicate is entered' )
        
        self._or_advanced = ClientGUICommon.BetterButton( self._dropdown_window, 'OR', self._AdvancedORInput )
        self._or_advanced.setToolTip( 'Advanced OR Search input.' )
        
        if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._or_advanced.hide()
            
        
        self._or_cancel = ClientGUICommon.BetterBitmapButton( self._dropdown_window, CC.global_pixmaps().delete, self._CancelORConstruction )
        self._or_cancel.setToolTip( 'Cancel OR Predicate construction.' )
        self._or_cancel.hide()
        
        self._or_rewind = ClientGUICommon.BetterBitmapButton( self._dropdown_window, CC.global_pixmaps().previous, self._RewindORConstruction )
        self._or_rewind.setToolTip( 'Rewind OR Predicate construction.' )
        self._or_rewind.hide()
        
        button_hbox_1 = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox_1, self._include_current_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox_1, self._include_pending_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        sync_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( sync_button_hbox, self._search_pause_play, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( sync_button_hbox, self._or_advanced, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( sync_button_hbox, self._or_cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( sync_button_hbox, self._or_rewind, CC.FLAGS_CENTER_PERPENDICULAR )
        
        button_hbox_2 = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox_2, self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox_2, self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, button_hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, sync_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, button_hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.setLayout( vbox )
        
        self._predicates_listbox.listBoxChanged.connect( self._SignalNewSearchState )
        
        self._include_current_tags.valueChanged.connect( self.SetIncludeCurrent )
        self._include_pending_tags.valueChanged.connect( self.SetIncludePending )
        self._search_pause_play.valueChanged.connect( self.SetSynchronised )
        
    
    def _IsAllKnownFilesServiceTypeAllowed( self ):
        
        advanced_mode = HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        return advanced_mode and self._allow_all_known_files
        
    
    def _AdvancedORInput( self ):
        
        title = 'enter advanced OR predicates'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = EditAdvancedORPredicates( dlg )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                predicates = panel.GetValue()
                shift_down = False
                
                if len( predicates ) > 0:
                    
                    self._BroadcastChoices( predicates, shift_down )
                    
                
            
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        or_pred_in_broadcast = self._under_construction_or_predicate is not None and self._under_construction_or_predicate in predicates
        
        if shift_down:
            
            if self._under_construction_or_predicate is None:
                
                self._under_construction_or_predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, value = predicates )
                
            else:
                
                if or_pred_in_broadcast:
                    
                    predicates.remove( self._under_construction_or_predicate )
                    
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                or_preds.extend( [ predicate for predicate in predicates if predicate not in or_preds ] )
                
                self._under_construction_or_predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, value = or_preds )
                
            
        else:
            
            if or_pred_in_broadcast:
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                if len( or_preds ) == 1:
                    
                    predicates.remove( self._under_construction_or_predicate )
                    
                    predicates.extend( or_preds )
                    
                
            elif self._under_construction_or_predicate is not None:
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                or_preds.extend( [ predicate for predicate in predicates if predicate not in or_preds ] )
                
                predicates = { ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, value = or_preds ) }
                
            
            self._under_construction_or_predicate = None
            
            self._predicates_listbox.EnterPredicates( self._page_key, predicates )
            
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
    
    def _SignalNewSearchState( self ):
        
        self._file_search_context.SetPredicates( self._predicates_listbox.GetPredicates() )
        
        file_search_context = self._file_search_context.Duplicate()
        
        self.searchChanged.emit( file_search_context )
        
    
    def _CancelORConstruction( self ):
        
        self._under_construction_or_predicate = None
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
    
    def _ChangeLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        AutoCompleteDropdownTags._ChangeLocationContext( self, location_context )
        
        self._file_search_context.SetLocationContext( location_context )
        
        self._SignalNewSearchState()
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        AutoCompleteDropdownTags._ChangeTagService( self, tag_service_key )
        
        self._file_search_context.SetTagServiceKey( tag_service_key )
        
        self._SignalNewSearchState()
        
    
    def _FavouriteSearchesMenu( self ):
        
        menu = QW.QMenu()
        
        if not self._hide_favourites_edit_actions:
            
            ClientGUIMenus.AppendMenuItem( menu, 'manage favourite searches', 'Open a dialog to edit your favourite searches.', self._ManageFavouriteSearches )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'save this search', 'Save this search for later.', self._SaveFavouriteSearch )
            
        
        folders_to_names = HG.client_controller.favourite_search_manager.GetFoldersToNames()
        
        if len( folders_to_names ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            folder_names = list( folders_to_names.keys() )
            
            if None in folder_names:
                
                folder_names.remove( None )
                
                folder_names.sort()
                
                folder_names.insert( 0, None )
                
            else:
                
                folder_names.sort()
                
            
            for folder_name in folder_names:
                
                if folder_name is None:
                    
                    menu_to_use = menu
                    
                else:
                    
                    menu_to_use = QW.QMenu( menu )
                    
                    ClientGUIMenus.AppendMenu( menu, menu_to_use, folder_name )
                    
                
                names = sorted( folders_to_names[ folder_name ] )
                
                for name in names:
                    
                    ClientGUIMenus.AppendMenuItem( menu_to_use, name, 'Load the {} search.'.format( name ), self._LoadFavouriteSearch, folder_name, name )
                    
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> typing.Optional[ ClientSearch.Predicate ]:
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        if parsed_autocomplete_text.IsAcceptableForFileSearches():
            
            return parsed_autocomplete_text.GetImmediateFileSearchPredicate()
            
        else:
            
            return None
            
        
    
    def _HandleEscape( self ):
        
        if self._under_construction_or_predicate is not None and self._text_ctrl.text() == '':
            
            self._CancelORConstruction()
            
            return True
            
        else:
            
            return AutoCompleteDropdown._HandleEscape( self )
            
        
    
    def _InitFavouritesList( self ):
        
        height_num_chars = HG.client_controller.new_options.GetInteger( 'ac_read_list_height_num_chars' )
        
        favs_list = ListBoxTagsPredicatesAC( self._dropdown_notebook, self.BroadcastChoices, self._float_mode, self._tag_service_key, tag_display_type = ClientTags.TAG_DISPLAY_ACTUAL, height_num_chars = height_num_chars )
        
        return favs_list
        
    
    def _InitSearchResultsList( self ):
        
        height_num_chars = HG.client_controller.new_options.GetInteger( 'ac_read_list_height_num_chars' )
        
        return ListBoxTagsPredicatesAC( self._dropdown_notebook, self.BroadcastChoices, self._tag_service_key, self._float_mode, tag_display_type = ClientTags.TAG_DISPLAY_ACTUAL, height_num_chars = height_num_chars )
        
    
    def _LoadFavouriteSearch( self, folder_name, name ):
        
        ( file_search_context, synchronised, media_sort, media_collect ) = HG.client_controller.favourite_search_manager.GetFavouriteSearch( folder_name, name )
        
        self.blockSignals( True )
        
        self.SetFileSearchContext( file_search_context )
        
        if media_sort is not None and self._media_sort_widget is not None:
            
            self._media_sort_widget.SetSort( media_sort )
            
        
        if media_collect is not None and self._media_collect_widget is not None:
            
            self._media_collect_widget.SetCollect( media_collect )
            
        
        self._search_pause_play.SetOnOff( synchronised )
        
        self.blockSignals( False )
        
        self._SignalNewSearchState()
        
    
    def _ManageFavouriteSearches( self, favourite_search_row_to_save = None ):
        
        from hydrus.client.gui.search import ClientGUISearchPanels
        
        favourite_searches_rows = HG.client_controller.favourite_search_manager.GetFavouriteSearchRows()
        
        title = 'edit favourite searches'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUISearchPanels.EditFavouriteSearchesPanel( dlg, favourite_searches_rows, initial_search_row_to_edit = favourite_search_row_to_save )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                edited_favourite_searches_rows = panel.GetValue()
                
                HG.client_controller.favourite_search_manager.SetFavouriteSearchRows( edited_favourite_searches_rows )
                
            
        
    
    def _RewindORConstruction( self ):
        
        if self._under_construction_or_predicate is not None:
            
            or_preds = self._under_construction_or_predicate.GetValue()
            
            if len( or_preds ) <= 1:
                
                self._CancelORConstruction()
                
                return
                
            
            or_preds = or_preds[:-1]
            
            self._under_construction_or_predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, value = or_preds )
            
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
    
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
        
    
    def _SetupTopListBox( self ):
        
        self._predicates_listbox = ListBoxTagsActiveSearchPredicates( self, self._page_key )
        
        QP.AddToLayout( self._main_vbox, self._predicates_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _StartSearchResultsFetchJob( self, job_key ):
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        stub_predicates = []
        
        InsertOtherPredicatesForRead( stub_predicates, parsed_autocomplete_text, self._include_unusual_predicate_types, self._under_construction_or_predicate )
        
        AppendLoadingPredicate( stub_predicates )
        
        HG.client_controller.CallLaterQtSafe( self, 0.2, 'set stub predicates', self.SetStubPredicates, job_key, stub_predicates, parsed_autocomplete_text )
        
        fsc = self.GetFileSearchContext()
        
        if self._under_construction_or_predicate is None:
            
            under_construction_or_predicate = None
            
        else:
            
            under_construction_or_predicate = self._under_construction_or_predicate.Duplicate()
            
        
        HG.client_controller.CallToThread( ReadFetch, self, job_key, self.SetFetchedResults, parsed_autocomplete_text, self._media_callable, fsc, self._search_pause_play.IsOn(), self._include_unusual_predicate_types, self._results_cache, under_construction_or_predicate, self._force_system_everything )
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        looking_at_search_results = self._dropdown_notebook.currentWidget() == self._search_results_list
        
        something_to_broadcast = self._GetCurrentBroadcastTextPredicate() is not None
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        # the list has results, but they are out of sync with what we have currently entered
        # when the user has quickly typed something in and the results are not yet in
        results_desynced_with_text = parsed_autocomplete_text != self._current_list_parsed_autocomplete_text
        
        p1 = looking_at_search_results and something_to_broadcast and results_desynced_with_text
        
        return p1
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        current_broadcast_predicate = self._GetCurrentBroadcastTextPredicate()
        
        if current_broadcast_predicate is not None:
            
            self._BroadcastChoices( { current_broadcast_predicate }, shift_down )
            
        
    
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
            
        
    
    def GetFileSearchContext( self ) -> ClientSearch.FileSearchContext:
        
        fsc = self._file_search_context.Duplicate()
        
        fsc.SetPredicates( self._predicates_listbox.GetPredicates() )
        
        return fsc
        
    
    def GetPredicates( self ) -> typing.Set[ ClientSearch.Predicate ]:
        
        return self._predicates_listbox.GetPredicates()
        
    
    def IsSynchronised( self ):
        
        return self._search_pause_play.IsOn()
        
    
    def PauseSearching( self ):
        
        self._search_pause_play.SetOnOff( False )
        
    
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
            
            command_processed = AutoCompleteDropdownTags.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def SetFetchedResults( self, job_key: ClientThreading.JobKey, parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText, results_cache: ClientSearch.PredicateResultsCache, results: list ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            AutoCompleteDropdownTags.SetFetchedResults( self, job_key, parsed_autocomplete_text, results_cache, results )
            
            if parsed_autocomplete_text.IsEmpty():
                
                # refresh system preds after five mins
                
                self._ScheduleResultsRefresh( 300 )
                
            
        
    
    def SetFileSearchContext( self, file_search_context: ClientSearch.FileSearchContext ):
        
        self._ClearInput()
        
        self._CancelORConstruction()
        
        self._file_search_context = file_search_context.Duplicate()
        
        self._predicates_listbox.SetPredicates( self._file_search_context.GetPredicates() )
        
        self._ChangeLocationContext( self._file_search_context.GetLocationContext() )
        self._ChangeTagService( self._file_search_context.GetTagSearchContext().service_key )
        
        self._SignalNewSearchState()
        
    
    def SetIncludeCurrent( self, value ):
        
        self._file_search_context.SetIncludeCurrentTags( value )
        
        self._SetListDirty()
        
        self._SignalNewSearchState()
        
        self._RestoreTextCtrlFocus()
        
    
    def SetIncludePending( self, value ):
        
        self._file_search_context.SetIncludePendingTags( value )
        
        self._SetListDirty()
        
        self._SignalNewSearchState()
        
        self._RestoreTextCtrlFocus()
        
    
    def SetSynchronised( self, value ):
        
        self._SignalNewSearchState()
        
        self._RestoreTextCtrlFocus()
        
        if not self._search_pause_play.IsOn() and not self._file_search_context.GetSystemPredicates().HasSystemLimit():
            
            # update if user goes from sync to non-sync
            self._SetListDirty()
            
        
    
    def PausePlaySearch( self ):
        
        self._search_pause_play.Flip()
        
        self._RestoreTextCtrlFocus()
        
    
    def ShowCancelSearchButton( self, show ):
        
        if self._cancel_search_button.isVisible() != show:
            
            self._cancel_search_button.setVisible( show )
            
        
    
class ListBoxTagsActiveSearchPredicates( ClientGUIListBoxes.ListBoxTagsPredicates ):
    
    def __init__( self, parent: AutoCompleteDropdownTagsRead, page_key, initial_predicates = None ):
        
        if initial_predicates is None:
            
            initial_predicates = []
            
        
        ClientGUIListBoxes.ListBoxTagsPredicates.__init__( self, parent, height_num_chars = 6 )
        
        self._my_ac_parent = parent
        
        self._page_key = page_key
        
        if len( initial_predicates ) > 0:
            
            terms = [ self._GenerateTermFromPredicate( predicate ) for predicate in initial_predicates ]
            
            self._AppendTerms( terms )
            
            self._Sort()
            
            self._DataHasChanged()
            
        
        HG.client_controller.sub( self, 'EnterPredicates', 'enter_predicates' )
        
    
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
        
        ( editable_predicates, non_editable_predicates ) = ClientGUISearch.GetEditablePredicates( self._GetPredicatesFromTerms( self._selected_terms ) )
        
        if len( editable_predicates ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if len( editable_predicates ) == 1:
                
                desc = list( editable_predicates )[0].ToString()
                
            else:
                
                desc = '{} search terms'.format( HydrusData.ToHumanInt( len( editable_predicates ) ) )
                
            
            label = 'edit {}'.format( desc )
            
            ClientGUIMenus.AppendMenuItem( menu, label, 'Edit these predicates and refresh the search. Not all predicates are editable.', self._EditPredicates, editable_predicates )
            
        
    
    def _CanProvideCurrentPagePredicates( self ):
        
        return True
        
    
    def _DeleteActivate( self ):
        
        ctrl_down = False
        shift_down = False
        
        self._Activate( ctrl_down, shift_down )
        
    
    def _EditPredicates( self, predicates ):
        
        original_predicates = set( predicates )
        
        try:
            
            edited_predicates = set( ClientGUISearch.EditPredicates( self, predicates ) )
            
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
        
    
    def _EnterPredicates( self, predicates, permit_add = True, permit_remove = True ):
        
        if len( predicates ) == 0:
            
            return
            
        
        terms_to_be_added = set()
        terms_to_be_removed = set()
        
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
                    
                    terms_to_be_removed.update( ( self._GenerateTermFromPredicate( pred ) for pred in m_e_preds ) )
                    
                
            
        
        self._AppendTerms( terms_to_be_added )
        
        self._RemoveTerms( terms_to_be_removed )
        
        self._Sort()
        
        self._DataHasChanged()
        
    
    def _GetCurrentLocationContext( self ):
        
        return self._my_ac_parent.GetFileSearchContext().GetLocationContext()
        
    
    def _GetCurrentPagePredicates( self ) -> typing.Set[ ClientSearch.Predicate ]:
        
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
                
            
        elif command == 'remove_predicates':
            
            self._EnterPredicates( predicates, permit_add = False )
            
        elif command == 'add_inverse_predicates':
            
            self._EnterPredicates( inverse_predicates, permit_remove = False )
            
        elif command == 'remove_inverse_predicates':
            
            self._EnterPredicates( inverse_predicates, permit_add = False )
            
        elif command == 'add_namespace_predicate':
            
            self._EnterPredicates( ( namespace_predicate, ), permit_remove = False )
            
        elif command == 'add_inverse_namespace_predicate':
            
            self._EnterPredicates( ( inverse_namespace_predicate, ), permit_remove = False )
            
        
    
    def EnterPredicates( self, page_key, predicates, permit_add = True, permit_remove = True ):
        
        if page_key == self._page_key:
            
            self._EnterPredicates( predicates, permit_add = permit_add, permit_remove = permit_remove )
            
        
    
    def SetPredicates( self, predicates ):
        
        self._Clear()
        
        terms = [ self._GenerateTermFromPredicate( predicate ) for predicate in predicates ]
        
        self._AppendTerms( terms )
        
        self._Sort()
        
        self._DataHasChanged()
        
    
class AutoCompleteDropdownTagsWrite( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, chosen_tag_callable, location_context, tag_service_key, null_entry_callable = None, tag_service_key_changed_callable = None, show_paste_button = False ):
        
        self._display_tag_service_key = tag_service_key
        
        self._chosen_tag_callable = chosen_tag_callable
        self._null_entry_callable = null_entry_callable
        self._tag_service_key_changed_callable = tag_service_key_changed_callable
        
        service = HG.client_controller.services_manager.GetService( tag_service_key )
        
        tag_autocomplete_options = HG.client_controller.tag_display_manager.GetTagAutocompleteOptions( tag_service_key )
        
        ( location_context, tag_service_key ) = tag_autocomplete_options.GetWriteAutocompleteDomain( location_context )
        
        AutoCompleteDropdownTags.__init__( self, parent, location_context, tag_service_key )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self._text_input_panel, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( 'Paste from the clipboard and quick-enter as if you had typed. This can take multiple newline-separated tags.' )
        
        if not show_paste_button:
            
            self._paste_button.hide()
            
        
        QP.AddToLayout( self._text_input_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.setLayout( vbox )
        
    
    def _IsAllKnownFilesServiceTypeAllowed( self ):
        
        return self._allow_all_known_files
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        tags = { predicate.GetValue() for predicate in predicates }
        
        if len( tags ) > 0:
            
            self._chosen_tag_callable( tags )
            
        
        self._ClearInput()
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        AutoCompleteDropdownTags._ChangeTagService( self, tag_service_key )
        
        if self._tag_service_key_changed_callable is not None:
            
            self._tag_service_key_changed_callable( tag_service_key )
            
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> typing.Optional[ ClientSearch.Predicate ]:
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        if parsed_autocomplete_text.IsTagSearch():
            
            return parsed_autocomplete_text.GetImmediateFileSearchPredicate()
            
        else:
            
            return None
            
        
    
    def _GetParsedAutocompleteText( self ) -> ClientSearch.ParsedAutocompleteText:
        
        parsed_autocomplete_text = AutoCompleteDropdownTags._GetParsedAutocompleteText( self )
        
        parsed_autocomplete_text.SetInclusive( True )
        
        return parsed_autocomplete_text
        
    
    def _InitFavouritesList( self ):
        
        height_num_chars = HG.client_controller.new_options.GetInteger( 'ac_write_list_height_num_chars' )
        
        favs_list = ListBoxTagsStringsAC( self._dropdown_notebook, self.BroadcastChoices, self._display_tag_service_key, self._float_mode, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE, height_num_chars = height_num_chars )
        
        favs_list.SetChildRowsAllowed( HG.client_controller.new_options.GetBoolean( 'expand_parents_on_storage_autocomplete_taglists' ) )
        
        return favs_list
        
    
    def _InitSearchResultsList( self ):
        
        height_num_chars = HG.client_controller.new_options.GetInteger( 'ac_write_list_height_num_chars' )
        
        preds_list = ListBoxTagsPredicatesAC( self._dropdown_notebook, self.BroadcastChoices, self._display_tag_service_key, self._float_mode, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE, height_num_chars = height_num_chars )
        
        preds_list.SetChildRowsAllowed( HG.client_controller.new_options.GetBoolean( 'expand_parents_on_storage_autocomplete_taglists' ) )
        
        return preds_list
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            tags = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            tags = HydrusTags.CleanTags( tags )
            
            entry_predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, value = tag ) for tag in tags ]
            
            if len( entry_predicates ) > 0:
                
                shift_down = False
                
                self._BroadcastChoices( entry_predicates, shift_down )
                
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
            raise
            
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
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
        
    
    def _StartSearchResultsFetchJob( self, job_key ):
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        stub_predicates = []
        
        InsertTagPredicates( stub_predicates, self._display_tag_service_key, parsed_autocomplete_text )
        
        AppendLoadingPredicate( stub_predicates )
        
        HG.client_controller.CallLaterQtSafe( self, 0.2, 'set stub predicates', self.SetStubPredicates, job_key, stub_predicates, parsed_autocomplete_text )
        
        tag_search_context = ClientSearch.TagSearchContext( service_key = self._tag_service_key, display_service_key = self._display_tag_service_key )
        
        file_search_context = ClientSearch.FileSearchContext( location_context = self._location_context, tag_search_context = tag_search_context )
        
        HG.client_controller.CallToThread( WriteFetch, self, job_key, self.SetFetchedResults, parsed_autocomplete_text, file_search_context, self._results_cache )
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        if parsed_autocomplete_text.IsEmpty() and self._dropdown_notebook.currentWidget() == self._search_results_list:
            
            if self._null_entry_callable is not None:
                
                self._null_entry_callable()
                
            
        else:
            
            current_broadcast_predicate = self._GetCurrentBroadcastTextPredicate()
            
            if current_broadcast_predicate is not None:
                
                self._BroadcastChoices( { current_broadcast_predicate }, shift_down )
                
            
        
    
    def RefreshFavouriteTags( self ):
        
        favourite_tags = sorted( HG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
        
        self._favourites_list.SetTags( favourite_tags )
        
    
    def SetDisplayTagServiceKey( self, service_key ):
        
        self._display_tag_service_key = service_key
        
    
class EditAdvancedORPredicates( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, initial_string = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
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
        summary += os.linesep * 2
        summary += 'Accepted operators: not (!, -), and (&&), or (||), implies (=>), xor, xnor (iff, <=>), nand, nor.'
        summary += os.linesep * 2
        summary += 'Parentheses work the usual way. \\ can be used to escape characters (e.g. to search for tags including parentheses)'
        
        st = ClientGUICommon.BetterStaticText( self, summary )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._UpdateText()
        
        self._input_text.textChanged.connect( self.EventUpdateText )
        
    
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
                    
                    row_preds = []
                    
                    for tag_string in s:
                        
                        if tag_string.startswith( '-' ):
                            
                            inclusive = False
                            
                            tag_string = tag_string[1:]
                            
                        else:
                            
                            inclusive = True
                            
                        
                        if '*' in tag_string:
                            
                            ( namespace, subtag ) = HydrusTags.SplitTag( tag_string )
                            
                            if len( namespace ) > 0 and subtag == '*':
                                
                                row_pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, value = namespace, inclusive = inclusive )
                                
                            else:
                                
                                row_pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, value = tag_string, inclusive = inclusive )
                                
                            
                        else:
                            
                            row_pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, value = tag_string, inclusive = inclusive )
                            
                        
                        row_preds.append( row_pred )
                        
                    
                    if len( row_preds ) == 1:
                        
                        self._current_predicates.append( row_preds[0] )
                        
                    else:
                        
                        self._current_predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, value = row_preds ) )
                        
                    
                
                output = os.linesep.join( ( pred.ToString() for pred in self._current_predicates ) )
                object_name = 'HydrusValid'
                
            except ValueError:
                
                output = 'Could not parse!'
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
        
    
