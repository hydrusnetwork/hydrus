import datetime
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientTime
from hydrus.client.metadata import ClientMetadataConditional
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientContentUpdates
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
        
    
    def test_type_tag_advanced( self ):
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED, ( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, ( HC.CONTENT_STATUS_CURRENT, ), 'abcdef' ) )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        media_result_pass.GetTagsManager().ProcessContentUpdate(
            CC.DEFAULT_LOCAL_TAG_SERVICE_KEY,
            ClientContentUpdates.ContentUpdate(
                HC.CONTENT_TYPE_MAPPINGS,
                HC.ADD,
                ( 'abcdef', ( media_result_pass.GetHash(), ) )
            )
        )
        
        media_result_fail = media_result_pass.Duplicate()
        
        media_result_fail.GetTagsManager().ProcessContentUpdate(
            CC.DEFAULT_LOCAL_TAG_SERVICE_KEY,
            ClientContentUpdates.ContentUpdate(
                HC.CONTENT_TYPE_MAPPINGS,
                HC.DELETE,
                ( 'abcdef', ( media_result_pass.GetHash(), ) )
            )
        )
        
        self.assertTrue( pred.TestMediaResult( media_result_pass ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED, ( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, ( HC.CONTENT_STATUS_CURRENT, ), 'abcdef' ), inclusive = False )
        
        self.assertTrue( pred.TestMediaResult( media_result_fail ) )
        self.assertFalse( pred.TestMediaResult( media_result_pass ) )
        
    
    def test_type_num_urls( self ):
        
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
        
    
    def test_type_times( self ):
        
        now = datetime.datetime.now()
        
        now_tuple = ( now.year, now.month, now.day, now.hour, now.minute )
        
        time_delta = datetime.timedelta( seconds = 86400 * 10 )
        
        ten_days_ago = now - time_delta
        
        ten_days_ago_tuple = ( ten_days_ago.year, ten_days_ago.month, ten_days_ago.day, ten_days_ago.hour, ten_days_ago.minute )
        
        jobs = [
            ( ( '<', 'delta', ( 1, 1, 1, 1, ) ), 0, - ( 1000 * 86400 * 365 * 2 ) ),
            ( ( '>', 'delta', ( 1, 1, 1, 1, ) ), - ( 1000 * 86400 * 365 * 2 ), 0 ),
            ( ( HC.UNICODE_APPROX_EQUAL, 'delta', ( 1, 1, 1, 1, ) ), - ( ( ( ( 365 + 1 ) * 86400 ) + ( 1 * 3600 ) + ( 1 * 60 ) ) * 1000 ), 0 ),
            ( ( '>', 'date', ten_days_ago_tuple ), 0, - 1000 * 86400 * 20 ),
            ( ( '<', 'date', ten_days_ago_tuple ), - 1000 * 86400 * 20, 0 ),
            #( ( '=', 'date', now_tuple ), 0, - 1000 * 86400 * 2 ),
            #( ( HC.UNICODE_APPROX_EQUAL, 'date', now_tuple ), 0, - 1000 * 86400 * 52 ),
        ]
        # skipping the 'day of' and 'month either way of' date tests since that sounds like too much fun across different calendar systems for the moment
        # maybe doable with some mock.gettime and stuff, but you'd prob want some mock locale gubbins, so let's not push our luck
        
        for ( predicate_value, pass_delta, fail_delta ) in jobs:
            
            pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, predicate_value )
            
            self.assertTrue( pred.CanTestMediaResult() )
            
            media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            media_result_fail = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            media_result_null = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            
            media_result_pass.GetTimesManager().SetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HydrusTime.GetNowMS() + pass_delta )
            media_result_fail.GetTimesManager().SetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HydrusTime.GetNowMS() + fail_delta )
            media_result_null.GetTimesManager().ClearTime( ClientTime.TimestampData( HC.TIMESTAMP_TYPE_IMPORTED, location = CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
            
            self.assertTrue( pred.TestMediaResult( media_result_pass ) )
            self.assertFalse( pred.TestMediaResult( media_result_fail ) )
            self.assertFalse( pred.TestMediaResult( media_result_null ) )
            
            #
            
            pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, predicate_value )
            
            self.assertTrue( pred.CanTestMediaResult() )
            
            media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            media_result_fail = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            media_result_null = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            
            media_result_pass.GetTimesManager().SetFileModifiedTimestampMS( HydrusTime.GetNowMS() + pass_delta )
            media_result_fail.GetTimesManager().SetFileModifiedTimestampMS( HydrusTime.GetNowMS() + fail_delta )
            media_result_null.GetTimesManager().ClearTime( ClientTime.TimestampData( HC.TIMESTAMP_TYPE_MODIFIED_FILE ) )
            
            self.assertTrue( pred.TestMediaResult( media_result_pass ) )
            self.assertFalse( pred.TestMediaResult( media_result_fail ) )
            self.assertFalse( pred.TestMediaResult( media_result_null ) )
            
            #
            
            pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, predicate_value )
            
            self.assertTrue( pred.CanTestMediaResult() )
            
            media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            media_result_fail = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            media_result_null = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            
            media_result_pass.GetTimesManager().SetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER, HydrusTime.GetNowMS() + pass_delta )
            media_result_fail.GetTimesManager().SetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER, HydrusTime.GetNowMS() + fail_delta )
            media_result_null.GetTimesManager().ClearTime( ClientTime.TimestampData( HC.TIMESTAMP_TYPE_LAST_VIEWED, location = CC.CANVAS_MEDIA_VIEWER ) )
            
            self.assertTrue( pred.TestMediaResult( media_result_pass ) )
            self.assertFalse( pred.TestMediaResult( media_result_fail ) )
            self.assertFalse( pred.TestMediaResult( media_result_null ) )
            
            #
            
            pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME, predicate_value )
            
            self.assertTrue( pred.CanTestMediaResult() )
            
            media_result_pass = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            media_result_fail = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            media_result_null = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
            
            media_result_pass.GetTimesManager().SetArchivedTimestampMS( HydrusTime.GetNowMS() + pass_delta )
            media_result_fail.GetTimesManager().SetArchivedTimestampMS( HydrusTime.GetNowMS() + fail_delta )
            media_result_null.GetTimesManager().ClearTime( ClientTime.TimestampData( HC.TIMESTAMP_TYPE_ARCHIVED ) )
            
            self.assertTrue( pred.TestMediaResult( media_result_pass ) )
            self.assertFalse( pred.TestMediaResult( media_result_fail ) )
            self.assertFalse( pred.TestMediaResult( media_result_null ) )
            
        
    
    def test_type_url_url_class( self ):
        
        from hydrus.client.networking import ClientNetworkingURLClass
        from hydrus.client import ClientStrings
        
        url_domain_mask = ClientNetworkingURLClass.URLDomainMask( raw_domains = [ 'somesite.com' ] )
        
        url_class = ClientNetworkingURLClass.URLClass(
            'test',
            url_type = HC.URL_TYPE_POST,
            url_domain_mask = url_domain_mask,
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
        
        url_domain_mask = ClientNetworkingURLClass.URLDomainMask( raw_domains = [ 'obscuresite.com' ] )
        
        url_class = ClientNetworkingURLClass.URLClass(
            'test',
            url_type = HC.URL_TYPE_POST,
            url_domain_mask = url_domain_mask,
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
        
    
    def test_type_url_domain( self ):
        
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
        
    
    def test_type_url_exact_match( self ):
        
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
        
    
    def test_type_url_regex( self ):
        
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
        
    
    def test_type_or( self ):
        
        pred = ClientSearchPredicate.Predicate(
            ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER,
            [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 200 ) ),
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 200 ) )
            ]
        )
        
        self.assertTrue( pred.CanTestMediaResult() )
        
        media_result_pass_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_pass_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_fail = media_result_pass_1.Duplicate()
        
        media_result_pass_1.GetFileInfoManager().width = 195
        media_result_pass_1.GetFileInfoManager().height = 205
        media_result_pass_2.GetFileInfoManager().width = 195
        media_result_pass_2.GetFileInfoManager().height = 205
        media_result_fail.GetFileInfoManager().width = 205
        media_result_fail.GetFileInfoManager().height = 205
        
        self.assertTrue( pred.TestMediaResult( media_result_pass_1 ) )
        self.assertTrue( pred.TestMediaResult( media_result_pass_2 ) )
        self.assertFalse( pred.TestMediaResult( media_result_fail ) )
        
    

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
        
        # num_tags
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        
        num = system_predicate.ExtractValueFromMediaResult( fake_media_result )
        
        self.assertNotEqual( num, 0 )
        self.assertEqual( num, len( fake_media_result.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) ) )
        
        # num_urls
        
        fake_media_result.GetLocationsManager()._urls = {
            'https://somesite.com/123456'
        }
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), len( fake_media_result.GetLocationsManager().GetURLs() ) )
        
        # import time
        
        fake_media_result.GetTimesManager().SetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, 123456 )
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), 123456 )
        
        # modified time
        
        fake_media_result.GetTimesManager().SetDomainModifiedTimestampMS( 'example.com', 123457 )
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), 123457 )
        
        # last viewed time
        
        fake_media_result.GetTimesManager().SetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER, 123458 )
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), 123458 )
        
        # archived time
        
        fake_media_result.GetTimesManager().SetArchivedTimestampMS( 123459 )
        
        system_predicate = ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME )
        
        self.assertTrue( system_predicate.CanExtractValueFromMediaResult() )
        
        self.assertEqual( system_predicate.ExtractValueFromMediaResult( fake_media_result ), 123459 )
        
    
