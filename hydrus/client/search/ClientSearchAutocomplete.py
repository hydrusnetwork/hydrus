import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusTags

from hydrus.client.metadata import ClientTagsHandling
from hydrus.client.search import ClientSearch
from hydrus.client.search import ClientSearchParseSystemPredicates

def SearchTextIsFetchAll( search_text: str ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
    
    if namespace in ( '', '*' ) and subtag == '*':
        
        return True
        
    
    return False
    

def SearchTextIsNamespaceBareFetchAll( search_text: str ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
    
    if namespace not in ( '', '*' ) and subtag == '':
        
        return True
        
    
    return False
    

def SearchTextIsNamespaceFetchAll( search_text: str ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
    
    if namespace not in ( '', '*' ) and subtag == '*':
        
        return True
        
    
    return False
    

class ParsedAutocompleteText( object ):
    
    def __init__( self, raw_input: str, tag_autocomplete_options: ClientTagsHandling.TagAutocompleteOptions, collapse_search_characters: bool ):
        
        self.raw_input = raw_input
        self._tag_autocomplete_options = tag_autocomplete_options
        self._collapse_search_characters = collapse_search_characters
        
        self.inclusive = not self.raw_input.startswith( '-' )
        
        self.raw_content = HydrusTags.CleanTag( self.raw_input )
        
    
    def __eq__( self, other ):
        
        if isinstance( other, ParsedAutocompleteText ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.raw_input, self._collapse_search_characters ).__hash__()
        
    
    def __repr__( self ):
        
        return 'AC Tag Text: {}'.format( self.raw_input )
        
    
    def _GetSearchText( self, always_autocompleting: bool, force_do_not_collapse: bool = False, allow_auto_wildcard_conversion: bool = False ) -> str:
        
        text = ClientSearch.CollapseWildcardCharacters( self.raw_content )
        
        if len( text ) == 0:
            
            return ''
            
        
        if self._collapse_search_characters and not force_do_not_collapse:
            
            text = ClientSearch.ConvertTagToSearchable( text )
            
        
        if allow_auto_wildcard_conversion and self._tag_autocomplete_options.UnnamespacedSearchGivesAnyNamespaceWildcards():
            
            if ':' not in text:
                
                ( namespace, subtag ) = HydrusTags.SplitTag( text )
                
                if namespace == '':
                    
                    if subtag == '':
                        
                        return ''
                        
                    
                    text = '*:{}'.format( subtag )
                    
                
            
        
        if always_autocompleting:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( text )
            
            should_have_it = len( namespace ) > 0 or len( subtag ) > 0
            
            if should_have_it and not subtag.endswith( '*' ):
                
                text = '{}*'.format( text )
                
            
        
        return text
        
    
    def GetAddTagPredicate( self ):
        
        return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, self.raw_content, self.inclusive )
        
    
    def GetImmediateFileSearchPredicate( self, allow_auto_wildcard_conversion ):
        
        if self.IsValidSystemPredicate():
            
            return self.GetValidSystemPredicates()[0]
            
        
        non_tag_predicates = self.GetNonTagFileSearchPredicates( allow_auto_wildcard_conversion )
        
        if len( non_tag_predicates ) > 0:
            
            return non_tag_predicates[0]
            
        
        tag_search_predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, self.raw_content, self.inclusive )
        
        return tag_search_predicate
        
    
    def GetNonTagFileSearchPredicates( self, allow_auto_wildcard_conversion ):
        
        predicates = []
        
        if self.IsAcceptableForFileSearches() and not self.IsPossibleSystemPredicate():
            
            if self.IsNamespaceSearch():
                
                search_text = self._GetSearchText( False )
                
                ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
                
                predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, namespace, self.inclusive )
                
                predicates.append( predicate )
                
            elif self.IsExplicitWildcard( allow_auto_wildcard_conversion ):
                
                search_texts = []
                
                allow_unnamespaced_search_gives_any_namespace_wildcards_values = [ True ]
                always_autocompleting_values = [ True, False ]
                
                if '*' in self.raw_content:
                    
                    # don't spam users who type something with this setting turned on
                    allow_unnamespaced_search_gives_any_namespace_wildcards_values.append( False )
                    
                
                for allow_unnamespaced_search_gives_any_namespace_wildcards in allow_unnamespaced_search_gives_any_namespace_wildcards_values:
                    
                    for always_autocompleting in always_autocompleting_values:
                        
                        search_texts.append( self._GetSearchText( always_autocompleting, allow_auto_wildcard_conversion = allow_unnamespaced_search_gives_any_namespace_wildcards, force_do_not_collapse = True ) )
                        
                    
                
                for s in list( search_texts ):
                    
                    if ':' not in s:
                        
                        search_texts.append( '*:{}'.format( s ) )
                        
                    
                
                search_texts = HydrusData.DedupeList( search_texts )
                
                predicates.extend( ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, search_text, self.inclusive ) for search_text in search_texts ) )
                
            
        
        return predicates
        
    
    def GetSearchText( self, always_autocompleting: bool, allow_auto_wildcard_conversion = True ):
        
        return self._GetSearchText( always_autocompleting, allow_auto_wildcard_conversion = allow_auto_wildcard_conversion )
        
    
    def GetTagAutocompleteOptions( self ):
        
        return self._tag_autocomplete_options
        
    
    def IsAcceptableForTagSearches( self ):
        
        if self.IsPossibleSystemPredicate():
            
            return False
            
        
        search_text = self._GetSearchText( False, allow_auto_wildcard_conversion = True )
        
        if search_text == '':
            
            return False
            
        
        bnfa = SearchTextIsNamespaceBareFetchAll( search_text )
        nfa = SearchTextIsNamespaceFetchAll( search_text )
        fa = SearchTextIsFetchAll( search_text )
        
        bare_ok = self._tag_autocomplete_options.NamespaceBareFetchAllAllowed() or self._tag_autocomplete_options.SearchNamespacesIntoFullTags()
        namespace_ok = self._tag_autocomplete_options.NamespaceBareFetchAllAllowed() or self._tag_autocomplete_options.NamespaceFetchAllAllowed() or self._tag_autocomplete_options.SearchNamespacesIntoFullTags()
        fa_ok = self._tag_autocomplete_options.FetchAllAllowed()
        
        if bnfa and not bare_ok:
            
            return False
            
        
        if nfa and not namespace_ok:
            
            return False
            
        
        if fa and not fa_ok:
            
            return False
            
        
        return True
        
    
    def IsAcceptableForFileSearches( self ):
        
        if self.IsPossibleSystemPredicate():
            
            return self.IsValidSystemPredicate()
            
        
        search_text = self._GetSearchText( False, allow_auto_wildcard_conversion = True )
        
        if len( search_text ) == 0:
            
            return False
            
        
        if SearchTextIsFetchAll( search_text ):
            
            return False
            
        
        return True
        
    
    def IsEmpty( self ):
        
        return self.raw_input == ''
        
    
    def IsExplicitWildcard( self, allow_auto_wildcard_conversion ):
        
        # user has intentionally put a '*' in
        return '*' in self.raw_content or self._GetSearchText( False, allow_auto_wildcard_conversion = allow_auto_wildcard_conversion ).startswith( '*:' )
        
    
    def IsNamespaceSearch( self ):
        
        search_text = self._GetSearchText( False )
        
        return SearchTextIsNamespaceFetchAll( search_text ) or SearchTextIsNamespaceBareFetchAll( search_text )
        
    
    def IsTagSearch( self, allow_auto_wildcard_conversion ):
        
        if self.IsEmpty() or self.IsExplicitWildcard( allow_auto_wildcard_conversion ) or self.IsNamespaceSearch() or self.IsPossibleSystemPredicate():
            
            return False
            
        
        search_text = self._GetSearchText( False )
        
        if ClientSearch.SubtagIsEmpty( search_text ):
            
            return False
            
        
        return True
        
    
    def GetValidSystemPredicates( self ):
        
        try:
            
            results = ClientSearchParseSystemPredicates.ParseSystemPredicateStringsToPredicates( [ self.raw_input ] )
            
        except:
            
            results = []
            
        
        return results
        
    
    def IsPossibleSystemPredicate( self ):
        
        return self.raw_input.startswith( 'system:' )
        
    
    def IsValidSystemPredicate( self ):
        
        if self.IsPossibleSystemPredicate():
            
            try:
                
                result = self.GetValidSystemPredicates()
                
                if len( result ) > 0:
                    
                    return True
                    
                
            except:
                
                return False
                
            
        
        return False
        
    
    def SetInclusive( self, inclusive: bool ):
        
        self.inclusive = inclusive
        
    
