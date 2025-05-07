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
        
        # copied this from some other unit test--whatever
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
        #
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG }, inclusive = False )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        #
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        # 
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG, HC.APPLICATION_PDF } )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
        #
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG, HC.APPLICATION_PDF } )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        # 
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.GENERAL_IMAGE, HC.GENERAL_VIDEO } )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
        # 
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.GENERAL_IMAGE, HC.GENERAL_VIDEO } )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.ANIMATION_GIF )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
    
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
        
    
    def test_num_urls( self ):
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 1 ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ))
        
        #
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 1 ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = set()
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ))
        
    
    def test_url_url_class( self ):
        
        from hydrus.client.networking import ClientNetworkingURLClass
        from hydrus.client import ClientStrings
        
        url_class = ClientNetworkingURLClass.URLClass(
            'test',
            url_type = HC.URL_TYPE_POST,
            netloc = 'somesite.com',
            path_components = [
                ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_ANY, example_string = '123456' ), None )
            ],
            parameters = []
        )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'url_class', url_class, 'whatever' ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( False, 'url_class', url_class, 'whatever' ) )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        #
        
        url_class = ClientNetworkingURLClass.URLClass(
            'test',
            url_type = HC.URL_TYPE_POST,
            netloc = 'obscuresite.com',
            path_components = [
                ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_ANY, example_string = '123456' ), None )
            ],
            parameters = []
        )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'url_class', url_class, 'whatever' ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( False, 'url_class', url_class, 'whatever' ) )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
    
    def test_url_domain( self ):
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'domain', 'somesite.com', 'whatever' ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( False, 'domain', 'somesite.com', 'whatever' ) )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        #
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'domain', 'obscuresite.com', 'whatever' ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( False, 'domain', 'obscuresite.com', 'whatever' ) )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
    
    def test_url_exact_match( self ):
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'exact_match', 'http://somesite.com/123456', 'whatever' ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( False, 'exact_match', 'http://somesite.com/123456', 'whatever' ) )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        #
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'exact_match', 'http://obscuresite.com/123456', 'whatever' ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( False, 'exact_match', 'http://obscuresite.com/123456', 'whatever' ) )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
    
    def test_url_regex( self ):
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'regex', 'some..te', 'whatever' ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( False, 'regex', 'some..te', 'whatever' ) )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        #
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( True, 'regex', 'obscure..te', 'whatever' ) )
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        fake_media_result.GetLocationsManager()._urls = {
            'http://somesite.com/123456',
            'http://othersite.com/123456'
        }
        
        self.assertTrue( system_predicate.CanTestMediaResult() )
        
        self.assertFalse( system_predicate.TestMediaResult( fake_media_result ) )
        
        system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, value = ( False, 'regex', 'obscure..te', 'whatever' ) )
        
        self.assertTrue( system_predicate.TestMediaResult( fake_media_result ) )
        
    

class TestPredicateValueExtraction( unittest.TestCase ):
    
    def test_extract_value( self ):
        
        fake_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        fake_non_image_media_result = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.APPLICATION_XLS )
        fake_non_image_media_result.GetFileInfoManager().width = None
        fake_non_image_media_result.GetFileInfoManager().height = None
        
        # size
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), fake_media_result.GetFileInfoManager().size )
        
        # width
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), fake_media_result.GetFileInfoManager().width )
        
        # height
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), fake_media_result.GetFileInfoManager().height )
        
        # num_pixels
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_PIXELS )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), fake_media_result.GetFileInfoManager().width * fake_media_result.GetFileInfoManager().height )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_non_image_media_result ), None )
        
        # duration
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), fake_media_result.GetFileInfoManager().duration_ms )
        
        # num_frames
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), fake_media_result.GetFileInfoManager().num_frames )
        
        # num_urls
        
        fake_media_result.GetLocationsManager()._urls = {
            'https://somesite.com/123456'
        }
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), len( fake_media_result.GetLocationsManager().GetURLs() ) )
        
    
