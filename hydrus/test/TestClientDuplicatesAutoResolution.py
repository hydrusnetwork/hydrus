import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicatesAutoResolutionComparators
from hydrus.client.metadata import ClientMetadataConditional
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import HelperFunctions

class TestComparatorOneFile( unittest.TestCase ):
    
    def test_comparator_1_empty( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_A )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_B )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_EITHER )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_2( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
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
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_A )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_B )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_EITHER )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    

class TestComparatorRelativeFileInfo( unittest.TestCase ):
    
    def test_comparator_0_flat( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 1.0 )
        comparator.SetDelta( 0 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL
            )
        )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 950
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 1.0 )
        comparator.SetDelta( 0 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 995
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_1_delta( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        # exactly 100 px difference
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 1.0 )
        comparator.SetDelta( 100 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 900
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        # at least 100 px difference to get any Trues
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 1.0 )
        comparator.SetDelta( 100 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 900
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 950
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 850
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_2_multiplier( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        # exactly twice
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 2.0 )
        comparator.SetDelta( 0 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 500
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        # at least twice to get any Trues
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 2.0 )
        comparator.SetDelta( 0 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 500
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 600
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 400
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_3_crazy( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        # just for fun
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 2.0 )
        comparator.SetDelta( 100 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_b.GetFileInfoManager().size = media_result_a.GetFileInfoManager().size
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 500
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 450
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 445
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    

class TestComparatorHardcoded( unittest.TestCase ):
    
    def test_comparator_0_filetypes( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_c = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_c ) )
        self.assertFalse( comparator.Test( media_result_c, media_result_a ) )
        
        #
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_c ) )
        self.assertTrue( comparator.Test( media_result_c, media_result_a ) )
        
    

class TestSelector( unittest.TestCase ):
    
    def test_selector_empty( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        self.assertTrue( selector.MatchingPairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertTrue( selector.MatchingPairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_one_way_around( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
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
        
        self.assertFalse( selector.MatchingPairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_both_ways_around( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
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
        
        self.assertTrue( selector.MatchingPairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertTrue( selector.MatchingPairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_no_match( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
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
        
        self.assertEqual( None, selector.GetMatchingAB( media_result_1, media_result_2 ) )
        self.assertEqual( None, selector.GetMatchingAB( media_result_2, media_result_1 ) )
        
    
    def test_multiple_comparators_fail( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator_1 = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
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
        
        comparator_2 = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
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
        
        self.assertEqual( None, selector.GetMatchingAB( media_result_1, media_result_2 ) )
        self.assertEqual( None, selector.GetMatchingAB( media_result_2, media_result_1 ) )
        
    
    def test_multiple_comparators_success( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator_1 = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
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
        
        comparator_2 = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
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
        
        self.assertFalse( selector.MatchingPairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )    
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