class PredicateResultsCache( object ):
    
    def __init__( self, predicates: typing.Iterable[ ClientSearch.Predicate ] ):
        
        self._predicates = list( predicates )
        
    
    def CanServeTagResults( self, parsed_autocomplete_text: ParsedAutocompleteText, exact_match: bool, allow_auto_wildcard_conversion = True ):
        
        return False
        
    
    def FilterPredicates( self, service_key: bytes, search_text: str ):
        
        return ClientSearch.FilterPredicatesBySearchText( service_key, search_text, self._predicates )
        
    
    def GetPredicates( self ):
        
        return self._predicates
        
    
class PredicateResultsCacheInit( PredicateResultsCache ):
    
    def __init__( self ):
        
        PredicateResultsCache.__init__( self, [] )
        
    
class PredicateResultsCacheSystem( PredicateResultsCache ):
    
    pass
    
class PredicateResultsCacheMedia( PredicateResultsCache ):
    
    # we could do a bunch of 'valid while media hasn't changed since last time', but experimentally, this is swapped out with a system cache on every new blank input, so no prob
    pass
    
class PredicateResultsCacheTag( PredicateResultsCache ):
    
    def __init__( self, predicates: typing.Iterable[ ClientSearch.Predicate ], strict_search_text: str, exact_match: bool ):
        
        PredicateResultsCache.__init__( self, predicates )
        
        self._strict_search_text = strict_search_text
        
        ( self._strict_search_text_namespace, self._strict_search_text_subtag ) = HydrusTags.SplitTag( self._strict_search_text )
        
        self._exact_match = exact_match
        
    
    def CanServeTagResults( self, parsed_autocomplete_text: ParsedAutocompleteText, exact_match: bool, allow_auto_wildcard_conversion = True ):
        
        strict_search_text = parsed_autocomplete_text.GetSearchText( False, allow_auto_wildcard_conversion = allow_auto_wildcard_conversion )
        
        if self._exact_match:
            
            if exact_match and strict_search_text == self._strict_search_text:
                
                return True
                
            else:
                
                return False
                
            
        else:
            
            tag_autocomplete_options = parsed_autocomplete_text.GetTagAutocompleteOptions()
            
            ( strict_search_text_namespace, strict_search_text_subtag ) = HydrusTags.SplitTag( strict_search_text )
            
            #
            
            if SearchTextIsFetchAll( self._strict_search_text ):
                
                # if '*' searches are ok, we should have all results
                return tag_autocomplete_options.FetchAllAllowed()
                
            
            #
            
            subtag_to_namespace_search = self._strict_search_text_namespace == '' and self._strict_search_text_subtag != '' and strict_search_text_namespace != ''
            
            if subtag_to_namespace_search:
                
                # if a user searches 'char*' and then later 'character:samus*', we may have the results
                # namespace changed, so if we do not satisfy this slim case, we can't provide any results
                we_searched_namespace_as_subtag = strict_search_text_namespace.startswith( self._strict_search_text_subtag )
                
                return we_searched_namespace_as_subtag and tag_autocomplete_options.SearchNamespacesIntoFullTags()
                
            
            #
            
            if self._strict_search_text_namespace != strict_search_text_namespace:
                
                return False
                
            
            #
            
            # if user searched 'character:' or 'character:*', we may have the results
            # if we do, we have all possible results
            if SearchTextIsNamespaceBareFetchAll( self._strict_search_text ):
                
                return tag_autocomplete_options.NamespaceBareFetchAllAllowed()
                
            
            if SearchTextIsNamespaceFetchAll( self._strict_search_text ):
                
                return tag_autocomplete_options.NamespaceFetchAllAllowed()
                
            
            #
            
            # 'sam' will match 'samus', character:sam will match character:samus
            
            return strict_search_text_subtag.startswith( self._strict_search_text_subtag )
            
        
    
