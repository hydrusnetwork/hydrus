import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.metadata import ClientMetadataConditional
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import HelperFunctions

class TestClientMetadataConditional( unittest.TestCase ):
    
    def test_mc_empty( self ):
        
        media_result_jpeg = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_png = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        self.assertTrue( mc.Test( media_result_jpeg ) )
        self.assertTrue( mc.Test( media_result_png ) )
        
    
    def test_mc_single( self ):
        
        media_result_jpeg = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_png = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        mc.SetFileSearchContext( file_search_context )
        
        self.assertTrue( mc.Test( media_result_jpeg ) )
        self.assertFalse( mc.Test( media_result_png ) )
        
    
    def test_mc_double_fail( self ):
        
        media_result_jpeg = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_png = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } ),
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', media_result_jpeg.GetResolution()[0] - 10 ) )
            ]
        )
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        mc.SetFileSearchContext( file_search_context )
        
        self.assertFalse( mc.Test( media_result_jpeg ) )
        self.assertFalse( mc.Test( media_result_png ) )
        
    
    def test_mc_double_success( self ):
        
        media_result_jpeg = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_png = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } ),
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', media_result_jpeg.GetResolution()[0] + 10 ) )
            ]
        )
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        mc.SetFileSearchContext( file_search_context )
        
        self.assertTrue( mc.Test( media_result_jpeg ) )
        self.assertFalse( mc.Test( media_result_png ) )
        
    

class TestPredicateTesting( unittest.TestCase ):
    
    def test_type_archive( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        media_result_pass.GetLocationsManager().inbox = False
        media_result_fail.GetLocationsManager().inbox = True
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    
    def test_type_filetype( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    
    def test_type_height( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 200 ) )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_pass.GetFileInfoManager().height = 195
        media_result_fail.GetFileInfoManager().height = 205
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    
    def test_type_inbox( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        media_result_pass.GetLocationsManager().inbox = True
        media_result_fail.GetLocationsManager().inbox = False
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    
    def test_type_width( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 200 ) )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_pass.GetFileInfoManager().width = 195
        media_result_fail.GetFileInfoManager().width = 205
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    
    def test_type_exif( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_pass.GetFileInfoManager().has_exif = True
        media_result_fail.GetFileInfoManager().has_exif = False
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
        #
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, value = False )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_pass.GetFileInfoManager().has_exif = False
        media_result_fail.GetFileInfoManager().has_exif = True
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    
    def test_type_icc_profile( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_pass.GetFileInfoManager().has_icc_profile = True
        media_result_fail.GetFileInfoManager().has_icc_profile = False
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
        #
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, value = False )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_pass.GetFileInfoManager().has_icc_profile = False
        media_result_fail.GetFileInfoManager().has_icc_profile = True
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    
    def test_type_human_readable_metadata( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_pass.GetFileInfoManager().has_human_readable_embedded_metadata = True
        media_result_fail.GetFileInfoManager().has_human_readable_embedded_metadata = False
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
        #
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, value = False )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_pass.GetFileInfoManager().has_human_readable_embedded_metadata = False
        media_result_fail.GetFileInfoManager().has_human_readable_embedded_metadata = True
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    
