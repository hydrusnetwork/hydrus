import os
import unittest

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client.metadata import ClientTagsHandling
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchAutocomplete
from hydrus.client.search import ClientSearchParseSystemPredicates
from hydrus.client.search import ClientSearchPredicate

class TestAutocompletePredGubbins( unittest.TestCase ):
    
    def test_parsed_autocomplete_text( self ):
        
        def bool_tests( pat: ClientSearchAutocomplete.ParsedAutocompleteText, values ):
            
            self.assertEqual( pat.IsAcceptableForFileSearches(), values[0] )
            self.assertEqual( pat.IsAcceptableForTagSearches(), values[1] )
            self.assertEqual( pat.IsEmpty(), values[2] )
            self.assertEqual( pat.IsExplicitWildcard( True ), values[3] )
            self.assertEqual( pat.IsNamespaceSearch(), values[4] )
            self.assertEqual( pat.IsTagSearch( True ), values[5] )
            self.assertEqual( pat.inclusive, values[6] )
            
        
        def search_text_tests( pat: ClientSearchAutocomplete.ParsedAutocompleteText, values ):
            
            self.assertEqual( pat.GetSearchText( False ), values[0] )
            self.assertEqual( pat.GetSearchText( True ), values[1] )
            
        
        def read_predicate_tests( pat: ClientSearchAutocomplete.ParsedAutocompleteText, values ):
            
            self.assertEqual( pat.GetImmediateFileSearchPredicate( True ), values[0] )
            self.assertEqual( pat.GetNonTagFileSearchPredicates( True ), values[1] )
            
        
        def write_predicate_tests( pat: ClientSearchAutocomplete.ParsedAutocompleteText, values ):
            
            self.assertEqual( pat.GetAddTagPredicate(), values[0] )
            
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ '', '' ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        search_text_tests( parsed_autocomplete_text, [ '', '' ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, False ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus', inclusive = False ), [] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus*', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 'samus*' ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 'samus*' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'character:samus', 'character:samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-character:samus ', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, False ] )
        search_text_tests( parsed_autocomplete_text, [ 'character:samus', 'character:samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus', inclusive = False ), [] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 's*s', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s', 's*s*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 's*s' ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 's*s' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-s*s', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, False ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s', 's*s*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 's*s', inclusive = False ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 's*s', inclusive = False ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'metroid' ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'metroid' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-metroid:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, False ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'metroid', inclusive = False ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'metroid', inclusive = False ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 's*s a*n', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s a*n', 's*s a*n*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 's*s a*n' ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 's*s a*n' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( ' samus ', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '[samus]', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, '[samus]' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, '[samus]' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'creator-id:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'creator-id' ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'creator-id' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'creator-id:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, True, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'creator-id' ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'creator-id' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'n*n g*s e*n:as*ka', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'n*n g*s e*n:as*ka', 'n*n g*s e*n:as*ka*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 'n*n g*s e*n:as*ka' ), [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 'n*n g*s e*n:as*ka' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'system:samus ', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        
        #
        #
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = True
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '*:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, True, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, True, False, True ] )
        
        #
        #
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = True
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '*:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, True, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, True, False, True ] )
        
        #
        #
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = True
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '*:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, True, False, True ] )
        
        #
        #
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = True
        fetch_all_allowed = True
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, True, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( '*:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, True, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, True, False, True ] )
        
    
    def test_predicate_results_cache_init( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheInit()
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
    
    def test_predicate_results_cache_system( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX ) ]
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheSystem( predicates )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
    
    def test_predicate_results_cache_subtag_normal( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        #
        
        predicates = [ samus, samus_aran, character_samus_aran ]
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, 'samus', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus*' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samas br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus ar*' ) ), { samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus aran*' ) ), { samus_aran, character_samus_aran } )
        
    
    def test_predicate_results_cache_subtag_exact( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ samus ]
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, 'samus', True )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus' ) ), { samus } )
        
    
    def test_predicate_results_cache_full_normal( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, 'character:samus', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'characte:samus aran*' ) ), set() )
        
    
    def test_predicate_results_cache_namespace_explicit_fetch_all( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, 'character:*', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        #
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = True
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
    
    def test_predicate_results_cache_namespace_bare_fetch_all( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, 'character:', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        #
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = True
        namespace_fetch_all_allowed = True
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
    
    def test_predicate_results_cache_namespaces_into_full_tags( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, 'char', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        #
        
        search_namespaces_into_full_tags = True
        namespace_bare_fetch_all_allowed = True
        namespace_fetch_all_allowed = True
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
    
    def test_predicate_results_cache_fetch_all_madness( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ samus, samus_aran, character_samus_aran ]
        
        predicate_results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, '*', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        #
        
        search_namespaces_into_full_tags = True
        namespace_bare_fetch_all_allowed = True
        namespace_fetch_all_allowed = True
        fetch_all_allowed = True
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteLocationContext(),
            tag_autocomplete_options.GetWriteAutocompleteLocationContext(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearchAutocomplete.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearchAutocomplete.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearchAutocomplete.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearchAutocomplete.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), True )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus*' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samas br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus ar*' ) ), { samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus aran*' ) ), { samus_aran, character_samus_aran } )
        
    
    def test_predicate_counts( self ):
        
        # quick test for counts and __hash__
        
        p_c = ClientSearchPredicate.PredicateCount( 1, 2, 3, 4 )
        
        self.assertEqual( p_c.min_current_count, 1 )
        self.assertEqual( p_c.min_pending_count, 2 )
        self.assertEqual( p_c.max_current_count, 3 )
        self.assertEqual( p_c.max_pending_count, 4 )
        
        self.assertNotEqual( p_c, ClientSearchPredicate.PredicateCount( 1, 2, 3, 5 ) )
        self.assertNotEqual( p_c, ClientSearchPredicate.PredicateCount( 1, 5, 3, 4 ) )
        self.assertEqual( p_c, ClientSearchPredicate.PredicateCount( 1, 2, 3, 4 ) )
        
        #
        
        null = ClientSearchPredicate.PredicateCount.STATICCreateNullCount()
        
        self.assertEqual( null, ClientSearchPredicate.PredicateCount( 0, 0, 0, 0 ) )
        self.assertEqual( null.GetMinCount(), 0 )
        self.assertEqual( null.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 0 )
        self.assertEqual( null.GetMinCount( HC.CONTENT_STATUS_PENDING ), 0 )
        self.assertEqual( null.HasZeroCount(), True )
        self.assertEqual( null.HasNonZeroCount(), False )
        self.assertEqual( null.GetSuffixString(), '' )
        
        #
        
        p_c = ClientSearchPredicate.PredicateCount( 3, 0, 3, 0 )
        
        self.assertEqual( p_c, ClientSearchPredicate.PredicateCount( 3, 0, 3, 0 ) )
        self.assertEqual( p_c.GetMinCount(), 3 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 3 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 0 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(3)' )
        
        #
        
        p_c = ClientSearchPredicate.PredicateCount( 0, 5, 0, 5 )
        
        self.assertEqual( p_c, ClientSearchPredicate.PredicateCount( 0, 5, 0, 5 ) )
        self.assertEqual( p_c.GetMinCount(), 5 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 0 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 5 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(+5)' )
        
        #
        
        p_c = ClientSearchPredicate.PredicateCount( 100, 0, 150, 0 )
        
        self.assertEqual( p_c, ClientSearchPredicate.PredicateCount( 100, 0, 150, 0 ) )
        self.assertEqual( p_c.GetMinCount(), 100 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 100 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 0 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(100-150)' )
        
        #
        
        p_c = ClientSearchPredicate.PredicateCount( 0, 80, 0, 85 )
        
        self.assertEqual( p_c, ClientSearchPredicate.PredicateCount( 0, 80, 0, 85 ) )
        self.assertEqual( p_c.GetMinCount(), 80 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 0 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 80 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(+80-85)' )
        
        #
        
        p_c = ClientSearchPredicate.PredicateCount( 0, 0, 1500, 0 )
        
        self.assertEqual( p_c, ClientSearchPredicate.PredicateCount( 0, 0, 1500, 0 ) )
        self.assertEqual( p_c.GetMinCount(), 0 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 0 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 0 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(0-1,500)' )
        
        #
        
        p_c = ClientSearchPredicate.PredicateCount( 1, 2, 3, 4 )
        
        self.assertEqual( p_c, ClientSearchPredicate.PredicateCount( 1, 2, 3, 4 ) )
        self.assertEqual( p_c.GetMinCount(), 3 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 2 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(1-3) (+2-4)' )
        
        #
        
        p_c_1 = ClientSearchPredicate.PredicateCount( 10, 2, 12, 4 )
        p_c_2 = ClientSearchPredicate.PredicateCount( 1, 0, 2, 4 )
        
        p_c_1.AddCounts( p_c_2 )
        
        self.assertEqual( p_c_1, ClientSearchPredicate.PredicateCount( 10, 2, 14, 8 ) )
        
    
    def test_predicate_strings_and_namespaces( self ):
        
        render_for_user = False
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'tag' )
        
        self.assertEqual( p.ToString(), 'tag' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'tag', True, count = ClientSearchPredicate.PredicateCount.STATICCreateStaticCount( 1, 2 ) )
        
        self.assertEqual( p.ToString( with_count = False ), 'tag' )
        self.assertEqual( p.ToString( with_count = True ), 'tag (1) (+2)' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'tag', False )
        
        self.assertEqual( p.ToString(), '-tag' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'tag', False, count = ClientSearchPredicate.PredicateCount.STATICCreateStaticCount( 1, 2 ) )
        
        self.assertEqual( p.ToString( with_count = False ), '-tag' )
        self.assertEqual( p.ToString( with_count = True ), '-tag (1) (+2)' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( '<', 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:import time: since 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( HC.UNICODE_APPROX_EQUAL, 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:import time: around 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( '>', 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:import time: before 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE, count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1000 ) )
        
        self.assertEqual( p.ToString(), 'system:archive (1,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 200 ) )
        
        self.assertEqual( p.ToString(), 'system:duration < 200 milliseconds' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING, count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 2000 ) )
        
        self.assertEqual( p.ToString(), 'system:everything (2,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is currently in my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_DELETED, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is deleted from my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is not pending to my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PETITIONED, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is not petitioned from my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True )
        
        self.assertEqual( p.ToString(), 'system:has audio' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False )
        
        self.assertEqual( p.ToString(), 'system:no audio' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, True )
        
        self.assertEqual( p.ToString(), 'system:has transparency' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, False )
        
        self.assertEqual( p.ToString(), 'system:no transparency' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, True )
        
        self.assertEqual( p.ToString(), 'system:has exif' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, False )
        
        self.assertEqual( p.ToString(), 'system:no exif' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, True )
        
        self.assertEqual( p.ToString(), 'system:has embedded metadata' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, False )
        
        self.assertEqual( p.ToString(), 'system:no embedded metadata' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, True )
        
        self.assertEqual( p.ToString(), 'system:has icc profile' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, False )
        
        self.assertEqual( p.ToString(), 'system:no icc profile' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, True )
        
        self.assertEqual( p.ToString(), 'system:has forced filetype' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, False )
        
        self.assertEqual( p.ToString(), 'system:no forced filetype' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, ( ( bytes.fromhex( 'abcd' ), ), 'sha256' ) )
        
        self.assertEqual( p.ToString(), 'system:hash is abcd' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 2000 ) )
        
        self.assertEqual( p.ToString(), 'system:height < 2,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX, count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1000 ) )
        
        self.assertEqual( p.ToString(), 'system:inbox (1,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, 2000 )
        
        self.assertEqual( p.ToString(), 'system:limit is 2,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LOCAL, count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 100 ) )
        
        self.assertEqual( p.ToString(), 'system:local (100)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, set( HC.IMAGES ).intersection( HC.SEARCHABLE_MIMES ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is image' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, ( HC.VIDEO_WEBM, ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is webm' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, ( HC.VIDEO_WEBM, HC.ANIMATION_GIF ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is animated gif, webm' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, ( HC.GENERAL_AUDIO, HC.GENERAL_VIDEO ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is audio, video' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 100 ) )
        
        self.assertEqual( p.ToString(), 'system:not local (100)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '*', '<', 2 ) )
        
        self.assertEqual( p.ToString(), 'system:number of tags < 2' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 2 ) )
        
        self.assertEqual( p.ToString(), 'system:number of character tags < 2' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 5 ) )
        
        self.assertEqual( p.ToString(), 'system:number of urls < 5' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 5000 ) )
        
        self.assertEqual( p.ToString(), 'system:number of words < 5,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        from hydrus.test import TestController
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.2, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:rating for example local rating numerical service more than 1/5' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 3, TestController.LOCAL_RATING_INCDEC_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:count for example local rating inc/dec service more than 3' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 16, 9 ) )
        
        self.assertEqual( p.ToString(), 'system:ratio = 16:9' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES, ( ( bytes.fromhex( 'abcd' ), ), 5 ) )
        
        self.assertEqual( p.ToString(), 'system:similar to 1 files with distance of 5' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA, ( ( os.urandom( 32 ), ), ( os.urandom( 32 ), ), 2 ) )
        
        self.assertEqual( p.ToString(), 'system:similar to data (1 pixel, 1 perceptual hashes) with distance of 2' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5, 1048576 ) )
        
        self.assertEqual( p.ToString(), 'system:filesize > 5MB' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 1920 ) )
        
        self.assertEqual( p.ToString(), 'system:width = 1,920' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, 'series' )
        
        self.assertEqual( p.ToString(), 'series:*anything*' )
        self.assertEqual( p.GetNamespace(), 'series' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'series', False )
        
        self.assertEqual( p.ToString(), '-series' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_WILDCARD, 'a*i:o*' )
        
        self.assertEqual( p.ToString(), 'a*i:o* (wildcard search)' )
        self.assertEqual( p.GetNamespace(), '*' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'a*i:o*', False )
        
        self.assertEqual( p.ToString(), '-a*i:o*' )
        self.assertEqual( p.GetNamespace(), '*' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_PARENT, 'series:game of thrones' )
        
        self.assertEqual( p.ToString(), '    series:game of thrones' )
        self.assertEqual( p.GetNamespace(), 'series' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), 'namespace', p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 2000 ) ), ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'blue eyes' ), ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'character:samus aran' ) ] )
        
        self.assertEqual( p.ToString(), 'blue eyes OR character:samus aran OR system:height < 2,000' )
        self.assertEqual( p.GetNamespace(), '' )
        
        or_texts_and_namespaces = []
        
        or_texts_and_namespaces.append( ( 'OR:', 'or', 'system' ) )
        
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), or_texts_and_namespaces )
        
    
    def test_system_predicate_parsing( self ):
        
        for ( expected_result_text, sys_pred_text ) in [
            ( 'system:similar to 4 files with distance of 3', "system:similar to e2c1592ce2a3338767bb7990738ae06357cbdfe917669da9a0d04069f9759c08 e2c1592ce2a3338767bb7990738ae06357cbdfe917669da9a0d04069f9759c09 e2c1592ce2a3338767bb7990738ae06357cbdfe917669da9a0d04069f9759c10, e2c1592ce2a3338767bb7990738ae06357cbdfe917669da9a0d04069f9759c11 with distance 3" ),
            ( 'system:similar to 1 files with distance of 5', "system:similar to e2c1592ce2a3338767bb7990738ae06357cbdfe917669da9a0d04069f9759c00 distance 5" ),
            ( 'system:similar to 1 files with distance of 4', "system:similar to e2c1592ce2a3338767bb7990738ae06357cbdfe917669da9a0d04069f9759c00" ),
            ( 'system:similar to 1 files with distance of 5', "system:similar to e2c1592ce2a3338767bb7990738ae06357cbdfe917669da9a0d04069f9759c00 with distance of 5" ),
            ( 'system:similar to data (2 pixel hashes)', "system:similar to data b51d75120456d6e2155416f26416a96290b0a524bf1582af50b4fcf46dedcd91 b51d75120456d6e2155416f26416a96290b0a524bf1582af50b4fcf46dedcd92 distance 4" ),
            ( 'system:similar to data (2 pixel hashes)', "system:similar to data b51d75120456d6e2155416f26416a96290b0a524bf1582af50b4fcf46dedcd91 b51d75120456d6e2155416f26416a96290b0a524bf1582af50b4fcf46dedcd92" ),
            ( 'system:similar to data (2 perceptual hashes) with distance of 4', "system:similar to data 0702790ffeae5c8a 51ad07c228ab7469 distance 4" ),
            ( 'system:similar to data (2 perceptual hashes) with distance of 8', "system:similar to data 0702790ffeae5c8a 51ad07c228ab7469" ),
            ( 'system:similar to data (2 pixel, 2 perceptual hashes) with distance of 4', "system:similar to data b51d75120456d6e2155416f26416a96290b0a524bf1582af50b4fcf46dedcd91 b51d75120456d6e2155416f26416a96290b0a524bf1582af50b4fcf46dedcd92 51ad07c228ab7469 0702790ffeae5c8a distance 4" ),
            ( 'system:everything', "system:everything" ),
            ( 'system:inbox', "system:inbox  " ),
            ( 'system:archive', "system:archive " ),
            ( 'system:archive', "system:archived " ),
            ( 'system:archive', "system:archived" ),
            ( 'system:has duration', "system:has duration" ),
            ( 'system:has duration', "system:has_duration" ),
            ( 'system:no duration', "   system:no_duration" ),
            ( 'system:no duration', "system:no duration" ),
            ( 'system:has duration', "system:duration: has duration" ),
            ( 'system:no duration', "system:duration: no duration" ),
            ( 'system:has framerate', "system:has framerate" ),
            ( 'system:has framerate', "system:has_framerate" ),
            ( 'system:no framerate', "   system:no_framerate" ),
            ( 'system:no framerate', "system:no framerate" ),
            ( 'system:has framerate', "system:framerate: has framerate" ),
            ( 'system:no framerate', "system:framerate: no framerate" ),
            ( 'system:has frames', "system:has frames" ),
            ( 'system:has frames', "system:has_frames" ),
            ( 'system:no frames', "   system:no_frames" ),
            ( 'system:no frames', "system:no frames" ),
            ( 'system:has frames', "system:number of frames: has frames" ),
            ( 'system:no frames', "system:number of frames: no frames" ),
            ( 'system:has width', "system:has width" ),
            ( 'system:has width', "system:has_width" ),
            ( 'system:no width', "   system:no_width" ),
            ( 'system:no width', "system:no width" ),
            ( 'system:has width', "system:width: has width" ),
            ( 'system:no width', "system:width: no width" ),
            ( 'system:has height', "system:has height" ),
            ( 'system:has height', "system:has_height" ),
            ( 'system:no height', "   system:no_height" ),
            ( 'system:no height', "system:no height" ),
            ( 'system:has height', "system:height: has height" ),
            ( 'system:no height', "system:height: no height" ),
            ( 'system:has notes', "system:has notes" ),
            ( 'system:has notes', "system:has_notes" ),
            ( 'system:no notes', "   system:no_notes" ),
            ( 'system:no notes', "system:no notes" ),
            ( 'system:has notes', "system:number of notes: has notes" ),
            ( 'system:no notes', "system:number of notes: no notes" ),
            ( 'system:has urls', "system:has urls" ),
            ( 'system:has urls', "system:has_urls" ),
            ( 'system:no urls', "   system:no_urls" ),
            ( 'system:no urls', "system:no urls" ),
            ( 'system:has urls', "system:number of urls: has urls" ),
            ( 'system:no urls', "system:number of urls: no urls" ),
            ( 'system:has words', "system:has words" ),
            ( 'system:has words', "system:has_words" ),
            ( 'system:no words', "   system:no_words" ),
            ( 'system:no words', "system:no words" ),
            ( 'system:has words', "system:number of words: has words" ),
            ( 'system:no words', "system:number of words: no words" ),
            ( 'system:is the best quality file of its duplicate group', "system:is the best quality file  of its group" ),
            ( 'system:is not the best quality file of its duplicate group', "system:isn't the best quality file of its duplicate group" ),
            ( 'system:is not the best quality file of its duplicate group', 'system:is not the best quality file of its duplicate group' ),
            ( 'system:has audio', "system:has_audio" ),
            ( 'system:no audio', "system:no audio" ),
            ( 'system:has tags', "system:has tags" ),
            ( 'system:untagged', "system:no tags" ),
            ( 'system:untagged', "system:untagged" ),
            ( 'system:has embedded metadata', "system:has human readable embedded metadata" ),
            ( 'system:no embedded metadata', "system:no human readable embedded metadata" ),
            ( 'system:has embedded metadata', "system:has human-readable embedded metadata" ),
            ( 'system:no embedded metadata', "system:no human-readable embedded metadata" ),
            ( 'system:has embedded metadata', "system:has embedded metadata" ),
            ( 'system:no embedded metadata', "system:no embedded metadata" ),
            ( 'system:has icc profile', "system:has icc profile" ),
            ( 'system:no icc profile', "system:no icc profile" ),
            ( 'system:has forced filetype', "system:has forced filetype" ),
            ( 'system:no forced filetype', "system:no forced filetype" ),
            ( 'system:number of tags > 5', "system:number of tags > 5" ),
            ( 'system:number of character tags > 5', "system:number of character tags > 5" ),
            ( f'system:number of tags {HC.UNICODE_APPROX_EQUAL} 10', "system:number of tags ~= 10" ),
            ( 'system:has tags', "system:number of tags > 0  " ),
            ( 'system:number of urls < 2', 'system:number of urls < 2' ),
            ( 'system:number of urls < 2', 'system:num urls < 2' ),
            ( 'system:has urls', 'system:num urls > 0' ),
            ( 'system:no urls', 'system:num urls = 0' ),
            ( 'system:number of urls < 2', 'system:number of urls < 2' ),
            ( 'system:number of urls < 2', 'system:num urls < 2' ),
            ( 'system:has words', 'system:num words > 0' ),
            ( 'system:no words', 'system:num words = 0' ),
            ( 'system:height = 600', "system:height = 600px" ),
            ( 'system:height = 800', "system:height is 800" ),
            ( 'system:height > 900', "system:height > 900" ),
            ( 'system:width < 200', "system:width < 200" ),
            ( 'system:width > 1,000', "system:width > 1000 pixels" ),
            ( f'system:filesize {HC.UNICODE_APPROX_EQUAL} 50KB', "system:filesize ~= 50 kilobytes" ),
            ( 'system:filesize > 10MB', "system:filesize > 10megabytes" ),
            ( 'system:filesize < 1GB', "system:file size    < 1 GB" ),
            ( 'system:filesize > 0B', "system:file size > 0 B" ),
            ( 'system:limit is 5,000', "system:limit is 5000" ),
            ( 'system:limit is 100', "system:limit = 100" ),
            ( 'system:filetype is jpeg', "system:filetype is jpeg" ),
            ( 'system:filetype is not jpeg', "system:filetype is not jpeg" ),
            ( 'system:filetype is apng, jpeg, png', "system:filetype =   image/jpg, image/png, apng" ),
            ( 'system:filetype is image', "system:filetype is image" ),
            ( 'system:filetype is animated gif, static gif, jpeg', "system:filetype =   static gif, animated gif, jpeg" ),
            ( 'system:hash is in 3 hashes', "system:hash = cf09faad262075f96bf9a30052b8ec224e096948a4f3a2776df5fa5a777bcfd8 a1b0ab771d11d9a6d1f993efee9d253d3aa78914387a7c8ceab520af88ab3de2 98a7d2f4735a5fcc70e7c94e2dadcc6ea45123fb2035b9cfe7ad1d78e48cae9e" ),
            ( 'system:hash (md5) is in 3 hashes', "system:hash = ada7a31713ba24652c52e52c6f212e47 546fd4b8c39fc53e77e2f28b59cd1b18, cec888bacb79825621738454a4c9d226 md5" ),
            ( 'system:hash (md5) is 666d0a395c8d4eebb5b15a0771972a01', "system:hash (md5) = 666d0a395c8d4eebb5b15a0771972a01" ),
            ( 'system:hash (md5) is 123fec741ebe7596c1faf8d7689693b8', "system:Hash = 123feC741ebe7596c1faf8d7689693b8 md5" ),
            ( 'system:hash (sha1) is not 2496baf1ded134b5ff7e44f72155240b9561ab5a', "system:Hash (sha1) != 2496baf1ded134b5ff7e44f72155240b9561ab5a" ),
            ( 'system:hash is not b49f25453c6351403d62cc4d065321106c90f98b5653e83d289dbe0d55ba8c94', "system:Hash is not b49f25453c6351403d62cc4d065321106c90f98b5653e83d289dbe0d55ba8c94 sha256" ),
            ( 'system:hash is 4d4ff3d42459f824295a36138782c444028f533b6ae5f0f67b27e9bf3c93de5d', "system:hash = 4d4ff3d42459f824295a36138782c444028f533b6ae5f0f67b27e9bf3c93de5d" ),
            ( 'system:archived time: since 60 days ago', "system:archived date < 60 days" ),
            ( 'system:archived time: since 60 days ago', "system:archive date < 60 days" ),
            ( 'system:archived time: since 60 days ago', "system:archived time < 60 days" ),
            ( 'system:archived time: since 60 days ago', "system:archive time < 60 days" ),
            ( 'system:archived time: since 60 days ago', "system:date archived < 60 days" ),
            ( 'system:archived time: since 60 days ago', "system:time archived < 60 days" ),
            ( 'system:archived time: since 60 days ago', "system:archived < 60 days" ),
            ( 'system:modified time: since 60 days ago', "system:modified date < 60 days" ),
            ( 'system:modified time: since 2011-06-04', "system:modified date > 2011-06-04" ),
            ( 'system:modified time: before 60 days 4 hours ago', "system:date modified > 60 days 4    hours" ),
            ( 'system:modified time: since 1 day ago', "system:date modified < 1 day" ),
            ( 'system:modified time: since 1 day ago', "system:time modified < 1 day" ),
            ( 'system:modified time: since 1 day ago', "system:modified date < 1 day" ),
            ( 'system:modified time: since 1 day ago', "system:modified time < 1 day" ),
            ( 'system:last viewed time: since 60 days ago', "system:last viewed time < 60 days" ),
            ( 'system:last viewed time: since 60 days ago', "system:last viewed date < 60 days" ),
            ( 'system:last viewed time: since 60 days ago', "system:last view time < 60 days" ),
            ( 'system:last viewed time: since 60 days ago', "system:last view date < 60 days" ),
            ( 'system:last viewed time: since 60 days ago', "system:time last viewed < 60 days" ),
            ( 'system:last viewed time: since 60 days ago', "system:date last viewed < 60 days" ),
            ( 'system:import time: since 60 days ago', "system:time_imported < 60 days" ),
            ( 'system:import time: since 2011-06-04', "system:time imported > 2011-06-04" ),
            ( 'system:import time: before 60 days 4 hours ago', "system:time imported > 60 days 4 hours" ),
            ( 'system:import time: before 60 days 4 hours ago', "system:time imported > 60 days 4 hours" ),
            ( 'system:import time: since 1 day ago', "system:time imported < 1 day" ),
            ( 'system:import time: a month either side of 2011-01-03', " system:time imported ~= 2011-1-3 " ),
            ( 'system:import time: a month either side of 1996-05-02', "system:time imported ~= 1996-05-2" ),
            ( 'system:import time: since 60 days ago', "system:import_time < 60 days" ),
            ( 'system:import time: since 2011-06-04', "system:import time > 2011-06-04" ),
            ( 'system:import time: before 60 days 4 hours ago', "system:import time > 60 days 4 hours" ),
            ( 'system:import time: around 1 day ago', "system:import time = 1 day" ),
            ( 'system:import time: a month either side of 2011-01-03', " system:import time ~= 2011-1-3 " ),
            ( 'system:import time: a month either side of 1996-05-02', "system:import time ~= 1996-05-2" ),
            ( 'system:import time: since 1 day ago', "system:import time < 1 day" ),
            ( 'system:import time: since 1 day ago', "system:imported time < 1 day" ),
            ( 'system:import time: since 1 day ago', "system:import date < 1 day" ),
            ( 'system:import time: since 1 day ago', "system:imported date < 1 day" ),
            ( 'system:import time: since 1 day ago', "system:time imported < 1 day" ),
            ( 'system:import time: since 1 day ago', "system:date imported < 1 day" ),
            ( 'system:import time: a month either side of 2020-01-03', "system:import time: the month of 2020-01-03" ),
            ( 'system:import time: on the day of 2020-01-03', "system:import time: the day of 2020-01-03" ),
            ( 'system:import time: around 7 days ago', "system:date imported around 7 days ago" ),
            ( 'system:duration < 5 seconds', "system:duration < 5 seconds" ),
            ( f'system:duration {HC.UNICODE_APPROX_EQUAL} 11 seconds {HC.UNICODE_PLUS_OR_MINUS}15%', "system:duration ~= 5 sec 6000 msecs" ),
            ( 'system:duration > 3 milliseconds', "system:duration > 3 milliseconds" ),
            ( 'system:duration > 5 minutes 30 seconds', "system:duration > 5m30s" ),
            ( 'system:duration > 5 minutes 0 seconds', "system:duration > 300 seconds" ),
            ( 'system:duration > 5 minutes 0 seconds', "system:duration > 5 minutes" ),
            ( 'system:framerate < 60fps', "system:framerate < 60fps" ),
            ( f'system:framerate {HC.UNICODE_APPROX_EQUAL} 12fps {HC.UNICODE_PLUS_OR_MINUS}15%', "system:framerate ~= 12fps" ),
            ( 'system:number of frames < 600', "system:number of frames < 600" ),
            ( f'system:number of frames {HC.UNICODE_APPROX_EQUAL} 120 {HC.UNICODE_PLUS_OR_MINUS}15%', "system:number of frames ~= 120" ),
            ( 'system:is pending to my files', "system:file service is pending to my files" ),
            ( 'system:is pending to my files', "system:file service is pending to MY FILES" ),
            ( 'system:is currently in my files', "   system:file service currently in my files" ),
            ( 'system:is not currently in my files', "system:file service isn't currently in my files" ),
            ( 'system:is not pending to my files', "system:file service is not pending to my files" ),
            ( 'system:num file relationships - has less than 3 alternates', "system:num file relationships < 3 alternates" ),
            ( 'system:num file relationships - has more than 3 not related/false positive', "system:number of file relationships > 3 false positives" ),
            ( 'system:ratio wider than 16:9', "system:ratio is wider than 16:9        " ),
            ( 'system:ratio = 16:9', "system:ratio is 16:9" ),
            ( 'system:ratio is portrait', "system:ratio taller than 1:1" ),
            ( 'system:ratio is square', "system:ratio is square" ),
            ( 'system:ratio is portrait', "system:ratio is portrait" ),
            ( 'system:ratio is landscape', "system:ratio is landscape" ),
            ( 'system:number of pixels > 50 pixels', "system:num pixels > 50 px" ),
            ( 'system:number of pixels < 1 megapixels', "system:num pixels < 1 megapixels " ),
            ( f'system:number of pixels {HC.UNICODE_APPROX_EQUAL} 5 kilopixels', "system:num pixels ~= 5 kilopixel" ),
            ( 'system:number of pixels > 50 pixels', "system:number pixels > 50 px" ),
            ( 'system:number of pixels < 1 megapixels', "system:num of pixels < 1 megapixels " ),
            ( f'system:number of pixels {HC.UNICODE_APPROX_EQUAL} 5 kilopixels', "system:number of pixels ~= 5 kilopixel" ),
            ( f'system:views in media {HC.UNICODE_APPROX_EQUAL} 10', "system:media views ~= 10" ),
            ( "system:views in media, preview > 0", 'system:all views > 0' ),
            ( 'system:views in preview < 10', "system:preview views < 10  " ),
            ( 'system:viewtime in media < 1 day 1 hour', "system:media viewtime < 1 days 1 hour 0 minutes" ),
            ( 'system:viewtime in media, preview > 1 hour 1 minute', "system:all viewtime > 1 hours 100 seconds" ),
            ( f'system:viewtime in preview {HC.UNICODE_APPROX_EQUAL} 2 days 7 hours', "system:preview viewtime ~= 1 day 30 hours 100 minutes 90s" ),
            ( 'system:views in media, preview > 0', 'system:views in media, preview > 0' ),
            ( 'system:views in client api = 5', 'system:views in client api = 5' ),
            ( 'system:viewtime in media, preview > 1 hour', 'system:viewtime in media, preview > 1 hour' ),
            ( 'system:viewtime in client api > 1 second', 'system:viewtime in client api > 1 second' ),
            ( 'system:has url matching regex index\\.php', " system:has url matching regex index\\.php" ),
            ( 'system:does not have url matching regex index\\.php', "system:does not have a url matching regex index\\.php" ),
            ( 'system:has url https://safebooru.donmai.us/posts/4695284', "system:has_url https://safebooru.donmai.us/posts/4695284" ),
            ( 'system:does not have url https://safebooru.donmai.us/posts/4695284', " system:doesn't have url https://safebooru.donmai.us/posts/4695284  " ),
            ( 'system:has url with domain safebooru.com', "system:has domain safebooru.com" ),
            ( 'system:does not have url with domain safebooru.com', "system:doesn't have domain safebooru.com" ),
            ( 'system:has url with class safebooru file page', "system:has url with class safebooru file page" ),
            ( 'system:does not have url with class safebooru file page', "system:doesn't have a url with url class safebooru file page " ),
            ( 'system:tag as number: page less than 5', "system:tag as number page < 5" ),
            ( 'system:tag as number: page less than 5', "system:tag as number: page less than 5" ),
            ( 'system:tag as number: page_underscore less than 5', "system:tag as number page_underscore < 5" ),
            ( 'system:number of notes = 5', 'system:num notes = 5' ),
            ( 'system:number of notes > 1', 'system:number of notes > 1' ),
            ( 'system:has notes', 'system:number of notes > 0' ),
            ( 'system:no notes', 'system:number of notes = 0' ),
            ( 'system:has note with name "test"', 'system:has note with name test' ),
            ( 'system:has note with name "test"', 'system:has a note with name test' ),
            ( 'system:has note with name "test"', 'system:note with name test' ),
            ( 'system:has note with name "test"', 'system:note with name "test"' ),
            ( 'system:does not have note with name "test"', 'system:no note with name test' ),
            ( 'system:does not have note with name "test"', 'system:does not have note with name test' ),
            ( 'system:does not have note with name "test"', 'system:doesn\'t have note with name test' ),
            ( 'system:does not have note with name "test"', 'system:does not have a note with name test' ),
            ( 'system:does not have note with name "test"', 'system:does not have a note with name "test"' ),
            ( 'system:has rating for example local rating numerical service', 'system:has rating example local rating numerical service' ),
            ( 'system:has rating for example local rating numerical service', 'system:has a rating for example local rating numerical service' ),
            ( 'system:no rating for example local rating numerical service', 'system:no rating example local rating numerical service' ),
            ( 'system:no rating for example local rating numerical service', 'system:does not have a rating for example local rating numerical service' ),
            ( 'system:rating for example local rating numerical service is 3/5', 'system:rating for example local rating numerical service = 3/5' ),
            ( 'system:rating for example local rating numerical service is 3/5', 'system:rating for example local rating numerical service is 3/5' ),
            ( f'system:rating for example local rating numerical service is about 3/5', f'system:rating for example local rating numerical service {HC.UNICODE_APPROX_EQUAL} 3/5' ),
            ( f'system:rating for example local rating numerical service is about 3/5', 'system:rating for example local rating numerical service about 3/5' ),
            ( 'system:rating for example local rating numerical service less than 3/5', 'system:rating for example local rating numerical service < 3/5' ),
            ( 'system:rating for example local rating numerical service less than 3/5', 'system:rating for example local rating numerical service less than 3/5' ),
            ( 'system:rating for example local rating numerical service more than 3/5', 'system:rating for example local rating numerical service > 3/5' ),
            ( 'system:rating for example local rating numerical service more than 3/5', 'system:rating for example local rating numerical service more than 3/5' ),
            ( 'system:rating for example local rating like service is like', 'system:rating for example local rating like service = like' ),
            ( 'system:rating for example local rating like service is dislike', 'system:rating for example local rating like service = dislike' ),
            ( 'system:has count for example local rating inc/dec service', 'system:has rating for example local rating inc/dec service' ),
            ( 'system:has count for example local rating inc/dec service', 'system:has a rating for example local rating inc/dec service' ),
            ( 'system:no count for example local rating inc/dec service', 'system:no rating for example local rating inc/dec service' ),
            ( 'system:no count for example local rating inc/dec service', 'system:does not have a rating for example local rating inc/dec service' ),
            ( 'system:count for example local rating inc/dec service is 123', 'system:rating for example local rating inc/dec service = 123' ),
            ( 'system:count for example local rating inc/dec service more than 123', 'system:rating for example local rating inc/dec service > 123' ),
            ( 'system:count for example local rating inc/dec service more than 123', 'system:rating example local rating inc/dec service more than 123' ),
            ( 'system:count for example local rating inc/dec service less than 123', 'system:rating for example local rating inc/dec service < 123' ),
            ( 'system:count for example local rating inc/dec service less than 123', 'system:rating for example local rating inc/dec service less than 123' ),
            ( f'system:count for example local rating inc/dec service is about 123', f'system:rating for example local rating inc/dec service {HC.UNICODE_APPROX_EQUAL} 123' ),
            ( f'system:count for example local rating inc/dec service is about 123', 'system:rating for example local rating inc/dec service is about 123' ),
            ( 'system:has tag: "skirt"', 'system:has tag: "skirt"' ),
            ( 'system:does not have tag: "skirt"', 'system:does not have tag: "skirt"' ),
            ( 'system:has tag in "my tags", ignoring siblings/parents: "skirt"', 'system:has tag in "my tags", ignoring siblings/parents, status current, pending: "skirt"' ),
            ( 'system:has tag in "all known tags", with status deleted: "filename:blarg"', 'system:has tag "all known tags", status deleted: "filename:blarg"' ),
            ( 'system:has tag in "all known tags", with status in current, pending, deleted, petitioned: "filename:blarg"', 'system:has tag "all known tags", deleted, current, pending, petitioned: "filename:blarg"' ),
            ( 'system:all ratings rated', 'system:all ratings rated' ),
            ( 'system:all ratings not rated', 'system:all ratings not rated' ),
            ( 'system:any ratings rated', 'system:any ratings rated' ),
            ( 'system:any ratings not rated', 'system:any ratings not rated' ),
            ( 'system:all inc/dec ratings rated', 'system:all inc/dec ratings rated' ),
            ( 'system:all inc/dec ratings not rated', 'system:all inc/dec ratings not rated' ),
            ( 'system:only inc/dec ratings rated', 'system:only inc/dec ratings rated' ),
            ( 'system:only inc/dec ratings not rated', 'system:only inc/dec ratings not rated' ),
            ( 'system:only inc/dec ratings (amongst inc/dec ratings, numerical ratings) not rated', 'system:only inc/dec ratings (amongst inc/dec ratings, numerical ratings) not rated' ),
            ( 'system:only 2 services rated', 'system:only example local rating numerical service, example local rating like service rated' ),
            ( 'system:only example local rating numerical service (amongst inc/dec ratings, numerical ratings) rated', 'system:only example local rating numerical service (amongst inc/dec ratings, numerical ratings) rated' ),
        ]:
            
            ( sys_pred, ) = ClientSearchParseSystemPredicates.ParseSystemPredicateStringsToPredicates( ( sys_pred_text, ) )
            
            self.assertEqual( sys_pred.ToString(), expected_result_text )
            
        
    
    def test_tag_import_options_simple( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        self.assertTrue( tag_autocomplete_options.FetchResultsAutomatically() )
        self.assertEqual( tag_autocomplete_options.GetExactMatchCharacterThreshold(), 2 )
        
        #
        
        tag_autocomplete_options.SetFetchResultsAutomatically( False )
        
        self.assertFalse( tag_autocomplete_options.FetchResultsAutomatically() )
        
        tag_autocomplete_options.SetFetchResultsAutomatically( True )
        
        self.assertTrue( tag_autocomplete_options.FetchResultsAutomatically() )
        
        tag_autocomplete_options.SetExactMatchCharacterThreshold( None )
        
        self.assertEqual( tag_autocomplete_options.GetExactMatchCharacterThreshold(), None )
        
        tag_autocomplete_options.SetExactMatchCharacterThreshold( 2 )
        
        self.assertEqual( tag_autocomplete_options.GetExactMatchCharacterThreshold(), 2 )
        
    
