import json
import os
import random
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientParsing
from hydrus.client import ClientStrings
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientMetadataMigration
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters

from hydrus.test import HelperFunctions as HF

class TestSingleFileMetadataRouter( unittest.TestCase ):
    
    def test_router( self ):
        
        my_current_storage_tags = { 'samus aran', 'blonde hair' }
        my_current_display_tags = { 'character:samus aran', 'blonde hair' }
        repo_current_storage_tags = { 'lara croft' }
        repo_current_display_tags = { 'character:lara croft' }
        repo_pending_storage_tags = { 'tomb raider' }
        repo_pending_display_tags = { 'series:tomb raider' }
        
        service_keys_to_statuses_to_storage_tags = {
            CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : {
                HC.CONTENT_STATUS_CURRENT : my_current_storage_tags
            },
            HG.test_controller.example_tag_repo_service_key : {
                HC.CONTENT_STATUS_CURRENT : repo_current_storage_tags,
                HC.CONTENT_STATUS_PENDING : repo_pending_storage_tags
            }
        }
        
        service_keys_to_statuses_to_display_tags = {
            CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : {
                HC.CONTENT_STATUS_CURRENT : my_current_display_tags
            },
            HG.test_controller.example_tag_repo_service_key : {
                HC.CONTENT_STATUS_CURRENT : repo_current_display_tags,
                HC.CONTENT_STATUS_PENDING : repo_pending_display_tags
            }
        }
        
        # duplicate to generate proper dicts
        
        tags_manager = ClientMediaManagers.TagsManager(
            service_keys_to_statuses_to_storage_tags,
            service_keys_to_statuses_to_display_tags
        ).Duplicate()
        
        #
        
        hash = HydrusData.GenerateKey()
        size = 40960
        mime = HC.IMAGE_JPEG
        width = 640
        height = 480
        duration = None
        num_frames = None
        has_audio = False
        num_words = None
        
        inbox = True
        
        local_locations_manager = ClientMediaManagers.LocationsManager( { CC.LOCAL_FILE_SERVICE_KEY : 123, CC.COMBINED_LOCAL_FILE_SERVICE_KEY : 123 }, dict(), set(), set(), inbox )
        
        ratings_manager = ClientMediaManagers.RatingsManager( {} )
        
        notes_manager = ClientMediaManagers.NotesManager( {} )
        
        file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager()
        
        #
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 1, hash, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, local_locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
        #
        
        actual_file_path = os.path.join( HG.test_controller.db_dir, 'file.jpg' )
        
        expected_output_path = actual_file_path + '.txt'
        
        # empty, works ok but does nothing
        
        router = ClientMetadataMigration.SingleFileMetadataRouter( importers = [], string_processor = None, exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT() )
        
        router.Work( media_result, actual_file_path )
        
        self.assertFalse( os.path.exists( expected_output_path ) )
        
        # doing everything
        
        rows_1 = [ 'character:samus aran', 'blonde hair' ]
        rows_2 = [ 'character:lara croft', 'brown hair' ]
        
        expected_input_path_1 = actual_file_path + '.1.txt'
        
        with open( expected_input_path_1, 'w', encoding = 'utf-8' ) as f:
            
            f.write( os.linesep.join( rows_1 ) )
            
        
        importer_1 = ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT( suffix = '1' )
        
        expected_input_path_2 = actual_file_path + '.2.txt'
        
        with open( expected_input_path_2, 'w', encoding = 'utf-8' ) as f:
            
            f.write( os.linesep.join( rows_2 ) )
            
        
        importer_2 = ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT( suffix = '2' )
        
        string_processor = ClientStrings.StringProcessor()
        
        processing_steps = [ ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) ]
        
        string_processor.SetProcessingSteps( processing_steps )
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT()
        
        router = ClientMetadataMigration.SingleFileMetadataRouter( importers = [ importer_1, importer_2 ], string_processor = string_processor, exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT() )
        
        router.Work( media_result, actual_file_path )
        
        self.assertTrue( os.path.exists( expected_output_path ) )
        
        with open( expected_output_path, 'r', encoding = 'utf-8' ) as f:
            
            text = f.read()
            
        
        os.unlink( expected_output_path )
        os.unlink( expected_input_path_1 )
        os.unlink( expected_input_path_2 )
        
        result = HydrusText.DeserialiseNewlinedTexts( text )
        expected_result = string_processor.ProcessStrings( set( rows_1 ).union( rows_2 ) )
        
        self.assertTrue( len( result ) > 0 )
        self.assertEqual( set( result ), set( expected_result ) )
        
    

