import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.metadata import ClientMetadataConditional
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import HelperFunctions

class TestComparatorOneFile( unittest.TestCase ):
    
    def test_comparator_empty( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolution.LOOKING_AT_A )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolution.LOOKING_AT_B )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolution.LOOKING_AT_EITHER )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolution.LOOKING_AT_A )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolution.LOOKING_AT_B )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolution.LOOKING_AT_EITHER )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    

class TestSelector( unittest.TestCase ):
    
    def test_selector_empty( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolution.PairSelector()
        
        self.assertTrue( selector.PairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertTrue( selector.PairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_one_way_around( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolution.PairSelector()
        
        comparator = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        self.assertFalse( selector.PairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertFalse( selector.PairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_both_ways_around( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolution.PairSelector()
        
        comparator = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 5 ) )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        self.assertTrue( selector.PairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertTrue( selector.PairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_no_match( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolution.PairSelector()
        
        comparator = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 5000000 ) )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        self.assertFalse( selector.PairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertFalse( selector.PairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( None, selector.GetMatchingAB( media_result_1, media_result_2 ) )
        self.assertEqual( None, selector.GetMatchingAB( media_result_2, media_result_1 ) )
        
    
    def test_multiple_comparators_fail( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolution.PairSelector()
        
        comparator_1 = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 5000000 ) )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator_1.SetMetadataConditional( mc )
        
        comparator_2 = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator_2.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator_1, comparator_2 ] )
        
        self.assertFalse( selector.PairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertFalse( selector.PairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( None, selector.GetMatchingAB( media_result_1, media_result_2 ) )
        self.assertEqual( None, selector.GetMatchingAB( media_result_2, media_result_1 ) )
        
    
    def test_multiple_comparators_success( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolution.PairSelector()
        
        comparator_1 = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 5 ) )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator_1.SetMetadataConditional( mc )
        
        comparator_2 = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator_2.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator_1, comparator_2 ] )
        
        self.assertFalse( selector.PairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertFalse( selector.PairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )    
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