class TestSingleFileMetadataImporters( unittest.TestCase ):
    
    def test_media_tags( self ):
        
        my_current_storage_tags = { 'samus aran', 'blonde hair' }
        my_current_display_tags = { 'character:samus aran', 'blonde hair' }
        repo_current_storage_tags = { 'lara croft' }
        repo_current_display_tags = { 'character:lara croft' }
        repo_pending_storage_tags = { 'tomb raider' }
        repo_pending_display_tags = { 'series:tomb raider' }
        
        service_keys_to_statuses_to_storage_tags = {
            CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : {
                HC.CONTENT_STATUS_CURRENT : my_current_storage_tags
            },
            HG.test_controller.example_tag_repo_service_key : {
                HC.CONTENT_STATUS_CURRENT : repo_current_storage_tags,
                HC.CONTENT_STATUS_PENDING : repo_pending_storage_tags
            }
        }
        
        service_keys_to_statuses_to_display_tags = {
            CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : {
                HC.CONTENT_STATUS_CURRENT : my_current_display_tags
            },
            HG.test_controller.example_tag_repo_service_key : {
                HC.CONTENT_STATUS_CURRENT : repo_current_display_tags,
                HC.CONTENT_STATUS_PENDING : repo_pending_display_tags
            }
        }
        
        # duplicate to generate proper dicts
        
        tags_manager = ClientMediaManagers.TagsManager(
            service_keys_to_statuses_to_storage_tags,
            service_keys_to_statuses_to_display_tags
        ).Duplicate()
        
        #
        
        hash = HydrusData.GenerateKey()
        size = 40960
        mime = HC.IMAGE_JPEG
        width = 640
        height = 480
        duration = None
        num_frames = None
        has_audio = False
        num_words = None
        
        inbox = True
        
        local_locations_manager = ClientMediaManagers.LocationsManager( { CC.LOCAL_FILE_SERVICE_KEY : 123, CC.COMBINED_LOCAL_FILE_SERVICE_KEY : 123 }, dict(), set(), set(), inbox )
        
        ratings_manager = ClientMediaManagers.RatingsManager( {} )
        
        notes_manager = ClientMediaManagers.NotesManager( {} )
        
        file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager()
        
        #
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 1, hash, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, local_locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
        # simple local
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags( service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY )
        
        result = importer.Import( media_result )
        
        self.assertEqual( set( result ), set( my_current_storage_tags ) )
        
        # simple repo
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags( service_key = HG.test_controller.example_tag_repo_service_key )
        
        result = importer.Import( media_result )
        
        self.assertEqual( set( result ), set( repo_current_storage_tags ) )
        
        # all known
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags( service_key = CC.COMBINED_TAG_SERVICE_KEY )
        
        result = importer.Import( media_result )
        
        self.assertEqual( set( result ), set( my_current_storage_tags ).union( repo_current_storage_tags ) )
        
        # with string processor
        
        string_processor = ClientStrings.StringProcessor()
        
        processing_steps = [ ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) ]
        
        string_processor.SetProcessingSteps( processing_steps )
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags( string_processor = string_processor, service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY )
        
        result = importer.Import( media_result )
        
        self.assertTrue( len( result ) > 0 )
        self.assertNotEqual( set( result ), set( my_current_storage_tags ) )
        self.assertEqual( set( result ), set( string_processor.ProcessStrings( my_current_storage_tags ) ) )
        
    
    def test_media_urls( self ):
        
        urls = { 'https://site.com/123456', 'https://cdn5.st.com/file/123456' }
        
        # simple
        
        hash = HydrusData.GenerateKey()
        size = 40960
        mime = HC.IMAGE_JPEG
        width = 640
        height = 480
        duration = None
        num_frames = None
        has_audio = False
        num_words = None
        
        inbox = True
        
        local_locations_manager = ClientMediaManagers.LocationsManager( { CC.LOCAL_FILE_SERVICE_KEY : 123, CC.COMBINED_LOCAL_FILE_SERVICE_KEY : 123 }, dict(), set(), set(), inbox, urls )
        
        # duplicate to generate proper dicts
        
        tags_manager = ClientMediaManagers.TagsManager( {}, {} ).Duplicate()
        
        ratings_manager = ClientMediaManagers.RatingsManager( {} )
        
        notes_manager = ClientMediaManagers.NotesManager( {} )
        
        file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager()
        
        #
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 1, hash, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, local_locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
        # simple
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs()
        
        result = importer.Import( media_result )
        
        self.assertEqual( set( result ), set( urls ) )
        
        # with string processor
        
        string_processor = ClientStrings.StringProcessor()
        
        processing_steps = [ ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) ]
        
        string_processor.SetProcessingSteps( processing_steps )
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs( string_processor = string_processor )
        
        result = importer.Import( media_result )
        
        self.assertTrue( len( result ) > 0 )
        self.assertNotEqual( set( result ), set( urls ) )
        self.assertEqual( set( result ), set( string_processor.ProcessStrings( urls ) ) )
        
    
    def test_media_txt( self ):
        
        actual_file_path = os.path.join( HG.test_controller.db_dir, 'file.jpg' )
        rows = [ 'character:samus aran', 'blonde hair' ]
        
        # simple
        
        expected_input_path = actual_file_path + '.txt'
        
        with open( expected_input_path, 'w', encoding = 'utf-8' ) as f:
            
            f.write( os.linesep.join( rows ) )
            
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT()
        
        result = importer.Import( actual_file_path )
        
        os.unlink( expected_input_path )
        
        self.assertEqual( set( result ), set( rows ) )
        
        # with suffix and processing
        
        string_processor = ClientStrings.StringProcessor()
        
        processing_steps = [ ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) ]
        
        string_processor.SetProcessingSteps( processing_steps )
        
        expected_input_path = actual_file_path + '.tags.txt'
        
        with open( expected_input_path, 'w', encoding = 'utf-8' ) as f:
            
            f.write( os.linesep.join( rows ) )
            
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT( string_processor = string_processor, suffix = 'tags' )
        
        result = importer.Import( actual_file_path )
        
        os.unlink( expected_input_path )
        
        self.assertTrue( len( result ) > 0 )
        self.assertNotEqual( set( result ), set( rows ) )
        self.assertEqual( set( result ), set( string_processor.ProcessStrings( rows ) ) )
        
        # with filename remove ext and string conversion
        
        expected_input_path = os.path.join( HG.test_controller.db_dir, 'file.jpg'[1:].rsplit( '.', 1 )[0] ) + '.txt'
        
        with open( expected_input_path, 'w', encoding = 'utf-8' ) as f:
            
            f.write( os.linesep.join( rows ) )
            
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT( remove_actual_filename_ext = True, filename_string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) )
        
        result = importer.Import( actual_file_path )
        
        os.unlink( expected_input_path )
        
        self.assertTrue( len( result ) > 0 )
        self.assertEqual( set( result ), set( rows ) )
        
    
    def test_media_json( self ):
        
        actual_file_path = os.path.join( HG.test_controller.db_dir, 'file.jpg' )
        rows = [ 'character:samus aran', 'blonde hair' ]
        
        # no file means no rows
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON()
        
        result = importer.Import( actual_file_path )
        
        self.assertEqual( set( result ), set() )
        
        # simple
        
        expected_input_path = actual_file_path + '.json'
        
        with open( expected_input_path, 'w', encoding = 'utf-8' ) as f:
            
            j = json.dumps( rows )
            
            f.write( j )
            
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON()
        
        result = importer.Import( actual_file_path )
        
        os.unlink( expected_input_path )
        
        self.assertEqual( set( result ), set( rows ) )
        
        # with suffix, processing, and dest
        
        string_processor = ClientStrings.StringProcessor()
        
        processing_steps = [ ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) ]
        
        string_processor.SetProcessingSteps( processing_steps )
        
        expected_input_path = actual_file_path + '.tags.json'
        
        with open( expected_input_path, 'w', encoding = 'utf-8' ) as f:
            
            d = { 'file_data' : { 'tags' : rows } }
            
            j = json.dumps( d )
            
            f.write( j )
            
        
        parse_rules = [
            ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'file_data', example_string = 'file_data' ) ),
            ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'tags', example_string = 'tags' ) ),
            ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None )
        ]
        
        json_parsing_formula = ClientParsing.ParseFormulaJSON( parse_rules = parse_rules, content_to_fetch = ClientParsing.JSON_CONTENT_STRING )
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON( string_processor = string_processor, suffix = 'tags', json_parsing_formula = json_parsing_formula )
        
        result = importer.Import( actual_file_path )
        
        os.unlink( expected_input_path )
        
        self.assertTrue( len( result ) > 0 )
        self.assertNotEqual( set( result ), set( rows ) )
        self.assertEqual( set( result ), set( string_processor.ProcessStrings( rows ) ) )
        
        # with filename remove ext and string conversion
        
        expected_input_path = os.path.join( HG.test_controller.db_dir, 'file.jpg'[1:].rsplit( '.', 1 )[0] ) + '.json'
        
        with open( expected_input_path, 'w', encoding = 'utf-8' ) as f:
            
            j = json.dumps( rows )
            
            f.write( j )
            
        
        importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON( remove_actual_filename_ext = True, filename_string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) )
        
        result = importer.Import( actual_file_path )
        
        os.unlink( expected_input_path )
        
        self.assertEqual( set( result ), set( rows ) )
        
    

class TestSingleFileMetadataExporters( unittest.TestCase ):
    
    def test_media_tags( self ):
        
        hash = os.urandom( 32 )
        rows = [ 'character:samus aran', 'blonde hair' ]
        
        # no tags makes no write
        
        service_key = HG.test_controller.example_tag_repo_service_key
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags( service_key )
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        exporter.Export( hash, [] )
        
        with self.assertRaises( Exception ):
            
            [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
            
        
        # simple local
        
        service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags( service_key )
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        exporter.Export( hash, rows )
        
        hashes = { hash }
        
        expected_service_keys_to_content_updates = { service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, hashes ) ) for tag in rows ] }
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_updates( self, service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        # simple repo
        
        service_key = HG.test_controller.example_tag_repo_service_key
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags( service_key )
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        exporter.Export( hash, rows )
        
        hashes = { hash }
        
        expected_service_keys_to_content_updates = { service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, hashes ) ) for tag in rows ] }
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_updates( self, service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
    
    def test_media_urls( self ):
        
        hash = os.urandom( 32 )
        urls = [ 'https://site.com/123456', 'https://cdn5.st.com/file/123456' ]
        
        # no urls makes no write
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs()
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        exporter.Export( hash, [] )
        
        with self.assertRaises( Exception ):
            
            [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
            
        
        # simple
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs()
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        exporter.Export( hash, urls )
        
        expected_service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( urls, { hash } ) ) ] }
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_updates( self, service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
    
    def test_media_txt( self ):
        
        actual_file_path = os.path.join( HG.test_controller.db_dir, 'file.jpg' )
        rows = [ 'character:samus aran', 'blonde hair' ]
        
        # no rows makes no write
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT()
        
        exporter.Export( actual_file_path, [] )
        
        expected_output_path = actual_file_path + '.txt'
        
        self.assertFalse( os.path.exists( expected_output_path ) )
        
        # simple
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT()
        
        exporter.Export( actual_file_path, rows )
        
        expected_output_path = actual_file_path + '.txt'
        
        self.assertTrue( os.path.exists( expected_output_path ) )
        
        with open( expected_output_path, 'r', encoding = 'utf-8' ) as f:
            
            text = f.read()
            
        
        os.unlink( expected_output_path )
        
        self.assertEqual( set( rows ), set( HydrusText.DeserialiseNewlinedTexts( text ) ) )
        
        # with suffix
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT( suffix = 'tags' )
        
        exporter.Export( actual_file_path, rows )
        
        expected_output_path = actual_file_path + '.tags.txt'
        
        self.assertTrue( os.path.exists( expected_output_path ) )
        
        with open( expected_output_path, 'r', encoding = 'utf-8' ) as f:
            
            text = f.read()
            
        
        os.unlink( expected_output_path )
        
        self.assertEqual( set( rows ), set( HydrusText.DeserialiseNewlinedTexts( text ) ) )
        
        # with filename remove ext and string conversion
        
        expected_output_path = os.path.join( HG.test_controller.db_dir, 'file.jpg'[1:].rsplit( '.', 1 )[0] ) + '.txt'
        
        with open( expected_output_path, 'w', encoding = 'utf-8' ) as f:
            
            f.write( os.linesep.join( rows ) )
            
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT( remove_actual_filename_ext = True, filename_string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) )
        
        with open( expected_output_path, 'r', encoding = 'utf-8' ) as f:
            
            text = f.read()
            
        
        os.unlink( expected_output_path )
        
        self.assertEqual( set( rows ), set( HydrusText.DeserialiseNewlinedTexts( text ) ) )
        
    
    def test_media_json( self ):
        
        actual_file_path = os.path.join( HG.test_controller.db_dir, 'file.jpg' )
        rows = [ 'character:samus aran', 'blonde hair' ]
        
        # no rows makes no write
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON()
        
        exporter.Export( actual_file_path, [] )
        
        expected_output_path = actual_file_path + '.json'
        
        self.assertFalse( os.path.exists( expected_output_path ) )
        
        # simple
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON()
        
        exporter.Export( actual_file_path, rows )
        
        expected_output_path = actual_file_path + '.json'
        
        self.assertTrue( os.path.exists( expected_output_path ) )
        
        with open( expected_output_path, 'r', encoding = 'utf-8' ) as f:
            
            text = f.read()
            
        
        os.unlink( expected_output_path )
        
        self.assertEqual( set( rows ), set( json.loads( text ) ) )
        
        # with suffix and json dest
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( suffix = 'tags', nested_object_names = [ 'file_data', 'tags' ] )
        
        exporter.Export( actual_file_path, rows )
        
        expected_output_path = actual_file_path + '.tags.json'
        
        self.assertTrue( os.path.exists( expected_output_path ) )
        
        with open( expected_output_path, 'r', encoding = 'utf-8' ) as f:
            
            text = f.read()
            
        
        os.unlink( expected_output_path )
        
        self.assertEqual( set( rows ), set( json.loads( text )[ 'file_data' ][ 'tags' ] ) )
        
        # with filename remove ext and string conversion
        
        expected_output_path = os.path.join( HG.test_controller.db_dir, 'file.jpg'[1:].rsplit( '.', 1 )[0] ) + '.json'
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( remove_actual_filename_ext = True, filename_string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] ) )
        
        exporter.Export( actual_file_path, rows )
        
        self.assertTrue( os.path.exists( expected_output_path ) )
        
        with open( expected_output_path, 'r', encoding = 'utf-8' ) as f:
            
            text = f.read()
            
        
        os.unlink( expected_output_path )
        
        self.assertEqual( set( rows ), set( json.loads( text ) ) )
        
    
    def test_media_json_combined( self ):
        
        actual_file_path = os.path.join( HG.test_controller.db_dir, 'file.jpg' )
        
        #
        
        tag_rows = [ 'character:samus aran', 'blonde hair' ]
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'file_data', 'tags' ] )
        
        exporter.Export( actual_file_path, tag_rows )
        
        #
        
        url_rows = [ 'https://site.com/123456' ]
        
        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'file_data', 'urls' ] )
        
        exporter.Export( actual_file_path, url_rows )
        
        #
        
        expected_output_path = actual_file_path + '.json'
        
        self.assertTrue( os.path.exists( expected_output_path ) )
        
        with open( expected_output_path, 'r', encoding = 'utf-8' ) as f:
            
            text = f.read()
            
        
        os.unlink( expected_output_path )
        
        self.assertEqual( set( tag_rows ), set( json.loads( text )[ 'file_data' ][ 'tags' ] ) )
        self.assertEqual( set( url_rows ), set( json.loads( text )[ 'file_data' ][ 'urls' ] ) )
        
    
